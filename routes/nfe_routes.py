import json
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from datetime import datetime
from database.connection import get_db
from database.models import Cliente, DestinatarioNFe, Produto, NFeEmitidas, Cfop, Csticms, Csosnicms
from auth.decorators import permission_required
from auth.permissions import get_accessible_client_ids
from services.certificate_service import get_active_certificate_for_client
from services.nfe_service import generate_nfe_xml, sign_xml, send_to_sefaz
from utils.helpers import produto_to_dict_for_template, get_uf_ibge_code
from config.settings import SEFAZ_AMBIENTE_HOMOLOGACAO

nfe_bp = Blueprint('nfe', __name__)

@nfe_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue')
def emitir_nfe():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    if not accessible_client_ids:
        flash('Você não está associado a nenhum cliente ou não tem permissão para emitir NF-e.', 'danger')
        return redirect(url_for('main.home'))
    
    emitente_cliente_id = accessible_client_ids[0]
    emitente_data = db.query(Cliente).options(joinedload(Cliente.regime_tributario)).filter_by(cliente_id=emitente_cliente_id).first()
    
    if not emitente_data:
        flash('Dados do emitente não encontrados.', 'danger')
        return redirect(url_for('main.home'))
    
    emitente_data_for_template = {
        "cliente_id": emitente_data.cliente_id,
        "razao_social": emitente_data.razao_social,
        "cnpj": emitente_data.cnpj,
        "inscricao_estadual": emitente_data.inscricao_estadual,
        "logradouro": emitente_data.logradouro,
        "numero": emitente_data.numero,
        "bairro": emitente_data.bairro,
        "cep": emitente_data.cep,
        "nome_municipio": emitente_data.nome_municipio,
        "uf": emitente_data.uf,
        "cnae": emitente_data.cnae,
        "regime_tributario_nome": emitente_data.regime_tributario.nome if emitente_data.regime_tributario else 'N/A',
        "regime_tributario_id": emitente_data.regime_tributario_id,
        "uf_codigo": get_uf_ibge_code(emitente_data.uf),
        "codigo_municipio": emitente_data.codigo_municipio
    }
    
    destinatarios_obj = db.query(DestinatarioNFe).filter_by(cliente_id=emitente_cliente_id).all()
    destinatarios_for_template = [d.to_dict() for d in destinatarios_obj]
    
    produtos_obj = db.query(Produto).filter_by(cliente_id=emitente_cliente_id).options(
        joinedload(Produto.ncm), 
        joinedload(Produto.cfop),
        joinedload(Produto.origem),
        joinedload(Produto.csts_icms),
        joinedload(Produto.csosns_icms)
    ).all()
    
    produtos_for_template_and_js = [produto_to_dict_for_template(p) for p in produtos_obj]
    
    all_cfops_data = [{"cfop_id": c.cfop_id, "cfop": c.cfop, "descricao": c.descricao} for c in db.query(Cfop).all()]
    all_csts_data = [{"cst_id": c.cst_id, "codigo": c.codigo, "descricao": c.descricao} for c in db.query(Csticms).all()]
    all_csosns_data = [{"csosn_id": c.csosn_id, "codigo": c.codigo, "descricao": c.descricao} for c in db.query(Csosnicms).all()]

    form_data_initial = {}
    initial_nfe_items = []
    
    if request.method == 'POST':
        form_data_initial = request.form.to_dict()
        
        nfe_items_raw = []
        for key in request.form:
            if key.startswith('items[') and key.endswith('][json]'):
                try:
                    nfe_items_raw.append(json.loads(request.form[key]))
                except json.JSONDecodeError as e:
                    flash(f"Erro ao decodificar item JSON: {request.form[key]} - {e}", 'danger')
                    initial_nfe_items = nfe_items_raw
                    return render_template('emitir_nfe.html',
                                           emitente_data=emitente_data_for_template,
                                           destinatarios=destinatarios_for_template,
                                           produtos=produtos_for_template_and_js,
                                           all_cfops=all_cfops_data,
                                           all_csts=all_csts_data,
                                           all_csosns=all_csosns_data,
                                           form_data=form_data_initial,
                                           initial_nfe_items=initial_nfe_items)
        initial_nfe_items = nfe_items_raw
        
        action = request.form.get('action')
        
        # Validações básicas
        if not form_data_initial.get('natOp') or not form_data_initial.get('finNFe'):
            flash('Os campos "Natureza da Operação" e "Finalidade da Emissão" são obrigatórios.', 'danger')
            return render_template('emitir_nfe.html',
                                   emitente_data=emitente_data_for_template,
                                   destinatarios=destinatarios_for_template,
                                   produtos=produtos_for_template_and_js,
                                   all_cfops=all_cfops_data,
                                   all_csts=all_csts_data,
                                   all_csosns=all_csosns_data,
                                   form_data=form_data_initial,
                                   initial_nfe_items=initial_nfe_items)
        
        if not initial_nfe_items:
            flash('É necessário adicionar pelo menos um item à nota fiscal.', 'danger')
            return render_template('emitir_nfe.html',
                                   emitente_data=emitente_data_for_template,
                                   destinatarios=destinatarios_for_template,
                                   produtos=produtos_for_template_and_js,
                                   all_cfops=all_cfops_data,
                                   all_csts=all_csts_data,
                                   all_csosns=all_csosns_data,
                                   form_data=form_data_initial,
                                   initial_nfe_items=initial_nfe_items)
        
        # Processar destinatário
        dest_cnpj_cpf = form_data_initial.get('dest_cnpj_cpf')
        destinatario_data = None
        if dest_cnpj_cpf:
            selected_destinatario = db.query(DestinatarioNFe).filter_by(
                cliente_id=emitente_cliente_id, 
                cpf_cnpj=dest_cnpj_cpf.replace('.', '').replace('/', '').replace('-', '')
            ).first()
            if selected_destinatario:
                destinatario_data = selected_destinatario.to_dict()
            else:
                flash('Destinatário selecionado não encontrado no cadastro.', 'danger')
                return render_template('emitir_nfe.html',
                                       emitente_data=emitente_data_for_template,
                                       destinatarios=destinatarios_for_template,
                                       produtos=produtos_for_template_and_js,
                                       all_cfops=all_cfops_data,
                                       all_csts=all_csts_data,
                                       all_csosns=all_csosns_data,
                                       form_data=form_data_initial,
                                       initial_nfe_items=initial_nfe_items)
        else:
            flash('Destinatário é obrigatório.', 'danger')
            return render_template('emitir_nfe.html',
                                   emitente_data=emitente_data_for_template,
                                   destinatarios=destinatarios_for_template,
                                   produtos=produtos_for_template_and_js,
                                   all_cfops=all_cfops_data,
                                   all_csts=all_csts_data,
                                   all_csosns=all_csosns_data,
                                   form_data=form_data_initial,
                                   initial_nfe_items=initial_nfe_items)
        
        # Gerar XML
        try:
            generated_xml = generate_nfe_xml(
                form_data_initial, 
                emitente_data_for_template, 
                destinatario_data, 
                initial_nfe_items, 
                form_data_initial.get('tpAmb'), 
                action
            )
        except Exception as e:
            flash(f'Erro ao gerar XML da NF-e: {e}', 'danger')
            return render_template('emitir_nfe.html',
                                   emitente_data=emitente_data_for_template,
                                   destinatarios=destinatarios_for_template,
                                   produtos=produtos_for_template_and_js,
                                   all_cfops=all_cfops_data,
                                   all_csts=all_csts_data,
                                   all_csosns=all_csosns_data,
                                   form_data=form_data_initial,
                                   initial_nfe_items=initial_nfe_items)
        
        if action == 'preview':
            return render_template('xml_preview.html', xml_content=generated_xml)
        elif action == 'draft':
            try:
                nfe_draft = NFeEmitidas(
                    cliente_id=emitente_cliente_id,
                    tipo_nfe=form_data_initial.get('finNFe'),
                    json_nfe={'xml_content': generated_xml},
                    status="RASCUNHO",
                    data_criacao=datetime.now(),
                    created_by_user_id=current_user.id
                )
                db.add(nfe_draft)
                db.commit()
                flash('Rascunho da NF-e salvo com sucesso!', 'success')
                return redirect(url_for('nfe.list_nfes'))
            except Exception as e:
                db.rollback()
                flash(f'Erro ao salvar rascunho da NF-e: {e}', 'danger')
                return render_template('emitir_nfe.html',
                                       emitente_data=emitente_data_for_template,
                                       destinatarios=destinatarios_for_template,
                                       produtos=produtos_for_template_and_js,
                                       all_cfops=all_cfops_data,
                                       all_csts=all_csts_data,
                                       all_csosns=all_csosns_data,
                                       form_data=form_data_initial,
                                       initial_nfe_items=initial_nfe_items)
        elif action == 'emitir':
            # Processo de emissão completo
            try:
                certificado = get_active_certificate_for_client(db, emitente_cliente_id)
                
                if not certificado:
                    flash('Nenhum certificado digital ativo encontrado para este cliente.', 'danger')
                    return render_template('emitir_nfe.html',
                                           emitente_data=emitente_data_for_template,
                                           destinatarios=destinatarios_for_template,
                                           produtos=produtos_for_template_and_js,
                                           all_cfops=all_cfops_data,
                                           all_csts=all_csts_data,
                                           all_csosns=all_csosns_data,
                                           form_data=form_data_initial,
                                           initial_nfe_items=initial_nfe_items)
                
                signed_xml = sign_xml(generated_xml, certificado)
                
                ambiente = 2 if SEFAZ_AMBIENTE_HOMOLOGACAO else 1
                sefaz_response = send_to_sefaz(signed_xml, certificado, emitente_data_for_template['cnpj'], ambiente)
                
                if sefaz_response.get("status") == "100":
                    nfe_autorizada = NFeEmitidas(
                        cliente_id=emitente_cliente_id,
                        tipo_nfe=form_data_initial.get('finNFe'),
                        json_nfe={'xml_content': signed_xml},
                        status="AUTORIZADA",
                        chave_acesso=sefaz_response.get("chave_acesso"),
                        protocolo_sefaz=sefaz_response.get("protocolo"),
                        data_criacao=datetime.now(),
                        data_autorizacao=datetime.fromisoformat(sefaz_response["data_autorizacao"]) if sefaz_response.get("data_autorizacao") else datetime.now(),
                        created_by_user_id=current_user.id
                    )
                    db.add(nfe_autorizada)
                    db.commit()
                    flash(f'NF-e emitida com sucesso! Protocolo: {sefaz_response["protocolo"]}', 'success')
                    return redirect(url_for('nfe.list_nfes'))
                else:
                    nfe_rejeitada = NFeEmitidas(
                        cliente_id=emitente_cliente_id,
                        tipo_nfe=form_data_initial.get('finNFe'),
                        json_nfe={'xml_content': signed_xml},
                        status=f"REJEITADA ({sefaz_response.get('status')})",
                        mensagem_sefaz=sefaz_response.get("mensagem"),
                        data_criacao=datetime.now(),
                        created_by_user_id=current_user.id
                    )
                    db.add(nfe_rejeitada)
                    db.commit()
                    flash(f'Erro na emissão da NF-e: {sefaz_response["status"]} - {sefaz_response["mensagem"]}', 'danger')
            except Exception as e:
                flash(f'Erro no processo de emissão: {e}', 'danger')
                return render_template('emitir_nfe.html',
                                       emitente_data=emitente_data_for_template,
                                       destinatarios=destinatarios_for_template,
                                       produtos=produtos_for_template_and_js,
                                       all_cfops=all_cfops_data,
                                       all_csts=all_csts_data,
                                       all_csosns=all_csosns_data,
                                       form_data=form_data_initial,
                                       initial_nfe_items=initial_nfe_items)
    
    return render_template('emitir_nfe.html',
                           emitente_data=emitente_data_for_template,
                           destinatarios=destinatarios_for_template,
                           produtos=produtos_for_template_and_js,
                           all_cfops=all_cfops_data,
                           all_csts=all_csts_data,
                           all_csosns=all_csosns_data,
                           form_data=form_data_initial,
                           initial_nfe_items=initial_nfe_items)

@nfe_bp.route('/list')
@login_required
@permission_required('nfe.read')
def list_nfes():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    from auth.permissions import has_permission
    if has_permission('admin.full_access'):
        nfes = db.query(NFeEmitidas).order_by(NFeEmitidas.data_criacao.desc()).all()
    else:
        nfes = db.query(NFeEmitidas).filter(
            NFeEmitidas.cliente_id.in_(accessible_client_ids)
        ).order_by(NFeEmitidas.data_criacao.desc()).all()
    
    from database.models import Cliente
    clientes = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    cliente_map = {c.cliente_id: c.razao_social for c in clientes}
    return render_template('admin_nfes_list.html', nfes=nfes, cliente_map=cliente_map)
import json
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from datetime import datetime
from database.connection import get_db
from database.models import Cliente, DestinatarioNFe, Produto, NFeEmitidas, Cfop, Csticms, Csosnicms
from auth.decorators import permission_required, admin_required  # ✅ IMPORTAR ADMIN_REQUIRED
from auth.permissions import get_accessible_client_ids
from services.certificate_service import get_active_certificate_for_client
from services.nfe_service import generate_nfe_xml, sign_xml, send_to_sefaz
from utils.helpers import produto_to_dict_for_template, get_uf_ibge_code
from config.settings import SEFAZ_AMBIENTE_HOMOLOGACAO

nfe_bp = Blueprint('nfe', __name__)

# ✅ ADICIONAR ROTA CREATE COMO ALIAS PARA EMITIR_NFE
@nfe_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue')
def create():
    """Alias para emitir_nfe - para compatibilidade com templates"""
    return emitir_nfe()

@nfe_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue')
def emitir_nfe():
    # ✅ INICIALIZAR DB PRIMEIRO
    db = next(get_db())
    
    try:
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
        
        # ✅ ADICIONAR DATA ATUAL PARA O TEMPLATE
        now = datetime.now()
        
        # ✅ DEBUG - PRINT DOS DADOS SENDO ENVIADOS
        print(f"🔍 DEBUG - Dados sendo enviados:")
        print(f"   Emitente: {emitente_data_for_template.get('razao_social', 'N/A')}")
        print(f"   Destinatários: {len(destinatarios_for_template) if destinatarios_for_template else 0}")
        print(f"   Produtos: {len(produtos_for_template_and_js) if produtos_for_template_and_js else 0}")
        print(f"   CFOPs: {len(all_cfops_data) if all_cfops_data else 0}")
        print(f"   CSTs: {len(all_csts_data) if all_csts_data else 0}")
        print(f"   CSOSNs: {len(all_csosns_data) if all_csosns_data else 0}")
        
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
                        return render_template('admin/nfes/emitir.html',
                                               emitente_data=emitente_data_for_template,
                                               destinatarios=destinatarios_for_template,
                                               produtos=produtos_for_template_and_js,
                                               all_cfops=all_cfops_data,
                                               all_csts=all_csts_data,
                                               all_csosns=all_csosns_data,
                                               form_data=form_data_initial,
                                               initial_nfe_items=initial_nfe_items,
                                               now=now)
            initial_nfe_items = nfe_items_raw
            
            action = request.form.get('action')
            
            # Validações básicas
            if not form_data_initial.get('natOp') or not form_data_initial.get('finNFe'):
                flash('Os campos "Natureza da Operação" e "Finalidade da Emissão" são obrigatórios.', 'danger')
                return render_template('admin/nfes/emitir.html',
                                       emitente_data=emitente_data_for_template,
                                       destinatarios=destinatarios_for_template,
                                       produtos=produtos_for_template_and_js,
                                       all_cfops=all_cfops_data,
                                       all_csts=all_csts_data,
                                       all_csosns=all_csosns_data,
                                       form_data=form_data_initial,
                                       initial_nfe_items=initial_nfe_items,
                                       now=now)
            
            if not initial_nfe_items:
                flash('É necessário adicionar pelo menos um item à nota fiscal.', 'danger')
                return render_template('admin/nfes/emitir.html',
                                       emitente_data=emitente_data_for_template,
                                       destinatarios=destinatarios_for_template,
                                       produtos=produtos_for_template_and_js,
                                       all_cfops=all_cfops_data,
                                       all_csts=all_csts_data,
                                       all_csosns=all_csosns_data,
                                       form_data=form_data_initial,
                                       initial_nfe_items=initial_nfe_items,
                                       now=now)
            
            # ✅ PROCESSAR AÇÃO BASEADA NO BOTÃO CLICADO
            ambiente = request.form.get('ambiente', 'homologacao')  # Default para homologação
            
            if action == 'emitir':
                # Emitir NFe nos ambientes específicos
                try:
                    # Aqui viria a lógica de emissão da NFe
                    flash(f'NFe emitida com sucesso no ambiente de {ambiente}!', 'success')
                    return redirect(url_for('nfe.list_nfes'))
                except Exception as e:
                    flash(f'Erro ao emitir NFe: {str(e)}', 'danger')
                    
            elif action == 'rascunho':
                # Salvar como rascunho
                try:
                    # Aqui viria a lógica de salvar rascunho
                    flash('NFe salva como rascunho!', 'success')
                    return redirect(url_for('nfe.list_nfes'))
                except Exception as e:
                    flash(f'Erro ao salvar rascunho: {str(e)}', 'danger')
        
        # ✅ RETORNO FINAL DO GET
        return render_template('admin/nfes/emitir.html',
                               emitente_data=emitente_data_for_template,
                               destinatarios=destinatarios_for_template,
                               produtos=produtos_for_template_and_js,
                               all_cfops=all_cfops_data,
                               all_csts=all_csts_data,
                               all_csosns=all_csosns_data,
                               form_data=form_data_initial,
                               initial_nfe_items=initial_nfe_items,
                               now=now)
    
    except Exception as e:
        print(f"❌ ERRO na rota emitir_nfe: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao carregar dados: {str(e)}', 'error')
        return redirect(url_for('main.home'))
    
    finally:
        # ✅ FECHAR CONEXÃO DB
        if 'db' in locals():
            db.close()

@nfe_bp.route('/list')
@login_required
@permission_required('nfe.read')
def list_nfes():
    db = next(get_db())
    
    try:
        cliente_id = request.args.get('cliente_id')
        
        # ✅ BUSCAR NFEs COM SQL RAW para evitar problemas de ORM
        if cliente_id:
            # Filtrar por cliente específico
            query = text("""
                SELECT 
                    n.nfe_emitida_id,
                    n.cliente_id,
                    n.tipo_nfe,
                    n.finalidade_emissao,
                    n.natureza_operacao,
                    n.status,
                    n.data_criacao,
                    n.destinatario_razao_social,
                    n.destinatario_cnpj_cpf,
                    n.chave_acesso,
                    n.protocolo_sefaz,
                    c.razao_social as cliente_nome
                FROM nfe_emitidas n
                JOIN clientes c ON n.cliente_id = c.cliente_id
                WHERE n.cliente_id = :cliente_id
                ORDER BY n.data_criacao DESC
                LIMIT 100
            """)
            result = db.execute(query, {'cliente_id': cliente_id})
        else:
            # Buscar todas as NFEs acessíveis ao usuário
            accessible_client_ids = get_accessible_client_ids(db)
            if not accessible_client_ids:
                flash('Você não tem acesso a nenhum cliente.', 'warning')
                return redirect(url_for('main.home'))
            
            # Usar placeholders seguros para evitar SQL injection
            placeholders = ','.join([f':id_{i}' for i in range(len(accessible_client_ids))])
            params = {f'id_{i}': client_id for i, client_id in enumerate(accessible_client_ids)}
            
            query = text(f"""
                SELECT 
                    n.nfe_emitida_id,
                    n.cliente_id,
                    n.tipo_nfe,
                    n.finalidade_emissao,
                    n.natureza_operacao,
                    n.status,
                    n.data_criacao,
                    n.destinatario_razao_social,
                    n.destinatario_cnpj_cpf,
                    n.chave_acesso,
                    n.protocolo_sefaz,
                    c.razao_social as cliente_nome
                FROM nfe_emitidas n
                JOIN clientes c ON n.cliente_id = c.cliente_id
                WHERE n.cliente_id IN ({placeholders})
                ORDER BY n.data_criacao DESC
                LIMIT 100
            """)
            result = db.execute(query, params)
        
        # Converter resultado em lista de dicionários
        nfes = [dict(row._mapping) for row in result]
        
        # Buscar clientes para o mapa
        accessible_client_ids = get_accessible_client_ids(db)
        if accessible_client_ids:
            # Usar placeholders seguros
            placeholders = ','.join([f':id_{i}' for i in range(len(accessible_client_ids))])
            params = {f'id_{i}': client_id for i, client_id in enumerate(accessible_client_ids)}
            
            clientes_query = text(f"""
                SELECT cliente_id, razao_social 
                FROM clientes 
                WHERE cliente_id IN ({placeholders})
            """)
            clientes_result = db.execute(clientes_query, params)
            cliente_map = {row.cliente_id: row.razao_social for row in clientes_result}
        else:
            cliente_map = {}
        
        return render_template('admin/nfes/list.html', 
                             nfes=nfes, 
                             cliente_map=cliente_map,
                             cliente_id=cliente_id)
        
    except Exception as e:
        print(f"❌ Erro ao listar NFes: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao listar NFes: {str(e)}', 'error')
        return redirect(url_for('main.home'))
    finally:
        if 'db' in locals():
            db.close()

@nfe_bp.route('/view/<int:nfe_id>')
@login_required
@permission_required('nfe.read')
def view(nfe_id):
    """Visualizar uma NFe específica"""
    db = next(get_db())
    try:
        query = text("""
            SELECT 
                n.*,
                c.razao_social as cliente_nome
            FROM nfe_emitidas n
            JOIN clientes c ON n.cliente_id = c.cliente_id
            WHERE n.nfe_emitida_id = :nfe_id
        """)
        result = db.execute(query, {'nfe_id': nfe_id})
        nfe = result.first()
        
        if not nfe:
            flash('NFe não encontrada.', 'error')
            return redirect(url_for('nfe.list_nfes'))
        
        # Converter para dict
        nfe_data = dict(nfe._mapping)
        
        return render_template('nfe/xml_preview.html', nfe=nfe_data)
        
    except Exception as e:
        flash(f'Erro ao visualizar NFe: {str(e)}', 'error')
        return redirect(url_for('nfe.list_nfes'))
    finally:
        db.close()

@nfe_bp.route('/edit/<int:nfe_id>')
@login_required
@permission_required('nfe.edit')
def edit(nfe_id):
    """Editar uma NFe em rascunho"""
    flash('Funcionalidade de edição em desenvolvimento.', 'info')
    return redirect(url_for('nfe.list_nfes'))

@nfe_bp.route('/download/<int:nfe_id>')
@login_required
@permission_required('nfe.read')
def download(nfe_id):
    """Download do XML da NFe"""
    flash('Funcionalidade de download em desenvolvimento.', 'info')
    return redirect(url_for('nfe.list_nfes'))
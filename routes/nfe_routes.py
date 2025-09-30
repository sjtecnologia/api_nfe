import json
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from datetime import datetime
from database.connection import get_db
from database.models import Cliente, DestinatarioNFe, Produto, NFeEmitidas, Cfop, Csticms, Csosnicms
from auth.decorators import permission_required, admin_required
from auth.permissions import get_accessible_client_ids
from services.certificate_service import get_active_certificate_for_client
from services.nfe_service import generate_nfe_xml, sign_xml, send_to_sefaz
from utils.helpers import produto_to_dict_for_template, get_uf_ibge_code
from config.settings import SEFAZ_AMBIENTE_HOMOLOGACAO

nfe_bp = Blueprint('nfe', __name__)

# ALIAS PARA COMPATIBILIDADE
@nfe_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue')
def create():
    """Alias para emitir_nfe - para compatibilidade com templates"""
    # ✅ SE USUÁRIO NÃO É ADMIN, USAR PRIMEIRO CLIENTE ACESSÍVEL
    if not current_user.is_admin:
        db = next(get_db())
        try:
            accessible_clients = get_accessible_client_ids(db)
            if accessible_clients:
                cliente_id = accessible_clients[0]
                print(f"🔍 Usuário não-admin, redirecionando para cliente: {cliente_id}")
                return redirect(url_for('nfe.emitir_nfe', cliente_id=cliente_id))
        finally:
            db.close()
    
    # Para admin, passar cliente_id se vier da URL
    cliente_id = request.args.get('cliente_id')
    if cliente_id:
        return redirect(url_for('nfe.emitir_nfe', cliente_id=cliente_id))
    
    return emitir_nfe()

@nfe_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue')
def emitir_nfe():
    db = next(get_db())
    
    try:
        # ✅ DETERMINAR CLIENTE - LÓGICA SIMPLIFICADA
        emitente_cliente_id = None
        
        # 1. Tentar pegar cliente_id da URL
        cliente_id_from_url = request.args.get('cliente_id')
        if cliente_id_from_url:
            try:
                emitente_cliente_id = int(cliente_id_from_url)
                print(f"🔍 Cliente ID da URL: {emitente_cliente_id}")
            except ValueError:
                flash('ID do cliente inválido', 'danger')
                return redirect(url_for('home.home'))
        
        # 2. Se não tem cliente_id, definir baseado no tipo de usuário
        if not emitente_cliente_id:
            accessible_clients = get_accessible_client_ids(db)
            
            if not accessible_clients:
                flash('Você não tem acesso a nenhum cliente.', 'danger')
                return redirect(url_for('home.home'))
            
            if current_user.is_admin:
                # Admin precisa especificar cliente
                flash('Selecione um cliente para emitir NFe', 'warning')
                return redirect(url_for('home.home'))
            else:
                # Usuário comum usa primeiro cliente acessível
                emitente_cliente_id = accessible_clients[0]
                print(f"🔍 Usuário não-admin, usando cliente: {emitente_cliente_id}")
        
        # 3. Verificar se usuário tem acesso ao cliente especificado
        accessible_clients = get_accessible_client_ids(db)
        if emitente_cliente_id not in accessible_clients:
            flash('Você não tem acesso a este cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # 4. Buscar dados do cliente
        emitente_data = db.query(Cliente).filter_by(cliente_id=emitente_cliente_id).first()
        if not emitente_data:
            flash('Cliente não encontrado', 'danger')
            return redirect(url_for('home.home'))
        
        print(f"✅ Emitente encontrado: {emitente_data.razao_social}")
        
        # CONVERTER EMITENTE PARA DICIONÁRIO
        emitente_data_for_template = {
            'cliente_id': emitente_data.cliente_id,
            'razao_social': emitente_data.razao_social,
            'cnpj': emitente_data.cnpj,
            'nome_fantasia': emitente_data.nome_fantasia,
            'logradouro': emitente_data.logradouro,
            'numero': emitente_data.numero,
            'bairro': emitente_data.bairro,
            'cep': emitente_data.cep,
            'codigo_municipio': emitente_data.codigo_municipio,
            'nome_municipio': emitente_data.nome_municipio,
            'uf': emitente_data.uf,
            'inscricao_estadual': emitente_data.inscricao_estadual
        }
        
        if request.method == 'POST':
            # CAPTURAR DADOS DO FORMULÁRIO
            form_data_initial = {
                'tpNF': request.form.get('tpNF', '1'),
                'finNFe': request.form.get('finNFe', '1'),
                'dataEmissao': request.form.get('dataEmissao'),
                'serie': request.form.get('serie', '1'),
                'natOp': request.form.get('natOp'),
                'infCpl': request.form.get('infCpl', '')
            }
            
            # PROCESSAR AÇÃO BASEADA NO BOTÃO CLICADO
            action = request.form.get('action')
            ambiente = request.form.get('ambiente', 'homologacao')
            
            print(f"🔍 DEBUG - Ação recebida: {action}, Ambiente: {ambiente}")
            
            if action == 'emitir':
                try:
                    # PROCESSAR EMISSÃO DA NFE
                    tp_amb = 2 if ambiente == 'homologacao' else 1
                    
                    # Buscar destinatário selecionado
                    destinatario_id = request.form.get('destinatario')
                    if not destinatario_id:
                        flash('Destinatário é obrigatório para emitir NFe', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    destinatario = db.query(DestinatarioNFe).filter_by(
                        destinatario_id=destinatario_id,
                        cliente_id=emitente_cliente_id
                    ).first()
                    
                    if not destinatario:
                        flash('Destinatário não encontrado', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    destinatario_data = {
                        'nome_razao_social': destinatario.nome_razao_social,
                        'cpf_cnpj': destinatario.cpf_cnpj,
                        'logradouro': destinatario.logradouro,
                        'numero': destinatario.numero,
                        'bairro': destinatario.bairro,
                        'cep': destinatario.cep,
                        'codigo_municipio': destinatario.codigo_municipio,
                        'nome_municipio': destinatario.nome_municipio,
                        'uf': destinatario.uf
                    }
                    
                    # Processar itens da NFe
                    nfe_items = []
                    item_index = 0
                    
                    while f'items[{item_index}][json]' in request.form:
                        item_json = request.form[f'items[{item_index}][json]']
                        if item_json:
                            try:
                                item_data = json.loads(item_json)
                                nfe_items.append(item_data)
                            except json.JSONDecodeError:
                                flash(f'Erro no formato do item {item_index + 1}', 'danger')
                                return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        item_index += 1
                    
                    if not nfe_items:
                        flash('Adicione pelo menos um item à NFe', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    print(f"📦 Processando {len(nfe_items)} itens")
                    
                    # 1. GERAR XML DA NFE
                    print("🔧 Gerando XML da NFe...")
                    xml_nfe = generate_nfe_xml(
                        form_data_initial, 
                        emitente_data_for_template, 
                        destinatario_data, 
                        nfe_items, 
                        tp_amb, 
                        'emitir'
                    )
                    
                    # 2. BUSCAR CERTIFICADO ATIVO
                    print("🔐 Buscando certificado digital...")
                    certificado = get_active_certificate_for_client(db, emitente_cliente_id)
                    
                    if not certificado:
                        flash('Nenhum certificado digital ativo encontrado. Cadastre um certificado válido.', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # 3. ASSINAR XML
                    print("✍️ Assinando XML...")
                    xml_assinado = sign_xml(xml_nfe, certificado)
                    
                    # 4. ENVIAR PARA SEFAZ
                    print(f"📤 Enviando para Sefaz - Ambiente: {ambiente}")
                    resultado_sefaz = send_to_sefaz(
                        xml_assinado, 
                        certificado, 
                        emitente_data.cnpj, 
                        tp_amb
                    )
                    
                    # 5. SALVAR NO BANCO
                    print("💾 Salvando NFe no banco...")
                    
                    status_nfe = 'AUTORIZADA' if resultado_sefaz.get('status') == '100' else 'REJEITADA'
                    
                    nova_nfe = NFeEmitidas(
                        cliente_id=emitente_cliente_id,
                        tipo_nfe=form_data_initial.get('tpNF', '1'),
                        finalidade_emissao=int(form_data_initial.get('finNFe', '1')),
                        natureza_operacao=form_data_initial.get('natOp', ''),
                        destinatario_razao_social=destinatario_data['nome_razao_social'],
                        destinatario_cnpj_cpf=destinatario_data['cpf_cnpj'],
                        json_nfe={
                            'xml_content': xml_assinado,
                            'form_data': form_data_initial,
                            'items': nfe_items,
                            'ambiente': ambiente,
                            'resultado_sefaz': resultado_sefaz
                        },
                        status=status_nfe,
                        chave_acesso=resultado_sefaz.get('chave_acesso'),
                        protocolo_sefaz=resultado_sefaz.get('protocolo'),
                        mensagem_sefaz=resultado_sefaz.get('mensagem'),
                        data_criacao=datetime.now(),
                        data_autorizacao=datetime.fromisoformat(resultado_sefaz['data_autorizacao']) if resultado_sefaz.get('data_autorizacao') else None,
                        created_by_user_id=current_user.id,
                        informacoes_adicionais=form_data_initial.get('infCpl')
                    )
                    
                    db.add(nova_nfe)
                    db.commit()
                    
                    # 6. FEEDBACK PARA O USUÁRIO
                    if status_nfe == 'AUTORIZADA':
                        flash(f'✅ NFe emitida com sucesso em {ambiente}! Protocolo: {resultado_sefaz.get("protocolo")}', 'success')
                    else:
                        flash(f'❌ NFe rejeitada: {resultado_sefaz.get("mensagem")}', 'danger')
                    
                    return redirect(url_for('nfe.list_nfes', cliente_id=emitente_cliente_id))
                    
                except Exception as e:
                    db.rollback()
                    print(f"❌ ERRO na emissão: {e}")
                    import traceback
                    traceback.print_exc()
                    flash(f'Erro ao emitir NFe: {str(e)}', 'danger')
                    return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        
            elif action == 'rascunho':
                # Salvar como rascunho
                try:
                    nova_nfe = NFeEmitidas(
                        cliente_id=emitente_cliente_id,
                        tipo_nfe=form_data_initial.get('tpNF', '1'),
                        finalidade_emissao=int(form_data_initial.get('finNFe', '1')),
                        natureza_operacao=form_data_initial.get('natOp', ''),
                        json_nfe={'form_data': form_data_initial},
                        status='RASCUNHO',
                        data_criacao=datetime.now(),
                        created_by_user_id=current_user.id,
                        informacoes_adicionais=form_data_initial.get('infCpl')
                    )
                    
                    db.add(nova_nfe)
                    db.commit()
                    
                    flash('NFe salva como rascunho!', 'success')
                    return redirect(url_for('nfe.list_nfes', cliente_id=emitente_cliente_id))
                    
                except Exception as e:
                    db.rollback()
                    flash(f'Erro ao salvar rascunho: {str(e)}', 'danger')
        
        # MÉTODO GET - CARREGAR DADOS PARA O FORMULÁRIO
        
        # BUSCAR DESTINATÁRIOS
        destinatarios = db.query(DestinatarioNFe).filter_by(cliente_id=emitente_cliente_id).all()
        destinatarios_data = []
        for dest in destinatarios:
            destinatarios_data.append({
                'destinatario_id': dest.destinatario_id,
                'nome_razao_social': dest.nome_razao_social,
                'cpf_cnpj': dest.cpf_cnpj,
                'logradouro': dest.logradouro,
                'numero': dest.numero,
                'bairro': dest.bairro,
                'cep': dest.cep,
                'codigo_municipio': dest.codigo_municipio,
                'nome_municipio': dest.nome_municipio,
                'uf': dest.uf
            })
        
        # BUSCAR PRODUTOS
        produtos = db.query(Produto).filter_by(cliente_id=emitente_cliente_id).all()
        produtos_data = []
        for prod in produtos:
            produtos_data.append({
                'produto_id': prod.produto_id,
                'codigo_interno': prod.codigo_interno,
                'descricao': prod.descricao,
                'preco_unitario_padrao': float(prod.preco_unitario_padrao) if prod.preco_unitario_padrao else 0.0,
                'unidade_comercial': prod.unidade_comercial
            })
        
        # BUSCAR CFOPs
        all_cfops = db.query(Cfop).all()
        cfops_data = []
        for cfop in all_cfops:
            cfops_data.append({
                'cfop_id': cfop.cfop_id,
                'cfop': cfop.cfop,
                'descricao': cfop.descricao
            })
        
        # BUSCAR CSTs E CSOSNs
        all_csts = db.query(Csticms).all()
        csts_data = [{'cst_id': cst.cst_id, 'cst': cst.cst, 'descricao': cst.descricao} for cst in all_csts]
        
        all_csosns = db.query(Csosnicms).all()
        csosns_data = [{'csosn_id': csosn.csosn_id, 'csosn': csosn.csosn, 'descricao': csosn.descricao} for csosn in all_csosns]
        
        print(f"📋 Renderizando template com {len(destinatarios_data)} destinatários e {len(produtos_data)} produtos")
        
        return render_template('admin/nfes/emitir.html',
                             emitente_data=emitente_data_for_template,
                             destinatarios=destinatarios_data,
                             produtos=produtos_data,
                             all_cfops=cfops_data,
                             all_csts=csts_data,
                             all_csosns=csosns_data,
                             initial_nfe_items=[])
        
    except Exception as e:
        print(f"❌ Erro geral em emitir_nfe: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao carregar formulário de NFe: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
    finally:
        if 'db' in locals():
            db.close()

# ... resto do código permanece igual ...

@nfe_bp.route('/list')
@login_required
@permission_required('nfe.read')
def list_nfes():
    db = next(get_db())
    
    try:
        cliente_id = request.args.get('cliente_id')
        
        # BUSCAR NFEs COM SQL RAW para evitar problemas de ORM
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
                return redirect(url_for('home.home'))
            
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
        return redirect(url_for('home.home'))
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
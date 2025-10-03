import json
import os
from flask import Blueprint, jsonify, request, render_template, redirect, session, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from datetime import datetime
from database.connection import get_db
from database.models import Cliente, DestinatarioNFe, Produto, NFeEmitidas, Cfop, Csticms, Csosnicms
from auth.decorators import permission_required, admin_required
from auth.permissions import get_accessible_client_ids
from services.certificate_service import get_active_certificate_for_client
from services.nfe_service import NFeService, generate_nfe_xml, sign_xml, send_to_sefaz
from utils.helpers import produto_to_dict_for_template, get_uf_ibge_code
from utils.nfe_validators import validar_dados_nfe, validar_xml_nfe
from config.settings import SEFAZ_AMBIENTE_HOMOLOGACAO

nfe_bp = Blueprint('nfe', __name__)

# ALIAS PARA COMPATIBILIDADE
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
    db = next(get_db())
    
    try:
        # ✅ BUSCAR CLIENTES ACESSÍVEIS PRIMEIRO
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # ✅ DETERMINAR CLIENTE
        emitente_cliente_id = None
        
        # 1. Tentar pegar cliente_id da URL
        cliente_id_from_url = request.args.get('cliente_id')
        if cliente_id_from_url:
            try:
                emitente_cliente_id = int(cliente_id_from_url)
                print(f"🔍 Cliente ID da URL: {emitente_cliente_id}")
                
                # Verificar se usuário tem acesso a este cliente
                if emitente_cliente_id not in accessible_clients:
                    flash('Você não tem acesso a este cliente.', 'danger')
                    return redirect(url_for('home.home'))
            except ValueError:
                flash('ID do cliente inválido', 'danger')
                return redirect(url_for('home.home'))
        
        # 2. Se não tem cliente_id na URL, usar primeiro disponível
        else:
            emitente_cliente_id = accessible_clients[0]
            print(f"🔍 Usando primeiro cliente disponível: {emitente_cliente_id}")
        
        # 3. Buscar dados do cliente
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
            print("📥 === INICIANDO PROCESSAMENTO POST ===")
            
            # CAPTURAR DADOS DO FORMULÁRIO
            form_data_initial = {
                'tpNF': request.form.get('tpNF', '1'),
                'finNFe': request.form.get('finNFe', '1'),
                'dataEmissao': request.form.get('dataEmissao'),
                'serie': request.form.get('serie', '1'),
                'natOp': request.form.get('natOp'),
                'infCpl': request.form.get('infCpl', ''),
                'formaPagamento': request.form.get('formaPagamento'),
                'valorPagamento': request.form.get('valorPagamento'),
                'modFrete': request.form.get('modFrete', '9')
            }
            
            print(f"📋 Form data: {form_data_initial}")
            
            # PROCESSAR AÇÃO BASEADA NO BOTÃO CLICADO
            action = request.form.get('action')
            ambiente = request.form.get('ambiente', 'homologacao')
            
            print(f"🔍 DEBUG - Ação recebida: {action}, Ambiente: {ambiente}")
            
            # ✅ INICIALIZAR VARIÁVEIS OBRIGATÓRIAS
            destinatario_data = None
            nfe_items = []
            
            if action == 'emitir':
                print("🚀 === PROCESSANDO EMISSÃO ===")
                try:
                    # ✅ BUSCAR DESTINATÁRIO SELECIONADO
                    destinatario_id = request.form.get('destinatario')
                    print(f"🎯 Destinatário ID: {destinatario_id}")
                    
                    if not destinatario_id:
                        print("❌ Destinatário não selecionado")
                        flash('Destinatário é obrigatório para emitir NFe', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    destinatario = db.query(DestinatarioNFe).filter_by(
                        destinatario_id=destinatario_id,
                        cliente_id=emitente_cliente_id
                    ).first()
                    
                    if not destinatario:
                        print("❌ Destinatário não encontrado no banco")
                        flash('Destinatário não encontrado', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    print(f"✅ Destinatário encontrado: {destinatario.nome_razao_social}")
                    
                    # ✅ CONVERTER DESTINATÁRIO PARA DICIONÁRIO
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
                    
                    print(f"📋 Destinatário data: {destinatario_data}")
                    
                    # ✅ PROCESSAR ITENS DA NFE
                    print("📦 === PROCESSANDO ITENS ===")
                    item_index = 0
                    
                    while f'items[{item_index}][json]' in request.form:
                        item_json = request.form[f'items[{item_index}][json]']
                        print(f"📄 Item {item_index} JSON: {item_json[:100]}...")
                        
                        if item_json:
                            try:
                                item_data = json.loads(item_json)
                                nfe_items.append(item_data)
                                print(f"📦 Item {item_index + 1}: {item_data.get('descricao', 'Sem descrição')}")
                            except json.JSONDecodeError as e:
                                print(f"❌ Erro JSON no item {item_index}: {e}")
                                flash(f'Erro no formato do item {item_index + 1}: {str(e)}', 'danger')
                                return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        item_index += 1
                    
                    if not nfe_items:
                        print("❌ Nenhum item encontrado")
                        flash('Adicione pelo menos um item à NFe', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    print(f"📦 Processando {len(nfe_items)} itens")
                    
                    # ✅ VALIDAR DADOS ANTES DE PROCESSAR
                    print("🔍 === VALIDANDO DADOS ===")
                    erros_validacao = validar_dados_nfe(form_data_initial, emitente_data_for_template, destinatario_data, nfe_items)
                    
                    if erros_validacao:
                        print(f"❌ Erros de validação: {erros_validacao}")
                        for erro in erros_validacao:
                            flash(f"❌ {erro}", 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    print("✅ Validação passou")
                    
                    # PROCESSAR EMISSÃO DA NFE
                    tp_amb = 2 if ambiente == 'homologacao' else 1
                    print(f"🌍 Ambiente SEFAZ: {tp_amb} ({ambiente})")
                    
                    # 1. GERAR XML DA NFE
                    print("🔧 === GERANDO XML ===")
                    try:
                        xml_nfe = generate_nfe_xml(
                            form_data_initial, 
                            emitente_data_for_template, 
                            destinatario_data, 
                            nfe_items, 
                            tp_amb, 
                            'emitir'
                        )
                        print(f"✅ XML gerado: {len(xml_nfe)} caracteres")
                        print(f"🔍 XML preview: {xml_nfe[:200]}...")
                    except Exception as e:
                        print(f"❌ ERRO ao gerar XML: {e}")
                        import traceback
                        traceback.print_exc()
                        flash(f'Erro ao gerar XML: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # ✅ VALIDAR XML GERADO
                    print("🔍 === VALIDANDO XML ===")
                    try:
                        xml_valido, erros_xml = validar_xml_nfe(xml_nfe)
                        if not xml_valido:
                            print(f"❌ XML inválido: {erros_xml}")
                            for erro in erros_xml:
                                flash(f"❌ XML: {erro}", 'danger')
                            return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        print("✅ XML válido")
                    except Exception as e:
                        print(f"❌ ERRO na validação XML: {e}")
                        flash(f'Erro na validação do XML: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # 2. BUSCAR CERTIFICADO ATIVO
                    print("🔐 === BUSCANDO CERTIFICADO ===")
                    try:
                        certificado = get_active_certificate_for_client(db, emitente_cliente_id)
                        
                        if not certificado:
                            print("❌ Certificado não encontrado")
                            flash('Nenhum certificado digital ativo encontrado. Cadastre um certificado válido.', 'danger')
                            return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        
                        print(f"✅ Certificado encontrado: {certificado.get('common_name', 'N/A')}")
                    except Exception as e:
                        print(f"❌ ERRO ao buscar certificado: {e}")
                        flash(f'Erro ao buscar certificado: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                   # 3. ASSINAR XML
                    print("✍️ === ASSINANDO XML ===")
                    try:
                        from services.xml_signature_service import xml_signature_service
                        xml_assinado = xml_signature_service.sign_nfe_xml(xml_nfe, db, emitente_cliente_id)  # ✅ CORRIGIDO
                        print(f"✅ XML assinado: {len(xml_assinado)} caracteres")
                    except Exception as e:
                        print(f"❌ Erro na assinatura: {e}")
                        flash(f'Erro na assinatura do XML: {e}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))  # ✅ CORRIGIDO
                    
                    # 4. ENVIAR PARA SEFAZ
                    print(f"📤 === ENVIANDO PARA SEFAZ ===")
                    try:
                        nfe_service = NFeService(db)
                        resultado_sefaz = nfe_service._processar_envio_sefaz(
                            xml_assinado,
                            certificado,
                            ambiente
                        )
                        print(f"📨 Resultado SEFAZ: {resultado_sefaz}")
                    except Exception as e:
                        print(f"❌ ERRO ao enviar para SEFAZ: {e}")
                        import traceback
                        traceback.print_exc()
                        flash(f'Erro ao enviar para SEFAZ: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # 5. SALVAR NO BANCO
                    print("💾 === SALVANDO NO BANCO ===")
                    try:
                        # CORREÇÃO: Usar o status retornado pelo serviço em vez de verificar apenas o código
                        status_nfe = resultado_sefaz.get('status', 'REJEITADA') if resultado_sefaz.get('success', False) else 'REJEITADA'
                        print(f"📊 Status NFe: {status_nfe}")
                        
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
                            mensagem_sefaz=resultado_sefaz.get('message'),
                            data_criacao=datetime.now(),
                            data_autorizacao=datetime.fromisoformat(resultado_sefaz['data_autorizacao']) if resultado_sefaz.get('data_autorizacao') else None,
                            created_by_user_id=current_user.id,
                            informacoes_adicionais=form_data_initial.get('infCpl')
                        )
                        
                        db.add(nova_nfe)
                        db.commit()
                        
                        # ✅ CORREÇÃO: Refresh para obter o ID real após commit
                        db.refresh(nova_nfe)
                        # ✅ CORREÇÃO: Acessar o valor do ID corretamente
                        nfe_id_raw = getattr(nova_nfe, 'nfe_emitida_id')
                        
                        # Verificar se o valor pode ser convertido para int
                        if nfe_id_raw is None:
                            raise ValueError("ID da NFe não pode ser None")
                        
                        # Conversão segura para int
                        try:
                            # Verificar tipo antes da conversão para evitar erro de tipo
                            if isinstance(nfe_id_raw, (int, float)):
                                nfe_id = int(nfe_id_raw)
                            elif isinstance(nfe_id_raw, str):
                                nfe_id = int(nfe_id_raw)
                            elif hasattr(nfe_id_raw, '__int__'):
                                nfe_id = nfe_id_raw.__int__()
                            else:
                                # Tentar conversão através de string
                                nfe_id_str = str(nfe_id_raw)
                                nfe_id = int(nfe_id_str)
                        except (ValueError, TypeError, AttributeError) as e:
                            raise ValueError(f"Não foi possível converter o ID da NFe para inteiro: {nfe_id_raw}, tipo: {type(nfe_id_raw)}") from e
                        print(f"✅ NFe salva no banco com ID: {nfe_id}")
                        
                    except Exception as e:
                        print(f"❌ ERRO ao salvar no banco: {e}")
                        db.rollback()
                        import traceback
                        traceback.print_exc()
                        flash(f'Erro ao salvar NFe no banco: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # 6. FEEDBACK PARA O USUÁRIO
                    print("🎉 === FINALIZANDO ===")
                    if status_nfe == 'AUTORIZADA':
                        msg = f'✅ NFe emitida com sucesso em {ambiente}! Protocolo: {resultado_sefaz.get("protocolo")}'
                        print(msg)
                        flash(msg, 'success')
                        # Se o DANFE deve ser gerado automaticamente, faça isso aqui
                        gerar_danfe_automatico = request.form.get('gerar_danfe_auto', 'false')
                        if gerar_danfe_automatico == 'true':
                            try:
                                from services.danfe_service import generate_danfe
                                # ✅ CORREÇÃO: Usar a variável nfe_id que já foi convertida para int
                                pdf_path = generate_danfe(xml_assinado, nfe_id)
                                pdf_url = url_for('static', filename=f'danfe/danfe_{nfe_id}.pdf')
                                # Adicionar URL do DANFE à sessão para mostrar no template de lista
                                if 'danfes_gerados' not in session:
                                    session['danfes_gerados'] = {}
                                session['danfes_gerados'][nfe_id] = {
                                    'url': pdf_url,
                                    'timestamp': datetime.now().timestamp()
                                }
                                
                                # Adicionar mensagem de sucesso
                                flash(f'✅ DANFE gerado automaticamente! <a href="{pdf_url}" target="_blank">Visualizar</a>', 'success')
                            except Exception as e:
                                print(f"❌ Erro ao gerar DANFE automático: {e}")
                                flash(f'⚠️ NFe emitida com sucesso, mas houve um erro ao gerar o DANFE: {str(e)}', 'warning')
                    else:
                        msg = f'❌ NFe rejeitada: {resultado_sefaz.get("message")}'
                        print(msg)
                        flash(msg, 'danger')
                    
                    print("🔄 Redirecionando para lista de NFes...")
                    return redirect(url_for('nfe.list_nfes', cliente_id=emitente_cliente_id))
                    
                except Exception as e:
                    db.rollback()
                    print(f"❌ ERRO GERAL na emissão: {e}")
                    import traceback
                    traceback.print_exc()
                    flash(f'Erro ao emitir NFe: {str(e)}', 'danger')
                    return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        
            elif action == 'rascunho':
                print("📝 === SALVANDO RASCUNHO ===")
                # ✅ SALVAR COMO RASCUNHO (SEM VALIDAÇÕES RIGOROSAS)
                try:
                    # Processar itens básicos para rascunho
                    item_index = 0
                    rascunho_items = []
                    
                    while f'items[{item_index}][json]' in request.form:
                        item_json = request.form[f'items[{item_index}][json]']
                        if item_json:
                            try:
                                item_data = json.loads(item_json)
                                rascunho_items.append(item_data)
                            except (json.JSONDecodeError, ValueError):
                                pass  # Ignorar erros em rascunho
                        item_index += 1
                    
                    nova_nfe = NFeEmitidas(
                        cliente_id=emitente_cliente_id,
                        tipo_nfe=form_data_initial.get('tpNF', '1'),
                        finalidade_emissao=int(form_data_initial.get('finNFe', '1')),
                        natureza_operacao=form_data_initial.get('natOp', ''),
                        json_nfe={
                            'form_data': form_data_initial,
                            'items': rascunho_items
                        },
                        status='RASCUNHO',
                        data_criacao=datetime.now(),
                        created_by_user_id=current_user.id,
                        informacoes_adicionais=form_data_initial.get('infCpl')
                    )
                    
                    db.add(nova_nfe)
                    db.commit()
                    
                    print("✅ Rascunho salvo")
                    flash('📄 NFe salva como rascunho!', 'success')
                    return redirect(url_for('nfe.list_nfes', cliente_id=emitente_cliente_id))
                    
                except Exception as e:
                    db.rollback()
                    print(f"❌ ERRO ao salvar rascunho: {e}")
                    flash(f'Erro ao salvar rascunho: {str(e)}', 'danger')
        
        # MÉTODO GET - CARREGAR DADOS PARA O FORMULÁRIO
        print("📋 === CARREGANDO FORMULÁRIO (GET) ===")
        
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
            # Get the actual value from the Decimal column
            preco_value = getattr(prod, 'preco_unitario_padrao', None)
            preco_float = float(preco_value) if preco_value is not None else 0.0
            
            produtos_data.append({
                'produto_id': prod.produto_id,
                'codigo_interno': prod.codigo_interno,
                'descricao': prod.descricao,
                'preco_unitario_padrao': preco_float,
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
        
        # ✅ BUSCAR CSTs E CSOSNs
        try:
            all_csts = db.query(Csticms).all()
            csts_data = []
            for cst in all_csts:
                csts_data.append({
                    'cst_id': cst.cst_id,
                    'cst': cst.codigo,
                    'descricao': cst.descricao
                })
            
            print(f"📋 CSTs carregados: {len(csts_data)} registros")
            
        except Exception as e:
            print(f"⚠️ Erro ao carregar CSTs: {e}")
            csts_data = []
        
        try:
            all_csosns = db.query(Csosnicms).all()
            csosns_data = []
            for csosn in all_csosns:
                csosns_data.append({
                    'csosn_id': csosn.csosn_id,
                    'csosn': csosn.codigo,
                    'descricao': csosn.descricao
                })
            
            print(f"📋 CSOSNs carregados: {len(csosns_data)} registros")
            
        except Exception as e:
            print(f"⚠️ Erro ao carregar CSOSNs: {e}")
            csosns_data = []
        
        print(f"📋 Renderizando template com {len(destinatarios_data)} destinatários e {len(produtos_data)} produtos para cliente {emitente_cliente_id}")
        
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
        
        # Converter para dict - CORREÇÃO AQUI
        try:
            # Se _mapping é um método, precisamos chamá-lo
            if hasattr(nfe, '_mapping') and callable(nfe._mapping):
                nfe_data = dict(nfe._mapping())
            # Se _mapping é um atributo
            elif hasattr(nfe, '_mapping'):
                nfe_data = dict(nfe._mapping)
            # Fallback para row._asdict() que alguns drivers SQL usam
            elif hasattr(nfe, '_asdict') and callable(nfe._asdict):
                nfe_data = nfe._asdict()
            # Último recurso: converter manualmente
            else:
                nfe_data = {column: getattr(nfe, column) for column in nfe._fields}
        except Exception as e:
            print(f"Erro ao converter resultado para dict: {e}")
            import traceback
            traceback.print_exc()
            # Fallback simples
            nfe_data = {key: getattr(nfe, key) for key in dir(nfe) if not key.startswith('_') and not callable(getattr(nfe, key))}
        
        return render_template('admin/nfes/xml_preview.html', nfe=nfe_data)
        
    except Exception as e:
        print(f"Erro ao visualizar NFe: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao visualizar NFe: {str(e)}', 'error')
        return redirect(url_for('nfe.list_nfes'))
    finally:
        db.close()

@nfe_bp.route('/generate-danfe/<int:nfe_id>', methods=['POST'])
@login_required
@permission_required('nfe.read')
def generate_danfe(nfe_id):
    """Gerar PDF do DANFE para uma NFe"""
    db = next(get_db())
    try:
        # Buscar NFe
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
            return jsonify({'success': False, 'message': 'NFe não encontrada'}), 404
        
        # Converter para dict
        nfe_data = dict(nfe._mapping)
        
        # Verificar se tem XML
        if not nfe_data.get('json_nfe') or not nfe_data['json_nfe'].get('xml_content'):
            return jsonify({'success': False, 'message': 'XML não disponível para esta NFe'}), 400
        
        # Gerar DANFE usando a biblioteca Python NFe
        from services.danfe_service import generate_danfe
        
        try:
            pdf_path = generate_danfe(nfe_data['json_nfe']['xml_content'], nfe_id)
            pdf_url = url_for('static', filename=f'danfe/danfe_{nfe_id}.pdf')
            
            return jsonify({
                'success': True,
                'pdf_url': pdf_url,
                'message': 'DANFE gerado com sucesso'
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Erro ao gerar DANFE: {str(e)}'}), 500
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500
    finally:
        db.close()        

@nfe_bp.route('/generate-danfe-after-issue', methods=['POST'])
@login_required
@permission_required('nfe.read')
def generate_danfe_after_issue():
    """Gerar PDF do DANFE para uma NFe recém emitida"""
    db = next(get_db())
    try:
        # Obter dados do request
        data = request.json or {}
        nfe_id = data.get('nfe_id')
        
        if not nfe_id:
            return jsonify({'success': False, 'message': 'ID da NFe não informado'}), 400
            
        # Buscar NFe
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
            return jsonify({'success': False, 'message': 'NFe não encontrada'}), 404
        
        # Converter para dict
        nfe_data = dict(nfe._mapping)
        
        # Verificar se tem XML
        if not nfe_data.get('json_nfe') or not nfe_data['json_nfe'].get('xml_content'):
            return jsonify({'success': False, 'message': 'XML não disponível para esta NFe'}), 400
        
        # Gerar DANFE usando o serviço
        from services.danfe_service import generate_danfe
        
        try:
            pdf_path = generate_danfe(nfe_data['json_nfe']['xml_content'], nfe_id)
            pdf_url = url_for('static', filename=f'danfe/danfe_{nfe_id}.pdf')
            
            return jsonify({
                'success': True,
                'pdf_url': pdf_url,
                'message': 'DANFE gerado com sucesso'
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Erro ao gerar DANFE: {str(e)}'}), 500
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500
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



# ...existing code...



@nfe_bp.route('/reenviar/<int:nfe_id>', methods=['POST'])
@login_required
@permission_required('nfe.issue')
def reenviar_nfe(nfe_id):
    """Reenviar NFe rejeitada para a SEFAZ"""
    db = next(get_db())
    try:
        # Buscar NFe
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
            return jsonify({'success': False, 'message': 'NFe não encontrada'}), 404
        
        # Converter para dict
        try:
            if hasattr(nfe, '_asdict'):
                nfe_data = nfe._asdict()
            elif hasattr(nfe, '_mapping'):
                mapping = nfe._mapping
                if callable(mapping):
                    nfe_data = dict(mapping())
                else:
                    nfe_data = dict(mapping)
            else:
                nfe_data = {}
                for key in nfe.keys():
                    nfe_data[key] = nfe[key]
        except Exception as e:
            print(f"Erro ao converter NFe para dict: {e}")
            return jsonify({'success': False, 'message': 'Erro ao processar dados da NFe'}), 500
        
        # Verificar se pode ser reenviada
        if nfe_data.get('status', '').upper() not in ['REJEITADA', 'ERRO']:
            return jsonify({
                'success': False, 
                'message': 'Apenas NFes rejeitadas podem ser reenviadas'
            }), 400
        
        # Verificar se tem XML
        json_nfe = nfe_data.get('json_nfe')
        if not json_nfe:
            return jsonify({'success': False, 'message': 'Dados da NFe não encontrados'}), 400
        
        # Se json_nfe for string, converter para dict
        if isinstance(json_nfe, str):
            try:
                import json as json_module
                json_nfe = json_module.loads(json_nfe)
            except ValueError:
                return jsonify({'success': False, 'message': 'Dados JSON da NFe inválidos'}), 400
        
        xml_content = json_nfe.get('xml_content')
        if not xml_content:
            return jsonify({'success': False, 'message': 'XML não disponível'}), 400
        
        # Reenviar para SEFAZ
        # Reenviar para SEFAZ
        nfe_service = NFeService(db)
        try:
            # Buscar certificado para reenvio
            certificado = get_active_certificate_for_client(db, nfe_data['cliente_id'])
            if not certificado:
                return jsonify({'success': False, 'message': 'Certificado não encontrado'}), 400
            
            # Determinar ambiente baseado nos dados originais
            ambiente = json_nfe.get('ambiente', 'homologacao')
            
            # Tentar reenviar
            resultado = nfe_service._processar_envio_sefaz(xml_content, certificado, ambiente)
            
            # Atualizar no banco
            if resultado.get('success', False):
                status = 'AUTORIZADA'
                mensagem = resultado.get('message', 'NFe autorizada com sucesso')
            else:
                status = 'REJEITADA'
                mensagem = resultado.get('message', 'NFe rejeitada novamente')
            
            # Atualizar dados no banco
            update_query = text("""
                UPDATE nfe_emitidas 
                SET status = :status,
                    protocolo_sefaz = :protocolo,
                    mensagem_sefaz = :mensagem,
                    data_autorizacao = :data_autorizacao,
                    chave_acesso = :chave_acesso
                WHERE nfe_emitida_id = :nfe_id
            """)
            
            db.execute(update_query, {
                'status': status,
                'protocolo': resultado.get('protocolo'),
                'mensagem': mensagem,
                'data_autorizacao': datetime.fromisoformat(resultado['data_autorizacao']) if resultado.get('data_autorizacao') else None,
                'chave_acesso': resultado.get('chave_acesso'),
                'nfe_id': nfe_id
            })
            db.commit()
            
            return jsonify({
                'success': resultado.get('success', False),
                'message': mensagem,
                'status': status,
                'protocolo': resultado.get('protocolo'),
                'chave_acesso': resultado.get('chave_acesso')
            })
            
        except Exception as e:
            print(f"Erro no reenvio: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Erro ao reenviar NFe: {str(e)}'
            }), 500
        
    except Exception as e:
        print(f"Erro geral no reenvio: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    finally:
        db.close()

@nfe_bp.route('/emitir-rascunho/<int:nfe_id>', methods=['POST'])
@login_required
@permission_required('nfe.issue')
def emitir_rascunho(nfe_id):
    """Emitir um rascunho de NFe"""
    db = next(get_db())
    try:
        # Buscar rascunho
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
            return jsonify({'success': False, 'message': 'Rascunho não encontrado'}), 404
        
        # Converter para dict
        try:
            if hasattr(nfe, '_asdict'):
                nfe_data = nfe._asdict()
            elif hasattr(nfe, '_mapping'):
                mapping = nfe._mapping
                if callable(mapping):
                    nfe_data = dict(mapping())
                else:
                    nfe_data = dict(mapping)
            else:
                nfe_data = {}
                for key in nfe.keys():
                    nfe_data[key] = nfe[key]
        except Exception as e:
            print(f"Erro ao converter NFe para dict: {e}")
            return jsonify({'success': False, 'message': 'Erro ao processar dados da NFe'}), 500
        
        # Verificar se é realmente um rascunho
        if nfe_data.get('status', '').upper() != 'RASCUNHO':
            return jsonify({
                'success': False, 
                'message': 'Apenas rascunhos podem ser emitidos por esta função'
            }), 400
        
        # Verificar se tem dados necessários
        json_nfe = nfe_data.get('json_nfe')
        if not json_nfe:
            return jsonify({'success': False, 'message': 'Dados do rascunho não encontrados'}), 400
        
        # Se json_nfe for string, converter para dict
        if isinstance(json_nfe, str):
            try:
                import json as json_module
                json_nfe = json_module.loads(json_nfe)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': 'Dados JSON do rascunho inválidos'}), 400
        
        form_data = json_nfe.get('form_data')
        items = json_nfe.get('items')
        
        if not form_data or not items:
            return jsonify({'success': False, 'message': 'Dados incompletos no rascunho'}), 400
        
        # Processar emissão usando o mesmo fluxo da emissão normal
        try:
            # Buscar dados do emitente
            emitente_data = db.query(Cliente).filter_by(cliente_id=nfe_data['cliente_id']).first()
            if not emitente_data:
                return jsonify({'success': False, 'message': 'Dados do emitente não encontrados'}), 400
            
            # Converter emitente para dicionário
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
            
            # 1. Gerar XML
            ambiente = json_nfe.get('ambiente', 'homologacao')
            tp_amb = 2 if ambiente == 'homologacao' else 1
            
            xml_gerado = generate_nfe_xml(
                form_data, 
                emitente_data_for_template, 
                None,  # destinatario será extraído dos form_data
                items, 
                tp_amb, 
                'emitir'
            )
            
            if not xml_gerado:
                return jsonify({'success': False, 'message': 'Erro ao gerar XML'}), 500
            
            # 2. Assinar XML
            from services.xml_signature_service import xml_signature_service
            xml_assinado = xml_signature_service.sign_nfe_xml(xml_gerado, db, nfe_data['cliente_id'])
            
            if not xml_assinado:
                return jsonify({'success': False, 'message': 'Erro ao assinar XML'}), 500
            
            # 3. Enviar para SEFAZ
            certificado = get_active_certificate_for_client(db, nfe_data['cliente_id'])
            if not certificado:
                return jsonify({'success': False, 'message': 'Certificado não encontrado'}), 400
            
            nfe_service = NFeService(db)
            resultado_sefaz = nfe_service._processar_envio_sefaz(xml_assinado, certificado, ambiente)
            
            # 4. Determinar status
            if resultado_sefaz.get('success', False):
                status = 'AUTORIZADA'
                mensagem = resultado_sefaz.get('message', 'NFe autorizada com sucesso')
            else:
                status = 'REJEITADA'
                mensagem = resultado_sefaz.get('message', 'NFe rejeitada')
            
            # Atualizar JSON com XML e resultado
            json_nfe_atualizado = json_nfe.copy()
            json_nfe_atualizado['xml_content'] = xml_assinado
            json_nfe_atualizado['resultado_sefaz'] = resultado_sefaz
            
            # Atualizar no banco
            update_query = text("""
                UPDATE nfe_emitidas 
                SET status = :status,
                    protocolo_sefaz = :protocolo,
                    mensagem_sefaz = :mensagem,
                    data_autorizacao = :data_autorizacao,
                    chave_acesso = :chave_acesso,
                    json_nfe = :json_nfe
                WHERE nfe_emitida_id = :nfe_id
            """)
            
            import json as json_module
            db.execute(update_query, {
                'status': status,
                'protocolo': resultado_sefaz.get('protocolo'),
                'mensagem': mensagem,
                'data_autorizacao': datetime.fromisoformat(resultado_sefaz['data_autorizacao']) if resultado_sefaz.get('data_autorizacao') else None,
                'chave_acesso': resultado_sefaz.get('chave_acesso'),
                'json_nfe': json_module.dumps(json_nfe_atualizado) if isinstance(json_nfe_atualizado, dict) else json_nfe_atualizado,
                'nfe_id': nfe_id
            })
            db.commit()
            
            return jsonify({
                'success': resultado_sefaz.get('success', False),
                'message': mensagem,
                'status': status,
                'protocolo': resultado_sefaz.get('protocolo'),
                'chave_acesso': resultado_sefaz.get('chave_acesso'),
                'nfe_id': nfe_id
            })
            
        except Exception as e:
            print(f"Erro na emissão do rascunho: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Erro ao emitir rascunho: {str(e)}'
            }), 500
        
    except Exception as e:
        print(f"Erro geral na emissão do rascunho: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    finally:
        db.close()

@nfe_bp.route('/compartilhar/<int:nfe_id>', methods=['POST'])
@login_required
@permission_required('nfe.read')
def compartilhar_nfe(nfe_id):
    """Compartilhar NFe por email"""
    db = next(get_db())
    try:
        # Obter dados do request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dados não recebidos'}), 400
            
        email_destino = data.get('email')
        include_danfe = data.get('include_danfe', True)
        include_xml = data.get('include_xml', True)
        
        print(f"📧 Compartilhando NFe {nfe_id} para {email_destino}")
        
        if not email_destino:
            return jsonify({'success': False, 'message': 'Email não informado'}), 400
        
        # Validar email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_destino):
            return jsonify({'success': False, 'message': 'Email inválido'}), 400
        
        # Buscar NFe
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
            return jsonify({'success': False, 'message': 'NFe não encontrada'}), 404
        
        # Converter para dict
        try:
            if hasattr(nfe, '_asdict'):
                nfe_data = nfe._asdict()
            elif hasattr(nfe, '_mapping'):
                mapping = nfe._mapping
                if callable(mapping):
                    nfe_data = dict(mapping())
                else:
                    nfe_data = dict(mapping)
            else:
                nfe_data = {}
                for key in nfe.keys():
                    nfe_data[key] = nfe[key]
        except Exception as e:
            print(f"Erro ao converter NFe para dict: {e}")
            return jsonify({'success': False, 'message': 'Erro ao processar dados da NFe'}), 500
        
        # Verificar se NFe está autorizada
        if nfe_data.get('status', '').upper() != 'AUTORIZADA':
            return jsonify({
                'success': False, 
                'message': 'Apenas NFes autorizadas podem ser compartilhadas'
            }), 400
        
        # Preparar anexos
        anexos = []
        
        try:
            # XML
            if include_xml:
                print(f"📄 Incluindo XML...")
                json_nfe = nfe_data.get('json_nfe')
                if json_nfe:
                    # Se json_nfe for string, converter para dict
                    if isinstance(json_nfe, str):
                        try:
                            json_nfe = json.loads(json_nfe)
                        except json.JSONDecodeError as e:
                            print(f"Erro ao decodificar JSON NFe: {e}")
                            return jsonify({'success': False, 'message': 'Dados JSON da NFe inválidos'}), 400
                    
                    xml_content = json_nfe.get('xml_content')
                    if xml_content:
                        anexos.append({
                            'nome': f'nfe_{nfe_id}.xml',
                            'conteudo': xml_content.encode('utf-8'),
                            'tipo': 'application/xml'
                        })
                        print(f"✅ XML adicionado aos anexos")
                    else:
                        print(f"⚠️ XML content não encontrado")
            
            # DANFE PDF
            if include_danfe:
                print(f"📋 Incluindo DANFE...")
                try:
                    json_nfe = nfe_data.get('json_nfe')
                    if json_nfe:
                        if isinstance(json_nfe, str):
                            json_nfe = json.loads(json_nfe)
                        
                        xml_content = json_nfe.get('xml_content')
                        if xml_content:
                            # ✅ CORREÇÃO: Usar caminho absoluto e verificar se existe
                            from services.danfe_service import generate_danfe
                            
                            # Gerar DANFE
                            pdf_path = generate_danfe(xml_content, nfe_id)
                            print(f"📋 DANFE path: {pdf_path}")
                            
                            if pdf_path:
                                # Verificar se é caminho absoluto
                                if not os.path.isabs(pdf_path):
                                    # Se for relativo, juntar com o diretório da aplicação
                                    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                    pdf_path = os.path.join(app_root, pdf_path)
                                
                                print(f"📋 Caminho absoluto DANFE: {pdf_path}")
                                
                                if os.path.exists(pdf_path):
                                    with open(pdf_path, 'rb') as pdf_file:
                                        pdf_content = pdf_file.read()
                                        anexos.append({
                                            'nome': f'danfe_{nfe_id}.pdf',
                                            'conteudo': pdf_content,
                                            'tipo': 'application/pdf'
                                        })
                                        print(f"✅ DANFE adicionado aos anexos ({len(pdf_content)} bytes)")
                                else:
                                    print(f"❌ Arquivo DANFE não encontrado: {pdf_path}")
                            else:
                                print(f"❌ DANFE não foi gerado")
                        else:
                            print(f"⚠️ XML content não disponível para gerar DANFE")
                except Exception as e:
                    print(f"❌ Erro ao gerar DANFE para compartilhamento: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continuar sem o DANFE se houver erro
            
            if not anexos:
                return jsonify({
                    'success': False, 
                    'message': 'Nenhum anexo disponível para envio'
                }), 400
            
            print(f"📎 Total de anexos preparados: {len(anexos)}")
            
            # Enviar email
            from services.email_service import EmailService
            
            email_service = EmailService()
            
            # Preparar dados do email
            assunto = f'NFe #{nfe_id} - {nfe_data.get("cliente_nome", "")}'
            
            # Verificar se data_autorizacao não é None antes do strftime
            data_autorizacao = nfe_data.get('data_autorizacao')
            if data_autorizacao:
                data_autorizacao_str = data_autorizacao.strftime('%d/%m/%Y %H:%M:%S')
            else:
                data_autorizacao_str = 'N/A'
            
            corpo_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h2 style="color: #007bff; margin: 0;">📋 Nota Fiscal Eletrônica</h2>
                    </div>
                    
                    <p>Prezado(a),</p>
                    <p>Segue em anexo a Nota Fiscal Eletrônica conforme solicitado:</p>
                    
                    <div style="background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin: 20px 0;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #eee;">
                                <td style="padding: 8px; font-weight: bold; width: 40%;">Número NFe:</td>
                                <td style="padding: 8px;">{nfe_id}</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #eee;">
                                <td style="padding: 8px; font-weight: bold;">Emitente:</td>
                                <td style="padding: 8px;">{nfe_data.get('cliente_nome', 'N/A')}</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #eee;">
                                <td style="padding: 8px; font-weight: bold;">Destinatário:</td>
                                <td style="padding: 8px;">{nfe_data.get('destinatario_razao_social', 'N/A')}</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #eee;">
                                <td style="padding: 8px; font-weight: bold;">Chave de Acesso:</td>
                                <td style="padding: 8px; font-family: monospace; font-size: 12px;">{nfe_data.get('chave_acesso', 'N/A')}</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #eee;">
                                <td style="padding: 8px; font-weight: bold;">Protocolo:</td>
                                <td style="padding: 8px;">{nfe_data.get('protocolo_sefaz', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Data de Autorização:</td>
                                <td style="padding: 8px;">{data_autorizacao_str}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; font-size: 14px;">
                        <strong>📎 Anexos inclusos:</strong>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            {"<li>📋 DANFE (PDF)</li>" if include_danfe else ""}
                            {"<li>📄 XML da NFe</li>" if include_xml else ""}
                        </ul>
                    </div>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #666; text-align: center;">
                        Este email foi enviado automaticamente pelo Sistema de NFe.<br>
                        Em caso de dúvidas, entre em contato conosco.
                    </p>
                </div>
            </body>
            </html>
            """
            
            print(f"📧 Enviando email...")
            
            # Enviar
            resultado = email_service.enviar_email(
                destinatario=email_destino,
                assunto=assunto,
                corpo_html=corpo_html,
                anexos=anexos
            )
            
            print(f"📧 Resultado do envio: {resultado}")
            
            if resultado.get('success', False):
                # Log do compartilhamento (opcional - se a tabela existir)
                try:
                    log_query = text("""
                        INSERT INTO nfe_compartilhamentos 
                        (nfe_id, cliente_id, email_destino, user_id, data_compartilhamento, include_danfe, include_xml)
                        VALUES (:nfe_id, :cliente_id, :email, :user_id, :data, :danfe, :xml)
                    """)
                    db.execute(log_query, {
                        'nfe_id': nfe_id,
                        'cliente_id': nfe_data['cliente_id'],  # ✅ ADICIONADO
                        'email': email_destino,
                        'user_id': current_user.id,
                        'data': datetime.now(),
                        'danfe': include_danfe,
                        'xml': include_xml
                    })
                    db.commit()
                    print(f"✅ Log de compartilhamento salvo")
                except Exception as e:
                    print(f"⚠️ Erro ao salvar log de compartilhamento: {e}")            
                
                return jsonify({
                    'success': True,
                    'message': f'NFe compartilhada com sucesso para {email_destino}'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': resultado.get('message', 'Erro ao enviar email')
                }), 500
                
        except Exception as e:
            print(f"❌ Erro no compartilhamento: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Erro ao preparar compartilhamento: {str(e)}'
            }), 500
        
    except Exception as e:
        print(f"❌ Erro geral no compartilhamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    finally:
        db.close()
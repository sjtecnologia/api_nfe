import json
import os
from flask import Blueprint, jsonify, request, render_template, redirect, session, url_for, flash
from typing import Dict, Any
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from datetime import datetime
from database.connection import get_db
from database.models import Cliente, DestinatarioNFe, Produto, NFeEmitidas, Cfop, Csticms, Csosnicms, Ncm, RegimeTributario
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
        
        # Buscar regime tributário
        regime_tributario_nome = 'Regime Normal'
        if emitente_data.regime_tributario_id:
            regime_trib = db.query(RegimeTributario).filter_by(
                regime_tributario_id=emitente_data.regime_tributario_id
            ).first()
            if regime_trib:
                regime_tributario_nome = regime_trib.nome
        
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
            destinatario_data = {}
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
                    
                    # Verificar se destinatario_data foi preenchido
                    if not destinatario_data:
                        print("❌ Dados do destinatário não foram processados")
                        flash('Erro: dados do destinatário não encontrados', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
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
                            destinatario_cnpj_cpf=destinatario_data['cpf_cnpj'].replace('.','').replace('/','').replace('-',''),
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
        
        # BUSCAR PRODUTOS (apenas ativos)
        produtos = db.query(Produto).filter_by(
            cliente_id=emitente_cliente_id,
            ativo=True
        ).all()
        produtos_data = []
        for prod in produtos:
            # Get the actual value from the Decimal column
            preco_value = getattr(prod, 'preco_unitario_padrao', None)
            preco_float = float(preco_value) if preco_value is not None else 0.0
            
            # Buscar códigos NCM e CFOP (não IDs)
            ncm_codigo = None
            if prod.ncm_id:
                ncm_obj = db.query(Ncm).filter_by(ncm_id=prod.ncm_id).first()
                if ncm_obj:
                    ncm_codigo = ncm_obj.codigo
            
            cfop_codigo = None
            if prod.cfop_id:
                cfop_obj = db.query(Cfop).filter_by(cfop_id=prod.cfop_id).first()
                if cfop_obj:
                    cfop_codigo = cfop_obj.cfop
            
            cst_codigo = None
            if prod.cst_id:
                cst_obj = db.query(Csticms).filter_by(cst_id=prod.cst_id).first()
                if cst_obj:
                    cst_codigo = cst_obj.codigo
            
            csosn_codigo = None
            if prod.csosn_id:
                csosn_obj = db.query(Csosnicms).filter_by(csosn_id=prod.csosn_id).first()
                if csosn_obj:
                    csosn_codigo = csosn_obj.codigo
            
            produto_dict = {
                'produto_id': prod.produto_id,
                'codigo_interno': prod.codigo_interno,
                'descricao': prod.descricao,
                'preco_unitario_padrao': preco_float,
                'unidade_comercial': prod.unidade_comercial,
                'ncm_codigo': ncm_codigo,
                'cfop_codigo': cfop_codigo,
                'cst_codigo': cst_codigo,
                'csosn_codigo': csosn_codigo,
                'origem_mercadoria_id': prod.origem_mercadoria
            }
            
            produtos_data.append(produto_dict)
        
        # BUSCAR CFOPs
        all_cfops = db.query(Cfop).all()
        cfops_data = []
        for cfop in all_cfops:
            cfops_data.append({
                'cfop_id': cfop.cfop_id,
                'cfop': cfop.cfop,
                'descricao': cfop.descricao
            })
        
        # BUSCAR NCMs
        all_ncms = db.query(Ncm).all()
        ncms_data = []
        for ncm in all_ncms:
            ncms_data.append({
                'ncm_id': ncm.ncm_id,
                'codigo': ncm.codigo,
                'descricao': ncm.descricao
            })

        # ✅ BUSCAR CSTs E CSOSNs
        try:
            all_csts = db.query(Csticms).all()
            csts_data = []
            for cst in all_csts:
                csts_data.append({
                    'cst_id': cst.cst_id,
                    'codigo': cst.codigo,
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
                    'codigo': csosn.codigo,
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
                             all_ncms=ncms_data,
                             regime_tributario=regime_tributario_nome,
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
        
        # ✅ AJUSTE: Admin comum só vê NFes do cliente ativo
        # Super Admin vê todas as NFes quando cliente_id não é fornecido
        if not cliente_id:
            # Se não forneceu cliente_id, verificar se é Super Admin
            if hasattr(current_user, 'is_super_admin') and current_user.is_super_admin():
                # Super Admin: buscar todos os clientes acessíveis
                accessible_client_ids = get_accessible_client_ids(db)
                print(f"🔑 Super Admin - Clientes acessíveis: {accessible_client_ids}")
            else:
                # Admin Comum: pegar apenas cliente ativo da sessão
                # ✅ CORREÇÃO: usar 'current_client_id' que é a chave correta na sessão
                cliente_ativo_id = session.get('current_client_id')
                print(f"🔍 Admin Comum - Cliente ativo na sessão: {cliente_ativo_id}")
                print(f"🔍 Sessão completa: {dict(session)}")
                
                if not cliente_ativo_id:
                    flash('Selecione um cliente para visualizar as NFes.', 'warning')
                    return redirect(url_for('home.home'))
                accessible_client_ids = [cliente_ativo_id]
                print(f"✅ Admin Comum - Filtrando NFes do cliente: {cliente_ativo_id}")
        else:
            # Se forneceu cliente_id específico, usar ele
            accessible_client_ids = [int(cliente_id)]
            cliente_id = int(cliente_id)  # Garantir que é int
            print(f"🎯 Cliente específico fornecido: {cliente_id}")
        
        # Verificar se tem acesso aos clientes
        if not accessible_client_ids:
            flash('Você não tem acesso a nenhum cliente.', 'warning')
            return redirect(url_for('home.home'))
        
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
            # Buscar NFEs dos clientes acessíveis (Super Admin = todos, Admin Comum = apenas ativo)
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
        
        # Se for NFC-e, redirecionar para a página correta
        if nfe_data.get('tipo_nfe') == 'NFCE':
            return redirect(url_for('nfce.consultar_nfce', nfce_id=nfe_id))
        
        # Parse json_nfe se for string
        if nfe_data.get('json_nfe') and isinstance(nfe_data['json_nfe'], str):
            try:
                import json
                nfe_data['json_nfe'] = json.loads(nfe_data['json_nfe'])
            except Exception as e:
                print(f"Erro ao fazer parse do json_nfe: {e}")
                nfe_data['json_nfe'] = None
        
        print(nfe_data)
        return render_template('admin/nfes/xml_preview.html', nfe=nfe_data)
        
    except Exception as e:
        print(f"Erro ao visualizar NFe: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao visualizar NFe: {str(e)}', 'error')
        return redirect(url_for('nfe.list_nfes'))
    finally:
        if db is not None:
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

# Substituir todo o método edit:

@nfe_bp.route('/edit/<int:nfe_id>', methods=['GET', 'POST'])
@login_required
def edit(nfe_id):
    """Editar NFe (rascunho ou rejeitada)"""
    db = next(get_db())
    
    try:
        if request.method == 'GET':
            try:
                # Buscar NFe
                nfe_query = text("""
                    SELECT ne.*, c.razao_social as cliente_nome 
                    FROM nfe_emitidas ne
                    JOIN clientes c ON ne.cliente_id = c.cliente_id
                    WHERE ne.nfe_emitida_id = :nfe_id
                """)
                nfe_result = db.execute(nfe_query, {'nfe_id': nfe_id}).fetchone()
                
                if not nfe_result:
                    flash('NF-e não encontrada', 'error')
                    return redirect(url_for('nfe.list_nfes'))
                
                # ✅ CONVERSÃO SEGURA PARA DICIONÁRIO - CORREÇÃO PRINCIPAL
                try:
                    # Método 1: _asdict() para Row objects
                    if hasattr(nfe_result, '_asdict') and callable(nfe_result._asdict):
                        nfe_data = nfe_result._asdict()
                    # Método 2: _mapping para alguns drivers
                    elif hasattr(nfe_result, '_mapping'):
                        mapping = nfe_result._mapping
                        if callable(mapping):
                            nfe_data = dict(mapping())
                        else:
                            nfe_data = dict(mapping)
                    # Método 3: tentativa com keys() (mais defensivo)
                    elif hasattr(nfe_result, 'keys'):
                        try:
                            keys_attr = nfe_result.keys
                            raw_keys = keys_attr() if callable(keys_attr) else keys_attr
                            if isinstance(raw_keys, (list, tuple, set)):
                                keys_list = list(raw_keys)
                            elif hasattr(raw_keys, '__iter__'):
                                keys_list = list(raw_keys)  # type: ignore[arg-type]
                            else:
                                keys_list = []
                            nfe_data = {}
                            for key in keys_list:
                                try:
                                    nfe_data[key] = nfe_result[key]
                                except Exception:
                                    nfe_data[key] = getattr(nfe_result, key, None)
                            if not nfe_data:
                                raise ValueError('Nenhum dado convertido via keys()')
                        except Exception:
                            # Fallback adicional antes do método 4
                            try:
                                nfe_data = dict(getattr(nfe_result, '_mapping'))
                            except Exception:
                                nfe_data = {}
                    # Método 4: Conversão manual usando índices conhecidos
                    else:
                        # Lista das colunas na ordem da query
                        colunas = [
                            'nfe_emitida_id', 'cliente_id', 'numero_nfe', 'serie', 'chave_acesso',
                            'protocolo_sefaz', 'data_emissao', 'data_autorizacao', 'status', 
                            'valor_total', 'natureza_operacao', 'tipo_nfe', 'finalidade_emissao',
                            'destinatario_razao_social', 'destinatario_cnpj_cpf', 'informacoes_adicionais',
                            'mensagem_sefaz', 'json_nfe', 'data_criacao', 'created_by_user_id',
                            'cliente_nome'  # Campo do JOIN
                        ]
                        
                        nfe_data = {}
                        for i, coluna in enumerate(colunas):
                            try:
                                nfe_data[coluna] = nfe_result[i] if i < len(nfe_result) else None
                            except (IndexError, TypeError):
                                nfe_data[coluna] = None
                
                except Exception as conv_error:
                    print(f"❌ Erro na conversão manual: {conv_error}")
                    flash('Erro ao processar dados da NFe', 'error')
                    return redirect(url_for('nfe.list_nfes'))
                
                print(f"✅ NFe {nfe_id} carregada para edição - Status: {nfe_data.get('status', 'N/A')}")
                
                # Verificar se pode ser editada
                status_editaveis = ['RASCUNHO', 'REJEITADA', 'ERRO']
                current_status = nfe_data.get('status', '').upper()
                if current_status not in status_editaveis:
                    print(f"⚠️ Status '{current_status}' não é editável")
                    flash('Esta NF-e não pode ser editada', 'error')
                    return redirect(url_for('nfe.view', nfe_id=nfe_id))
                
                # Extrair dados do JSON para preencher o formulário
                form_data = {}
                items_data = []
                
                json_nfe_raw = nfe_data.get('json_nfe')
                if json_nfe_raw:
                    try:
                        if isinstance(json_nfe_raw, str):
                            json_data = json.loads(json_nfe_raw)
                        elif isinstance(json_nfe_raw, dict):
                            json_data = json_nfe_raw
                        else:
                            print(f"⚠️ json_nfe em formato inesperado: {type(json_nfe_raw)}")
                            json_data = {}
                        
                        form_data = json_data.get('form_data', {})
                        items_data = json_data.get('items', [])
                        
                        print(f"📋 Form data extraído: {len(form_data)} campos")
                        print(f"📦 Items extraídos: {len(items_data)} itens")
                        
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"⚠️ Erro ao decodificar JSON NFe: {e}")
                        # Criar form_data básico a partir dos campos da tabela
                        data_emissao = nfe_data.get('data_emissao')
                        form_data = {
                            'natOp': nfe_data.get('natureza_operacao', ''),
                            'serie': str(nfe_data.get('serie', '1')),
                            'tpNF': str(nfe_data.get('tipo_nfe', '1')),
                            'finNFe': str(nfe_data.get('finalidade_emissao', '1')),
                            'infCpl': nfe_data.get('informacoes_adicionais', ''),
                            'dataEmissao': data_emissao.isoformat() if isinstance(data_emissao, datetime) else None
                        }
                        items_data = []
                
                # Buscar dados auxiliares com conversão segura
                print("📊 Carregando dados auxiliares...")
                
                # ✅ CLIENTES
                try:
                    clientes_query = text("SELECT cliente_id, razao_social FROM clientes WHERE ativo = true ORDER BY razao_social")
                    clientes_result = db.execute(clientes_query).fetchall()
                    clientes = []
                    for cliente_row in clientes_result:
                        try:
                            if hasattr(cliente_row, '_asdict'):
                                clientes.append(cliente_row._asdict())
                            elif hasattr(cliente_row, '_mapping'):
                                mapping = cliente_row._mapping
                                if callable(mapping):
                                    clientes.append(dict(mapping()))
                                else:
                                    clientes.append(dict(mapping))
                            else:
                                clientes.append({
                                    'cliente_id': cliente_row[0],
                                    'razao_social': cliente_row[1]
                                })
                        except Exception as e:
                            print(f"⚠️ Erro ao processar cliente: {e}")
                            continue
                except Exception as e:
                    print(f"⚠️ Erro ao buscar clientes: {e}")
                    clientes = []
                
                # ✅ CFOPS
                try:
                    cfops_query = text("SELECT cfop, descricao FROM cfops ORDER BY cfop")
                    cfops_result = db.execute(cfops_query).fetchall()
                    cfops = []
                    for cfop_row in cfops_result:
                        try:
                            if hasattr(cfop_row, '_asdict'):
                                cfops.append(cfop_row._asdict())
                            elif hasattr(cfop_row, '_mapping'):
                                mapping = cfop_row._mapping
                                if callable(mapping):
                                    cfops.append(dict(mapping()))
                                else:
                                    cfops.append(dict(mapping))
                            else:
                                cfops.append({
                                    'cfop': cfop_row[0],
                                    'descricao': cfop_row[1]
                                })
                        except Exception as e:
                            print(f"⚠️ Erro ao processar CFOP: {e}")
                            continue
                except Exception as e:
                    print(f"⚠️ Erro ao buscar CFOPs: {e}")
                    cfops = []
                
                # ✅ NCMs
                try:
                    ncms_query = text("SELECT codigo, descricao FROM ncms ORDER BY codigo")
                    ncms_result = db.execute(ncms_query).fetchall()
                    ncms = []
                    for ncm_row in ncms_result:
                        try:
                            if hasattr(ncm_row, '_asdict'):
                                ncms.append(ncm_row._asdict())
                            elif hasattr(ncm_row, '_mapping'):
                                mapping = ncm_row._mapping
                                if callable(mapping):
                                    ncms.append(dict(mapping()))
                                else:
                                    ncms.append(dict(mapping))
                            else:
                                ncms.append({
                                    'codigo': ncm_row[0],
                                    'descricao': ncm_row[1]
                                })
                        except Exception as e:
                            print(f"⚠️ Erro ao processar NCM: {e}")
                            continue
                except Exception as e:
                    print(f"⚠️ Erro ao buscar NCMs: {e}")
                    ncms = []

                # ✅ CSTs
                try:
                    csts_query = text("SELECT codigo, descricao FROM cst_icms ORDER BY codigo ")
                    csts_result = db.execute(csts_query).fetchall()
                    csts = []
                    for cst_row in csts_result:
                        try:
                            if hasattr(cst_row, '_asdict'):
                                csts.append(cst_row._asdict())
                            elif hasattr(cst_row, '_mapping'):
                                mapping = cst_row._mapping
                                if callable(mapping):
                                    csts.append(dict(mapping()))
                                else:
                                    csts.append(dict(mapping))
                            else:
                                csts.append({
                                    'codigo': cst_row[0],
                                    'descricao': cst_row[1]
                                })
                        except Exception as e:
                            print(f"⚠️ Erro ao processar CST: {e}")
                            continue
                except Exception as e:
                    print(f"⚠️ Erro ao buscar CSTs: {e}")
                    csts = []
                
                # ✅ PRODUTOS
                try:
                    produtos_query = text("SELECT produto_id, codigo_interno, descricao FROM produtos WHERE ativo = true ORDER BY descricao")
                    produtos_result = db.execute(produtos_query).fetchall()
                    produtos = []
                    for produto_row in produtos_result:
                        try:
                            if hasattr(produto_row, '_asdict'):
                                produtos.append(produto_row._asdict())
                            elif hasattr(produto_row, '_mapping'):
                                mapping = produto_row._mapping
                                if callable(mapping):
                                    produtos.append(dict(mapping()))
                                else:
                                    produtos.append(dict(mapping))
                            else:
                                produtos.append({
                                    'produto_id': produto_row[0],
                                    'codigo_interno': produto_row[1],
                                    'descricao': produto_row[2]
                                })
                        except Exception as e:
                            print(f"⚠️ Erro ao processar produto: {e}")
                            continue
                except Exception as e:
                    print(f"⚠️ Erro ao buscar produtos: {e}")
                    produtos = []
                
                print(f"📊 Dados auxiliares carregados: {len(clientes)} clientes, {len(cfops)} CFOPs, {len(ncms)} NCMs, {len(produtos)} produtos")
                
                return render_template('admin/nfes/edit.html',
                                     nfe=nfe_data,
                                     form_data=form_data,
                                     items_data=items_data,
                                     clientes=clientes,
                                     cfops=cfops,
                                     ncms=ncms,
                                     csts=csts,
                                     produtos=produtos,
                                     from_rejected=request.args.get('from') == 'rejected')
                
            except Exception as e:
                print(f"❌ Erro ao carregar NFe para edição: {e}")
                import traceback
                traceback.print_exc()
                flash('Erro ao carregar NF-e', 'error')
                return redirect(url_for('nfe.list_nfes'))
        
        elif request.method == 'POST':
            # ... código do POST permanece o mesmo ...
            try:
                # Processar dados do formulário
                dados_nfe = {
                    'dataEmissao': request.form.get('dataEmissao'),
                    'serie': request.form.get('serie', '1'),
                    'natOp': request.form.get('natOp'),
                    'tpNF': request.form.get('tpNF', '1'),
                    'finNFe': request.form.get('finNFe', '1'),
                    'modFrete': request.form.get('modFrete', '9'),
                    'formaPagamento': request.form.get('formaPagamento', '01'),
                    'valorPagamento': request.form.get('valorPagamento'),
                    'infCpl': request.form.get('infCpl', '')
                }
                
                # ✅ CORREÇÃO: Processar itens com CFOP obrigatório
                itens = []
                item_indices = request.form.getlist('item_index')
                
                for i, idx in enumerate(item_indices):
                    # ✅ BUSCAR CFOP DO PRODUTO SE NÃO FORNECIDO
                    cfop_item = request.form.get(f'cfop_{idx}')
                    codigo_produto = request.form.get(f'codigo_produto_{idx}')
                    
                    # Se CFOP não fornecido, buscar do produto
                    if not cfop_item or cfop_item.strip() == '':
                        print(f"⚠️ CFOP vazio para item {i+1}, buscando do produto {codigo_produto}")
                        
                        if codigo_produto:
                            try:
                                # Buscar CFOP padrão do produto
                                produto_query = text("""
                                    SELECT p.cfop_padrao, rt.cfop 
                                    FROM produtos p
                                    LEFT JOIN regras_tributacao rt ON p.produto_id = rt.produto_id
                                    WHERE p.codigo_interno = :codigo OR p.produto_id = :codigo
                                    ORDER BY rt.regra_tributacao_id DESC
                                    LIMIT 1
                                """)
                                
                                produto_result = db.execute(produto_query, {
                                    'codigo': codigo_produto
                                }).fetchone()
                                
                                if produto_result:
                                    # Tentar primeiro o CFOP da regra de tributação, depois o padrão do produto
                                    cfop_produto = produto_result[1] or produto_result[0]
                                    if cfop_produto:
                                        cfop_item = str(cfop_produto).replace('.', '').replace('-', '')
                                        print(f"✅ CFOP encontrado para produto {codigo_produto}: {cfop_item}")
                                    else:
                                        cfop_item = '5102'  # CFOP padrão para venda
                                        print(f"⚠️ CFOP não encontrado para produto {codigo_produto}, usando padrão: {cfop_item}")
                                else:
                                    cfop_item = '5102'
                                    print(f"⚠️ Produto {codigo_produto} não encontrado, usando CFOP padrão: {cfop_item}")
                            except Exception as e:
                                print(f"❌ Erro ao buscar CFOP do produto: {e}")
                                cfop_item = '5102'
                        else:
                            cfop_item = '5102'
                            print(f"⚠️ Código do produto vazio, usando CFOP padrão: {cfop_item}")
                    
                    # ✅ VALIDAR E FORMATAR CFOP
                    if cfop_item:
                        cfop_item = str(cfop_item).replace('.', '').replace('-', '').strip()
                        if len(cfop_item) != 4 or not cfop_item.isdigit():
                            print(f"⚠️ CFOP inválido '{cfop_item}', usando padrão '5102'")
                            cfop_item = '5102'
                    else:
                        cfop_item = '5102'
                    
                    item = {
                        'codigo_produto': codigo_produto,
                        'descricao': request.form.get(f'descricao_{idx}'),
                        'ncm': request.form.get(f'ncm_{idx}'),
                        'cfop': cfop_item,  # ✅ CFOP garantido
                        'origem': request.form.get(f'origem_{idx}', '0'),
                        'cst_icms': request.form.get(f'cst_icms_{idx}', '00'),
                        'aliquota_icms': request.form.get(f'aliquota_icms_{idx}', '0'),
                        'bc_icms': request.form.get(f'bc_icms_{idx}', '0'),
                        'valor_icms': request.form.get(f'valor_icms_{idx}', '0'),
                        'quantidade': request.form.get(f'quantidade_{idx}'),
                        'unidade': request.form.get(f'unidade_{idx}'),
                        'valor_unitario': request.form.get(f'valor_unitario_{idx}'),
                        'valor_total': request.form.get(f'valor_total_{idx}')
                    }
                    
                    print(f"📦 Item {i+1} processado - CFOP: {item['cfop']}, Produto: {item['codigo_produto']}")
                    itens.append(item)
                
                cliente_id = request.form.get('cliente_id')
                
                # Validações básicas
                if not cliente_id or not dados_nfe['natOp'] or not itens:
                    flash('Preencha todos os campos obrigatórios', 'error')
                    return redirect(url_for('nfe.edit', nfe_id=nfe_id))
                
                # Buscar NFe atual
                nfe_query = text("SELECT status FROM nfe_emitidas WHERE nfe_emitida_id = :nfe_id")
                nfe_result = db.execute(nfe_query, {'nfe_id': nfe_id}).fetchone()
                
                if not nfe_result:
                    flash('NF-e não encontrada', 'error')
                    return redirect(url_for('nfe.list_nfes'))
                
                # Verificar se pode ser editada
                status_editaveis = ['RASCUNHO', 'REJEITADA', 'ERRO']
                current_status = nfe_result[0] if nfe_result else ''  # Acessar por índice
                if current_status.upper() not in status_editaveis:
                    flash('Esta NF-e não pode ser editada', 'error')
                    return redirect(url_for('nfe.view', nfe_id=nfe_id))
                
                # Buscar destinatário correto
                # destinatario_cnpj_cpf = request.form.get('destinatario_cnpj_cpf')  # ou o nome do campo correto do formulário
                destinatario_query = text("SELECT * FROM nfe_emitidas WHERE WHERE nfe_emitida_id = :nfe_id")
                destinatario_result = db.execute(destinatario_query, {'nfe_id': nfe_id}).fetchone()
                
                if not destinatario_result:
                    flash('Destinatário não encontrado', 'error')
                    return redirect(url_for('nfe.edit', nfe_id=nfe_id))
                
                # Preparar dados para salvar
                json_nfe = {
                    'form_data': dados_nfe,
                    'items': itens,
                    'ambiente': 'homologacao'  # ou 'producao'
                }
                
                # Atualizar NFe no banco
                update_query = text("""
                    UPDATE nfe_emitidas 
                    SET cliente_id = :cliente_id,
                        natureza_operacao = :natureza_operacao,
                        tipo_nfe = :tipo_nfe,
                        finalidade_emissao = :finalidade_emissao,
                        informacoes_adicionais = :informacoes_adicionais,
                        destinatario_razao_social = :destinatario_razao_social,
                        destinatario_cnpj_cpf = :destinatario_cnpj_cpf,
                        json_nfe = :json_nfe,
                        status = :status,
                        mensagem_sefaz = :mensagem_sefaz
                    WHERE nfe_emitida_id = :nfe_id
                """)
                
                # Determinar novo status
                action = request.form.get('action', 'save')
                if action == 'save':
                    new_status = 'RASCUNHO'
                    mensagem = 'Rascunho atualizado'
                elif action == 'emit':
                    new_status = 'PROCESSANDO'
                    mensagem = 'Aguardando processamento na SEFAZ'
                else:
                    new_status = 'RASCUNHO'
                    mensagem = 'Rascunho atualizado'
                
                # ✅ CORREÇÃO: Acessar dados do destinatário por índice ou atributo
                try:
                    if hasattr(destinatario_result, '_asdict'):
                        dest_data = destinatario_result._asdict()
                        dest_razao = dest_data.get('razao_social', '')
                        dest_cnpj = dest_data.get('cnpj_cpf') or dest_data.get('cnpj', '')
                    else:
                        # Acessar por índice - assumindo ordem específica da query
                        dest_razao = destinatario_result[1] if len(destinatario_result) > 1 else ''
                        dest_cnpj = destinatario_result[2] if len(destinatario_result) > 2 else ''
                except Exception as e:
                    print(f"⚠️ Erro ao extrair dados do destinatário: {e}")
                    dest_razao = 'N/A'
                    dest_cnpj = 'N/A'
                
                db.execute(update_query, {
                    'nfe_id': nfe_id,
                    'cliente_id': cliente_id,
                    'natureza_operacao': dados_nfe['natOp'],
                    'tipo_nfe': dados_nfe['tpNF'],
                    'finalidade_emissao': int(dados_nfe['finNFe']),
                    'informacoes_adicionais': dados_nfe['infCpl'],
                    'destinatario_razao_social': dest_razao,
                    'destinatario_cnpj_cpf': dest_cnpj.replace('.','').replace('/','').replace('-',''),
                    'json_nfe': json.dumps(json_nfe),
                    'status': new_status,
                    'mensagem_sefaz': mensagem
                })
                db.commit()
                
                print(f"✅ NFe {nfe_id} atualizada - Status: {new_status}")
                
                # Se escolheu emitir, processar na SEFAZ
                if action == 'emit':
                    try:
                        print(f"🚀 Tentando emitir NFe {nfe_id}...")
                        
                        # Usar serviço NFeService para processar
                        from services.nfe_service import NFeService
                        nfe_service = NFeService(db)
                        
                        # Processar emissão usando o nfe_id existente
                        resultado = nfe_service.processar_nfe(dados_nfe, itens, int(cliente_id), nfe_id)
                        
                        if resultado.get('success', False):
                            flash('NF-e atualizada e emitida com sucesso!', 'success')
                        else:
                            flash(f'NF-e atualizada, mas erro na emissão: {resultado.get("message", "Erro desconhecido")}', 'warning')
                    
                    except Exception as e:
                        print(f"❌ Erro ao emitir NFe editada: {e}")
                        import traceback
                        traceback.print_exc()
                        flash(f'NF-e atualizada, mas erro na emissão: {str(e)}', 'danger')
                else:
                    flash('NF-e atualizada com sucesso!', 'success')
                
                return redirect(url_for('nfe.view', nfe_id=nfe_id))
                
            except Exception as e:
                print(f"❌ Erro ao atualizar NFe: {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erro ao atualizar NF-e: {str(e)}', 'error')
                return redirect(url_for('nfe.edit', nfe_id=nfe_id))
        
        # Fallback for any other HTTP method
        flash('Método HTTP não suportado', 'error')
        return redirect(url_for('nfe.list_nfes'))
        
    finally:
        if db is not None:
            db.close()

@nfe_bp.route('/download/<int:nfe_id>')
@login_required
@permission_required('nfe.read')
def download(nfe_id):
    """Download do XML da NFe"""
    flash('Funcionalidade de download em desenvolvimento.', 'info')
    return redirect(url_for('nfe.list_nfes'))

@nfe_bp.route('/reenviar/<int:nfe_id>', methods=['POST'])
@login_required
def reenviar_nfe(nfe_id):
    """Reenviar NFe rejeitada para a SEFAZ"""
    try:
        print(f"🔄 Tentando reenviar NFe ID: {nfe_id}")
        
        db = next(get_db())
        
        # Buscar NFe
        nfe_query = text("""
            SELECT ne.*, c.razao_social as cliente_nome 
            FROM nfe_emitidas ne
            JOIN clientes c ON ne.cliente_id = c.cliente_id
            WHERE ne.nfe_emitida_id = :nfe_id
        """)
        nfe_result = db.execute(nfe_query, {'nfe_id': nfe_id}).fetchone()
        
        if not nfe_result:
            return jsonify({
                'success': False,
                'message': 'NF-e não encontrada'
            }), 404
        
        nfe_data = dict(nfe_result)
        
        # Verificar se está rejeitada
        if nfe_data['status'].upper() not in ['REJEITADA', 'ERRO']:
            return jsonify({
                'success': False,
                'message': 'Apenas NF-es rejeitadas podem ser reenviadas'
            }), 400
        
        print(f"✅ NFe encontrada - Status: {nfe_data['status']}")
        
        # Verificar se tem dados JSON
        if not nfe_data['json_nfe']:
            return jsonify({
                'success': False,
                'message': 'Dados da NF-e não encontrados para reenvio'
            }), 400
        
        # Atualizar status para processando
        update_query = text("""
            UPDATE nfe_emitidas 
            SET status = 'PROCESSANDO',
                mensagem_sefaz = 'Reenviando para SEFAZ...'
            WHERE nfe_emitida_id = :nfe_id
        """)
        db.execute(update_query, {'nfe_id': nfe_id})
        db.commit()
        
        print(f"🔄 Status atualizado para PROCESSANDO")
        
        # Reenviar para SEFAZ
        from services.nfe_service import NFeService
        nfe_service = NFeService(db)
        
        # Extrair dados do JSON
        json_data = nfe_data['json_nfe']
        
        # Buscar dados do emitente
        emitente_data = db.query(Cliente).filter_by(cliente_id=nfe_data['cliente_id']).first()
        if not emitente_data:
            return jsonify({
                'success': False,
                'message': 'Dados do emitente não encontrados'
            }), 400
        
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
        # Buscar destinatário baseado nos dados do form_data
        
        form_data = json_data.get('form_data', {})
        destinatario_id = form_data.get('destinatario')
        destinatario_data: Dict[str, Any] = {}
        
        if destinatario_id:
            destinatario = db.query(DestinatarioNFe).filter_by(
                destinatario_id=destinatario_id,
                cliente_id=nfe_data['cliente_id']
            ).first()
            
            if destinatario:
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
        
        # ✅ CORREÇÃO: Verificar se destinatário foi encontrado
        if not destinatario_data:
            # Atualizar status de volta para rascunho
            update_back_query = text("""
                UPDATE nfe_emitidas 
                SET status = 'RASCUNHO',
                    mensagem_sefaz = 'Dados do destinatário não encontrados'
                WHERE nfe_emitida_id = :nfe_id
            """)
            db.execute(update_back_query, {'nfe_id': nfe_id})
            db.commit()
            
            return jsonify({
                'success': False,
                'message': 'Dados do destinatário não encontrados no rascunho'
            }), 400
           
        
        # Verificar se destinatário foi encontrado
        if not destinatario_data:
            return jsonify({
                'success': False,
                'message': 'Dados do destinatário não encontrados no rascunho'
            }), 400
        
        # Gerar XML
        ambiente = json_data.get('ambiente', 'homologacao')
        tp_amb = 2 if ambiente == 'homologacao' else 1
        
        xml_gerado = generate_nfe_xml(
            json_data.get('form_data', {}),
            emitente_data_for_template,
            destinatario_data,
            json_data.get('items', []),
            tp_amb,
            'emitir'
        )
        
        # Assinar XML
        from services.xml_signature_service import xml_signature_service
        xml_assinado = xml_signature_service.sign_nfe_xml(xml_gerado, db, nfe_data['cliente_id'])
        
        # Buscar certificado
        certificado = get_active_certificate_for_client(db, nfe_data['cliente_id'])
        if not certificado:
            return jsonify({
                'success': False,
                'message': 'Certificado não encontrado'
            }), 400
        
        # Enviar para SEFAZ
        resultado_sefaz = nfe_service._processar_envio_sefaz(xml_assinado, certificado, ambiente)
        
        # Preparar resultado
        resultado = {
            'success': resultado_sefaz.get('success', False),
            'message': resultado_sefaz.get('message', 'Erro no reenvio'),
            'protocolo': resultado_sefaz.get('protocolo'),
            'chave_acesso': resultado_sefaz.get('chave_acesso')
        }
        
        if resultado['success']:
            print(f"✅ NFe reenviada com sucesso")
            return jsonify({
                'success': True,
                'message': 'NF-e reenviada com sucesso!',
                'protocolo': resultado.get('protocolo'),
                'chave_acesso': resultado.get('chave_acesso')
            })
        else:
            print(f"❌ Erro no reenvio: {resultado.get('message')}")
            
            # Atualizar status para rejeitada novamente
            error_query = text("""
                UPDATE nfe_emitidas 
                SET status = 'REJEITADA',
                    mensagem_sefaz = :mensagem
                WHERE nfe_emitida_id = :nfe_id
            """)
            db.execute(error_query, {
                'nfe_id': nfe_id,
                'mensagem': resultado.get('message', 'Erro no reenvio')
            })
            db.commit()
            
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Erro ao reenviar NF-e')
            }), 400
        
    except Exception as e:
        print(f"❌ Erro no reenvio da NFe: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
@nfe_bp.route('/emitir-rascunho/<int:nfe_id>', methods=['POST'])
@login_required
def emitir_rascunho(nfe_id):
    """Emitir NFe que está em rascunho"""
    db = None
    try:
        print(f"📝 Emitindo rascunho NFe ID: {nfe_id}")
        
        db = next(get_db())
        db = next(get_db())
        
        # Buscar NFe
        nfe_query = text("""
            SELECT ne.*, c.razao_social as cliente_nome 
            FROM nfe_emitidas ne
            JOIN clientes c ON ne.cliente_id = c.cliente_id
            WHERE ne.nfe_emitida_id = :nfe_id
        """)
        nfe_result = db.execute(nfe_query, {'nfe_id': nfe_id}).fetchone()
        
        if not nfe_result:
            return jsonify({
                'success': False,
                'message': 'NF-e não encontrada'
            }), 404
        
        nfe_data = dict(nfe_result)
        
        # Verificar se está em rascunho
        if nfe_data['status'].upper() != 'RASCUNHO':
            return jsonify({
                'success': False,
                'message': 'Apenas rascunhos podem ser emitidos por esta função'
            }), 400
        
        print(f"✅ Rascunho encontrado")
        
        # Verificar se tem dados JSON
        if not nfe_data['json_nfe']:
            return jsonify({
                'success': False,
                'message': 'Dados do rascunho não encontrados'
            }), 400
        
        # Atualizar status para processando
        update_query = text("""
            UPDATE nfe_emitidas 
            SET status = 'PROCESSANDO',
                mensagem_sefaz = 'Processando na SEFAZ...'
            WHERE nfe_emitida_id = :nfe_id
        """)
        db.execute(update_query, {'nfe_id': nfe_id})
        db.commit()
        
        print(f"🔄 Status atualizado para PROCESSANDO")
        
        # Emitir na SEFAZ
        from services.nfe_service import NFeService
        nfe_service = NFeService(db)
        
        # Extrair dados do JSON
        json_data = nfe_data['json_nfe']
        
        # Buscar dados do emitente
        emitente_data = db.query(Cliente).filter_by(cliente_id=nfe_data['cliente_id']).first()
        if not emitente_data:
            return jsonify({
                'success': False,
                'message': 'Dados do emitente não encontrados'
            }), 400
        
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
        
        # Buscar destinatário para o rascunho
        form_data = json_data.get('form_data', {})
        destinatario_id = form_data.get('destinatario')
        destinatario_data = {}
        
        if destinatario_id:
            destinatario = db.query(DestinatarioNFe).filter_by(
                destinatario_id=destinatario_id,
                cliente_id=nfe_data['cliente_id']
            ).first()
            
            if destinatario:
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
        
        # Verificar se destinatário foi encontrado
        if not destinatario_data:
            return jsonify({
                'success': False,
                'message': 'Dados do destinatário não encontrados no rascunho'
            }), 400
        
        # ✅ CORREÇÃO: Gerar XML com dados válidos
        ambiente = json_data.get('ambiente', 'homologacao')
        tp_amb = 2 if ambiente == 'homologacao' else 1
        
        xml_gerado = generate_nfe_xml(
            json_data.get('form_data', {}),
            emitente_data_for_template,
            destinatario_data,  # ✅ AGORA É DICT VÁLIDO
            json_data.get('items', []),
            tp_amb,
            'emitir'
        )
        
        # Assinar XML
        from services.xml_signature_service import xml_signature_service
        xml_assinado = xml_signature_service.sign_nfe_xml(xml_gerado, db, nfe_data['cliente_id'])
        
        # Buscar certificado
        certificado = get_active_certificate_for_client(db, nfe_data['cliente_id'])
        if not certificado:
            return jsonify({
                'success': False,
                'message': 'Certificado não encontrado'
            }), 400
        
        # Enviar para SEFAZ
        resultado_sefaz = nfe_service._processar_envio_sefaz(xml_assinado, certificado, ambiente)
        
        # Preparar resultado
        resultado = {
            'success': resultado_sefaz.get('success', False),
            'message': resultado_sefaz.get('message', 'Erro no processamento'),
            'protocolo': resultado_sefaz.get('protocolo'),
            'chave_acesso': resultado_sefaz.get('chave_acesso')
        }
        
        # Atualizar status da NFe no banco
        if resultado['success']:
            status_nfe = 'AUTORIZADA'
            update_final_query = text("""
                UPDATE nfe_emitidas 
                SET status = :status,
                    chave_acesso = :chave_acesso,
                    protocolo_sefaz = :protocolo,
                    mensagem_sefaz = :mensagem,
                    data_autorizacao = :data_autorizacao,
                    json_nfe = :json_nfe
                WHERE nfe_emitida_id = :nfe_id
            """)
            
            # Atualizar JSON com dados da emissão
            json_data['xml_content'] = xml_assinado
            json_data['resultado_sefaz'] = resultado_sefaz
            
            db.execute(update_final_query, {
                'nfe_id': nfe_id,
                'status': status_nfe,
                'chave_acesso': resultado.get('chave_acesso'),
                'protocolo': resultado.get('protocolo'),
                'mensagem': resultado.get('message'),
                'data_autorizacao': datetime.fromisoformat(resultado_sefaz['data_autorizacao']) if resultado_sefaz.get('data_autorizacao') else datetime.now(),
                'json_nfe': json.dumps(json_data)
            })
            db.commit()
        else:
            status_nfe = 'REJEITADA'
            update_final_query = text("""
                UPDATE nfe_emitidas 
                SET status = :status,
                    mensagem_sefaz = :mensagem
                WHERE nfe_emitida_id = :nfe_id
            """)
            db.execute(update_final_query, {
                'nfe_id': nfe_id,
                'status': status_nfe,
                'mensagem': resultado.get('message', 'Erro no processamento')
            })
            db.commit()
        
        if resultado['success']:
            print(f"✅ Rascunho emitido com sucesso")
            return jsonify({
                'success': True,
                'message': 'NF-e emitida com sucesso!',
                'protocolo': resultado.get('protocolo'),
                'chave_acesso': resultado.get('chave_acesso')
            })
        else:
            print(f"❌ Erro na emissão: {resultado.get('message')}")
            
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Erro ao emitir NF-e')
            }), 400
        
    except Exception as e:
        print(f"❌ Erro na emissão do rascunho: {e}")
        import traceback
        traceback.print_exc()
        
        # Reverter status se houver erro
        if db is not None:
            try:
                error_query = text("""
                    UPDATE nfe_emitidas 
                    SET status = 'RASCUNHO',
                        mensagem_sefaz = :mensagem
                    WHERE nfe_emitida_id = :nfe_id
                """)
                db.execute(error_query, {
                    'nfe_id': nfe_id,
                    'mensagem': f'Erro na emissão: {str(e)}'
                })
                db.commit()
            except Exception:
                pass  # Ignore erro no rollback
        
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    finally:
        if db is not None:
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
                        'cliente_id': nfe_data['cliente_id'],
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
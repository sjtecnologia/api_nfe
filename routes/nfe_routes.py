import json
import os
from flask import Blueprint, jsonify, request, render_template, redirect, session, url_for, flash
from typing import Dict, Any
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import text, func
from datetime import datetime, timezone, timedelta
from database.connection import get_db
from database.models import Cliente, DestinatarioNFe, Produto, NFeEmitidas, Cfop, Csticms, Csosnicms, Ncm, RegimeTributario, NFeInutilizacao
from database.models import UserModel, UserClient
from auth.decorators import (
    admin_required,
    block_viewer_access,
    editor_or_admin_required,
    viewer_or_higher_required
)
from auth.permissions import get_accessible_client_ids
from services.certificate_service import get_active_certificate_for_client
from services.nfe_service import NFeService, generate_nfe_xml, sign_xml, send_to_sefaz, validar_tributacao_nfe
from utils.helpers import produto_to_dict_for_template, get_uf_ibge_code
from utils.nfe_validators import validar_cpf, validar_cnpj
from utils.nfe_validators import validar_dados_nfe, validar_xml_nfe
from config.settings import SEFAZ_AMBIENTE_HOMOLOGACAO

nfe_bp = Blueprint('nfe', __name__)

# ALIAS PARA COMPATIBILIDADE
@nfe_bp.route('/create', methods=['GET', 'POST'])
@login_required
@editor_or_admin_required()
def create():
    """Alias para emitir_nfe - para compatibilidade com templates"""
    return emitir_nfe()

@nfe_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@editor_or_admin_required()
def emitir_nfe():
    db = next(get_db())
    
    try:
        # OK: BUSCAR CLIENTES ACESSÍVEIS PRIMEIRO
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # OK: DETERMINAR CLIENTE
        emitente_cliente_id = None
        
        # 1. Tentar pegar cliente_id da URL
        cliente_id_from_url = request.args.get('cliente_id')
        if cliente_id_from_url:
            try:
                emitente_cliente_id = int(cliente_id_from_url)
                print(f" Cliente ID da URL: {emitente_cliente_id}")
                
                # Verificar se usuário tem acesso a este cliente
                if emitente_cliente_id not in accessible_clients:
                    flash('Você não tem acesso a este cliente.', 'danger')
                    return redirect(url_for('home.home'))
            except ValueError:
                flash('ID do cliente inválido', 'danger')
                return redirect(url_for('home.home'))
        
        # 2. Se não tem cliente_id na URL, tentar usar cliente ativo da sessão
        elif session.get('current_client_id'):
            emitente_cliente_id = session.get('current_client_id')
            print(f" Usando cliente ativo da sessão: {emitente_cliente_id}")
            
            # Verificar se usuário tem acesso a este cliente
            if emitente_cliente_id not in accessible_clients:
                emitente_cliente_id = accessible_clients[0]
                print(f" Cliente da sessão sem acesso, usando primeiro disponível: {emitente_cliente_id}")
        
        # 3. Se não tem na URL nem na sessão, usar primeiro disponível
        else:
            emitente_cliente_id = accessible_clients[0]
            print(f" Usando primeiro cliente disponível: {emitente_cliente_id}")
        
        # 3. Buscar dados do cliente
        emitente_data = db.query(Cliente).filter_by(cliente_id=emitente_cliente_id).first()
        if not emitente_data:
            flash('Cliente não encontrado', 'danger')
            return redirect(url_for('home.home'))
        
        print(f"OK: Emitente encontrado: {emitente_data.razao_social}")
        
        # VALIDAR CNPJ DO EMITENTE
        cnpj_emitente_limpo = emitente_data.cnpj.replace('.', '').replace('/', '').replace('-', '').strip()
        print(f"🔍 [VALIDAÇÃO] CNPJ emitente: {cnpj_emitente_limpo}")
        if not validar_cnpj(cnpj_emitente_limpo):
            print(f"❌ [VALIDAÇÃO] CNPJ EMITENTE INVÁLIDO: {cnpj_emitente_limpo}")
            flash(f'CNPJ do emitente é inválido: {emitente_data.cnpj}. Corrija o cadastro do cliente antes de emitir NFe.', 'danger')
            return redirect(url_for('home.home'))
        print(f"✅ [VALIDAÇÃO] CNPJ emitente válido")
        
        # Buscar regime tributário
        regime_tributario_nome = 'Regime Normal'
        if emitente_data.regime_tributario_id is not None:
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
            'inscricao_estadual': emitente_data.inscricao_estadual,
            'regime_tributario_id': emitente_data.regime_tributario_id,  # [?] CRÍTICO para buscar regras tributárias
            'ambiente': emitente_data.ambiente  # Campo ambiente (1=Produção, 2=Homologação - padrão SEFAZ)
        }
        
        if request.method == 'POST':
            print(" === INICIANDO PROCESSAMENTO POST ===")
            
            # CAPTURAR DADOS DO FORMULÁRIO
            form_data_initial = {
                'tpNF': request.form.get('tpNF', '1'),
                'finNFe': request.form.get('finNFe', '1'),
                'dataEmissao': request.form.get('dataEmissao'),
                'serie': request.form.get('serie', '1'),
                'numero_nfe': request.form.get('numero_nfe', '1'),  # [*] Capturar número da NFe da tela
                'natOp': request.form.get('natOp'),
                'infCpl': request.form.get('infCpl', ''),
                'formaPagamento': request.form.get('formaPagamento'),
                'valorPagamento': request.form.get('valorPagamento'),
                'modFrete': request.form.get('modFrete', '9'),
                'vFrete': request.form.get('vFrete', '0.00'),
                'vSeg': request.form.get('vSeg', '0.00'),
                'vDesc': request.form.get('vDesc', '0.00'),
                # Dados da Transportadora
                'transportadoraNome': request.form.get('transportadoraNome', ''),
                'transportadoraCnpjCpf': request.form.get('transportadoraCnpjCpf', ''),
                'transportadoraIE': request.form.get('transportadoraIE', ''),
                'transportadoraEndereco': request.form.get('transportadoraEndereco', ''),
                'transportadoraMunicipio': request.form.get('transportadoraMunicipio', ''),
                'transportadoraUF': request.form.get('transportadoraUF', ''),
                # Dados do Veículo
                'veiculoPlaca': request.form.get('veiculoPlaca', ''),
                'veiculoUF': request.form.get('veiculoUF', ''),
                # ANTT da transportadora
                'transportadoraANTT': request.form.get('transportadoraANTT', ''),
                # Dados dos Volumes
                'volumeQuantidade': request.form.get('volumeQuantidade', ''),
                'volumeEspecie': request.form.get('volumeEspecie', ''),
                'volumeMarca': request.form.get('volumeMarca', ''),
                'volumeNumeracao': request.form.get('volumeNumeracao', ''),
                'volumePesoBruto': request.form.get('volumePesoBruto', ''),
                'volumePesoLiquido': request.form.get('volumePesoLiquido', '')
            }
            
            print(f" Form data: {form_data_initial}")
            print(f" Dados transporte - Modalidade: {form_data_initial['modFrete']}, Transportadora: {form_data_initial['transportadoraNome']}")
            
            # PROCESSAR AÇÃO BASEADA NO BOTÃO CLICADO
            action = request.form.get('action')
            preview_only = request.form.get('preview_only') == 'true'
            preview_danfe = request.form.get('preview_danfe') == 'true'
            
            # Usar ambiente do cliente (1=Produção, 2=Homologação - padrão SEFAZ)
            tp_amb = emitente_data.ambiente
            ambiente = 'producao' if tp_amb == 1 else 'homologacao'
            
            print(f" DEBUG - Ação recebida: {action}, Preview: {preview_only}, Preview DANFE: {preview_danfe}, Ambiente: {ambiente} (tpAmb={tp_amb})")
            
            # OK: INICIALIZAR VARIÁVEIS OBRIGATÓRIAS
            destinatario_data = {}
            nfe_items = []
            
            # MODO PREVIEW: Gerar apenas o XML sem assinar ou enviar
            if preview_only:
                print(" === MODO PREVIEW XML ===")
                try:
                    # BUSCAR DESTINATÁRIO
                    destinatario_id = request.form.get('destinatario')
                    if not destinatario_id:
                        return jsonify({'success': False, 'message': 'Destinatário é obrigatório'}), 400
                    
                    destinatario = db.query(DestinatarioNFe).filter_by(
                        destinatario_id=destinatario_id,
                        cliente_id=emitente_cliente_id
                    ).first()
                    
                    if not destinatario:
                        return jsonify({'success': False, 'message': 'Destinatário não encontrado'}), 404
                    
                    destinatario_data = {
                        'nome_razao_social': destinatario.nome_razao_social,
                        'cpf_cnpj': destinatario.cpf_cnpj,
                        'inscricao_estadual': destinatario.ie,
                        'logradouro': destinatario.logradouro,
                        'numero': destinatario.numero,
                        'bairro': destinatario.bairro,
                        'cep': destinatario.cep,
                        'codigo_municipio': destinatario.codigo_municipio,
                        'nome_municipio': destinatario.nome_municipio,
                        'uf': destinatario.uf
                    }
                    
                    # PROCESSAR ITENS
                    item_index = 0
                    while f'items[{item_index}][json]' in request.form:
                        item_json = request.form[f'items[{item_index}][json]']
                        if item_json:
                            item_data = json.loads(item_json)
                            nfe_items.append(item_data)
                        item_index += 1
                    
                    if not nfe_items:
                        return jsonify({'success': False, 'message': 'Adicione pelo menos um item'}), 400
                    
                    # GERAR XML (sem assinatura) - tpAmb já vem correto do banco
                    xml_nfe = generate_nfe_xml(
                        form_data_initial,
                        emitente_data_for_template,
                        destinatario_data,
                        nfe_items,
                        tp_amb,
                        'preview'
                    )
                    
                    print(f"OK: XML preview gerado: {len(xml_nfe)} caracteres")
                    return jsonify({
                        'success': True,
                        'xml_preview': xml_nfe,
                        'message': 'XML gerado com sucesso (preview)'
                    })
                    
                except ValueError as ve:
                    # Erros de validação tributária
                    erro_msg = str(ve)
                    print(f"ERRO DE VALIDAÇÃO: {erro_msg}")
                    return jsonify({'success': False, 'message': erro_msg}), 400
                except Exception as e:
                    print(f"ERRO: Erro no preview: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({'success': False, 'message': f'Erro ao gerar preview: {str(e)}'}), 500
            
            # MODO PREVIEW DANFE: Gerar XML e DANFE em PDF sem salvar no banco
            if preview_danfe:
                print(" === MODO PREVIEW DANFE ===")
                try:
                    # BUSCAR DESTINATÁRIO
                    destinatario_id = request.form.get('destinatario')
                    if not destinatario_id:
                        return jsonify({'success': False, 'message': 'Destinatário é obrigatório'}), 400
                    
                    destinatario = db.query(DestinatarioNFe).filter_by(
                        destinatario_id=destinatario_id,
                        cliente_id=emitente_cliente_id
                    ).first()
                    
                    if not destinatario:
                        return jsonify({'success': False, 'message': 'Destinatário não encontrado'}), 404
                    
                    destinatario_data = {
                        'nome_razao_social': destinatario.nome_razao_social,
                        'cpf_cnpj': destinatario.cpf_cnpj,
                        'inscricao_estadual': destinatario.ie,
                        'logradouro': destinatario.logradouro,
                        'numero': destinatario.numero,
                        'bairro': destinatario.bairro,
                        'cep': destinatario.cep,
                        'codigo_municipio': destinatario.codigo_municipio,
                        'nome_municipio': destinatario.nome_municipio,
                        'uf': destinatario.uf
                    }
                    
                    # PROCESSAR ITENS
                    item_index = 0
                    while f'items[{item_index}][json]' in request.form:
                        item_json = request.form[f'items[{item_index}][json]']
                        if item_json:
                            item_data = json.loads(item_json)
                            nfe_items.append(item_data)
                        item_index += 1
                    
                    if not nfe_items:
                        return jsonify({'success': False, 'message': 'Adicione pelo menos um item'}), 400
                    
                    # GERAR XML (sem assinatura)
                    xml_nfe = generate_nfe_xml(
                        form_data_initial,
                        emitente_data_for_template,
                        destinatario_data,
                        nfe_items,
                        tp_amb,
                        'preview'
                    )
                    
                    # GERAR DANFE em PDF usando o serviço existente
                    from services.danfe_service import generate_danfe
                    
                    # Gerar DANFE usando ID temporário (não será salvo no banco)
                    # O generate_danfe retorna o caminho do arquivo PDF gerado
                    pdf_path = generate_danfe(xml_nfe, 'preview', emitente_cliente_id)
                    
                    # Ler o PDF e converter para bytes
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    
                    # Limpar arquivo temporário
                    try:
                        os.remove(pdf_path)
                    except:
                        pass
                    
                    # Retornar PDF como base64 para exibir no frontend
                    import base64
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    
                    print(f"✅ DANFE preview gerado: {len(pdf_bytes)} bytes")
                    return jsonify({
                        'success': True,
                        'pdf_base64': pdf_base64,
                        'message': 'DANFE preview gerado com sucesso'
                    })
                    
                except ValueError as ve:
                    erro_msg = str(ve)
                    print(f"❌ ERRO DE VALIDAÇÃO: {erro_msg}")
                    return jsonify({'success': False, 'message': erro_msg}), 400
                except Exception as e:
                    print(f"❌ ERRO: Erro no preview DANFE: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({'success': False, 'message': f'Erro ao gerar DANFE preview: {str(e)}'}), 500
            
            if action == 'emitir':
                print(" === PROCESSANDO EMISSÃO ===")
                try:
                    # OK: BUSCAR DESTINATÁRIO SELECIONADO
                    destinatario_id = request.form.get('destinatario')
                    print(f" Destinatário ID: {destinatario_id}")
                    
                    if not destinatario_id:
                        print("ERRO: Destinatário não selecionado")
                        flash('Destinatário é obrigatório para emitir NFe', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    destinatario = db.query(DestinatarioNFe).filter_by(
                        destinatario_id=destinatario_id,
                        cliente_id=emitente_cliente_id
                    ).first()
                    
                    if not destinatario:
                        print("ERRO: Destinatário não encontrado no banco")
                        flash('Destinatário não encontrado', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    print(f"OK: Destinatário encontrado: {destinatario.nome_razao_social}")
                    
                    # VALIDAR CPF/CNPJ DO DESTINATÁRIO
                    cpf_cnpj_limpo = destinatario.cpf_cnpj.replace('.', '').replace('/', '').replace('-', '').strip()
                    print(f"🔍 [VALIDAÇÃO] CPF/CNPJ destinatário: {cpf_cnpj_limpo}")
                    
                    if len(cpf_cnpj_limpo) == 11:  # CPF
                        if not validar_cpf(cpf_cnpj_limpo):
                            print(f"❌ [VALIDAÇÃO] CPF INVÁLIDO: {cpf_cnpj_limpo}")
                            flash(f'CPF do destinatário é inválido: {destinatario.cpf_cnpj}. Corrija o cadastro antes de emitir a NFe.', 'danger')
                            return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        print(f"✅ [VALIDAÇÃO] CPF válido")
                    elif len(cpf_cnpj_limpo) == 14:  # CNPJ
                        if not validar_cnpj(cpf_cnpj_limpo):
                            print(f"❌ [VALIDAÇÃO] CNPJ INVÁLIDO: {cpf_cnpj_limpo}")
                            flash(f'CNPJ do destinatário é inválido: {destinatario.cpf_cnpj}. Corrija o cadastro antes de emitir a NFe.', 'danger')
                            return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        print(f"✅ [VALIDAÇÃO] CNPJ válido")
                    else:
                        print(f"❌ [VALIDAÇÃO] CPF/CNPJ com tamanho inválido: {len(cpf_cnpj_limpo)} dígitos")
                        flash(f'CPF/CNPJ do destinatário tem formato inválido: {destinatario.cpf_cnpj}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # OK: CONVERTER DESTINATÁRIO PARA DICIONÁRIO
                    destinatario_data = {
                        'nome_razao_social': destinatario.nome_razao_social,
                        'cpf_cnpj': destinatario.cpf_cnpj,
                        'inscricao_estadual': destinatario.ie,
                        'logradouro': destinatario.logradouro,
                        'numero': destinatario.numero,
                        'bairro': destinatario.bairro,
                        'cep': destinatario.cep,
                        'codigo_municipio': destinatario.codigo_municipio,
                        'nome_municipio': destinatario.nome_municipio,
                        'uf': destinatario.uf
                    }
                    
                    print(f" Destinatário data: {destinatario_data}")
                    print(f"🔍 [DEBUG] IE do destinatário: {destinatario.ie}")
                    
                    # OK: PROCESSAR ITENS DA NFE
                    print(" === PROCESSANDO ITENS ===")
                    item_index = 0
                    
                    while f'items[{item_index}][json]' in request.form:
                        item_json = request.form[f'items[{item_index}][json]']
                        print(f" Item {item_index} JSON: {item_json[:100]}...")
                        
                        if item_json:
                            try:
                                item_data = json.loads(item_json)
                                nfe_items.append(item_data)
                                print(f" Item {item_index + 1}: {item_data.get('descricao', 'Sem descrição')}")
                            except json.JSONDecodeError as e:
                                print(f"ERRO: Erro JSON no item {item_index}: {e}")
                                flash(f'Erro no formato do item {item_index + 1}: {str(e)}', 'danger')
                                return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        item_index += 1
                    
                    if not nfe_items:
                        print("ERRO: Nenhum item encontrado")
                        flash('Adicione pelo menos um item à NFe', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    print(f" Processando {len(nfe_items)} itens")
                    
                    # OK: VALIDAR DADOS ANTES DE PROCESSAR
                    print(" === VALIDANDO DADOS ===")
                    
                    # Verificar se destinatario_data foi preenchido
                    if not destinatario_data:
                        print("ERRO: Dados do destinatário não foram processados")
                        flash('Erro: dados do destinatário não encontrados', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    erros_validacao = validar_dados_nfe(form_data_initial, emitente_data_for_template, destinatario_data, nfe_items)
                    
                    if erros_validacao:
                        print(f"ERRO: Erros de validação: {erros_validacao}")
                        for erro in erros_validacao:
                            flash(f"ERRO: {erro}", 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    print("OK: Validação passou")
                    
                    # VALIDAR TRIBUTAÇÃO DOS ITENS
                    print(" === VALIDANDO TRIBUTAÇÃO ===")
                    sucesso_trib, erros_tributacao = validar_tributacao_nfe(emitente_data_for_template, nfe_items)
                    if not sucesso_trib:
                        print(f"❌ [VALIDAÇÃO TRIBUTÁRIA] {len(erros_tributacao)} erro(s) encontrado(s)")
                        for erro in erros_tributacao:
                            print(f"  • {erro}")
                        flash('Erros de tributação encontrados:\n' + '\n'.join(erros_tributacao), 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    print("✅ [VALIDAÇÃO TRIBUTÁRIA] Tributação válida")
                    
                    # PROCESSAR EMISSÃO DA NFE
                    # tpAmb já vem correto do banco (1=Produção, 2=Homologação - padrão SEFAZ)
                    print(f"→ Ambiente SEFAZ: tpAmb={tp_amb} ({ambiente})")
                    print(" === GERANDO XML ===")
                    try:
                        xml_nfe = generate_nfe_xml(
                            form_data_initial, 
                            emitente_data_for_template, 
                            destinatario_data, 
                            nfe_items, 
                            tp_amb, 
                            'emitir'
                        )
                        print(f"OK: XML gerado: {len(xml_nfe)} caracteres")
                        print(f" XML preview: {xml_nfe[:200]}...")
                    except ValueError as ve:
                        # Erros de validação tributária
                        erro_msg = str(ve)
                        print(f"ERRO DE VALIDAÇÃO: {erro_msg}")
                        
                        # Dividir mensagem em linhas para flash individual
                        if "ERROS DE TRIBUTAÇÃO" in erro_msg:
                            # Remover o cabeçalho
                            erros_linhas = erro_msg.replace("❌ ERROS DE TRIBUTAÇÃO ENCONTRADOS:", "").strip().split("\n\n")
                            flash('❌ ERROS DE TRIBUTAÇÃO - Corrija no cadastro de produtos:', 'danger')
                            for erro_linha in erros_linhas:
                                if erro_linha.strip():
                                    flash(erro_linha.strip(), 'warning')
                        else:
                            flash(f'Erro de validação: {erro_msg}', 'danger')
                        
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    except Exception as e:
                        print(f"ERRO: ERRO ao gerar XML: {e}")
                        import traceback
                        traceback.print_exc()
                        flash(f'Erro ao gerar XML: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # OK: VALIDAR XML GERADO
                    print(" === VALIDANDO XML ===")
                    try:
                        xml_valido, erros_xml = validar_xml_nfe(xml_nfe)
                        if not xml_valido:
                            print(f"ERRO: XML inválido: {erros_xml}")
                            for erro in erros_xml:
                                flash(f"ERRO: XML: {erro}", 'danger')
                            return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        print("OK: XML válido")
                    except Exception as e:
                        print(f"ERRO: ERRO na validação XML: {e}")
                        flash(f'Erro na validação do XML: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # 2. BUSCAR CERTIFICADO ATIVO
                    print(" === BUSCANDO CERTIFICADO ===")
                    try:
                        certificado = get_active_certificate_for_client(db, emitente_cliente_id)
                        
                        if not certificado:
                            print("ERRO: Certificado não encontrado")
                            flash('Nenhum certificado digital ativo encontrado. Cadastre um certificado válido.', 'danger')
                            return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        
                        print(f"OK: Certificado encontrado: {certificado.get('common_name', 'N/A')}")
                    except Exception as e:
                        print(f"ERRO: ERRO ao buscar certificado: {e}")
                        flash(f'Erro ao buscar certificado: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                   # 3. ASSINAR XML
                    print("️ === ASSINANDO XML ===")
                    try:
                        from services.xml_signature_service import xml_signature_service
                        xml_assinado = xml_signature_service.sign_nfe_xml(xml_nfe, db, emitente_cliente_id)  # OK: CORRIGIDO
                        print(f"OK: XML assinado: {len(xml_assinado)} caracteres")
                    except Exception as e:
                        print(f"ERRO: Erro na assinatura: {e}")
                        flash(f'Erro na assinatura do XML: {e}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))  # OK: CORRIGIDO
                    
                    # 3.5. VALIDAÇÃO FINAL COM IA (OPCIONAL - NÃO BLOQUEIA)
                    print("🤖 === VALIDAÇÃO FINAL COM IA ===")
                    try:
                        import requests
                        validacao_ia = requests.post(
                            "http://localhost:8081/valida/xml",
                            json={
                                "xml_content": xml_assinado,
                                "ambiente": ambiente
                            },
                            timeout=20
                        )
                        
                        if validacao_ia.status_code == 200:
                            resultado_ia = validacao_ia.json()
                            
                            if not resultado_ia.get("valido", True):
                                erros_ia = resultado_ia.get("erros", [])
                                print(f"⚠️  IA detectou {len(erros_ia)} problema(s):")
                                for erro in erros_ia:
                                    print(f"  • {erro.get('campo', '?')}: {erro.get('erro', '')}")
                                    flash(f"⚠️ Alerta IA: {erro.get('campo', '?')} - {erro.get('erro', '')}", 'warning')
                            
                            avisos_ia = resultado_ia.get("avisos", [])
                            if avisos_ia:
                                print(f"💡 {len(avisos_ia)} aviso(s) da IA")
                                for aviso in avisos_ia:
                                    print(f"  • {aviso}")
                            
                            score = resultado_ia.get("score_confianca", 0)
                            if score > 0:
                                print(f"✅ Score de confiança IA: {score}/100")
                        else:
                            print(f"⚠️  Validação IA não disponível (HTTP {validacao_ia.status_code})")
                    except requests.exceptions.Timeout:
                        print("⏱️  Timeout validação IA (continuando)")
                    except Exception as e:
                        print(f"⚠️  Erro validação IA: {e} (continuando)")
                    
                    # 4. ENVIAR PARA SEFAZ
                    print(f" === ENVIANDO PARA SEFAZ ===")
                    try:
                        nfe_service = NFeService(db)
                        resultado_sefaz = nfe_service._processar_envio_sefaz(
                            xml_assinado,
                            certificado,
                            ambiente,
                            emitente_cliente_id
                        )
                        print(f" Resultado SEFAZ: {resultado_sefaz}")
                    except Exception as e:
                        print(f"ERRO: ERRO ao enviar para SEFAZ: {e}")
                        import traceback
                        traceback.print_exc()
                        flash(f'Erro ao enviar para SEFAZ: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # 5. SALVAR NO BANCO
                    print(" === SALVANDO NO BANCO ===")
                    try:
                        # CORREÇÃO: Usar o status retornado pelo serviço em vez de verificar apenas o código
                        status_nfe = resultado_sefaz.get('status', 'REJEITADA') if resultado_sefaz.get('success', False) else 'REJEITADA'
                        print(f" Status NFe: {status_nfe}")
                        
                        # Extrair data de autorização do resultado SEFAZ
                        data_autorizacao_nfe = None
                        if resultado_sefaz.get('data_autorizacao'):
                            try:
                                data_autorizacao_nfe = datetime.fromisoformat(resultado_sefaz['data_autorizacao'])
                            except:
                                data_autorizacao_nfe = datetime.now() if status_nfe == 'AUTORIZADA' else None
                        elif status_nfe == 'AUTORIZADA':
                            data_autorizacao_nfe = datetime.now()
                        
                        # Calcular valor total
                        valor_total_nfe = sum(float(item.get('valor_total', 0)) for item in nfe_items)
                        
                        # Preparar data de emissão
                        # O formulário HTML envia datetime local (BRT), precisamos converter para timezone aware
                        data_emissao_nfe = None
                        if form_data_initial.get('dataEmissao'):
                            try:
                                # Parse da string ISO (ex: "2026-01-26T09:36")
                                dt_str = form_data_initial['dataEmissao'].replace('T', ' ')
                                print(f"📅 [DEBUG] dataEmissao do formulário: '{form_data_initial.get('dataEmissao')}'")
                                data_emissao_naive = datetime.fromisoformat(dt_str)
                                print(f"📅 [DEBUG] datetime naive parseado: {data_emissao_naive}")
                                
                                # Adicionar timezone de Brasília (BRT = UTC-3)
                                brasilia_tz = timezone(timedelta(hours=-3))
                                data_emissao_nfe = data_emissao_naive.replace(tzinfo=brasilia_tz)
                                print(f"📅 [DEBUG] datetime com timezone BRT: {data_emissao_nfe}")
                                print(f"📅 [DEBUG] ISO format: {data_emissao_nfe.isoformat()}")
                            except Exception as e:
                                print(f"⚠️  [DEBUG] Erro ao parsear data: {e}")
                                # Fallback: usar horário atual em BRT
                                brasilia_tz = timezone(timedelta(hours=-3))
                                data_emissao_nfe = datetime.now(brasilia_tz)
                                print(f"📅 [DEBUG] Usando fallback: {data_emissao_nfe.isoformat()}")
                        else:
                            # Usar horário atual em BRT
                            brasilia_tz = timezone(timedelta(hours=-3))
                            data_emissao_nfe = datetime.now(brasilia_tz)
                            print(f"📅 [DEBUG] Sem dataEmissao, usando now(): {data_emissao_nfe.isoformat()}")
                        
                        nova_nfe = NFeEmitidas(
                            cliente_id=emitente_cliente_id,
                            numero=int(form_data_initial.get('numero_nfe', '1')),
                            serie=int(form_data_initial.get('serie', '1')),
                            data_emissao=data_emissao_nfe,
                            valor_total=valor_total_nfe,
                            tipo_nfe=form_data_initial.get('tpNF', '1'),
                            modelo='55',  # 55=NFe, 65=NFCe
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
                            data_autorizacao=data_autorizacao_nfe,
                            created_by_user_id=current_user.id,
                            informacoes_adicionais=form_data_initial.get('infCpl')
                        )
                        
                        db.add(nova_nfe)
                        db.commit()
                        print(f"💾 [DEBUG] NFe salva no banco - data_emissao: {nova_nfe.data_emissao}")
                        
                        # OK: CORREÇÃO: Refresh para obter o ID real após commit
                        db.refresh(nova_nfe)
                        # OK: CORREÇÃO: Acessar o valor do ID corretamente
                        nfe_id_raw = getattr(nova_nfe, 'nfe_emitida_id')
                        print(f"💾 [DEBUG] Após refresh - data_emissao: {nova_nfe.data_emissao}")
                        
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
                        print(f"OK: NFe salva no banco com ID: {nfe_id}")
                        
                    except Exception as e:
                        print(f"ERRO: ERRO ao salvar no banco: {e}")
                        db.rollback()
                        import traceback
                        traceback.print_exc()
                        flash(f'Erro ao salvar NFe no banco: {str(e)}', 'danger')
                        return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                    
                    # 6. FEEDBACK PARA O USUÁRIO
                    print(" === FINALIZANDO ===")
                    danfe_gerado_com_sucesso = False
                    caminho_danfe = None
                    
                    if status_nfe == 'AUTORIZADA':
                        msg = f'OK: NFe emitida com sucesso em {ambiente}! Protocolo: {resultado_sefaz.get("protocolo")}'
                        print(msg)
                        flash(msg, 'success')
                        
                        # Gerar DANFE automaticamente sempre que NFe for autorizada
                        try:
                            print(" === GERANDO DANFE AUTOMATICAMENTE ===")
                            from services.danfe_service import generate_danfe
                            # OK: CORREÇÃO: Usar a variável nfe_id que já foi convertida para int
                            pdf_path = generate_danfe(xml_assinado, nfe_id, emitente_cliente_id)
                            
                            if pdf_path and os.path.exists(pdf_path):
                                print(f"OK: DANFE gerado: {pdf_path}")
                                # Adicionar URL do DANFE à sessão (opcional - para uso futuro)
                                pdf_url = url_for('static', filename=f'danfe/danfe_{nfe_id}.pdf')
                                if 'danfes_gerados' not in session:
                                    session['danfes_gerados'] = {}
                                # CORREÇÃO: Converter nfe_id para string para evitar erro de serialização JSON
                                session['danfes_gerados'][str(nfe_id)] = {
                                    'url': pdf_url,
                                    'timestamp': datetime.now().timestamp()
                                }
                                session.modified = True
                                flash('DANFE gerado com sucesso!', 'success')
                                
                                # Marcar que DANFE foi gerado para abrir o modal
                                danfe_gerado_com_sucesso = True
                                caminho_danfe = f'static/danfe/danfe_{nfe_id}.pdf'
                                
                                # === ENVIAR EMAIL AUTOMATICAMENTE PARA O DESTINATÁRIO ===
                                try:
                                    print(" === ENVIANDO EMAIL AUTOMÁTICO PARA DESTINATÁRIO ===")
                                    from services.email_service import enviar_nfe_automaticamente
                                    
                                    resultado_email = enviar_nfe_automaticamente(nfe_id, db)
                                    
                                    if resultado_email.get('success'):
                                        print(f"✅ Email automático enviado com sucesso!")
                                        flash('Email com NFe enviado automaticamente para o destinatário!', 'success')
                                    else:
                                        msg_erro = resultado_email.get('message', 'Erro desconhecido')
                                        print(f"⚠️  Email automático não enviado: {msg_erro}")
                                        # Não mostrar erro crítico ao usuário, apenas avisar no log
                                        if 'sem email' not in msg_erro.lower():
                                            flash(f'Aviso: Não foi possível enviar email automático - {msg_erro}', 'warning')
                                        
                                except Exception as email_error:
                                    print(f"❌ Erro ao enviar email automático: {str(email_error)}")
                                    import traceback
                                    traceback.print_exc()
                                    # Não bloquear a emissão da NFe por causa do email
                                    flash('NFe emitida com sucesso, mas houve erro no envio automático do email.', 'warning')
                            else:
                                print(f"AVISO: DANFE não foi gerado (pdf_path: {pdf_path})")
                                flash('NFe emitida, mas o DANFE não foi gerado.', 'warning')
                        except Exception as e:
                            print(f"ERRO: Erro ao gerar DANFE automático: {e}")
                            import traceback
                            traceback.print_exc()
                            # Não falhar a emissão por causa do DANFE
                            flash(f'NFe emitida com sucesso! DANFE: {str(e)}', 'warning')
                    else:
                        msg = f'ERRO: NFe rejeitada: {resultado_sefaz.get("message")}'
                        print(msg)
                        flash(msg, 'danger')
                    
                    # Commit da sessão antes do redirect
                    try:
                        db.commit()
                    except:
                        pass  # Já foi commitado antes
                    
                    print(" Redirecionando para lista de NFes...")
                    try:
                        # Se DANFE foi gerado, adicionar parâmetros para abrir modal
                        if danfe_gerado_com_sucesso:
                            # Converter cliente_id para int e garantir que nfe_id também é int
                            return redirect(url_for('nfe.list_nfes', 
                                                   cliente_id=int(emitente_cliente_id),
                                                   danfe_gerado='true',
                                                   nfe_id=int(nfe_id),
                                                   danfe_path=caminho_danfe.replace('\\', '/')))
                        else:
                            return redirect(url_for('nfe.list_nfes', cliente_id=int(emitente_cliente_id)))
                    except Exception as redirect_error:
                        print(f"ERRO no redirect: {redirect_error}")
                        import traceback
                        traceback.print_exc()
                        # Fallback: redirecionar para home
                        return redirect(url_for('home.home'))
                    
                except Exception as e:
                    db.rollback()
                    print(f"ERRO: ERRO GERAL na emissão: {e}")
                    import traceback
                    traceback.print_exc()
                    flash(f'Erro ao emitir NFe: {str(e)}', 'danger')
                    return redirect(url_for('nfe.emitir_nfe', cliente_id=emitente_cliente_id))
                        
            elif action == 'rascunho':
                print("NOTA: === SALVANDO RASCUNHO ===")
                # OK: SALVAR COMO RASCUNHO (SEM VALIDAÇÕES RIGOROSAS)
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
                    
                    print("OK: Rascunho salvo")
                    flash(' NFe salva como rascunho!', 'success')
                    return redirect(url_for('nfe.list_nfes', cliente_id=emitente_cliente_id))
                    
                except Exception as e:
                    db.rollback()
                    print(f"ERRO: ERRO ao salvar rascunho: {e}")
                    flash(f'Erro ao salvar rascunho: {str(e)}', 'danger')
        
        # MÉTODO GET - CARREGAR DADOS PARA O FORMULÁRIO
        print(" === CARREGANDO FORMULÁRIO (GET) ===")
        
        # BUSCAR Destinatários/Tomadores
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
            ncm_id_value = getattr(prod, 'ncm_id', None)
            if ncm_id_value is not None:
                ncm_obj = db.query(Ncm).filter_by(ncm_id=ncm_id_value).first()
                if ncm_obj:
                    ncm_codigo = ncm_obj.codigo
            
            cfop_codigo = None
            cfop_id_value = getattr(prod, 'cfop_id', None)
            if cfop_id_value is not None:
                cfop_obj = db.query(Cfop).filter_by(cfop_id=cfop_id_value).first()
                if cfop_obj:
                    cfop_codigo = cfop_obj.cfop
            
            cst_codigo = None
            cst_id_value = getattr(prod, 'cst_id', None)
            if cst_id_value is not None:
                cst_obj = db.query(Csticms).filter_by(cst_id=cst_id_value).first()
                if cst_obj:
                    cst_codigo = cst_obj.codigo
            
            csosn_codigo = None
            csosn_id_value = getattr(prod, 'csosn_id', None)
            if csosn_id_value is not None:
                csosn_obj = db.query(Csosnicms).filter_by(csosn_id=csosn_id_value).first()
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

        # OK: BUSCAR CSTs E CSOSNs
        try:
            all_csts = db.query(Csticms).all()
            csts_data = []
            for cst in all_csts:
                csts_data.append({
                    'cst_id': cst.cst_id,
                    'codigo': cst.codigo,
                    'descricao': cst.descricao
                })
            
            print(f" CSTs carregados: {len(csts_data)} registros")
            
        except Exception as e:
            print(f"AVISO: Erro ao carregar CSTs: {e}")
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
            
            print(f" CSOSNs carregados: {len(csosns_data)} registros")
            
        except Exception as e:
            print(f"AVISO: Erro ao carregar CSOSNs: {e}")
            csosns_data = []
        
        # BUSCAR CLASSIFICAÇÕES IBS/CBS
        try:
            from database.models import ClassificacaoIBSCBS
            all_classificacoes = db.query(ClassificacaoIBSCBS).filter_by(ativo=True).all()
            classificacoes_ibs_cbs = []
            for clf in all_classificacoes:
                classificacoes_ibs_cbs.append({
                    'classificacao_id': clf.classificacao_id,
                    'codigo': clf.codigo,
                    'descricao': clf.descricao,
                    'aliquota_ibs_uf': float(clf.aliquota_ibs_uf),
                    'aliquota_ibs_mun': float(clf.aliquota_ibs_mun),
                    'aliquota_cbs': float(clf.aliquota_cbs)
                })
            
            print(f" Classificações IBS/CBS carregadas: {len(classificacoes_ibs_cbs)} registros")
            
        except Exception as e:
            print(f"AVISO: Erro ao carregar Classificações IBS/CBS: {e}")
            classificacoes_ibs_cbs = []
        
        print(f" Renderizando template com {len(destinatarios_data)} Destinatários/Tomadores e {len(produtos_data)} produtos para cliente {emitente_cliente_id}")
        
        return render_template('admin/nfes/emitir.html',
                             emitente_data=emitente_data_for_template,
                             destinatarios=destinatarios_data,
                             produtos=produtos_data,
                             all_cfops=cfops_data,
                             all_csts=csts_data,
                             all_csosns=csosns_data,
                             all_ncms=ncms_data,
                             classificacoes_ibs_cbs=classificacoes_ibs_cbs,
                             regime_tributario=regime_tributario_nome,
                             initial_nfe_items=[])
        
    except Exception as e:
        print(f"ERRO: Erro geral em emitir_nfe: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao carregar formulário de NFe: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
    finally:
        if 'db' in locals():
            db.close()

@nfe_bp.route('/list')
@login_required
@viewer_or_higher_required()
def list_nfes():
    db = next(get_db())
    
    try:
        print("\n=== LIST_NFES: Iniciando ===")
        cliente_id_str = request.args.get('cliente_id')
        print(f"[IN] cliente_id recebido: {cliente_id_str} (tipo: {type(cliente_id_str)})")
        
        cliente_id = None  # Inicializar
        accessible_client_ids = []
        
        # OK: AJUSTE: Admin comum só vê NFes do cliente ativo
        # Super Admin vê todas as NFes quando cliente_id não é fornecido
        if not cliente_id_str:
            print("[?] Nenhum cliente_id fornecido na URL")
            # Se não forneceu cliente_id, verificar se é Super Admin
            if hasattr(current_user, 'is_super_admin') and current_user.is_super_admin():
                # Super Admin: buscar todos os clientes acessíveis
                accessible_client_ids = get_accessible_client_ids(db)
                print(f"[ADMIN] Super Admin - Clientes acessíveis: {accessible_client_ids}")
            else:
                # Admin Comum: pegar apenas cliente ativo da sessão
                cliente_ativo_id = session.get('current_client_id')
                print(f"[USER] Admin Comum - Cliente ativo na sessão: {cliente_ativo_id}")
                
                if not cliente_ativo_id:
                    print("[!] Nenhum cliente ativo na sessão")
                    flash('Selecione um cliente para visualizar as NFes.', 'warning')
                    return redirect(url_for('home.home'))
                accessible_client_ids = [cliente_ativo_id]
                cliente_id = cliente_ativo_id
                print(f"[OK] Admin Comum - Filtrando NFes do cliente: {cliente_id}")
        else:
            # Se forneceu cliente_id específico, usar ele
            try:
                cliente_id = int(cliente_id_str)
                accessible_client_ids = [cliente_id]
                print(f"[OK] Cliente específico fornecido: {cliente_id}")
            except ValueError as ve:
                print(f"[X] Erro ao converter cliente_id: {ve}")
                flash('ID do cliente inválido.', 'danger')
                return redirect(url_for('home.home'))
        
        # Verificar se tem acesso aos clientes
        if not accessible_client_ids:
            flash('Você não tem acesso a nenhum cliente.', 'warning')
            return redirect(url_for('home.home'))
        
        # Obter parâmetros de filtro
        filtro_numero = request.args.get('numero', '').strip()
        filtro_destinatario = request.args.get('destinatario', '').strip()
        filtro_data_inicio = request.args.get('data_inicio', '').strip()
        filtro_data_fim = request.args.get('data_fim', '').strip()
        filtro_status = request.args.get('status', '').strip()
        
        # BUSCAR NFEs COM SQL RAW para evitar problemas de ORM
        if cliente_id:
            # Filtrar por cliente específico
            where_clauses = ["n.cliente_id = :cliente_id"]
            params = {'cliente_id': cliente_id}
            
            # Adicionar filtros adicionais
            if filtro_numero:
                where_clauses.append("CAST(n.numero AS TEXT) LIKE :numero")
                params['numero'] = f'%{filtro_numero}%'
            
            if filtro_destinatario:
                where_clauses.append("(n.destinatario_razao_social ILIKE :destinatario OR n.destinatario_cnpj_cpf LIKE :destinatario)")
                params['destinatario'] = f'%{filtro_destinatario}%'
            
            if filtro_data_inicio:
                where_clauses.append("DATE(n.data_criacao) >= :data_inicio")
                params['data_inicio'] = filtro_data_inicio
            
            if filtro_data_fim:
                where_clauses.append("DATE(n.data_criacao) <= :data_fim")
                params['data_fim'] = filtro_data_fim
            
            if filtro_status:
                where_clauses.append("n.status = :status")
                params['status'] = filtro_status
            
            where_sql = " AND ".join(where_clauses)
            
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
                    n.mensagem_sefaz,
                    n.numero,
                    n.serie,
                    c.razao_social as cliente_nome
                FROM nfe_emitidas n
                JOIN clientes c ON n.cliente_id = c.cliente_id
                WHERE {where_sql}
                ORDER BY n.numero DESC, n.serie DESC
                LIMIT 100
            """)
            result = db.execute(query, params)
        else:
            # Buscar NFEs dos clientes acessíveis (Super Admin = todos, Admin Comum = apenas ativo)
            # Usar placeholders seguros para evitar SQL injection
            where_clauses = []
            placeholders = ','.join([f':id_{i}' for i in range(len(accessible_client_ids))])
            params = {f'id_{i}': client_id for i, client_id in enumerate(accessible_client_ids)}
            
            where_clauses.append(f"n.cliente_id IN ({placeholders})")
            
            # Adicionar filtros adicionais
            if filtro_numero:
                where_clauses.append("CAST(n.numero AS TEXT) LIKE :numero")
                params['numero'] = f'%{filtro_numero}%'
            
            if filtro_destinatario:
                where_clauses.append("(n.destinatario_razao_social ILIKE :destinatario OR n.destinatario_cnpj_cpf LIKE :destinatario)")
                params['destinatario'] = f'%{filtro_destinatario}%'
            
            if filtro_data_inicio:
                where_clauses.append("DATE(n.data_criacao) >= :data_inicio")
                params['data_inicio'] = filtro_data_inicio
            
            if filtro_data_fim:
                where_clauses.append("DATE(n.data_criacao) <= :data_fim")
                params['data_fim'] = filtro_data_fim
            
            if filtro_status:
                where_clauses.append("n.status = :status")
                params['status'] = filtro_status
            
            where_sql = " AND ".join(where_clauses)
            
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
                    n.mensagem_sefaz,
                    n.numero,
                    n.serie,
                    c.razao_social as cliente_nome
                FROM nfe_emitidas n
                JOIN clientes c ON n.cliente_id = c.cliente_id
                WHERE {where_sql}
                ORDER BY n.numero DESC, n.serie DESC
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
        print(f"ERRO: Erro ao listar NFes: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao listar NFes: {str(e)}', 'error')
        return redirect(url_for('home.home'))
    finally:
        if 'db' in locals():
            db.close()

@nfe_bp.route('/view/<int:nfe_id>')
@login_required
@viewer_or_higher_required()
def view(nfe_id):
    """Visualizar uma NFe específica"""
    from datetime import datetime, date
    from decimal import Decimal
    from jinja2 import Undefined
    
    def sanitize_value(value):
        """Converte valores não serializáveis para tipos Python básicos"""
        # Se for Undefined do Jinja2, retorna None
        if isinstance(value, Undefined):
            return None
        # Mantém datetime e date como estão (Jinja2 sabe trabalhar com eles)
        if isinstance(value, (datetime, date)):
            return value
        # Decimal para float
        if isinstance(value, Decimal):
            return float(value)
        # Bytes para string
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8')
            except:
                return None
        # Se for dict, sanitiza recursivamente
        if isinstance(value, dict):
            return {k: sanitize_value(v) for k, v in value.items()}
        # Se for lista, sanitiza cada item
        if isinstance(value, (list, tuple)):
            return [sanitize_value(item) for item in value]
        return value
    
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
        try:
            if hasattr(nfe, '_mapping') and callable(nfe._mapping):
                nfe_data = dict(nfe._mapping())
            elif hasattr(nfe, '_mapping'):
                nfe_data = dict(nfe._mapping)
            elif hasattr(nfe, '_asdict') and callable(nfe._asdict):
                nfe_data = nfe._asdict()
            else:
                nfe_data = {column: getattr(nfe, column) for column in nfe._fields}
        except Exception as e:
            print(f"Erro ao converter resultado para dict: {e}")
            import traceback
            traceback.print_exc()
            nfe_data = {key: getattr(nfe, key) for key in dir(nfe) if not key.startswith('_') and not callable(getattr(nfe, key))}
        
        # Sanitiza todos os valores não serializáveis
        nfe_data = sanitize_value(nfe_data)
        
        # Se for NFC-e, redirecionar para a página correta
        if nfe_data.get('tipo_nfe') == 'NFCE':
            return redirect(url_for('nfce.consultar_nfce', nfce_id=nfe_id))
        
        # Parse json_nfe se for string
        if nfe_data.get('json_nfe') and isinstance(nfe_data['json_nfe'], str):
            try:
                import json
                nfe_data['json_nfe'] = json.loads(nfe_data['json_nfe'])
                # Sanitiza o json_nfe também após o parse
                nfe_data['json_nfe'] = sanitize_value(nfe_data['json_nfe'])
            except Exception as e:
                print(f"Erro ao fazer parse do json_nfe: {e}")
                nfe_data['json_nfe'] = None
        elif nfe_data.get('json_nfe'):
            # Se json_nfe já é um dict/objeto, sanitiza também
            nfe_data['json_nfe'] = sanitize_value(nfe_data['json_nfe'])
        
        # Enriquecer json_nfe com dados do emitente se não existir
        if nfe_data.get('json_nfe') and not nfe_data['json_nfe'].get('emitente'):
            try:
                emitente_query = text("""
                    SELECT cnpj, razao_social, nome_fantasia, inscricao_estadual
                    FROM clientes 
                    WHERE cliente_id = :cliente_id
                """)
                emitente_result = db.execute(emitente_query, {'cliente_id': nfe_data['cliente_id']}).fetchone()
                
                if emitente_result:
                    nfe_data['json_nfe']['emitente'] = {
                        'cnpj': emitente_result[0],
                        'razao_social': emitente_result[1],
                        'nome_fantasia': emitente_result[2],
                        'ie': emitente_result[3]
                    }
            except Exception as e:
                print(f"Aviso: Erro ao buscar dados do emitente: {e}")
        
        # Enriquecer items com descrições dos produtos se não existir
        if nfe_data.get('json_nfe') and nfe_data['json_nfe'].get('items'):
            try:
                for item in nfe_data['json_nfe']['items']:
                    if not item.get('descricao') or item.get('descricao') == 'None':
                        codigo = item.get('codigo_produto') or item.get('codigo') or item.get('cProd')
                        if codigo:
                            produto_query = text("""
                                SELECT descricao FROM produtos 
                                WHERE codigo = :codigo AND cliente_id = :cliente_id
                            """)
                            produto_result = db.execute(produto_query, {
                                'codigo': codigo,
                                'cliente_id': nfe_data['cliente_id']
                            }).fetchone()
                            
                            if produto_result and produto_result[0]:
                                item['descricao'] = produto_result[0]
            except Exception as e:
                print(f"Aviso: Erro ao buscar descrições dos produtos: {e}")
        
        # Debug com serialização segura
        try:
            import json
            print(f"NFe data keys: {list(nfe_data.keys())}")
            # Tenta serializar para verificar se há problemas
            json.dumps(nfe_data, default=str)
        except Exception as e:
            print(f"Aviso: NFe data contém valores não serializáveis: {e}")
        
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
@viewer_or_higher_required()
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
        xml_original = None
        if nfe_data.get('json_nfe'):
            xml_original = nfe_data['json_nfe'].get('xml_content')
        
        if not xml_original:
            return jsonify({'success': False, 'message': 'XML não disponível para esta NFe'}), 400
        
        # CORREÇÃO: Se a NFe está AUTORIZADA e o XML não tem protNFe, gerar protocolo
        xml_para_danfe = xml_original
        status = nfe_data.get('status', '').upper()
        
        if status == 'AUTORIZADA' and '<protNFe' not in xml_original:
            print(f"[DANFE] NFe {nfe_id} autorizada sem protNFe, gerando protocolo com tpAmb=1...")
            try:
                from services.nfe_service import NFeService
                
                # XML já é só NFe sem protocolo
                nfe_service = NFeService()
                resultado_sefaz = {
                    'chave_acesso': nfe_data.get('chave_acesso'),
                    'protocolo': nfe_data.get('protocolo_autorizacao') or nfe_data.get('protocolo_sefaz'),
                    'status': '100',
                    'digVal': 'N/A',
                    'ambiente_real': True
                }
                
                xml_para_danfe = nfe_service._gerar_xml_protocolo(xml_original, resultado_sefaz)
                print(f"[DANFE] Protocolo gerado com tpAmb=1")
                # Verificar se protNFe foi realmente adicionado
                if '<protNFe' in xml_para_danfe and '<tpAmb>1</tpAmb>' in xml_para_danfe:
                    print(f"[DANFE] ✅ XML final contém protNFe com tpAmb=1")
                else:
                    print(f"[DANFE] ❌ ERRO: XML final não contém protNFe com tpAmb=1")
                    print(f"[DANFE] Primeiros 1000 chars: {xml_para_danfe[:1000]}")
            except Exception as ex:
                print(f"[DANFE] Erro ao gerar protocolo: {ex}")
                import traceback
                traceback.print_exc()
        
        # Gerar DANFE usando a biblioteca Python NFe
        from services.danfe_service import generate_danfe
        import time
        
        try:
            # Buscar cliente_id da NFe
            cliente_id_nfe = nfe_data.get('cliente_id')
            pdf_path = generate_danfe(xml_para_danfe, nfe_id, cliente_id_nfe)
            
            # Adicionar timestamp para evitar cache do navegador
            timestamp = int(time.time())
            pdf_url = url_for('static', filename=f'danfe/danfe_{nfe_id}.pdf') + f'?t={timestamp}'
            
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
@viewer_or_higher_required()
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
        xml_original = None
        if nfe_data.get('json_nfe'):
            xml_original = nfe_data['json_nfe'].get('xml_content')
        
        if not xml_original:
            return jsonify({'success': False, 'message': 'XML não disponível para esta NFe'}), 400
        
        # CORREÇÃO: Se a NFe está AUTORIZADA e o XML não tem protNFe, gerar protocolo
        xml_para_danfe = xml_original
        status = nfe_data.get('status', '').upper()
        
        if status == 'AUTORIZADA' and '<protNFe' not in xml_original:
            print(f"[DANFE-AFTER] NFe {nfe_id} autorizada sem protNFe, gerando protocolo com tpAmb=1...")
            try:
                from services.nfe_service import NFeService
                
                # XML já é só NFe sem protocolo
                nfe_service = NFeService()
                resultado_sefaz = {
                    'chave_acesso': nfe_data.get('chave_acesso'),
                    'protocolo': nfe_data.get('protocolo_autorizacao') or nfe_data.get('protocolo_sefaz'),
                    'status': '100',
                    'digVal': 'N/A',
                    'ambiente_real': True
                }
                
                xml_para_danfe = nfe_service._gerar_xml_protocolo(xml_original, resultado_sefaz)
                print(f"[DANFE-AFTER] Protocolo gerado com tpAmb=1")
            except Exception as ex:
                print(f"[DANFE-AFTER] Erro ao gerar protocolo: {ex}")
                import traceback
                traceback.print_exc()
        
        # Gerar DANFE usando o serviço
        from services.danfe_service import generate_danfe
        import time
        
        try:
            # Buscar cliente_id da NFe
            cliente_id_nfe = nfe_data.get('cliente_id')
            pdf_path = generate_danfe(xml_para_danfe, nfe_id, cliente_id_nfe)
            
            # Adicionar timestamp para evitar cache do navegador
            timestamp = int(time.time())
            pdf_url = url_for('static', filename=f'danfe/danfe_{nfe_id}.pdf') + f'?t={timestamp}'
            
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


@nfe_bp.route('/<int:nfe_id>/enviar-danfe', methods=['POST'])
@login_required
@viewer_or_higher_required()
def enviar_danfe_email(nfe_id):
    """Enviar DANFE por email"""
    db = next(get_db())
    try:
        # Obter dados do request
        data = request.json or {}
        email_destinatario = data.get('email_destinatario')
        
        if not email_destinatario:
            return jsonify({'success': False, 'message': 'Email do destinatário não informado'}), 400
        
        # Validar formato do email
        import re
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email_destinatario):
            return jsonify({'success': False, 'message': 'Email inválido'}), 400
        
        # Buscar NFe no banco
        query = text("""
            SELECT 
                n.*,
                c.razao_social as cliente_razao_social,
                c.nome_fantasia as cliente_fantasia
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
        
        # Verificar se DANFE existe
        danfe_path = os.path.join('static', 'danfe', f'danfe_{nfe_id}.pdf')
        if not os.path.exists(danfe_path):
            return jsonify({'success': False, 'message': 'DANFE não encontrado. Gere o DANFE primeiro.'}), 404
        
        # Preparar dados do email
        chave_acesso = nfe_data.get('chave_acesso', 'N/A')
        numero = nfe_data.get('numero', 'N/A')
        cliente_nome = nfe_data.get('cliente_fantasia') or nfe_data.get('cliente_razao_social', 'N/A')
        
        assunto = f'NFe {numero} - DANFE - {cliente_nome}'
        
        corpo_html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 15px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .info {{ margin: 10px 0; padding: 10px; background-color: white; border-left: 4px solid #4CAF50; }}
                    .footer {{ text-align: center; padding: 15px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Documento Auxiliar da Nota Fiscal Eletrônica</h2>
                    </div>
                    <div class="content">
                        <p>Prezado(a),</p>
                        <p>Segue em anexo o DANFE (Documento Auxiliar da Nota Fiscal Eletrônica).</p>
                        
                        <div class="info">
                            <strong>Número NFe:</strong> {numero}<br>
                            <strong>Emitente:</strong> {cliente_nome}<br>
                            <strong>Chave de Acesso:</strong> {chave_acesso}
                        </div>
                        
                        <p>Este documento deve acompanhar a mercadoria em trânsito.</p>
                        <p>O arquivo XML da NFe pode ser consultado usando a chave de acesso acima.</p>
                    </div>
                    <div class="footer">
                        <p>Este é um email automático. Por favor, não responda.</p>
                        <p>Sistema de Gestão de NFe</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Ler arquivo PDF
        try:
            with open(danfe_path, 'rb') as f:
                pdf_content = f.read()
        except Exception as e:
            print(f"Erro ao ler arquivo DANFE: {e}")
            return jsonify({'success': False, 'message': f'Erro ao ler arquivo DANFE: {str(e)}'}), 500
        
        # Preparar anexo
        anexos = [{
            'nome': f'DANFE_{numero}.pdf',
            'conteudo': pdf_content
        }]
        
        # Enviar email usando o serviço
        from services.email_service import EmailService
        
        try:
            email_service = EmailService()
            resultado = email_service.enviar_email(
                destinatario=email_destinatario,
                assunto=assunto,
                corpo_html=corpo_html,
                anexos=anexos
            )
            
            if resultado['success']:
                print(f"Email com DANFE enviado com sucesso para {email_destinatario}")
                return jsonify({'success': True, 'message': f'DANFE enviado para {email_destinatario}'})
            else:
                print(f"Erro ao enviar email: {resultado['message']}")
                return jsonify({'success': False, 'message': resultado['message']}), 500
                
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Erro ao enviar email: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500
    finally:
        db.close()


# Substituir todo o método edit:

@nfe_bp.route('/edit/<int:nfe_id>', methods=['GET', 'POST'])
@login_required
@editor_or_admin_required()
def edit(nfe_id):
    """Editar NFe (rascunho ou rejeitada)"""
    db = next(get_db())
    
    # DEBUG: Log do método HTTP recebido
    print(f"🔍 [EDIT NFe {nfe_id}] Método: {request.method}")
    print(f"🔍 [EDIT NFe {nfe_id}] Form data: {dict(request.form)}")
    print(f"🔍 [EDIT NFe {nfe_id}] Action: {request.form.get('action', 'N/A')}")
    
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
                
                # OK: CONVERSÃO SEGURA PARA DICIONÁRIO - CORREÇÃO PRINCIPAL
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
                    print(f"ERRO: Erro na conversão manual: {conv_error}")
                    flash('Erro ao processar dados da NFe', 'error')
                    return redirect(url_for('nfe.list_nfes'))
                
                print(f"OK: NFe {nfe_id} carregada para edição - Status: {nfe_data.get('status', 'N/A')}")
                
                # Verificar se pode ser editada
                status_editaveis = ['RASCUNHO', 'REJEITADA', 'ERRO']
                current_status = nfe_data.get('status', '').upper()
                if current_status not in status_editaveis:
                    print(f"AVISO: Status '{current_status}' não é editável")
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
                            print(f"AVISO: json_nfe em formato inesperado: {type(json_nfe_raw)}")
                            json_data = {}
                        
                        form_data = json_data.get('form_data', {})
                        items_data = json_data.get('items', [])
                        
                        # Adicionar dados do destinatário ao form_data (necessário para preencher select)
                        if nfe_data.get('destinatario_cnpj_cpf'):
                            form_data['destinatario_cnpj_cpf'] = nfe_data['destinatario_cnpj_cpf']
                        if nfe_data.get('destinatario_razao_social'):
                            form_data['destinatario_razao_social'] = nfe_data['destinatario_razao_social']
                        
                        print(f" Form data extraído: {len(form_data)} campos")
                        print(f" Items extraídos: {len(items_data)} itens")
                        
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"AVISO: Erro ao decodificar JSON NFe: {e}")
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
                print(" Carregando dados auxiliares...")
                
                # OK: CLIENTES
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
                            print(f"AVISO: Erro ao processar cliente: {e}")
                            continue
                except Exception as e:
                    print(f"AVISO: Erro ao buscar clientes: {e}")
                    clientes = []
                
                # OK: CFOPS
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
                            print(f"AVISO: Erro ao processar CFOP: {e}")
                            continue
                except Exception as e:
                    print(f"AVISO: Erro ao buscar CFOPs: {e}")
                    cfops = []
                
                # OK: NCMs
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
                            print(f"AVISO: Erro ao processar NCM: {e}")
                            continue
                except Exception as e:
                    print(f"AVISO: Erro ao buscar NCMs: {e}")
                    ncms = []

                # OK: CSTs
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
                            print(f"AVISO: Erro ao processar CST: {e}")
                            continue
                except Exception as e:
                    print(f"AVISO: Erro ao buscar CSTs: {e}")
                    csts = []
                
                # OBTER CLIENTE_ID DA NFE (necessário para filtrar produtos)
                cliente_id = nfe_data.get('cliente_id')
                if not cliente_id:
                    print("ERRO: cliente_id não encontrado na NFe")
                    flash('Erro: Cliente não identificado na NFe', 'error')
                    return redirect(url_for('nfe.list_nfes'))
                
                # OK: PRODUTOS (filtrar por cliente)
                try:
                    produtos_query = text("""
                        SELECT p.produto_id, p.codigo_interno, p.descricao, p.preco_unitario_padrao,
                               p.unidade_comercial, n.codigo as ncm_codigo, cf.cfop as cfop_codigo,
                               cst.codigo as cst_codigo, cs.codigo as csosn_codigo, p.origem_mercadoria as origem_mercadoria_id
                        FROM produtos p
                        LEFT JOIN ncms n ON p.ncm_id = n.ncm_id
                        LEFT JOIN cfops cf ON p.cfop_id = cf.cfop_id
                        LEFT JOIN cst_icms cst ON p.cst_id = cst.cst_id
                        LEFT JOIN csosn_icms cs ON p.csosn_id = cs.csosn_id
                        WHERE p.cliente_id = :cliente_id AND p.ativo = true
                        ORDER BY p.descricao
                    """)
                    produtos_result = db.execute(produtos_query, {'cliente_id': cliente_id}).fetchall()
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
                                    'descricao': produto_row[2],
                                    'preco_unitario_padrao': float(produto_row[3]) if produto_row[3] else 0.0,
                                    'unidade_comercial': produto_row[4],
                                    'ncm_codigo': produto_row[5],
                                    'cfop_codigo': produto_row[6],
                                    'cst_codigo': produto_row[7],
                                    'csosn_codigo': produto_row[8],
                                    'origem_mercadoria_id': produto_row[9]
                                })
                        except Exception as e:
                            print(f"AVISO: Erro ao processar produto: {e}")
                            continue
                except Exception as e:
                    print(f"AVISO: Erro ao buscar produtos: {e}")
                    produtos = []
                
                # BUSCAR DADOS DO EMITENTE (CLIENTE)
                try:
                    cliente_id = nfe_data.get('cliente_id')
                    emitente_query = text("""
                        SELECT cliente_id, razao_social, cnpj, nome_fantasia, logradouro, numero, 
                               bairro, cep, codigo_municipio, nome_municipio, uf, inscricao_estadual, 
                               regime_tributario_id, ambiente, complemento
                        FROM clientes WHERE cliente_id = :cliente_id
                    """)
                    emitente_result = db.execute(emitente_query, {'cliente_id': cliente_id}).fetchone()
                    
                    if emitente_result:
                        if hasattr(emitente_result, '_asdict'):
                            emitente_data_for_template = emitente_result._asdict()
                        elif hasattr(emitente_result, '_mapping'):
                            mapping = emitente_result._mapping
                            emitente_data_for_template = dict(mapping() if callable(mapping) else mapping)
                        else:
                            emitente_data_for_template = {
                                'cliente_id': emitente_result[0],
                                'razao_social': emitente_result[1],
                                'cnpj': emitente_result[2],
                                'nome_fantasia': emitente_result[3],
                                'logradouro': emitente_result[4],
                                'numero': emitente_result[5],
                                'bairro': emitente_result[6],
                                'cep': emitente_result[7],
                                'codigo_municipio': emitente_result[8],
                                'nome_municipio': emitente_result[9],
                                'uf': emitente_result[10],
                                'inscricao_estadual': emitente_result[11],
                                'regime_tributario_id': emitente_result[12],
                                'ambiente': emitente_result[13],
                                'complemento': emitente_result[14] if len(emitente_result) > 14 else None
                            }
                    else:
                        emitente_data_for_template = {}
                        print(f"AVISO: Emitente não encontrado para cliente_id: {cliente_id}")
                except Exception as e:
                    print(f"AVISO: Erro ao buscar dados do emitente: {e}")
                    emitente_data_for_template = {}
                
                # BUSCAR Destinatários/Tomadores DO CLIENTE
                try:
                    destinatarios_query = text("""
                        SELECT destinatario_id, nome_razao_social, cpf_cnpj, logradouro, numero, 
                               bairro, cep, codigo_municipio, nome_municipio, uf
                        FROM destinatarios_nfe WHERE cliente_id = :cliente_id
                    """)
                    destinatarios_result = db.execute(destinatarios_query, {'cliente_id': cliente_id}).fetchall()
                    destinatarios = []
                    for dest_row in destinatarios_result:
                        try:
                            if hasattr(dest_row, '_asdict'):
                                destinatarios.append(dest_row._asdict())
                            elif hasattr(dest_row, '_mapping'):
                                mapping = dest_row._mapping
                                destinatarios.append(dict(mapping() if callable(mapping) else mapping))
                            else:
                                destinatarios.append({
                                    'destinatario_id': dest_row[0],
                                    'nome_razao_social': dest_row[1],
                                    'cpf_cnpj': dest_row[2],
                                    'logradouro': dest_row[3],
                                    'numero': dest_row[4],
                                    'bairro': dest_row[5],
                                    'cep': dest_row[6],
                                    'codigo_municipio': dest_row[7],
                                    'nome_municipio': dest_row[8],
                                    'uf': dest_row[9]
                                })
                        except Exception as e:
                            print(f"AVISO: Erro ao processar destinatário: {e}")
                            continue
                except Exception as e:
                    print(f"AVISO: Erro ao buscar Destinatários/Tomadores: {e}")
                    destinatarios = []
                
                # BUSCAR CSOSNs
                try:
                    csosns_query = text("SELECT codigo, descricao FROM csosn_icms ORDER BY codigo")
                    csosns_result = db.execute(csosns_query).fetchall()
                    csosns = []
                    for csosn_row in csosns_result:
                        try:
                            if hasattr(csosn_row, '_asdict'):
                                csosns.append(csosn_row._asdict())
                            elif hasattr(csosn_row, '_mapping'):
                                mapping = csosn_row._mapping
                                csosns.append(dict(mapping() if callable(mapping) else mapping))
                            else:
                                csosns.append({
                                    'codigo': csosn_row[0],
                                    'descricao': csosn_row[1]
                                })
                        except Exception as e:
                            print(f"AVISO: Erro ao processar CSOSN: {e}")
                            continue
                except Exception as e:
                    print(f"AVISO: Erro ao buscar CSOSNs: {e}")
                    csosns = []
                
                # BUSCAR REGIME TRIBUTÁRIO
                regime_tributario_nome = 'Regime Normal'
                try:
                    if emitente_data_for_template.get('regime_tributario_id'):
                        regime_query = text("SELECT nome FROM regimes_tributarios WHERE regime_tributario_id = :regime_id")
                        regime_result = db.execute(regime_query, {'regime_id': emitente_data_for_template['regime_tributario_id']}).fetchone()
                        if regime_result:
                            regime_tributario_nome = regime_result[0] if hasattr(regime_result, '__getitem__') else regime_result.nome
                except Exception as e:
                    print(f"AVISO: Erro ao buscar regime tributário: {e}")
                
                print(f" Dados auxiliares carregados: {len(clientes)} clientes, {len(cfops)} CFOPs, {len(ncms)} NCMs, {len(produtos)} produtos")
                print(f" Destinatários/Tomadores: {len(destinatarios)}, CSOSNs: {len(csosns)}, Regime: {regime_tributario_nome}")
                
                # BUSCAR CLASSIFICAÇÕES IBS/CBS
                classificacoes_ibs_cbs = []
                try:
                    from database.models import ClassificacaoIBSCBS
                    clf_query = text("SELECT classificacao_id, codigo, descricao, aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs FROM classificacoes_ibs_cbs WHERE ativo = true")
                    clf_results = db.execute(clf_query).fetchall()
                    for clf_row in clf_results:
                        classificacoes_ibs_cbs.append({
                            'classificacao_id': clf_row[0],
                            'codigo': clf_row[1],
                            'descricao': clf_row[2],
                            'aliquota_ibs_uf': float(clf_row[3]),
                            'aliquota_ibs_mun': float(clf_row[4]),
                            'aliquota_cbs': float(clf_row[5])
                        })
                    print(f" Classificações IBS/CBS carregadas: {len(classificacoes_ibs_cbs)} registros")
                except Exception as e:
                    print(f"AVISO: Erro ao buscar Classificações IBS/CBS: {e}")
                
                # USAR O MESMO TEMPLATE DE EMISSÃO MAS EM MODO EDIÇÃO
                return render_template('admin/nfes/emitir.html',
                                     emitente_data=emitente_data_for_template,
                                     destinatarios=destinatarios,
                                     produtos=produtos,
                                     all_cfops=cfops,
                                     all_csts=csts,
                                     all_csosns=csosns,
                                     all_ncms=ncms,
                                     classificacoes_ibs_cbs=classificacoes_ibs_cbs,
                                     regime_tributario=regime_tributario_nome,
                                     initial_nfe_items=items_data,
                                     form_data=form_data,
                                     nfe_id=nfe_id,
                                     edit_mode=True,
                                     from_rejected=request.args.get('from') == 'rejected')
                
            except Exception as e:
                print(f"ERRO: Erro ao carregar NFe para edição: {e}")
                import traceback
                traceback.print_exc()
                flash('Erro ao carregar NF-e', 'error')
                return redirect(url_for('nfe.list_nfes'))
        
        elif request.method == 'POST':
            # ... código do POST permanece o mesmo ...
            try:
                # Processar dados do formulário
                dados_nfe = {
                    'numero_nfe': request.form.get('numero_nfe', '1'),
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
                
                # Processar itens - detectar automaticamente pelos campos produto_N
                itens = []
                
                # Encontrar todos os índices de produtos no formulário
                item_indices = []
                for key in request.form.keys():
                    if key.startswith('produto_'):
                        idx = key.split('_')[1]
                        if idx not in item_indices:
                            item_indices.append(idx)
                
                print(f"🔍 [EDIT NFe {nfe_id}] Índices de itens encontrados: {item_indices}")
                
                for i, idx in enumerate(item_indices):
                    # OK: BUSCAR CFOP DO PRODUTO SE NÃO FORNECIDO
                    cfop_item = request.form.get(f'cfop_{idx}')
                    codigo_produto = request.form.get(f'codigo_produto_{idx}')
                    
                    # Se CFOP não fornecido, buscar do produto
                    if not cfop_item or cfop_item.strip() == '':
                        print(f"AVISO: CFOP vazio para item {i+1}, buscando do produto {codigo_produto}")
                        
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
                                        print(f"OK: CFOP encontrado para produto {codigo_produto}: {cfop_item}")
                                    else:
                                        cfop_item = '5102'  # CFOP padrão para venda
                                        print(f"AVISO: CFOP não encontrado para produto {codigo_produto}, usando padrão: {cfop_item}")
                                else:
                                    cfop_item = '5102'
                                    print(f"AVISO: Produto {codigo_produto} não encontrado, usando CFOP padrão: {cfop_item}")
                            except Exception as e:
                                print(f"ERRO: Erro ao buscar CFOP do produto: {e}")
                                cfop_item = '5102'
                        else:
                            cfop_item = '5102'
                            print(f"AVISO: Código do produto vazio, usando CFOP padrão: {cfop_item}")
                    
                    # OK: VALIDAR E FORMATAR CFOP
                    if cfop_item:
                        cfop_item = str(cfop_item).replace('.', '').replace('-', '').strip()
                        if len(cfop_item) != 4 or not cfop_item.isdigit():
                            print(f"AVISO: CFOP inválido '{cfop_item}', usando padrão '5102'")
                            cfop_item = '5102'
                    else:
                        cfop_item = '5102'
                    
                    # SEMPRE buscar descrição real do banco, ignorando o que vem do form
                    descricao_produto = None
                    if codigo_produto:
                        try:
                            produto_query = text("""
                                SELECT descricao FROM produtos 
                                WHERE (codigo = :codigo OR codigo_interno = :codigo OR produto_id::text = :codigo)
                                AND cliente_id = :cliente_id
                                LIMIT 1
                            """)
                            produto_result = db.execute(produto_query, {
                                'codigo': codigo_produto,
                                'cliente_id': cliente_id
                            }).fetchone()
                            
                            if produto_result and produto_result[0]:
                                descricao_produto = produto_result[0]
                                print(f"✅ Descrição do produto {codigo_produto} encontrada no banco: {descricao_produto[:50]}...")
                            else:
                                print(f"⚠️ Descrição do produto {codigo_produto} NÃO encontrada no banco")
                                # Fallback para o form apenas se não encontrar no banco
                                descricao_produto = request.form.get(f'descricao_{idx}')
                        except Exception as e:
                            print(f"❌ Erro ao buscar descrição do produto: {e}")
                            # Fallback para o form em caso de erro
                            descricao_produto = request.form.get(f'descricao_{idx}')
                    
                    # Se ainda não tem descrição, usar genérica
                    if not descricao_produto or descricao_produto.strip() == '' or descricao_produto.startswith('Produto '):
                        descricao_produto = f'Produto {codigo_produto}'
                        print(f"⚠️ Usando descrição genérica para produto {codigo_produto}")
                    
                    item = {
                        'codigo_produto': codigo_produto,
                        'descricao': descricao_produto,
                        'ncm': request.form.get(f'ncm_{idx}'),
                        'cfop': cfop_item,  # OK: CFOP garantido
                        'origem': request.form.get(f'origem_{idx}', '0'),
                        # ICMS
                        'cst_icms': request.form.get(f'cst_icms_{idx}', '00'),
                        'csosn_icms': request.form.get(f'csosn_{idx}'),
                        'aliquota_icms': request.form.get(f'aliquota_icms_{idx}', '0'),
                        'reducao_base_icms': request.form.get(f'reducao_base_icms_{idx}', '0'),
                        'modalidade_bc_icms': request.form.get(f'modalidade_bc_icms_{idx}'),
                        'motivo_desoneracao_icms': request.form.get(f'motivo_desoneracao_icms_{idx}'),
                        'bc_icms': request.form.get(f'bc_icms_{idx}', '0'),
                        'valor_icms': request.form.get(f'valor_icms_{idx}', '0'),
                        # PIS
                        'cst_pis': request.form.get(f'cst_pis_{idx}'),
                        'aliquota_pis': request.form.get(f'aliquota_pis_{idx}', '0'),
                        # COFINS
                        'cst_cofins': request.form.get(f'cst_cofins_{idx}'),
                        'aliquota_cofins': request.form.get(f'aliquota_cofins_{idx}', '0'),
                        # IPI
                        'cst_ipi': request.form.get(f'cst_ipi_{idx}'),
                        'aliquota_ipi': request.form.get(f'aliquota_ipi_{idx}', '0'),
                        # Produto
                        'quantidade': request.form.get(f'quantidade_{idx}'),
                        'unidade': request.form.get(f'unidade_{idx}'),
                        'valor_unitario': request.form.get(f'valor_unitario_{idx}'),
                        'valor_total': request.form.get(f'valor_total_{idx}')
                    }
                    
                    print(f" Item {i+1} processado - CFOP: {item['cfop']}, Produto: {item['codigo_produto']}")
                    itens.append(item)
                
                # Buscar NFe atual para pegar cliente_id
                nfe_query = text("SELECT cliente_id, status FROM nfe_emitidas WHERE nfe_emitida_id = :nfe_id")
                nfe_result = db.execute(nfe_query, {'nfe_id': nfe_id}).fetchone()
                
                if not nfe_result:
                    flash('NF-e não encontrada', 'error')
                    return redirect(url_for('nfe.list_nfes'))
                
                # Pegar cliente_id da NFe
                cliente_id = nfe_result[0]
                current_status = nfe_result[1]
                
                print(f"🔍 [EDIT NFe {nfe_id}] Cliente ID: {cliente_id}, Status: {current_status}")
                
                # Validações básicas
                if not cliente_id or not dados_nfe['natOp'] or not itens:
                    print(f"❌ [EDIT NFe {nfe_id}] Validação falhou - cliente_id: {cliente_id}, natOp: {dados_nfe.get('natOp')}, itens: {len(itens)}")
                    flash('Preencha todos os campos obrigatórios', 'error')
                    return redirect(url_for('nfe.edit', nfe_id=nfe_id))
                
                # Verificar se pode ser editada
                status_editaveis = ['RASCUNHO', 'REJEITADA', 'ERRO']
                if current_status.upper() not in status_editaveis:
                    flash('Esta NF-e não pode ser editada', 'error')
                    return redirect(url_for('nfe.view', nfe_id=nfe_id))
                
                # Buscar destinatário correto
                destinatario_id = request.form.get('destinatario')
                if not destinatario_id:
                    flash('Destinatário não selecionado', 'error')
                    return redirect(url_for('nfe.edit', nfe_id=nfe_id))
                
                destinatario_query = text("SELECT destinatario_id, nome_razao_social, cpf_cnpj FROM destinatarios_nfe WHERE destinatario_id = :dest_id")
                destinatario_result = db.execute(destinatario_query, {'dest_id': destinatario_id}).fetchone()
                
                if not destinatario_result:
                    flash('Destinatário não encontrado', 'error')
                    return redirect(url_for('nfe.edit', nfe_id=nfe_id))
                
                # Buscar dados completos do emitente para salvar no JSON
                emitente_query = text("""
                    SELECT cliente_id, razao_social, cnpj, nome_fantasia, inscricao_estadual, 
                           logradouro, numero, bairro, cep, codigo_municipio, nome_municipio, uf, ambiente
                    FROM clientes 
                    WHERE cliente_id = :cliente_id
                """)
                emitente_result = db.execute(emitente_query, {'cliente_id': cliente_id}).fetchone()
                
                emitente_dict = {}
                ambiente_str = 'homologacao'  # default
                if emitente_result:
                    # Ambiente: 1=Produção, 2=Homologação (padrão SEFAZ)
                    ambiente_cliente = emitente_result[12]
                    ambiente_str = 'producao' if ambiente_cliente == 1 else 'homologacao'
                    
                    emitente_dict = {
                        'cliente_id': emitente_result[0],
                        'razao_social': emitente_result[1],
                        'cnpj': emitente_result[2],
                        'nome_fantasia': emitente_result[3],
                        'ie': emitente_result[4],
                        'logradouro': emitente_result[5],
                        'numero': emitente_result[6],
                        'bairro': emitente_result[7],
                        'cep': emitente_result[8],
                        'codigo_municipio': emitente_result[9],
                        'nome_municipio': emitente_result[10],
                        'uf': emitente_result[11]
                    }
                
                # Preparar dados para salvar
                json_nfe = {
                    'form_data': dados_nfe,
                    'items': itens,
                    'emitente': emitente_dict,
                    'ambiente': ambiente_str
                }
                
                # Atualizar NFe no banco
                update_query = text("""
                    UPDATE nfe_emitidas 
                    SET cliente_id = :cliente_id,
                        numero = :numero,
                        serie = :serie,
                        data_emissao = :data_emissao,
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
                
                # NÃO mudar para PROCESSANDO aqui - só depois de confirmar emissão
                if action == 'save':
                    new_status = 'RASCUNHO'
                    mensagem = 'Rascunho atualizado'
                else:
                    # Para action='emit', manter o status atual até confirmar emissão
                    new_status = current_status if current_status in status_editaveis else 'RASCUNHO'
                    mensagem = 'Aguardando processamento'
                
                # OK: CORREÇÃO: Acessar dados do destinatário por índice ou atributo
                try:
                    if hasattr(destinatario_result, '_asdict'):
                        dest_data = destinatario_result._asdict()
                        dest_razao = dest_data.get('nome_razao_social', '')
                        dest_cnpj = dest_data.get('cpf_cnpj', '')
                    else:
                        # Acessar por índice - assumindo ordem específica da query
                        dest_razao = destinatario_result[1] if len(destinatario_result) > 1 else ''
                        dest_cnpj = destinatario_result[2] if len(destinatario_result) > 2 else ''
                except Exception as e:
                    print(f"AVISO: Erro ao extrair dados do destinatário: {e}")
                    dest_razao = 'N/A'
                    dest_cnpj = 'N/A'
                
                db.execute(update_query, {
                    'nfe_id': nfe_id,
                    'cliente_id': cliente_id,
                    'numero': int(dados_nfe['numero_nfe']),
                    'serie': int(dados_nfe['serie']),
                    'data_emissao': dados_nfe['dataEmissao'],
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
                
                print(f"OK: NFe {nfe_id} atualizada - Status: {new_status}")
                
                # Se escolheu emitir, processar na SEFAZ
                if action == 'emit':
                    try:
                        print(f" Tentando emitir NFe {nfe_id}...")
                        
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
                        print(f"ERRO: Erro ao emitir NFe editada: {e}")
                        import traceback
                        traceback.print_exc()
                        flash(f'NF-e atualizada, mas erro na emissão: {str(e)}', 'danger')
                else:
                    flash('NF-e atualizada com sucesso!', 'success')
                
                return redirect(url_for('nfe.view', nfe_id=nfe_id))
                
            except Exception as e:
                print(f"ERRO: Erro ao atualizar NFe: {e}")
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
@viewer_or_higher_required()
def download(nfe_id):
    """Download do XML da NFe"""
    flash('Funcionalidade de download em desenvolvimento.', 'info')
    return redirect(url_for('nfe.list_nfes'))

@nfe_bp.route('/reenviar/<int:nfe_id>', methods=['POST'])
@login_required
@editor_or_admin_required()
def reenviar_nfe(nfe_id):
    """Reenviar NFe rejeitada para a SEFAZ"""
    try:
        print(f" Tentando reenviar NFe ID: {nfe_id}")
        
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
        
        # Converter resultado para dict corretamente
        if hasattr(nfe_result, '_mapping'):
            nfe_data = dict(nfe_result._mapping)
        else:
            nfe_data = dict(nfe_result)
        
        # Verificar se está rejeitada ou processando
        status_upper = nfe_data['status'].upper()
        if status_upper not in ['REJEITADA', 'ERRO', 'PROCESSANDO']:
            return jsonify({
                'success': False,
                'message': f'Apenas NF-es rejeitadas ou em processamento podem ser reenviadas. Status atual: {nfe_data["status"]}'
            }), 400
        
        print(f"OK: NFe encontrada - Status: {nfe_data['status']}")
        
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
        
        print(f" Status atualizado para PROCESSANDO")
        
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
            'inscricao_estadual': emitente_data.inscricao_estadual,
            'regime_tributario_id': emitente_data.regime_tributario_id,  # [?] CRÍTICO para buscar regras tributárias
            'ambiente': emitente_data.ambiente  # Campo ambiente (1=Produção, 2=Homologação - padrão SEFAZ)
        }
        # Buscar destinatário - pode estar no form_data ou já armazenado na NFe
        
        form_data = json_data.get('form_data', {})
        destinatario_id = form_data.get('destinatario')
        destinatario_data: Dict[str, Any] = {}
        
        # Tentar buscar destinatário pelo ID no form_data
        if destinatario_id:
            try:
                dest_query = text("""
                    SELECT destinatario_id, nome_razao_social, cpf_cnpj, logradouro, numero, 
                           bairro, cep, codigo_municipio, nome_municipio, uf
                    FROM destinatarios_nfe 
                    WHERE destinatario_id = :dest_id AND cliente_id = :cliente_id
                """)
                dest_result = db.execute(dest_query, {
                    'dest_id': destinatario_id,
                    'cliente_id': nfe_data['cliente_id']
                }).fetchone()
                
                if dest_result:
                    dest_mapping = dest_result._mapping if hasattr(dest_result, '_mapping') else dest_result
                    destinatario_data = {
                        'nome_razao_social': dest_mapping['nome_razao_social'],
                        'cpf_cnpj': dest_mapping['cpf_cnpj'],
                        'logradouro': dest_mapping['logradouro'],
                        'numero': dest_mapping['numero'],
                        'bairro': dest_mapping['bairro'],
                        'cep': dest_mapping['cep'],
                        'codigo_municipio': dest_mapping['codigo_municipio'],
                        'nome_municipio': dest_mapping['nome_municipio'],
                        'uf': dest_mapping['uf']
                    }
            except Exception as e:
                print(f"Aviso: Erro ao buscar destinatário por ID: {e}")
        
        # Se não encontrou pelo ID, tentar usar dados já armazenados na NFe
        if not destinatario_data and nfe_data.get('destinatario_razao_social'):
            print("Usando dados do destinatário já armazenados na NFe")
            destinatario_data = {
                'nome_razao_social': nfe_data.get('destinatario_razao_social'),
                'cpf_cnpj': nfe_data.get('destinatario_cnpj_cpf'),
                'logradouro': form_data.get('dest_logradouro', 'RUA TESTE'),
                'numero': form_data.get('dest_numero', 'SN'),
                'bairro': form_data.get('dest_bairro', 'CENTRO'),
                'cep': form_data.get('dest_cep', '00000000'),
                'codigo_municipio': form_data.get('dest_codigo_municipio', '3550308'),
                'nome_municipio': form_data.get('dest_municipio', 'SAO PAULO'),
                'uf': form_data.get('dest_uf', 'SP')
            }
        
        # Verificar se destinatário foi encontrado
        if not destinatario_data or not destinatario_data.get('nome_razao_social'):
            # Atualizar status de volta para erro
            update_back_query = text("""
                UPDATE nfe_emitidas 
                SET status = 'ERRO',
                    mensagem_sefaz = 'Dados do destinatário não encontrados'
                WHERE nfe_emitida_id = :nfe_id
            """)
            db.execute(update_back_query, {'nfe_id': nfe_id})
            db.commit()
            
            return jsonify({
                'success': False,
                'message': 'Dados do destinatário não encontrados no rascunho'
            }), 400
        
        # Gerar XML
        ambiente = json_data.get('ambiente', 'homologacao')
        # tpAmb SEFAZ: 1=Produção, 2=Homologação
        tp_amb = 1 if ambiente == 'producao' else 2
        
        xml_gerado = generate_nfe_xml(
            json_data.get('form_data', {}),
            emitente_data_for_template,
            destinatario_data,
            json_data.get('items', []),
            tp_amb,
            'emitir'
        )
        
        # Assinar XML - BLOQUEIA SE FALHAR
        try:
            from services.xml_signature_service import xml_signature_service
            xml_assinado = xml_signature_service.sign_nfe_xml(xml_gerado, db, nfe_data['cliente_id'])
            print(f"[OK] XML assinado com sucesso - reenvio")
        except Exception as e:
            print(f"[X] ERRO CRÍTICO na assinatura (reenvio): {e}")
            return jsonify({
                'success': False,
                'message': f'Erro na assinatura digital: {str(e)}. Verifique se o certificado está válido.'
            }), 400
        
        # Buscar certificado
        certificado = get_active_certificate_for_client(db, nfe_data['cliente_id'])
        if not certificado:
            return jsonify({
                'success': False,
                'message': 'Certificado não encontrado'
            }), 400
        
        # Enviar para SEFAZ
        resultado_sefaz = nfe_service._processar_envio_sefaz(xml_assinado, certificado, ambiente, nfe_data['cliente_id'])
        
        # Preparar resultado
        resultado = {
            'success': resultado_sefaz.get('success', False),
            'message': resultado_sefaz.get('message', 'Erro no reenvio'),
            'protocolo': resultado_sefaz.get('protocolo'),
            'chave_acesso': resultado_sefaz.get('chave_acesso')
        }
        
        if resultado['success']:
            print(f"OK: NFe reenviada com sucesso")
            return jsonify({
                'success': True,
                'message': 'NF-e reenviada com sucesso!',
                'protocolo': resultado.get('protocolo'),
                'chave_acesso': resultado.get('chave_acesso')
            })
        else:
            print(f"ERRO: Erro no reenvio: {resultado.get('message')}")
            
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
        print(f"ERRO: Erro no reenvio da NFe: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
@nfe_bp.route('/emitir-rascunho/<int:nfe_id>', methods=['POST'])
@login_required
@editor_or_admin_required()
def emitir_rascunho(nfe_id):
    """Emitir NFe que está em rascunho"""
    db = None
    try:
        print(f"NOTA: Emitindo rascunho NFe ID: {nfe_id}")
        
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
        
        # Converter resultado para dict corretamente
        if hasattr(nfe_result, '_mapping'):
            nfe_data = dict(nfe_result._mapping)
        else:
            nfe_data = dict(nfe_result)
        
        # Verificar se está em rascunho ou processando
        status_upper = nfe_data['status'].upper()
        if status_upper not in ['RASCUNHO', 'PROCESSANDO']:
            return jsonify({
                'success': False,
                'message': f'Apenas rascunhos ou NFes em processamento podem ser emitidos. Status atual: {nfe_data["status"]}'
            }), 400
        
        print(f"OK: Rascunho encontrado")
        
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
        
        print(f" Status atualizado para PROCESSANDO")
        
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
            'inscricao_estadual': emitente_data.inscricao_estadual,
            'regime_tributario_id': emitente_data.regime_tributario_id,  # [?] CRÍTICO para buscar regras tributárias
            'ambiente': emitente_data.ambiente  # Campo ambiente (1=Produção, 2=Homologação - padrão SEFAZ)
        }
        
        # Buscar destinatário - pode estar no form_data ou já armazenado na NFe
        form_data = json_data.get('form_data', {})
        destinatario_id = form_data.get('destinatario')
        destinatario_data = {}
        
        print("="*80)
        print(f"BUSCA DESTINATÁRIO - NFe {nfe_id}")
        print(f"ID no form_data: {destinatario_id}")
        print(f"CPF/CNPJ na NFe: {nfe_data.get('destinatario_cnpj_cpf')}")
        print(f"Cliente ID: {nfe_data['cliente_id']}")
        print("="*80)
        
        # Tentar buscar destinatário pelo ID no form_data
        if destinatario_id:
            try:
                dest_query = text("""
                    SELECT destinatario_id, nome_razao_social, cpf_cnpj, logradouro, numero, 
                           bairro, cep, codigo_municipio, nome_municipio, uf, complemento
                    FROM destinatarios_nfe 
                    WHERE destinatario_id = :dest_id AND cliente_id = :cliente_id
                """)
                dest_result = db.execute(dest_query, {
                    'dest_id': destinatario_id,
                    'cliente_id': nfe_data['cliente_id']
                }).fetchone()
                
                if dest_result:
                    dest_mapping = dest_result._mapping if hasattr(dest_result, '_mapping') else dest_result
                    destinatario_data = {
                        'nome_razao_social': dest_mapping['nome_razao_social'],
                        'cpf_cnpj': dest_mapping['cpf_cnpj'],
                        'logradouro': dest_mapping['logradouro'],
                        'numero': dest_mapping['numero'],
                        'bairro': dest_mapping['bairro'],
                        'cep': dest_mapping['cep'],
                        'codigo_municipio': dest_mapping['codigo_municipio'],
                        'nome_municipio': dest_mapping['nome_municipio'],
                        'uf': dest_mapping['uf'],
                        'complemento': dest_mapping.get('complemento')
                    }
                    print(f"✅ Destinatário encontrado no banco por ID - UF: {dest_mapping['uf']}")
            except Exception as e:
                print(f"❌ ERRO ao buscar destinatário por ID: {e}")
                import traceback
                traceback.print_exc()
        
        # Se não encontrou pelo ID, buscar pelo CPF/CNPJ armazenado na NFe
        if not destinatario_data and nfe_data.get('destinatario_cnpj_cpf'):
            cpf_cnpj_nfe = nfe_data.get('destinatario_cnpj_cpf', '').replace('.', '').replace('-', '').replace('/', '')
            print(f"Buscando pelo CPF/CNPJ: {nfe_data.get('destinatario_cnpj_cpf')} (limpo: {cpf_cnpj_nfe})")
            try:
                dest_query2 = text("""
                    SELECT destinatario_id, nome_razao_social, cpf_cnpj, logradouro, numero, 
                           bairro, cep, codigo_municipio, nome_municipio, uf, complemento
                    FROM destinatarios_nfe 
                    WHERE REPLACE(REPLACE(REPLACE(cpf_cnpj, '.', ''), '-', ''), '/', '') = :cpf_cnpj_limpo 
                    AND cliente_id = :cliente_id
                    LIMIT 1
                """)
                dest_result2 = db.execute(dest_query2, {
                    'cpf_cnpj_limpo': cpf_cnpj_nfe,
                    'cliente_id': nfe_data['cliente_id']
                }).fetchone()
                
                if dest_result2:
                    dest_mapping2 = dest_result2._mapping if hasattr(dest_result2, '_mapping') else dest_result2
                    destinatario_data = {
                        'nome_razao_social': dest_mapping2['nome_razao_social'],
                        'cpf_cnpj': dest_mapping2['cpf_cnpj'],
                        'logradouro': dest_mapping2['logradouro'],
                        'numero': dest_mapping2['numero'],
                        'bairro': dest_mapping2['bairro'],
                        'cep': dest_mapping2['cep'],
                        'codigo_municipio': dest_mapping2['codigo_municipio'],
                        'nome_municipio': dest_mapping2['nome_municipio'],
                        'uf': dest_mapping2['uf'],
                        'complemento': dest_mapping2.get('complemento')
                    }
                    print(f"✅ Destinatário encontrado pelo CPF/CNPJ - UF: {dest_mapping2['uf']}, Município: {dest_mapping2['nome_municipio']}")
                else:
                    print(f"❌ Destinatário NÃO encontrado pelo CPF/CNPJ na base")
                    # Fazer uma query para verificar quantos destinatários existem
                    count_query = text("SELECT COUNT(*) FROM destinatarios_nfe WHERE cliente_id = :cliente_id")
                    count_result = db.execute(count_query, {'cliente_id': nfe_data['cliente_id']}).scalar()
                    print(f"Total de destinatários cadastrados para este cliente: {count_result}")
            except Exception as e:
                print(f"[ERRO] Erro ao buscar destinatário por CPF/CNPJ: {e}", file=sys.stderr)
        
        # Se não encontrou pelo ID ou CPF/CNPJ no banco
        if not destinatario_data:
            print("❌ Destinatário não encontrado no banco de dados")
            
            # Verificar se o CFOP indica operação interestadual
            cfop_primeiro = json_data.get('items', [{}])[0].get('cfop', '5102') if json_data.get('items') else '5102'
            is_interestadual = cfop_primeiro.startswith('6') or cfop_primeiro.startswith('7')
            uf_emitente = emitente_data_for_template.get('uf', 'SP')
            
            print(f"CFOP: {cfop_primeiro}, Interestadual: {is_interestadual}")
            
            # Para operações interestaduais, DEVE ter o destinatário cadastrado
            if is_interestadual:
                return jsonify({
                    'success': False,
                    'message': f'CFOP {cfop_primeiro} indica operação interestadual, mas o destinatário não foi encontrado no banco de dados. CPF/CNPJ na NFe: {nfe_data.get("destinatario_cnpj_cpf")}. Certifique-se de que o destinatário está cadastrado com os dados completos incluindo UF.'
                }), 400
            
            # Para operações internas, pode usar dados básicos da NFe com fallbacks
            print("⚠️ Usando dados básicos da NFe com fallbacks para operação interna")
            destinatario_data = {
                'nome_razao_social': nfe_data.get('destinatario_razao_social'),
                'cpf_cnpj': nfe_data.get('destinatario_cnpj_cpf'),
                'logradouro': form_data.get('dest_logradouro') or 'RUA TESTE',
                'numero': form_data.get('dest_numero') or 'SN',
                'bairro': form_data.get('dest_bairro') or 'CENTRO',
                'cep': form_data.get('dest_cep') or '00000000',
                'codigo_municipio': form_data.get('dest_codigo_municipio') or '3550308',
                'nome_municipio': form_data.get('dest_municipio') or 'SAO PAULO',
                'uf': uf_emitente  # Para operação interna, usa UF do emitente
            }
        
        print(f"[DEBUG] Dados do destinatário final:")
        print(f"[DEBUG] - Nome: {destinatario_data.get('nome_razao_social')}")
        print(f"[DEBUG] - CPF/CNPJ: {destinatario_data.get('cpf_cnpj')}")
        print(f"[DEBUG] - Logradouro: {destinatario_data.get('logradouro')}")
        print(f"[DEBUG] - Município: {destinatario_data.get('nome_municipio')} ({destinatario_data.get('codigo_municipio')})")
        print(f"[DEBUG] - UF: {destinatario_data.get('uf')}")
        
        # Verificar se destinatário foi encontrado
        if not destinatario_data or not destinatario_data.get('nome_razao_social'):
            return jsonify({
                'success': False,
                'message': 'Dados do destinatário não encontrados no rascunho'
            }), 400
        
        # OK: CORREÇÃO: Gerar XML com dados válidos
        ambiente = json_data.get('ambiente', 'homologacao')
        # tpAmb SEFAZ: 1=Produção, 2=Homologação
        tp_amb = 1 if ambiente == 'producao' else 2
        
        print(f"[DEBUG] Gerando XML para emissão de rascunho")
        print(f"[DEBUG] Ambiente: {ambiente} (tpAmb={tp_amb})")
        print(f"[DEBUG] Items: {len(json_data.get('items', []))}")
        
        xml_gerado = generate_nfe_xml(
            json_data.get('form_data', {}),
            emitente_data_for_template,
            destinatario_data,  # OK: AGORA É DICT VÁLIDO
            json_data.get('items', []),
            tp_amb,
            'emitir'
        )
        
        # Log do XML gerado (primeiros 500 caracteres)
        print(f"[DEBUG] XML gerado (início): {xml_gerado[:500]}...")
        
        # Assinar XML - BLOQUEIA SE FALHAR
        try:
            from services.xml_signature_service import xml_signature_service
            xml_assinado = xml_signature_service.sign_nfe_xml(xml_gerado, db, nfe_data['cliente_id'])
            print(f"[OK] XML assinado com sucesso - emissão de rascunho")
        except Exception as e:
            print(f"[X] ERRO CRÍTICO na assinatura (rascunho): {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Erro na assinatura digital: {str(e)}. Verifique se o certificado está válido.'
            }), 400
        
        # Buscar certificado
        certificado = get_active_certificate_for_client(db, nfe_data['cliente_id'])
        if not certificado:
            return jsonify({
                'success': False,
                'message': 'Certificado não encontrado'
            }), 400
        
        print(f"[DEBUG] Enviando para SEFAZ...")
        
        # Enviar para SEFAZ
        resultado_sefaz = nfe_service._processar_envio_sefaz(xml_assinado, certificado, ambiente, nfe_data['cliente_id'])
        
        print(f"[DEBUG] Resultado SEFAZ: {resultado_sefaz}")
        
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
            
            # === ENVIAR EMAIL AUTOMATICAMENTE ===
            try:
                print("📧 [RASCUNHO] Tentando enviar email automático")
                from services.email_service import enviar_nfe_automaticamente
                
                resultado_email = enviar_nfe_automaticamente(nfe_id, db)
                
                if resultado_email.get('success'):
                    print(f"✅ [RASCUNHO] Email enviado com sucesso!")
                else:
                    print(f"⚠️  [RASCUNHO] Email não enviado: {resultado_email.get('message')}")
            except Exception as email_error:
                print(f"❌ [RASCUNHO] Erro ao enviar email: {str(email_error)}")
                # Não bloquear a emissão por causa do email
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
            print(f"OK: Rascunho emitido com sucesso")
            return jsonify({
                'success': True,
                'message': 'NF-e emitida com sucesso!',
                'protocolo': resultado.get('protocolo'),
                'chave_acesso': resultado.get('chave_acesso')
            })
        else:
            print(f"ERRO: Erro na emissão: {resultado.get('message')}")
            
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Erro ao emitir NF-e')
            }), 400
        
    except Exception as e:
        print(f"ERRO: Erro na emissão do rascunho: {e}")
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
@viewer_or_higher_required()
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
        
        print(f" Compartilhando NFe {nfe_id} para {email_destino}")
        
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
                print(f" Incluindo XML...")
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
                        print(f"OK: XML adicionado aos anexos")
                    else:
                        print(f"AVISO: XML content não encontrado")
            
            # DANFE PDF
            if include_danfe:
                print(f" Incluindo DANFE...")
                try:
                    json_nfe = nfe_data.get('json_nfe')
                    if json_nfe:
                        if isinstance(json_nfe, str):
                            json_nfe = json.loads(json_nfe)
                        
                        xml_content = json_nfe.get('xml_content')
                        if xml_content:
                            # Aplicar correção de protocolo se necessário
                            xml_para_danfe = xml_content
                            status = nfe_data.get('status', '').upper()
                            
                            if status == 'AUTORIZADA' and '<protNFe' not in xml_content:
                                print(f"[EMAIL] NFe {nfe_id} autorizada sem protNFe, gerando protocolo com tpAmb=1...")
                                try:
                                    from services.nfe_service import NFeService
                                    nfe_service = NFeService()
                                    resultado_sefaz = {
                                        'chave_acesso': nfe_data.get('chave_acesso'),
                                        'protocolo': nfe_data.get('protocolo_autorizacao') or nfe_data.get('protocolo_sefaz'),
                                        'status': '100',
                                        'digVal': 'N/A',
                                        'ambiente_real': True
                                    }
                                    xml_para_danfe = nfe_service._gerar_xml_protocolo(xml_content, resultado_sefaz)
                                    print(f"[EMAIL] Protocolo gerado com tpAmb=1")
                                except Exception as ex:
                                    print(f"[EMAIL] Erro ao gerar protocolo: {ex}")
                            
                            # OK: CORREÇÃO: Usar caminho absoluto e verificar se existe
                            from services.danfe_service import generate_danfe
                            
                            # Gerar DANFE com XML corrigido
                            pdf_path = generate_danfe(xml_para_danfe, nfe_id)
                            print(f" DANFE path: {pdf_path}")
                            
                            if pdf_path:
                                # Verificar se é caminho absoluto
                                if not os.path.isabs(pdf_path):
                                    # Se for relativo, juntar com o diretório da aplicação
                                    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                    pdf_path = os.path.join(app_root, pdf_path)
                                
                                print(f" Caminho absoluto DANFE: {pdf_path}")
                                
                                if os.path.exists(pdf_path):
                                    with open(pdf_path, 'rb') as pdf_file:
                                        pdf_content = pdf_file.read()
                                        anexos.append({
                                            'nome': f'danfe_{nfe_id}.pdf',
                                            'conteudo': pdf_content,
                                            'tipo': 'application/pdf'
                                        })
                                        print(f"OK: DANFE adicionado aos anexos ({len(pdf_content)} bytes)")
                                else:
                                    print(f"ERRO: Arquivo DANFE não encontrado: {pdf_path}")
                            else:
                                print(f"ERRO: DANFE não foi gerado")
                        else:
                            print(f"AVISO: XML content não disponível para gerar DANFE")
                except Exception as e:
                    print(f"ERRO: Erro ao gerar DANFE para compartilhamento: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continuar sem o DANFE se houver erro
            
            if not anexos:
                return jsonify({
                    'success': False, 
                    'message': 'Nenhum anexo disponível para envio'
                }), 400
            
            print(f" Total de anexos preparados: {len(anexos)}")
            
            # Enviar email com template profissional
            from services.email_service import EmailService, gerar_template_email_nfe
            
            email_service = EmailService()
            
            # Preparar dados do email
            assunto = f'Nota Fiscal Eletrônica #{nfe_data.get("numero", nfe_id)} - {nfe_data.get("cliente_nome", "")}'
            
            # Verificar se data_autorizacao não é None antes do strftime
            data_autorizacao = nfe_data.get('data_autorizacao')
            if data_autorizacao:
                data_autorizacao_str = data_autorizacao.strftime('%d/%m/%Y às %H:%M')
            else:
                data_autorizacao_str = 'N/A'
            
            # Usar o template profissional com logo da EmiteMax
            corpo_html = gerar_template_email_nfe(
                nfe_id=nfe_id,
                numero_nfe=nfe_data.get('numero', nfe_id),
                emitente=nfe_data.get('cliente_nome', 'N/A'),
                destinatario=nfe_data.get('destinatario_razao_social', 'N/A'),
                chave_acesso=nfe_data.get('chave_acesso', 'N/A'),
                protocolo=nfe_data.get('protocolo_sefaz', 'N/A'),
                data_autorizacao=data_autorizacao_str,
                valor_total=nfe_data.get('valor_total', 0),
                anexos=anexos
            )
            
            print(f" Enviando email...")
            
            # Enviar
            resultado = email_service.enviar_email(
                destinatario=email_destino,
                assunto=assunto,
                corpo_html=corpo_html,
                anexos=anexos
            )
            
            print(f" Resultado do envio: {resultado}")
            
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
                    print(f"OK: Log de compartilhamento salvo")
                except Exception as e:
                    print(f"AVISO: Erro ao salvar log de compartilhamento: {e}")            
                
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
            print(f"ERRO: Erro no compartilhamento: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Erro ao preparar compartilhamento: {str(e)}'
            }), 500
        
    except Exception as e:
        print(f"ERRO: Erro geral no compartilhamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    finally:
        db.close()


@nfe_bp.route('/consultar-status/<int:nfe_id>', methods=['POST'])
@login_required
@viewer_or_higher_required()
def consultar_status_sefaz(nfe_id):
    """Consultar status da NFe na SEFAZ"""
    db = next(get_db())
    try:
        # Buscar NFe
        query = text("""
            SELECT n.*, c.cnpj as emitente_cnpj, c.razao_social as emitente_razao
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
        
        chave_acesso = nfe_data.get('chave_acesso')
        if not chave_acesso:
            return jsonify({'success': False, 'message': 'Chave de acesso não encontrada'}), 400
        
        # Consultar na SEFAZ
        from services.nfe_service import NFeService
        nfe_service = NFeService()
        
        # Determinar ambiente
        ambiente = 2  # Homologação por padrão
        if nfe_data.get('json_nfe'):
            json_nfe = nfe_data['json_nfe']
            if isinstance(json_nfe, str):
                import json
                json_nfe = json.loads(json_nfe)
            
            xml_content = json_nfe.get('xml_content', '')
            if '<tpAmb>1</tpAmb>' in xml_content:
                ambiente = 1  # Produção
        
        # Fazer consulta
        try:
            resultado = nfe_service.consultar_nfe(chave_acesso, ambiente)
            
            if resultado.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Consulta realizada com sucesso',
                    'status': resultado.get('status'),
                    'protocolo': resultado.get('protocolo'),
                    'data_autorizacao': resultado.get('data_autorizacao'),
                    'mensagem': resultado.get('motivo') or resultado.get('mensagem', 'Autorizada')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': resultado.get('message', 'Erro na consulta SEFAZ')
                })
        except Exception as e:
            print(f"[ERRO] Erro ao consultar SEFAZ: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Erro ao consultar SEFAZ: {str(e)}'
            }), 500
            
    except Exception as e:
        print(f"[ERRO] Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    finally:
        db.close()@nfe_bp.route('/cancelar/<int:nfe_id>', methods=['POST'])
@login_required
@editor_or_admin_required()
def cancelar_nfe(nfe_id):
    """Cancelar NFe na SEFAZ"""
    db = next(get_db())
    try:
        # Buscar NFe
        query = text("""
            SELECT n.*, c.cnpj as emitente_cnpj, c.razao_social as emitente_razao
            FROM nfe_emitidas n
            JOIN clientes c ON n.cliente_id = c.cliente_id
            WHERE n.nfe_emitida_id = :nfe_id
        """)
        result = db.execute(query, {'nfe_id': nfe_id})
        nfe = result.first()
        
        if not nfe:
            return jsonify({'success': False, 'message': 'NFe não encontrada'}), 404
        
        nfe_data = dict(nfe._mapping)
        
        # Validações
        if nfe_data.get('status', '').upper() != 'AUTORIZADA':
            return jsonify({'success': False, 'message': 'Apenas NFes autorizadas podem ser canceladas'}), 400
        
        chave_acesso = nfe_data.get('chave_acesso')
        if not chave_acesso or len(chave_acesso) != 44:
            return jsonify({'success': False, 'message': 'Chave de acesso inválida'}), 400
        
        protocolo = nfe_data.get('protocolo_autorizacao') or nfe_data.get('protocolo_sefaz')
        if not protocolo:
            return jsonify({'success': False, 'message': 'Protocolo não encontrado'}), 400
        
        # Verificar prazo de 24h
        from datetime import datetime, timedelta
        data_emissao = nfe_data.get('data_emissao')
        if data_emissao:
            if isinstance(data_emissao, str):
                data_emissao = datetime.fromisoformat(data_emissao.replace('Z', '+00:00'))
            if datetime.now() - data_emissao > timedelta(hours=24):
                return jsonify({'success': False, 'message': 'Prazo de cancelamento expirado (24 horas)'}), 400
        
        # Obter justificativa
        data = request.get_json()
        justificativa = data.get('justificativa', '').strip()
        
        if not justificativa or len(justificativa) < 15:
            return jsonify({'success': False, 'message': 'Justificativa deve ter no mínimo 15 caracteres'}), 400
        
        # Determinar ambiente
        ambiente = 'producao'
        if nfe_data.get('json_nfe'):
            json_nfe = nfe_data['json_nfe']
            if isinstance(json_nfe, str):
                import json
                json_nfe = json.loads(json_nfe)
            xml_content = json_nfe.get('xml_content', '')
            if '<tpAmb>2</tpAmb>' in xml_content:
                ambiente = 'homologacao'
        
        # Obter certificado
        from services.certificate_service import get_active_certificate_for_client
        certificado = get_active_certificate_for_client(db, nfe_data['cliente_id'])
        
        if not certificado:
            return jsonify({'success': False, 'message': 'Certificado não encontrado'}), 400
        
        # Cancelar na SEFAZ
        from services.sefaz_service import SefazService
        
        sefaz = SefazService(
            ambiente=ambiente,
            cert_path=certificado.get('cert_path'),
            key_path=certificado.get('key_path')
        )
        
        resultado = sefaz.cancelar_nfe(
            chave_nfe=chave_acesso,
            protocolo=protocolo,
            justificativa=justificativa,
            cnpj_emitente=nfe_data['emitente_cnpj']
        )
        
        if resultado.get('success'):
            # Atualizar no banco
            update_query = text("""
                UPDATE nfe_emitidas 
                SET status = 'CANCELADA',
                    protocolo_cancelamento = :protocolo,
                    data_cancelamento = :data_cancelamento,
                    justificativa_cancelamento = :justificativa
                WHERE nfe_emitida_id = :nfe_id
            """)
            db.execute(update_query, {
                'protocolo': resultado.get('protocolo'),
                'data_cancelamento': datetime.now(),
                'justificativa': justificativa,
                'nfe_id': nfe_id
            })
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'NFe cancelada com sucesso na SEFAZ',
                'protocolo': resultado.get('protocolo'),
                'data_cancelamento': resultado.get('data_cancelamento')
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Erro ao cancelar na SEFAZ')
            })
            
    except Exception as e:
        db.rollback()
        print(f"[ERRO] Erro ao cancelar NFe: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao cancelar: {str(e)}'
        }), 500
    finally:
        db.close()


# ===== STATUS DE CONTINGÊNCIA =====
@nfe_bp.route('/contingencia/status', methods=['GET'])
@login_required
@viewer_or_higher_required()
def status_contingencia():
    """Consulta status de contingência do sistema"""
    try:
        from services.contingencia_service import contingencia_service
        status = contingencia_service.obter_status_geral()
        return jsonify({'success': True, **status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== INUTILIZAÇÃO DE NUMERAÇÃO =====
@nfe_bp.route('/inutilizar/form', methods=['GET'])
@login_required
@viewer_or_higher_required()
def form_inutilizar():
    """Formulário para inutilização de numeração"""
    try:
        cliente_id = request.args.get('cliente_id', type=int)
        
        if not cliente_id:
            flash('Cliente não especificado', 'danger')
            return redirect(url_for('nfe.list_nfes'))
        
        # Verificar acesso do usuário ao cliente
        db = next(get_db())
        accessible_clients = get_accessible_client_ids(db)
        
        if cliente_id not in accessible_clients:
            flash('Você não tem acesso a este cliente.', 'danger')
            return redirect(url_for('nfe.list_nfes'))
        
        # Buscar dados do cliente/emitente
        from database.models import Cliente
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        
        if not cliente:
            flash('Cliente não encontrado', 'danger')
            return redirect(url_for('nfe.list_nfes'))
        
        # Buscar último número emitido por série
        from database.models import NFeEmitidas
        ultimas_nfes = db.query(
            NFeEmitidas.serie,
            NFeEmitidas.modelo,
            func.max(NFeEmitidas.numero).label('ultimo_numero')
        ).filter(
            NFeEmitidas.cliente_id == cliente_id,
            NFeEmitidas.status == 'AUTORIZADA'
        ).group_by(
            NFeEmitidas.serie,
            NFeEmitidas.modelo
        ).all()
        
        series_info = []
        for serie, modelo, ultimo_num in ultimas_nfes:
            modelo_desc = 'NFe' if modelo == '55' else 'NFCe'
            series_info.append({
                'serie': serie,
                'modelo': modelo,
                'modelo_desc': modelo_desc,
                'ultimo_numero': ultimo_num,
                'sugestao_inicial': ultimo_num + 1 if ultimo_num else 1
            })
        
        db.close()
        
        return render_template('admin/nfes/inutilizar.html',
                             cliente=cliente,
                             series_info=series_info,
                             cliente_id=cliente_id)
                             
    except Exception as e:
        print(f"[ERRO] Erro ao carregar formulário de inutilização: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao carregar formulário: {str(e)}', 'danger')
        return redirect(url_for('nfe.list_nfes'))


@nfe_bp.route('/inutilizar', methods=['POST'])
@login_required
@editor_or_admin_required()
def processar_inutilizacao():
    """Processa inutilização de numeração na SEFAZ"""
    db = None
    try:
        # Obter dados do formulário
        cliente_id = request.form.get('cliente_id', type=int)
        modelo = request.form.get('modelo')  # 55 ou 65
        serie = request.form.get('serie', type=int)
        numero_inicial = request.form.get('numero_inicial', type=int)
        numero_final = request.form.get('numero_final', type=int)
        ano = request.form.get('ano')  # 2 dígitos
        justificativa = request.form.get('justificativa', '').strip()
        
        print(f"[INUTILIZAR] Requisição recebida:")
        print(f"  Cliente: {cliente_id}")
        print(f"  Modelo: {modelo}, Série: {serie}")
        print(f"  Números: {numero_inicial} a {numero_final}")
        print(f"  Ano: {ano}")
        print(f"  Justificativa: {justificativa[:50]}...")
        
        # Validações
        if not all([cliente_id, modelo, serie is not None, numero_inicial, numero_final, ano, justificativa]):
            return jsonify({
                'success': False,
                'message': 'Todos os campos são obrigatórios'
            }), 400
        
        if len(justificativa) < 15:
            return jsonify({
                'success': False,
                'message': 'Justificativa deve ter no mínimo 15 caracteres'
            }), 400
        
        if numero_final < numero_inicial:
            return jsonify({
                'success': False,
                'message': 'Número final deve ser maior ou igual ao número inicial'
            }), 400
        
        if modelo not in ['55', '65']:
            return jsonify({
                'success': False,
                'message': 'Modelo inválido (deve ser 55 ou 65)'
            }), 400
        
        # Abrir conexão com banco
        db = next(get_db())
        
        # Verificar acesso do usuário ao cliente
        accessible_clients = get_accessible_client_ids(db)
        if cliente_id not in accessible_clients:
            return jsonify({
                'success': False,
                'message': 'Você não tem acesso a este cliente'
            }), 403
        
        # Obter ID do usuário logado
        user_id = current_user.id
        
        # Buscar cliente/emitente
        from database.models import Cliente
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        
        if not cliente:
            return jsonify({
                'success': False,
                'message': 'Cliente não encontrado'
            }), 404
        
        # Obter CNPJ do emitente
        cnpj_emitente = cliente.cnpj
        
        # Obter certificado digital
        from services.certificate_service import get_active_certificate_for_client
        certificado = get_active_certificate_for_client(db, cliente_id)
        
        if not certificado or certificado.get('modo_simulado'):
            return jsonify({
                'success': False,
                'message': 'Certificado digital não configurado ou em modo simulado'
            }), 400
        
        # Determinar ambiente (1=Produção, 2=Homologação)
        ambiente = 'producao' if cliente.ambiente == 1 else 'homologacao'
        
        # Extrair certificado em arquivos temporários
        import tempfile
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.serialization import pkcs12
        
        cert_data = certificado['cert_data']
        password = certificado['password'].encode('utf-8')
        
        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            cert_data, password
        )
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as cert_file:
            cert_file.write(certificate.public_bytes(serialization.Encoding.PEM))
            cert_path = cert_file.name
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_file:
            key_file.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            key_path = key_file.name
        
        try:
            # Inicializar serviço SEFAZ
            from services.sefaz_service import SefazService
            sefaz = SefazService(
                ambiente=ambiente, 
                cert_path=cert_path, 
                key_path=key_path,
                cert_pfx_data=cert_data,  # Manter dados originais para assinatura
                cert_pfx_password=certificado['password']
            )
            
            # Enviar inutilização para SEFAZ
            resultado = sefaz.inutilizar_numeracao(
                cnpj_emitente=cnpj_emitente,
                modelo=modelo,
                serie=serie,
                numero_inicial=numero_inicial,
                numero_final=numero_final,
                ano=ano,
                justificativa=justificativa
            )
            
            print(f"[INUTILIZAR] Resultado SEFAZ: {resultado.get('status')}")
            
            # Normalizar status para valores válidos do banco
            # Constraint aceita: 'PROCESSANDO', 'AUTORIZADA', 'REJEITADA', 'ERRO'
            status_sefaz = resultado.get('status', 'ERRO')
            if status_sefaz not in ['PROCESSANDO', 'AUTORIZADA', 'REJEITADA']:
                status_sefaz = 'ERRO'
            
            # Salvar no banco
            inutilizacao = NFeInutilizacao(
                cliente_id=cliente_id,
                modelo=modelo,
                serie=serie,
                numero_inicial=numero_inicial,
                numero_final=numero_final,
                ano=ano,
                justificativa=justificativa,
                status=status_sefaz,
                protocolo=resultado.get('protocolo'),
                chave_inutilizacao=resultado.get('chave_inutilizacao'),
                codigo_status=resultado.get('codigo'),
                mensagem_sefaz=resultado.get('mensagem'),
                xml_pedido=resultado.get('xml_pedido'),
                xml_resposta=resultado.get('xml_resposta'),
                data_inutilizacao=datetime.now() if resultado.get('success') else None,
                created_by_user_id=user_id
            )
            
            db.add(inutilizacao)
            db.commit()
            
            print(f"[INUTILIZAR] Registro salvo no banco: ID {inutilizacao.inutilizacao_id}")
            
            if resultado.get('success'):
                return jsonify({
                    'success': True,
                    'message': f'Numeração inutilizada com sucesso!',
                    'protocolo': resultado.get('protocolo'),
                    'codigo': resultado.get('codigo'),
                    'inutilizacao_id': inutilizacao.inutilizacao_id
                })
            else:
                return jsonify({
                    'success': False,
                    'message': resultado.get('mensagem', 'Erro ao inutilizar na SEFAZ'),
                    'codigo': resultado.get('codigo')
                })
                
        finally:
            # Limpar arquivos temporários
            import os
            try:
                os.unlink(cert_path)
                os.unlink(key_path)
            except:
                pass
                
    except Exception as e:
        if db:
            db.rollback()
        print(f"[ERRO] Erro ao processar inutilização: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao processar: {str(e)}'
        }), 500
    finally:
        if db:
            db.close()


@nfe_bp.route('/inutilizacoes', methods=['GET'])
@login_required
@viewer_or_higher_required()
def listar_inutilizacoes():
    """Lista inutilizações de numeração"""
    try:
        cliente_id = request.args.get('cliente_id', type=int)
        
        if not cliente_id:
            flash('Cliente não especificado', 'danger')
            return redirect(url_for('nfe.list_nfes'))
        
        db = next(get_db())
        
        # Verificar acesso do usuário ao cliente
        accessible_clients = get_accessible_client_ids(db)
        if cliente_id not in accessible_clients:
            flash('Você não tem acesso a este cliente.', 'danger')
            return redirect(url_for('nfe.list_nfes'))
        
        # Buscar inutilizações
        inutilizacoes = db.query(NFeInutilizacao).options(
            joinedload(NFeInutilizacao.created_by_user)
        ).filter(
            NFeInutilizacao.cliente_id == cliente_id
        ).order_by(
            NFeInutilizacao.data_criacao.desc()
        ).all()
        
        # Estatísticas
        stats = {
            'autorizadas': db.query(func.count(NFeInutilizacao.inutilizacao_id)).filter(
                NFeInutilizacao.cliente_id == cliente_id,
                NFeInutilizacao.status == 'AUTORIZADA'
            ).scalar(),
            'rejeitadas': db.query(func.count(NFeInutilizacao.inutilizacao_id)).filter(
                NFeInutilizacao.cliente_id == cliente_id,
                NFeInutilizacao.status == 'REJEITADA'
            ).scalar(),
            'processando': db.query(func.count(NFeInutilizacao.inutilizacao_id)).filter(
                NFeInutilizacao.cliente_id == cliente_id,
                NFeInutilizacao.status == 'PROCESSANDO'
            ).scalar()
        }
        
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        
        db.close()
        
        return render_template('admin/nfes/listar_inutilizacoes.html',
                             inutilizacoes=inutilizacoes,
                             cliente=cliente,
                             cliente_id=cliente_id,
                             stats=stats)
                             
    except Exception as e:
        print(f"[ERRO] Erro ao listar inutilizações: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao listar: {str(e)}', 'danger')
        return redirect(url_for('nfe.list_nfes'))


@nfe_bp.route('/inutilizacao/<int:inutilizacao_id>/detalhes', methods=['GET'])
@login_required
@viewer_or_higher_required()
def detalhes_inutilizacao(inutilizacao_id):
    """Retorna detalhes de uma inutilização em JSON"""
    try:
        db = next(get_db())
        
        inut = db.query(NFeInutilizacao).options(
            joinedload(NFeInutilizacao.created_by_user)
        ).filter_by(
            inutilizacao_id=inutilizacao_id
        ).first()
        
        if not inut:
            db.close()
            return jsonify({'success': False, 'message': 'Inutilização não encontrada'}), 404
        
        # Verificar permissões
        accessible_clients = get_accessible_client_ids(db)
        if inut.cliente_id not in accessible_clients:
            db.close()
            return jsonify({'success': False, 'message': 'Sem permissão'}), 403
        
        # Montar resposta
        data = {
            'success': True,
            'inutilizacao': {
                'inutilizacao_id': inut.inutilizacao_id,
                'modelo': inut.modelo,
                'serie': inut.serie,
                'numero_inicial': inut.numero_inicial,
                'numero_final': inut.numero_final,
                'ano': inut.ano,
                'justificativa': inut.justificativa,
                'status': inut.status,
                'protocolo': inut.protocolo,
                'chave_inutilizacao': inut.chave_inutilizacao,
                'codigo_status': inut.codigo_status,
                'mensagem_sefaz': inut.mensagem_sefaz,
                'data_criacao': inut.data_criacao.strftime('%d/%m/%Y %H:%M:%S') if inut.data_criacao else None,
                'created_by_user': inut.created_by_user.username if inut.created_by_user else None
            }
        }
        
        db.close()
        return jsonify(data)
        
    except Exception as e:
        print(f"[ERRO] Erro ao buscar detalhes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@nfe_bp.route('/inutilizacao/<int:inutilizacao_id>/xml/<tipo>', methods=['GET'])
@login_required
@viewer_or_higher_required()
def download_xml_inutilizacao(inutilizacao_id, tipo):
    """Baixa XML de pedido ou resposta da inutilização"""
    try:
        db = next(get_db())
        
        inut = db.query(NFeInutilizacao).filter_by(
            inutilizacao_id=inutilizacao_id
        ).first()
        
        if not inut:
            db.close()
            flash('Inutilização não encontrada', 'danger')
            return redirect(url_for('nfe.list_nfes'))
        
        # Verificar permissões
        accessible_clients = get_accessible_client_ids(db)
        if inut.cliente_id not in accessible_clients:
            db.close()
            flash('Sem permissão para acessar', 'danger')
            return redirect(url_for('nfe.list_nfes'))
        
        # Selecionar XML
        if tipo == 'pedido':
            xml_content = inut.xml_pedido
            filename = f'inut_pedido_{inut.inutilizacao_id}.xml'
        elif tipo == 'resposta':
            xml_content = inut.xml_resposta
            filename = f'inut_resposta_{inut.inutilizacao_id}.xml'
        else:
            db.close()
            flash('Tipo de XML inválido', 'danger')
            return redirect(url_for('nfe.list_nfes'))
        
        if not xml_content:
            db.close()
            flash(f'XML de {tipo} não disponível', 'warning')
            return redirect(url_for('nfe.listar_inutilizacoes', cliente_id=inut.cliente_id))
        
        db.close()
        
        # Retornar XML
        from flask import Response
        return Response(
            xml_content,
            mimetype='application/xml',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
    except Exception as e:
        print(f"[ERRO] Erro ao baixar XML: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao baixar XML: {str(e)}', 'danger')
        return redirect(url_for('nfe.list_nfes'))



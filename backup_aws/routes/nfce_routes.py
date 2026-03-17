"""
Rotas para NFC-e (Nota Fiscal de Consumidor Eletrônica)
"""

from flask import Blueprint, jsonify, request, render_template, redirect, session, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from datetime import datetime
from typing import Dict, Any

from database.connection import get_db
from database.models import Cliente, Produto, NFeEmitidas, Cfop, Csticms, Csosnicms, Ncm
from auth.decorators import permission_required
from auth.permissions import get_accessible_client_ids
from services.certificate_service import get_active_certificate_for_client
from utils.nfce_generator import gerar_xml_nfce, gerar_qrcode_nfce, gerar_chave_acesso_nfce
from utils.helpers import get_uf_ibge_code

# Funções stub temporárias até implementação real com SEFAZ
def enviar_nfce_sefaz(xml_assinado: str, emitente: Any, certificado: Any) -> Dict[str, Any]:
    """
    Modo de teste - Simula autorização da SEFAZ
    TODO: Implementar comunicação real com SEFAZ em produção
    """
    import random
    from datetime import datetime
    
    # Gerar número aleatório para teste
    numero = random.randint(1, 999999)
    
    # Extrair chave de acesso do XML ou gerar uma
    chave_match = xml_assinado.find('Id="NFe')
    if chave_match != -1:
        chave_start = chave_match + 8
        chave_acesso = xml_assinado[chave_start:chave_start + 44]
    else:
        # Gerar chave fake para teste
        uf = emitente.get('uf_codigo', 35)
        cnpj = ''.join(filter(str.isdigit, emitente.get('cnpj', '00000000000000')))
        chave_acesso = f"{uf}{datetime.now().strftime('%y%m')}{cnpj}65001{numero:09d}1{'0'*8}0"
    
    return {
        'sucesso': True,
        'chave_acesso': chave_acesso,
        'numero': numero,
        'serie': 1,
        'protocolo': f'TEST{random.randint(100000, 999999)}',
        'ambiente': 2,  # Homologação
        'data_autorizacao': datetime.now().isoformat(),
        'url_consulta': 'https://www.fazenda.sp.gov.br/nfce/consulta'
    }

def assinar_xml_nfce(xml: str, certificado: Any) -> str:
    """Stub temporário - implementar assinatura digital"""
    return xml  # Retorna XML sem assinatura (apenas para testes)

def consultar_nfce(chave_acesso: str, ambiente: str = 'homologacao') -> Dict[str, Any]:
    """Stub temporário - implementar consulta SEFAZ"""
    return {'sucesso': False, 'erro': 'Consulta não implementada'}

def cancelar_nfce(chave_acesso: str, justificativa: str, emitente: Any, certificado: Any) -> Dict[str, Any]:
    """
    Modo de teste - Simula cancelamento da SEFAZ
    TODO: Implementar comunicação real com SEFAZ em produção
    """
    import random
    from datetime import datetime
    
    # Simular sucesso em modo de teste
    return {
        'sucesso': True,
        'protocolo': f'CANCEL{random.randint(100000, 999999)}',
        'data_cancelamento': datetime.now().isoformat(),
        'mensagem': f'Cancelamento simulado - Homologação. Justificativa: {justificativa[:50]}...'
    }

def gerar_qrcode(chave_acesso: str, url_consulta: str = '') -> str:
    """Wrapper para gerar_qrcode_nfce"""
    resultado = gerar_qrcode_nfce(chave_acesso, url_consulta or 'https://nfce.fazenda.gov.br')
    return resultado.get('base64', '')
from utils.nfce_validators import validar_dados_nfce
from utils.helpers import produto_to_dict_for_template

nfce_bp = Blueprint('nfce', __name__, url_prefix='/admin/nfce')


@nfce_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue')
def emitir_nfce():
    """Emitir NFC-e"""
    db = next(get_db())
    
    try:
        # Buscar clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Determinar cliente emitente
        emitente_cliente_id = None
        cliente_id_from_url = request.args.get('cliente_id')
        
        if cliente_id_from_url:
            try:
                emitente_cliente_id = int(cliente_id_from_url)
                if emitente_cliente_id not in accessible_clients:
                    flash('Você não tem acesso a este cliente.', 'danger')
                    return redirect(url_for('home.home'))
                # Salvar na sessão para próximas operações
                session['current_client_id'] = emitente_cliente_id
            except ValueError:
                flash('ID do cliente inválido', 'danger')
                return redirect(url_for('home.home'))
        else:
            # Se não passou cliente_id, tentar usar o da sessão
            if session.get('current_client_id') and session.get('current_client_id') in accessible_clients:
                emitente_cliente_id = session.get('current_client_id')
            elif len(accessible_clients) == 1:
                # Se tem apenas 1 cliente, usar automaticamente
                emitente_cliente_id = accessible_clients[0]
                session['current_client_id'] = emitente_cliente_id
            else:
                # Múltiplos clientes e sem cliente na sessão - mostrar seletor apenas no GET
                if request.method == 'GET':
                    clientes = db.query(Cliente).filter(
                        Cliente.cliente_id.in_(accessible_clients)
                    ).all()
                    return render_template('admin/nfce/selecionar_cliente.html', clientes=clientes)
                else:
                    # No POST sem cliente definido, usar o primeiro como fallback
                    emitente_cliente_id = accessible_clients[0]
        
        # Buscar dados do emitente
        emitente_data = db.query(Cliente).filter_by(cliente_id=emitente_cliente_id).first()
        if not emitente_data:
            flash('Cliente não encontrado', 'danger')
            return redirect(url_for('home.home'))
        
        if request.method == 'POST':
            try:
                # Capturar dados do formulário
                dados_nfce = {
                    'emitente_id': emitente_cliente_id,
                    'produtos': [],
                    'forma_pagamento': request.form.get('forma_pagamento', '01'),  # 01=Dinheiro
                    'valor_pago': float(request.form.get('valor_pago', 0)),
                    'troco': float(request.form.get('troco', 0)),
                    'informacoes_adicionais': request.form.get('informacoes_adicionais', ''),
                    'destinatario': {}  # NFC-e não exige destinatário
                }
                
                # Destinatário (opcional para NFC-e)
                cpf_cnpj = request.form.get('destinatario_cpf_cnpj', '').strip()
                if cpf_cnpj:
                    dados_nfce['destinatario'] = {
                        'cpf_cnpj': cpf_cnpj,
                        'nome': request.form.get('destinatario_nome', ''),
                        'email': request.form.get('destinatario_email', '')
                    }
                
                # Produtos
                produtos_json = request.form.get('produtos_json', '[]')
                import json
                produtos = json.loads(produtos_json)
                
                for prod in produtos:
                    produto_db = db.query(Produto).filter_by(
                        produto_id=prod['produto_id'],
                        cliente_id=emitente_cliente_id
                    ).first()
                    
                    if not produto_db:
                        flash(f'Produto {prod["produto_id"]} não encontrado', 'danger')
                        return redirect(url_for('nfce.emitir_nfce', cliente_id=emitente_cliente_id))
                    
                    dados_nfce['produtos'].append({
                        'produto': produto_db,
                        'quantidade': float(prod['quantidade']),
                        'valor_unitario': float(prod['valor_unitario']),
                        'desconto': float(prod.get('desconto', 0))
                    })
                
                # Validar dados
                erros = validar_dados_nfce(dados_nfce)
                if erros:
                    for erro in erros:
                        flash(erro, 'danger')
                    return redirect(url_for('nfce.emitir_nfce', cliente_id=emitente_cliente_id))
                
                # Preparar dados do emitente (converter Cliente object para dict)
                emitente_dict = {
                    'cnpj': emitente_data.cnpj,
                    'razao_social': emitente_data.razao_social,
                    'nome_fantasia': emitente_data.nome_fantasia or emitente_data.razao_social,
                    'inscricao_estadual': emitente_data.inscricao_estadual,
                    'regime_tributario': emitente_data.regime_tributario_id,
                    'logradouro': emitente_data.logradouro,
                    'numero': emitente_data.numero,
                    'complemento': emitente_data.complemento,
                    'bairro': emitente_data.bairro,
                    'codigo_municipio': emitente_data.codigo_municipio,
                    'municipio': emitente_data.nome_municipio,
                    'uf': emitente_data.uf,
                    'uf_codigo': get_uf_ibge_code(emitente_data.uf),
                    'cep': emitente_data.cep
                }
                
                # Preparar itens (converter produtos para formato XML)
                itens = []
                for prod in dados_nfce['produtos']:
                    produto_obj = prod['produto']
                    itens.append({
                        'codigo': produto_obj.codigo_interno or str(produto_obj.produto_id),
                        'descricao': produto_obj.descricao,
                        'ncm': produto_obj.ncm.codigo if produto_obj.ncm else '00000000',
                        'cfop': produto_obj.cfop.cfop if produto_obj.cfop else '5102',
                        'unidade': produto_obj.unidade_comercial or 'UN',
                        'quantidade': prod['quantidade'],
                        'valor_unitario': prod['valor_unitario'],
                        'valor_total': prod['quantidade'] * prod['valor_unitario'] - prod.get('desconto', 0),
                        'csosn': '102',  # TODO: pegar da regra tributária do produto
                        'origem': '0'  # TODO: pegar do produto
                    })
                
                # Calcular totais
                valor_produtos = sum(item['valor_total'] for item in itens)
                valor_desconto = sum(prod.get('desconto', 0) for prod in dados_nfce['produtos'])
                valor_total = valor_produtos
                
                # Gerar XML (adaptar estrutura de dados)
                dados_xml = {
                    'emitente': emitente_dict,
                    'nfce_info': {
                        'numero': 1,  # TODO: buscar próximo número
                        'serie': 1,
                        'modelo': '65',
                        'tipo_emissao': '1',  # Normal
                        'finalidade': '1',  # NF-e normal
                        'destino_operacao': '1',  # Interna
                        'tipo_impressao': '4',  # DANFE NFC-e
                        'ambiente': '2'  # Homologação
                    },
                    'itens': itens,
                    'destinatario': dados_nfce.get('destinatario'),
                    'totais': {
                        'valor_produtos': valor_produtos,
                        'valor_desconto': valor_desconto,
                        'valor_total': valor_total,
                        'base_calculo': 0,
                        'valor_icms': 0
                    },
                    'pagamento': {
                        'forma_pagamento': dados_nfce['forma_pagamento'],
                        'valor': valor_total
                    }
                }
                xml_nfce = gerar_xml_nfce(dados_xml)
                
                # Buscar certificado
                certificado = get_active_certificate_for_client(db, emitente_cliente_id)
                if not certificado:
                    flash('Nenhum certificado ativo encontrado para este cliente', 'danger')
                    return redirect(url_for('nfce.emitir_nfce', cliente_id=emitente_cliente_id))
                
                # Assinar XML
                xml_assinado = assinar_xml_nfce(xml_nfce, certificado)
                
                # Enviar para SEFAZ
                resultado = enviar_nfce_sefaz(xml_assinado, emitente_dict, certificado)
                
                if resultado['sucesso']:
                    # Gerar QR Code
                    chave_acesso = resultado['chave_acesso']
                    qrcode_base64 = gerar_qrcode(chave_acesso, resultado.get('url_consulta', ''))
                    qrcode_url = f"data:image/png;base64,{qrcode_base64}" if qrcode_base64 else None
                    
                    # Preparar dados completos para JSON (serializar objetos SQLAlchemy)
                    dados_nfce_json = {
                        'emitente_id': dados_nfce['emitente_id'],
                        'forma_pagamento': dados_nfce['forma_pagamento'],
                        'valor_pago': dados_nfce['valor_pago'],
                        'troco': dados_nfce['troco'],
                        'informacoes_adicionais': dados_nfce.get('informacoes_adicionais', ''),
                        'destinatario': dados_nfce.get('destinatario', {}),
                        'produtos': [
                            {
                                'produto_id': p['produto'].produto_id,
                                'descricao': p['produto'].descricao,
                                'quantidade': p['quantidade'],
                                'valor_unitario': p['valor_unitario'],
                                'desconto': p.get('desconto', 0)
                            }
                            for p in dados_nfce['produtos']
                        ],
                        'totais': {
                            'valor_produtos': valor_produtos,
                            'valor_desconto': valor_desconto,
                            'valor_total': valor_total
                        },
                        # Dados da emissão
                        'numero': resultado['numero'],
                        'serie': resultado.get('serie', 1),
                        'modelo': '65',
                        'xml_content': xml_assinado,
                        'qrcode_url': qrcode_url,
                        'ambiente': resultado.get('ambiente', 2),
                        'protocolo': resultado.get('protocolo', ''),
                        'url_consulta': resultado.get('url_consulta', '')
                    }
                    
                    # Extrair dados do destinatário
                    destinatario = dados_nfce.get('destinatario', {})
                    dest_razao = destinatario.get('nome', '') if destinatario else ''
                    dest_cpf_cnpj = destinatario.get('cpf_cnpj', '') if destinatario else ''
                    
                    # Salvar no banco usando campos existentes
                    nfce = NFeEmitidas(
                        cliente_id=emitente_cliente_id,
                        tipo_nfe='1',  # 1=Saída
                        modelo='65',  # 65=NFCe
                        finalidade_emissao=1,  # 1=NF-e normal
                        natureza_operacao='Venda',
                        informacoes_adicionais=dados_nfce.get('informacoes_adicionais', ''),
                        destinatario_razao_social=dest_razao or 'Consumidor Final',
                        destinatario_cnpj_cpf=dest_cpf_cnpj,
                        json_nfe=json.dumps(dados_nfce_json),
                        chave_acesso=chave_acesso,
                        protocolo_sefaz=resultado.get('protocolo', ''),
                        status='Autorizada',
                        data_criacao=datetime.now(),
                        data_autorizacao=datetime.now(),
                        mensagem_sefaz=f"Emitida em ambiente de homologação - Número: {resultado['numero']}"
                    )
                    db.add(nfce)
                    db.commit()
                    
                    # Mensagem de sucesso com informações detalhadas
                    flash(f'[OK] NFC-e #{resultado["numero"]} emitida com sucesso em AMBIENTE DE HOMOLOGAÇÃO!', 'success')
                    flash(f'Chave de Acesso: {chave_acesso}', 'info')
                    flash(f'Protocolo: {resultado["protocolo"]}', 'info')
                    
                    return redirect(url_for('nfce.consultar_nfce', nfce_id=nfce.nfe_emitida_id))
                else:
                    flash(f'Erro ao emitir NFC-e: {resultado.get("erro", "Erro desconhecido")}', 'danger')
                    return redirect(url_for('nfce.emitir_nfce', cliente_id=emitente_cliente_id))
                    
            except Exception as e:
                db.rollback()
                flash(f'Erro ao processar NFC-e: {str(e)}', 'danger')
                return redirect(url_for('nfce.emitir_nfce', cliente_id=emitente_cliente_id))
        
        # GET - Renderizar formulário
        # Buscar produtos do emitente
        produtos = db.query(Produto).filter_by(
            cliente_id=emitente_cliente_id,
            ativo=True
        ).all()
        
        produtos_dict = [produto_to_dict_for_template(p) for p in produtos]
        
        # Buscar CFOPs de venda
        cfops = db.query(Cfop).filter(
            Cfop.cfop.in_(['5102', '5405', '6102', '6404'])  # Vendas dentro/fora do estado
        ).all()
        
        return render_template(
            'admin/nfce/emitir.html',
            emitente=emitente_data,
            produtos=produtos_dict,
            cfops=cfops,
            accessible_clients=accessible_clients
        )
        
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
    finally:
        db.close()


@nfce_bp.route('/list')
@login_required
@permission_required('nfe.view')
def listar_nfce():
    """Listar NFC-e emitidas"""
    db = next(get_db())
    
    try:
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Filtros
        cliente_id = request.args.get('cliente_id', type=int)
        if cliente_id and cliente_id not in accessible_clients:
            flash('Acesso negado a este cliente', 'danger')
            return redirect(url_for('nfce.listar_nfce'))
        
        # Query
        query = db.query(NFeEmitidas).filter(
            NFeEmitidas.cliente_id.in_(accessible_clients),
            NFeEmitidas.modelo == '65'  # NFC-e
        )
        
        if cliente_id:
            query = query.filter(NFeEmitidas.cliente_id == cliente_id)
        
        # Filtro por período
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        if data_inicio:
            query = query.filter(NFeEmitidas.data_criacao >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(NFeEmitidas.data_criacao <= datetime.strptime(data_fim, '%Y-%m-%d'))
        
        # Ordenar
        nfces = query.order_by(NFeEmitidas.data_criacao.desc()).all()
        
        # Buscar clientes para filtro
        clientes = db.query(Cliente).filter(
            Cliente.cliente_id.in_(accessible_clients)
        ).all()
        
        return render_template(
            'admin/nfce/list.html',
            nfces=nfces,
            clientes=clientes,
            filtros={
                'cliente_id': cliente_id,
                'data_inicio': data_inicio,
                'data_fim': data_fim
            }
        )
        
    except Exception as e:
        flash(f'Erro ao listar NFC-e: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
    finally:
        db.close()


@nfce_bp.route('/consultar/<int:nfce_id>')
@login_required
@permission_required('nfe.view')
def consultar_nfce(nfce_id: int):
    """Consultar NFC-e específica"""
    db = next(get_db())
    
    try:
        accessible_clients = get_accessible_client_ids(db)
        
        nfce = db.query(NFeEmitidas).filter(
            NFeEmitidas.nfe_emitida_id == nfce_id,
            NFeEmitidas.cliente_id.in_(accessible_clients),
            NFeEmitidas.modelo == '65'
        ).first()
        
        if not nfce:
            flash('NFC-e não encontrada', 'danger')
            return redirect(url_for('nfce.listar_nfce'))
        
        # Buscar dados do emitente
        emitente = db.query(Cliente).filter_by(cliente_id=nfce.cliente_id).first()
        
        # Parse JSON
        import json
        dados_nfce = json.loads(nfce.json_nfe) if getattr(nfce, 'json_nfe', None) else {}
        
        return render_template(
            'admin/nfce/consultar.html',
            nfce=nfce,
            emitente=emitente,
            dados=dados_nfce
        )
        
    except Exception as e:
        flash(f'Erro ao consultar NFC-e: {str(e)}', 'danger')
        return redirect(url_for('nfce.listar_nfce'))
    finally:
        db.close()


@nfce_bp.route('/download-xml/<int:nfce_id>')
@login_required
@permission_required('nfe.view')
def download_xml_nfce(nfce_id: int):
    """Download do XML da NFC-e"""
    from flask import make_response
    db = next(get_db())
    
    try:
        accessible_clients = get_accessible_client_ids(db)
        
        nfce = db.query(NFeEmitidas).filter(
            NFeEmitidas.nfe_emitida_id == nfce_id,
            NFeEmitidas.cliente_id.in_(accessible_clients),
            NFeEmitidas.modelo == '65'
        ).first()
        
        if not nfce:
            flash('NFC-e não encontrada', 'danger')
            return redirect(url_for('nfce.listar_nfce'))
        
        # Extrair XML do JSON
        import json
        dados_nfce = json.loads(nfce.json_nfe) if nfce.json_nfe else {}
        xml_content = dados_nfce.get('xml_content', '<xml>Conteúdo não disponível</xml>')
        
        # Criar response com XML
        response = make_response(xml_content)
        response.headers['Content-Type'] = 'application/xml'
        response.headers['Content-Disposition'] = f'attachment; filename=NFCe_{nfce.chave_acesso}.xml'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao baixar XML: {str(e)}', 'danger')
        return redirect(url_for('nfce.listar_nfce'))
    finally:
        db.close()


@nfce_bp.route('/cancelar/<int:nfce_id>', methods=['POST'])
@login_required
@permission_required('nfe.cancel')
def cancelar_nfce_route(nfce_id: int):
    """Cancelar NFC-e"""
    db = next(get_db())
    
    try:
        accessible_clients = get_accessible_client_ids(db)
        
        nfce = db.query(NFeEmitidas).filter(
            NFeEmitidas.nfe_emitida_id == nfce_id,
            NFeEmitidas.cliente_id.in_(accessible_clients),
            NFeEmitidas.modelo == '65'
        ).first()
        
        if not nfce:
            return jsonify({'sucesso': False, 'erro': 'NFC-e não encontrada'}), 404
        
        if nfce.status != 'Autorizada':
            return jsonify({'sucesso': False, 'erro': 'Apenas NFC-e autorizadas podem ser canceladas'}), 400
        
        # Verificar prazo de cancelamento (24h)
        from datetime import timedelta
        if datetime.now() - nfce.data_autorizacao > timedelta(hours=24):
            return jsonify({'sucesso': False, 'erro': 'Prazo de cancelamento expirado (24h)'}), 400
        
        # Buscar dados
        emitente = db.query(Cliente).filter_by(cliente_id=nfce.cliente_id).first()
        certificado = get_active_certificate_for_client(db, nfce.cliente_id)
        
        if not certificado:
            return jsonify({'sucesso': False, 'erro': 'Certificado não encontrado'}), 400
        
        # Justificativa
        justificativa = request.form.get('justificativa', '')
        if len(justificativa) < 15:
            return jsonify({'sucesso': False, 'erro': 'Justificativa deve ter pelo menos 15 caracteres'}), 400
        
        # Cancelar
        resultado = cancelar_nfce(nfce.chave_acesso, justificativa, emitente, certificado)
        
        if resultado['sucesso']:
            nfce.status = 'Cancelada'
            nfce.motivo_rejeicao = justificativa
            db.commit()
            
            return jsonify({
                'sucesso': True,
                'mensagem': 'NFC-e cancelada com sucesso',
                'protocolo': resultado.get('protocolo', '')
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': resultado.get('erro', 'Erro ao cancelar NFC-e')
            }), 400
            
    except Exception as e:
        db.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
    finally:
        db.close()


@nfce_bp.route('/danfce/<int:nfce_id>')
@login_required
@permission_required('nfe.view')
def danfce(nfce_id: int):
    """Gerar DANFC-e (Documento Auxiliar da NFC-e)"""
    db = next(get_db())
    
    try:
        accessible_clients = get_accessible_client_ids(db)
        
        nfce = db.query(NFeEmitidas).filter(
            NFeEmitidas.nfe_id == nfce_id,
            NFeEmitidas.cliente_id.in_(accessible_clients),
            NFeEmitidas.modelo == '65'
        ).first()
        
        if not nfce:
            flash('NFC-e não encontrada', 'danger')
            return redirect(url_for('nfce.listar_nfce'))
        
        # Buscar dados
        emitente = db.query(Cliente).filter_by(cliente_id=nfce.cliente_id).first()
        
        import json
        dados_nfce = json.loads(nfce.json_nfe) if nfce.json_nfe else {}
        
        return render_template(
            'admin/danfe/danfce.html',
            nfce=nfce,
            emitente=emitente,
            dados=dados_nfce
        )
        
    except Exception as e:
        flash(f'Erro ao gerar DANFC-e: {str(e)}', 'danger')
        return redirect(url_for('nfce.listar_nfce'))
    finally:
        db.close()

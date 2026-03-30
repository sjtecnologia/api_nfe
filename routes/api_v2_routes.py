"""
API v2 - Endpoints com autenticação via API Key
Inclui emissão de NFe, consultas e webhooks
"""
from flask import Blueprint, jsonify, request, g
from auth.api_key_auth import require_api_key
from database.connection import get_db
from database.models import (
    Cliente, Produto, NFeEmitidas, DestinatarioNFe,
    Cfop, Ncm
)

from services.webhook_service import trigger_webhook
from datetime import datetime
import json
import base64
import os

api_v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')


# ==================== FUNÇÕES AUXILIARES ====================

def buscar_e_aplicar_regra_tributaria_automatica(item, cliente_id, uf_destino, db):
    """
    Busca regra tributária automaticamente e aplica nos itens que não têm dados completos
    
    Args:
        item: Dicionário com dados do item (deve conter pelo menos 'ncm' e 'cfop')
        cliente_id: ID do cliente emitente
        uf_destino: UF do destinatário
        db: Sessão do banco de dados
    
    Returns:
        item modificado com dados tributários aplicados
    """
    from sqlalchemy import text, or_
    from database.models import RegraTributacao, Cliente
    
    # Se item já tem dados tributários completos, não busca
    tem_icms = item.get('cst_icms') or item.get('csosn_icms')
    tem_pis = item.get('cst_pis')
    tem_cofins = item.get('cst_cofins')
    
    if tem_icms and tem_pis and tem_cofins:
        print(f"[API v2] [REGRA] Item já possui dados tributários completos, pulando busca automática")
        return item
    
    # Buscar dados do emitente para pegar regime tributário e UF
    cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
    if not cliente:
        print(f"[API v2] [REGRA] Cliente não encontrado para busca de regra")
        return item
    
    ncm_codigo = item.get('ncm')
    cfop_codigo = item.get('cfop')
    
    if not ncm_codigo or not cfop_codigo:
        print(f"[API v2] [REGRA] NCM ou CFOP não fornecidos, impossível buscar regra")
        return item
    
    print(f"[API v2] [REGRA] Buscando regra tributária automática...")
    print(f"[API v2] [REGRA]   Cliente ID: {cliente_id}")
    print(f"[API v2] [REGRA]   Regime: {cliente.regime_tributario_id}")
    print(f"[API v2] [REGRA]   NCM: {ncm_codigo}")
    print(f"[API v2] [REGRA]   CFOP: {cfop_codigo}")
    print(f"[API v2] [REGRA]   UF: {cliente.uf} → {uf_destino}")
    
    try:
        # Buscar regra usando a mesma lógica da API de busca
        from sqlalchemy.orm import joinedload
        
        query = db.query(RegraTributacao).options(
            joinedload(RegraTributacao.regime_tributario),
            joinedload(RegraTributacao.cfop),
            joinedload(RegraTributacao.ncm)
        ).filter(RegraTributacao.ativo == True)
        
        # Filtrar por cliente (específico ou genérico)
        query = query.filter(
            or_(
                RegraTributacao.cliente_id == cliente_id,
                RegraTributacao.cliente_id.is_(None)
            )
        )
        
        # Filtrar por regime tributário
        if cliente.regime_tributario_id:
            query = query.filter(RegraTributacao.regime_tributario_id == cliente.regime_tributario_id)
        
        # Filtrar por CFOP
        from database.models import Cfop, Ncm
        cfop_obj = db.query(Cfop).filter(Cfop.cfop == cfop_codigo).first()
        if cfop_obj:
            query = query.filter(
                or_(
                    RegraTributacao.cfop_id == cfop_obj.cfop_id,
                    RegraTributacao.cfop_id.is_(None)
                )
            )
        
        # Filtrar por NCM
        ncm_obj = db.query(Ncm).filter(Ncm.codigo == ncm_codigo).first()
        if ncm_obj:
            query = query.filter(
                or_(
                    RegraTributacao.ncm_id == ncm_obj.ncm_id,
                    RegraTributacao.ncm_id.is_(None)
                )
            )
        
        # Filtrar por UF origem/destino
        query = query.filter(
            or_(
                RegraTributacao.uf_origem == cliente.uf,
                RegraTributacao.uf_origem.is_(None)
            )
        )
        query = query.filter(
            or_(
                RegraTributacao.uf_destino == uf_destino,
                RegraTributacao.uf_destino.is_(None)
            )
        )
        
        # Filtrar por tipo item (Produto por padrão)
        tipo_item = item.get('tipo_item', 'Produto')
        query = query.filter(
            or_(
                RegraTributacao.tipo_item == tipo_item,
                RegraTributacao.tipo_item.is_(None)
            )
        )
        
        # Ordenar por prioridade
        query = query.order_by(
            RegraTributacao.prioridade.desc(),
            RegraTributacao.cliente_id.desc().nullslast(),
            RegraTributacao.cfop_id.desc().nullslast(),
            RegraTributacao.ncm_id.desc().nullslast(),
            RegraTributacao.uf_origem.desc().nullslast(),
            RegraTributacao.uf_destino.desc().nullslast()
        )
        
        regra = query.first()
        
        if regra:
            print(f"[API v2] [REGRA] ✅ Regra encontrada: ID {regra.regra_tributacao_id}")
            print(f"[API v2] [REGRA]   Descrição: {regra.descricao_regra}")
            
            # Aplicar dados da regra no item
            # ICMS
            if not tem_icms:
                if regra.csosn_icms:
                    item['csosn_icms'] = regra.csosn_icms
                    print(f"[API v2] [REGRA]   → CSOSN ICMS: {regra.csosn_icms}")
                elif regra.cst_icms:
                    item['cst_icms'] = regra.cst_icms
                    print(f"[API v2] [REGRA]   → CST ICMS: {regra.cst_icms}")
                
                if regra.aliquota_icms:
                    item['aliquota_icms'] = float(regra.aliquota_icms)
                    print(f"[API v2] [REGRA]   → Alíquota ICMS: {regra.aliquota_icms}%")
                
                if regra.reducao_base_icms:
                    item['reducao_base_icms'] = float(regra.reducao_base_icms)
                
                if regra.modalidade_bc_icms:
                    item['modalidade_bc_icms'] = regra.modalidade_bc_icms
                
                if regra.motivo_desoneracao_icms:
                    item['motivo_desoneracao_icms'] = regra.motivo_desoneracao_icms
            
            # PIS
            if not tem_pis and regra.cst_pis:
                item['cst_pis'] = regra.cst_pis
                print(f"[API v2] [REGRA]   → CST PIS: {regra.cst_pis}")
                if regra.aliquota_pis:
                    item['aliquota_pis'] = float(regra.aliquota_pis)
                    print(f"[API v2] [REGRA]   → Alíquota PIS: {regra.aliquota_pis}%")
            
            # COFINS
            if not tem_cofins and regra.cst_cofins:
                item['cst_cofins'] = regra.cst_cofins
                print(f"[API v2] [REGRA]   → CST COFINS: {regra.cst_cofins}")
                if regra.aliquota_cofins:
                    item['aliquota_cofins'] = float(regra.aliquota_cofins)
                    print(f"[API v2] [REGRA]   → Alíquota COFINS: {regra.aliquota_cofins}%")
            
            # IPI
            if regra.cst_ipi:
                item['cst_ipi'] = regra.cst_ipi
                print(f"[API v2] [REGRA]   → CST IPI: {regra.cst_ipi}")
                if regra.aliquota_ipi:
                    item['aliquota_ipi'] = float(regra.aliquota_ipi)
                    print(f"[API v2] [REGRA]   → Alíquota IPI: {regra.aliquota_ipi}%")
            
        else:
            print(f"[API v2] [REGRA] ⚠️ Nenhuma regra encontrada para os critérios")
            print(f"[API v2] [REGRA] ℹ️ Item será processado com valores padrão ou fornecidos")
    
    except Exception as e:
        print(f"[API v2] [REGRA] ❌ Erro ao buscar regra tributária: {e}")
        import traceback
        traceback.print_exc()
    
    return item


# ==================== EMISSÃO DE NFE ====================

@api_v2_bp.route('/nfe/emitir', methods=['POST'])
@require_api_key(permissions=['nfe.write', 'nfe.emit'])
def emit_nfe():
    """
    Emite uma NFe via API
    
    Payload JSON:
    {
      "destinatario": {
        "cpf_cnpj": "12345678000195",
        "nome": "Cliente Teste",
        "endereco": "Rua Teste, 123",
        "numero": "123",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "uf": "SP",
        "cep": "01234567",
        "email": "cliente@teste.com"
      },
      "itens": [
        {
          "produto_id": 1,  // OU fornecer dados completos
          "descricao": "Produto Teste",
          "quantidade": 1,
          "valor_unitario": 100.00,
          "ncm": "84713000",
          "cfop": "5102",
          "unidade": "UN"
        }
      ],
      "natureza_operacao": "Venda",
      "informacoes_adicionais": "Observações da nota",
      "enviar_email": true
    }
    """
    try:
        print("=" * 80)
        print("[API v2] [START] Recebendo requisição POST /api/v2/nfe/emitir")
        print("=" * 80)
        
        db = next(get_db())
        print("[API v2] [OK] Conexão com banco estabelecida")
        
        data = request.get_json()
        print(f"[API v2] [INFO] Dados recebidos: {json.dumps(data, indent=2, default=str) if data else 'None'}")
        
        if not data:
            return jsonify({"error": "Dados JSON não fornecidos"}), 400
        
        # Validar campos obrigatórios
        if not data.get('destinatario'):
            return jsonify({"error": "Destinatario obrigatório"}), 400
        
        if not data.get('itens') or len(data['itens']) == 0:
            return jsonify({"error": "Pelo menos um item é obrigatório"}), 400
        
        cliente_id = g.cliente_id
        print(f"[API v2] [USER] Cliente ID: {cliente_id}")
        
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        
        if not cliente:
            print(f"[API v2] [ERROR] Cliente não encontrado: {cliente_id}")
            return jsonify({"error": "Cliente não encontrado"}), 404
        
        print(f"[API v2] [OK] Cliente encontrado: {cliente.razao_social}")
        
        # Verificar se pode emitir (plano ativo)
        print("[API v2] [CHECK] Verificando assinatura ativa...")
        from database.models import AssinaturaCliente
        assinatura = db.query(AssinaturaCliente).filter_by(
            cliente_id=cliente_id,
            status='ATIVA'
        ).first()
        
        if not assinatura:
            print("[API v2] [ERROR] Nenhuma assinatura ativa encontrada")
            return jsonify({"error": "Nenhuma assinatura ativa"}), 403
        
        print(f"[API v2] [OK] Assinatura ativa encontrada: {assinatura.plano.nome if assinatura.plano else 'N/A'}")
        
        pode_emitir, msg = assinatura.pode_emitir()
        print("[API v2] [DATA] Processando destinatário...")
        print(f"[API v2] [CHECK] Pode emitir? {pode_emitir} - {msg}")
        if not pode_emitir:
            return jsonify({"error": f"Não pode emitir: {msg}"}), 403
        
        # Criar ou buscar destinatário
        dest_data = data['destinatario']
        destinatario = db.query(DestinatarioNFe).filter_by(
            cliente_id=cliente_id,
            cpf_cnpj=dest_data['cpf_cnpj']
        ).first()
        
        if not destinatario:
            print(f"[API v2] [NEW] Criando novo destinatário: {dest_data.get('nome')}")
            destinatario = DestinatarioNFe(
                cliente_id=cliente_id,
                tipo_pessoa='J' if len(dest_data['cpf_cnpj']) == 14 else 'F',
                cpf_cnpj=dest_data['cpf_cnpj'],
                nome_razao_social=dest_data.get('nome'),
                logradouro=dest_data.get('endereco', 'Rua Teste'),
                numero=dest_data.get('numero', 'S/N'),
                complemento=dest_data.get('complemento'),
                bairro=dest_data.get('bairro', 'Centro'),
                nome_municipio=dest_data.get('cidade', 'São Paulo'),
                codigo_municipio=dest_data.get('codigo_municipio', '3550308'),
                uf=dest_data.get('uf', 'SP'),
                codigo_uf=dest_data.get('codigo_uf', '35'),
                cep=dest_data.get('cep', '00000000'),
                telefone=dest_data.get('telefone'),
                email=dest_data.get('email')
            )
            db.add(destinatario)
            db.flush()
            print(f"[API v2] [OK] Destinatário criado: ID {destinatario.destinatario_id}")
        else:
            print(f"[API v2] [OK] Destinatário existente: ID {destinatario.destinatario_id}")
        
        # Obter próximo número
        print("[API v2] [NUM] Obtendo próximo número de NFe...")
        from sqlalchemy import text
        try:
            result = db.execute(
                text("SELECT get_proximo_numero_nfe(:cliente_id, :modelo, :serie)"),
                {"cliente_id": cliente_id, "modelo": "55", "serie": 1}
            ).scalar()
            proximo_numero = result if result else 1
            print(f"[API v2] [OK] Próximo número (via function): {proximo_numero}")
        except Exception as e:
            print(f"[API v2] [WARN] Function get_proximo_numero_nfe falhou, usando fallback: {e}")
            result = db.execute(
                text("""
                    SELECT COALESCE(MAX(numero), 0) + 1 
                    FROM nfe_emitidas 
                    WHERE cliente_id = :cliente_id 
                      AND modelo = '55' 
                      AND serie = 1
                """),
                {"cliente_id": cliente_id}
            ).scalar()
            proximo_numero = result if result else 1
            print(f"[API v2] [OK] Próximo número (via MAX): {proximo_numero}")
        
        # Criar NFe
        # Calcular valor total dos itens
        print(f"[API v2] [CALC] Calculando valor total de {len(data['itens'])} item(ns)...")
        from decimal import Decimal
        valor_total = Decimal('0')
        for item in data['itens']:
            quantidade = Decimal(str(item.get('quantidade', 0)))
            valor_unitario = Decimal(str(item.get('valor_unitario', 0)))
            valor_total += quantidade * valor_unitario
        print(f"[API v2] [OK] Valor total calculado: R$ {valor_total}")
        
        # ======================================================================
        # 🤖 APLICAR REGRAS TRIBUTÁRIAS AUTOMATICAMENTE
        # ======================================================================
        print(f"[API v2] [AUTO] Aplicando regras tributárias automaticamente nos itens...")
        itens_processados = []
        for idx, item in enumerate(data['itens'], 1):
            print(f"[API v2] [AUTO] Processando item {idx}/{len(data['itens'])}...")
            item_com_regra = buscar_e_aplicar_regra_tributaria_automatica(
                item=item,
                cliente_id=cliente_id,
                uf_destino=destinatario.uf,
                db=db
            )
            itens_processados.append(item_com_regra)
        
        print(f"[API v2] [AUTO] ✅ Regras aplicadas em {len(itens_processados)} item(ns)")
        
        # Preparar dados da NFe com destinatário e itens (agora com tributação automática)
        nfe_data = {
            'cliente_id': cliente_id,
            'destinatario_id': destinatario.destinatario_id,
            'destinatario_cnpj_cpf': destinatario.cpf_cnpj,
            'numero_nfe': proximo_numero,  # Número da NFe
            'serie': 1,  # Série
            'modelo': '55',  # Modelo NFe
            'natureza_operacao': data.get('natureza_operacao', 'Venda'),
            'tipo_operacao': data.get('tipo_operacao', '1'),
            'finalidade_emissao': data.get('finalidade_emissao', '1'),
            'consumidor_final': data.get('consumidor_final', '1'),
            'presenca_comprador': data.get('presenca_comprador', '1'),
            'informacoes_adicionais': data.get('informacoes_adicionais'),
            'transporte': data.get('transporte', {}),  # ADICIONAR TRANSPORTE
            'cobranca': data.get('cobranca', {}),  # ADICIONAR COBRANÇA
            'totais': data.get('totais', {}),  # ADICIONAR TOTAIS
            'referenciadas': data.get('referenciadas', []),  # ADICIONAR REFERENCIADAS
            'destinatario': {
                'cnpj_cpf': destinatario.cpf_cnpj,
                'nome_razao_social': destinatario.nome_razao_social,
                'logradouro': destinatario.logradouro,
                'numero': destinatario.numero,
                'bairro': destinatario.bairro,
                'cep': destinatario.cep,
                'nome_municipio': destinatario.nome_municipio,
                'codigo_municipio': destinatario.codigo_municipio,
                'uf': destinatario.uf
            },
            'itens': itens_processados  # Usar itens com regras aplicadas
        }
        print(f"[API v2] [DB] Criando NFe no banco: Número {proximo_numero}, Série 1...")
        # Converter informacoes_adicionais para JSON string se for dict
        info_adicionais = data.get('informacoes_adicionais')
        if isinstance(info_adicionais, dict):
            info_adicionais = json.dumps(info_adicionais)
        
        nfe = NFeEmitidas(
            cliente_id=cliente_id,
            destinatario_razao_social=destinatario.nome_razao_social,
            destinatario_cnpj_cpf=destinatario.cpf_cnpj,
            tipo_nfe='1',  # Saída
            modelo='55',
            serie=1,
            numero=proximo_numero,
            data_emissao=datetime.now(),
            natureza_operacao=data.get('natureza_operacao', 'Venda'),
            finalidade_emissao='1',  # 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução
            informacoes_adicionais=info_adicionais,
            valor_total=valor_total,  # Adicionar valor total calculado
            json_nfe=json.dumps(nfe_data),
            status='CRIADA'
        )
        db.add(nfe)
        db.commit()
        print(f"[API v2] [OK] NFe criada no banco: ID {nfe.nfe_emitida_id}")
        
        # Processar NFe (calcular impostos, gerar XML, assinar)
        try:
            print("[API v2] [INFO] Importando services (NFeService, SefazService)...")
            from services.nfe_service import NFeService
            from services.sefaz_service import SefazService
            print("[API v2] [OK] Services importados com sucesso")
            
            nfe_service = NFeService(db)
            print("[API v2] [OK] NFeService instanciado")
            
            print(f"[API v2] [PROCESS] Processando NFe ID: {nfe.nfe_emitida_id}")
            print(f"[API v2] [DATA] Dados NFe: {json.dumps(nfe_data, indent=2, default=str)}")
            print(f"[API v2] [INFO] Itens: {len(data['itens'])} item(ns)")
            
            print("[API v2] [PROC] Chamando nfe_service.processar_nfe()...")
            # Usar itens_processados com regras tributárias aplicadas
            resultado = nfe_service.processar_nfe(nfe_data, itens_processados, cliente_id, nfe.nfe_emitida_id)
            print(f"[API v2] [OK] processar_nfe() retornou: {resultado.get('success')}")
            
            print(f"[API] Resultado do processamento: success={resultado.get('success')}, status={resultado.get('status')}")
            
            if not resultado.get('success'):
                # Verificar se tem lista de erros
                erros = resultado.get('errors', [resultado.get('message', 'Erro desconhecido')])
                mensagem_erro = erros[0] if isinstance(erros, list) and len(erros) > 0 else str(erros)
                
                return jsonify({
                    "error": "Erro ao processar NFe",
                    "message": mensagem_erro
                }), 500
            
            # O processar_nfe já envia para SEFAZ, então pegamos o resultado dele
            status_sefaz = resultado.get('status', '').upper()
            sefaz_response = resultado.get('sefaz_response', {})
            
            if status_sefaz == 'AUTORIZADA':
                nfe.status = 'AUTORIZADA'
                nfe.chave_acesso = resultado.get('chave_acesso')
                nfe.protocolo_sefaz = resultado.get('protocolo')
                nfe.data_autorizacao = datetime.now()
                
                # Atualizar consumo da assinatura
                assinatura.registrar_emissao()
                db.commit()
                
                # Enviar email se solicitado
                if data.get('enviar_email', False) and destinatario.email:
                    from services.email_service import send_nfe_email
                    send_nfe_email(nfe.nfe_emitida_id, destinatario.email)
                
                # Trigger webhook
                trigger_webhook(
                    cliente_id=cliente_id,
                    evento='nfe.autorizada',
                    payload={
                        'nfe_id': nfe.nfe_emitida_id,
                        'numero': nfe.numero,
                        'serie': nfe.serie,
                        'chave_acesso': nfe.chave_acesso,
                        'valor_total': float(nfe.valor_total) if nfe.valor_total else 0,
                        'destinatario': destinatario.nome_razao_social
                    }
                )
                
                return jsonify({
                    "success": True,
                    "message": "NFe emitida e autorizada com sucesso",
                    "nfe": {
                        "nfe_id": nfe.nfe_emitida_id,
                        "numero": nfe.numero,
                        "serie": nfe.serie,
                        "chave_acesso": nfe.chave_acesso,
                        "protocolo": nfe.protocolo_sefaz,
                        "status": nfe.status,
                        "valor_total": float(nfe.valor_total) if nfe.valor_total else 0
                    }
                }), 201
            elif status_sefaz == 'PROCESSANDO':
                # Lote em processamento - retornar sucesso parcial
                nfe.status = 'PROCESSANDO'
                nfe.chave_acesso = resultado.get('chave_acesso')
                nfe.mensagem_sefaz = str(resultado.get('message', ''))[:250]
                db.commit()
                
                return jsonify({
                    "success": True,
                    "message": "NFe enviada - Aguardando processamento da SEFAZ",
                    "nfe": {
                        "nfe_id": nfe.nfe_emitida_id,
                        "numero": nfe.numero,
                        "serie": nfe.serie,
                        "chave_acesso": nfe.chave_acesso,
                        "status": "PROCESSANDO",
                        "mensagem": resultado.get('message'),
                        "info": "Consulte o status posteriormente para verificar se foi autorizada"
                    }
                }), 202  # 202 Accepted
            else:
                # Rejeição ou erro
                nfe.status = 'REJEITADA'
                mensagem_erro = resultado.get('message', sefaz_response.get('mensagem', sefaz_response.get('motivo', 'Erro desconhecido')))
                # Truncar mensagem para caber no banco (limite de 250 caracteres por segurança)
                nfe.mensagem_sefaz = str(mensagem_erro)[:250] if mensagem_erro else 'Erro na transmissão'
                db.commit()
                
                # Trigger webhook de rejeição
                trigger_webhook(
                    cliente_id=cliente_id,
                    evento='nfe.rejeitada',
                    payload={
                        'nfe_id': nfe.nfe_emitida_id,
                        'numero': nfe.numero,
                        'codigo_sefaz': sefaz_response.get('codigo'),
                        'motivo': mensagem_erro[:100] if mensagem_erro else 'Erro na transmissão'
                    }
                )
                
                return jsonify({
                    "error": "NFe rejeitada pela SEFAZ",
                    "message": mensagem_erro,
                    "codigo_sefaz": sefaz_response.get('codigo'),
                    "nfe_id": nfe.nfe_emitida_id
                }), 422
        
        except Exception as e:
            db.rollback()
            print(f"[ERROR] Erro ao processar NFe: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": "Erro ao processar NFe",
                "message": str(e)
            }), 500
    
    except Exception as e:
        print(f"[ERROR] Erro ao emitir NFe via API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Erro interno",
            "message": str(e)
        }), 500


# ==================== CONSULTAS ====================

@api_v2_bp.route('/nfe/<int:nfe_id>', methods=['GET'])
@require_api_key(permissions=['nfe.read'])
def get_nfe(nfe_id):
    """Consulta dados de uma NFe específica"""
    db = next(get_db())
    
    nfe = db.query(NFeEmitidas).filter_by(
        nfe_emitida_id=nfe_id,
        cliente_id=g.cliente_id
    ).first()
    
    if not nfe:
        return jsonify({"error": "NFe não encontrada"}), 404
    
    return jsonify({
        "success": True,
        "nfe": nfe.to_dict()
    }), 200


@api_v2_bp.route('/nfes', methods=['GET'])
@require_api_key(permissions=['nfe.read'])
def list_nfes():
    """Lista NFes do cliente"""
    db = next(get_db())
    
    # Parâmetros de filtro
    limite = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    status = request.args.get('status')
    
    query = db.query(NFeEmitidas).filter_by(cliente_id=g.cliente_id)
    
    if status:
        query = query.filter_by(status=status)
    
    query = query.order_by(NFeEmitidas.data_emissao.desc())
    
    total = query.count()
    nfes = query.limit(limite).offset(offset).all()
    
    return jsonify({
        "success": True,
        "total": total,
        "limit": limite,
        "offset": offset,
        "nfes": [nfe.to_dict() for nfe in nfes]
    }), 200


@api_v2_bp.route('/nfe/<int:nfe_id>/xml', methods=['GET'])
@require_api_key(permissions=['nfe.read'])
def get_nfe_xml(nfe_id):
    """Retorna o XML da NFe"""
    db = next(get_db())
    
    nfe = db.query(NFeEmitidas).filter_by(
        nfe_emitida_id=nfe_id,
        cliente_id=g.cliente_id
    ).first()
    
    if not nfe:
        return jsonify({"error": "NFe não encontrada"}), 404
    
    # TODO: Implementar armazenamento do XML em tabela separada ou campo BLOB
    # Por ora, retornar erro informativo
    return jsonify({
        "error": "XML não disponível via API",
        "message": "Utilize a interface web para baixar o XML da NFe"
    }), 501


@api_v2_bp.route('/nfe/<int:nfe_id>/cancelar', methods=['POST'])
@require_api_key(permissions=['nfe.write', 'nfe.cancel'])
def cancel_nfe(nfe_id):
    """Cancela uma NFe"""
    db = next(get_db())
    data = request.get_json()
    
    nfe = db.query(NFeEmitidas).filter_by(
        nfe_id=nfe_id,
        cliente_id=g.cliente_id
    ).first()
    
    if not nfe:
        return jsonify({"error": "NFe não encontrada"}), 404
    
    if nfe.status != 'AUTORIZADA':
        return jsonify({"error": "Apenas NFes autorizadas podem ser canceladas"}), 400
    
    justificativa = data.get('justificativa')
    if not justificativa or len(justificativa) < 15:
        return jsonify({"error": "Justificativa deve ter no mínimo 15 caracteres"}), 400
    
    try:
        # TODO: Implementar método de cancelamento no SefazService
        # Por ora, retornar erro indicando que precisa ser implementado
        return jsonify({
            "error": "Funcionalidade de cancelamento em implementação",
            "message": "O cancelamento via API estará disponível em breve. Use a interface web."
        }), 501
    
    except Exception as e:
        return jsonify({
            "error": "Erro ao cancelar NFe",
            "message": str(e)
        }), 500

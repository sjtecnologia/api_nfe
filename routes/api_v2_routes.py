"""
API v2 - Endpoints com autenticação via API Key
Inclui emissão de NFe, consultas e webhooks
"""
from flask import Blueprint, jsonify, request, g, Response
from auth.api_key_auth import require_api_key
from database.connection import get_db
from database.models import (
    Cliente, Produto, NFeEmitidas, DestinatarioNFe,
    Cfop, Ncm
)
from sqlalchemy import text
from lxml import etree

from services.webhook_service import trigger_webhook
from datetime import datetime
import json
import base64
import os
import hashlib

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


def _validar_ambiente_api(ambiente):
    """Impede uma chave de teste de atingir emissão em produção."""
    solicitado = ambiente if ambiente in ('producao', 'homologacao') else 'homologacao'
    if getattr(g, 'api_environment', 'producao') == 'teste' and solicitado == 'producao':
        return False, solicitado
    return True, solicitado


def _chave_pode_emitir_nfe(cliente):
    """Aplica o isolamento da chave ao ambiente do emitente NF-e."""
    return not (
        getattr(g, 'api_environment', 'producao') == 'teste'
        and getattr(cliente, 'ambiente', 2) == 1
    )


def _persistir_falha_idempotencia(db, registro, status_code, payload):
    """Finaliza uma reserva idempotente mesmo quando a emissão falha."""
    if not registro:
        return
    try:
        from database.models import FiscalApiIdempotency
        atual = db.query(FiscalApiIdempotency).filter_by(
            idempotency_id=registro.idempotency_id
        ).first()
        if atual:
            atual.response_json = json.dumps(payload, default=str)
            atual.status_code = status_code
            db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[WARN] Não foi possível persistir falha idempotente: {exc}")


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
        # Nunca registrar o payload fiscal completo: ele pode conter CPF/CNPJ,
        # endereços, valores e informações comerciais sensíveis.
        if data:
            print(
                "[API v2] [INFO] Payload recebido: "
                f"destinatario={'sim' if data.get('destinatario') else 'não'}, "
                f"itens={len(data.get('itens') or [])}"
            )
        else:
            print("[API v2] [INFO] Payload vazio")
        
        if not data:
            return jsonify({"error": "Dados JSON não fornecidos"}), 400
        
        # Validar campos obrigatórios
        if not data.get('destinatario'):
            return jsonify({"error": "Destinatario obrigatório"}), 400
        
        if not data.get('itens') or len(data['itens']) == 0:
            return jsonify({"error": "Pelo menos um item é obrigatório"}), 400
        
        cliente_id = g.cliente_id
        print(f"[API v2] [USER] Cliente ID: {cliente_id}")

        # Idempotência opcional e retrocompatível. Para emissões fiscais,
        # recomendamos sempre enviar Idempotency-Key; retries com a mesma
        # chave e payload devolvem exatamente a resposta original.
        idempotency_key = (request.headers.get('Idempotency-Key') or '').strip()
        idempotency_record = None
        if idempotency_key:
            if len(idempotency_key) > 255:
                return jsonify({"error": "Idempotency-Key excede 255 caracteres"}), 400
            canonical_payload = json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)
            request_hash = hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()
            from database.models import FiscalApiIdempotency
            idempotency_record = db.query(FiscalApiIdempotency).filter_by(
                cliente_id=cliente_id,
                endpoint='/api/v2/nfe/emitir',
                idempotency_key=idempotency_key,
            ).first()
            if idempotency_record:
                if idempotency_record.request_hash != request_hash:
                    return jsonify({
                        "error": "Idempotency-Key já utilizada com payload diferente"
                    }), 409
                if idempotency_record.response_json:
                    saved = json.loads(idempotency_record.response_json)
                    return jsonify(saved), idempotency_record.status_code or 200
                return jsonify({'success': True, 'status': 'PROCESSANDO',
                                'message': 'Requisição idempotente já está em processamento'}), 202
            else:
                idempotency_record = FiscalApiIdempotency(
                    cliente_id=cliente_id,
                    endpoint='/api/v2/nfe/emitir',
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    status_code=202,
                )
                db.add(idempotency_record)
                try:
                    db.commit()
                except Exception:
                    # Outra requisição pode ter reservado a mesma chave.
                    db.rollback()
                    idempotency_record = db.query(FiscalApiIdempotency).filter_by(
                        cliente_id=cliente_id,
                        endpoint='/api/v2/nfe/emitir',
                        idempotency_key=idempotency_key,
                    ).first()
                    if idempotency_record and idempotency_record.response_json:
                        return jsonify(json.loads(idempotency_record.response_json)), idempotency_record.status_code or 200
        
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        
        if not cliente:
            print(f"[API v2] [ERROR] Cliente não encontrado: {cliente_id}")
            return jsonify({"error": "Cliente não encontrado"}), 404

        # NF-e usa o ambiente configurado no emitente. Uma chave de teste não
        # pode alcançar um emitente marcado como produção.
        if not _chave_pode_emitir_nfe(cliente):
            return jsonify({
                "error": "Chave de teste não pode emitir NF-e em produção"
            }), 403
        
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
            'quota_reservation_key': f"NFE:api:{cliente_id}:1:{proximo_numero}",
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
            
            if resultado.get('quota_blocked'):
                db.delete(nfe)
                db.commit()
                quota = resultado.get('quota', {})
                return jsonify({
                    "success": False,
                    "code": quota.get('code', 'PLAN_NFE_QUOTA_EXCEEDED'),
                    "metric": "NFE_ISSUED",
                    "used": quota.get('used'),
                    "limit": quota.get('limit', 50),
                    "period_start": quota.get('period_start'),
                    "period_end": quota.get('period_end'),
                    "upgrade_available": True,
                    "message": resultado.get('message'),
                }), 409

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
                
                response_payload = {
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
                }
                if idempotency_record:
                    idempotency_record.response_json = json.dumps(response_payload, default=str)
                    idempotency_record.status_code = 201
                    db.commit()
                return jsonify(response_payload), 201
            elif status_sefaz == 'PROCESSANDO':
                # Lote em processamento - retornar sucesso parcial
                nfe.status = 'PROCESSANDO'
                nfe.chave_acesso = resultado.get('chave_acesso')
                nfe.mensagem_sefaz = str(resultado.get('message', ''))[:250]
                db.commit()
                
                response_payload = {
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
                }
                if idempotency_record:
                    idempotency_record.response_json = json.dumps(response_payload, default=str)
                    idempotency_record.status_code = 202
                    db.commit()
                return jsonify(response_payload), 202  # 202 Accepted
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
            _persistir_falha_idempotencia(db, idempotency_record, 500, {
                'success': False, 'error': 'Erro ao processar NFe', 'message': str(e)
            })
            print(f"[ERROR] Erro ao processar NFe: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": "Erro ao processar NFe",
                "message": str(e)
            }), 500
    
    except Exception as e:
        _persistir_falha_idempotencia(db, idempotency_record, 500, {
            'success': False, 'error': 'Erro interno', 'message': str(e)
        })
        print(f"[ERROR] Erro ao emitir NFe via API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Erro interno",
            "message": str(e)
        }), 500


# ==================== CONSULTAS ====================

@api_v2_bp.route('/nfses', methods=['GET'])
@require_api_key(permissions=['nfse.read'])
def list_nfses():
    """Lista NFS-e/RPS do cliente autenticado."""
    db = next(get_db())
    limite = min(max(request.args.get('limit', 50, type=int), 1), 100)
    offset = max(request.args.get('offset', 0, type=int), 0)
    rows = db.execute(text("""
        SELECT id, numero_rps, serie_rps, status, ambiente, protocolo,
               data_emissao, tomador_razao_social, valor_servicos,
               mensagem_retorno
          FROM nfse WHERE cliente_id = :cliente_id
         ORDER BY created_at DESC LIMIT :limite OFFSET :offset
    """), {'cliente_id': g.cliente_id, 'limite': limite, 'offset': offset}).mappings().all()
    return jsonify({'success': True, 'limit': limite, 'offset': offset,
                    'nfses': [dict(row) for row in rows]}), 200


@api_v2_bp.route('/nfse/<int:nfse_id>', methods=['GET'])
@require_api_key(permissions=['nfse.read'])
def get_nfse(nfse_id):
    """Consulta uma NFS-e/RPS do cliente autenticado."""
    db = next(get_db())
    row = db.execute(text("""
        SELECT * FROM nfse WHERE id = :id AND cliente_id = :cliente_id
    """), {'id': nfse_id, 'cliente_id': g.cliente_id}).mappings().first()
    if not row:
        return jsonify({'error': 'NFS-e não encontrada'}), 404
    return jsonify({'success': True, 'nfse': dict(row)}), 200


@api_v2_bp.route('/nfse/<int:nfse_id>/xml', methods=['GET'])
@require_api_key(permissions=['nfse.read'])
def get_nfse_xml(nfse_id):
    """Baixa o XML do RPS armazenado para a NFS-e."""
    db = next(get_db())
    row = db.execute(text("""
        SELECT numero_rps, numero_nfse, protocolo, xml_nfse, xml_rps FROM nfse
         WHERE id = :id AND cliente_id = :cliente_id
    """), {'id': nfse_id, 'cliente_id': g.cliente_id}).mappings().first()
    if not row:
        return jsonify({'error': 'NFS-e não encontrada'}), 404
    xml_content = row['xml_nfse'] or row['xml_rps']
    if not xml_content:
        return jsonify({'error': 'XML ainda não disponível'}), 404
    numero = row['numero_nfse'] or row['numero_rps']
    response = Response(xml_content, mimetype='application/xml')
    response.headers['Content-Disposition'] = f"attachment; filename=NFSe_{numero}.xml"
    return response


@api_v2_bp.route('/nfse/<int:nfse_id>/status', methods=['GET'])
@require_api_key(permissions=['nfse.read'])
def get_nfse_status(nfse_id):
    """Consulta e sincroniza o lote NFS-e no provedor municipal."""
    db = next(get_db())
    row = db.execute(text("""
        SELECT id, cliente_id, protocolo, ambiente, status, numero_nfse,
               chave_nota_nacional, mensagem_retorno
          FROM nfse WHERE id = :id AND cliente_id = :cliente_id
    """), {'id': nfse_id, 'cliente_id': g.cliente_id}).mappings().first()
    if not row:
        return jsonify({'error': 'NFS-e não encontrada'}), 404
    if not row['protocolo']:
        return jsonify({'success': True, 'nfse': dict(row), 'source': 'local'}), 200
    try:
        prestador = db.query(Cliente).filter_by(cliente_id=g.cliente_id).first()
        from services.nfse_service import NFSeService
        sucesso, resultado = NFSeService(ambiente=row['ambiente'] or 'homologacao').consultar_lote(
            protocolo=row['protocolo'],
            prestador_cnpj=''.join(ch for ch in (prestador.cnpj or '') if ch.isdigit()),
            inscricao_municipal=prestador.inscricao_municipal or '',
            db_session=db, cliente_id=g.cliente_id,
        )
        if sucesso and resultado.get('situacao_codigo') == '4':
            db.execute(text("""
                UPDATE nfse SET status = '1', numero_nfse = COALESCE(:numero_nfse, numero_nfse),
                    codigo_verificacao = COALESCE(:codigo_verificacao, codigo_verificacao),
                    chave_nota_nacional = COALESCE(:chave, chave_nota_nacional),
                    xml_nfse = COALESCE(:xml, xml_nfse), updated_at = :updated_at
                WHERE id = :id AND cliente_id = :cliente_id
            """), {'numero_nfse': resultado.get('numero_nfse'), 'codigo_verificacao': resultado.get('codigo_verificacao'),
                    'chave': resultado.get('chave_nota_nacional'), 'xml': resultado.get('xml_nfse'),
                    'updated_at': datetime.now(), 'id': nfse_id, 'cliente_id': g.cliente_id})
            db.commit()
        return jsonify({'success': sucesso, 'nfse_id': nfse_id, 'status': resultado.get('situacao'),
                        'situacao_codigo': resultado.get('situacao_codigo'), 'resultado': resultado}), 200 if sucesso else 502
    except Exception as exc:
        db.rollback()
        return jsonify({'success': False, 'error': 'Erro ao consultar NFS-e', 'detail': str(exc)}), 502


@api_v2_bp.route('/nfse/<int:nfse_id>/cancelar', methods=['POST'])
@require_api_key(permissions=['nfse.write', 'nfse.cancel'])
def cancel_nfse(nfse_id):
    """Cancela NFS-e autorizada no provedor municipal configurado."""
    db = next(get_db())
    row = db.execute(text("""
        SELECT id, cliente_id, numero_nfse, ambiente, status FROM nfse
         WHERE id = :id AND cliente_id = :cliente_id
    """), {'id': nfse_id, 'cliente_id': g.cliente_id}).mappings().first()
    if not row:
        return jsonify({'error': 'NFS-e não encontrada'}), 404
    if str(row['status']) not in {'1', 'AUTORIZADA'}:
        return jsonify({'error': 'Apenas NFS-e autorizadas podem ser canceladas'}), 400
    if not row['numero_nfse']:
        return jsonify({'error': 'Número da NFS-e não disponível'}), 400
    payload = request.get_json(silent=True) or {}
    codigo = str(payload.get('codigo_cancelamento') or '1')
    prestador = db.query(Cliente).filter_by(cliente_id=g.cliente_id).first()
    if not prestador:
        return jsonify({'error': 'Prestador não encontrado'}), 404
    try:
        from services.nfse_service import NFSeService
        sucesso, resultado = NFSeService(ambiente=row['ambiente'] or 'homologacao').cancelar_nfse(
            numero_nfse=str(row['numero_nfse']), codigo_cancelamento=codigo,
            prestador_cnpj=''.join(ch for ch in (prestador.cnpj or '') if ch.isdigit()),
            inscricao_municipal=prestador.inscricao_municipal or '',
            codigo_municipio=prestador.codigo_municipio or '3549805',
            db_session=db, cliente_id=g.cliente_id,
        )
        if not sucesso:
            return jsonify({'success': False, 'error': resultado.get('erro', 'Cancelamento rejeitado')}), 502
        db.execute(text("""UPDATE nfse SET status = '3', updated_at = :updated_at
            WHERE id = :id AND cliente_id = :cliente_id"""),
                   {'updated_at': datetime.now(), 'id': nfse_id, 'cliente_id': g.cliente_id})
        db.commit()
        trigger_webhook(cliente_id=g.cliente_id, evento='nfse.cancelada',
                        payload={'nfse_id': nfse_id, 'numero_nfse': row['numero_nfse']})
        return jsonify({'success': True, 'nfse_id': nfse_id,
                        'numero_nfse': row['numero_nfse'], 'resultado': resultado}), 200
    except Exception as exc:
        db.rollback()
        return jsonify({'success': False, 'error': 'Erro ao cancelar NFS-e', 'detail': str(exc)}), 502

@api_v2_bp.route('/nfse/emitir', methods=['POST'])
@require_api_key(permissions=['nfse.write', 'nfse.emit'])
def emit_nfse():
    """Emite NFS-e pelo mesmo serviço usado pelo frontend."""
    db = next(get_db())
    data = request.get_json(silent=True) or {}
    ambiente_ok, ambiente_solicitado = _validar_ambiente_api(data.get('ambiente'))
    if not ambiente_ok:
        return jsonify({'error': 'Chave de teste não pode emitir em produção'}), 403
    required = ('tomador_cpf_cnpj', 'tomador_razao_social', 'discriminacao', 'valor_servico')
    missing = [field for field in required if data.get(field) in (None, '')]
    if missing:
        return jsonify({'error': 'Campos obrigatórios ausentes', 'fields': missing}), 400

    idempotency_record = None
    idempotency_key = (request.headers.get('Idempotency-Key') or '').strip()
    if idempotency_key:
        if len(idempotency_key) > 255:
            return jsonify({'error': 'Idempotency-Key excede 255 caracteres'}), 400
        request_hash = hashlib.sha256(json.dumps(
            data, sort_keys=True, separators=(',', ':'), default=str
        ).encode('utf-8')).hexdigest()
        from database.models import FiscalApiIdempotency
        idempotency_record = db.query(FiscalApiIdempotency).filter_by(
            cliente_id=g.cliente_id, endpoint='/api/v2/nfse/emitir',
            idempotency_key=idempotency_key,
        ).first()
        if idempotency_record:
            if idempotency_record.request_hash != request_hash:
                return jsonify({'error': 'Idempotency-Key já utilizada com payload diferente'}), 409
            if idempotency_record.response_json:
                return jsonify(json.loads(idempotency_record.response_json)), idempotency_record.status_code or 200
            return jsonify({'success': True, 'status': 'PROCESSANDO',
                            'message': 'Requisição idempotente já está em processamento'}), 202
        else:
            idempotency_record = FiscalApiIdempotency(
                cliente_id=g.cliente_id, endpoint='/api/v2/nfse/emitir',
                idempotency_key=idempotency_key, request_hash=request_hash,
                status_code=202,
            )
            db.add(idempotency_record)
            try:
                db.commit()
            except Exception:
                db.rollback()
                idempotency_record = db.query(FiscalApiIdempotency).filter_by(
                    cliente_id=g.cliente_id, endpoint='/api/v2/nfse/emitir',
                    idempotency_key=idempotency_key,
                ).first()
                if idempotency_record and idempotency_record.response_json:
                    return jsonify(json.loads(idempotency_record.response_json)), idempotency_record.status_code or 200

    cliente = db.query(Cliente).filter_by(cliente_id=g.cliente_id).first()
    if not cliente:
        return jsonify({'error': 'Prestador não encontrado'}), 404
    try:
        valor = float(data['valor_servico'])
        if valor <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({'error': 'valor_servico deve ser numérico e maior que zero'}), 400

    try:
        numero_rps = int(data.get('numero_rps') or (db.execute(text(
            "SELECT COALESCE(MAX(numero_rps), 0) + 1 FROM nfse WHERE cliente_id = :cliente_id"
        ), {'cliente_id': g.cliente_id}).scalar() or 1))
        dados = dict(data)
        dados.update({
            'cliente_id': g.cliente_id, 'numero_rps': numero_rps,
            'serie_rps': str(data.get('serie_rps') or '1'),
            'tipo_rps': str(data.get('tipo_rps') or '1'),
            'data_competencia': data.get('data_competencia') or datetime.now().strftime('%Y-%m-%d'),
            'ambiente': ambiente_solicitado,
            'valor_servico': valor,
        })
        prestador = {
            'cnpj': cliente.cnpj, 'inscricao_municipal': cliente.inscricao_municipal or '',
            'razao_social': cliente.razao_social, 'nome_fantasia': cliente.nome_fantasia,
            'logradouro': cliente.logradouro, 'numero': cliente.numero, 'bairro': cliente.bairro,
            'codigo_municipio': cliente.codigo_municipio or '3549805', 'uf': cliente.uf or 'SP',
            'cep': cliente.cep or '', 'optante_simples': getattr(cliente, 'optante_simples', True),
        }
        from services.nfse_service import NFSeService, criar_nfse_de_formulario
        nfse = criar_nfse_de_formulario(dados, prestador)
        service = NFSeService(ambiente=dados['ambiente'], municipio_slug=data.get('giss_municipio_slug'), ws_host=data.get('giss_ws_host'))
        xml_rps = service.gerar_xml_rps(nfse)
        sucesso, resposta = service.enviar_lote_rps(nfse, db_session=db)
        protocolo = resposta.get('protocolo') if isinstance(resposta, dict) else None
        mensagem = None if sucesso else str((resposta or {}).get('mensagem') or (resposta or {}).get('erro') or 'Falha no envio')
        status = '2' if sucesso else '0'
        tomador_doc = ''.join(ch for ch in str(data['tomador_cpf_cnpj']) if ch.isdigit())
        aliquota = float(data.get('aliquota_iss') or 0)
        valor_iss = round(valor * aliquota / 100, 2)
        row = db.execute(text("""
            INSERT INTO nfse (
              cliente_id, numero_rps, serie_rps, tipo_rps, data_emissao,
              data_competencia, natureza_operacao, tomador_cpf_cnpj,
              tomador_razao_social, tomador_endereco, codigo_servico,
              discriminacao, valor_servicos, aliquota_iss, valor_iss,
              valor_liquido, codigo_nbs, xml_rps, status, ambiente,
              protocolo, mensagem_retorno, created_at
            ) VALUES (
              :cliente_id, :numero_rps, :serie_rps, :tipo_rps, :data_emissao,
              :data_competencia, :natureza, :tomador_doc, :tomador_nome,
              :tomador_endereco, :codigo_servico, :discriminacao, :valor,
              :aliquota, :valor_iss, :valor_liquido, :codigo_nbs, :xml_rps,
              :status, :ambiente, :protocolo, :mensagem, :created_at
            ) RETURNING id
        """), {
            'cliente_id': g.cliente_id, 'numero_rps': numero_rps, 'serie_rps': dados['serie_rps'],
            'tipo_rps': dados['tipo_rps'], 'data_emissao': datetime.now(), 'data_competencia': dados['data_competencia'],
            'natureza': dados.get('natureza_operacao', '1'), 'tomador_doc': tomador_doc,
            'tomador_nome': data['tomador_razao_social'], 'tomador_endereco': f"{data.get('tomador_logradouro', '')}, {data.get('tomador_numero', '')}",
            'codigo_servico': data.get('codigo_servico', '17.01'), 'discriminacao': data['discriminacao'],
            'valor': valor, 'aliquota': aliquota, 'valor_iss': valor_iss,
            'valor_liquido': valor - valor_iss if data.get('iss_retido') else valor,
            'codigo_nbs': data.get('codigo_nbs', '101010000'), 'xml_rps': xml_rps,
            'status': status, 'ambiente': dados['ambiente'], 'protocolo': protocolo,
            'mensagem': mensagem, 'created_at': datetime.now(),
        })
        nfse_id = row.scalar_one()
        db.commit()
        result = {'success': sucesso, 'nfse': {'id': nfse_id, 'numero_rps': numero_rps,
            'serie_rps': dados['serie_rps'], 'status': status, 'protocolo': protocolo,
            'mensagem': mensagem, 'ambiente': dados['ambiente']}}
        if idempotency_record:
            idempotency_record.response_json = json.dumps(result, default=str)
            idempotency_record.status_code = 202 if sucesso else 502
            db.commit()
        if sucesso:
            trigger_webhook(cliente_id=g.cliente_id, evento='nfse.enviada', payload=result['nfse'])
        return jsonify(result), 202 if sucesso else 502
    except Exception as exc:
        db.rollback()
        _persistir_falha_idempotencia(db, idempotency_record, 500, {
            'success': False, 'error': 'Erro ao emitir NFS-e', 'detail': str(exc)
        })
        return jsonify({'success': False, 'error': 'Erro ao emitir NFS-e', 'detail': str(exc)}), 500


@api_v2_bp.route('/nfse/nacional/emitir', methods=['POST'])
@require_api_key(permissions=['nfse.write', 'nfse.emit'])
def emit_nfse_nacional():
    """Envia DPS XML assinada diretamente à SEFIN Nacional."""
    data = request.get_json(silent=True) or {}
    ambiente = data.get('ambiente') if data.get('ambiente') in ('producao', 'homologacao') else 'homologacao'
    if getattr(g, 'api_environment', 'producao') == 'teste' and ambiente == 'producao':
        return jsonify({'success': False, 'error': 'Chave de teste não pode emitir em produção'}), 403
    xml_dps = data.get('dps_xml')
    db = next(get_db())
    idempotency_record = None
    try:
        idempotency_key = (request.headers.get('Idempotency-Key') or '').strip()
        if idempotency_key:
            if len(idempotency_key) > 255:
                return jsonify({'success': False, 'error': 'Idempotency-Key excede 255 caracteres'}), 400
            request_hash = hashlib.sha256(json.dumps(
                data, sort_keys=True, separators=(',', ':'), default=str
            ).encode('utf-8')).hexdigest()
            from database.models import FiscalApiIdempotency
            idempotency_record = db.query(FiscalApiIdempotency).filter_by(
                cliente_id=g.cliente_id, endpoint='/api/v2/nfse/nacional/emitir',
                idempotency_key=idempotency_key).first()
            if idempotency_record:
                if idempotency_record.request_hash != request_hash:
                    return jsonify({'success': False, 'error': 'Idempotency-Key já utilizada com payload diferente'}), 409
                if idempotency_record.response_json:
                    return jsonify(json.loads(idempotency_record.response_json)), idempotency_record.status_code or 200
                return jsonify({'success': True, 'status': 'PROCESSANDO'}), 202
            idempotency_record = FiscalApiIdempotency(
                cliente_id=g.cliente_id, endpoint='/api/v2/nfse/nacional/emitir',
                idempotency_key=idempotency_key, request_hash=request_hash, status_code=202)
            db.add(idempotency_record)
            try:
                db.commit()
            except Exception:
                db.rollback()
                idempotency_record = db.query(FiscalApiIdempotency).filter_by(
                    cliente_id=g.cliente_id, endpoint='/api/v2/nfse/nacional/emitir',
                    idempotency_key=idempotency_key).first()
                if idempotency_record and idempotency_record.response_json:
                    return jsonify(json.loads(idempotency_record.response_json)), idempotency_record.status_code or 200
        from services.certificate_service import get_active_certificate_for_client
        certificado = get_active_certificate_for_client(db, g.cliente_id)
        if not certificado:
            return jsonify({'success': False, 'error': 'Certificado do cliente não encontrado'}), 400
        from services.nfse_sefin_nacional import emitir_dps, gerar_dps, assinar_dps
        if not isinstance(xml_dps, str) or not xml_dps.strip():
            dps = dict(data.get('dps') or {})
            cliente = db.query(Cliente).filter_by(cliente_id=g.cliente_id).first()
            dps.setdefault('cnpj_prestador', cliente.cnpj if cliente else '')
            dps.setdefault('ambiente', ambiente)
            xml_dps = assinar_dps(gerar_dps(dps), certificado)
        sucesso, resposta = emitir_dps(xml_dps, ambiente, certificado)
        result = {'success': sucesso, 'ambiente': ambiente, 'resultado': resposta}
        if idempotency_record:
            idempotency_record.response_json = json.dumps(result, default=str)
            idempotency_record.status_code = 201 if sucesso else 502
            db.commit()
        return jsonify(result), 201 if sucesso else 502
    except (ValueError, etree.XMLSyntaxError) as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        _persistir_falha_idempotencia(db, idempotency_record, 502,
                                      {'success': False, 'error': 'Falha na SEFIN Nacional', 'detail': str(exc)})
        return jsonify({'success': False, 'error': 'Falha na SEFIN Nacional', 'detail': str(exc)}), 502
    finally:
        db.close()

@api_v2_bp.route('/nfce/emitir', methods=['POST'])
@require_api_key(permissions=['nfce.write', 'nfce.emit'])
def emit_nfce():
    """Emite NFC-e real (modelo 65) pela SEFAZ."""
    db = next(get_db())
    data = request.get_json(silent=True) or {}
    ambiente_ok, ambiente_solicitado = _validar_ambiente_api(data.get('ambiente'))
    if not ambiente_ok:
        return jsonify({'error': 'Chave de teste não pode emitir em produção'}), 403
    itens = data.get('itens') or []
    if not itens:
        return jsonify({'error': 'Pelo menos um item é obrigatório'}), 400

    idempotency_record = None
    idempotency_key = (request.headers.get('Idempotency-Key') or '').strip()
    if idempotency_key:
        if len(idempotency_key) > 255:
            return jsonify({'error': 'Idempotency-Key excede 255 caracteres'}), 400
        request_hash = hashlib.sha256(json.dumps(
            data, sort_keys=True, separators=(',', ':'), default=str
        ).encode('utf-8')).hexdigest()
        from database.models import FiscalApiIdempotency
        idempotency_record = db.query(FiscalApiIdempotency).filter_by(
            cliente_id=g.cliente_id, endpoint='/api/v2/nfce/emitir',
            idempotency_key=idempotency_key,
        ).first()
        if idempotency_record:
            if idempotency_record.request_hash != request_hash:
                return jsonify({'error': 'Idempotency-Key já utilizada com payload diferente'}), 409
            if idempotency_record.response_json:
                return jsonify(json.loads(idempotency_record.response_json)), idempotency_record.status_code or 200
            return jsonify({'success': True, 'status': 'PROCESSANDO',
                            'message': 'Requisição idempotente já está em processamento'}), 202
        else:
            idempotency_record = FiscalApiIdempotency(
                cliente_id=g.cliente_id, endpoint='/api/v2/nfce/emitir',
                idempotency_key=idempotency_key, request_hash=request_hash,
                status_code=202,
            )
            db.add(idempotency_record)
            try:
                db.commit()
            except Exception:
                db.rollback()
                idempotency_record = db.query(FiscalApiIdempotency).filter_by(
                    cliente_id=g.cliente_id, endpoint='/api/v2/nfce/emitir',
                    idempotency_key=idempotency_key,
                ).first()
                if idempotency_record and idempotency_record.response_json:
                    return jsonify(json.loads(idempotency_record.response_json)), idempotency_record.status_code or 200

    cliente = db.query(Cliente).filter_by(cliente_id=g.cliente_id).first()
    if not cliente:
        return jsonify({'error': 'Emitente não encontrado'}), 404
    certificado = __import__('services.certificate_service', fromlist=['get_active_certificate_for_client']).get_active_certificate_for_client(db, g.cliente_id)
    if not certificado or not certificado.get('cert_data') or not certificado.get('password'):
        return jsonify({'error': 'Certificado A1 do emitente não configurado'}), 400

    try:
        serie = int(data.get('serie', 1) or 1)
        numero = db.execute(text(
            "SELECT get_proximo_numero_nfe(:cliente_id, :modelo, :serie)"
        ), {'cliente_id': g.cliente_id, 'modelo': '65', 'serie': serie}).scalar() or 1
    except Exception:
        db.rollback()
        numero = db.query(NFeEmitidas).filter_by(
            cliente_id=g.cliente_id, modelo='65', serie=serie
        ).count() + 1

    emitente = {
        'cnpj': cliente.cnpj,
        'razao_social': cliente.razao_social,
        'nome_fantasia': getattr(cliente, 'nome_fantasia', None),
        'logradouro': cliente.logradouro,
        'numero': cliente.numero,
        'bairro': cliente.bairro,
        'codigo_municipio': cliente.codigo_municipio,
        'municipio': cliente.nome_municipio,
        'uf': cliente.uf,
        'uf_codigo': int(str(cliente.codigo_uf or '35')),
        'cep': cliente.cep,
    }
    itens_xml = []
    for item in itens:
        try:
            quantidade = float(item.get('quantidade', 0))
            unitario = float(item.get('valor_unitario', 0))
        except (TypeError, ValueError):
            return jsonify({'error': 'Quantidade e valor_unitario devem ser numéricos'}), 400
        if quantidade <= 0 or unitario < 0:
            return jsonify({'error': 'Quantidade deve ser positiva e valor não pode ser negativo'}), 400
        itens_xml.append({
            'codigo': str(item.get('codigo') or item.get('produto_id') or '1'),
            'descricao': str(item.get('descricao') or '').strip(),
            'ncm': str(item.get('ncm') or '00000000'),
            'cfop': str(item.get('cfop') or '5102'),
            'unidade': str(item.get('unidade') or 'UN'),
            'quantidade': quantidade,
            'valor_unitario': unitario,
            'valor_total': round(quantidade * unitario, 2),
            'csosn': str(item.get('csosn') or '102'),
            'origem': str(item.get('origem') or '0'),
        })
    if any(not item['descricao'] for item in itens_xml):
        return jsonify({'error': 'Descrição é obrigatória em todos os itens'}), 400

    total = round(sum(item['valor_total'] for item in itens_xml), 2)
    dados_xml = {
        'emitente': emitente,
        'nfce_info': {
            'numero': numero, 'serie': serie, 'modelo': '65',
            'tipo_emissao': '1', 'finalidade': '1', 'destino_operacao': '1',
            'tipo_impressao': '4', 'ambiente': '1' if ambiente_solicitado == 'producao' else '2',
        },
        'itens': itens_xml,
        'destinatario': data.get('destinatario') or {},
        'totais': {'valor_produtos': total, 'valor_desconto': 0, 'valor_total': total,
                   'base_calculo': 0, 'valor_icms': 0},
        'pagamento': {'forma_pagamento': str(data.get('forma_pagamento') or '01'), 'valor': total},
    }
    try:
        from utils.nfce_generator import gerar_xml_nfce
        from routes.nfce_routes import assinar_xml_nfce, enviar_nfce_sefaz
        xml_assinado = assinar_xml_nfce(gerar_xml_nfce(dados_xml), certificado)
        resultado = enviar_nfce_sefaz(xml_assinado, {**emitente, 'numero_nfce': numero, 'serie_nfce': serie}, certificado)
        if not resultado.get('sucesso'):
            return jsonify({'success': False, 'error': resultado.get('erro', 'Rejeição da SEFAZ')}), 502

        nota = NFeEmitidas(
            cliente_id=g.cliente_id, tipo_nfe='1', modelo='65', serie=serie,
            numero=numero, finalidade_emissao=1, natureza_operacao='Venda',
            destinatario_razao_social=(data.get('destinatario') or {}).get('nome', 'Consumidor Final'),
            destinatario_cnpj_cpf=(data.get('destinatario') or {}).get('cpf_cnpj'),
            json_nfe=json.dumps({**data, 'xml_content': xml_assinado, 'numero': numero, 'serie': serie}),
            chave_acesso=resultado.get('chave_acesso'), protocolo_sefaz=resultado.get('protocolo'),
            status='Autorizada', data_emissao=datetime.now(), data_autorizacao=datetime.now(),
            valor_total=total, mensagem_sefaz='NFC-e autorizada pela SEFAZ',
        )
        db.add(nota)
        db.commit()
        trigger_webhook(cliente_id=g.cliente_id, evento='nfce.autorizada', payload={
            'nfce_id': nota.nfe_emitida_id, 'numero': numero, 'serie': serie,
            'chave_acesso': nota.chave_acesso, 'valor_total': total,
        })
        response_payload = {'success': True, 'nfce': {
            'nfce_id': nota.nfe_emitida_id, 'numero': numero, 'serie': serie,
            'chave_acesso': nota.chave_acesso, 'protocolo': nota.protocolo_sefaz,
            'status': nota.status, 'valor_total': total,
        }}
        if idempotency_record:
            idempotency_record.response_json = json.dumps(response_payload, default=str)
            idempotency_record.status_code = 201
            db.commit()
        return jsonify(response_payload), 201
    except Exception as exc:
        db.rollback()
        _persistir_falha_idempotencia(db, idempotency_record, 500, {
            'success': False, 'error': 'Erro ao emitir NFC-e', 'detail': str(exc)
        })
        return jsonify({'success': False, 'error': 'Erro ao emitir NFC-e', 'detail': str(exc)}), 500

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


@api_v2_bp.route('/nfe/<int:nfe_id>/status', methods=['GET'])
@require_api_key(permissions=['nfe.read'])
def get_nfe_status(nfe_id):
    """Consulta o estado local e, quando possível, atualiza pela SEFAZ."""
    db = next(get_db())
    nfe = db.query(NFeEmitidas).filter_by(
        nfe_emitida_id=nfe_id,
        cliente_id=g.cliente_id,
    ).first()
    if not nfe:
        return jsonify({"error": "NFe não encontrada"}), 404

    if not nfe.chave_acesso:
        return jsonify({
            "success": True,
            "nfe_id": nfe.nfe_emitida_id,
            "status": nfe.status,
            "message": nfe.mensagem_sefaz,
            "source": "local",
        }), 200

    try:
        from services.nfe_service import NFeService
        nfe_payload = nfe.json_nfe
        if isinstance(nfe_payload, str):
            try:
                nfe_payload = json.loads(nfe_payload)
            except (TypeError, ValueError):
                nfe_payload = {}
        ambiente = 1 if str((nfe_payload or {}).get('ambiente', '')).lower() == 'producao' else 2
        resultado = NFeService(db).consultar_nfe(nfe.chave_acesso, ambiente)
        if resultado.get('success') and resultado.get('status'):
            nfe.status = str(resultado['status']).upper()
            nfe.mensagem_sefaz = resultado.get('message') or nfe.mensagem_sefaz
            db.commit()
        return jsonify({
            "success": bool(resultado.get('success')),
            "nfe_id": nfe.nfe_emitida_id,
            "status": nfe.status,
            "chave_acesso": nfe.chave_acesso,
            "protocolo": nfe.protocolo_sefaz,
            "message": resultado.get('message') or resultado.get('motivo') or nfe.mensagem_sefaz,
            "source": "sefaz",
        }), 200 if resultado.get('success') else 502
    except Exception as exc:
        db.rollback()
        return jsonify({
            "success": False,
            "nfe_id": nfe.nfe_emitida_id,
            "status": nfe.status,
            "message": "Não foi possível consultar a SEFAZ neste momento",
            "detail": str(exc),
            "source": "local",
        }), 502


@api_v2_bp.route('/nfces', methods=['GET'])
@require_api_key(permissions=['nfce.read'])
def list_nfces():
    """Lista NFC-e do cliente autenticado."""
    db = next(get_db())
    limite = min(max(request.args.get('limit', 50, type=int), 1), 100)
    offset = max(request.args.get('offset', 0, type=int), 0)
    query = db.query(NFeEmitidas).filter_by(cliente_id=g.cliente_id, modelo='65')
    total = query.count()
    notas = query.order_by(NFeEmitidas.data_emissao.desc()).limit(limite).offset(offset).all()
    return jsonify({
        'success': True,
        'total': total,
        'limit': limite,
        'offset': offset,
        'nfces': [nota.to_dict() for nota in notas],
    }), 200


@api_v2_bp.route('/nfce/<int:nfce_id>', methods=['GET'])
@require_api_key(permissions=['nfce.read'])
def get_nfce(nfce_id):
    """Consulta uma NFC-e pertencente ao cliente da API Key."""
    db = next(get_db())
    nota = db.query(NFeEmitidas).filter_by(
        nfe_emitida_id=nfce_id, cliente_id=g.cliente_id, modelo='65'
    ).first()
    if not nota:
        return jsonify({'error': 'NFC-e não encontrada'}), 404
    return jsonify({'success': True, 'nfce': nota.to_dict()}), 200


@api_v2_bp.route('/nfce/<int:nfce_id>/status', methods=['GET'])
@require_api_key(permissions=['nfce.read'])
def get_nfce_status(nfce_id):
    """Consulta o status local e, quando possível, atualiza na SEFAZ."""
    db = next(get_db())
    nota = db.query(NFeEmitidas).filter_by(
        nfe_emitida_id=nfce_id, cliente_id=g.cliente_id, modelo='65'
    ).first()
    if not nota:
        return jsonify({'error': 'NFC-e não encontrada'}), 404
    if not nota.chave_acesso:
        return jsonify({'success': True, 'nfce_id': nfce_id,
                        'status': nota.status, 'source': 'local'}), 200
    try:
        payload = nota.json_nfe
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (TypeError, ValueError):
                payload = {}
        ambiente = 'producao' if str((payload or {}).get('ambiente', '')).lower() in ('producao', '1') else 'homologacao'
        from routes.nfce_routes import consultar_nfce
        resultado = consultar_nfce(nota.chave_acesso, ambiente=ambiente)
        if resultado.get('sucesso') and resultado.get('status'):
            nota.status = str(resultado['status']).upper()
            nota.mensagem_sefaz = resultado.get('message') or nota.mensagem_sefaz
            db.commit()
        return jsonify({'success': bool(resultado.get('sucesso')), 'nfce_id': nfce_id,
                        'status': nota.status, 'chave_acesso': nota.chave_acesso,
                        'protocolo': nota.protocolo_sefaz,
                        'message': resultado.get('message') or nota.mensagem_sefaz,
                        'source': 'sefaz'}), 200 if resultado.get('sucesso') else 502
    except Exception as exc:
        db.rollback()
        return jsonify({'success': False, 'nfce_id': nfce_id, 'status': nota.status,
                        'message': 'Não foi possível consultar a SEFAZ neste momento',
                        'detail': str(exc), 'source': 'local'}), 502


@api_v2_bp.route('/nfce/<int:nfce_id>/xml', methods=['GET'])
@require_api_key(permissions=['nfce.read'])
def get_nfce_xml(nfce_id):
    """Baixa o XML assinado/autorizado da NFC-e."""
    db = next(get_db())
    nota = db.query(NFeEmitidas).filter_by(
        nfe_emitida_id=nfce_id, cliente_id=g.cliente_id, modelo='65'
    ).first()
    if not nota:
        return jsonify({'error': 'NFC-e não encontrada'}), 404
    payload = nota.json_nfe
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            payload = {}
    xml_content = payload.get('xml_content') if isinstance(payload, dict) else None
    if not xml_content:
        return jsonify({'error': 'XML ainda não disponível', 'status': nota.status}), 404
    response = Response(xml_content, mimetype='application/xml')
    response.headers['Content-Disposition'] = (
        f'attachment; filename=NFCe_{nota.chave_acesso or nfce_id}.xml'
    )
    return response


@api_v2_bp.route('/nfce/<int:nfce_id>/cancelar', methods=['POST'])
@require_api_key(permissions=['nfce.write', 'nfce.cancel'])
def cancel_nfce(nfce_id):
    """Solicita cancelamento real da NFC-e na SEFAZ."""
    db = next(get_db())
    nota = db.query(NFeEmitidas).filter_by(
        nfe_emitida_id=nfce_id, cliente_id=g.cliente_id, modelo='65'
    ).first()
    if not nota:
        return jsonify({'error': 'NFC-e não encontrada'}), 404
    if str(nota.status).upper() not in {'AUTORIZADA', 'AUTORIZADA'}:
        return jsonify({'error': 'Apenas NFC-e autorizadas podem ser canceladas'}), 400
    payload = request.get_json(silent=True) or {}
    justificativa = str(payload.get('justificativa') or '').strip()
    if len(justificativa) < 15:
        return jsonify({'error': 'Justificativa deve ter no mínimo 15 caracteres'}), 400
    certificado = __import__('services.certificate_service', fromlist=['get_active_certificate_for_client']).get_active_certificate_for_client(db, g.cliente_id)
    if not certificado:
        return jsonify({'error': 'Certificado do cliente não encontrado'}), 400
    from routes.nfce_routes import cancelar_nfce as cancelar_nfce_real
    cliente = db.query(Cliente).filter_by(cliente_id=g.cliente_id).first()
    resultado = cancelar_nfce_real(
        nota.chave_acesso,
        justificativa,
        {'cnpj': cliente.cnpj if cliente else '', 'protocolo_sefaz': nota.protocolo_sefaz},
        certificado,
        ambiente=('producao' if '<tpAmb>1</tpAmb>' in str((nota.json_nfe or '')) else 'homologacao'),
    )
    if not resultado.get('sucesso'):
        return jsonify({'success': False, 'error': resultado.get('erro') or resultado.get('message')}), 502
    nota.status = 'Cancelada'
    db.commit()
    trigger_webhook(
        cliente_id=g.cliente_id,
        evento='nfce.cancelada',
        payload={'nfce_id': nfce_id, 'chave_acesso': nota.chave_acesso,
                 'protocolo': resultado.get('protocolo')},
    )
    return jsonify({'success': True, 'nfce_id': nfce_id,
                    'protocolo': resultado.get('protocolo')}), 200


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
    
    # O fluxo atual persiste o XML autorizado dentro de json_nfe. Aceitamos
    # tanto JSONB (PostgreSQL) quanto texto JSON (ambientes legados).
    payload = nfe.json_nfe
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            payload = {}

    xml_content = (payload or {}).get('xml_content') if isinstance(payload, dict) else None
    if not xml_content:
        return jsonify({
            "error": "XML ainda não disponível",
            "message": "O XML só fica disponível após autorização da NF-e.",
            "status": nfe.status
        }), 404

    response = Response(xml_content, mimetype='application/xml')
    response.headers['Content-Disposition'] = (
        f'attachment; filename=NFe_{nfe.chave_acesso or nfe.nfe_emitida_id}.xml'
    )
    return response


@api_v2_bp.route('/nfe/<int:nfe_id>/cancelar', methods=['POST'])
@require_api_key(permissions=['nfe.write', 'nfe.cancel'])
def cancel_nfe(nfe_id):
    """Cancela uma NFe"""
    db = next(get_db())
    data = request.get_json()
    
    nfe = db.query(NFeEmitidas).filter_by(
        nfe_emitida_id=nfe_id,
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
        if not nfe.chave_acesso or len(nfe.chave_acesso) != 44:
            return jsonify({"error": "Chave de acesso inválida"}), 400
        if not nfe.protocolo_sefaz:
            return jsonify({"error": "Protocolo de autorização não encontrado"}), 400

        payload = nfe.json_nfe
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (TypeError, ValueError):
                payload = {}
        xml_content = (payload or {}).get('xml_content', '') if isinstance(payload, dict) else ''
        ambiente = 'producao' if '<tpAmb>1</tpAmb>' in xml_content else 'homologacao'

        from services.certificate_service import get_active_certificate_for_client
        certificado = get_active_certificate_for_client(db, g.cliente_id)
        if not certificado:
            return jsonify({"error": "Certificado do cliente não encontrado"}), 400
        cert_data = certificado.get('cert_data') or certificado.get('arquivo_certificado')
        cert_password = certificado.get('password') or certificado.get('senha_certificado')
        if not cert_data or not cert_password:
            return jsonify({"error": "Certificado ou senha não configurado"}), 400

        from services.sefaz_service import SefazService
        resultado = SefazService(ambiente=ambiente).cancelar_nfe(
            chave_nfe=nfe.chave_acesso,
            protocolo=nfe.protocolo_sefaz,
            justificativa=justificativa.strip(),
            cnpj_emitente=nfe.cliente.cnpj if nfe.cliente else '',
            certificado_pfx=cert_data,
            senha_certificado=cert_password,
        )
        if not resultado.get('success'):
            return jsonify({
                "success": False,
                "error": "Falha no cancelamento pela SEFAZ",
                "message": resultado.get('message', 'Cancelamento rejeitado'),
                "code": resultado.get('codigo'),
            }), 502

        # Campos legados de cancelamento existem na tabela fiscal mesmo quando
        # ainda não estão declarados no modelo ORM.
        db.execute(text("""
            UPDATE nfe_emitidas
               SET status = 'CANCELADA',
                   protocolo_cancelamento = :protocolo,
                   data_cancelamento = :data_cancelamento,
                   justificativa_cancelamento = :justificativa
             WHERE nfe_emitida_id = :nfe_id AND cliente_id = :cliente_id
        """), {
            'protocolo': resultado.get('protocolo'),
            'data_cancelamento': datetime.now(),
            'justificativa': justificativa.strip(),
            'nfe_id': nfe_id,
            'cliente_id': g.cliente_id,
        })
        db.commit()
        trigger_webhook(
            cliente_id=g.cliente_id,
            evento='nfe.cancelada',
            payload={'nfe_id': nfe_id, 'chave_acesso': nfe.chave_acesso,
                     'protocolo': resultado.get('protocolo')},
        )
        return jsonify({
            "success": True,
            "message": "NFe cancelada com sucesso na SEFAZ",
            "nfe_id": nfe_id,
            "chave_acesso": nfe.chave_acesso,
            "protocolo": resultado.get('protocolo'),
        }), 200
    
    except Exception as e:
        return jsonify({
            "error": "Erro ao cancelar NFe",
            "message": str(e)
        }), 500

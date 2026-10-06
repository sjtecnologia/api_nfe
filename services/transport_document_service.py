"""Domínio e transmissão de documentos fiscais de transporte.

O provider é deliberadamente configurável: endpoints e token reais devem ser
fornecidos pelo ambiente de homologação/produção. Sem eles, nenhuma
autorização simulada é retornada.
"""
import json
import os
import hashlib
from datetime import datetime
from urllib.parse import urljoin

import requests
from sqlalchemy import text


SUPPORTED_TYPES = {'cte', 'cte_os', 'cte_simplificado', 'mdfe'}


def validate_transport_payload(tipo, payload):
    if tipo not in SUPPORTED_TYPES:
        return False, 'tipo_documento inválido'
    if not isinstance(payload, dict):
        return False, 'documento deve ser um objeto JSON'
    if not payload.get('emitente'):
        return False, 'emitente é obrigatório'
    if not payload.get('tomador') and tipo.startswith('cte'):
        return False, 'tomador é obrigatório para CT-e'
    if not payload.get('carga') and tipo in {'cte', 'cte_os', 'cte_simplificado', 'mdfe'}:
        return False, 'carga é obrigatória'
    if tipo == 'mdfe' and not payload.get('modal'):
        return False, 'modal é obrigatório para MDF-e'
    return True, None


def submit_transport_document(tipo, ambiente, referencia, payload, xml_envio=None):
    """Transmite para um adapter HTTP configurado e normaliza sua resposta."""
    base_url = os.getenv(f'FISCAL_{tipo.upper()}_URL') or os.getenv('FISCAL_TRANSPORT_URL')
    token = os.getenv(f'FISCAL_{tipo.upper()}_TOKEN') or os.getenv('FISCAL_TRANSPORT_TOKEN')
    if not base_url or not token:
        return False, {'status': 'NAO_CONFIGURADO',
                       'mensagem': 'Provider de transporte não configurado para este ambiente'}
    try:
        url = urljoin(base_url.rstrip('/') + '/', ambiente + '/' + tipo)
        response = requests.post(
            url,
            json={'referencia': referencia, 'documento': payload, 'xml': xml_envio},
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=int(os.getenv('FISCAL_TRANSPORT_TIMEOUT', '60')),
        )
        body = response.json() if response.content else {}
        if 200 <= response.status_code < 300:
            return True, {
                'status': body.get('status') or 'PROCESSANDO',
                'chave_acesso': body.get('chave_acesso') or body.get('chave'),
                'protocolo': body.get('protocolo'),
                'codigo_status': body.get('codigo_status'),
                'mensagem': body.get('mensagem') or body.get('message'),
                'xml_autorizado': body.get('xml_autorizado') or body.get('xml'),
            }
        return False, {'status': 'REJEITADA', 'codigo_status': str(response.status_code),
                       'mensagem': str(body.get('mensagem') or body.get('message') or response.text)[:1000]}
    except requests.RequestException as exc:
        return False, {'status': 'ERRO', 'mensagem': str(exc)[:1000]}


def operate_transport_document(tipo, ambiente, referencia, operation, payload=None):
    """Executa consulta/cancelamento/encerramento no provider configurado."""
    base_url = os.getenv(f'FISCAL_{tipo.upper()}_URL') or os.getenv('FISCAL_TRANSPORT_URL')
    token = os.getenv(f'FISCAL_{tipo.upper()}_TOKEN') or os.getenv('FISCAL_TRANSPORT_TOKEN')
    if not base_url or not token:
        return False, {'status': 'NAO_CONFIGURADO', 'mensagem': 'Provider de transporte não configurado'}
    try:
        url = urljoin(base_url.rstrip('/') + '/', ambiente + '/' + tipo + '/' + referencia + '/' + operation)
        response = requests.post(url, json=payload or {}, headers={'Authorization': f'Bearer {token}'},
                                 timeout=int(os.getenv('FISCAL_TRANSPORT_TIMEOUT', '60')))
        body = response.json() if response.content else {}
        result = {
            'status': body.get('status'), 'chave_acesso': body.get('chave_acesso') or body.get('chave'),
            'protocolo': body.get('protocolo'), 'codigo_status': body.get('codigo_status'),
            'mensagem': body.get('mensagem') or body.get('message'),
            'xml_autorizado': body.get('xml_autorizado') or body.get('xml'),
        }
        return (200 <= response.status_code < 300), result
    except requests.RequestException as exc:
        return False, {'status': 'ERRO', 'mensagem': str(exc)[:1000]}


def insert_transport_document(db, cliente_id, tipo, ambiente, referencia, payload, xml_envio=None):
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    result = db.execute(text("""
        INSERT INTO transport_documents
          (cliente_id, tipo_documento, ambiente, referencia, status, payload_json, payload_hash, xml_envio, created_at, updated_at)
        VALUES (:cliente_id, :tipo, :ambiente, :referencia, 'ENVIANDO', :payload, :payload_hash, :xml, :now, :now)
        RETURNING id
    """), {'cliente_id': cliente_id, 'tipo': tipo, 'ambiente': ambiente,
           'referencia': referencia, 'payload': json.dumps(payload, default=str), 'payload_hash': payload_hash,
           'xml': xml_envio, 'now': datetime.now()})
    return result.scalar_one()

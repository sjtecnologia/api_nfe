from flask import Blueprint, jsonify, request, g
from sqlalchemy import text
import json
import hashlib

from auth.api_key_auth import require_api_key
from database.connection import get_db
from services.transport_document_service import (
    insert_transport_document, submit_transport_document, operate_transport_document,
    validate_transport_payload,
)
from services.webhook_service import trigger_webhook

transport_bp = Blueprint('transport_documents', __name__, url_prefix='/api/v2')


@transport_bp.route('/transport-documents/emitir', methods=['POST'])
@require_api_key(permissions=['transport.write', 'transport.emit'])
def emit_transport_document(forced_type=None):
    db = next(get_db())
    data = request.get_json(silent=True) or {}
    tipo = str(forced_type or data.get('tipo_documento') or '').lower()
    if forced_type and data.get('tipo_documento') and str(data['tipo_documento']).lower() != tipo:
        return jsonify({'success': False, 'error': 'tipo_documento não corresponde à rota'}), 400
    ambiente = data.get('ambiente') if data.get('ambiente') in ('producao', 'homologacao') else 'homologacao'
    if getattr(g, 'api_environment', 'producao') == 'teste' and ambiente == 'producao':
        return jsonify({'success': False, 'error': 'Chave de teste não pode emitir em produção'}), 403
    payload = data.get('documento') or {}
    ok, error = validate_transport_payload(tipo, payload)
    if not ok:
        return jsonify({'success': False, 'error': error}), 400
    referencia = str(data.get('referencia') or '').strip()
    if not referencia or len(referencia) > 80:
        return jsonify({'success': False, 'error': 'referencia obrigatória (até 80 caracteres)'}), 400
    try:
        existing = db.execute(text("""
            SELECT id, status, chave_acesso, protocolo, mensagem, payload_hash
            FROM transport_documents
            WHERE cliente_id=:cliente_id AND tipo_documento=:tipo AND referencia=:referencia
        """), {'cliente_id': g.cliente_id, 'tipo': tipo, 'referencia': referencia}).mappings().first()
        if existing:
            requested_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
            if existing['payload_hash'] != requested_hash:
                return jsonify({'success': False, 'error': 'referencia já utilizada com documento diferente'}), 409
            return jsonify({'success': True, 'idempotent': True, 'documento': dict(existing)}), 200
        document_id = insert_transport_document(db, g.cliente_id, tipo, ambiente, referencia, payload, data.get('xml'))
        db.commit()
        success, result = submit_transport_document(tipo, ambiente, referencia, payload, data.get('xml'))
        db.execute(text("""
            UPDATE transport_documents SET status=:status, chave_acesso=:chave,
              protocolo=:protocolo, codigo_status=:codigo, mensagem=:mensagem,
              xml_autorizado=:xml, updated_at=CURRENT_TIMESTAMP,
              authorized_at=CASE WHEN :status='AUTORIZADA' THEN CURRENT_TIMESTAMP ELSE authorized_at END
            WHERE id=:id AND cliente_id=:cliente_id
        """), {'status': result.get('status', 'ERRO'), 'chave': result.get('chave_acesso'),
               'protocolo': result.get('protocolo'), 'codigo': result.get('codigo_status'),
               'mensagem': result.get('mensagem'), 'xml': result.get('xml_autorizado'),
               'id': document_id, 'cliente_id': g.cliente_id})
        db.commit()
        return jsonify({'success': success, 'documento': {'id': document_id, 'tipo_documento': tipo,
            'referencia': referencia, **result}}), 202 if result.get('status') in ('PROCESSANDO', 'NAO_CONFIGURADO') else (201 if success else 502)
    except Exception as exc:
        db.rollback()
        return jsonify({'success': False, 'error': 'Erro ao emitir documento de transporte', 'detail': str(exc)}), 500


@transport_bp.route('/transport-documents', methods=['GET'])
@require_api_key(permissions=['transport.read'])
def list_transport_documents():
    db = next(get_db())
    tipo = request.args.get('tipo_documento')
    query = "SELECT id, tipo_documento, ambiente, referencia, status, chave_acesso, protocolo, codigo_status, mensagem, created_at FROM transport_documents WHERE cliente_id=:cliente_id"
    params = {'cliente_id': g.cliente_id}
    if tipo:
        query += ' AND tipo_documento=:tipo'
        params['tipo'] = tipo
    query += ' ORDER BY created_at DESC LIMIT 100'
    rows = db.execute(text(query), params).mappings().all()
    return jsonify({'success': True, 'documentos': [dict(row) for row in rows]}), 200


@transport_bp.route('/transport-documents/<int:document_id>', methods=['GET'])
@require_api_key(permissions=['transport.read'])
def get_transport_document(document_id):
    db = next(get_db())
    row = db.execute(text("SELECT * FROM transport_documents WHERE id=:id AND cliente_id=:cliente_id"),
                     {'id': document_id, 'cliente_id': g.cliente_id}).mappings().first()
    if not row:
        return jsonify({'error': 'Documento de transporte não encontrado'}), 404
    return jsonify({'success': True, 'documento': dict(row)}), 200


@transport_bp.route('/transport-documents/<int:document_id>/status', methods=['GET'])
@require_api_key(permissions=['transport.read'])
def status_transport_document(document_id):
    db = next(get_db())
    row = db.execute(text('SELECT * FROM transport_documents WHERE id=:id AND cliente_id=:cliente_id'),
                     {'id': document_id, 'cliente_id': g.cliente_id}).mappings().first()
    if not row:
        return jsonify({'error': 'Documento de transporte não encontrado'}), 404
    ok, result = operate_transport_document(row['tipo_documento'], row['ambiente'], row['referencia'], 'status')
    if ok and result.get('status'):
        db.execute(text("""UPDATE transport_documents SET status=:status, chave_acesso=COALESCE(:chave,chave_acesso),
            protocolo=COALESCE(:protocolo,protocolo), codigo_status=:codigo, mensagem=:mensagem,
            xml_autorizado=COALESCE(:xml,xml_autorizado), updated_at=CURRENT_TIMESTAMP WHERE id=:id AND cliente_id=:cliente_id"""),
                   {**result, 'id': document_id, 'cliente_id': g.cliente_id})
        db.commit()
    return jsonify({'success': ok, 'documento': {'id': document_id, **result,
        'status': result.get('status') or row['status']}}), 200 if ok else 502


@transport_bp.route('/transport-documents/<int:document_id>/xml', methods=['GET'])
@require_api_key(permissions=['transport.read'])
def xml_transport_document(document_id):
    db = next(get_db())
    row = db.execute(text('SELECT tipo_documento, chave_acesso, status, xml_autorizado FROM transport_documents WHERE id=:id AND cliente_id=:cliente_id'),
                     {'id': document_id, 'cliente_id': g.cliente_id}).mappings().first()
    if not row:
        return jsonify({'error': 'Documento de transporte não encontrado'}), 404
    if not row['xml_autorizado']:
        return jsonify({'error': 'XML ainda não disponível', 'status': row['status']}), 404
    from flask import Response
    response = Response(row['xml_autorizado'], mimetype='application/xml')
    response.headers['Content-Disposition'] = f"attachment; filename={row['tipo_documento'].upper()}_{row['chave_acesso'] or document_id}.xml"
    return response


def _operate_transport_mutation(document_id, operation):
    db = next(get_db())
    row = db.execute(text('SELECT * FROM transport_documents WHERE id=:id AND cliente_id=:cliente_id'),
                     {'id': document_id, 'cliente_id': g.cliente_id}).mappings().first()
    if not row:
        return jsonify({'error': 'Documento de transporte não encontrado'}), 404
    if operation == 'encerrar' and row['tipo_documento'] != 'mdfe':
        return jsonify({'error': 'Somente MDF-e pode ser encerrado'}), 400
    if operation == 'cancelar' and row['status'] not in ('AUTORIZADA', 'AUTORIZADO'):
        return jsonify({'error': 'Somente documento autorizado pode ser cancelado'}), 400
    payload = request.get_json(silent=True) or {}
    if operation == 'cancelar' and len(str(payload.get('justificativa') or '').strip()) < 15:
        return jsonify({'error': 'Justificativa deve ter no mínimo 15 caracteres'}), 400
    ok, result = operate_transport_document(row['tipo_documento'], row['ambiente'], row['referencia'], operation, payload)
    if not ok:
        return jsonify({'success': False, 'error': result.get('mensagem'), 'status': result.get('status')}), 502
    new_status = 'CANCELADA' if operation == 'cancelar' else ('ENCERRADA' if operation == 'encerrar' else result.get('status') or row['status'])
    db.execute(text("UPDATE transport_documents SET status=:status, protocolo=COALESCE(:protocolo,protocolo), mensagem=:mensagem, updated_at=CURRENT_TIMESTAMP WHERE id=:id AND cliente_id=:cliente_id"),
               {'status': new_status, 'protocolo': result.get('protocolo'), 'mensagem': result.get('mensagem'), 'id': document_id, 'cliente_id': g.cliente_id})
    db.commit()
    trigger_webhook(cliente_id=g.cliente_id, evento=f"{row['tipo_documento']}.{operation}",
                    payload={'id': document_id, 'referencia': row['referencia'], 'status': new_status, **result})
    return jsonify({'success': True, 'documento': {'id': document_id, 'status': new_status, **result}}), 200


@transport_bp.route('/transport-documents/<int:document_id>/cancelar', methods=['POST'])
@require_api_key(permissions=['transport.write', 'transport.cancel'])
def cancel_transport_document(document_id):
    return _operate_transport_mutation(document_id, 'cancelar')


@transport_bp.route('/transport-documents/<int:document_id>/encerrar', methods=['POST'])
@require_api_key(permissions=['transport.write', 'transport.close'])
def close_transport_document(document_id):
    return _operate_transport_mutation(document_id, 'encerrar')


# Aliases estáveis para integrações, sem duplicar o fluxo de autenticação e
# persistência da rota genérica.
for _path, _kind in (
    ('/cte/emitir', 'cte'),
    ('/cte-os/emitir', 'cte_os'),
    ('/cte-simplificado/emitir', 'cte_simplificado'),
    ('/mdfe/emitir', 'mdfe'),
):
    transport_bp.add_url_rule(
        _path, endpoint=f'emit_{_kind}', view_func=emit_transport_document,
        defaults={'forced_type': _kind}, methods=['POST'],
    )

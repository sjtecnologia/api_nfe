"""
Rotas para gerenciamento de Webhooks
"""
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required
from database.connection import get_db
from database.models import Webhook, WebhookQueue
from auth.permissions import get_accessible_client_ids
from auth.api_key_auth import require_api_key
from services.webhook_service import validate_webhook_url
import json

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/admin/webhooks')


# ==================== INTERFACE WEB ====================

@webhooks_bp.route('/<int:cliente_id>', methods=['GET'])
@login_required
def list_webhooks(cliente_id):
    """Lista webhooks de um cliente"""
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    if cliente_id not in accessible_client_ids:
        flash('Acesso negado para este cliente.', 'error')
        return redirect(url_for('home.index'))
    
    from database.models import Cliente
    cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
    
    webhooks = db.query(Webhook).filter_by(cliente_id=cliente_id).order_by(Webhook.criado_em.desc()).all()
    
    return render_template('admin/webhooks/list.html',
                         cliente=cliente,
                         webhooks=webhooks,
                         cliente_id=cliente_id)


@webhooks_bp.route('/<int:cliente_id>/create', methods=['GET', 'POST'])
@login_required
def create_webhook(cliente_id):
    """Cria um novo webhook"""
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    if cliente_id not in accessible_client_ids:
        flash('Acesso negado para este cliente.', 'error')
        return redirect(url_for('home.index'))
    
    if request.method == 'POST':
        url = request.form.get('url')
        eventos = request.form.getlist('eventos')
        secret = request.form.get('secret')
        retry_count = request.form.get('retry_count', 3, type=int)
        timeout_seconds = request.form.get('timeout_seconds', 30, type=int)
        
        if not url:
            flash('URL é obrigatória.', 'error')
            return redirect(url_for('webhooks.create_webhook', cliente_id=cliente_id))

        url_ok, url_error = validate_webhook_url(url)
        if not url_ok:
            flash(f'URL de webhook inválida: {url_error}.', 'error')
            return redirect(url_for('webhooks.create_webhook', cliente_id=cliente_id))
        
        if not eventos:
            flash('Selecione pelo menos um evento.', 'error')
            return redirect(url_for('webhooks.create_webhook', cliente_id=cliente_id))
        
        eventos_json = json.dumps(eventos)
        
        webhook = Webhook(
            cliente_id=cliente_id,
            url=url,
            eventos=eventos_json,
            secret=secret if secret else None,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds
        )
        
        db.add(webhook)
        db.commit()
        
        flash('Webhook criado com sucesso!', 'success')
        return redirect(url_for('webhooks.list_webhooks', cliente_id=cliente_id))
    
    from database.models import Cliente
    cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
    
    # Eventos disponíveis
    eventos_disponiveis = [
        ('nfe.autorizada', 'NFe Autorizada'),
        ('nfe.rejeitada', 'NFe Rejeitada'),
        ('nfe.cancelada', 'NFe Cancelada'),
        ('nfe.inutilizada', 'NFe Inutilizada'),
        ('nfce.autorizada', 'NFCe Autorizada'),
        ('nfce.cancelada', 'NFCe Cancelada'),
    ]
    
    return render_template('admin/webhooks/create.html',
                         cliente=cliente,
                         cliente_id=cliente_id,
                         eventos_disponiveis=eventos_disponiveis)


@webhooks_bp.route('/<int:webhook_id>/toggle', methods=['POST'])
@login_required
def toggle_webhook(webhook_id):
    """Ativa/desativa um webhook"""
    db = next(get_db())
    webhook = db.query(Webhook).filter_by(webhook_id=webhook_id).first()
    
    if not webhook:
        flash('Webhook não encontrado.', 'error')
        return redirect(url_for('home.index'))
    
    accessible_client_ids = get_accessible_client_ids(db)
    if webhook.cliente_id not in accessible_client_ids:
        flash('Acesso negado.', 'error')
        return redirect(url_for('home.index'))
    
    webhook.ativo = not webhook.ativo
    db.commit()
    
    status = 'ativado' if webhook.ativo else 'desativado'
    flash(f'Webhook {status} com sucesso.', 'success')
    return redirect(url_for('webhooks.list_webhooks', cliente_id=webhook.cliente_id))


@webhooks_bp.route('/<int:webhook_id>/delete', methods=['POST'])
@login_required
def delete_webhook(webhook_id):
    """Exclui um webhook"""
    db = next(get_db())
    webhook = db.query(Webhook).filter_by(webhook_id=webhook_id).first()
    
    if not webhook:
        flash('Webhook não encontrado.', 'error')
        return redirect(url_for('home.index'))
    
    accessible_client_ids = get_accessible_client_ids(db)
    if webhook.cliente_id not in accessible_client_ids:
        flash('Acesso negado.', 'error')
        return redirect(url_for('home.index'))
    
    cliente_id = webhook.cliente_id
    db.delete(webhook)
    db.commit()
    
    flash('Webhook excluído com sucesso.', 'success')
    return redirect(url_for('webhooks.list_webhooks', cliente_id=cliente_id))


@webhooks_bp.route('/<int:webhook_id>/test', methods=['POST'])
@login_required
def test_webhook(webhook_id):
    """Envia um evento de teste para o webhook"""
    db = next(get_db())
    webhook = db.query(Webhook).filter_by(webhook_id=webhook_id).first()
    
    if not webhook:
        return jsonify({"error": "Webhook não encontrado"}), 404
    
    accessible_client_ids = get_accessible_client_ids(db)
    if webhook.cliente_id not in accessible_client_ids:
        return jsonify({"error": "Acesso negado"}), 403
    
    # Enviar evento de teste
    from services.webhook_service import trigger_webhook
    trigger_webhook(
        cliente_id=webhook.cliente_id,
        evento='test.ping',
        payload={
            'message': 'Teste de webhook',
            'webhook_id': webhook.webhook_id
        }
    )
    
    return jsonify({"success": True, "message": "Evento de teste enviado"}), 200


# ==================== API ENDPOINTS ====================

@webhooks_bp.route('/api/v2/webhooks', methods=['GET'])
@require_api_key(permissions=['admin'])
def api_list_webhooks():
    """Lista webhooks via API"""
    from flask import g
    db = next(get_db())
    
    webhooks = db.query(Webhook).filter_by(cliente_id=g.cliente_id).all()
    
    return jsonify({
        'success': True,
        'webhooks': [w.to_dict() for w in webhooks]
    }), 200


@webhooks_bp.route('/api/v2/webhooks', methods=['POST'])
@require_api_key(permissions=['admin'])
def api_create_webhook():
    """Cria webhook via API"""
    from flask import g
    db = next(get_db())
    data = request.get_json()
    
    if not data.get('url'):
        return jsonify({"error": "URL obrigatória"}), 400

    url_ok, url_error = validate_webhook_url(data.get('url'))
    if not url_ok:
        return jsonify({"error": "URL de webhook inválida", "message": url_error}), 400
    
    if not data.get('eventos'):
        return jsonify({"error": "Lista de eventos obrigatória"}), 400
    
    webhook = Webhook(
        cliente_id=g.cliente_id,
        url=data['url'],
        eventos=json.dumps(data['eventos']),
        secret=data.get('secret'),
        retry_count=data.get('retry_count', 3),
        timeout_seconds=data.get('timeout_seconds', 30)
    )
    
    db.add(webhook)
    db.commit()
    
    return jsonify({
        'success': True,
        'webhook': webhook.to_dict()
    }), 201


@webhooks_bp.route('/api/v2/webhooks/<int:webhook_id>', methods=['DELETE'])
@require_api_key(permissions=['admin'])
def api_delete_webhook(webhook_id):
    """Exclui webhook via API"""
    from flask import g
    db = next(get_db())
    
    webhook = db.query(Webhook).filter_by(
        webhook_id=webhook_id,
        cliente_id=g.cliente_id
    ).first()
    
    if not webhook:
        return jsonify({"error": "Webhook não encontrado"}), 404
    
    db.delete(webhook)
    db.commit()
    
    return jsonify({"success": True, "message": "Webhook excluído"}), 200

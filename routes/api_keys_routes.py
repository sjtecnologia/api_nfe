"""
Rotas para gerenciamento de API Keys
"""
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for, abort
from markupsafe import Markup
from flask_login import login_required, current_user
from database.connection import get_db
from database.models import ApiKey, ApiUsageLog, Webhook, WebhookQueue
from auth.permissions import get_accessible_client_ids
from auth.api_key_auth import generate_api_key, require_api_key
from datetime import datetime, timedelta
import markdown
import os
from pathlib import Path
import json
import markdown
import os
from pathlib import Path

api_keys_bp = Blueprint('api_keys', __name__, url_prefix='/admin/api-keys')


# ==================== INTERFACE WEB (Admin) ====================

@api_keys_bp.route('/<int:cliente_id>', methods=['GET'])
@login_required
def list_api_keys(cliente_id):
    """Lista as API Keys de um cliente"""
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    if cliente_id not in accessible_client_ids:
        flash('Acesso negado para este cliente.', 'error')
        return redirect(url_for('home.home'))
    
    from database.models import Cliente
    cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
    
    if not cliente:
        flash('Cliente não encontrado.', 'error')
        return redirect(url_for('home.home'))
    
    api_keys = db.query(ApiKey).filter_by(cliente_id=cliente_id).order_by(ApiKey.criada_em.desc()).all()
    
    return render_template('admin/api_keys/list.html',
                         cliente=cliente,
                         api_keys=api_keys,
                         cliente_id=cliente_id,
                         now=datetime.now())


@api_keys_bp.route('/docs', methods=['GET'])
@api_keys_bp.route('/docs/<path:doc_name>', methods=['GET'])
@login_required
def api_documentation(doc_name=None):
    """Exibe a documentação da API em HTML"""
    # Documentações disponíveis
    docs_disponiveis = {
        'tributacao-automatica': {
            'arquivo': 'API_TRIBUTACAO_AUTOMATICA.md',
            'titulo': 'API v2 - Tributação Automática',
            'descricao': 'Guia completo para usar a API v2 com busca automática de regras tributárias'
        },
        'tributacao-completo': {
            'arquivo': 'TRIBUTACAO_AUTOMATICA_COMPLETO.md',
            'titulo': 'Sistema de Tributação Automática - Documentação Completa',
            'descricao': 'Documentação técnica detalhada do sistema de tributação automática'
        },
        'integracao': {
            'arquivo': 'API_INTEGRACAO_MANUAL.md',
            'titulo': 'Manual de Integração da API',
            'descricao': 'Manual completo para integração com a API do sistema'
        }
    }
    
    # Se não especificou, mostra lista de documentações
    if not doc_name:
        return render_template('admin/api_keys/docs_index.html',
                             docs=docs_disponiveis)
    
    # Buscar a documentação solicitada
    if doc_name not in docs_disponiveis:
        abort(404)
    
    doc_info = docs_disponiveis[doc_name]
    
    # Ler arquivo markdown
    docs_path = Path(__file__).parent.parent / 'docs' / doc_info['arquivo']
    
    if not docs_path.exists():
        flash(f'Arquivo de documentação não encontrado: {doc_info["arquivo"]}', 'error')
        abort(404)
    
    with open(docs_path, 'r', encoding='utf-8') as f:
        conteudo_md = f.read()
    
    # Converter markdown para HTML com extensões
    html_content = markdown.markdown(
        conteudo_md,
        extensions=[
            'fenced_code',
            'codehilite',
            'tables',
            'toc',
            'nl2br',
            'sane_lists'
        ]
    )
    
    return render_template('admin/api_keys/docs_viewer.html',
                         titulo=doc_info['titulo'],
                         descricao=doc_info['descricao'],
                         conteudo=Markup(html_content),
                         doc_name=doc_name,
                         docs=docs_disponiveis,
                         now=datetime.now())


@api_keys_bp.route('/<int:cliente_id>/create', methods=['GET', 'POST'])
@login_required
def create_api_key(cliente_id):
    """Cria uma nova API Key"""
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    if cliente_id not in accessible_client_ids:
        flash('Acesso negado para este cliente.', 'error')
        return redirect(url_for('home.home'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        rate_limit = request.form.get('rate_limit', 1000, type=int)
        expira_em_dias = request.form.get('expira_em_dias', type=int)
        ip_whitelist = request.form.get('ip_whitelist', '').strip()
        permissoes_lista = request.form.getlist('permissoes')
        
        if not nome:
            flash('Nome da chave é obrigatório.', 'error')
            return redirect(url_for('api_keys.create_api_key', cliente_id=cliente_id))
        
        # Gerar a chave
        key_string, key_hash, key_prefix = generate_api_key(cliente_id, nome)
        
        # Calcular expiração
        expira_em = None
        if expira_em_dias and expira_em_dias > 0:
            expira_em = datetime.now() + timedelta(days=expira_em_dias)
        
        # Processar IP whitelist
        ip_whitelist_json = None
        if ip_whitelist:
            ips = [ip.strip() for ip in ip_whitelist.split(',') if ip.strip()]
            if ips:
                ip_whitelist_json = json.dumps(ips)
        
        # Processar permissões
        permissoes_json = None
        if permissoes_lista:
            permissoes_json = json.dumps({'allowed': permissoes_lista})
        
        # Criar no banco
        api_key = ApiKey(
            cliente_id=cliente_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            nome=nome,
            rate_limit=rate_limit,
            expira_em=expira_em,
            ip_whitelist=ip_whitelist_json,
            permissoes=permissoes_json
        )
        
        db.add(api_key)
        db.commit()
        
        # Mostrar a chave uma única vez
        flash(f'API Key criada com sucesso! ATENÇÃO: Copie agora, não será mostrada novamente: {key_string}', 'success')
        return redirect(url_for('api_keys.list_api_keys', cliente_id=cliente_id))
    
    from database.models import Cliente
    cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
    
    return render_template('admin/api_keys/create.html',
                         cliente=cliente,
                         cliente_id=cliente_id)


@api_keys_bp.route('/<int:api_key_id>/toggle', methods=['POST'])
@login_required
def toggle_api_key(api_key_id):
    """Ativa/desativa uma API Key"""
    db = next(get_db())
    api_key = db.query(ApiKey).filter_by(api_key_id=api_key_id).first()
    
    if not api_key:
        flash('API Key não encontrada.', 'error')
        return redirect(url_for('home.home'))
    
    accessible_client_ids = get_accessible_client_ids(db)
    if api_key.cliente_id not in accessible_client_ids:
        flash('Acesso negado.', 'error')
        return redirect(url_for('home.home'))
    
    api_key.ativa = not api_key.ativa
    db.commit()
    
    status = 'ativada' if api_key.ativa else 'desativada'
    flash(f'API Key {status} com sucesso.', 'success')
    return redirect(url_for('api_keys.list_api_keys', cliente_id=api_key.cliente_id))


@api_keys_bp.route('/<int:api_key_id>/delete', methods=['POST'])
@login_required
def delete_api_key(api_key_id):
    """Exclui uma API Key"""
    db = next(get_db())
    api_key = db.query(ApiKey).filter_by(api_key_id=api_key_id).first()
    
    if not api_key:
        flash('API Key não encontrada.', 'error')
        return redirect(url_for('home.home'))
    
    accessible_client_ids = get_accessible_client_ids(db)
    if api_key.cliente_id not in accessible_client_ids:
        flash('Acesso negado.', 'error')
        return redirect(url_for('home.home'))
    
    cliente_id = api_key.cliente_id
    db.delete(api_key)
    db.commit()
    
    flash('API Key excluída com sucesso.', 'success')
    return redirect(url_for('api_keys.list_api_keys', cliente_id=cliente_id))


@api_keys_bp.route('/<int:api_key_id>/stats', methods=['GET'])
@login_required
def api_key_stats(api_key_id):
    """Estatísticas de uso de uma API Key"""
    db = next(get_db())
    api_key = db.query(ApiKey).filter_by(api_key_id=api_key_id).first()
    
    if not api_key:
        flash('API Key não encontrada.', 'error')
        return redirect(url_for('home.home'))
    
    accessible_client_ids = get_accessible_client_ids(db)
    if api_key.cliente_id not in accessible_client_ids:
        flash('Acesso negado.', 'error')
        return redirect(url_for('home.home'))
    
    # Estatísticas dos últimos 7 dias
    sete_dias_atras = datetime.now() - timedelta(days=7)
    
    logs = db.query(ApiUsageLog).filter(
        ApiUsageLog.api_key_id == api_key_id,
        ApiUsageLog.request_time >= sete_dias_atras
    ).order_by(ApiUsageLog.request_time.desc()).limit(100).all()
    
    # Resumo
    total_requests = db.query(ApiUsageLog).filter(
        ApiUsageLog.api_key_id == api_key_id
    ).count()
    
    total_7_days = len(logs)
    
    total_errors = db.query(ApiUsageLog).filter(
        ApiUsageLog.api_key_id == api_key_id,
        ApiUsageLog.status_code >= 400
    ).count()
    
    return render_template('admin/api_keys/stats.html',
                         api_key=api_key,
                         logs=logs,
                         total_requests=total_requests,
                         total_7_days=total_7_days,
                         total_errors=total_errors,
                         cliente_id=api_key.cliente_id)


# ==================== API ENDPOINTS (Gerenciamento via API) ====================

@api_keys_bp.route('/api/v2/keys', methods=['GET'])
@require_api_key(permissions=['admin'])
def api_list_keys():
    """Lista API Keys do cliente (via API)"""
    from flask import g
    db = next(get_db())
    
    api_keys = db.query(ApiKey).filter_by(cliente_id=g.cliente_id).all()
    
    return jsonify({
        'success': True,
        'keys': [k.to_dict() for k in api_keys]
    }), 200


@api_keys_bp.route('/api/v2/keys/stats', methods=['GET'])
@require_api_key(permissions=['admin'])
def api_key_usage_stats():
    """Estatísticas de uso via API"""
    from flask import g
    db = next(get_db())
    
    # Últimos 30 dias
    trinta_dias_atras = datetime.now() - timedelta(days=30)
    
    logs = db.query(ApiUsageLog).filter(
        ApiUsageLog.cliente_id == g.cliente_id,
        ApiUsageLog.request_time >= trinta_dias_atras
    ).all()
    
    # Agrupar por endpoint
    from collections import Counter
    endpoints = Counter([log.endpoint for log in logs])
    status_codes = Counter([log.status_code for log in logs])
    
    return jsonify({
        'success': True,
        'period': '30 days',
        'total_requests': len(logs),
        'endpoints': dict(endpoints.most_common(10)),
        'status_codes': dict(status_codes),
        'average_response_time_ms': sum([log.response_time_ms or 0 for log in logs]) / len(logs) if logs else 0
    }), 200

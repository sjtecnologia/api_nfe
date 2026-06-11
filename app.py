import os
import uuid
from flask import Flask, render_template, jsonify, redirect, url_for, request, g
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from datetime import datetime
from config.settings import SECRET_KEY, DEBUG, HOST, PORT
from config.logging_config import configure_logging
from database.connection import get_db
from auth.login_manager import init_login_manager
from auth.permissions import has_permission
from flask_login import current_user, login_required
from models.user import User
from werkzeug.exceptions import HTTPException

configure_logging()

# Configurar encoding UTF-8 no stdout para Windows
import sys
import io
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # Se falhar, continua com encoding padrão

# Importar blueprints
from routes.auth_routes import auth_bp
from routes.api_routes import api_bp
from routes.nfe_routes import nfe_bp
from routes.nfce_routes import nfce_bp
from routes.admin_routes import admin_bp
from routes.home_routes import home_bp
from routes.cliente_routes import cliente_bp
from routes.llm_api_routes import llm_api_bp
from routes.planos_routes import planos_bp
from routes.a3_routes import a3_bp
from routes.api_keys_routes import api_keys_bp
from routes.api_v2_routes import api_v2_bp
from routes.webhooks_routes import webhooks_bp
from routes.nfse_routes import nfse_bp
from routes.regras_servicos_routes import regras_servicos_bp
from routes.classificacao_ibs_cbs_routes import classificacao_ibs_cbs_bp
from routes.nfse_api_routes import nfse_api_bp
from routes.admin_api_routes import admin_api_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

os.makedirs(app.instance_path, exist_ok=True)

default_upload_dir = os.getenv('UPLOAD_FOLDER', os.path.join(app.instance_path, 'uploads'))
private_upload_dir = os.getenv('PRIVATE_UPLOAD_FOLDER', os.path.join(app.instance_path, 'private_uploads'))
os.makedirs(default_upload_dir, exist_ok=True)
os.makedirs(private_upload_dir, exist_ok=True)

app.config['UPLOAD_FOLDER'] = default_upload_dir
app.config['PRIVATE_UPLOAD_FOLDER'] = private_upload_dir

# Werkzeug 3.x define max_form_memory_size=500KB e max_form_parts=1000 como atributos de classe.
# Flask 2.3.x não repassa app.config para esses atributos — é preciso fazer monkey-patch direto.
# NFes com muitos itens excedem esses limites e geram erro 413.
from werkzeug.wrappers import Request as WerkzeugRequest
WerkzeugRequest.max_form_memory_size = 50 * 1024 * 1024  # 50MB (padrão: 500KB)
WerkzeugRequest.max_form_parts = 10000                    # 10.000 campos (padrão: 1000)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024       # 50MB

# Configurações de sessão para compatibilidade com iOS/Safari
_is_production = os.getenv('FLASK_ENV', 'production') == 'production'
app.config['SESSION_COOKIE_SECURE'] = _is_production   # HTTPS apenas em produção
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Proteção contra XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Compatível com iOS
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

# Configurações do Flask-Login "Remember Me"
from datetime import timedelta
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # 30 dias
app.config['REMEMBER_COOKIE_SECURE'] = _is_production         # HTTPS apenas em produção
app.config['REMEMBER_COOKIE_HTTPONLY'] = True  # Proteção contra XSS
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'  # Compatível com iOS

# CSRF — protege todos os formulários HTML (exceto APIs autenticadas via API Key)
csrf = CSRFProtect(app)
# Isentar blueprints de API pura (autenticados via API Key no header)
csrf.exempt(api_v2_bp)
csrf.exempt(api_bp)
csrf.exempt(llm_api_bp)
csrf.exempt(nfse_api_bp)

# CORS — origens explícitas via variável de ambiente
_raw_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5000')
_allowed_origins = [o.strip() for o in _raw_origins.split(',') if o.strip()]
CORS(
    app,
    resources={r"/api/*": {"origins": _allowed_origins}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-API-Key"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    expose_headers=["Content-Type", "X-Total-Count", "X-Request-ID"],
)

# Rate Limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],  # sem limite global; aplicar por rota
    storage_uri=os.getenv('RATELIMIT_STORAGE_URI', 'memory://'),
)

# Cache
cache = Cache(app, config={
    'CACHE_TYPE': os.getenv('CACHE_TYPE', 'SimpleCache'),
    'CACHE_DEFAULT_TIMEOUT': 3600,
})

# Expor cache e limiter para uso nos blueprints
app.extensions['cache'] = cache
app.extensions['limiter'] = limiter

# Inicializar Flask-Login
login_manager = init_login_manager(app)

# Registrar blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(api_v2_bp)  # API v2 com autenticação por API Key
app.register_blueprint(nfe_bp, url_prefix='/admin/nfe')
app.register_blueprint(nfce_bp)  # NFC-e já tem url_prefix='/admin/nfce' no blueprint
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(cliente_bp, url_prefix='/cliente')
app.register_blueprint(planos_bp, url_prefix='/admin/planos')
app.register_blueprint(a3_bp)  # Certificados A3
app.register_blueprint(api_keys_bp)  # Gerenciamento de API Keys
app.register_blueprint(webhooks_bp)  # Gerenciamento de Webhooks
app.register_blueprint(home_bp)
app.register_blueprint(llm_api_bp)  # API específica para LLM
app.register_blueprint(nfse_bp)  # NFS-e Nacional
app.register_blueprint(regras_servicos_bp)  # Regras Tributárias de Serviços
app.register_blueprint(classificacao_ibs_cbs_bp)  # Classificações IBS/CBS - Reforma Tributária
app.register_blueprint(nfse_api_bp)  # API NFS-e - Busca NBS e Validações NT007
app.register_blueprint(admin_api_bp, url_prefix='/admin')  # Rotas API JSON do admin

import re
from markupsafe import Markup, escape

def highlight(text, query):
    if not query or not text:
        return escape(text)
    # Escape para HTML
    text_escaped = escape(text)
    query_escaped = escape(query)
    # Regex para case-insensitive e todas ocorrências
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return Markup(pattern.sub(lambda m: f'<mark>{m.group(0)}</mark>', text_escaped))

app.jinja_env.filters['highlight'] = highlight

# Registrar filtros Jinja2 customizados (badges, datas, moeda, etc.)
from utils.template_filters import register_filters
register_filters(app)


@app.context_processor
def inject_permissions():
    """Injeta funções de permissão e verificação de admin nos templates"""
    def has_permission(permission_name):
        from flask_login import current_user
        if not current_user.is_authenticated:
            return False
        return current_user.has_permission(permission_name)
    
    def is_super_admin():
        from flask_login import current_user
        if not current_user.is_authenticated:
            return False
        return current_user.is_super_admin()
    
    def can_edit():
        """Verifica se o usuário pode editar (não é Viewer)"""
        from flask_login import current_user
        if not current_user.is_authenticated:
            return False
        if is_super_admin():
            return True
        # Verifica se tem alguma permissão de edição (edit, create, delete)
        return (has_permission('nfes.create') or 
                has_permission('produtos.create') or 
                has_permission('destinatarios_nfe.create') or
                has_permission('clientes.edit'))
    
    def can_create():
        """Verifica se o usuário pode criar registros (não é Viewer)"""
        return can_edit()
    
    def is_viewer_only():
        """Verifica se o usuário tem apenas permissão de visualização"""
        from flask_login import current_user
        if not current_user.is_authenticated:
            return True
        if is_super_admin():
            return False
        # Se não tem nenhuma permissão de edição, é viewer only
        return not can_edit()
    
    # Importar função de encode_id para templates
    from utils.id_encoder import encode_id
    
    return dict(
        csrf_token=generate_csrf,
        has_permission=has_permission, 
        is_super_admin=is_super_admin,
        can_edit=can_edit,
        can_create=can_create,
        is_viewer_only=is_viewer_only,
        encode_id=encode_id
    )

@app.before_request
def inject_request_id():
    """Gera um ID único por requisição para rastreabilidade nos logs."""
    g.request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    if current_user.is_authenticated:
        g.user_id = current_user.id


@app.after_request
def add_security_headers(response):
    """Adiciona headers de segurança HTTP em todas as respostas."""
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'self';"
    )
    # Propaga request_id na resposta
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
    return response


@app.route('/')
def home():
    """Rota inicial"""
    return render_template('home.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar a saúde da API"""
    return jsonify({"status": "UP", "timestamp": datetime.now().isoformat()}), 200

@app.route('/diagnostico', methods=['GET'])
def diagnostico():
    """Página de diagnóstico para verificar conectividade"""
    return render_template('diagnostico.html')

@app.route('/favicon.ico')
def favicon():
    """Rota para favicon - retorna o arquivo ou 204 se não existir"""
    from flask import send_from_directory
    import os
    favicon_path = os.path.join(app.root_path, 'static', 'img', 'Logonew.ico')
    if os.path.exists(favicon_path):
        return send_from_directory(os.path.join(app.root_path, 'static', 'img'), 'Logonew.ico', mimetype='image/vnd.microsoft.icon')
    return '', 204

import logging

from utils.rastro import capture_exception

logger = logging.getLogger(__name__)


def _is_api_request():
    """Retorna True se a requisição espera JSON (API/fetch) em vez de HTML."""
    return (
        request.path.startswith('/api/')
        or request.path.startswith('/admin/api/')
        or request.path.startswith('/admin/nfe/api/')
        or request.path.startswith('/admin/nfse/api/')
        or request.headers.get('Accept', '').startswith('application/json')
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.content_type == 'application/json'
    )


@app.errorhandler(400)
def bad_request(error):
    """400 Bad Request"""
    if _is_api_request():
        return jsonify({'success': False, 'error': 'Requisição inválida', 'message': str(error)}), 400
    return render_template('errors/400.html', error=error), 400


@app.errorhandler(403)
def forbidden(error):
    """403 Forbidden"""
    if _is_api_request():
        return jsonify({'success': False, 'error': 'Acesso negado', 'message': str(error)}), 403
    return render_template('errors/403.html', error=error), 403


@app.errorhandler(404)
def not_found(error):
    """404 Not Found"""
    if _is_api_request():
        return jsonify({'success': False, 'error': 'Recurso não encontrado', 'message': str(error)}), 404
    return render_template('errors/404.html', error=error), 404


@app.errorhandler(500)
def internal_error(error):
    """Handler para erro 500 — loga detalhes completos"""
    import traceback
    import sys

    exc_type, exc_value, exc_tb = sys.exc_info()

    logger.error(
        "ERRO 500 — %s: %s",
        exc_type.__name__ if exc_type else 'Unknown',
        str(exc_value or error),
        exc_info=True,
    )

    # Envia ao Rastro de forma assíncrona (fire-and-forget)
    _exc = exc_value if exc_value else (error if isinstance(error, BaseException) else None)
    if _exc:
        _rid = getattr(g, 'request_id', None)
        capture_exception(_exc, level='error', trace_id=_rid)

    if _is_api_request():
        return jsonify({'success': False, 'error': 'Erro interno do servidor', 'message': 'Tente novamente mais tarde.'}), 500

    return render_template('errors/500.html', error=error), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handler para TODAS as exceções não tratadas"""
    if isinstance(e, HTTPException):
        return e
    logger.error("Exceção não tratada — %s: %s", type(e).__name__, str(e), exc_info=True)
    _rid = getattr(g, 'request_id', None)
    capture_exception(e, level='error', trace_id=_rid)
    return internal_error(e)


@app.route('/docs/<path:filename>')
@login_required
def serve_docs(filename):
    """
    Rota legada - Redireciona para documentação protegida
    Mantida para compatibilidade com links antigos
    """
    # Redirecionar para o novo sistema de documentação
    # Remove extensão .md se houver
    doc_name = filename.replace('.md', '').replace('API_', '').replace('_MANUAL', '').lower()
    
    # Mapear nomes antigos para novos
    doc_mapping = {
        'integracao': 'integracao',
        'tributacao_automatica': 'tributacao-automatica',
        'tributacao_automatica_completo': 'tributacao-completo'
    }
    
    mapped_name = doc_mapping.get(doc_name, None)
    
    if mapped_name:
        return redirect(url_for('api_keys.api_documentation', doc_name=mapped_name))
    else:
        # Se não encontrar mapeamento, vai para o índice
        return redirect(url_for('api_keys.api_documentation'))

def list_routes():
    """Lista todas as rotas registradas na aplicação"""
    print("\n=== ROTAS REGISTRADAS ===")
    for rule in app.url_map.iter_rules():
        methods = ', '.join(sorted(rule.methods or []))
        print(f"{methods:<20} {rule.rule:<50} -> {rule.endpoint}")
    print("=== FIM DAS ROTAS ===\n")

if __name__ == '__main__':
    if DEBUG:
        list_routes()
    app.run(debug=DEBUG, host=HOST, port=PORT)
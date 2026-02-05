from flask import Flask, render_template, jsonify
from flask_cors import CORS
from datetime import datetime
from config.settings import SECRET_KEY, DEBUG, HOST, PORT
from database.connection import get_db
from auth.login_manager import init_login_manager
from auth.permissions import has_permission
from flask_login import current_user
from models.user import User

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

# Configurar Flask-Login
from auth.login_manager import init_login_manager




app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configurações de sessão para compatibilidade com iOS/Safari
app.config['SESSION_COOKIE_SECURE'] = True  # Apenas HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Proteção contra XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Compatível com iOS
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

# Configurações do Flask-Login "Remember Me"
from datetime import timedelta
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # 30 dias
app.config['REMEMBER_COOKIE_SECURE'] = True  # Apenas HTTPS
app.config['REMEMBER_COOKIE_HTTPONLY'] = True  # Proteção contra XSS
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'  # Compatível com iOS

# Configurar CORS - Permitir acesso de qualquer origem
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-API-Key"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
     expose_headers=["Content-Type", "X-Total-Count"])

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
        has_permission=has_permission, 
        is_super_admin=is_super_admin,
        can_edit=can_edit,
        can_create=can_create,
        is_viewer_only=is_viewer_only,
        encode_id=encode_id
    )

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

@app.errorhandler(500)
def internal_error(error):
    """Handler para erro 500 - loga detalhes completos"""
    import traceback
    import sys
    
    # Obter informações do erro
    exc_type, exc_value, exc_tb = sys.exc_info()
    
    # Logar erro completo no console
    print("\n" + "="*80, flush=True)
    print("[X] ERRO 500 - INTERNAL SERVER ERROR", flush=True)
    print("="*80, flush=True)
    print(f"[RED] Tipo do erro: {exc_type.__name__ if exc_type else 'Unknown'}", flush=True)
    print(f"[LOG] Mensagem: {str(error)}", flush=True)
    print(f"[ERROR] Exceção: {str(exc_value)}", flush=True)
    
    if exc_tb:
        print("\n[TRACE] Traceback completo:", flush=True)
        traceback.print_tb(exc_tb, file=sys.stdout)
        print("\n[LIST] Traceback formatado:", flush=True)
        for line in traceback.format_tb(exc_tb):
            print(line, flush=True)
    else:
        print("[!] Nenhum traceback disponível", flush=True)
    
    print("\n[SEARCH] Exception completa:", flush=True)
    traceback.print_exc(file=sys.stdout)
    print("="*80 + "\n", flush=True)
    
    # Se DEBUG está ativo, mostrar erro na página
    if DEBUG:
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb) if exc_tb else []
        return f"""
        <h1>Internal Server Error</h1>
        <h2>Tipo: {exc_type.__name__ if exc_type else 'Unknown'}</h2>
        <pre>{str(error)}</pre>
        <h2>Exceção:</h2>
        <pre>{str(exc_value)}</pre>
        <h2>Traceback:</h2>
        <pre>{''.join(tb_lines)}</pre>
        """, 500
    
    # Em produção, página genérica
    return render_template('error.html', error=error), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handler para TODAS as exceções não tratadas"""
    import traceback
    import sys
    
    print("\n" + "="*80, flush=True)
    print("[ERROR] EXCEÇÃO NÃO TRATADA", flush=True)
    print("="*80, flush=True)
    print(f"[RED] Tipo: {type(e).__name__}", flush=True)
    print(f"[LOG] Mensagem: {str(e)}", flush=True)
    print("\n[TRACE] Traceback completo:", flush=True)
    traceback.print_exc(file=sys.stdout)
    print("="*80 + "\n", flush=True)
    
    # Passar para o handler 500
    return internal_error(e)

@app.route('/docs/<path:filename>')
def serve_docs(filename):
    """Serve arquivos de documentação"""
    from flask import send_from_directory
    import os
    docs_dir = os.path.join(app.root_path, 'docs')
    return send_from_directory(docs_dir, filename)

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
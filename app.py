from flask import Flask, render_template, jsonify
from datetime import datetime
from config.settings import SECRET_KEY, DEBUG, HOST, PORT
from database.connection import get_db
from auth.login_manager import init_login_manager
from auth.permissions import has_permission
from flask_login import current_user
from models.user import User

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

# Configurar Flask-Login
from auth.login_manager import init_login_manager




app = Flask(__name__)
app.secret_key = SECRET_KEY

# Inicializar Flask-Login
login_manager = init_login_manager(app)

# Registrar blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(nfe_bp, url_prefix='/admin/nfe')
app.register_blueprint(nfce_bp)  # NFC-e já tem url_prefix='/admin/nfce' no blueprint
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(cliente_bp, url_prefix='/cliente')
app.register_blueprint(planos_bp, url_prefix='/admin/planos')
app.register_blueprint(home_bp)
app.register_blueprint(llm_api_bp)  # API específica para LLM

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
    
    return dict(has_permission=has_permission, is_super_admin=is_super_admin)

@app.route('/')
def home():
    """Rota inicial"""
    return render_template('home.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar a saúde da API"""
    return jsonify({"status": "UP", "timestamp": datetime.now().isoformat()}), 200

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
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
from flask_login import LoginManager
from models.user import User

def init_login_manager(app):
    """Inicializa o Flask-Login"""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Você precisa fazer login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Carrega o usuário pelo ID para o Flask-Login"""
        try:
            # Usar nosso método personalizado User.get() em vez do SQLAlchemy
            return User.get(int(user_id))
        except (ValueError, TypeError):
            return None
    
    return login_manager
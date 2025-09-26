from functools import wraps
from flask import request, redirect, url_for, flash, g, session
from flask_login import current_user

def permission_required(permission_name):
    """Decorador que verifica se o usuário tem a permissão necessária"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.has_permission(permission_name):
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def client_access_required():
    """Decorador que verifica se o usuário pode acessar o cliente especificado"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Pegar cliente_id da URL, session ou parâmetros
            cliente_id = kwargs.get('cliente_id') or request.args.get('cliente_id') or session.get('current_client_id')
            
            if cliente_id and not current_user.can_access_client(int(cliente_id)):
                flash('Você não tem acesso a este cliente.', 'danger')
                return redirect(url_for('home'))
            
            # Definir cliente atual no contexto
            if cliente_id:
                g.current_client_id = int(cliente_id)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required():
    """Decorador que permite acesso apenas para administradores"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.is_admin():
                flash('Acesso restrito a administradores.', 'danger')
                return redirect(url_for('home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
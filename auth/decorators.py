from functools import wraps
from flask import redirect, url_for, flash, session
from flask_login import current_user
from database.connection import get_db
from sqlalchemy import text

def permission_required(permission):
    """Decorator para verificar se o usuário tem uma permissão específica"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Implementar verificação de permissão
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required():
    """Decorator para verificar se o usuário é admin ou super_admin - USER.ID CORRIGIDO"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))
            
            try:
                db = next(get_db())
                
                # ✅ CORRIGIDO: current_user.id (não user_id)
                user_roles = db.execute(text("""
                    SELECT r.name
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id
                    AND r.name IN ('Admin', 'Super_Admin')
                """), {"user_id": current_user.id}).fetchall()
                
                if not user_roles:
                    print(f"❌ Usuário {current_user.username} (ID:{current_user.id}) sem role admin/super_admin")
                    flash('Acesso negado. Você não tem permissão de administrador.', 'danger')
                    return redirect(url_for('auth.login'))
                
                role_names = [role.name for role in user_roles]
                print(f"✅ Acesso admin autorizado para {current_user.username} com roles: {role_names}")
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"❌ Erro na verificação admin: {e}")
                import traceback
                traceback.print_exc()
                flash('Erro na verificação de permissões.', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if 'db' in locals():
                    db.close()
                    
        return decorated_function
    return decorator

def editor_or_admin_required():
    """Decorator que permite acesso a editores e admins (bloqueia apenas viewers)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def viewer_or_higher_required():
    """Decorator que permite acesso a viewers, editores e admins"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def block_viewer_access(f):
    """Decorator que bloqueia acesso de viewers (apenas leitura)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Acesso não autorizado. Faça login.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def client_access_required():
    """Decorator para verificar se o usuário tem acesso ao cliente - USER.ID CORRIGIDO"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Extrair cliente_id dos argumentos da URL
            cliente_id = kwargs.get('cliente_id')
            
            if not cliente_id:
                flash('Cliente não especificado.', 'danger')
                return redirect(url_for('auth.login'))
            
            try:
                db = next(get_db())
                
                # ✅ CORRIGIDO: current_user.id (não user_id)
                super_admin_check = db.execute(text("""
                    SELECT 1 FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id AND r.name = 'Super_Admin'
                """), {"user_id": current_user.id}).first()
                
                if super_admin_check:
                    print(f"✅ Acesso SUPER_ADMIN autorizado para cliente {cliente_id}")
                    return f(*args, **kwargs)
                
                # ✅ CORRIGIDO: usar client_id e current_user.id
                client_access = db.execute(text("""
                    SELECT 1 FROM user_clients 
                    WHERE user_id = :user_id AND client_id = :cliente_id
                """), {"user_id": current_user.id, "cliente_id": cliente_id}).first()
                
                if not client_access:
                    print(f"❌ Usuário {current_user.username} (ID:{current_user.id}) sem acesso ao cliente {cliente_id}")
                    flash('Acesso negado. Você não tem permissão para este cliente.', 'danger')
                    return redirect(url_for('auth.login'))
                
                print(f"✅ Acesso permitido ao cliente {cliente_id} para usuário {current_user.username}")
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"❌ Erro na verificação de acesso: {e}")
                import traceback
                traceback.print_exc()
                flash('Erro na verificação de permissões.', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if 'db' in locals():
                    db.close()
                    
        return decorated_function
    return decorator
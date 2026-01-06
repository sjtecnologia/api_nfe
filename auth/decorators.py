from functools import wraps
from flask import redirect, url_for, flash, session
from flask_login import current_user
from database.connection import get_db
from sqlalchemy import text
from utils.id_encoder import decode_id

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
            
            db = None
            try:
                db = next(get_db())
                
                # [OK] CORRIGIDO: current_user.id (não user_id)
                user_roles = db.execute(text("""
                    SELECT r.name
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id
                    AND r.name IN ('Admin', 'Super_Admin')
                """), {"user_id": current_user.id}).fetchall()
                
                if not user_roles:
                    print(f"[X] Usuário {current_user.username} (ID:{current_user.id}) sem role admin/super_admin")
                    flash('Acesso negado. Você não tem permissão de administrador.', 'danger')
                    return redirect(url_for('auth.login'))
                
                role_names = [role.name for role in user_roles]
                print(f"[OK] Acesso admin autorizado para {current_user.username} com roles: {role_names}")
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"[X] Erro na verificação admin: {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erro na verificação de permissões: {str(e)}', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if db is not None:
                    db.close()
                    
        return decorated_function
    return decorator

def super_admin_required():
    """Decorator para verificar se o usuário é SUPER ADMIN (apenas)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))
            
            db = None
            try:
                db = next(get_db())
                
                # Verificar se tem role Super_Admin
                user_roles = db.execute(text("""
                    SELECT r.name
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id
                    AND r.name = 'Super_Admin'
                """), {"user_id": current_user.id}).fetchall()
                
                if not user_roles:
                    print(f"[X] Acesso negado: Usuário {current_user.username} (ID:{current_user.id}) não é Super Admin")
                    flash('Acesso negado. Esta funcionalidade é exclusiva para Super Administradores.', 'danger')
                    # Redirecionar para home ao invés de dashboard (que agora é protegido)
                    return redirect(url_for('home.home'))
                
                print(f"[OK] Acesso Super Admin autorizado para {current_user.username}")
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"[X] Erro na verificação super admin: {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erro na verificação de permissões: {str(e)}', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if db is not None:
                    db.close()
                    
        return decorated_function
    return decorator

def client_access_required():
    """Decorator para verificar se o usuário tem acesso ao cliente - USER.ID CORRIGIDO"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Extrair cliente_id dos argumentos da URL (suporta cliente_id e cliente_hash)
            cliente_id = kwargs.get('cliente_id')
            cliente_hash = kwargs.get('cliente_hash')
            
            # Se recebeu hash, decodifica para obter o ID
            if cliente_hash and not cliente_id:
                cliente_id = decode_id(cliente_hash)
                if cliente_id is None:
                    flash('Link inválido ou expirado.', 'danger')
                    return redirect(url_for('auth.login'))
            
            if not cliente_id:
                flash('Cliente não especificado.', 'danger')
                return redirect(url_for('auth.login'))
            db = None
            try:
                db = next(get_db())
                
                # [OK] CORRIGIDO: current_user.id (não user_id)
                super_admin_check = db.execute(text("""
                    SELECT 1 FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id AND r.name = 'Super_Admin'
                """), {"user_id": current_user.id}).first()
                
                if super_admin_check:
                    print(f"[OK] Acesso SUPER_ADMIN autorizado para cliente {cliente_id}")
                    return f(*args, **kwargs)
                
                # [OK] CORRIGIDO: usar client_id e current_user.id
                client_access = db.execute(text("""
                    SELECT 1 FROM user_clients 
                    WHERE user_id = :user_id AND client_id = :cliente_id
                """), {"user_id": current_user.id, "cliente_id": cliente_id}).first()
                
                if not client_access:
                    print(f"[X] Usuário {current_user.username} (ID:{current_user.id}) sem acesso ao cliente {cliente_id}")
                    flash('Acesso negado. Você não tem permissão para este cliente.', 'danger')
                    return redirect(url_for('auth.login'))
                
                print(f"[OK] Acesso permitido ao cliente {cliente_id} para usuário {current_user.username}")
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"[X] Erro na verificação de acesso: {e}")
                import traceback
                traceback.print_exc()
                flash('Erro na verificação de permissões.', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if db is not None:
                    db.close()
                    db.close()
                    
        return decorated_function
    return decorator

def role_required(allowed_roles):
    """
    Decorator para verificar se o usuário tem uma das roles especificadas
    
    Args:
        allowed_roles: Lista de roles permitidas (ex: ['Super_Admin', 'Admin', 'Editor'])
        
    Usage:
        @role_required(['Super_Admin', 'Admin'])
        def minha_funcao():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))
            
            db = None
            try:
                db = next(get_db())
                
                # Verificar se o usuário tem uma das roles permitidas
                user_roles = db.execute(text("""
                    SELECT r.name
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id
                """), {"user_id": current_user.id}).fetchall()
                
                user_role_names = [role.name for role in user_roles]
                
                # Verificar se tem alguma das roles permitidas
                has_access = any(role in allowed_roles for role in user_role_names)
                
                if not has_access:
                    print(f"[X] Acesso negado: Usuário {current_user.username} com roles {user_role_names} tentou acessar função que requer {allowed_roles}")
                    flash(f'Acesso negado. Esta funcionalidade requer uma das seguintes permissões: {", ".join(allowed_roles)}.', 'danger')
                    return redirect(url_for('home.home'))
                
                print(f"[OK] Acesso autorizado para {current_user.username} com roles: {user_role_names}")
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"[X] Erro na verificação de roles: {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erro na verificação de permissões: {str(e)}', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if db is not None:
                    db.close()
                    
        return decorated_function
    return decorator

def editor_or_admin_required():
    """Decorator para verificar se o usuário é Editor, Admin ou Super_Admin"""
    return role_required(['Super_Admin', 'Admin', 'Editor'])

def viewer_or_higher_required():
    """Decorator para verificar se o usuário tem qualquer role (Viewer, Editor, Admin ou Super_Admin)"""
    return role_required(['Super_Admin', 'Admin', 'Editor', 'Viewer'])

def block_viewer_access():
    """
    Decorator para bloquear explicitamente acesso de Viewers (somente leitura)
    Permite apenas Editor, Admin e Super_Admin
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))
            
            db = None
            try:
                db = next(get_db())
                
                # Verificar se o usuário é Viewer
                is_viewer = db.execute(text("""
                    SELECT 1
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id AND r.name = 'Viewer'
                """), {"user_id": current_user.id}).first()
                
                if is_viewer:
                    # Verificar se tem outras roles além de Viewer
                    other_roles = db.execute(text("""
                        SELECT r.name
                        FROM user_roles ur
                        JOIN roles r ON ur.role_id = r.id
                        WHERE ur.user_id = :user_id AND r.name != 'Viewer'
                    """), {"user_id": current_user.id}).fetchall()
                    
                    if not other_roles:
                        print(f"[X] Acesso negado: Usuário {current_user.username} com role Viewer tentou realizar ação de escrita")
                        flash('Acesso negado. Usuários com perfil Viewer não podem realizar esta ação (somente leitura).', 'warning')
                        # Redirecionar para a página anterior ou home
                        return redirect(request.referrer or url_for('home.home'))
                
                print(f"[OK] Usuário {current_user.username} autorizado para ação de escrita")
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"[X] Erro na verificação de Viewer: {e}")
                import traceback
                traceback.print_exc()
                flash(f'Erro na verificação de permissões: {str(e)}', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if db is not None:
                    db.close()
                    
        return decorated_function
    return decorator

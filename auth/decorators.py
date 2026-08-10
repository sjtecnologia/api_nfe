from functools import wraps
from flask import redirect, url_for, flash, session, jsonify, request
from flask_login import current_user
from database.connection import get_db
from sqlalchemy import text
from utils.id_encoder import decode_id
import logging

logger = logging.getLogger(__name__)

def permission_required(permission):
    """Decorator para verificar se o usuário tem uma permissão específica."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Autenticação necessária'}), 401
                flash('Acesso não autorizado. Faça login.', 'danger')
                return redirect(url_for('auth.login'))

            db = None
            try:
                db = next(get_db())
                # Verifica permissão via tabela user_roles → role_permissions → permissions
                row = db.execute(text("""
                    SELECT 1
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    JOIN role_permissions rp ON rp.role_id = r.id
                    JOIN permissions p ON p.id = rp.permission_id
                    WHERE ur.user_id = :user_id
                      AND p.name = :permission
                    LIMIT 1
                """), {"user_id": current_user.id, "permission": permission}).first()

                # Super_Admin sempre tem acesso
                if not row:
                    super_row = db.execute(text("""
                        SELECT 1 FROM user_roles ur
                        JOIN roles r ON ur.role_id = r.id
                        WHERE ur.user_id = :user_id AND r.name = 'Super_Admin'
                        LIMIT 1
                    """), {"user_id": current_user.id}).first()
                    row = super_row

                if not row:
                    logger.warning(
                        "Acesso negado: user_id=%s tentou acessar permissão=%s em %s",
                        current_user.id, permission, request.path
                    )
                    if request.is_json or request.path.startswith('/api/'):
                        return jsonify({'error': f'Permissão {permission} necessária'}), 403
                    flash(f'Acesso negado. Permissão necessária: {permission}', 'danger')
                    return redirect(url_for('home.home'))

                return f(*args, **kwargs)

            except Exception as e:
                logger.error("Erro na verificação de permissão %s: %s", permission, e, exc_info=True)
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Erro interno na verificação de permissões'}), 500
                flash('Erro na verificação de permissões.', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if db is not None:
                    db.close()

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
                    logger.warning("admin_required: acesso negado user_id=%s roles insuficientes", current_user.id)
                    flash('Acesso negado. Você não tem permissão de administrador.', 'danger')
                    return redirect(url_for('auth.login'))
                
                role_names = [role.name for role in user_roles]
                logger.debug("admin_required: acesso concedido user_id=%s roles=%s", current_user.id, role_names)
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error("admin_required: erro verificação user_id=%s: %s", current_user.id, e, exc_info=True)
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
                    logger.warning("super_admin_required: acesso negado user_id=%s", current_user.id)
                    flash('Acesso negado. Esta funcionalidade é exclusiva para Super Administradores.', 'danger')
                    # Redirecionar para home ao invés de dashboard (que agora é protegido)
                    return redirect(url_for('home.home'))
                
                logger.debug("super_admin_required: acesso concedido user_id=%s", current_user.id)
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error("super_admin_required: erro verificação user_id=%s: %s", current_user.id, e, exc_info=True)
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
                    logger.debug("client_access: super_admin user_id=%s cliente_id=%s", current_user.id, cliente_id)
                    return f(*args, **kwargs)
                
                # [OK] CORRIGIDO: usar client_id e current_user.id
                client_access = db.execute(text("""
                    SELECT 1 FROM user_clients 
                    WHERE user_id = :user_id AND client_id = :cliente_id
                """), {"user_id": current_user.id, "cliente_id": cliente_id}).first()
                
                if not client_access:
                    logger.warning("client_access: acesso negado user_id=%s cliente_id=%s", current_user.id, cliente_id)
                    flash('Acesso negado. Você não tem permissão para este cliente.', 'danger')
                    return redirect(url_for('auth.login'))
                
                logger.debug("client_access: acesso concedido user_id=%s cliente_id=%s", current_user.id, cliente_id)
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error("client_access: erro verificação user_id=%s: %s", current_user.id, e, exc_info=True)
                flash('Erro na verificação de permissões.', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if db is not None:
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
                    logger.warning("role_required: acesso negado user_id=%s roles=%s required=%s", current_user.id, user_role_names, allowed_roles)
                    flash(f'Acesso negado. Esta funcionalidade requer uma das seguintes permissões: {", ".join(allowed_roles)}.', 'danger')
                    return redirect(url_for('home.home'))
                
                logger.debug("role_required: acesso concedido user_id=%s roles=%s", current_user.id, user_role_names)
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error("role_required: erro verificação user_id=%s: %s", current_user.id, e, exc_info=True)
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
                        logger.warning("block_viewer: ação de escrita bloqueada user_id=%s", current_user.id)
                        flash('Acesso negado. Usuários com perfil Viewer não podem realizar esta ação (somente leitura).', 'warning')
                        # Redirecionar para a página anterior ou home
                        return redirect(request.referrer or url_for('home.home'))
                
                logger.debug("block_viewer: ação permitida user_id=%s", current_user.id)
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error("block_viewer: erro verificação user_id=%s: %s", current_user.id, e, exc_info=True)
                flash(f'Erro na verificação de permissões: {str(e)}', 'error')
                return redirect(url_for('auth.login'))
            finally:
                if db is not None:
                    db.close()
                    
        return decorated_function
    return decorator

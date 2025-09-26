from flask_login import current_user
from database.connection import SessionLocal
from database.models import Permission, RolePermission, Role, UserRole, UserClient, Cliente

def get_accessible_client_ids(db_session):
    """Retorna os IDs dos clientes que o usuário logado tem acesso"""
    if not current_user.is_authenticated:
        return []
    
    if has_permission('admin.full_access'):
        return [c.cliente_id for c in db_session.query(Cliente.cliente_id).all()]
    
    accessible_client_ids = db_session.query(UserClient.client_id).filter_by(user_id=current_user.id).all()
    return [c[0] for c in accessible_client_ids]

def has_permission(permission_name):
    """Verifica se o usuário atual tem uma permissão específica"""
    if not current_user.is_authenticated:
        return False
    
    db = SessionLocal()
    try:
        user_permissions_query = db.query(Permission.name).join(RolePermission).join(Role).join(UserRole).filter(UserRole.user_id == current_user.id).distinct()
        user_permissions_names = [p[0] for p in user_permissions_query.all()]
        
        if 'admin.full_access' in user_permissions_names:
            return True
        
        return permission_name in user_permissions_names
    finally:
        db.close()
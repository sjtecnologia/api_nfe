from flask_login import UserMixin
from database.connection import get_db
from sqlalchemy import text

class User(UserMixin):
    def __init__(self, id, username, email, _is_active, roles=None, clients=None):
        self.id = id
        self.username = username
        self.email = email
        self._is_active = _is_active
        self.roles = roles or []
        self.clients = clients or []

    def is_active(self):
        return self._is_active

    def is_admin(self):
        """Verifica se o usuário é administrador da plataforma"""
        admin_roles = ['admin', 'super_admin', 'platform_admin']
        return any(role.name.lower() in admin_roles for role in self.roles)

    def get_accessible_clients(self):
        """Retorna lista de clientes que o usuário pode acessar"""
        if self.is_admin():
            # Admin pode acessar todos os clientes
            db = next(get_db())
            result = db.execute(text("""
                SELECT cliente_id, razao_social, nome_fantasia, cnpj
                FROM clientes
                WHERE ativo = true
                ORDER BY razao_social
            """))
            return [dict(row._mapping) for row in result]
        else:
            # Usuário comum só acessa clientes vinculados
            return self.clients

    def can_access_client(self, cliente_id):
        """Verifica se o usuário pode acessar um cliente específico"""
        if self.is_admin():
            return True
        
        return any(client['cliente_id'] == cliente_id for client in self.clients)

    def has_permission(self, permission_name):
        """Verifica se o usuário tem uma permissão específica"""
        if self.is_admin():
            return True
        
        for role in self.roles:
            if hasattr(role, 'permissions'):
                for perm in role.permissions:
                    if perm.name == permission_name:
                        return True
        return False

    @staticmethod
    def get(user_id):
        """Carrega usuário com roles e clientes"""
        try:
            db = next(get_db())
            
            # Buscar dados do usuário
            user_result = db.execute(text("""
                SELECT id, username, email, _is_active
                FROM users 
                WHERE id = :user_id AND _is_active = true
            """), {"user_id": user_id})
            
            user_data = user_result.first()
            if not user_data:
                return None

            # Buscar roles do usuário
            roles_result = db.execute(text("""
                SELECT r.id, r.name, r.description,
                       p.id as perm_id, p.name as perm_name, p.description as perm_desc
                FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                JOIN roles r ON ur.role_id = r.id
                LEFT JOIN role_permissions rp ON r.id = rp.role_id
                LEFT JOIN permissions p ON rp.permission_id = p.id
                WHERE u.id = :user_id
            """), {"user_id": user_id})

            # Organizar roles e permissões
            roles_dict = {}
            for row in roles_result:
                role_id = row.id
                if role_id not in roles_dict:
                    roles_dict[role_id] = {
                        'id': role_id,
                        'name': row.name,
                        'description': row.description,
                        'permissions': []
                    }
                
                if row.perm_id:
                    perm = {
                        'id': row.perm_id,
                        'name': row.perm_name,
                        'description': row.perm_desc
                    }
                    if perm not in roles_dict[role_id]['permissions']:
                        roles_dict[role_id]['permissions'].append(perm)

            # Buscar clientes do usuário
            clients_result = db.execute(text("""
                SELECT c.cliente_id, c.razao_social, c.nome_fantasia, c.cnpj
                FROM user_clients uc
                JOIN clientes c ON uc.client_id = c.cliente_id
                WHERE uc.user_id = :user_id AND c.ativo = true
                ORDER BY c.razao_social
            """), {"user_id": user_id})

            clients = [dict(row._mapping) for row in clients_result]

            # Criar objetos Role simples
            class SimpleRole:
                def __init__(self, **kwargs):
                    for key, value in kwargs.items():
                        setattr(self, key, value)

            # Criar objeto User
            user = User(
                id=user_data.id,
                username=user_data.username,
                email=user_data.email,
                _is_active=user_data._is_active,
                roles=[SimpleRole(**role) for role in roles_dict.values()],
                clients=clients
            )

            return user
            
        except Exception as e:
            print(f"Erro ao carregar usuário {user_id}: {e}")
            return None

    @staticmethod
    def authenticate(username, password):
        """Autentica usuário e retorna objeto User completo"""
        from werkzeug.security import check_password_hash
        
        try:
            db = next(get_db())
            result = db.execute(text("""
                SELECT id, username, password_hash, email, _is_active
                FROM users 
                WHERE username = :username AND _is_active = true
            """), {"username": username})
            
            user_data = result.first()
            if user_data and check_password_hash(user_data.password_hash, password):
                return User.get(user_data.id)
            
            return None
            
        except Exception as e:
            print(f"Erro na autenticação: {e}")
            return None
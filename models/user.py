import logging
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from database.connection import get_db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class User(UserMixin):
    def __init__(self, id, username, email, _is_active, roles=None, clients=None):
        self.id = id
        self.username = username
        self.email = email
        self._is_active = _is_active
        self.roles = roles or []
        self.clients = clients or []

    @property
    def is_active(self):
        return self._is_active

    def is_admin(self):
        """Verifica se o usuário é administrador da plataforma"""
        return any(role.get('name', '') in ['Admin', 'Super_Admin'] for role in self.roles)
    def is_super_admin(self):
        """Verifica se o usuário tem role Super_Admin"""
        return any(role.get('name', '') == 'Super_Admin' for role in self.roles)

    def get_accessible_clients(self):
        """Retorna lista de clientes que o usuário pode acessar"""
        if self.is_super_admin():
            # Admin pode acessar todos os clientes
            db = None
            try:
                db = next(get_db())
                result = db.execute(text("""
                    SELECT cliente_id, razao_social, nome_fantasia, cnpj
                    FROM clientes
                    WHERE ativo = true
                    ORDER BY razao_social
                """))
                return [dict(row._mapping) for row in result]
            except Exception as e:
                logger.warning("user.py: erro ao buscar clientes user_id=%s: %s", self.id, e)
                return []
            finally:
                if db is not None:
                    db.close()
        else:
            # Usuário comum só acessa clientes vinculados
            return self.clients

    def can_access_client(self, cliente_id):
        """Verifica se o usuário pode acessar um cliente específico"""
        if self.is_super_admin():
            return True
        
        return any(client.get('cliente_id') == cliente_id for client in self.clients)

    def has_permission(self, permission_name):
        """Verifica se o usuário tem uma permissão específica via roles."""
        if self.is_super_admin():
            return True
        from auth.permissions import has_permission as _check
        return _check(permission_name)

    @staticmethod
    def get(user_id):
        db = None
        try:
            db = next(get_db())
            user_data = db.execute(text("""
                SELECT u.id, u.username, u.email, u.is_active AS _is_active
                FROM users u
                WHERE u.id = :user_id AND u.is_active = true
            """), {"user_id": int(user_id)}).first()
            if not user_data:
                return None

            # Buscar roles do usuário
            roles_data = db.execute(text("""
                SELECT r.name
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id
            """), {"user_id": int(user_id)}).fetchall()
            roles = [{'name': row.name} for row in roles_data]

            # Buscar clientes do usuário
            clients_data = db.execute(text("""
                SELECT c.cliente_id, c.razao_social, c.nome_fantasia, c.cnpj
                FROM clientes c
                INNER JOIN user_clients uc ON c.cliente_id = uc.client_id
                WHERE uc.user_id = :user_id AND c.ativo = true
            """), {"user_id": int(user_id)}).fetchall()
            clients = [dict(row._mapping) for row in clients_data]

            return User(
                id=user_data.id,
                username=user_data.username,
                email=user_data.email,
                _is_active=user_data._is_active,
                roles=roles,
                clients=clients
            )
        except Exception as e:
            logger.error("user.py: erro ao carregar usuário user_id=%s: %s", user_id, e, exc_info=True)
            return None
        finally:
            if db is not None:
                db.close()

    @staticmethod
    def authenticate(username, password):
        # ...existing code...
        db = None
        try:
            db = next(get_db())
            user_data = db.execute(text("""
                SELECT u.id, u.username, u.password_hash, u.email, u.is_active AS _is_active
                FROM users u
                WHERE u.username = :username AND u.is_active = true
            """), {"username": username}).first()
            if user_data and check_password_hash(user_data.password_hash, password):
                logger.debug("user.py: autenticação OK username=%s", username)

                # Buscar roles do usuário
                roles_data = db.execute(text("""
                    SELECT r.name
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id
                """), {"user_id": user_data.id}).fetchall()
                roles = [{'name': row.name} for row in roles_data]

                # Buscar clientes do usuário
                clients_data = db.execute(text("""
                    SELECT c.cliente_id, c.razao_social, c.nome_fantasia, c.cnpj
                    FROM clientes c
                    INNER JOIN user_clients uc ON c.cliente_id = uc.client_id
                    WHERE uc.user_id = :user_id AND c.ativo = true
                """), {"user_id": user_data.id}).fetchall()
                clients = [dict(row._mapping) for row in clients_data]

                return User(
                    id=user_data.id,
                    username=user_data.username,
                    email=user_data.email,
                    _is_active=user_data._is_active,
                    roles=roles,
                    clients=clients
                )
            else:
                logger.warning("user.py: falha na autenticação username=%s", username)
                return None
        except Exception as e:
            logger.error("user.py: erro na autenticação username=%s: %s", username, e, exc_info=True)
            return None
        finally:
            if db is not None:
                db.close()

    def get_primary_client(self):
        """Retorna o cliente principal do usuário"""
        if self.clients:
            return self.clients[0]
        return None
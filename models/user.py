from flask_login import UserMixin
from werkzeug.security import check_password_hash
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
        # Por enquanto, user_id = 1 é admin
        return self.id == 1

    def get_accessible_clients(self):
        """Retorna lista de clientes que o usuário pode acessar"""
        if self.is_admin():
            # Admin pode acessar todos os clientes
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
                print(f"Erro ao buscar clientes: {e}")
                return []
            finally:
                db.close()
        else:
            # Usuário comum só acessa clientes vinculados
            return self.clients

    def can_access_client(self, cliente_id):
        """Verifica se o usuário pode acessar um cliente específico"""
        if self.is_admin():
            return True
        
        return any(client.get('cliente_id') == cliente_id for client in self.clients)

    def has_permission(self, permission_name):
        """Verifica se o usuário tem uma permissão específica"""
        # Por enquanto, todos têm todas as permissões
        return True

    @staticmethod
    def get(user_id):
        """Método para carregar usuário pelo ID (usado pelo login_manager)"""
        try:
            db = next(get_db())
            
            # Buscar usuário
            user_data = db.execute(text("""
                SELECT u.id, u.username, u.email, u._is_active
                FROM users u
                WHERE u.id = :user_id AND u._is_active = true
            """), {"user_id": int(user_id)}).first()
            
            if not user_data:
                return None
            
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
                roles=[],  # Simplificado por enquanto
                clients=clients
            )
            
        except Exception as e:
            print(f"❌ Erro ao carregar usuário {user_id}: {e}")
            return None
        finally:
            db.close()

    @staticmethod
    def authenticate(username, password):
        """Autenticar usuário"""
        if not username or not password:
            return None
            
        try:
            db = next(get_db())
            
            # Buscar usuário com dados do cliente
            user_data = db.execute(text("""
                SELECT u.id, u.username, u.password_hash, u.email, u._is_active
                FROM users u
                WHERE u.username = :username AND u._is_active = true
            """), {"username": username}).first()
            
            if user_data and check_password_hash(user_data.password_hash, password):
                print(f"✅ Usuário autenticado: {username}")
                
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
                    roles=[],  # Simplificado por enquanto
                    clients=clients
                )
            else:
                print(f"❌ Falha na autenticação: {username}")
                return None
            
        except Exception as e:
            print(f"❌ Erro na autenticação: {e}")
            return None
        finally:
            db.close()

    def get_primary_client(self):
        """Retorna o cliente principal do usuário"""
        if self.clients:
            return self.clients[0]
        return None
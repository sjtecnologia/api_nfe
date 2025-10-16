from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from database.connection import get_db
from sqlalchemy import text

auth_bp = Blueprint('auth', __name__)

# Classe User simples (sem arquivo separado)
class User:
    def __init__(self, user_id, username, role_name='client', permissions=None):
        self.user_id = user_id
        self.username = username
        self.role_name = role_name
        self.permissions = permissions or {}
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.user_id)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login do usuário - ESTRUTURA CORRETA DA TABELA"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = None
        try:
            db = next(get_db())
            
            # ✅ QUERY CORRETA COM OS NOMES REAIS DAS COLUNAS
            result = db.execute(text("""
                SELECT id, username, password_hash, _is_active
                FROM users
                WHERE username = :username AND _is_active = true
            """), {"username": username})
            
            user_data = result.first()
            
            if user_data and check_password_hash(user_data.password_hash, password):
                # Determinar role baseado no username (temporário)
                role_name = 'admin' if username == 'admin' else 'client'
                
                user = User(
                    user_id=user_data.id,  # ✅ USAR 'id' EM VEZ DE 'user_id'
                    username=user_data.username,
                    role_name=role_name,
                    permissions={}
                )
                login_user(user)
                
                print(f"✅ LOGIN: Usuário {username} (ID: {user_data.id}) logado com role {role_name}")
                
                # Determinar redirecionamento
                if role_name == 'admin':
                    return redirect(url_for('admin.admin_home'))
                else:
                    # Para usuários cliente, buscar cliente associado
                    cliente_result = db.execute(text("""
                        SELECT c.cliente_id 
                        FROM user_clients uc
                        JOIN clientes c ON c.cliente_id = uc.client_id
                        WHERE uc.user_id = :user_id AND c.ativo = true
                    """), {"user_id": user_data.id})  # ✅ USAR user_data.id
                    
                    cliente_data = cliente_result.first()
                    if cliente_data:
                        print(f"🔄 Redirecionando usuário {username} para cliente {cliente_data.cliente_id}")
                        return redirect(url_for('cliente.dashboard', cliente_id=cliente_data.cliente_id))
                    else:
                        print(f"⚠️  Nenhum cliente encontrado para user_id {user_data.id}")
                        
                        # Vamos ver se tem clientes disponíveis
                        clientes_result = db.execute(text("""
                            SELECT cliente_id, razao_social FROM clientes 
                            WHERE ativo = true
                            
                        """))
                        
                        clientes_disponiveis = [dict(row._mapping) for row in clientes_result]
                        
                        if clientes_disponiveis:
                            print(f"📋 Clientes disponíveis: {len(clientes_disponiveis)}")
                            # Por enquanto, redirecionar para o primeiro cliente
                            primeiro_cliente = clientes_disponiveis[0]
                            print(f"🔄 Redirecionando para primeiro cliente: {primeiro_cliente['razao_social']}")
                            return redirect(url_for('cliente.dashboard', cliente_id=primeiro_cliente['cliente_id']))
                        else:
                            flash('Nenhum cliente encontrado no sistema.', 'warning')
                            return redirect(url_for('home.home'))
                        
            else:
                print(f"❌ LOGIN FALHOU: Usuário {username} não encontrado ou senha incorreta")
                flash('Usuário ou senha inválidos.', 'danger')
                
        except Exception as e:
            print(f"❌ Erro no login: {e}")
            import traceback
            traceback.print_exc()
            flash('Erro interno do servidor.', 'danger')
        finally:
            if db is not None:
                db.close()
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    try:
        print(f"🚪 LOGOUT: Fazendo logout do usuário {current_user.username}")
        
        # Limpar TODA a sessão
        session.clear()
        
        # Fazer logout do Flask-Login
        logout_user()
        
        print("✅ LOGOUT: Sessão limpa e usuário deslogado")
        
        # Flash message para confirmar logout
        flash('Você foi desconectado com sucesso.', 'info')
        
        # Redirecionar para login
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        print(f"❌ ERRO no logout: {e}")
        # Mesmo com erro, limpar sessão e redirecionar
        session.clear()
        logout_user()
        return redirect(url_for('auth.login'))
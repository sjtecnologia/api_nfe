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
        print("\n" + "="*80)
        print("[AUTH] LOGIN: Iniciando processo de autenticação")
        print("="*80)
        
        username = request.form['username']
        password = request.form['password']
        print(f"[USER] Username: {username}")
        
        db = None
        try:
            print("[DATA] Conectando ao banco de dados...")
            db = next(get_db())
            print("[OK] Conexão estabelecida")
            
            print("[SEARCH] Buscando usuário no banco...")
            # [OK] QUERY CORRETA COM OS NOMES REAIS DAS COLUNAS
            result = db.execute(text("""
                SELECT id, username, password_hash, _is_active
                FROM users
                WHERE username = :username AND _is_active = true
            """), {"username": username})
            
            user_data = result.first()
            print(f"[LOG] Resultado da query: {'Usuário encontrado' if user_data else 'Usuário não encontrado'}")
            
            if not user_data:
                print("[X] Usuário não encontrado no banco")
                flash('Usuário ou senha inválidos.', 'danger')
                return render_template('login.html')
            
            # Usuário encontrado, verificar senha
            print("[KEY] Verificando senha...")
            senha_valida = check_password_hash(user_data.password_hash, password)
            print(f"[UNLOCK] Senha válida: {senha_valida}")
            
            if not senha_valida:
                print("[X] Senha incorreta")
                flash('Usuário ou senha inválidos.', 'danger')
                return render_template('login.html')
            
            # Autenticação bem-sucedida!
            print("[OK] Autenticação bem-sucedida!")
            
            # Determinar role baseado no username (temporário)
            role_name = 'admin' if username == 'admin' else 'client'
            print(f"[ADMIN] Role atribuída: {role_name}")
            
            print("[BUILD] Criando objeto User...")
            user = User(
                user_id=user_data.id,  # [OK] USAR 'id' EM VEZ DE 'user_id'
                username=user_data.username,
                role_name=role_name,
                permissions={}
            )
            
            print("[AUTH] Fazendo login do usuário...")
            login_user(user)
            
            print(f"[OK] [OK] LOGIN: Usuario {username} (ID: {user_data.id}) logado com role {role_name}")
            
            # Determinar redirecionamento
            print("[START] Determinando redirecionamento...")
            if role_name == 'admin':
                # Super admin vai para dashboard que mostra dados de todos os clientes
                print("--> Redirecionando para admin.dashboard")
                return redirect(url_for('admin.dashboard'))
            else:
                print("[SEARCH] Buscando clientes acessíveis do usuário...")
                # Buscar todos os clientes acessíveis do usuário
                clientes_result = db.execute(text("""
                    SELECT c.cliente_id, c.razao_social
                    FROM user_clients uc
                    JOIN clientes c ON c.cliente_id = uc.client_id
                    WHERE uc.user_id = :user_id AND c.ativo = true
                    ORDER BY c.razao_social ASC
                """), {"user_id": user_data.id})
                clientes_acessiveis = [dict(row._mapping) for row in clientes_result]
                print(f"[LIST] Clientes encontrados: {len(clientes_acessiveis)}")
                if clientes_acessiveis:
                    primeiro_cliente = clientes_acessiveis[0]
                    print(f"[CLIENT] Primeiro cliente: {primeiro_cliente['razao_social']} (ID: {primeiro_cliente['cliente_id']})")
                    
                    print("[SAVE] Salvando cliente na sessão...")
                    session['current_client_id'] = primeiro_cliente['cliente_id']
                    session['current_client_name'] = primeiro_cliente['razao_social']
                    
                    print(f"[OK] Cliente padrão atribuído: {primeiro_cliente['razao_social']} (ID: {primeiro_cliente['cliente_id']})")
                    print(f"--> Redirecionando para cliente.dashboard com cliente_id={primeiro_cliente['cliente_id']}")
                    print("="*80 + "\n")
                    return redirect(url_for('cliente.dashboard', cliente_id=primeiro_cliente['cliente_id']))
                else:
                    print(f"[!] Nenhum cliente encontrado para user_id {user_data.id}")
                    print("="*80 + "\n")
                    flash('Nenhum cliente encontrado no sistema.', 'warning')
                    return redirect(url_for('home.home'))
                
        except Exception as e:
            print("\n" + "="*80)
            print("[X] ERRO NO LOGIN")
            print("="*80)
            print(f"Tipo do erro: {type(e).__name__}")
            print(f"Mensagem: {str(e)}")
            print("\nTraceback completo:")
            import traceback
            traceback.print_exc()
            print("="*80 + "\n")
            flash('Erro interno do servidor.', 'danger')
            return render_template('login.html')
        finally:
            if db is not None:
                print("[?] Fechando conexão com banco de dados")
                db.close()
    
    # GET request - mostrar formulário de login
    print("[?] GET /login - Mostrando formulário de login")
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    try:
        print(f"[?] LOGOUT: Fazendo logout do usuário {current_user.username}")
        
        # Limpar TODA a sessão
        session.clear()
        
        # Fazer logout do Flask-Login
        logout_user()
        
        print("[OK] LOGOUT: Sessão limpa e usuário deslogado")
        
        # Flash message para confirmar logout
        flash('Você foi desconectado com sucesso.', 'info')
        
        # Redirecionar para login
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        print(f"[X] ERRO no logout: {e}")
        # Mesmo com erro, limpar sessão e redirecionar
        session.clear()
        logout_user()
        return redirect(url_for('auth.login'))
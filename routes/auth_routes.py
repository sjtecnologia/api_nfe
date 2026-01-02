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
    """Login do usuário - ACEITA EMAIL OU USERNAME"""
    if request.method == 'POST':
        print("\n" + "="*80)
        print("[AUTH] LOGIN: Iniciando processo de autenticação")
        print("="*80)
        
        email = request.form['username']  # Campo "username" no form, mas aceita email
        password = request.form['password']
        print(f"[USER] Email/Username: {email}")
        
        db = None
        try:
            print("[DATA] Conectando ao banco de dados...")
            db = next(get_db())
            print("[OK] Conexão estabelecida")
            
            print("[SEARCH] Buscando usuário no banco por EMAIL...")
            # [OK] BUSCA POR EMAIL AO INVÉS DE USERNAME
            result = db.execute(text("""
                SELECT id, username, email, password_hash, _is_active
                FROM users
                WHERE email = :email AND _is_active = true
            """), {"email": email})
            
            user_data = result.first()
            print(f"[LOG] Resultado da query: {'Usuário encontrado' if user_data else 'Usuário não encontrado'}")
            
            if not user_data:
                print("[X] Usuário não encontrado no banco")
                flash('Email ou senha inválidos.', 'danger')
                return render_template('login.html')
            
            # Usuário encontrado, verificar senha
            print("[KEY] Verificando senha...")
            senha_valida = check_password_hash(user_data.password_hash, password)
            print(f"[UNLOCK] Senha válida: {senha_valida}")
            
            if not senha_valida:
                print("[X] Senha incorreta")
                flash('Email ou senha inválidos.', 'danger')
                return render_template('login.html')
            
            # Autenticação bem-sucedida!
            print("[OK] Autenticação bem-sucedida!")
            
            # Determinar role baseado no email (temporário)
            role_name = 'admin' if user_data.email == 'admin@emitemax.com.br' else 'client'
            print(f"[ADMIN] Role atribuída: {role_name}")
            
            print("[BUILD] Criando objeto User...")
            user = User(
                user_id=user_data.id,  # [OK] USAR 'id' EM VEZ DE 'user_id'
                username=user_data.username or user_data.email,  # Usa username ou email
                role_name=role_name,
                permissions={}
            )
            
            print("[AUTH] Fazendo login do usuário...")
            login_user(user)
            
            print(f"[OK] [OK] LOGIN: Usuario {user_data.email} (ID: {user_data.id}) logado com role {role_name}")
            
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


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Solicita recuperação de senha"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Por favor, informe seu email.', 'warning')
            return render_template('forgot_password.html')
        
        db = None
        try:
            db = next(get_db())
            
            # Buscar usuário pelo email
            result = db.execute(text("""
                SELECT id, username, email
                FROM users
                WHERE email = :email AND _is_active = true
            """), {"email": email})
            
            user_data = result.first()
            
            if user_data:
                # Gerar token único
                import secrets
                from datetime import datetime, timedelta
                
                token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(hours=1)  # Token válido por 1 hora
                
                # Salvar token no banco
                db.execute(text("""
                    INSERT INTO password_reset_tokens (user_id, token, expires_at)
                    VALUES (:user_id, :token, :expires_at)
                """), {
                    "user_id": user_data.id,
                    "token": token,
                    "expires_at": expires_at
                })
                db.commit()
                
                # Enviar email com link de recuperação
                from utils.email_sender import enviar_email_recuperacao_senha
                
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                
                try:
                    enviar_email_recuperacao_senha(
                        destinatario=email,
                        usuario=user_data.username,
                        reset_url=reset_url
                    )
                    flash('Email de recuperação enviado! Verifique sua caixa de entrada.', 'success')
                except Exception as email_error:
                    print(f"[X] Erro ao enviar email: {email_error}")
                    flash('Erro ao enviar email. Tente novamente mais tarde.', 'danger')
            else:
                # Por segurança, mostrar mesma mensagem mesmo se email não existir
                flash('Se o email existir, você receberá as instruções de recuperação.', 'info')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            print(f"[X] Erro ao processar recuperação de senha: {e}")
            import traceback
            traceback.print_exc()
            flash('Erro ao processar solicitação. Tente novamente.', 'danger')
            return render_template('forgot_password.html')
        finally:
            if db is not None:
                db.close()
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reseta a senha com token válido"""
    db = None
    try:
        db = next(get_db())
        
        # Verificar se token é válido e não expirado
        from datetime import datetime
        
        result = db.execute(text("""
            SELECT prt.id, prt.user_id, prt.expires_at, prt.used, u.username, u.email
            FROM password_reset_tokens prt
            JOIN users u ON u.id = prt.user_id
            WHERE prt.token = :token
        """), {"token": token})
        
        token_data = result.first()
        
        if not token_data:
            flash('Link de recuperação inválido.', 'danger')
            return redirect(url_for('auth.login'))
        
        if token_data.used:
            flash('Este link já foi utilizado.', 'warning')
            return redirect(url_for('auth.login'))
        
        if token_data.expires_at < datetime.now():
            flash('Este link expirou. Solicite um novo link de recuperação.', 'warning')
            return redirect(url_for('auth.forgot_password'))
        
        # Token válido - processar formulário
        if request.method == 'POST':
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if not password or not confirm_password:
                flash('Por favor, preencha todos os campos.', 'warning')
                return render_template('reset_password.html')
            
            if password != confirm_password:
                flash('As senhas não coincidem.', 'danger')
                return render_template('reset_password.html')
            
            if len(password) < 6:
                flash('A senha deve ter no mínimo 6 caracteres.', 'danger')
                return render_template('reset_password.html')
            
            # Atualizar senha do usuário
            from werkzeug.security import generate_password_hash
            
            password_hash = generate_password_hash(password)
            
            db.execute(text("""
                UPDATE users
                SET password_hash = :password_hash
                WHERE id = :user_id
            """), {
                "password_hash": password_hash,
                "user_id": token_data.user_id
            })
            
            # Marcar token como usado
            db.execute(text("""
                UPDATE password_reset_tokens
                SET used = true, used_at = NOW()
                WHERE id = :token_id
            """), {"token_id": token_data.id})
            
            db.commit()
            
            print(f"[OK] Senha resetada com sucesso para usuário: {token_data.username}")
            flash('Senha resetada com sucesso! Faça login com sua nova senha.', 'success')
            return redirect(url_for('auth.login'))
        
        # GET request - mostrar formulário
        return render_template('reset_password.html')
        
    except Exception as e:
        print(f"[X] Erro ao resetar senha: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao resetar senha. Tente novamente.', 'danger')
        return redirect(url_for('auth.login'))
    finally:
        if db is not None:
            db.close()
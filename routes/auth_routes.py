import logging
from flask import Blueprint, render_template, redirect, url_for, session, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from database.connection import get_db
from database.models import User
from utils.password import verify_password, hash_password, needs_rehash
from sqlalchemy import text

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def _get_limiter():
    return current_app.extensions.get('limiter')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login do usuário - ACEITA EMAIL OU USERNAME"""
    limiter = _get_limiter()
    if limiter:
        limiter.limit('10/minute')(lambda: None)()

    if request.method == 'POST':
        logger.info("LOGIN: Iniciando autenticação")

        email = (request.form.get('username') or request.form.get('email') or '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            logger.warning("LOGIN: campos obrigatórios ausentes")
            flash('Email ou senha inválidos.', 'danger')
            return render_template('login.html')

        db = None
        try:
            db = next(get_db())

            result = db.execute(text("""
                SELECT id, username, email, password_hash, _is_active
                FROM users
                WHERE (LOWER(email) = LOWER(:login) OR LOWER(username) = LOWER(:login))
                  AND _is_active = true
            """), {"login": email})

            user_data = result.first()
            
            if not user_data:
                logger.warning("LOGIN: usuário não encontrado para login='%s'", email)
                flash('Email ou senha inválidos.', 'danger')
                return render_template('login.html')

            senha_valida = verify_password(user_data.password_hash, password)

            if not senha_valida:
                logger.warning("LOGIN: senha incorreta para user_id=%s", user_data.id)
                flash('Email ou senha inválidos.', 'danger')
                return render_template('login.html')
            
            # Rehash transparente: migra senhas legadas werkzeug para Argon2id
            if needs_rehash(user_data.password_hash):
                try:
                    new_hash = hash_password(password)
                    db.execute(text(
                        "UPDATE users SET password_hash = :h WHERE id = :uid"
                    ), {"h": new_hash, "uid": user_data.id})
                    db.commit()
                    logger.info("LOGIN: senha rehashed para user_id=%s", user_data.id)
                except Exception as rehash_err:
                    logger.warning("LOGIN: falha no rehash para user_id=%s: %s", user_data.id, rehash_err)

            logger.info("LOGIN: autenticação bem-sucedida user_id=%s", user_data.id)
            
            # Buscar roles do usuário no banco de dados
            user_roles_query = db.execute(text("""
                SELECT r.id, r.name, r.description
                FROM roles r
                INNER JOIN user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = :user_id
            """), {'user_id': user_data.id})
            
            user_roles = [{'id': row.id, 'name': row.name, 'description': row.description}
                         for row in user_roles_query]

            # Buscar clientes vinculados ao usuário
            user_clients_query = db.execute(text("""
                SELECT c.cliente_id, c.razao_social, c.nome_fantasia, c.cnpj
                FROM clientes c
                INNER JOIN user_clients uc ON c.cliente_id = uc.client_id
                WHERE uc.user_id = :user_id AND c.ativo = true
            """), {'user_id': user_data.id})
            
            user_clients = [{'cliente_id': row.cliente_id, 'razao_social': row.razao_social,
                           'nome_fantasia': row.nome_fantasia, 'cnpj': row.cnpj}
                          for row in user_clients_query]

            user = User(
                user_data.id,
                user_data.username or user_data.email,
                user_data.email,
                user_data._is_active,
                user_roles,
                user_clients
            )

            remember = request.form.get('remember_me') == 'on'
            login_user(user, remember=remember)

            logger.info("LOGIN: user_id=%s roles=%s clientes=%d",
                        user_data.id, [r['name'] for r in user_roles], len(user_clients))
            
            if user.is_super_admin():
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('home.home'))

        except Exception as e:
            logger.error("ERRO no login: %s", e, exc_info=True)
            flash('Erro interno do servidor.', 'danger')
            return render_template('login.html')
        finally:
            if db is not None:
                db.close()

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    try:
        logger.info("LOGOUT: user_id=%s", current_user.id)
        session.clear()
        logout_user()
        flash('Você foi desconectado com sucesso.', 'info')
        return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error("ERRO no logout: %s", e, exc_info=True)
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
                    resultado = enviar_email_recuperacao_senha(
                        destinatario=email,
                        usuario=user_data.username,
                        reset_url=reset_url
                    )
                    
                    if resultado and resultado.get('success'):
                        logger.info("Recuperação de senha: email enviado para %s", email)
                        flash('Email de recuperação enviado! Verifique sua caixa de entrada e spam.', 'success')
                    else:
                        erro_msg = resultado.get('message', 'Erro desconhecido') if resultado else 'Sem resposta do servidor'
                        logger.error("Falha ao enviar email de recuperação: %s", erro_msg)
                        flash(f'Erro ao enviar email: {erro_msg}', 'danger')
                except Exception as email_error:
                    logger.error("Exceção ao enviar email de recuperação: %s", email_error, exc_info=True)
                    flash('Erro ao enviar email. Entre em contato com o suporte.', 'danger')
            else:
                # Por segurança, mostrar mesma mensagem mesmo se email não existir
                flash('Se o email existir, você receberá as instruções de recuperação.', 'info')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error("Erro ao processar recuperação de senha: %s", e, exc_info=True)
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
            
            # Atualizar senha do usuário com Argon2id
            password_hash = hash_password(password)
            
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
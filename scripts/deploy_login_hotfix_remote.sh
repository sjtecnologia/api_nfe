#!/usr/bin/env bash

set -euo pipefail

# Uso:
#   scripts/deploy_login_hotfix_remote.sh
# Variaveis opcionais:
#   SSH_KEY="$HOME/Downloads/nfe-new-api-key.pem"
#   EC2_HOST="ubuntu@100.26.12.107"
#   SERVICE_NAME="api-nfe-principal"
#   APP_DIR="/home/ubuntu/api_nfe"

SSH_KEY="${SSH_KEY:-$HOME/Downloads/nfe-new-api-key.pem}"
EC2_HOST="${EC2_HOST:-ubuntu@100.26.12.107}"
SERVICE_NAME="${SERVICE_NAME:-api-nfe-principal}"
APP_DIR="${APP_DIR:-/home/ubuntu/api_nfe}"

if [[ ! -f "$SSH_KEY" ]]; then
    echo "Erro: chave SSH nao encontrada em $SSH_KEY"
    exit 1
fi

echo "[1/5] Criando backup remoto..."
BACKUP_DIR=$(ssh -i "$SSH_KEY" "$EC2_HOST" "
set -e
BACKUP_DIR=$APP_DIR/backups/hotfix_\$(date +%Y%m%d_%H%M%S)
mkdir -p \"\$BACKUP_DIR\"
cp $APP_DIR/routes/auth_routes.py \"\$BACKUP_DIR\"/
cp $APP_DIR/app.py \"\$BACKUP_DIR\"/
echo \"\$BACKUP_DIR\"
")
echo "Backup: $BACKUP_DIR"

echo "[2/5] Gerando patch remoto idempotente..."
cat > /tmp/remote_patch_login_http.py <<'PY'
from pathlib import Path


auth = Path('/home/ubuntu/api_nfe/routes/auth_routes.py')
a = auth.read_text(encoding='utf-8')

if 'from argon2 import PasswordHasher' not in a:
    a = a.replace(
        'from werkzeug.security import check_password_hash\n',
        'from werkzeug.security import check_password_hash\nfrom argon2 import PasswordHasher\nfrom argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError\n',
        1,
    )

if '_argon2_hasher = PasswordHasher()' not in a and "auth_bp = Blueprint('auth', __name__)" in a:
    marker = "auth_bp = Blueprint('auth', __name__)\n"
    helper = "\n_argon2_hasher = PasswordHasher()\n\ndef _verify_password_compat(stored_hash, plain_password):\n    if not stored_hash or not plain_password:\n        return False\n\n    if isinstance(stored_hash, str) and stored_hash.startswith('$argon2'):\n        try:\n            return _argon2_hasher.verify(stored_hash, plain_password)\n        except VerifyMismatchError:\n            return False\n        except (VerificationError, InvalidHashError) as hash_err:\n            print(f\"[WARN] Hash Argon2 invalido: {hash_err}\")\n            return False\n\n    try:\n        return check_password_hash(stored_hash, plain_password)\n    except (ValueError, TypeError) as hash_err:\n        print(f\"[WARN] Hash legado invalido: {hash_err}\")\n        return False\n\n"
    a = a.replace(marker, marker + helper, 1)

a = a.replace(
    "email = request.form['username']  # Campo \"username\" no form, mas aceita email",
    "email = (request.form.get('username') or request.form.get('email') or '').strip()  # Campo username no form",
)
a = a.replace("password = request.form['password']", "password = request.form.get('password', '')")

anchor = "        print(f\"[USER] Email/Username: {email}\")\n"
guard = "        if not email or not password:\n            flash('Email ou senha invalidos.', 'danger')\n            return render_template('login.html')\n"
if guard not in a and anchor in a:
    a = a.replace(anchor, anchor + "\n" + guard, 1)

a = a.replace(
    'senha_valida = check_password_hash(user_data.password_hash, password)',
    'senha_valida = _verify_password_compat(user_data.password_hash, password)',
)

auth.write_text(a, encoding='utf-8')


app = Path('/home/ubuntu/api_nfe/app.py')
p = app.read_text(encoding='utf-8')

if 'from werkzeug.exceptions import HTTPException' not in p:
    if 'from flask_wtf.csrf import generate_csrf\n' in p:
        p = p.replace(
            'from flask_wtf.csrf import generate_csrf\n',
            'from flask_wtf.csrf import generate_csrf\nfrom werkzeug.exceptions import HTTPException\n',
            1,
        )

if 'if isinstance(e, HTTPException):' not in p and '@app.errorhandler(Exception)' in p:
    p = p.replace(
        '@app.errorhandler(Exception)\ndef handle_exception(e):\n    """Handler para TODAS as exceções não tratadas"""\n    logger.error("Exceção não tratada — %s: %s", type(e).__name__, str(e), exc_info=True)\n    return internal_error(e)\n',
        '@app.errorhandler(Exception)\ndef handle_exception(e):\n    """Handler para TODAS as exceções não tratadas"""\n    if isinstance(e, HTTPException):\n        return e\n    logger.error("Exceção não tratada — %s: %s", type(e).__name__, str(e), exc_info=True)\n    return internal_error(e)\n',
        1,
    )

app.write_text(p, encoding='utf-8')
print('patched remote files')
PY

echo "[3/5] Aplicando patch e reiniciando servico..."
scp -i "$SSH_KEY" /tmp/remote_patch_login_http.py "$EC2_HOST":/tmp/remote_patch_login_http.py
ssh -i "$SSH_KEY" "$EC2_HOST" "python3 /tmp/remote_patch_login_http.py && sudo systemctl restart $SERVICE_NAME && sleep 3 && sudo systemctl is-active $SERVICE_NAME"

echo "[4/5] Smoke tests..."
echo "--- health interno ---"
ssh -i "$SSH_KEY" "$EC2_HOST" "curl -i -s http://127.0.0.1:8080/health | head -n 20"

echo "--- health publico ---"
curl -i -s http://100.26.12.107:8080/health | head -n 20

echo "--- rota inexistente (esperado 404) ---"
curl -i -s http://100.26.12.107:8080/rota-que-nao-existe | head -n 20

echo "--- login GET (esperado 200) ---"
curl -i -s http://100.26.12.107:8080/auth/login | head -n 20

echo "--- login POST invalido (sem 500) ---"
curl -i -s -c /tmp/api_nfe_hotfix_ck.txt http://100.26.12.107:8080/auth/login >/tmp/api_nfe_hotfix_get.out
curl -i -s -b /tmp/api_nfe_hotfix_ck.txt -X POST http://100.26.12.107:8080/auth/login -d 'username=naoexiste@teste.com&password=senhaerrada' | head -n 25

echo "[5/5] Ultimas linhas de log..."
ssh -i "$SSH_KEY" "$EC2_HOST" "tail -n 80 $APP_DIR/logs/error.log"

echo "Concluido. Backup remoto em: $BACKUP_DIR"
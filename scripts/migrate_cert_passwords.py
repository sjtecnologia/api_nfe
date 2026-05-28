"""
Script de migração de senhas de certificados digitais.

Contexto:
- Código ANTIGO usava: salt fixo b'cert_salt_nfe_2024' + chave padrão 'default_master_key_change_in_production_2024'
- Código NOVO usa: salt derivado de hashlib.sha256(CERT_MASTER_KEY) + CERT_MASTER_KEY do env

Este script:
1. Lê todas as senhas criptografadas com a chave ANTIGA
2. Re-criptografa com a chave NOVA (lida de CERT_MASTER_KEY no env/.env)
3. Atualiza o banco

EXECUTAR NO SERVIDOR AWS ANTES DE FAZER DEPLOY DO NOVO CÓDIGO.
"""

import os
import sys
import base64
import hashlib

from dotenv import load_dotenv
load_dotenv()

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import create_engine, text


# ─── Chave ANTIGA (hard-coded como estava no código) ─────────────────────────

def _get_old_encryption_key():
    """Recria a chave usada pelo código legado (salt fixo)."""
    master_key = 'default_master_key_change_in_production_2024'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'cert_salt_nfe_2024',   # salt fixo original
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))


# ─── Chave NOVA (derivada de CERT_MASTER_KEY do env) ─────────────────────────

def _get_new_encryption_key():
    """Recria a chave com o novo esquema (salt derivado da própria master key)."""
    master_key = os.environ.get('CERT_MASTER_KEY')
    if not master_key:
        print("[ERRO] CERT_MASTER_KEY não está definida no ambiente.")
        sys.exit(1)
    salt = hashlib.sha256(master_key.encode()).digest()[:16]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))


def decrypt_old(encrypted_b64: str) -> str | None:
    """Tenta descriptografar com a chave antiga."""
    try:
        key = _get_old_encryption_key()
        f = Fernet(key)
        raw = base64.b64decode(encrypted_b64.encode('utf-8'))
        return f.decrypt(raw).decode('utf-8')
    except (InvalidToken, Exception):
        return None


def decrypt_fallback(encrypted_b64: str) -> str | None:
    """Tenta base64 simples (método legado mais antigo ainda)."""
    try:
        return base64.b64decode(encrypted_b64.encode('utf-8')).decode('utf-8')
    except Exception:
        return None


def encrypt_new(password: str) -> str:
    """Criptografa com a nova chave."""
    key = _get_new_encryption_key()
    f = Fernet(key)
    encrypted_bytes = f.encrypt(password.encode('utf-8'))
    return base64.b64encode(encrypted_bytes).decode('utf-8')


def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("[ERRO] DATABASE_URL não definida.")
        sys.exit(1)

    print(f"[INFO] Conectando ao banco de dados...")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT certificado_digital_id, senha_certificado FROM certificados_digitais ORDER BY certificado_digital_id"
        )).fetchall()

    print(f"[INFO] Encontrados {len(rows)} certificados para migrar.")

    success = 0
    failed = 0

    with engine.connect() as conn:
        for row in rows:
            cert_id, senha_enc = row[0], row[1]

            if not senha_enc:
                print(f"  [{cert_id}] Sem senha registrada — pulando.")
                continue

            # 1) Tentar descriptografar com chave antiga
            senha_plain = decrypt_old(senha_enc)
            method = "Fernet-antigo"

            if senha_plain is None:
                # 2) Tentar base64 simples
                senha_plain = decrypt_fallback(senha_enc)
                method = "base64-legado"

            if senha_plain is None:
                # 3) Pode já estar em texto plano (muito improvável mas seguro)
                senha_plain = senha_enc
                method = "texto-plano"
                print(f"  [{cert_id}] AVISO: não foi possível descriptografar — assumindo texto plano.")

            # Re-criptografar com nova chave
            try:
                nova_senha_enc = encrypt_new(senha_plain)
                conn.execute(
                    text("UPDATE certificados_digitais SET senha_certificado = :s WHERE certificado_digital_id = :id"),
                    {'s': nova_senha_enc, 'id': cert_id}
                )
                conn.commit()
                print(f"  [{cert_id}] OK  (descriptografado via {method}, re-encriptado com nova chave)")
                success += 1
            except Exception as e:
                print(f"  [{cert_id}] FALHA ao re-encriptar: {e}")
                conn.rollback()
                failed += 1

    print()
    print(f"[RESULTADO] {success} migrados com sucesso, {failed} com falha.")
    if failed:
        print("[AVISO] Resolva as falhas antes de fazer deploy do novo código!")
        sys.exit(1)
    else:
        print("[OK] Migração concluída. Pode prosseguir com o deploy.")


if __name__ == '__main__':
    main()

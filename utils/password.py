"""
Utilitário centralizado de hashing de senhas.

Usa Argon2id (RFC 9106) como algoritmo primário.
A verificação aceita também hashes legados werkzeug (pbkdf2:sha256)
para suporte à migração transparente.
"""
import logging
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

logger = logging.getLogger(__name__)

# Parâmetros Argon2id — OWASP 2024 mínimos:
#   time_cost ≥ 2 iterações, memory_cost ≥ 19 MiB, parallelism ≥ 1
_ph = PasswordHasher(
    time_cost=3,        # iterações
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain_password: str) -> str:
    """
    Gera hash Argon2id da senha.

    Raises:
        ValueError: se plain_password for vazio.
    """
    if not plain_password:
        raise ValueError("Senha não pode ser vazia.")
    return _ph.hash(plain_password)


def verify_password(stored_hash: str, plain_password: str) -> bool:
    """
    Verifica senha contra hash armazenado.
    Suporta hashes Argon2id (novo) e werkzeug pbkdf2:sha256 (legado).

    Returns:
        True se a senha for válida, False caso contrário.
    """
    if not stored_hash or not plain_password:
        return False

    # Argon2id (formato: $argon2id$...)
    if stored_hash.startswith("$argon2"):
        try:
            return _ph.verify(stored_hash, plain_password)
        except VerifyMismatchError:
            return False
        except (VerificationError, InvalidHashError) as e:
            logger.warning("Erro ao verificar hash Argon2id: %s", e)
            return False

    # Legado: werkzeug pbkdf2:sha256 (formato: pbkdf2:sha256:...)
    try:
        from werkzeug.security import check_password_hash
        return check_password_hash(stored_hash, plain_password)
    except Exception as e:
        logger.warning("Erro ao verificar hash legado werkzeug: %s", e)
        return False


def needs_rehash(stored_hash: str) -> bool:
    """
    Retorna True se o hash não usa os parâmetros Argon2id atuais
    (hash legado werkzeug ou parâmetros desatualizados).
    Útil para rehash transparente no login.
    """
    if not stored_hash.startswith("$argon2"):
        return True
    try:
        return _ph.check_needs_rehash(stored_hash)
    except Exception:
        return True

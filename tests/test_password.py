"""
Testes unitários para utils/password.py.

Não requerem banco de dados ou contexto Flask.
"""
import pytest
from utils.password import hash_password, verify_password, needs_rehash


class TestHashPassword:
    def test_returns_argon2id_hash(self):
        h = hash_password("SenhaForte@123")
        assert h.startswith("$argon2id$")

    def test_empty_password_raises(self):
        with pytest.raises(ValueError):
            hash_password("")

    def test_none_equivalent_raises(self):
        with pytest.raises((ValueError, TypeError)):
            hash_password(None)

    def test_different_hashes_same_password(self):
        """Argon2id usa salt aleatório — dois hashes da mesma senha devem diferir."""
        h1 = hash_password("igual")
        h2 = hash_password("igual")
        assert h1 != h2


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password("MinhaSenha#1")
        assert verify_password(h, "MinhaSenha#1") is True

    def test_wrong_password_returns_false(self):
        h = hash_password("MinhaSenha#1")
        assert verify_password(h, "SenhaErrada") is False

    def test_empty_password_returns_false(self):
        h = hash_password("alguma")
        assert verify_password(h, "") is False

    def test_empty_hash_returns_false(self):
        assert verify_password("", "qualquer") is False

    def test_legacy_werkzeug_hash(self):
        """Hashes werkzeug pbkdf2 legados devem ser verificados corretamente."""
        from werkzeug.security import generate_password_hash
        legacy = generate_password_hash("LegacyPass@1")
        assert verify_password(legacy, "LegacyPass@1") is True
        assert verify_password(legacy, "Errada") is False


class TestNeedsRehash:
    def test_argon2id_hash_no_rehash_needed(self):
        h = hash_password("SenhaNova@1")
        assert needs_rehash(h) is False

    def test_werkzeug_hash_needs_rehash(self):
        from werkzeug.security import generate_password_hash
        legacy = generate_password_hash("SenhaLegacy@1")
        assert needs_rehash(legacy) is True

    def test_empty_string_needs_rehash(self):
        assert needs_rehash("") is True

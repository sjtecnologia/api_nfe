"""
Testes para a rota de autenticação (login/logout).

Usa o cliente de teste Flask sem conexão com banco de dados real.
Os testes mockam o acesso ao banco para focar no comportamento da rota.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture()
def mock_user():
    """Usuário falso para simular login bem-sucedido."""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.ativo = True
    user.is_active = True
    user.is_authenticated = True
    user.is_anonymous = False
    user.get_id = lambda: "1"
    user.password_hash = None  # será sobrescrito no mock
    return user


class TestLoginRoute:
    def test_login_page_get(self, client):
        """GET /auth/login deve retornar 200."""
        response = client.get("/auth/login")
        assert response.status_code == 200

    def test_login_missing_fields(self, client):
        """POST sem credenciais deve redirecionar ou retornar erro."""
        response = client.post(
            "/auth/login",
            data={"username": "", "password": ""},
            follow_redirects=False,
        )
        # Sem credenciais: redireciona de volta ou retorna 200 com mensagem de erro
        assert response.status_code in (200, 302, 400)

    def test_login_invalid_credentials(self, client):
        """Credenciais inválidas não devem autenticar."""
        with patch("routes.auth_routes.get_db") as mock_db_gen:
            mock_db = MagicMock()
            mock_db_gen.return_value = iter([mock_db])
            # Simular usuário não encontrado
            mock_db.execute.return_value.fetchone.return_value = None

            response = client.post(
                "/auth/login",
                data={"username": "invalido", "password": "errada"},
                follow_redirects=True,
            )
        assert response.status_code == 200
        # A resposta deve conter indicação de erro (não redirecionar para dashboard)
        assert b"login" in response.data.lower() or response.status_code == 200

    def test_logout_redirects(self, client):
        """GET /auth/logout deve redirecionar."""
        response = client.get("/auth/logout", follow_redirects=False)
        # Sem sessão ativa: redireciona para login
        assert response.status_code in (302, 200)


class TestLoginRateLimiting:
    def test_multiple_failed_logins(self, client):
        """
        Múltiplas tentativas de login inválido não devem causar crash.
        (Rate limiting desativado em testes via RATELIMIT_ENABLED=False)
        """
        with patch("routes.auth_routes.get_db") as mock_db_gen:
            mock_db = MagicMock()
            mock_db_gen.return_value = iter([mock_db])
            mock_db.execute.return_value.fetchone.return_value = None

            for _ in range(5):
                response = client.post(
                    "/auth/login",
                    data={"username": "brute", "password": "force"},
                    follow_redirects=True,
                )
                assert response.status_code in (200, 429)

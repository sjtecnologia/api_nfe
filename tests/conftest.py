"""
Fixtures compartilhadas para o pytest.

O app Flask não usa create_app(), então configuramos as variáveis
de ambiente ANTES da importação para evitar RuntimeError de
configuração ausente.
"""
import os
import pytest
import werkzeug

if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'

# Variáveis de ambiente mínimas necessárias antes de qualquer import do app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-tests")
os.environ.setdefault("FLASK_ENV", "testing")


@pytest.fixture(scope="session")
def app():
    """Cria a instância Flask com configurações de teste."""
    from app import app as flask_app
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,  # desabilitar CSRF nos testes
        RATELIMIT_ENABLED=False,  # desabilitar rate limiting nos testes
        SERVER_NAME="localhost",
    )
    yield flask_app


@pytest.fixture()
def client(app):
    """Cliente de teste HTTP."""
    return app.test_client()


@pytest.fixture()
def runner(app):
    """CLI runner de teste."""
    return app.test_cli_runner()

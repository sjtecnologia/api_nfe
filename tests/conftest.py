"""
Fixtures compartilhadas para o pytest.

O app Flask não usa create_app(), então configuramos as variáveis
de ambiente ANTES da importação para evitar RuntimeError de
configuração ausente.
"""
import os
import sys
from pathlib import Path
import pytest
import werkzeug

if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3'

# Variáveis de ambiente mínimas necessárias antes de qualquer import do app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-tests")
os.environ.setdefault("FLASK_ENV", "testing")

# Garante import absoluto de módulos do projeto (ex.: utils.*, routes.*) nos testes.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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
    
    # Criar tabelas no banco em memória
    with flask_app.app_context():
        try:
            from database.models import Base
            from database.connection import engine
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"Aviso ao criar tabelas: {e}")
    
    yield flask_app


@pytest.fixture()
def client(app):
    """Cliente de teste HTTP."""
    return app.test_client()


@pytest.fixture()
def runner(app):
    """CLI runner de teste."""
    return app.test_cli_runner()

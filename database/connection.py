import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from config.settings import SQLALCHEMY_DATABASE_URL

if "postgresql" in SQLALCHEMY_DATABASE_URL:
    os.environ['DB_TYPE'] = 'postgresql'

# Configurar timezone para America/Sao_Paulo em todas as conexões PostgreSQL
_engine_kwargs = {
    'echo': False,
}

if "postgresql" in SQLALCHEMY_DATABASE_URL:
    _engine_kwargs.update({
        # Pool de conexões otimizado (apenas PostgreSQL)
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_pre_ping': True,   # Valida conexão antes de usar (detecta quedas)
        'pool_recycle': 1800,    # Recicla conexões a cada 30 min
        'connect_args': {'options': '-c timezone=America/Sao_Paulo'},
    })

engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependência para obter a sessão do DB em cada requisição (padrão legado)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    """
    Context manager para acesso ao banco de dados.
    Uso preferido em novos handlers:

        with db_session() as db:
            rows = db.execute(text("SELECT ..."), {...}).fetchall()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

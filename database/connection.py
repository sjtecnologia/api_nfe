import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from config.settings import SQLALCHEMY_DATABASE_URL

if "postgresql" in SQLALCHEMY_DATABASE_URL:
    os.environ['DB_TYPE'] = 'postgresql'

# Configurar timezone para America/Sao_Paulo em todas as conexões PostgreSQL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=False,
    connect_args={'options': '-c timezone=America/Sao_Paulo'} if "postgresql" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependência para obter a sessão do DB em cada requisição"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
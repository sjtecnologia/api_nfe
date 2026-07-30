"""
Utilitários de banco de dados: context manager de sessão e queries reutilizáveis.
Elimina os 70+ blocos try/except/finally/_get_db() duplicados no projeto.
"""
from contextlib import contextmanager
from typing import Optional
from sqlalchemy import text
from database.connection import get_db


def _get_db():
    """Retorna uma conexão de banco de dados. Use db_session() sempre que possível."""
    return next(get_db())


@contextmanager
def db_session():
    """
    Context manager para sessão de banco de dados com commit/rollback automático.

    Uso:
        from utils.db_utils import db_session

        with db_session() as db:
            db.execute(text("DELETE FROM tabela WHERE id = :id"), {'id': row_id})
        # commit automático ao sair do bloco
        # rollback automático em caso de exceção
    """
    db = next(get_db())
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_cliente_by_id(db, cliente_id: int) -> Optional[dict]:
    """Busca um cliente pelo ID. Retorna dict ou None."""
    if not cliente_id:
        return None
    row = db.execute(
        text("SELECT * FROM clientes WHERE cliente_id = :cid"),
        {'cid': int(cliente_id)}
    ).fetchone()
    return dict(row._mapping) if row else None


def get_all_clientes(db) -> list:
    """Retorna lista de todos os clientes ordenada por razão social."""
    rows = db.execute(
        text("SELECT cliente_id, razao_social FROM clientes ORDER BY razao_social")
    ).fetchall()
    return [dict(r._mapping) for r in rows]

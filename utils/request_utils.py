"""
Utilitários para extrair parâmetros da request Flask.
Unifica as 8 formas diferentes de resolver cliente_id e as 2 chaves de sessão.
"""
from typing import Optional
from flask import request, session

# Chaves de sessão aceitas (em ordem de prioridade)
_SESSION_CLIENTE_KEYS = ('current_client_id', 'active_cliente_id')


def get_current_cliente_id(param_name: str = 'cliente_id') -> Optional[int]:
    """
    Única fonte da verdade para resolver o cliente_id corrente.

    Verifica em ordem:
      1. request.args (query string)
      2. request.form (POST body)
      3. session['current_client_id']
      4. session['active_cliente_id']

    Retorna int ou None.

    Uso:
        from utils.request_utils import get_current_cliente_id

        cliente_id = get_current_cliente_id()
        if not cliente_id:
            return error('Cliente não selecionado', 400)
    """
    raw = (
        request.args.get(param_name)
        or request.form.get(param_name)
        or next((session.get(k) for k in _SESSION_CLIENTE_KEYS if session.get(k)), None)
    )
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None

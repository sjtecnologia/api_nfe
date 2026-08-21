"""Validações compartilhadas de empresa ativa para a camada de inteligência."""

from __future__ import annotations

from typing import Any


def resolve_active_cliente_id(current_user: Any, session: dict[str, Any]) -> int:
    """Resolve exclusivamente a empresa ativa da sessão e valida o escopo."""
    raw = session.get('current_client_id') or session.get('active_cliente_id')
    if raw in (None, ''):
        raise ValueError('Selecione uma empresa para continuar')

    cliente_id = int(raw)
    if current_user.is_super_admin():
        return cliente_id

    accessible = {
        int(item.get('cliente_id'))
        for item in (current_user.get_accessible_clients() or [])
        if item.get('cliente_id') is not None
    }
    if cliente_id not in accessible:
        raise PermissionError('Acesso negado ao cliente ativo')
    return cliente_id

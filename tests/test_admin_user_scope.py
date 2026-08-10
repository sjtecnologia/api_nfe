"""
Testes de escopo da listagem de usuários no admin.

Objetivo: garantir que Admin comum veja apenas usuários do cliente ativo,
enquanto Super Admin mantém visão global.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from flask import session

from routes import admin_routes


class _FakeUser:
    def __init__(self, user_id, super_admin=False):
        self.id = user_id
        self._super_admin = super_admin

    def is_super_admin(self):
        return self._super_admin


class _Row:
    def __init__(self, **kwargs):
        self._mapping = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


def _undecorated_list_usuarios():
    """Remove wrappers de decorators para testar apenas a lógica da rota."""
    return admin_routes.list_usuarios.__wrapped__.__wrapped__


def test_list_usuarios_admin_sem_cliente_ativo_retorna_vazio(app):
    view = _undecorated_list_usuarios()

    with app.test_request_context('/admin/usuarios'):
        db = MagicMock()
        with patch('routes.admin_routes.current_user', _FakeUser(10, super_admin=False)), \
             patch('routes.admin_routes._get_db', return_value=db), \
             patch('routes.admin_routes.render_template', side_effect=lambda tpl, **ctx: ctx):
            result = view()

    assert result['usuarios'] == []
    db.execute.assert_not_called()


def test_list_usuarios_admin_com_cliente_ativo_aplica_filtro_por_cliente(app):
    view = _undecorated_list_usuarios()

    with app.test_request_context('/admin/usuarios?q=joao'):
        session['current_client_id'] = 27

        db = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(first=lambda: (1,)),
            SimpleNamespace(fetchall=lambda: [_Row(id=2, username='joao', email='joao@x.com', _is_active=True, created_at=None)]),
            SimpleNamespace(fetchall=lambda: [SimpleNamespace(name='Admin')]),
        ]

        with patch('routes.admin_routes.current_user', _FakeUser(10, super_admin=False)), \
             patch('routes.admin_routes._get_db', return_value=db), \
             patch('routes.admin_routes.render_template', side_effect=lambda tpl, **ctx: ctx):
            result = view()

    assert len(result['usuarios']) == 1
    assert result['usuarios'][0]['id'] == 2

    # 1a query: valida acesso ao cliente ativo
    access_params = db.execute.call_args_list[0].args[1]
    assert access_params['current_user_id'] == 10
    assert access_params['active_client_id'] == 27

    # 2a query: listagem filtrada pelo cliente ativo
    list_params = db.execute.call_args_list[1].args[1]
    assert list_params['active_client_id'] == 27
    assert list_params['q'] == '%joao%'


def test_list_usuarios_super_admin_lista_todos_sem_filtro_cliente(app):
    view = _undecorated_list_usuarios()

    with app.test_request_context('/admin/usuarios'):
        db = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(fetchall=lambda: [_Row(id=1, username='root', email='root@x.com', _is_active=True, created_at=None)]),
            SimpleNamespace(fetchall=lambda: [SimpleNamespace(name='Super_Admin')]),
        ]

        with patch('routes.admin_routes.current_user', _FakeUser(1, super_admin=True)), \
             patch('routes.admin_routes._get_db', return_value=db), \
             patch('routes.admin_routes.render_template', side_effect=lambda tpl, **ctx: ctx):
            result = view()

    assert len(result['usuarios']) == 1
    assert result['usuarios'][0]['username'] == 'root'

    # Super admin não deve executar query de validação de cliente ativo.
    first_query_sql = str(db.execute.call_args_list[0].args[0])
    assert 'WHERE username ILIKE :q OR email ILIKE :q' not in first_query_sql
    assert 'FROM users' in first_query_sql

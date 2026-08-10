"""
Testes de autorização para stubs administrativos do blueprint admin.
"""

from types import SimpleNamespace
from unittest.mock import patch

from routes import admin_routes


class _FakeUser:
    def __init__(self, user_id, authenticated=True):
        self.id = user_id
        self.is_authenticated = authenticated


def _build_db_with_roles(role_names):
    class _DB:
        def execute(self, query, *_args, **_kwargs):
            sql = str(query)

            if "r.name = 'Super_Admin'" in sql:
                rows = [SimpleNamespace(name='Super_Admin')] if 'Super_Admin' in role_names else []
                return SimpleNamespace(fetchall=lambda: rows)

            if "r.name IN ('Admin', 'Super_Admin')" in sql:
                allowed = [r for r in role_names if r in ('Admin', 'Super_Admin')]
                rows = [SimpleNamespace(name=role) for role in allowed]
                return SimpleNamespace(fetchall=lambda: rows)

            rows = [SimpleNamespace(name=role) for role in role_names]
            return SimpleNamespace(fetchall=lambda: rows)

        def close(self):
            return None

    return _DB()


def test_list_user_permissions_exige_super_admin(app):
    # Remove login_required e testa comportamento do super_admin_required
    view = admin_routes.list_user_permissions.__wrapped__

    with app.test_request_context('/admin/user-permissions'):
        with patch('auth.decorators.current_user', _FakeUser(20)), \
             patch('auth.decorators.get_db', return_value=iter([_build_db_with_roles(['Admin'])])):
            response = view()

    assert response.status_code == 302
    assert response.location.endswith('/')


def test_list_user_permissions_super_admin_permitido(app):
    view = admin_routes.list_user_permissions.__wrapped__

    with app.test_request_context('/admin/user-permissions'):
        with patch('auth.decorators.current_user', _FakeUser(1)), \
             patch('auth.decorators.get_db', return_value=iter([_build_db_with_roles(['Super_Admin'])])):
            response = view()

    assert response.status_code == 302
    assert '/admin/' in response.location


def test_list_logs_exige_admin_ou_super_admin(app):
    view = admin_routes.list_logs.__wrapped__

    with app.test_request_context('/admin/logs'):
        with patch('auth.decorators.current_user', _FakeUser(30)), \
             patch('auth.decorators.get_db', return_value=iter([_build_db_with_roles(['Viewer'])])):
            response = view()

    assert response.status_code == 302
    assert '/auth/login' in response.location


def test_configuracoes_admin_permitido(app):
    view = admin_routes.configuracoes.__wrapped__

    with app.test_request_context('/admin/configuracoes'):
        with patch('auth.decorators.current_user', _FakeUser(31)), \
             patch('auth.decorators.get_db', return_value=iter([_build_db_with_roles(['Admin'])])):
            response = view()

    assert response.status_code == 302
    assert '/admin/' in response.location

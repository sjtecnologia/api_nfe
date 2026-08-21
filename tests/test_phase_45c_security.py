"""Testes A/B mínimos para o gate de segurança da Fase 4.5C."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _login(client, user_id="7001"):
    with client.session_transaction() as session:
        session["_user_id"] = user_id
        session["_fresh"] = True


def _db_for_next_number():
    db = MagicMock()
    db.execute.side_effect = [
        SimpleNamespace(fetchone=lambda: None),
        SimpleNamespace(fetchone=lambda: (1,)),
    ]
    return db


def test_empresa_a_nao_consulta_proximo_numero_da_empresa_b(app, client):
    user = type(
        "TenantUser",
        (),
        {
            "id": 7001,
            "is_authenticated": True,
            "is_active": True,
            "is_anonymous": False,
            "get_id": lambda self: "7001",
        },
    )()
    db = _db_for_next_number()

    with patch("models.user.User.get", return_value=user), \
         patch("routes.nfe_routes.get_db", return_value=iter([db])), \
         patch("routes.nfe_routes.get_accessible_client_ids", return_value=[101]):
        _login(client)
        response = client.get("/admin/nfe/api/proximo-numero?cliente_id=202")

    assert response.status_code == 403
    assert response.is_json
    assert response.get_json()["success"] is False
    db.execute.assert_not_called()


def test_usuario_a_nao_visualiza_nfe_da_empresa_b(app, client):
    user = type(
        "TenantViewer",
        (),
        {
            "id": 7002,
            "is_authenticated": True,
            "is_active": True,
            "is_anonymous": False,
            "get_id": lambda self: "7002",
        },
    )()
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = [SimpleNamespace(name="Viewer")]

    with patch("models.user.User.get", return_value=user), \
         patch("routes.nfe_routes.get_db", return_value=iter([db])), \
         patch("auth.decorators.get_db", return_value=iter([db])), \
         patch("routes.nfe_routes.get_accessible_client_ids", return_value=[101]):
        _login(client, "7002")
        response = client.get("/admin/nfe/list?cliente_id=202")

    assert response.status_code == 302
    assert "/" in response.headers["Location"]


def test_empresa_a_nao_pode_emitir_nfce_com_cliente_b(app):
    from routes import nfce_routes

    source = open("routes/nfce_routes.py", encoding="utf-8").read()
    assert "emitente_cliente_id not in accessible_clients" in source
    assert "session['current_client_id'] = emitente_cliente_id" in source


def test_matriz_roles_para_emissao_e_visualizacao(app):
    from auth.decorators import editor_or_admin_required, viewer_or_higher_required

    def target():
        return "allowed"

    cases = {
        "Viewer": (False, True),
        "Editor": (True, True),
        "Admin": (True, True),
        "Super_Admin": (True, True),
    }

    for role, (can_emit, can_view) in cases.items():
        user = type(
            "RoleUser",
            (),
            {"id": 8001, "is_authenticated": True},
        )()
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [SimpleNamespace(name=role)]

        with app.test_request_context("/admin/nfe/emitir"):
            with patch("auth.decorators.current_user", user), \
                 patch("auth.decorators.get_db", return_value=iter([db])):
                emit_response = editor_or_admin_required()(target)()

        with app.test_request_context("/admin/nfe/list"):
            with patch("auth.decorators.current_user", user), \
                 patch("auth.decorators.get_db", return_value=iter([db])):
                view_response = viewer_or_higher_required()(target)()

        assert (emit_response == "allowed") is can_emit, role
        assert (view_response == "allowed") is can_view, role


def test_permission_required_sem_permissao_retorna_403_json(app):
    from auth.decorators import permission_required

    user = type("PermissionUser", (), {"id": 8002, "is_authenticated": True})()
    db = MagicMock()
    db.execute.return_value.first.side_effect = [None, None]

    with app.test_request_context("/api/protegida", headers={"Accept": "application/json"}):
        with patch("auth.decorators.current_user", user), \
             patch("auth.decorators.get_db", return_value=iter([db])):
            response = permission_required("nfe.issue")(lambda: "allowed")()

    assert response[1] == 403
    assert response[0].get_json()["error"].startswith("Permissão")

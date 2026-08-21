"""Blindagem comportamental da Fase 4.5B.

Estes testes devem falhar quando o núcleo de autenticação, rotas globais,
CSRF, templates críticos ou JavaScript de emissão regredirem.
"""

import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import template_rendered


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CRITICAL_TEMPLATES = (
    "templates/base.html",
    "templates/cliente/base.html",
    "templates/admin/dashboard.html",
)


def _static_url_for_endpoints(template_path):
    content = Path(template_path).read_text(encoding="utf-8")
    return sorted(set(re.findall(
        r"url_for\(\s*['\"]([^'\"]+)['\"]",
        content,
    )))


def _login_session(client, user_id="9001"):
    with client.session_transaction() as session:
        session["_user_id"] = user_id
        session["_fresh"] = True


def test_blueprint_registered_from_active_module(app):
    blueprint = app.blueprints.get("nfe")
    assert blueprint is not None
    assert blueprint.import_name == "routes.nfe_routes"
    assert app.view_functions["nfe.emitir_nfe"].__module__ == "routes.nfe_routes"


def test_active_emission_route_renders_canonical_template(app):
    rendered = []

    def capture(sender, template, context, **extra):
        rendered.append(template.name)

    cliente = SimpleNamespace(
        cliente_id=1,
        razao_social="Empresa Teste",
        nome_fantasia="Empresa Teste",
        cnpj="11444777000161",
        logradouro="Rua Teste",
        numero="1",
        bairro="Centro",
        cep="01001000",
        codigo_municipio="3550308",
        nome_municipio="Sao Paulo",
        uf="SP",
        inscricao_estadual="110042490114",
        regime_tributario_id=None,
        ambiente=2,
        telefone_contato=None,
    )

    def query_for(model):
        query = MagicMock()
        query.filter_by.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.first.return_value = cliente if getattr(model, "__name__", "") == "Cliente" else None
        query.all.return_value = []
        return query

    db = MagicMock()
    db.query.side_effect = query_for
    db.execute.return_value.fetchone.return_value = None
    db.close.return_value = None

    view = app.view_functions["nfe.emitir_nfe"]
    while hasattr(view, "__wrapped__"):
        view = view.__wrapped__

    with template_rendered.connected_to(capture, app):
        with app.test_request_context("/admin/nfe/emitir?cliente_id=1"):
            with patch("routes.nfe_routes.get_db", return_value=iter([db])), \
                 patch("routes.nfe_routes.get_accessible_client_ids", return_value=[1]):
                response = view()

    assert isinstance(response, str)
    assert rendered == ["admin/nfes/emitir.html"]


def test_no_active_route_renders_legacy_emission_template(app):
    legacy_references = []
    pattern = re.compile(r"render_template(?:_string)?\(\s*['\"]([^'\"]*emitir[^'\"]*)")

    for path in PROJECT_ROOT.glob("**/*.py"):
        if path == Path(__file__):
            continue
        if any(part in {".git", "backup_aws", "backups", "__pycache__"} for part in path.parts):
            continue
        for match in pattern.finditer(path.read_text(encoding="utf-8", errors="ignore")):
            if "routes/emitir" in match.group(1) or match.group(1) == "emitir.html":
                legacy_references.append(f"{path}:{match.group(1)}")

    assert legacy_references == []


def test_login_routes_are_reachable(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"password" in response.data.lower()

    legacy_response = client.get("/login", follow_redirects=False)
    assert legacy_response.status_code in {301, 302, 303, 307, 308}
    assert "/auth/login" in legacy_response.headers["Location"]


def test_login_page_renders_base_without_build_error(app, client):
    rendered = []

    def capture(sender, template, context, **extra):
        rendered.append(template.name)

    with template_rendered.connected_to(capture, app):
        response = client.get("/auth/login")

    assert response.status_code == 200
    assert "login.html" in rendered
    assert "base.html" not in rendered
    assert b"Internal Server Error" not in response.data


def test_critical_templates_reference_registered_endpoints(app):
    missing = {
        template: [
            endpoint for endpoint in _static_url_for_endpoints(template)
            if endpoint not in app.view_functions
        ]
        for template in CRITICAL_TEMPLATES
    }
    missing = {template: endpoints for template, endpoints in missing.items() if endpoints}
    assert missing == {}


def test_admin_test_ai_is_registered_with_expected_endpoint(app):
    rule = next(
        (rule for rule in app.url_map.iter_rules() if str(rule) == "/admin/test-ai"),
        None,
    )
    assert rule is not None
    assert rule.endpoint == "admin.test_ai"
    assert "GET" in rule.methods


def test_csrf_endpoint_returns_json_for_authenticated_user(app, client):
    fake_user = type(
        "FakeUser",
        (),
        {
            "id": 9001,
            "is_authenticated": True,
            "is_active": True,
            "is_anonymous": False,
            "get_id": lambda self: "9001",
        },
    )()
    with patch("models.user.User.get", return_value=fake_user):
        _login_session(client)
        response = client.get("/api/csrf-token")

    assert response.status_code == 200
    assert response.is_json
    payload = response.get_json()
    assert isinstance(payload.get("csrf_token"), str)
    assert payload["csrf_token"]


def test_csrf_endpoint_rejects_anonymous_user(client):
    response = client.get("/api/csrf-token")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_required_route_map_is_exactly_present(app):
    expected = {
        "auth.login": "/auth/login",
        "admin.dashboard": "/admin/dashboard",
        "admin.test_ai": "/admin/test-ai",
        "home.select_client": "/select-client/<int:cliente_id>",
        "cliente.selecionar_cliente": "/cliente/selecionar-cliente",
        "nfe.create": "/admin/nfe/create",
        "nfe.emitir_nfe": "/admin/nfe/emitir",
        "nfe.api_proximo_numero": "/admin/nfe/api/proximo-numero",
        "nfe.emitir_rascunho": "/admin/nfe/emitir-rascunho/<int:nfe_id>",
        "nfe.download_danfe_pdf": "/admin/nfe/danfe/<int:nfe_id>/pdf",
        "nfce.listar_nfce": "/admin/nfce/list",
        "nfce.emitir_nfce": "/admin/nfce/emitir",
        "admin.estoque_dashboard": "/admin/estoque",
        "admin.fluxo_caixa_dashboard": "/admin/fluxo-caixa",
        "admin.analise_vendas": "/admin/analise-vendas",
        "admin.inteligencia_emitemax": "/admin/inteligencia",
    }
    actual = {rule.endpoint: str(rule) for rule in app.url_map.iter_rules()}
    assert {key: actual.get(key) for key in expected} == expected


def test_critical_javascript_has_valid_syntax():
    node_script = PROJECT_ROOT / "tests" / "check_critical_js_syntax.js"
    result = subprocess.run(
        ["node", str(node_script)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_emission_template_has_real_submit_contract():
    content = Path("templates/admin/nfes/emitir.html").read_text(encoding="utf-8")
    button = re.search(r"id=\"btnEmitir\"(?P<body>.*?)</button>", content, re.S)
    assert button is not None
    body = button.group("body")
    assert "name=\"action\"" in body or "name='action'" in body
    assert "a.value='emitir'" in body or 'a.value="emitir"' in body
    assert "HTMLFormElement.prototype.submit.call" in body
    assert "/api/csrf-token" in body


def test_emission_frontend_requires_explicit_json_success_true():
    content = Path("templates/admin/nfes/emitir.html").read_text(encoding="utf-8")
    assert "JSON.parse(html)" in content
    assert "parsed && parsed.success" in content
    assert "response.includes('success')" not in content
    assert 'response.includes("success")' not in content


def _emission_view_dependencies():
    from database.models import Cliente, DestinatarioNFe

    cliente = type("ClienteFake", (), {
        "cliente_id": 1,
        "razao_social": "Empresa Teste",
        "nome_fantasia": "Empresa Teste",
        "cnpj": "11444777000161",
        "logradouro": "Rua Teste",
        "numero": "1",
        "bairro": "Centro",
        "cep": "01001000",
        "codigo_municipio": "3550308",
        "nome_municipio": "Sao Paulo",
        "uf": "SP",
        "inscricao_estadual": "110042490114",
        "regime_tributario_id": None,
        "ambiente": 2,
        "telefone_contato": None,
    })()
    destinatario = type("DestinatarioFake", (), {
        "destinatario_id": 10,
        "cliente_id": 1,
        "nome_razao_social": "Destinatario Teste",
        "cpf_cnpj": "52998224725",
        "ie": "",
        "logradouro": "Rua Destino",
        "numero": "2",
        "bairro": "Centro",
        "cep": "01001001",
        "codigo_municipio": "3550308",
        "nome_municipio": "Sao Paulo",
        "uf": "SP",
    })()

    class Query:
        def __init__(self, model):
            self.model = model

        def filter_by(self, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            if self.model is Cliente:
                return cliente
            if self.model is DestinatarioNFe:
                return destinatario
            return None

        def all(self):
            return []

    db = MagicMock()
    db.query.side_effect = lambda model, *args: Query(model)
    db.execute.return_value.fetchone.return_value = None
    return db, cliente, destinatario


def _undecorated_emission_view(app):
    view = app.view_functions["nfe.emitir_nfe"]
    while hasattr(view, "__wrapped__"):
        view = view.__wrapped__
    return view


def test_action_emitir_enters_real_emission_branch_without_external_call(app):
    from models.user import User

    db, _, _ = _emission_view_dependencies()
    user = User(9001, "editor", "editor@example.com", True,
                roles=[{"name": "Editor"}], clients=[{"cliente_id": 1}])
    sefaz_result = {"success": False, "status": "REJEITADA", "message": "mock rejeicao"}
    form = {
        "action": "emitir",
        "destinatario": "10",
        "natOp": "Venda",
        "numero_nfe": "1",
        "serie": "1",
        "items[0][json]": '{"descricao":"Produto","valor_total":10,"cfop":"5102","quantidade":1}',
    }

    with app.test_request_context("/admin/nfe/emitir?cliente_id=1", method="POST", data=form):
        with patch("routes.nfe_routes.current_user", user), \
             patch("routes.nfe_routes.get_db", return_value=iter([db])), \
             patch("routes.nfe_routes.get_accessible_client_ids", return_value=[1]), \
             patch("routes.nfe_routes.validar_dados_nfe", return_value=[]), \
             patch("routes.nfe_routes.validar_tributacao_nfe", return_value=(True, [])), \
             patch("routes.nfe_routes.generate_nfe_xml", return_value="<NFe />"), \
             patch("routes.nfe_routes.validar_xml_nfe", return_value=(True, [])), \
             patch("routes.nfe_routes.get_active_certificate_for_client", return_value={"common_name": "mock"}), \
             patch("services.xml_signature_service.xml_signature_service.sign_nfe_xml", return_value="<NFe signed />"), \
             patch("routes.nfe_routes.NFeService") as mock_service, \
             patch("requests.post", side_effect=RuntimeError("IA offline")):
            mock_service.return_value._processar_envio_sefaz.return_value = sefaz_result
            response = _undecorated_emission_view(app)()

    assert response.status_code == 302
    mock_service.return_value._processar_envio_sefaz.assert_called_once()


def test_post_without_action_does_not_enter_emission_service(app):
    from models.user import User

    db, _, _ = _emission_view_dependencies()
    user = User(9001, "editor", "editor@example.com", True,
                roles=[{"name": "Editor"}], clients=[{"cliente_id": 1}])
    form = {
        "destinatario": "10",
        "natOp": "Venda",
        "items[0][json]": '{"descricao":"Produto","valor_total":10,"cfop":"5102","quantidade":1}',
    }

    with app.test_request_context("/admin/nfe/emitir?cliente_id=1", method="POST", data=form):
        with patch("routes.nfe_routes.current_user", user), \
             patch("routes.nfe_routes.get_db", return_value=iter([db])), \
             patch("routes.nfe_routes.get_accessible_client_ids", return_value=[1]), \
             patch("routes.nfe_routes.NFeService") as mock_service:
            response = _undecorated_emission_view(app)()

    assert response is not None
    mock_service.assert_not_called()


def test_nfce_smoke_routes_have_real_endpoints_and_permissions(app):
    expected = {
        "nfce.listar_nfce": "/admin/nfce/list",
        "nfce.emitir_nfce": "/admin/nfce/emitir",
    }
    actual = {rule.endpoint: str(rule) for rule in app.url_map.iter_rules()}
    assert {endpoint: actual.get(endpoint) for endpoint in expected} == expected
    nfce_source = Path("routes/nfce_routes.py").read_text(encoding="utf-8")
    assert "@permission_required('nfe.issue')" in nfce_source


def test_no_permissive_patterns_in_critical_tests():
    content = Path("tests/test_nfe_critical_regression.py").read_text(encoding="utf-8")
    assert re.search(r"\bor\s+True\b", content) is None
    assert not re.search(r"^\s*pass\s*(#.*)?$", content, re.M)
    assert re.search(r"status_code\s+in\s*\[[^\]]*404", content) is None

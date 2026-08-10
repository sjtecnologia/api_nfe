"""Testes da superfície administrativa de IA.

Cobrem a página de teste e os endpoints JSON sem depender de banco real.
"""
from unittest.mock import MagicMock, patch


def _mock_admin_user():
    user = MagicMock()
    user.id = 1
    user.is_authenticated = True
    user.is_active = True
    user.is_anonymous = False
    user.is_super_admin.return_value = True
    return user


def _mock_role(name: str):
    role = MagicMock()
    role.name = name
    return role


class TestAdminAiRoutes:
    def test_test_ai_page_renders(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("auth.decorators.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.execute.return_value.fetchall.return_value = [_mock_role("Admin")]
            mock_get_db.return_value = iter([mock_db])

            response = client.get("/admin/test-ai")

        assert response.status_code == 200
        assert b"Teste de IA" in response.data
        assert b"Prompts" in response.data

    def test_ai_status_endpoint_returns_configuration(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.get("/admin/api/ia/status")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert "provider_model" in payload["data"]
        assert "prompt_count" in payload["data"]
        assert "feedback_count" in payload["data"]

    def test_ai_status_endpoint_reports_feedback_metrics(self, client):
        mock_user = _mock_admin_user()
        mock_feedback_query = MagicMock()
        mock_positive_query = MagicMock()
        mock_negative_query = MagicMock()
        mock_feedback_query.count.return_value = 12
        mock_positive_query.count.return_value = 9
        mock_negative_query.count.return_value = 3
        mock_feedback_query.filter.side_effect = [mock_positive_query, mock_negative_query]

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.AiFeedback") as mock_ai_feedback, \
             patch("routes.admin_api_routes.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value = mock_feedback_query
            mock_get_db.return_value = iter([mock_db])
            response = client.get("/admin/api/ia/status")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["data"]["feedback_count"] == 12
        assert payload["data"]["feedback_positive_count"] == 9
        assert payload["data"]["feedback_negative_count"] == 3
        assert payload["data"]["feedback_positive_rate"] == 75.0

    def test_ai_prompts_endpoint_lists_prompts(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.get("/admin/api/ia/prompts")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert isinstance(payload["data"], list)
        assert any(prompt["nome"] == "assistant_business" for prompt in payload["data"])

    def test_ai_prompt_preview_renders_prompt(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/admin/api/ia/prompts/assistant_business/preview",
                json={"variables": {"empresa": "EmiteMax"}},
            )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert "EmiteMax IA" in payload["data"]["rendered_prompt"]

    def test_ai_prompt_preview_unknown_prompt_returns_404(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post("/admin/api/ia/prompts/inexistente/preview", json={"variables": {}})

        assert response.status_code == 404
        payload = response.get_json()
        assert payload["success"] is False

    def test_ai_classificar_produto_returns_result(self, client):
        mock_user = _mock_admin_user()
        mock_service = MagicMock()
        mock_service.classify.return_value = {
            "sucesso": True,
            "classificacao": {"ncm": "94013000", "cfop": "5102"},
            "ids": {"ncm_id": 10, "cfop_id": 20},
        }

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.get_db") as mock_get_db, \
             patch("routes.admin_api_routes.ProductClassificationService", return_value=mock_service):
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            response = client.post(
                "/admin/api/ia/classificar-produto",
                json={
                    "descricao": "Cadeira ergonômica",
                    "cliente_id": 1,
                    "tipo_item": "Produto",
                    "unidade_comercial": "UN",
                    "codigo_interno": "CAD-001",
                },
            )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["data"]["sucesso"] is True
        mock_service.classify.assert_called_once()

    def test_ai_classificar_produto_requires_description(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post("/admin/api/ia/classificar-produto", json={"descricao": "   "})

        assert response.status_code == 400
        payload = response.get_json()
        assert payload["success"] is False

    def test_ai_logs_endpoint_lists_recent_usage(self, client):
        mock_user = _mock_admin_user()
        mock_log = MagicMock()
        mock_log.to_dict.return_value = {
            "usage_id": 1,
            "funcionalidade": "classificacao_produto",
            "model": "gpt-4o-mini",
            "status": "SUCCESS",
            "total_tokens": 123,
            "cost_estimated": 0.0042,
        }

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_log]

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = iter([mock_db])
            response = client.get("/admin/api/ia/logs?limit=10")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert len(payload["data"]) == 1
        assert payload["data"][0]["funcionalidade"] == "classificacao_produto"

    def test_ai_feedbacks_endpoint_lists_recent_feedback(self, client):
        mock_user = _mock_admin_user()
        mock_feedback = MagicMock()
        mock_feedback.to_dict.return_value = {
            "feedback_id": 7,
            "funcionalidade": "classificacao_produto",
            "feedback": "POSITIVO",
            "cliente_id": 1,
            "comentario": "Boa resposta",
        }

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_feedback]

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value = mock_query
            mock_get_db.return_value = iter([mock_db])
            response = client.get("/admin/api/ia/feedbacks?limit=10")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert len(payload["data"]) == 1
        assert payload["data"][0]["feedback"] == "POSITIVO"

    def test_ai_feedback_endpoint_registers_feedback(self, client):
        mock_user = _mock_admin_user()
        mock_service = MagicMock()
        mock_service.register_feedback.return_value = {
            "feedback_id": 99,
            "cliente_id": 1,
            "funcionalidade": "classificacao_produto",
            "feedback": "POSITIVO",
        }

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.AIService", return_value=mock_service):
            response = client.post(
                "/admin/api/ia/feedback",
                json={
                    "cliente_id": 1,
                    "funcionalidade": "classificacao_produto",
                    "feedback": "POSITIVO",
                    "comentario": "Boa resposta",
                },
            )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["data"]["feedback_id"] == 99
        mock_service.register_feedback.assert_called_once()

    def test_ai_feedback_endpoint_requires_cliente_id(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/admin/api/ia/feedback",
                json={
                    "funcionalidade": "classificacao_produto",
                    "feedback": "POSITIVO",
                },
            )

        assert response.status_code == 400
        payload = response.get_json()
        assert payload["success"] is False

    def test_ai_health_endpoint_reports_checks(self, client):
        mock_user = _mock_admin_user()

        ok_response = MagicMock()
        ok_response.status_code = 200

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.requests.post", return_value=ok_response):
            response = client.get("/admin/api/ia/health")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["data"]["operational"] is True
        assert len(payload["data"]["checks"]) == 2
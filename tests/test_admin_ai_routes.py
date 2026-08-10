"""Testes da superfície administrativa de IA.

Cobrem a página de teste e os endpoints JSON sem depender de banco real.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from routes import admin_api_routes


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

    def test_ai_analytics_endpoint_aggregates_metrics(self, client):
        mock_user = _mock_admin_user()
        now = datetime.now()

        logs = [
            SimpleNamespace(
                created_at=now - timedelta(days=1),
                funcionalidade='classificacao_produto',
                status='SUCCESS',
                total_tokens=120,
                cost_estimated=0.0123,
                response_time_ms=400,
            ),
            SimpleNamespace(
                created_at=now,
                funcionalidade='classificacao_produto',
                status='ERROR',
                total_tokens=30,
                cost_estimated=0.0010,
                response_time_ms=250,
            ),
            SimpleNamespace(
                created_at=now,
                funcionalidade='assistente_business',
                status='SUCCESS',
                total_tokens=200,
                cost_estimated=0.0200,
                response_time_ms=800,
            ),
        ]

        feedbacks = [
            SimpleNamespace(created_at=now, feedback='POSITIVO'),
            SimpleNamespace(created_at=now, feedback='NEGATIVO'),
            SimpleNamespace(created_at=now - timedelta(days=1), feedback='POSITIVO'),
        ]

        class _MockQuery:
            def __init__(self, rows):
                self._rows = rows

            def filter(self, *_args, **_kwargs):
                return self

            def all(self):
                return self._rows

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.get_db") as mock_get_db:
            mock_db = MagicMock()

            def _query_side_effect(model):
                if model is admin_api_routes.AiUsageLog:
                    return _MockQuery(logs)
                if model is admin_api_routes.AiFeedback:
                    return _MockQuery(feedbacks)
                raise AssertionError(f'Modelo inesperado: {model}')

            mock_db.query.side_effect = _query_side_effect
            mock_get_db.return_value = iter([mock_db])

            response = client.get('/admin/api/ia/analytics?days=14')

        assert response.status_code == 200
        payload = response.get_json()
        assert payload['success'] is True
        summary = payload['data']['summary']
        assert summary['total_requests'] == 3
        assert summary['success_requests'] == 2
        assert summary['error_requests'] == 1
        assert summary['feedback_total'] == 3
        assert summary['feedback_positive'] == 2
        assert len(payload['data']['by_functionality']) == 2
        assert len(payload['data']['daily_history']) == 14

    def test_ai_analytics_endpoint_handles_empty_data(self, client):
        mock_user = _mock_admin_user()

        class _MockQuery:
            def filter(self, *_args, **_kwargs):
                return self

            def all(self):
                return []

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.return_value = _MockQuery()
            mock_get_db.return_value = iter([mock_db])

            response = client.get('/admin/api/ia/analytics?days=7')

        assert response.status_code == 200
        payload = response.get_json()
        assert payload['success'] is True
        assert payload['data']['summary']['total_requests'] == 0
        assert payload['data']['summary']['confidence_score'] == 0
        assert len(payload['data']['daily_history']) == 7
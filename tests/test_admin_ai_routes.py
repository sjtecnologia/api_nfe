"""Testes da superfície administrativa de IA.

Cobrem a página de teste e os endpoints JSON sem depender de banco real.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from routes import admin_api_routes
from services.ai_providers import AIProviderError


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

    def test_ai_assistente_fiscal_perguntar_returns_answer(self, client):
        mock_user = _mock_admin_user()
        mock_service = MagicMock()
        mock_service.start_conversation.return_value = {"conversation_id": 123}
        mock_service.append_message.side_effect = [
            {"message_id": 1, "role": "user"},
            {"message_id": 2, "role": "assistant"},
        ]
        mock_service.chat.return_value = {
            "content": "Use CFOP 6108 quando aplicável ao cenário informado.",
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 120, "cost_estimated": 0.0012},
        }

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.AIService", return_value=mock_service):
            response = client.post(
                "/admin/api/ia/assistente-fiscal/perguntar",
                json={
                    "cliente_id": 1,
                    "pergunta": "Qual CFOP usar para venda interestadual?",
                },
            )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["data"]["conversation_id"] == 123
        assert "Valide com seu contador" in payload["data"]["answer"]
        mock_service.start_conversation.assert_called_once()
        assert mock_service.append_message.call_count == 2
        mock_service.chat.assert_called_once()

    def test_ai_assistente_fiscal_perguntar_requires_fields(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/admin/api/ia/assistente-fiscal/perguntar",
                json={"cliente_id": 1, "pergunta": "   "},
            )

        assert response.status_code == 400
        payload = response.get_json()
        assert payload["success"] is False

    def test_ai_assistente_fiscal_perguntar_provider_unavailable(self, client):
        mock_user = _mock_admin_user()
        mock_service = MagicMock()
        mock_service.start_conversation.return_value = {"conversation_id": 777}
        mock_service.append_message.return_value = {"message_id": 1, "role": "user"}
        mock_service.chat.side_effect = AIProviderError("Nenhum provedor de IA configurado")

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.AIService", return_value=mock_service):
            response = client.post(
                "/admin/api/ia/assistente-fiscal/perguntar",
                json={
                    "cliente_id": 1,
                    "pergunta": "Quando usar CST 060?",
                },
            )

        assert response.status_code == 503
        payload = response.get_json()
        assert payload["success"] is False
        assert "Provedor de IA indisponível" in payload["error"]

    def test_ai_assistente_fiscal_conversas_lists_data(self, client):
        mock_user = _mock_admin_user()

        conversation = MagicMock()
        conversation.conversation_id = 555
        conversation.to_dict.return_value = {
            "conversation_id": 555,
            "cliente_id": 1,
            "titulo": "Pergunta fiscal",
            "updated_at": "2026-08-10T15:00:00",
        }

        message = MagicMock()
        message.role = "assistant"
        message.content = "Resposta curta"
        message.created_at = "2026-08-10T15:00:01"

        conv_query = MagicMock()
        conv_query.filter.return_value = conv_query
        conv_query.order_by.return_value = conv_query
        conv_query.limit.return_value = conv_query
        conv_query.all.return_value = [conversation]

        msg_query = MagicMock()
        msg_query.filter.return_value = msg_query
        msg_query.order_by.return_value = msg_query
        msg_query.first.return_value = message

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.query.side_effect = [conv_query, msg_query]
            mock_get_db.return_value = iter([mock_db])

            response = client.get("/admin/api/ia/assistente-fiscal/conversas?limit=10")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert len(payload["data"]) == 1
        assert payload["data"][0]["conversation_id"] == 555

    def test_ai_consultor_vendas_insights_returns_metrics(self, client):
        mock_user = _mock_admin_user()

        fake_data = {
            'metricas': {
                'cliente_id': 1,
                'days': 30,
                'total_notas': 12,
                'faturamento': 3200.0,
                'ticket_medio': 266.67,
                'taxa_autorizacao': 85.7,
            },
            'insights': ['Insight 1', 'Insight 2'],
            'top_produtos': [
                {'descricao': 'Produto A', 'total_ocorrencias': 7, 'valor_total': 1400.0},
                {'descricao': 'Produto B', 'total_ocorrencias': 3, 'valor_total': 700.0},
            ],
            'top_destinatarios': [
                {'destinatario': 'Cliente XPTO', 'total_notas': 4, 'faturamento': 1100.0},
            ],
            'narrativa_ia': {'enabled': True, 'source': 'ia', 'text': 'Resumo IA'},
        }

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.gerar_resumo_consultor_vendas", return_value=fake_data) as resumo_mock:
            response = client.get('/admin/api/ia/consultor-vendas/insights?cliente_id=1&days=30&include_ai=1')

        assert response.status_code == 200
        payload = response.get_json()
        assert payload['success'] is True
        assert payload['data']['metricas']['cliente_id'] == 1
        assert payload['data']['metricas']['total_notas'] == 12
        assert len(payload['data']['insights']) >= 1
        assert len(payload['data']['top_produtos']) == 2
        assert payload['data']['narrativa_ia']['source'] == 'ia'
        resumo_mock.assert_called_once()

    def test_ai_consultor_vendas_insights_requires_cliente_id(self, client):
        mock_user = _mock_admin_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.get('/admin/api/ia/consultor-vendas/insights?days=30')

        assert response.status_code == 400
        payload = response.get_json()
        assert payload['success'] is False

    def test_ai_health_endpoint_reports_checks(self, client):
        mock_user = _mock_admin_user()

        ok_response = MagicMock()
        ok_response.status_code = 200

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("routes.admin_api_routes.requests.get", return_value=ok_response), \
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
        assert payload['data']['applied_filters']['cliente_id'] is None
        assert payload['data']['applied_filters']['funcionalidade'] is None
        assert payload['data']['top_errors'][0]['count'] == 1

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
        assert payload['data']['top_errors'] == []

    def test_ai_analytics_endpoint_applies_filters(self, client):
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

            response = client.get('/admin/api/ia/analytics?days=30&cliente_id=27&funcionalidade=classificacao_produto')

        assert response.status_code == 200
        payload = response.get_json()
        assert payload['success'] is True
        assert payload['data']['period_days'] == 30
        assert payload['data']['applied_filters']['cliente_id'] == 27
        assert payload['data']['applied_filters']['funcionalidade'] == 'classificacao_produto'

    def test_ai_analytics_endpoint_rejects_invalid_cliente_id(self, client):
        mock_user = _mock_admin_user()

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.get('/admin/api/ia/analytics?cliente_id=abc')

        assert response.status_code == 400
        payload = response.get_json()
        assert payload['success'] is False
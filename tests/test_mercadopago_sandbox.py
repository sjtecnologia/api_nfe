from unittest.mock import Mock, patch

import pytest

from payments.mercadopago_sandbox import MercadoPagoSandboxClient
from scripts.map_mercadopago_test_plans import classify_candidates
from decimal import Decimal


def client(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_ENVIRONMENT", "TEST")
    monkeypatch.setenv("MERCADOPAGO_TEST_ACCESS_TOKEN", "test-secret-token")
    return MercadoPagoSandboxClient()


def test_http_400_json_diagnostic_and_original_error(monkeypatch, capsys):
    response = Mock(ok=False, status_code=400, headers={"x-request-id": "req-123"})
    response.json.return_value = {"message": "invalid payload", "access_token": "must-not-log"}
    response.raise_for_status.side_effect = RuntimeError("HTTP 400")
    with patch("payments.mercadopago_sandbox.requests.post", return_value=response):
        with pytest.raises(RuntimeError, match="HTTP 400"):
            client(monkeypatch).create_preapproval_plan(reason="Start", amount="60.00")
    output = capsys.readouterr().out
    assert "MERCADOPAGO_TEST_HTTP_STATUS=400" in output
    assert '"message":"invalid payload"' in output
    assert "req-123" in output
    assert "test-secret-token" not in output
    assert "must-not-log" not in output
    response.raise_for_status.assert_called_once()


def test_http_400_non_json_is_limited(monkeypatch, capsys):
    response = Mock(ok=False, status_code=400, headers={})
    response.json.side_effect = ValueError("not json")
    response.text = "x" * 2000
    response.raise_for_status.side_effect = RuntimeError("HTTP 400")
    with patch("payments.mercadopago_sandbox.requests.post", return_value=response):
        with pytest.raises(RuntimeError):
            client(monkeypatch).create_preapproval_plan(reason="Start", amount="60.00")
    output = capsys.readouterr().out
    error_line = next(line for line in output.splitlines() if line.startswith("MERCADOPAGO_TEST_ERROR="))
    assert len(error_line.split("=", 1)[1]) == 1000


def test_http_200_with_id_returns_payload(monkeypatch):
    response = Mock(ok=True, status_code=201)
    response.json.return_value = {"id": "TEST_START_1", "status": "active"}
    with patch("payments.mercadopago_sandbox.requests.post", return_value=response):
        result = client(monkeypatch).create_preapproval_plan(reason="Start", amount="60.00")
    assert result["id"] == "TEST_START_1"
    response.raise_for_status.assert_called_once()


def test_http_200_without_id_fails(monkeypatch):
    response = Mock(ok=True, status_code=200)
    response.json.return_value = {"status": "active"}
    with patch("payments.mercadopago_sandbox.requests.post", return_value=response):
        with pytest.raises(RuntimeError, match="MERCADOPAGO_TEST_PLAN_ID_MISSING"):
            client(monkeypatch).create_preapproval_plan(reason="Start", amount="60.00")


def test_search_preapproval_plans_paginates_and_sanitizes(monkeypatch):
    first = Mock(ok=True, status_code=200, headers={})
    first.json.return_value = {"paging": {"total": 2}, "results": [{"id": "a", "reason": "Old", "application_id": "app", "auto_recurring": {"transaction_amount": 60, "currency_id": "BRL"}, "access_token": "secret"}]}
    second = Mock(ok=True, status_code=200, headers={})
    second.json.return_value = {"paging": {"total": 2}, "results": [{"id": "b", "reason": "Old 2", "application_id": "app", "auto_recurring": {"transaction_amount": 70, "currency_id": "BRL"}}]}
    with patch("payments.mercadopago_sandbox.requests.get", side_effect=[first, second]) as request:
        plans = client(monkeypatch).search_preapproval_plans(limit=1)
    assert [plan["id"] for plan in plans] == ["a", "b"]
    assert "access_token" not in plans[0]
    assert request.call_count == 2


def test_candidate_classification_requires_exact_identity():
    exact = {"reason": "EmiteMax Start V1", "transaction_amount": 60, "currency_id": "BRL", "frequency": 1, "frequency_type": "months", "status": "active", "application_id": "app"}
    assert classify_candidates("EmiteMax Start V1", Decimal("60.00"), [exact], "app")[0] == "EXACT_TEST_CANDIDATE"
    collision = {**exact, "reason": "Pacote Básico"}
    assert classify_candidates("EmiteMax Start V1", Decimal("60.00"), [collision], "app")[0] == "PRICE_ONLY_COLLISION"

import hashlib
import hmac
import os
from unittest.mock import MagicMock

import pytest

from payments.mercadopago_provider import (
    MercadoPagoTestPaymentProvider,
    ShadowPaymentProvider,
    build_payment_provider,
)


def test_test_environment_selects_real_provider(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_ENVIRONMENT", "TEST")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres@localhost:5432/e2e_emitemax_commercial")
    monkeypatch.setenv("MERCADOPAGO_TEST_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("MERCADOPAGO_TEST_BACK_URL", "https://example.com/mercadopago/return")
    monkeypatch.setenv("MERCADOPAGO_TEST_WEBHOOK_URL", "https://example.com/api/public/commercial/webhooks/mercadopago")

    provider = build_payment_provider()

    assert isinstance(provider, MercadoPagoTestPaymentProvider)


def test_explicit_provider_injection_keeps_shadow_compatibility(monkeypatch):
    monkeypatch.delenv("MERCADOPAGO_ENVIRONMENT", raising=False)
    provider = ShadowPaymentProvider()

    assert build_payment_provider(provider=provider) is provider


def test_missing_test_token_fails_closed(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_ENVIRONMENT", "TEST")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres@localhost:5432/e2e_emitemax_commercial")
    monkeypatch.delenv("MERCADOPAGO_TEST_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("MERCADOPAGO_TEST_BACK_URL", "https://example.com/mercadopago/return")

    with pytest.raises(RuntimeError, match="MERCADOPAGO_TEST_ACCESS_TOKEN_REQUIRED"):
        build_payment_provider()


def test_non_test_database_is_rejected(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_ENVIRONMENT", "TEST")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres@sjtnfe:5432/sjtnfe")
    monkeypatch.setenv("MERCADOPAGO_TEST_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("MERCADOPAGO_TEST_BACK_URL", "https://example.com/mercadopago/return")

    with pytest.raises(RuntimeError, match="REFUSE_NON_TEST_DATABASE"):
        build_payment_provider()


def test_provider_returns_real_checkout_url_when_api_ok(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_ENVIRONMENT", "TEST")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres@localhost:5432/e2e_emitemax_commercial")
    monkeypatch.setenv("MERCADOPAGO_TEST_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("MERCADOPAGO_TEST_BACK_URL", "https://example.com/mercadopago/return")
    monkeypatch.setenv("MERCADOPAGO_TEST_WEBHOOK_URL", "https://example.com/api/public/commercial/webhooks/mercadopago")

    provider = MercadoPagoTestPaymentProvider()
    provider.client = MagicMock()
    provider.client.create_preapproval_payment.return_value = {
        "id": "mp-sub-123",
        "status": "authorized",
        "init_point": "https://sandbox.mercadopago.com/checkout/real/123",
    }

    result = provider.create_checkout(
        amount="60.00",
        currency="BRL",
        idempotency_key="checkout-123",
        reference="EMITEMAX:10:START_V1:99",
        provider_plan_id="abc123",
        payer_email="synthetic@example.test",
        card_token_id="card-token-test-123",
    )

    assert result["provider"] == "mercadopago"
    assert result["status"] == "AUTHORIZED"
    assert result["checkout_url"] == "https://sandbox.mercadopago.com/checkout/real/123"
    assert result["provider_subscription_id"] == "mp-sub-123"

    payload = provider.client.create_preapproval_payment.call_args.args[0]
    assert payload["preapproval_plan_id"] == "abc123"
    assert payload["payer_email"] == "synthetic@example.test"
    assert payload["card_token_id"] == "card-token-test-123"
    assert payload["status"] == "authorized"
    assert payload["notification_url"] == "https://example.com/api/public/commercial/webhooks/mercadopago"
    assert "card-token-test-123" not in result["external_reference"]


def test_card_token_is_required_without_network_call(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_TEST_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("MERCADOPAGO_TEST_BACK_URL", "https://example.com/mercadopago/return")
    provider = MercadoPagoTestPaymentProvider()
    provider.client = MagicMock()

    with pytest.raises(ValueError, match="CARD_TOKEN_REQUIRED"):
        provider.create_checkout(
            amount="60.00", currency="BRL", idempotency_key="checkout-missing-token",
            reference="EMITEMAX:10:START_V1:99", provider_plan_id="abc123",
            payer_email="synthetic@example.test", card_token_id="",
        )
    provider.client.create_preapproval_payment.assert_not_called()


def test_webhook_signature_uses_mercado_pago_manifest(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_TEST_WEBHOOK_SECRET", "webhook-secret")
    provider = MercadoPagoTestPaymentProvider(access_token="test-token", back_url="https://example.com/return")
    manifest = "id:sub123;request-id:req-123;ts:1742505638683;"
    signature = "ts=1742505638683,v1=" + hmac.new(
        b"webhook-secret", manifest.encode(), hashlib.sha256
    ).hexdigest()

    assert provider.verify_webhook(
        raw_body=b'{}', signature=signature, request_id="req-123", data_id="SUB123"
    ) is True
    assert provider.verify_webhook(
        raw_body=b'{}', signature="ts=1742505638683,v1=invalid", request_id="req-123", data_id="SUB123"
    ) is False


def test_webhook_loads_subscription_from_seller_account(monkeypatch):
    provider = MercadoPagoTestPaymentProvider(access_token="test-token", back_url="https://example.com/return")
    provider.client = MagicMock()
    provider.client.get_preapproval_payment.return_value = {
        "external_reference": "EMITEMAX:10:START_V1:99",
        "status": "authorized",
        "preapproval_plan_id": "plan-123",
        "auto_recurring": {"transaction_amount": 60, "currency_id": "BRL"},
    }

    event = provider.parse_webhook(
        {"id": "delivery-123", "type": "subscription_preapproval", "action": "preapproval.updated"},
        data_id="subscription-123",
    )

    provider.client.get_preapproval_payment.assert_called_once_with("subscription-123")
    assert event == {
        "provider_event_id": "delivery-123",
        "event_type": "subscription_preapproval",
        "status": "APPROVED",
        "checkout_attempt_id": 99,
        "plan_code": "START_V1",
        "provider_plan_id": "plan-123",
        "environment": "TEST",
        "amount": 60,
        "currency": "BRL",
    }


def test_minimal_preapproval_keeps_notification_url(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_TEST_MINIMAL_PREAPPROVAL", "true")
    provider = MercadoPagoTestPaymentProvider(
        access_token="test-token",
        back_url="https://example.com/return",
        webhook_url="https://example.com/api/public/commercial/webhooks/mercadopago",
    )
    provider.client = MagicMock()
    provider.client.create_preapproval_payment.return_value = {"id": "subscription-123"}

    provider.create_checkout(
        amount="60.00", currency="BRL", idempotency_key="checkout-123",
        reference="EMITEMAX:10:START_V1:99", provider_plan_id="plan-123",
        payer_email="buyer@example.test", card_token_id="card-token-test-123",
    )

    payload = provider.client.create_preapproval_payment.call_args.args[0]
    assert payload["notification_url"] == "https://example.com/api/public/commercial/webhooks/mercadopago"

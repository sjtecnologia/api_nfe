import hashlib
import hmac
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from payments.mercadopago_provider import ShadowPaymentProvider
from services.commercial_checkout import CommercialCheckoutService
from database.billing_shadow_models import BillingCheckoutAttempt, PendingSignup


def test_shadow_provider_never_calls_network_and_is_deterministic():
    provider = ShadowPaymentProvider()
    first = provider.create_checkout(amount="60.00", currency="BRL", idempotency_key="signup-1", reference="token")
    second = provider.create_checkout(amount="60.00", currency="BRL", idempotency_key="signup-1", reference="token")
    assert first == second
    assert first["status"] == "PENDING"
    assert first["redirect_url"].startswith("/mock/")


def test_invalid_webhook_signature_is_rejected():
    provider = ShadowPaymentProvider()
    assert provider.verify_webhook(raw_body=b"{}", signature="invalid") is False


def test_webhook_signature_uses_hmac_sha256(monkeypatch):
    monkeypatch.setenv("SHADOW_WEBHOOK_SECRET", "test-secret")
    body = b'{"id":"evt-1"}'
    signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert ShadowPaymentProvider().verify_webhook(raw_body=body, signature=signature) is True


def test_checkout_never_accepts_frontend_price():
    db = MagicMock()
    version = SimpleNamespace(plan_version_id=1, version_code="START_V1", price=Decimal("60.00"), currency="BRL")
    version_query = MagicMock()
    version_query.filter_by.return_value = version_query
    version_query.first.return_value = version
    existing_query = MagicMock()
    existing_query.filter_by.return_value = existing_query
    existing_query.first.return_value = None
    db.query.side_effect = [version_query, existing_query]
    entities = []
    def add(entity):
        entities.append(entity)
        if isinstance(entity, PendingSignup):
            entity.pending_signup_id = 1
        if isinstance(entity, BillingCheckoutAttempt):
            entity.checkout_attempt_id = 1
            entity.pending_signup = entities[0]
    db.add.side_effect = add
    db.flush.side_effect = lambda: None
    service = CommercialCheckoutService(db)
    result = service.create_checkout(
        plan_code="START_V1", email="buyer@example.test", company_name="Buyer",
        contract_version="2026-08", contract_accepted=True,
        idempotency_key="signup-price-test",
    )
    assert result["amount"] == "60.00"
    assert result["currency"] == "BRL"


def test_legacy_checkout_is_closed():
    db = MagicMock()
    version = SimpleNamespace(plan_version_id=1, version_code="LEGACY_60_V1", price=Decimal("60.00"), currency="BRL")
    db.query.return_value.filter_by.return_value.first.return_value = version
    with pytest.raises(ValueError, match="PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS"):
        CommercialCheckoutService(db).create_checkout(
            plan_code="LEGACY_60_V1", email="buyer@example.test", company_name="Buyer",
            contract_version="2026-08", contract_accepted=True, idempotency_key="legacy-test",
        )
    db.add.assert_not_called()

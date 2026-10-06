import hashlib
import hmac
import json
import os
import uuid
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from database.billing_shadow_models import (
    BillingAccount,
    BillingFeature,
    BillingPlan,
    BillingPlanFeature,
    BillingPlanVersion,
)
from database.models import Base


@pytest.fixture()
def public_api_context(app):
    from database.connection import SessionLocal

    admin_url = os.getenv("BILLING_SHADOW_DATABASE_URL", "postgresql://postgres@localhost:5432/postgres")
    parsed = urlsplit(admin_url)
    name = f"billing_public_api_{os.getpid()}_{uuid.uuid4().hex[:8]}"
    admin = create_engine(urlunsplit(parsed._replace(path="/postgres")), poolclass=NullPool)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"CREATE DATABASE {name}"))
    engine = create_engine(urlunsplit(parsed._replace(path=f"/{name}")), poolclass=NullPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    start = BillingPlan(code="START", name="Start", active=True, display_order=1)
    legacy = BillingPlan(code="LEGACY_60", name="Legacy", active=False, display_order=99)
    db.add_all([start, legacy])
    db.flush()
    db.add_all([
        BillingPlanVersion(plan_id=start.plan_id, version_code="START_V1", price=Decimal("60.00"), currency="BRL", status="ACTIVE"),
        BillingPlanVersion(plan_id=legacy.plan_id, version_code="LEGACY_60_V1", price=Decimal("60.00"), currency="BRL", status="ACTIVE"),
    ])
    db.commit()
    db.close()

    original_bind = SessionLocal.kw.get("bind")
    SessionLocal.configure(bind=engine)
    original_testing = app.config.get("TESTING")
    app.config["TESTING"] = True
    os.environ["FEATURE_NEW_BILLING_CHECKOUT_ENABLED"] = "true"
    os.environ["PAYMENT_PROVIDER"] = "shadow"
    yield app, engine
    os.environ.pop("FEATURE_NEW_BILLING_CHECKOUT_ENABLED", None)
    os.environ.pop("PAYMENT_PROVIDER", None)
    SessionLocal.configure(bind=original_bind)
    app.config["TESTING"] = original_testing
    engine.dispose()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"), {"name": name})
        conn.execute(text(f"DROP DATABASE IF EXISTS {name}"))
    admin.dispose()


def test_public_catalog_hides_legacy_and_internal_metadata(public_api_context):
    app, _ = public_api_context
    response = app.test_client().get("/api/public/commercial/plans")
    assert response.status_code == 200
    payload = response.get_json()
    versions = {plan.get("code") for plan in payload["plans"]}
    assert "Start" in {plan["name"] for plan in payload["plans"]}
    assert "LEGACY_60_V1" not in versions
    assert "START_V1" in versions
    serialized = json.dumps(payload)
    assert "plan_id" not in serialized
    assert "override" not in serialized.lower()


def test_mercadopago_test_checkout_page_is_test_only(public_api_context, monkeypatch):
    app, _ = public_api_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mercadopago")
    monkeypatch.setenv("MERCADOPAGO_ENVIRONMENT", "TEST")
    monkeypatch.setenv("MERCADOPAGO_TEST_PUBLIC_KEY", "TEST-public-key")

    response = app.test_client().get("/api/public/commercial/checkout/test?plan_code=START_V1")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "sdk.mercadopago.com/js/v2" in body
    assert "TEST-public-key" in body
    assert "START_V1" in body
    assert "card_token_id" in body
    assert "transaction_amount" not in body
    assert "MERCADOPAGO_TEST_ACCESS_TOKEN" not in body


def test_mercadopago_test_checkout_page_requires_explicit_test_configuration(public_api_context, monkeypatch):
    app, _ = public_api_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "shadow")
    monkeypatch.delenv("MERCADOPAGO_TEST_PUBLIC_KEY", raising=False)

    response = app.test_client().get("/api/public/commercial/checkout/test")

    assert response.status_code == 503


def test_checkout_is_disabled_without_explicit_shadow_flag(public_api_context, monkeypatch):
    app, engine = public_api_context
    monkeypatch.setenv("FEATURE_NEW_BILLING_CHECKOUT_ENABLED", "false")
    response = app.test_client().post("/api/public/commercial/checkout", json={"plan_code": "START_V1", "contract_accepted": True, "signup": {"email": "disabled@example.test", "company_name": "Disabled"}}, headers={"Idempotency-Key": "disabled-checkout"})
    assert response.status_code == 503
    assert response.get_json()["code"] == "COMMERCIAL_CHECKOUT_DISABLED"
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM pending_signups")).scalar() == 0


def test_checkout_without_csrf_is_exempt_only_for_public_api(app, monkeypatch):
    from app import csrf
    from routes.commercial_public_routes import public_checkout

    original_csrf_enabled = app.config.get("WTF_CSRF_ENABLED")
    original_feature_flag = os.environ.get("FEATURE_NEW_BILLING_CHECKOUT_ENABLED")
    try:
        app.config["WTF_CSRF_ENABLED"] = True
        monkeypatch.setenv("FEATURE_NEW_BILLING_CHECKOUT_ENABLED", "false")
        response = app.test_client().post(
            "/api/public/commercial/checkout",
            json={"plan_code": "START_V1", "contract_accepted": True},
            headers={"Idempotency-Key": "csrf-regression-checkout"},
        )

        assert response.status_code == 503
        assert response.get_json()["code"] == "COMMERCIAL_CHECKOUT_DISABLED"
        assert "The CSRF token is missing" not in response.get_data(as_text=True)
        assert app.config["WTF_CSRF_ENABLED"] is True
        assert f"{public_checkout.__module__}.{public_checkout.__name__}" in csrf._exempt_views
        assert "fiscal" not in response.get_data(as_text=True).lower()
    finally:
        app.config["WTF_CSRF_ENABLED"] = original_csrf_enabled
        if original_feature_flag is None:
            os.environ.pop("FEATURE_NEW_BILLING_CHECKOUT_ENABLED", None)
        else:
            os.environ["FEATURE_NEW_BILLING_CHECKOUT_ENABLED"] = original_feature_flag


def test_checkout_resolves_backend_price_and_is_idempotent(public_api_context):
    app, engine = public_api_context
    client = app.test_client()
    headers = {"Idempotency-Key": "public-checkout-1"}
    payload = {"plan_code": "START_V1", "price": "1.00", "max_users": 99, "contract_accepted": True, "contract_version": "2026-08", "signup": {"email": "new@example.test", "company_name": "New Co"}}
    first = client.post("/api/public/commercial/checkout", json=payload, headers=headers)
    second = client.post("/api/public/commercial/checkout", json=payload, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.get_json() == second.get_json()
    assert first.get_json()["amount"] == "60.00"
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM pending_signups")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM billing_checkout_attempts")).scalar() == 1


def test_legacy_checkout_is_rejected_without_writes(public_api_context):
    app, engine = public_api_context
    response = app.test_client().post("/api/public/commercial/checkout", json={"plan_code": "LEGACY_60_V1", "contract_accepted": True, "signup": {"email": "legacy@example.test", "company_name": "Legacy Co"}}, headers={"Idempotency-Key": "legacy-checkout"})
    assert response.status_code == 400
    assert response.get_json()["code"] == "PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS"
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM pending_signups")).scalar() == 0


def test_webhook_signature_and_duplicate_processing(public_api_context, monkeypatch):
    app, engine = public_api_context
    monkeypatch.setenv("SHADOW_WEBHOOK_SECRET", "shadow-test")
    client = app.test_client()
    response = client.post("/api/public/commercial/checkout", json={"plan_code": "START_V1", "contract_accepted": True, "signup": {"email": "buyer@example.test", "company_name": "Buyer Co"}}, headers={"Idempotency-Key": "webhook-checkout"})
    assert response.status_code == 201
    with engine.connect() as conn:
        attempt_id = conn.execute(text("SELECT checkout_attempt_id FROM billing_checkout_attempts")).scalar()
    payload = {"id": "event-1", "type": "payment", "status": "approved", "checkout_attempt_id": attempt_id}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    invalid = client.post("/api/public/commercial/webhooks/mercadopago", data=raw, content_type="application/json", headers={"X-Shadow-Signature": "invalid"})
    assert invalid.status_code == 401
    signature = hmac.new(b"shadow-test", raw, hashlib.sha256).hexdigest()
    first = client.post("/api/public/commercial/webhooks/mercadopago", data=raw, content_type="application/json", headers={"X-Shadow-Signature": signature})
    second = client.post("/api/public/commercial/webhooks/mercadopago", data=raw, content_type="application/json", headers={"X-Shadow-Signature": signature})
    assert first.status_code == second.status_code == 200
    assert first.get_json()["status"] == "PROCESSED"
    assert second.get_json()["status"] == "ALREADY_PROCESSED"
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM billing_payment_events")).scalar() == 1
        assert conn.execute(text("SELECT status FROM pending_signups")).scalar() == "PROVISIONING"

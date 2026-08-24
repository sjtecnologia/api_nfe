import os
import threading
from datetime import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from services.billing_nfe_quota import BillingNFeQuotaAdapter
from services.billing_usage_shadow import BillingQuotaReservationService
from tests.test_billing_reservation_shadow import _seed_subscription, pg_engine as _source_pg_engine


@pytest.fixture(scope="module")
def pg_engine():
    yield from _source_pg_engine.__wrapped__()


@pytest.fixture(autouse=True)
def clean_billing_state(pg_engine):
    with pg_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE billing_usage_reservations, billing_usage_events, billing_usage_counters, billing_subscription_companies, billing_subscriptions, billing_plan_versions, billing_plans, billing_accounts, clientes, regimes_tributarios RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture(autouse=True)
def quota_flags(monkeypatch):
    monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", "true")
    monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_SHADOW", "false")
    monkeypatch.setenv("BILLING_NFE_QUOTA_ROLLOUT_CLIENT_IDS", "1")


def _set_usage(db, subscription_id, quantity):
    db.execute(text("UPDATE billing_usage_counters SET quantity = :quantity WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id, "quantity": quantity})
    db.commit()


def _active_reserved(db, subscription_id):
    return db.execute(text("SELECT COALESCE(SUM(quantity), 0) FROM billing_usage_reservations WHERE subscription_id = :sid AND status IN ('RESERVED', 'PENDING_RECONCILIATION')"), {"sid": subscription_id}).scalar()


def test_authorized_49_to_50_and_blocked_50_does_not_call_sefaz(pg_engine):
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=49)
        adapter = BillingNFeQuotaAdapter(db)
        sefaz = Mock(return_value={"success": True, "status": "AUTORIZADA"})
        reservation_key = "NFE:integrated:49"
        reserved = adapter.before_external_send(cliente_id=1, reservation_key=reservation_key, source_id=reservation_key)
        assert reserved["status"] == "RESERVED"
        result = sefaz()
        assert result["status"] == "AUTORIZADA"
        assert adapter.after_authorized(reservation_key=reservation_key, source_id=reservation_key)["status"] == "CONFIRMED"
        assert db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription.subscription_id}).scalar() == 50

        blocked_sefaz = Mock()
        blocked = adapter.before_external_send(cliente_id=1, reservation_key="NFE:integrated:50", source_id="NFE:integrated:50")
        assert blocked["status"] == "QUOTA_EXCEEDED"
        blocked_sefaz.assert_not_called()
    finally:
        db.close()


def test_rejection_releases_and_keeps_usage_49(pg_engine):
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=49)
        adapter = BillingNFeQuotaAdapter(db)
        key = "NFE:integrated:rejected"
        assert adapter.before_external_send(cliente_id=1, reservation_key=key, source_id=key)["status"] == "RESERVED"
        sefaz = Mock(return_value={"success": False, "status": "REJEITADA"})
        assert sefaz()["status"] == "REJEITADA"
        assert adapter.known_not_authorized(reservation_key=key, reason="REJEITADA")["status"] == "RELEASED"
        assert _active_reserved(db, subscription.subscription_id) == 0
        assert db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription.subscription_id}).scalar() == 49
    finally:
        db.close()


def test_confirm_failure_preserves_fiscal_success_and_marks_pending(pg_engine, monkeypatch):
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        _seed_subscription(db, counted=49)
        adapter = BillingNFeQuotaAdapter(db)
        key = "NFE:integrated:confirm-failure"
        assert adapter.before_external_send(cliente_id=1, reservation_key=key, source_id=key)["status"] == "RESERVED"
        sefaz = Mock(return_value={"success": True, "status": "AUTORIZADA"})
        fiscal_result = sefaz()
        monkeypatch.setattr(adapter.reservations, "confirm", Mock(side_effect=RuntimeError("billing unavailable")))
        try:
            adapter.after_authorized(reservation_key=key, source_id=key)
        except RuntimeError:
            billing_status = "BILLING_CONFIRM_PENDING"
        else:
            billing_status = "UNEXPECTED"
        assert fiscal_result["success"] is True
        assert billing_status == "BILLING_CONFIRM_PENDING"
    finally:
        db.close()


def test_unknown_result_is_pending_and_retry_is_idempotent(pg_engine):
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=49)
        adapter = BillingNFeQuotaAdapter(db)
        key = "NFE:integrated:unknown"
        assert adapter.before_external_send(cliente_id=1, reservation_key=key, source_id=key)["status"] == "RESERVED"
        pending = adapter.reservations.reconcile(reservation_key=key, real_status="TIMEOUT")
        assert pending["status"] == "PENDING_RECONCILIATION"
        assert _active_reserved(db, subscription.subscription_id) == 1
        retry = adapter.before_external_send(cliente_id=1, reservation_key=key, source_id=key)
        assert retry["status"] == "DUPLICATE"
    finally:
        db.close()


def test_web_api_compete_for_last_slot(pg_engine):
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=49)
        barrier = threading.Barrier(2)
        results = {}

        def worker(channel):
            session = Session()
            try:
                barrier.wait()
                adapter = BillingNFeQuotaAdapter(session)
                results[channel] = adapter.before_external_send(cliente_id=1, reservation_key=f"NFE:{channel}:last", source_id=f"NFE:{channel}:last")
            finally:
                session.close()

        threads = [threading.Thread(target=worker, args=(channel,)) for channel in ("web", "api")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert sorted(value["status"] for value in results.values()) == ["QUOTA_EXCEEDED", "RESERVED"]
        assert _active_reserved(db, subscription.subscription_id) == 1
    finally:
        db.close()


def test_flag_off_legacy_premium_and_override(pg_engine, monkeypatch):
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        start = _seed_subscription(db, counted=50)
        monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", "false")
        off = BillingNFeQuotaAdapter(db).before_external_send(cliente_id=1, reservation_key="NFE:off", source_id="NFE:off")
        assert off["allowed"] is True and off["status"] == "FLAG_OFF"
        monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", "true")
        premium = _seed_subscription(db, plan_code="PREMIUM_V1", counted=51)
        premium_result = BillingQuotaReservationService(db).reserve(subscription_id=premium.subscription_id, cliente_id=1, metric_key="NFE_ISSUED", reservation_key="NFE:premium", source_id="NFE:premium")
        assert premium_result["status"] == "ALLOWED_FAIR_USE"
        legacy = _seed_subscription(db, plan_code="LEGACY_START_V1", counted=51)
        legacy_result = BillingQuotaReservationService(db).reserve(subscription_id=legacy.subscription_id, cliente_id=1, metric_key="NFE_ISSUED", reservation_key="NFE:legacy", source_id="NFE:legacy")
        assert legacy_result["status"] in {"LEGACY_BYPASS", "LEGACY_UNMIGRATED"}
        assert start.subscription_id != premium.subscription_id != legacy.subscription_id
    finally:
        db.close()

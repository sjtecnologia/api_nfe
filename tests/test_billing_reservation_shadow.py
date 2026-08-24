import os
import threading
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database.billing_shadow_models import (
    BillingAccount,
    BillingPlan,
    BillingPlanVersion,
    BillingSubscription,
    BillingSubscriptionCompany,
    BillingSubscriptionOverride,
)
from database.billing_usage_models import BillingUsageCounter, BillingUsageReservation
from database.models import Base
from services.billing_usage_shadow import BillingQuotaReservationService


@pytest.fixture(scope="module")
def pg_engine():
    url = os.getenv("BILLING_SHADOW_DATABASE_URL")
    if not url or ("127.0.0.1" not in url and "localhost" not in url):
        pytest.skip("BILLING_SHADOW_DATABASE_URL não configurado para PostgreSQL local")
    parsed = urlsplit(url)
    db_name = "billing_reservation_46e2"
    if parsed.path and parsed.path.rstrip("/") != f"/{db_name}":
        base = parsed._replace(path=f"/{db_name}")
        target_url = urlunsplit(base)
    else:
        target_url = url
    admin_url = urlunsplit(parsed._replace(path="/postgres"))
    admin_engine = create_engine(admin_url)
    assert db_name.startswith("billing_reservation_test_") or db_name == "billing_reservation_46e2"
    with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :db_name AND pid <> pg_backend_pid()"), {"db_name": db_name})
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        conn.execute(text(f"CREATE DATABASE {db_name}"))
    engine = create_engine(target_url)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE billing_usage_reservations, billing_usage_counters, billing_subscription_companies, billing_subscriptions, billing_plan_versions, billing_plans, billing_accounts, clientes, regimes_tributarios RESTART IDENTITY CASCADE"))
    yield engine
    engine.dispose()
    with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :db_name AND pid <> pg_backend_pid()"), {"db_name": db_name})
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
    admin_engine.dispose()


@pytest.fixture(autouse=True)
def clean_billing_state(pg_engine):
    with pg_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE billing_usage_reservations, billing_usage_counters, billing_subscription_companies, billing_subscriptions, billing_plan_versions, billing_plans, billing_accounts, clientes, regimes_tributarios RESTART IDENTITY CASCADE"))
    yield
    with pg_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE billing_usage_reservations, billing_usage_counters, billing_subscription_companies, billing_subscriptions, billing_plan_versions, billing_plans, billing_accounts, clientes, regimes_tributarios RESTART IDENTITY CASCADE"))


def _seed_subscription(db, *, plan_code="START_V1", limit=50, counted=49, clientes=(1,)):
    db.execute(text("INSERT INTO regimes_tributarios (regime_tributario_id, nome, crt) VALUES (1, 'Simples Nacional', 1) ON CONFLICT DO NOTHING"))
    db.execute(text("INSERT INTO clientes (cliente_id, razao_social, nome_fantasia, produtor_rural, regime_tributario_id, cnae, logradouro, numero, bairro, codigo_municipio, nome_municipio, uf, cep, ambiente, ativo, data_cadastro, data_atualizacao) VALUES (1, 'Cliente Reserva', 'Cliente Reserva', FALSE, 1, '4781100', 'Rua A', '100', 'Centro', '3550308', 'São Paulo', 'SP', '01000-000', 2, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) ON CONFLICT (cliente_id) DO NOTHING"))

    account = BillingAccount(name="Reservation Account")
    db.add(account)
    db.flush()

    plan = BillingPlan(code=plan_code, name=plan_code, active=True, display_order=1)
    db.add(plan)
    db.flush()

    version = BillingPlanVersion(
        plan_id=plan.plan_id,
        version_code=plan_code,
        price=Decimal("60.00"),
        currency="BRL",
        valid_from=datetime.utcnow(),
        status="ACTIVE",
    )
    db.add(version)
    db.flush()

    subscription = BillingSubscription(
        account_id=account.account_id,
        plan_version_id=version.plan_version_id,
        status="ACTIVE",
        contracted_price=Decimal("60.00"),
        currency="BRL",
        started_at=datetime.utcnow(),
        billing_cycle="MONTHLY",
    )
    db.add(subscription)
    db.flush()

    for cliente_id in clientes:
        db.add(BillingSubscriptionCompany(subscription_id=subscription.subscription_id, cliente_id=cliente_id, status="ACTIVE"))

    db.add(BillingUsageCounter(
        subscription_id=subscription.subscription_id,
        metric_key="NFE_ISSUED",
        period_start=datetime.utcnow().date().replace(day=1),
        period_end=(datetime.utcnow().date().replace(day=28) + __import__('datetime').timedelta(days=4)).replace(day=1),
        quantity=counted,
        version=1,
    ))
    db.commit()
    return subscription


def _run_concurrent(Session, subscription_id, keys, *, metric_key="NFE_ISSUED", period_start=None, period_end=None):
    barrier = threading.Barrier(len(keys))
    results = {}

    def run(label):
        barrier.wait()
        session = Session()
        try:
            results[label] = BillingQuotaReservationService(session).reserve(
                subscription_id=subscription_id, cliente_id=1, metric_key=metric_key,
                reservation_key=keys[label], source_type="NFE", source_id=f"nfe-{label}",
                period_start=period_start, period_end=period_end,
            )
        finally:
            session.close()

    threads = [threading.Thread(target=run, args=(label,)) for label in keys]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_49_50_two_concurrent_reservations_allow_only_one(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=49)
        barrier = threading.Barrier(2)
        results = {}

        def run(label):
            barrier.wait()
            session = Session()
            try:
                service = BillingQuotaReservationService(session, reservation_ttl_minutes=15)
                results[label] = service.reserve(
                    subscription_id=subscription.subscription_id,
                    cliente_id=1,
                    metric_key="NFE_ISSUED",
                    reservation_key=f"NFE:issue:{label}",
                    source_type="NFE",
                    source_id=f"nfe-{label}",
                )
            finally:
                session.close()

        t1 = threading.Thread(target=run, args=("A",))
        t2 = threading.Thread(target=run, args=("B",))
        t1.start(); t2.start(); t1.join(); t2.join()

        assert sum(1 for value in results.values() if value.get("allowed") is True) == 1
        assert any(value.get("status") == "QUOTA_EXCEEDED" for value in results.values())
        used = db.execute(text("SELECT COALESCE(SUM(quantity), 0) FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription.subscription_id}).scalar()
        reserved = db.execute(text("SELECT COALESCE(SUM(quantity), 0) FROM billing_usage_reservations WHERE subscription_id = :sid AND status IN ('RESERVED', 'PENDING_RECONCILIATION')"), {"sid": subscription.subscription_id}).scalar()
        assert used + reserved == 50
    finally:
        db.close()


def test_confirm_duplicate_increments_once(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=0)
        service = BillingQuotaReservationService(db)
        reserve = service.reserve(
            subscription_id=subscription.subscription_id,
            cliente_id=1,
            metric_key="NFE_ISSUED",
            reservation_key="NFE:confirm-duplicate",
            source_type="NFE",
            source_id="nfe-confirm-duplicate",
        )
        assert reserve["allowed"] is True
        r1 = service.confirm(reservation_key="NFE:confirm-duplicate", source_id="nfe-confirm-duplicate")
        r2 = service.confirm(reservation_key="NFE:confirm-duplicate", source_id="nfe-confirm-duplicate")
        assert r1["status"] == "CONFIRMED"
        assert r2["status"] == "DUPLICATE"
        total = db.execute(text("SELECT COALESCE(SUM(quantity), 0) FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription.subscription_id}).scalar()
        assert total == 1
    finally:
        db.close()


def test_48_50_two_concurrent_reservations_allow_both(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=48)
        results = _run_concurrent(Session, subscription.subscription_id, {"A": "NFE:48:A", "B": "NFE:48:B"})
        assert all(value["status"] == "RESERVED" for value in results.values())
        assert db.execute(text("SELECT SUM(quantity) FROM billing_usage_reservations WHERE subscription_id = :sid AND status = 'RESERVED'"), {"sid": subscription.subscription_id}).scalar() == 2
    finally:
        db.close()


def test_50_50_two_concurrent_reservations_reject_both(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=50)
        results = _run_concurrent(Session, subscription.subscription_id, {"A": "NFE:50:A", "B": "NFE:50:B"})
        assert all(value["status"] == "QUOTA_EXCEEDED" for value in results.values())
        assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid"), {"sid": subscription.subscription_id}).scalar() == 0
    finally:
        db.close()


def test_same_reservation_key_is_logically_idempotent(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=49)
        results = _run_concurrent(Session, subscription.subscription_id, {"A": "NFE:same-key", "B": "NFE:same-key"})
        assert sum(value["status"] == "RESERVED" for value in results.values()) == 1
        assert sum(value["status"] == "DUPLICATE" for value in results.values()) == 1
        assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid"), {"sid": subscription.subscription_id}).scalar() == 1
    finally:
        db.close()


def test_override_and_period_are_isolated(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=74)
        db.add(BillingSubscriptionOverride(subscription_id=subscription.subscription_id, key="NFE_MONTHLY", value="75", reason="Teste 4.6E.2c"))
        db.commit()
        current_start = datetime.utcnow().date().replace(day=1)
        current_end = (current_start.replace(day=28) + __import__('datetime').timedelta(days=4)).replace(day=1)
        next_start = current_end
        next_end = (next_start.replace(day=28) + __import__('datetime').timedelta(days=4)).replace(day=1)
        current = BillingQuotaReservationService(db).reserve(subscription_id=subscription.subscription_id, cliente_id=1, metric_key="NFE_ISSUED", reservation_key="NFE:override:current", period_start=current_start, period_end=current_end)
        future = BillingQuotaReservationService(db).reserve(subscription_id=subscription.subscription_id, cliente_id=1, metric_key="NFE_ISSUED", reservation_key="NFE:override:future", period_start=next_start, period_end=next_end)
        assert current["status"] == "RESERVED"
        assert future["status"] == "RESERVED"
    finally:
        db.close()


def test_different_subscriptions_do_not_compete_for_lock(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        first = _seed_subscription(db, counted=49)
        second = _seed_subscription(db, plan_code="START_V1_B", counted=49)
        first_result = _run_concurrent(Session, first.subscription_id, {"A": "NFE:sub-a"})
        second_result = _run_concurrent(Session, second.subscription_id, {"B": "NFE:sub-b"})
        assert first_result["A"]["status"] == "RESERVED"
        assert second_result["B"]["status"] == "RESERVED"
    finally:
        db.close()


def test_different_metrics_do_not_share_quota_lock(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=49)
        nfe = _run_concurrent(Session, subscription.subscription_id, {"A": "NFE:metric-nfe"}, metric_key="NFE_ISSUED")
        ai = _run_concurrent(Session, subscription.subscription_id, {"B": "AI:metric-ai"}, metric_key="AI_REQUEST")
        assert nfe["A"]["status"] == "RESERVED"
        assert ai["B"]["status"] == "ALLOWED_FAIR_USE"
    finally:
        db.close()


def test_release_and_expiration_work(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        subscription = _seed_subscription(db, counted=0)
        service = BillingQuotaReservationService(db, reservation_ttl_minutes=0)
        result = service.reserve(
            subscription_id=subscription.subscription_id,
            cliente_id=1,
            metric_key="NFE_ISSUED",
            reservation_key="NFE:release-and-expire",
            source_type="NFE",
            source_id="nfe-release-and-expire",
        )
        assert result["allowed"] is True
        released = service.release(reservation_key="NFE:release-and-expire", reason="REJEITADA")
        assert released["status"] == "RELEASED"
        expired = service.expire(reservation_key="NFE:release-and-expire")
        assert expired["status"] == "EXPIRED"
    finally:
        db.close()


def test_premium_uses_fair_use_and_legacy_bypass_is_non_blocking(pg_engine):
    os.environ["FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"] = "true"
    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        premium = _seed_subscription(db, plan_code="PREMIUM_V1", counted=0)
        service = BillingQuotaReservationService(db)
        allowed = service.reserve(
            subscription_id=premium.subscription_id,
            cliente_id=1,
            metric_key="NFE_ISSUED",
            reservation_key="NFE:premium",
            source_type="NFE",
            source_id="nfe-premium",
        )
        assert allowed["status"] == "ALLOWED_FAIR_USE"

        legacy = _seed_subscription(db, plan_code="LEGACY_START_V1", counted=0)
        legacy_result = service.reserve(
            subscription_id=legacy.subscription_id,
            cliente_id=1,
            metric_key="NFE_ISSUED",
            reservation_key="NFE:legacy",
            source_type="NFE",
            source_id="nfe-legacy",
        )
        assert legacy_result["status"] in {"LEGACY_BYPASS", "LEGACY_UNMIGRATED", "CONTRACTUAL_REVIEW"}
    finally:
        db.close()

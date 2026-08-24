"""Medição de uso shadow, sem enforcement e sem dependência fiscal."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import os
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database.billing_usage_models import BillingUsageCounter, BillingUsageEvent, BillingUsageReservation
from database.billing_shadow_models import BillingSubscription, BillingSubscriptionCompany

USAGE_SHADOW_FLAG = "FEATURE_BILLING_USAGE_SHADOW_ENABLED"
RESERVATION_SHADOW_FLAG = "FEATURE_BILLING_NFE_RESERVATION_SHADOW_ENABLED"
QUOTA_SHADOW_FLAG = "FEATURE_BILLING_NFE_QUOTA_SHADOW"
QUOTA_ENFORCEMENT_FLAG = "FEATURE_BILLING_NFE_QUOTA_ENABLED"
METRICS = {"NFE_ISSUED", "NFCE_ISSUED", "NFSE_ISSUED", "AI_REQUEST", "API_REQUEST"}
STATUSES = {"PENDING", "COUNTED", "IGNORED", "REVERSED"}
SOURCES = {"NFE", "NFCE", "NFSE", "AI", "API"}
RESERVATION_STATUSES = {"RESERVED", "CONFIRMED", "RELEASED", "EXPIRED", "CANCELLED", "PENDING_RECONCILIATION"}


@dataclass(frozen=True)
class BillingPeriod:
    start: date
    end: date


class BillingPeriodResolver:
    def resolve(self, started_at=None, cycle="MONTHLY", today=None):
        today = today or date.today()
        if cycle != "MONTHLY" or not started_at:
            return BillingPeriod(today.replace(day=1), today.replace(day=1) + timedelta(days=32))
        start = started_at.date() if isinstance(started_at, datetime) else started_at
        while True:
            next_start = start.replace(day=28) + timedelta(days=4)
            next_start = next_start.replace(day=1)
            if today < next_start:
                return BillingPeriod(start, next_start)
            start = next_start


class BillingUsageShadowService:
    """Registra evento/counter apenas quando a flag shadow está ativa."""

    def __init__(self, db, period_resolver=None):
        self.db = db
        self.period_resolver = period_resolver or BillingPeriodResolver()

    @staticmethod
    def enabled():
        return os.getenv(USAGE_SHADOW_FLAG, "false").lower() in {"1", "true", "yes", "on"}

    def resolve_subscription(self, cliente_id):
        rows = self.db.query(BillingSubscription).filter(
            BillingSubscription.status == "ACTIVE",
        ).all()
        return next((sub for sub in rows if any(
            link.cliente_id == cliente_id and link.status == "ACTIVE"
            for link in sub.companies
        )), None)

    def record(self, *, cliente_id, metric_key, event_key, source_type, source_id=None,
               quantity=1, status="COUNTED", occurred_at=None, metadata=None):
        if metric_key not in METRICS:
            raise ValueError(f"Métrica inválida: {metric_key}")
        if source_type not in SOURCES:
            raise ValueError(f"Fonte inválida: {source_type}")
        if status not in STATUSES:
            raise ValueError(f"Status inválido: {status}")
        if not self.enabled():
            return {"recorded": False, "reason": "FEATURE_FLAG_OFF", "event_key": event_key}
        subscription = self.resolve_subscription(cliente_id)
        if not subscription:
            return {"recorded": False, "reason": "NO_SHADOW_SUBSCRIPTION", "event_key": event_key}
        occurred_at = occurred_at or datetime.utcnow()
        period = self.period_resolver.resolve(subscription.started_at, subscription.billing_cycle, occurred_at.date())
        existing = self.db.query(BillingUsageEvent).filter_by(metric_key=metric_key, event_key=event_key).first()
        if existing:
            return {"recorded": False, "reason": "DUPLICATE", "event_id": existing.usage_event_id}
        event = BillingUsageEvent(
            account_id=subscription.account_id, subscription_id=subscription.subscription_id,
            cliente_id=cliente_id, metric_key=metric_key, event_key=event_key,
            quantity=quantity, period_start=period.start, period_end=period.end,
            source_type=source_type, source_id=source_id, status=status,
            metadata_json=metadata, occurred_at=occurred_at,
        )
        self.db.add(event)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.query(BillingUsageEvent).filter_by(metric_key=metric_key, event_key=event_key).first()
            if existing:
                return {"recorded": False, "reason": "DUPLICATE", "event_id": existing.usage_event_id}
            return {"recorded": False, "reason": "DUPLICATE", "event_key": event_key}
        self._upsert_counter(subscription.subscription_id, metric_key, period, quantity if status == "COUNTED" else 0)
        self.db.commit()
        return {"recorded": True, "event_id": event.usage_event_id, "status": status}

    def _upsert_counter(self, subscription_id, metric_key, period, quantity):
        dialect = self.db.bind.dialect.name if getattr(self.db, "bind", None) else ""
        if dialect == "postgresql":
            self.db.execute(text("""
                INSERT INTO billing_usage_counters
                    (subscription_id, metric_key, period_start, period_end, quantity, version, updated_at)
                VALUES (:sid, :metric, :start, :end, :quantity, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (subscription_id, metric_key, period_start, period_end)
                DO UPDATE SET quantity = billing_usage_counters.quantity + EXCLUDED.quantity,
                              version = billing_usage_counters.version + 1,
                              updated_at = CURRENT_TIMESTAMP
            """), {"sid": subscription_id, "metric": metric_key, "start": period.start, "end": period.end, "quantity": quantity})
        else:
            counter = self.db.query(BillingUsageCounter).filter_by(
                subscription_id=subscription_id, metric_key=metric_key,
                period_start=period.start, period_end=period.end,
            ).first()
            if counter:
                counter.quantity += quantity
                counter.version += 1
            else:
                self.db.add(BillingUsageCounter(
                    subscription_id=subscription_id, metric_key=metric_key,
                    period_start=period.start, period_end=period.end,
                    quantity=quantity, version=1,
                ))

    def record_safe(self, **kwargs):
        """Registra uso sem permitir que falha de billing afete o chamador."""
        try:
            return self.record(**kwargs)
        except Exception:
            return {
                "recorded": False,
                "reason": "USAGE_LOGGING_FAILED",
                "event_key": kwargs.get("event_key"),
            }


class BillingQuotaReservationService:
    """Reserva de quota NF-e em modo shadow, sem bloquear emissão em produção."""

    def __init__(self, db, reservation_ttl_minutes=15, period_resolver=None):
        self.db = db
        self.reservation_ttl_minutes = reservation_ttl_minutes
        self.period_resolver = period_resolver or BillingPeriodResolver()

    @staticmethod
    def enabled():
        flags = (RESERVATION_SHADOW_FLAG, QUOTA_SHADOW_FLAG, QUOTA_ENFORCEMENT_FLAG)
        return any(os.getenv(flag, "false").lower() in {"1", "true", "yes", "on"} for flag in flags)

    def _resolve_subscription(self, subscription_id=None, cliente_id=None):
        if subscription_id is not None:
            return self.db.query(BillingSubscription).filter_by(subscription_id=subscription_id).first()
        if cliente_id is None:
            return None
        rows = self.db.query(BillingSubscription).filter(BillingSubscription.status == "ACTIVE").all()
        return next((sub for sub in rows if any(link.cliente_id == cliente_id and link.status == "ACTIVE" for link in sub.companies)), None)

    def _resolve_limit(self, subscription):
        plan_code = getattr(getattr(subscription, "plan_version", None), "version_code", "")
        if plan_code == "PREMIUM_V1":
            return None
        if plan_code == "ENTERPRISE_V1":
            override = next((o for o in subscription.overrides if o.key == "NFE_MONTHLY" and (o.expires_at is None or o.expires_at >= datetime.utcnow())), None)
            if override:
                try:
                    return int(override.value)
                except (TypeError, ValueError):
                    return None
            if subscription.plan_version and getattr(subscription.plan_version, "features", None):
                for feature in subscription.plan_version.features:
                    if getattr(feature.feature, "key", None) == "NFE_MONTHLY":
                        if feature.limit_type in {"CONTRACTUAL", "UNMETERED_WITH_FAIR_USE"}:
                            return None
                        if feature.limit_value is not None:
                            return int(feature.limit_value)
            return None
        override = next((o for o in subscription.overrides if o.key == "NFE_MONTHLY" and (o.expires_at is None or o.expires_at >= datetime.utcnow())), None)
        if override:
            try:
                return int(override.value)
            except (TypeError, ValueError):
                return None
        if plan_code.startswith("LEGACY_"):
            return None
        return 50

    @contextmanager
    def _owned_transaction_scope(self):
        # reserve/confirm own their short database transaction; callers must
        # not keep an unrelated autobegin transaction open on this session.
        if self.db.in_transaction():
            self.db.rollback()
        with self.db.begin():
            yield

    def _quota_lock(self, subscription_id, metric_key, period_start, period_end):
        lock_key = f"billing-quota:{subscription_id}:{metric_key}:{period_start}:{period_end}"
        self.db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"), {"lock_key": lock_key})

    def _counted_usage(self, subscription_id, metric_key, period_start=None, period_end=None):
        total = self.db.execute(text("""
            SELECT COALESCE(SUM(quantity), 0)
            FROM billing_usage_counters
            WHERE subscription_id = :sid AND metric_key = :metric
              AND (:period_start IS NULL OR period_start = :period_start)
              AND (:period_end IS NULL OR period_end = :period_end)
        """), {"sid": subscription_id, "metric": metric_key, "period_start": period_start, "period_end": period_end}).scalar()
        return int(total or 0)

    def _reserved_usage(self, subscription_id, metric_key, period_start=None, period_end=None):
        total = self.db.execute(text("""
            SELECT COALESCE(SUM(quantity), 0)
            FROM billing_usage_reservations
            WHERE subscription_id = :sid AND metric_key = :metric
                            AND status IN ('RESERVED', 'PENDING_RECONCILIATION')
                            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
              AND (:period_start IS NULL OR period_start = :period_start)
              AND (:period_end IS NULL OR period_end = :period_end)
        """), {"sid": subscription_id, "metric": metric_key, "period_start": period_start, "period_end": period_end}).scalar()
        return int(total or 0)

    def reserve(self, *, subscription_id, cliente_id, metric_key, reservation_key, source_type="NFE", source_id=None,
                quantity=1, period_start=None, period_end=None, expires_in_minutes=None):
        if metric_key not in METRICS:
            raise ValueError(f"Métrica inválida: {metric_key}")
        if source_type not in SOURCES:
            raise ValueError(f"Fonte inválida: {source_type}")
        if not self.enabled():
            return {"allowed": False, "status": "FLAG_OFF", "code": "BILLING_RESERVATION_DISABLED", "reservation_key": reservation_key}
        subscription = self._resolve_subscription(subscription_id=subscription_id)
        if not subscription:
            return {"allowed": False, "status": "LEGACY_UNMIGRATED", "code": "NO_SUBSCRIPTION", "reservation_key": reservation_key}
        if metric_key != "NFE_ISSUED":
            return {"allowed": True, "status": "ALLOWED_FAIR_USE", "code": "NON_FISCAL_RESERVATION", "reservation_key": reservation_key}
        limit = self._resolve_limit(subscription)
        if limit is None:
            if getattr(getattr(subscription, "plan_version", None), "version_code", "") == "PREMIUM_V1":
                return {"allowed": True, "status": "ALLOWED_FAIR_USE", "code": "UNMETERED_WITH_FAIR_USE", "reservation_key": reservation_key}
            if getattr(getattr(subscription, "plan_version", None), "version_code", "").startswith("LEGACY_"):
                return {"allowed": True, "status": "LEGACY_BYPASS", "code": "LEGACY_UNMIGRATED", "reservation_key": reservation_key}
            return {"allowed": False, "status": "CONTRACTUAL_REVIEW", "code": "NO_LIMIT_CONFIGURED", "reservation_key": reservation_key}
        now = datetime.utcnow()
        period_start = period_start or now.date().replace(day=1)
        period_end = period_end or (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        try:
            with self._owned_transaction_scope():
                self._quota_lock(subscription_id, metric_key, period_start, period_end)
                subscription = self._resolve_subscription(subscription_id=subscription_id)
                if not subscription:
                    return {"allowed": False, "status": "LEGACY_UNMIGRATED", "code": "NO_SUBSCRIPTION", "reservation_key": reservation_key}
                existing = self.db.query(BillingUsageReservation).filter_by(
                    subscription_id=subscription_id, metric_key=metric_key, reservation_key=reservation_key,
                ).first()
                if existing:
                    return {"allowed": False, "status": "DUPLICATE", "code": "RESERVATION_DUPLICATE", "reservation_id": existing.reservation_id, "reservation_key": reservation_key}
                now = datetime.utcnow()
                counted = self._counted_usage(subscription_id, metric_key, period_start, period_end)
                reserved = self._reserved_usage(subscription_id, metric_key, period_start, period_end)
                if counted + reserved + quantity > limit:
                    return {"allowed": False, "status": "QUOTA_EXCEEDED", "code": "PLAN_NFE_QUOTA_EXCEEDED", "used": counted + reserved, "limit": limit, "reservation_key": reservation_key}
                expires_at = now + timedelta(minutes=expires_in_minutes or self.reservation_ttl_minutes)
                reservation = BillingUsageReservation(
                    subscription_id=subscription_id,
                    cliente_id=cliente_id,
                    metric_key=metric_key,
                    reservation_key=reservation_key,
                    quantity=quantity,
                    period_start=period_start,
                    period_end=period_end,
                    status="RESERVED",
                    expires_at=expires_at,
                    source_type=source_type,
                    source_id=source_id,
                    created_at=now,
                )
                self.db.add(reservation)
                self.db.flush()
                return {
                    "allowed": True,
                    "status": "RESERVED",
                    "code": "RESERVATION_CREATED",
                    "reservation_id": reservation.reservation_id,
                    "reservation_key": reservation_key,
                    "used": counted + reserved,
                    "limit": limit,
                    "expires_at": expires_at,
                }
        except IntegrityError:
            self.db.rollback()
            existing = self.db.query(BillingUsageReservation).filter_by(
                subscription_id=subscription_id, metric_key=metric_key, reservation_key=reservation_key,
            ).first()
            if existing:
                return {"allowed": False, "status": "DUPLICATE", "code": "RESERVATION_DUPLICATE", "reservation_id": existing.reservation_id, "reservation_key": reservation_key}
            return {"allowed": False, "status": "DUPLICATE", "code": "RESERVATION_DUPLICATE", "reservation_key": reservation_key}

    def confirm(self, *, reservation_id=None, reservation_key=None, source_id=None, status="AUTORIZADA"):
        if not self.enabled():
            return {"status": "FLAG_OFF", "code": "BILLING_RESERVATION_DISABLED"}
        reservation = self.db.query(BillingUsageReservation).filter_by(reservation_id=reservation_id).first() if reservation_id is not None else self.db.query(BillingUsageReservation).filter_by(reservation_key=reservation_key).first()
        if not reservation:
            return {"status": "NOT_FOUND", "code": "RESERVATION_NOT_FOUND"}
        if reservation.status == "CONFIRMED":
            return {"status": "DUPLICATE", "code": "CONFIRM_DUPLICATE", "reservation_id": reservation.reservation_id}
        now = datetime.utcnow()
        try:
            reservation_id = reservation.reservation_id
            with self._owned_transaction_scope():
                reservation = self.db.query(BillingUsageReservation).filter_by(reservation_id=reservation_id).with_for_update().first()
                if reservation.status == "CONFIRMED":
                    return {"status": "DUPLICATE", "code": "CONFIRM_DUPLICATE", "reservation_id": reservation.reservation_id}
                reservation.status = "CONFIRMED"
                reservation.confirmed_at = now
                event_key = reservation.reservation_key if reservation_key is not None else reservation.reservation_key
                event = self.db.query(BillingUsageEvent).filter_by(metric_key="NFE_ISSUED", event_key=event_key).first()
                if event is None:
                    event = BillingUsageEvent(
                        account_id=reservation.subscription_id,
                        subscription_id=reservation.subscription_id,
                        cliente_id=reservation.cliente_id,
                        metric_key="NFE_ISSUED",
                        event_key=event_key,
                        quantity=reservation.quantity,
                        period_start=reservation.period_start,
                        period_end=reservation.period_end,
                        source_type=reservation.source_type,
                        source_id=source_id or reservation.source_id,
                        status="COUNTED",
                        occurred_at=now,
                    )
                    self.db.add(event)
                    self.db.flush()
                self._upsert_counter(reservation.subscription_id, "NFE_ISSUED", reservation.period_start, reservation.period_end, reservation.quantity)
                return {"status": "CONFIRMED", "code": "CONFIRM_OK", "reservation_id": reservation.reservation_id, "event_key": event_key}
        except IntegrityError:
            self.db.rollback()
            return {"status": "DUPLICATE", "code": "CONFIRM_DUPLICATE", "reservation_id": reservation.reservation_id}

    def release(self, *, reservation_id=None, reservation_key=None, reason="REJEITADA"):
        if not self.enabled():
            return {"status": "FLAG_OFF", "code": "BILLING_RESERVATION_DISABLED"}
        reservation = self.db.query(BillingUsageReservation).filter_by(reservation_id=reservation_id).first() if reservation_id is not None else self.db.query(BillingUsageReservation).filter_by(reservation_key=reservation_key).first()
        if not reservation:
            return {"status": "NOT_FOUND", "code": "RESERVATION_NOT_FOUND"}
        if reservation.status in {"RELEASED", "EXPIRED", "CANCELLED"}:
            return {"status": reservation.status, "code": "RELEASE_ALREADY_DONE", "reservation_id": reservation.reservation_id}
        reservation.status = "RELEASED"
        reservation.released_at = datetime.utcnow()
        return {"status": "RELEASED", "code": "RELEASE_OK", "reservation_id": reservation.reservation_id, "reason": reason}

    def expire(self, *, reservation_id=None, reservation_key=None):
        if not self.enabled():
            return {"status": "FLAG_OFF", "code": "BILLING_RESERVATION_DISABLED"}
        reservation = self.db.query(BillingUsageReservation).filter_by(reservation_id=reservation_id).first() if reservation_id is not None else self.db.query(BillingUsageReservation).filter_by(reservation_key=reservation_key).first()
        if not reservation:
            return {"status": "NOT_FOUND", "code": "RESERVATION_NOT_FOUND"}
        reservation.status = "EXPIRED"
        reservation.released_at = datetime.utcnow()
        return {"status": "EXPIRED", "code": "RESERVATION_EXPIRED", "reservation_id": reservation.reservation_id}

    def reconcile(self, *, reservation_id=None, reservation_key=None, real_status):
        if real_status in {"AUTORIZADA", "AUTHORIZED"}:
            return self.confirm(reservation_id=reservation_id, reservation_key=reservation_key)
        if real_status in {"REJEITADA", "VALIDACAO_LOCAL_FALHOU", "REJECTED", "LOCAL_VALIDATION_FAILED"}:
            return self.release(reservation_id=reservation_id, reservation_key=reservation_key, reason=real_status)
        if reservation_id is not None:
            reservation = self.db.query(BillingUsageReservation).filter_by(reservation_id=reservation_id).first()
        else:
            reservation = self.db.query(BillingUsageReservation).filter_by(reservation_key=reservation_key).first()
        if reservation:
            reservation.status = "PENDING_RECONCILIATION"
        return {"status": "PENDING_RECONCILIATION", "code": "RECONCILE_PENDING", "reservation_id": reservation.reservation_id if reservation else None}

    def _upsert_counter(self, subscription_id, metric_key, period_start, period_end, quantity):
        self.db.execute(text("""
            INSERT INTO billing_usage_counters
                (subscription_id, metric_key, period_start, period_end, quantity, version, updated_at)
            VALUES (:sid, :metric, :start, :end, :quantity, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (subscription_id, metric_key, period_start, period_end)
            DO UPDATE SET quantity = billing_usage_counters.quantity + EXCLUDED.quantity,
                          version = billing_usage_counters.version + 1,
                          updated_at = CURRENT_TIMESTAMP
        """), {"sid": subscription_id, "metric": metric_key, "start": period_start, "end": period_end, "quantity": quantity})


class AIUsageAdapter:
    def __init__(self, usage_service):
        self.usage_service = usage_service

    def record_request(self, *, cliente_id, source_id, funcionalidade, tokens=0, cost=0):
        return self.usage_service.record(
            cliente_id=cliente_id, metric_key="AI_REQUEST", event_key=f"ai:{source_id}",
            source_type="AI", source_id=source_id, metadata={
                "feature_key": funcionalidade, "tokens": tokens, "cost": cost,
            },
        )


class APIUsageAdapter:
    def __init__(self, usage_service):
        self.usage_service = usage_service

    def record_request(self, *, cliente_id, source_id, endpoint, status_code):
        return self.usage_service.record(
            cliente_id=cliente_id, metric_key="API_REQUEST", event_key=f"api:{source_id}",
            source_type="API", source_id=source_id, metadata={
                "endpoint": endpoint, "status_code": status_code,
            },
        )

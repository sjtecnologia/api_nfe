"""Medição de uso shadow, sem enforcement e sem dependência fiscal."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import os

from sqlalchemy import text

from database.billing_usage_models import BillingUsageCounter, BillingUsageEvent
from database.billing_shadow_models import BillingSubscription, BillingSubscriptionCompany

USAGE_SHADOW_FLAG = "FEATURE_BILLING_USAGE_SHADOW_ENABLED"
METRICS = {"NFE_ISSUED", "NFCE_ISSUED", "NFSE_ISSUED", "AI_REQUEST", "API_REQUEST"}
STATUSES = {"PENDING", "COUNTED", "IGNORED", "REVERSED"}
SOURCES = {"NFE", "NFCE", "NFSE", "AI", "API"}


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
        self.db.flush()
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

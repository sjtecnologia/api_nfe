"""Adapter fino do hook de quota NF-e da Fase 4.6F."""
import os

from services.billing_usage_shadow import BillingQuotaReservationService


def _enabled(name):
    return os.getenv(name, "false").lower() in {"1", "true", "yes", "on"}


class BillingNFeQuotaAdapter:
    """Coordena observação/reserva sem espalhar regra comercial no fluxo fiscal."""

    def __init__(self, db, reservation_service=None):
        self.db = db
        self.reservations = reservation_service or BillingQuotaReservationService(db)

    @staticmethod
    def _rollout_client_ids():
        raw = os.getenv("BILLING_NFE_QUOTA_ROLLOUT_CLIENT_IDS", "")
        return {int(value.strip()) for value in raw.split(",") if value.strip().isdigit()}

    def before_external_send(self, *, cliente_id, reservation_key, source_id):
        global_enabled = _enabled("FEATURE_BILLING_NFE_QUOTA_ENABLED")
        shadow_enabled = _enabled("FEATURE_BILLING_NFE_QUOTA_SHADOW")
        rollout_enabled = cliente_id in self._rollout_client_ids()
        if not shadow_enabled and not (global_enabled and rollout_enabled):
            return {"allowed": True, "status": "FLAG_OFF", "code": "BILLING_QUOTA_DISABLED"}

        subscription = self.reservations._resolve_subscription(cliente_id=cliente_id)
        if not subscription:
            return {"allowed": True, "status": "LEGACY_UNMIGRATED", "code": "NO_SUBSCRIPTION"}
        plan_code = getattr(getattr(subscription, "plan_version", None), "version_code", "")
        if plan_code != "START_V1":
            return {"allowed": True, "status": "NOT_IN_ROLLOUT", "code": "PLAN_NOT_START_V1", "plan": plan_code}

        result = self.reservations.reserve(
            subscription_id=subscription.subscription_id,
            cliente_id=cliente_id,
            metric_key="NFE_ISSUED",
            reservation_key=reservation_key,
            source_type="NFE",
            source_id=source_id,
        )
        if result.get("status") == "QUOTA_EXCEEDED" and not (global_enabled and rollout_enabled):
            result["allowed"] = True
            result["status"] = "SHADOW_QUOTA_EXCEEDED"
        return result

    def after_authorized(self, *, reservation_key, source_id=None):
        return self.reservations.confirm(reservation_key=reservation_key, source_id=source_id)

    def known_not_authorized(self, *, reservation_key, reason):
        return self.reservations.release(reservation_key=reservation_key, reason=reason)

"""Entitlements comerciais não fiscais.

A flag permanece desligada por padrão. UNKNOWN é observável e não bloqueante
para preservar clientes legados durante a transição.
"""
from dataclasses import dataclass
import os
from functools import wraps

from flask import jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user

from auth.permissions import get_accessible_client_ids
from database.billing_shadow_models import BillingSubscription
from database.connection import get_db
from services.billing_shadow import EntitlementResolver, LegacySubscriptionAdapter

FEATURE_BILLING_ENTITLEMENTS_ENABLED = "FEATURE_BILLING_ENTITLEMENTS_ENABLED"
FEATURE_ENTITLEMENT_AI_SALES_ANALYSIS = "FEATURE_ENTITLEMENT_AI_SALES_ANALYSIS"

FEATURE_REQUIRED_PLANS = {
    "AI_SALES_ANALYSIS": ["PROFISSIONAL_V1", "PREMIUM_V1", "ENTERPRISE_V1"],
}


@dataclass(frozen=True)
class FeatureAccess:
    feature: str
    enabled: bool
    source: str
    reason: str
    current_plan: str | None = None
    required_plans: tuple[str, ...] = ()
    limit_type: str = "DISABLED"
    limit_value: int | None = None

    def to_dict(self):
        return {
            "feature": self.feature,
            "enabled": self.enabled,
            "source": self.source,
            "reason": self.reason,
            "current_plan": self.current_plan,
            "required_plans": list(self.required_plans),
            "limit_type": self.limit_type,
            "limit_value": self.limit_value,
        }


class CommercialEntitlementService:
    """Fonte única de decisão para features comerciais não fiscais."""

    def __init__(self, db):
        self.db = db

    @staticmethod
    def enabled():
        return os.getenv(FEATURE_BILLING_ENTITLEMENTS_ENABLED, "false").lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def feature_enabled(feature):
        if not CommercialEntitlementService.enabled():
            return False
        key = f"FEATURE_ENTITLEMENT_{feature}"
        return os.getenv(key, "true").lower() in {"1", "true", "yes", "on"}

    def resolve_feature_access(self, *, cliente_id, user_id, feature):
        required = tuple(FEATURE_REQUIRED_PLANS.get(feature, ()))
        if not self.feature_enabled(feature):
            return FeatureAccess(feature, True, "FLAG_OFF", "ALLOWED", required_plans=required)

        try:
            subscriptions = self.db.query(BillingSubscription).filter(
                BillingSubscription.status == "ACTIVE",
            ).all()
            subscription = next(
                (
                    candidate for candidate in subscriptions
                    if any(
                        link.cliente_id == cliente_id and link.status == "ACTIVE"
                        for link in candidate.companies
                    )
                ),
                None,
            )
            if subscription:
                result = EntitlementResolver(self.db).resolve(subscription.subscription_id, feature)
                current_plan = subscription.plan_version.version_code
                if result.get("enabled"):
                    reason = "OVERRIDE" if result.get("source") == "OVERRIDE" else "ALLOWED"
                    return FeatureAccess(feature, True, result.get("source", "PLAN"), reason, current_plan, required, result.get("limit_type", "ENABLED"), result.get("limit_value"))
                reason = "ROADMAP" if result.get("reason") == "ROADMAP" else "PLAN_NOT_ENTITLED"
                return FeatureAccess(feature, False, result.get("source", "PLAN"), reason, current_plan, required, result.get("limit_type", "DISABLED"), result.get("limit_value"))

            legacy = LegacySubscriptionAdapter(self.db).get_for_company(cliente_id)
            if legacy:
                # Grandfathering: não retirar acesso conhecido de clientes legados.
                return FeatureAccess(feature, True, "LEGACY", "ALLOWED", legacy.get("plan_code"), required)
            return FeatureAccess(feature, True, "DEFAULT", "LEGACY_UNKNOWN", None, required)
        except Exception:
            # Falha de shadow não pode quebrar o recurso durante transição.
            return FeatureAccess(feature, True, "DEFAULT", "LEGACY_UNKNOWN", None, required)

    def get_upgrade_options(self, feature):
        return list(FEATURE_REQUIRED_PLANS.get(feature, ()))


def _current_client_id():
    return session.get("current_client_id") or session.get("active_cliente_id")


def feature_required(feature):
    """Guard não fiscal; preserva acesso quando a flag está desligada/UNKNOWN."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            cliente_id = _current_client_id()
            if not cliente_id:
                return view(*args, **kwargs)
            db = next(get_db())
            try:
                access = CommercialEntitlementService(db).resolve_feature_access(
                    cliente_id=cliente_id, user_id=current_user.id, feature=feature
                )
                if access.enabled or access.reason == "LEGACY_UNKNOWN":
                    return view(*args, **kwargs)
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({
                        "success": False,
                        "code": "PLAN_UPGRADE_REQUIRED",
                        **access.to_dict(),
                        "upgrade_url": url_for("billing_shadow.meu_plano"),
                    }), 403
                return render_template("admin/billing/feature_upgrade.html", access=access.to_dict()), 200
            finally:
                db.close()
        return wrapped
    return decorator

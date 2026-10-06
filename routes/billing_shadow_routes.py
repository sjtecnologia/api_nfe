"""Views de diagnóstico comercial e upgrade, sem checkout/enforcement fiscal."""
from datetime import date

from flask import Blueprint, render_template, session
from flask_login import login_required, current_user

from auth.decorators import admin_required, super_admin_required
from database.connection import get_db
from database.billing_shadow_models import BillingSubscription
from database.billing_usage_models import BillingUsageCounter
from services.billing_shadow import CapacityResolver
from services.commercial_catalog import classify_usage, get_catalog, find_plan
from services.commercial_entitlements import CommercialEntitlementService

billing_shadow_bp = Blueprint("billing_shadow", __name__, url_prefix="/admin")


@billing_shadow_bp.route("/meu-plano")
@login_required
@admin_required()
def meu_plano():
    cliente_id = session.get("current_client_id") or session.get("active_cliente_id")
    db = next(get_db())
    try:
        subscription = None
        access = None
        plan = None
        capacities = {"companies": None, "users": None}
        usage = None
        catalog = get_catalog()
        if cliente_id:
            try:
                subscription = db.query(BillingSubscription).join(
                    BillingSubscription.companies
                ).filter_by(cliente_id=cliente_id, status="ACTIVE").first()
            except Exception:
                subscription = None
            if subscription:
                plan = find_plan(subscription.plan_version.version_code)
                resolver = CapacityResolver(db)
                capacities = {
                    "companies": resolver.companies(subscription.subscription_id),
                    "users": resolver.users(subscription.subscription_id),
                }
                if plan and plan.nfe_policy.endswith("/mês"):
                    current_start = date.today().replace(day=1)
                    usage = db.query(BillingUsageCounter).filter(
                        BillingUsageCounter.subscription_id == subscription.subscription_id,
                        BillingUsageCounter.metric_key == "NFE_ISSUED",
                        BillingUsageCounter.period_start == current_start,
                    ).first()
            access = CommercialEntitlementService(db).resolve_feature_access(
                cliente_id=cliente_id, user_id=current_user.id, feature="AI_SALES_ANALYSIS"
            ).to_dict()
        return render_template(
            "admin/billing/meu_plano.html",
            subscription=subscription,
            access=access,
            cliente_id=cliente_id,
            plan=plan,
            capacities=capacities,
            nfe_usage=usage.quantity if usage else 0,
            nfe_usage_state=classify_usage(usage.quantity if usage else 0, 50 if plan and plan.nfe_policy.endswith("/mês") else None),
            catalog=catalog,
        )
    finally:
        db.close()


@billing_shadow_bp.route("/billing-shadow")
@login_required
@super_admin_required()
def billing_shadow_diagnostic():
    """Diagnóstico administrativo; não altera registros."""
    return render_template("admin/billing/shadow_diagnostic.html")

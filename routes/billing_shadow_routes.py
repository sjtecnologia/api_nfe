"""Views de diagnóstico comercial e upgrade, sem checkout/enforcement fiscal."""
from flask import Blueprint, render_template, session
from flask_login import login_required, current_user

from auth.decorators import admin_required, super_admin_required
from database.connection import get_db
from database.billing_shadow_models import BillingSubscription
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
        if cliente_id:
            try:
                subscription = db.query(BillingSubscription).join(
                    BillingSubscription.companies
                ).filter_by(cliente_id=cliente_id, status="ACTIVE").first()
            except Exception:
                subscription = None
            access = CommercialEntitlementService(db).resolve_feature_access(
                cliente_id=cliente_id, user_id=current_user.id, feature="AI_SALES_ANALYSIS"
            ).to_dict()
        return render_template("admin/billing/meu_plano.html", subscription=subscription, access=access, cliente_id=cliente_id)
    finally:
        db.close()


@billing_shadow_bp.route("/billing-shadow")
@login_required
@super_admin_required()
def billing_shadow_diagnostic():
    """Diagnóstico administrativo; não altera registros."""
    return render_template("admin/billing/shadow_diagnostic.html")

"""Executor controlado para migração legacy com dry-run real e apply de laboratório.

O executor é deliberadamente separado do fluxo fiscal. O dry-run pode auditar
clientes reais em READ ONLY; o apply permanece restrito a laboratório.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from database.billing_shadow_models import (
    BillingAccount,
    BillingFeature,
    BillingPlan,
    BillingPlanFeature,
    BillingPlanVersion,
    BillingSubscription,
    BillingSubscriptionCompany,
    BillingSubscriptionOverride,
)

PLAN_CODE = "LEGACY_60"
VERSION_CODE = "LEGACY_60_V1"
DECISION_SOURCE = "MANUAL_BUSINESS_DECISION"
NFE_POLICY = "LEGACY_PRESERVED"


@dataclass(frozen=True)
class LegacyMigrationSpec:
    cliente_id: int
    current_users: int
    current_companies: int
    contracted_price: Decimal = Decimal("60.00")
    currency: str = "BRL"
    decision_date: str = "2026-08-25"
    source: str = DECISION_SOURCE


@dataclass(frozen=True)
class MigrationResult:
    cliente_id: int
    mode: str
    status: str
    account_id: int | None
    subscription_id: int | None
    objects_to_create: tuple[str, ...]
    objects_existing: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cliente_id": self.cliente_id,
            "decision": "GRANDFATHER_READY" if self.mode == "DRY_RUN" else None,
            "mode": self.mode,
            "status": self.status,
            "account_id": self.account_id,
            "subscription_id": self.subscription_id,
            "objects_to_create": list(self.objects_to_create),
            "objects_existing": list(self.objects_existing),
            "warnings": list(self.warnings),
            "would_update_legacy": [],
            "conflicts": [],
        }


class LegacyGrandfatherMigrationExecutor:
    """Executa somente specs aprovadas pelo chamador, em sessão transacional."""

    def __init__(self, session):
        self.session = session

    def preview(self, spec: LegacyMigrationSpec) -> MigrationResult:
        existing = self._existing(spec)
        if existing:
            return MigrationResult(spec.cliente_id, "DRY_RUN", "ALREADY_MIGRATED", existing[0], existing[1], (), ("BillingAccount", "BillingSubscription", "BillingSubscriptionCompany", "BillingSubscriptionOverride"), ("NO_CHANGES",))
        return MigrationResult(
            spec.cliente_id,
            "DRY_RUN",
            "WOULD_MIGRATE",
            None,
            None,
            ("BillingAccount", "BillingSubscription", "BillingSubscriptionCompany", "BillingSubscriptionOverride(MAX_USERS)", "BillingSubscriptionOverride(MAX_COMPANIES)"),
            (),
            ("LEGACY_QUOTA_PRESERVED", "CLOSED_TO_NEW_SUBSCRIPTIONS", "MANUAL_BUSINESS_DECISION", "CONTRACTED_PRICE_60.00_BRL", f"MAX_USERS={spec.current_users}", f"MAX_COMPANIES={spec.current_companies}", "PRESERVE_EXISTING_ACCESS", "NO_LEGACY_DATA_UPDATE"),
        )

    def apply(self, spec: LegacyMigrationSpec, *, fail_after_account: bool = False) -> MigrationResult:
        self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"), {"lock_name": f"legacy-grandfather:{spec.cliente_id}"})
        existing = self._existing(spec)
        if existing:
            return MigrationResult(spec.cliente_id, "APPLY", "ALREADY_MIGRATED", existing[0], existing[1], (), ("BillingAccount", "BillingSubscription", "BillingSubscriptionCompany", "BillingSubscriptionOverride"), ("NO_CHANGES",))

        plan_version = self._ensure_plan_version()
        account = BillingAccount(
            name=f"LEGACY_GRANDFATHER_CLIENT_{spec.cliente_id}",
            description="Controlled legacy grandfather migration representation",
            status="ACTIVE",
        )
        self.session.add(account)
        self.session.flush()
        if fail_after_account:
            raise RuntimeError("INJECTED_FAILURE_AFTER_ACCOUNT")

        subscription = BillingSubscription(
            account_id=account.account_id,
            plan_version_id=plan_version.plan_version_id,
            status="ACTIVE",
            contracted_price=spec.contracted_price,
            currency=spec.currency,
            billing_cycle="MONTHLY",
        )
        self.session.add(subscription)
        self.session.flush()
        self.session.add(BillingSubscriptionCompany(subscription_id=subscription.subscription_id, cliente_id=spec.cliente_id, status="ACTIVE"))
        reason = f"{DECISION_SOURCE}; decision_date={spec.decision_date}; nfe_quota_policy={NFE_POLICY}"
        self.session.add(BillingSubscriptionOverride(subscription_id=subscription.subscription_id, key="MAX_USERS", value=str(spec.current_users), reason=reason))
        self.session.add(BillingSubscriptionOverride(subscription_id=subscription.subscription_id, key="MAX_COMPANIES", value=str(spec.current_companies), reason=reason))
        self.session.flush()
        return MigrationResult(spec.cliente_id, "APPLY", "MIGRATED", account.account_id, subscription.subscription_id, (), (), ("LEGACY_QUOTA_PRESERVED", "CLOSED_TO_NEW_SUBSCRIPTIONS"))

    def _existing(self, spec: LegacyMigrationSpec) -> tuple[int, int] | None:
        has_shadow = self.session.execute(text("""
            SELECT COUNT(*) = 5 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN (
                'billing_accounts', 'billing_subscriptions',
                'billing_subscription_companies', 'billing_plan_versions',
                'billing_plans'
            )
        """)).scalar()
        if not has_shadow:
            return None
        row = self.session.execute(text("""
            SELECT a.account_id, s.subscription_id
            FROM billing_accounts a
            JOIN billing_subscriptions s ON s.account_id = a.account_id AND s.status = 'ACTIVE'
            JOIN billing_subscription_companies sc ON sc.subscription_id = s.subscription_id AND sc.status = 'ACTIVE'
            JOIN billing_plan_versions v ON v.plan_version_id = s.plan_version_id AND v.version_code = :version_code
            WHERE a.name = :account_name AND sc.cliente_id = :cliente_id
        """), {"version_code": VERSION_CODE, "account_name": f"LEGACY_GRANDFATHER_CLIENT_{spec.cliente_id}", "cliente_id": spec.cliente_id}).first()
        return (row[0], row[1]) if row else None

    def _ensure_plan_version(self) -> BillingPlanVersion:
        version = self.session.query(BillingPlanVersion).filter_by(version_code=VERSION_CODE).first()
        if version:
            return version
        plan = self.session.query(BillingPlan).filter_by(code=PLAN_CODE).first()
        if not plan:
            plan = BillingPlan(code=PLAN_CODE, name="Legacy Grandfathered R$60", active=False, display_order=99)
            self.session.add(plan)
            self.session.flush()
        version = BillingPlanVersion(plan_id=plan.plan_id, version_code=VERSION_CODE, price=Decimal("60.00"), currency="BRL", status="ACTIVE")
        self.session.add(version)
        self.session.flush()
        feature_specs = (
            ("MAX_USERS", "Máximo de usuários", "LIMITED", None),
            ("MAX_COMPANIES", "Máximo de empresas", "LIMITED", None),
            ("NFE_MONTHLY", "NF-e mensal legacy", "CONTRACTUAL", None),
            ("AI_INSIGHTS_CENTER", "Central de Insights", "DISABLED", None),
        )
        for key, name, limit_type, limit_value in feature_specs:
            feature = self.session.query(BillingFeature).filter_by(key=key).first()
            if not feature:
                feature = BillingFeature(key=key, name=name, description="Legacy migration feature", status="ROADMAP" if key == "AI_INSIGHTS_CENTER" else "AVAILABLE")
                self.session.add(feature)
                self.session.flush()
            self.session.add(BillingPlanFeature(
                plan_version_id=version.plan_version_id,
                feature_id=feature.feature_id,
                enabled=key != "AI_INSIGHTS_CENTER",
                access_level="LEGACY_PRESERVED" if key == "NFE_MONTHLY" else "STANDARD",
                limit_type=limit_type,
                limit_value=limit_value,
                metadata_json='{"policy":"LEGACY_PRESERVED","closed_to_new_subscriptions":true}' if key == "NFE_MONTHLY" else None,
            ))
        self.session.flush()
        return version

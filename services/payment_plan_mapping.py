"""Mapeamento explícito de PlanVersion para planos de provider por ambiente."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text

from database.billing_shadow_models import BillingPlanVersion, PaymentProviderPlanMapping


@dataclass(frozen=True)
class ProviderPlanMapping:
    billing_plan_version_id: int
    plan_code: str
    provider: str
    provider_plan_id: str
    environment: str
    currency: str
    amount: Decimal
    status: str = "ACTIVE"


class PaymentPlanMappingService:
    def __init__(self, db):
        self.db = db

    def register_test_mapping(self, *, plan_code: str, provider_plan_id: str, amount: Decimal, currency: str = "BRL") -> ProviderPlanMapping:
        # Note: provider_plan_id should be the real ID from Mercado Pago.
        # The environment column provides isolation; TEST_ prefix is redundant and breaks webhook validation.
        if not provider_plan_id:
            raise ValueError("PROVIDER_PLAN_ID_REQUIRED")
        version = self.db.query(BillingPlanVersion).filter_by(version_code=plan_code, status="ACTIVE").first()
        if version is None:
            raise ValueError("PLAN_VERSION_NOT_AVAILABLE")
        if plan_code in {"LEGACY_60_V1", "ENTERPRISE_V1"}:
            raise ValueError("PLAN_NOT_ELIGIBLE_FOR_TEST_CHECKOUT")
        if Decimal(str(version.price)) != Decimal(str(amount)):
            raise ValueError("PAYMENT_AMOUNT_MISMATCH")
        if version.currency != currency:
            raise ValueError("PAYMENT_CURRENCY_MISMATCH")
        existing = self.db.query(PaymentProviderPlanMapping).filter_by(
            billing_plan_version_id=version.plan_version_id,
            provider="MERCADOPAGO", environment="TEST",
        ).first()
        if existing:
            if existing.provider_plan_id != provider_plan_id or Decimal(str(existing.amount)) != Decimal(str(amount)) or existing.currency != currency:
                raise ValueError("PAYMENT_MAPPING_MISMATCH")
            return ProviderPlanMapping(version.plan_version_id, plan_code, existing.provider, existing.provider_plan_id, existing.environment, existing.currency, existing.amount, existing.status)
        row = PaymentProviderPlanMapping(
            billing_plan_version_id=version.plan_version_id,
            provider="MERCADOPAGO", provider_plan_id=provider_plan_id,
            environment="TEST", currency=currency, amount=amount, status="ACTIVE",
        )
        self.db.add(row)
        self.db.flush()
        return ProviderPlanMapping(version.plan_version_id, plan_code, row.provider, row.provider_plan_id, row.environment, row.currency, row.amount, row.status)

    def resolve(self, *, plan_code: str, provider: str = "MERCADOPAGO", environment: str = "TEST") -> ProviderPlanMapping:
        if environment not in {"TEST", "PRODUCTION"}:
            raise ValueError("PAYMENT_ENVIRONMENT_INVALID")
        if provider != "MERCADOPAGO":
            raise ValueError("PAYMENT_PROVIDER_UNSUPPORTED")
        version = self.db.query(BillingPlanVersion).filter_by(version_code=plan_code, status="ACTIVE").first()
        if version is None:
            raise ValueError("PLAN_VERSION_NOT_AVAILABLE")
        if plan_code == "LEGACY_60_V1":
            raise ValueError("PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS")
        row = self.db.execute(text("""
            SELECT m.billing_plan_version_id, v.version_code, m.provider,
                   m.provider_plan_id, m.environment, m.currency, m.amount, m.status
            FROM payment_provider_plan_mappings m
            JOIN billing_plan_versions v ON v.plan_version_id=m.billing_plan_version_id
            WHERE v.version_code=:plan_code AND m.provider=:provider AND m.environment=:environment AND m.status='ACTIVE'
        """), {"plan_code": plan_code, "provider": provider, "environment": environment}).first()
        if row is None:
            raise ValueError("PROVIDER_PLAN_MAPPING_NOT_FOUND")
        if row.currency != version.currency:
            raise ValueError("PAYMENT_CURRENCY_MISMATCH")
        if Decimal(str(row.amount)) != Decimal(str(version.price)):
            raise ValueError("PAYMENT_AMOUNT_MISMATCH")
        return ProviderPlanMapping(*row)

    def validate_webhook_mapping(self, *, plan_code: str, provider_plan_id: str, environment: str, amount: Decimal, currency: str) -> ProviderPlanMapping:
        mapping = self.resolve(plan_code=plan_code, environment=environment)
        if mapping.provider_plan_id != provider_plan_id:
            raise ValueError("PAYMENT_MAPPING_MISMATCH")
        if mapping.currency != currency:
            raise ValueError("PAYMENT_CURRENCY_MISMATCH")
        if mapping.amount != amount:
            raise ValueError("PAYMENT_AMOUNT_MISMATCH")
        return mapping

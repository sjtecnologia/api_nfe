"""Preparação transacional de novas assinaturas comerciais.

Nenhuma rota chama este serviço nesta fase; checkout e cobrança permanecem OFF.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from database.billing_shadow_models import (
    BillingAccount,
    BillingPlanVersion,
    BillingSubscription,
    BillingSubscriptionCompany,
)

LEGACY_VERSION_CODE = "LEGACY_60_V1"


@dataclass(frozen=True)
class NewSubscriptionSpec:
    cliente_id: int
    plan_version_code: str
    contracted_price: Decimal | None = None
    currency: str = "BRL"


class CommercialSubscriptionService:
    """Cria assinatura futura somente quando chamado por fluxo aprovado."""

    def __init__(self, db):
        self.db = db

    def create_new_subscription(self, spec: NewSubscriptionSpec) -> BillingSubscription:
        if spec.plan_version_code == LEGACY_VERSION_CODE:
            raise ValueError("PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS")
        version = self.db.query(BillingPlanVersion).filter_by(
            version_code=spec.plan_version_code,
            status="ACTIVE",
        ).first()
        if version is None:
            raise ValueError("PLAN_VERSION_NOT_AVAILABLE")
        price = spec.contracted_price if spec.contracted_price is not None else version.price
        account = BillingAccount(
            name=f"COMMERCIAL_CLIENT_{spec.cliente_id}",
            description="Account created by approved commercial onboarding",
            status="ACTIVE",
        )
        self.db.add(account)
        self.db.flush()
        subscription = BillingSubscription(
            account_id=account.account_id,
            plan_version_id=version.plan_version_id,
            status="ACTIVE",
            contracted_price=price,
            currency=spec.currency,
            billing_cycle="MONTHLY",
        )
        self.db.add(subscription)
        self.db.flush()
        self.db.add(BillingSubscriptionCompany(
            subscription_id=subscription.subscription_id,
            cliente_id=spec.cliente_id,
            status="ACTIVE",
        ))
        self.db.flush()
        return subscription

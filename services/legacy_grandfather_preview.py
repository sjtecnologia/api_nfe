"""Preview read-only da decisão comercial de grandfathering.

A decisão é administrativa e não altera assinaturas, preços, Billing ou fiscal.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

APPROVED_LEGACY_CLIENTS = {11, 13}
UNCHANGED_CLIENTS = {5, 12, 14}
LEGACY_PLAN_CODE = "LEGACY_60_V1"
DECISION_SOURCE = "MANUAL_BUSINESS_DECISION"
DECISION_REASON = "Existing real customer explicitly approved for grandfathering by EmiteMax administration."


@dataclass(frozen=True)
class GrandfatherPreview:
    cliente_id: int
    decision: str
    current_status: str
    current_plan: str | None
    subscription_id: int | None
    subscription_start: date | None
    current_users: int
    current_companies: int
    contracted_price: Decimal | None
    currency: str
    price_source: str
    price_confidence: str
    grandfathered: bool
    closed_to_new_subscriptions: bool
    nfe_quota_policy: str
    user_capacity_policy: str
    company_capacity_policy: str
    feature_policy: str
    historical_contract_evidence: str
    decision_source: str | None
    decision_date: str | None
    decision_reason: str | None
    notes_required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "cliente_id": self.cliente_id,
            "decision": self.decision,
            "current_status": self.current_status,
            "current_plan": self.current_plan,
            "subscription_id": self.subscription_id,
            "subscription_start": self.subscription_start.isoformat() if self.subscription_start else None,
            "current_users": self.current_users,
            "current_companies": self.current_companies,
            "contracted_price": str(self.contracted_price) if self.contracted_price is not None else None,
            "currency": self.currency,
            "price_source": self.price_source,
            "price_confidence": self.price_confidence,
            "grandfathered": self.grandfathered,
            "closed_to_new_subscriptions": self.closed_to_new_subscriptions,
            "nfe_quota_policy": self.nfe_quota_policy,
            "user_capacity_policy": self.user_capacity_policy,
            "company_capacity_policy": self.company_capacity_policy,
            "feature_policy": self.feature_policy,
            "historical_contract_evidence": self.historical_contract_evidence,
            "decision_source": self.decision_source,
            "decision_date": self.decision_date,
            "decision_reason": self.decision_reason,
            "notes_required": self.notes_required,
        }


def build_preview(*, cliente_id: int, current_status: str, current_plan: str | None,
                  subscription_id: int | None, subscription_start: date | None,
                  current_users: int, current_companies: int,
                  decision_date: str) -> GrandfatherPreview:
    if cliente_id in APPROVED_LEGACY_CLIENTS:
        return GrandfatherPreview(
            cliente_id=cliente_id,
            decision="GRANDFATHER_READY",
            current_status=current_status,
            current_plan=current_plan,
            subscription_id=subscription_id,
            subscription_start=subscription_start,
            current_users=current_users,
            current_companies=current_companies,
            contracted_price=Decimal("60.00"),
            currency="BRL",
            price_source=DECISION_SOURCE,
            price_confidence="CONFIRMED",
            grandfathered=True,
            closed_to_new_subscriptions=True,
            nfe_quota_policy="LEGACY_PRESERVED",
            user_capacity_policy="PRESERVE_CURRENT",
            company_capacity_policy="PRESERVE_CURRENT",
            feature_policy="PRESERVE_EXISTING_ACCESS",
            historical_contract_evidence="NOT_FOUND",
            decision_source=DECISION_SOURCE,
            decision_date=decision_date,
            decision_reason=DECISION_REASON,
            notes_required=False,
        )
    if cliente_id in UNCHANGED_CLIENTS:
        return GrandfatherPreview(
            cliente_id=cliente_id,
            decision="UNCHANGED_NO_COMMERCIAL_MIGRATION",
            current_status=current_status,
            current_plan=current_plan,
            subscription_id=subscription_id,
            subscription_start=subscription_start,
            current_users=current_users,
            current_companies=current_companies,
            contracted_price=None,
            currency="BRL",
            price_source="NOT_ASSIGNED",
            price_confidence="UNKNOWN",
            grandfathered=False,
            closed_to_new_subscriptions=False,
            nfe_quota_policy="UNCHANGED",
            user_capacity_policy="UNCHANGED",
            company_capacity_policy="UNCHANGED",
            feature_policy="UNCHANGED",
            historical_contract_evidence="NOT_REVIEWED",
            decision_source=None,
            decision_date=None,
            decision_reason=None,
            notes_required=True,
        )
    raise ValueError(f"CLIENT_NOT_IN_APPROVED_SCOPE:{cliente_id}")

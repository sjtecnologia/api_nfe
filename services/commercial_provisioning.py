"""Preview de provisionamento comercial; escrita futura ainda não habilitada."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProvisioningPreview:
    plan_version_code: str
    contracted_price: str
    currency: str
    objects_to_create: tuple[str, ...]
    status: str = "DRY_RUN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_version_code": self.plan_version_code,
            "contracted_price": self.contracted_price,
            "currency": self.currency,
            "objects_to_create": list(self.objects_to_create),
            "status": self.status,
        }


class CommercialProvisioningService:
    """Produz plano de provisionamento sem persistir entidade definitiva."""

    def preview(self, *, plan_version_code: str, contracted_price: str, currency: str = "BRL") -> ProvisioningPreview:
        if plan_version_code == "LEGACY_60_V1":
            raise ValueError("PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS")
        return ProvisioningPreview(
            plan_version_code=plan_version_code,
            contracted_price=contracted_price,
            currency=currency,
            objects_to_create=("Cliente", "User", "UserClient", "BillingAccount", "BillingSubscription", "BillingSubscriptionCompany"),
        )

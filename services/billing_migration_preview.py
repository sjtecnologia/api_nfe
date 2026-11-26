"""Preview read-only da migração comercial legacy.

Este módulo produz snapshots para revisão humana. Ele não cria, atualiza ou
remove assinaturas, planos, vínculos, eventos ou qualquer registro fiscal.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from database.billing_shadow_models import BillingSubscription, BillingSubscriptionCompany
from database.models import AssinaturaCliente, PlanoNFe

LEGACY_PLAN_CODE = "LEGACY_START_V1"
LEGACY_POLICY_REVIEW_REQUIRED = "LEGACY_POLICY_REVIEW_REQUIRED"


@dataclass(frozen=True)
class MigrationPreview:
    cliente_id: int
    legacy_plan: str | None
    contracted_price: float | None
    billing_account_id: int | None
    suggested_plan: str
    grandfathered: bool
    reason: str
    confidence: str
    action: str
    migration_state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cliente_id": self.cliente_id,
            "legacy_plan": self.legacy_plan,
            "contracted_price": self.contracted_price,
            "billing_account_id": self.billing_account_id,
            "suggested_plan": self.suggested_plan,
            "grandfathered": self.grandfathered,
            "reason": self.reason,
            "confidence": self.confidence,
            "action": self.action,
            "migration_state": self.migration_state,
        }


class BillingMigrationPreviewService:
    """Audita legado e shadow sem persistir estado de migração."""

    def __init__(self, db):
        self.db = db

    def preview_company(self, cliente_id: int) -> MigrationPreview:
        legacy = self.db.query(AssinaturaCliente).filter(
            AssinaturaCliente.cliente_id == cliente_id,
            AssinaturaCliente.status == "ATIVA",
        ).order_by(AssinaturaCliente.updated_at.desc(), AssinaturaCliente.assinatura_id.desc()).first()
        legacy_plan = self.db.query(PlanoNFe).filter_by(plano_id=legacy.plano_id).first() if legacy else None

        shadow = self.db.query(BillingSubscription).filter(
            BillingSubscription.status == "ACTIVE",
        ).order_by(BillingSubscription.updated_at.desc(), BillingSubscription.subscription_id.desc()).all()
        shadow = next(
            (subscription for subscription in shadow if any(
                link.cliente_id == cliente_id and link.status == "ACTIVE"
                for link in subscription.companies
            )),
            None,
        )

        if legacy is None:
            return MigrationPreview(
                cliente_id=cliente_id,
                legacy_plan=None,
                contracted_price=self._price(shadow.contracted_price) if shadow else None,
                billing_account_id=shadow.account_id if shadow else None,
                suggested_plan=LEGACY_POLICY_REVIEW_REQUIRED,
                grandfathered=False,
                reason="NO_ACTIVE_LEGACY_SUBSCRIPTION",
                confidence="LOW",
                action="REVIEW_REQUIRED",
                migration_state="REVIEW_REQUIRED",
            )

        plan_name = (legacy_plan.nome if legacy_plan else "").strip()
        normalized_name = plan_name.casefold()
        explicit_legacy = any(marker in normalized_name for marker in ("legacy", "básico", "basico"))
        approximate_public_price = legacy_plan and legacy_plan.valor_mensal is not None and abs(float(legacy_plan.valor_mensal) - 60.0) < 0.01
        shadow_price = self._price(shadow.contracted_price) if shadow else None
        contracted_price = shadow_price

        if shadow and shadow_price is not None:
            reason = "ACTIVE_LEGACY_AND_SHADOW_CONTRACT_PRICE"
            confidence = "HIGH" if explicit_legacy else "MEDIUM"
            suggested_plan = LEGACY_PLAN_CODE
        elif explicit_legacy:
            reason = "ACTIVE_LEGACY_PLAN_WITHOUT_CONTRACTED_PRICE"
            confidence = "MEDIUM"
            suggested_plan = LEGACY_PLAN_CODE
        elif approximate_public_price:
            reason = "PUBLIC_PLAN_PRICE_APPROXIMATES_60_BUT_CONTRACT_PRICE_UNKNOWN"
            confidence = "MEDIUM"
            suggested_plan = LEGACY_POLICY_REVIEW_REQUIRED
        else:
            reason = "ACTIVE_LEGACY_PLAN_REQUIRES_CONTRACT_REVIEW"
            confidence = "LOW"
            suggested_plan = LEGACY_POLICY_REVIEW_REQUIRED

        return MigrationPreview(
            cliente_id=cliente_id,
            legacy_plan=plan_name or None,
            contracted_price=contracted_price,
            billing_account_id=shadow.account_id if shadow else None,
            suggested_plan=suggested_plan,
            grandfathered=True,
            reason=reason,
            confidence=confidence,
            action="MANUAL_REVIEW",
            migration_state="GRANDFATHERED" if suggested_plan == LEGACY_PLAN_CODE else "REVIEW_REQUIRED",
        )

    def active_legacy_previews(self) -> list[MigrationPreview]:
        client_ids = self.db.query(AssinaturaCliente.cliente_id).filter(
            AssinaturaCliente.status == "ATIVA",
        ).distinct().all()
        return [self.preview_company(int(row[0])) for row in client_ids]

    @staticmethod
    def _price(value: Decimal | float | None) -> float | None:
        return float(value) if value is not None else None

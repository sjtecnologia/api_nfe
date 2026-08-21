"""Resolvers comerciais read-only da Fase 4.6C.

Nenhum resultado deste módulo é usado para bloquear emissão ou qualquer fluxo
existente. A fonte é sempre informada para permitir auditoria.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from database.billing_shadow_models import (
    BillingFeature,
    BillingPlanFeature,
    BillingSubscription,
    BillingSubscriptionCompany,
    BillingSubscriptionOverride,
)
from database.models import AssinaturaCliente, PlanoNFe, UserClient

LIMIT_TYPES = {"DISABLED", "ENABLED", "LIMITED", "UNMETERED_WITH_FAIR_USE", "CONTRACTUAL"}
SOURCES = {"PLAN", "OVERRIDE", "LEGACY", "DEFAULT"}


@dataclass(frozen=True)
class ShadowCapability:
    used: Optional[int]
    limit: Optional[int]
    remaining: Optional[int]
    status: str
    source: str


class LegacySubscriptionAdapter:
    """Lê a assinatura legada sem criar, alterar ou migrar registros."""

    def __init__(self, db):
        self.db = db

    def get_for_company(self, cliente_id: int) -> Optional[dict]:
        subscription = self.db.query(AssinaturaCliente).filter(
            AssinaturaCliente.cliente_id == cliente_id,
            AssinaturaCliente.status == "ATIVA",
        ).order_by(AssinaturaCliente.updated_at.desc()).first()
        if not subscription:
            return None
        plan = self.db.query(PlanoNFe).filter(PlanoNFe.plano_id == subscription.plano_id).first()
        if not plan:
            return None
        return {
            "source": "LEGACY",
            "cliente_id": cliente_id,
            "legacy_assinatura_id": subscription.assinatura_id,
            "legacy_plano_id": plan.plano_id,
            "plan_code": "LEGACY_START_V1" if any(
                marker in plan.nome.lower() for marker in ("básico", "basico")
            ) else plan.nome,
            "status": subscription.status,
            "contracted_price": None,
            "nfe_consumed": subscription.nfes_consumidas,
            "nfe_limit": plan.quantidade_nfes,
        }


class EntitlementResolver:
    """Resolve features shadow sem aplicar enforcement."""

    def __init__(self, db):
        self.db = db

    def resolve(self, subscription_id: int, feature_key: str) -> dict:
        row = self.db.query(BillingPlanFeature, BillingFeature).join(
            BillingFeature, BillingPlanFeature.feature_id == BillingFeature.feature_id
        ).join(
            BillingSubscription, BillingSubscription.plan_version_id == BillingPlanFeature.plan_version_id
        ).filter(
            BillingSubscription.subscription_id == subscription_id,
            BillingFeature.key == feature_key,
        ).first()
        if not row:
            return {"enabled": False, "limit_type": "DISABLED", "limit_value": None, "source": "DEFAULT"}
        plan_feature, feature = row
        if feature.status == "ROADMAP":
            return {"enabled": False, "limit_type": "DISABLED", "limit_value": None, "source": "PLAN", "reason": "ROADMAP"}
        if plan_feature.limit_type not in LIMIT_TYPES:
            raise ValueError(f"Tipo de limite desconhecido: {plan_feature.limit_type}")
        return {
            "enabled": bool(plan_feature.enabled),
            "limit_type": plan_feature.limit_type,
            "limit_value": plan_feature.limit_value,
            "source": "PLAN",
        }


class CapacityResolver:
    """Calcula capacidade shadow de empresas/usuários; nunca bloqueia."""

    def __init__(self, db):
        self.db = db

    def companies(self, subscription_id: int) -> ShadowCapability:
        subscription = self.db.query(BillingSubscription).filter_by(subscription_id=subscription_id).first()
        if not subscription:
            return ShadowCapability(0, 0, 0, "UNKNOWN", "DEFAULT")
        used = self.db.query(BillingSubscriptionCompany).filter_by(
            subscription_id=subscription_id, status="ACTIVE"
        ).count()
        limit = self._override_or_feature(subscription, "MAX_COMPANIES")
        return self._capability(used, limit, "PLAN")

    def users(self, subscription_id: int) -> ShadowCapability:
        subscription = self.db.query(BillingSubscription).filter_by(subscription_id=subscription_id).first()
        if not subscription:
            return ShadowCapability(0, 0, 0, "UNKNOWN", "DEFAULT")
        company_ids = [link.cliente_id for link in subscription.companies if link.status == "ACTIVE"]
        used = self.db.query(UserClient.user_id).filter(UserClient.client_id.in_(company_ids)).distinct().count() if company_ids else 0
        limit = self._override_or_feature(subscription, "MAX_USERS")
        return self._capability(used, limit, "PLAN")

    def _override_or_feature(self, subscription, key):
        for override in subscription.overrides:
            if override.key == key and (override.expires_at is None or override.expires_at >= datetime.utcnow()):
                return int(override.value) if override.value.isdigit() else override.value
        for plan_feature in subscription.plan_version.features:
            feature = plan_feature.feature
            if feature.key == key:
                if plan_feature.limit_type in {"UNMETERED_WITH_FAIR_USE", "CONTRACTUAL"}:
                    return plan_feature.limit_type
                return plan_feature.limit_value
        return 0

    @staticmethod
    def _capability(used, limit, source):
        if limit in {"UNMETERED_WITH_FAIR_USE", "CONTRACTUAL"}:
            return ShadowCapability(used, None, None, limit, source)
        limit = int(limit or 0)
        return ShadowCapability(used, limit, max(limit - used, 0), "OK" if used <= limit else "OVER_LIMIT", source)

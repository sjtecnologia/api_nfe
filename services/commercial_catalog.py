"""Catálogo comercial canônico para leitura e UX informativa.

Este catálogo não cobra, não altera subscriptions e não aplica enforcement.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class CommercialPlan:
    code: str
    version_code: str
    name: str
    price: Decimal | None
    currency: str
    companies: int | None
    users: int | None
    nfe_policy: str
    nfce_policy: str
    nfse_policy: str
    status: str
    availability: str
    closed_to_new_subscriptions: bool = False
    features: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["price"] = str(self.price) if self.price is not None else None
        value["features"] = list(self.features)
        value["notes"] = list(self.notes)
        return value


FEATURE_CATALOG: tuple[dict[str, str], ...] = (
    {"key": "NFE", "name": "NF-e", "status": "AVAILABLE"},
    {"key": "NFCE", "name": "NFC-e", "status": "AVAILABLE"},
    {"key": "NFSE", "name": "NFS-e", "status": "AVAILABLE"},
    {"key": "INVENTORY", "name": "Estoque", "status": "AVAILABLE"},
    {"key": "CASH_FLOW", "name": "Fluxo de caixa", "status": "AVAILABLE"},
    {"key": "REPORTS", "name": "Relatórios", "status": "AVAILABLE"},
    {"key": "MULTI_COMPANY", "name": "Multiempresa", "status": "AVAILABLE"},
    {"key": "MULTI_USER", "name": "Multiusuário", "status": "AVAILABLE"},
    {"key": "AI_NCM", "name": "Sugestão de NCM", "status": "PARTIAL"},
    {"key": "AI_CFOP", "name": "Sugestão de CFOP", "status": "PARTIAL"},
    {"key": "AI_PRODUCT_DESCRIPTION", "name": "Descrição comercial com IA", "status": "AVAILABLE"},
    {"key": "AI_SALES_ANALYSIS", "name": "Análise inteligente de vendas", "status": "AVAILABLE"},
    {"key": "API_ACCESS", "name": "API", "status": "PARTIAL"},
    {"key": "IBS_CBS", "name": "IBS/CBS", "status": "PARTIAL"},
    {"key": "AI_INSIGHTS_CENTER", "name": "Central de Insights", "status": "ROADMAP"},
)

PLANS: tuple[CommercialPlan, ...] = (
    CommercialPlan(
        "START", "START_V1", "Start", Decimal("60.00"), "BRL", 1, 1,
        "50 NF-e/mês", "50 NFC-e/mês", "30 NFS-e/mês", "AVAILABLE", "NEW_SALES",
        features=("NF-e", "NFC-e", "NFS-e", "Estoque", "Fluxo de caixa", "Relatórios"),
    ),
    CommercialPlan(
        "ESSENCIAL", "ESSENCIAL_V1", "Essencial", Decimal("99.00"), "BRL", 1, 2,
        "200 NF-e/mês", "200 NFC-e/mês", "100 NFS-e/mês", "AVAILABLE", "NEW_SALES",
        features=("NF-e", "NFC-e", "NFS-e", "Estoque", "Fluxo de caixa", "Relatórios", "API"),
    ),
    CommercialPlan(
        "PROFISSIONAL", "PROFISSIONAL_V1", "Profissional", Decimal("169.00"), "BRL", 2, 5,
        "500 NF-e/mês", "500 NFC-e/mês", "300 NFS-e/mês", "AVAILABLE", "NEW_SALES",
        features=("NF-e", "NFC-e", "NFS-e", "Estoque", "Fluxo de caixa", "Relatórios", "API", "Análise inteligente de vendas"),
    ),
    CommercialPlan(
        "PREMIUM", "PREMIUM_V1", "Premium", Decimal("299.00"), "BRL", 5, 10,
        "Sem limite mensal fixo, com uso justo", "Sem limite mensal fixo, com uso justo", "Sem limite mensal fixo, com uso justo", "AVAILABLE", "NEW_SALES",
        features=("Todos os recursos disponíveis", "Análise inteligente de vendas", "API"),
        notes=("Uso sujeito à política de uso justo.", "Capacidade máxima de 5 empresas e 10 usuários."),
    ),
    CommercialPlan(
        "ENTERPRISE", "ENTERPRISE_V1", "Enterprise", None, "BRL", None, None,
        "Contratual", "Contratual", "Contratual", "AVAILABLE", "CONTACT_SALES",
        features=("Recursos e capacidades definidos em contrato",),
        notes=("Fale com a equipe comercial.",),
    ),
    CommercialPlan(
        "LEGACY_60", "LEGACY_60_V1", "Legacy — Condição preservada", Decimal("60.00"), "BRL", None, None,
        "Condição preservada", "Condição preservada", "Condição preservada", "LEGACY_ONLY", "EXISTING_CUSTOMERS",
        closed_to_new_subscriptions=True,
        features=("Acesso existente preservado",),
        notes=("Não disponível para novas contratações.", "Novos recursos exigem decisão comercial própria."),
    ),
)


def get_catalog() -> dict[str, Any]:
    return {
        "plans": [plan.to_dict() for plan in PLANS],
        "features": [dict(feature) for feature in FEATURE_CATALOG],
        "new_sales_version_codes": [plan.version_code for plan in PLANS if plan.availability == "NEW_SALES"],
    }


def find_plan(version_code: str | None) -> CommercialPlan | None:
    return next((plan for plan in PLANS if plan.version_code == version_code), None)


def classify_usage(used: int, limit: int | None) -> str | None:
    if limit is None:
        return None
    percentage = (used / limit) if limit else 1
    if percentage >= 1:
        return "LIMIT_REACHED"
    if percentage >= 0.8:
        return "APPROACHING_LIMIT"
    return "NORMAL"

from decimal import Decimal
from pathlib import Path

from services.commercial_catalog import FEATURE_CATALOG, find_plan, get_catalog


def test_catalog_has_only_canonical_new_sales_plans():
    catalog = get_catalog()
    assert catalog["new_sales_version_codes"] == [
        "START_V1", "ESSENCIAL_V1", "PROFISSIONAL_V1", "PREMIUM_V1"
    ]
    assert "LEGACY_60_V1" not in catalog["new_sales_version_codes"]


def test_plan_values_match_approved_catalog():
    assert find_plan("START_V1").price == Decimal("60.00")
    assert find_plan("START_V1").companies == 1
    assert find_plan("START_V1").users == 1
    assert find_plan("START_V1").nfe_policy == "50 NF-e/mês"
    assert find_plan("ESSENCIAL_V1").users == 2
    assert find_plan("PROFISSIONAL_V1").companies == 2
    assert find_plan("PREMIUM_V1").companies == 5
    assert "ilimit" not in " ".join(find_plan("PREMIUM_V1").notes).lower()
    assert find_plan("ENTERPRISE_V1").price is None


def test_legacy_plan_is_preserved_and_closed():
    legacy = find_plan("LEGACY_60_V1")
    assert legacy.closed_to_new_subscriptions is True
    assert legacy.availability == "EXISTING_CUSTOMERS"
    assert legacy.nfe_policy == "Condição preservada"
    assert legacy.price == Decimal("60.00")


def test_feature_catalog_has_explicit_statuses():
    statuses = {feature["key"]: feature["status"] for feature in FEATURE_CATALOG}
    assert statuses["AI_INSIGHTS_CENTER"] == "ROADMAP"
    assert statuses["NFE"] == "AVAILABLE"
    assert statuses["API_ACCESS"] == "PARTIAL"


def test_legacy_plan_page_hides_internal_metadata():
    template = (Path(__file__).parents[1] / "templates/admin/billing/meu_plano.html").read_text()
    assert "Condição comercial preservada" in template
    assert "Sem novo limite aplicado" in template
    assert "LEGACY_60_V1" not in template
    assert "MANUAL_BUSINESS_DECISION" not in template

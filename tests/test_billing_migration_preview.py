from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.billing_migration_preview import BillingMigrationPreviewService


def _db_for(legacy, plan, shadows):
    db = MagicMock()
    legacy_query = MagicMock()
    legacy_query.filter.return_value.order_by.return_value.first.return_value = legacy
    plan_query = MagicMock()
    plan_query.filter_by.return_value = plan_query
    plan_query.first.return_value = plan
    shadow_query = MagicMock()
    shadow_query.filter.return_value.order_by.return_value.all.return_value = shadows
    clients_query = MagicMock()
    clients_query.filter.return_value.distinct.return_value.all.return_value = [(7,)]
    db.query.side_effect = [legacy_query, plan_query, shadow_query]
    return db


def test_approximate_60_without_contract_price_requires_manual_review():
    legacy = SimpleNamespace(cliente_id=7, assinatura_id=10, plano_id=2, status="ATIVA", updated_at=datetime.utcnow())
    plan = SimpleNamespace(plano_id=2, nome="Pacote Básico", valor_mensal=Decimal("60.00"), quantidade_nfes=50)
    db = _db_for(legacy, plan, [])

    preview = BillingMigrationPreviewService(db).preview_company(7)

    assert preview.suggested_plan == "LEGACY_START_V1"
    assert preview.confidence == "MEDIUM"
    assert preview.grandfathered is True
    assert preview.contracted_price is None
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_shadow_contracted_price_is_preserved_without_migration():
    legacy = SimpleNamespace(cliente_id=7, assinatura_id=10, plano_id=2, status="ATIVA", updated_at=datetime.utcnow())
    plan = SimpleNamespace(plano_id=2, nome="Pacote Básico", valor_mensal=Decimal("60.00"), quantidade_nfes=50)
    shadow = SimpleNamespace(
        subscription_id=20,
        account_id=30,
        contracted_price=Decimal("60.00"),
        status="ACTIVE",
        updated_at=datetime.utcnow(),
        companies=[SimpleNamespace(cliente_id=7, status="ACTIVE")],
    )
    db = _db_for(legacy, plan, [shadow])

    preview = BillingMigrationPreviewService(db).preview_company(7)

    assert preview.suggested_plan == "LEGACY_START_V1"
    assert preview.confidence == "HIGH"
    assert preview.contracted_price == 60.0
    assert preview.billing_account_id == 30
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_no_legacy_subscription_is_unknown_and_fail_open():
    db = MagicMock()
    legacy_query = MagicMock()
    legacy_query.filter.return_value.order_by.return_value.first.return_value = None
    shadow_query = MagicMock()
    shadow_query.filter.return_value.order_by.return_value.all.return_value = []
    db.query.side_effect = [legacy_query, shadow_query]

    preview = BillingMigrationPreviewService(db).preview_company(7)

    assert preview.suggested_plan == "LEGACY_POLICY_REVIEW_REQUIRED"
    assert preview.confidence == "LOW"
    assert preview.reason == "NO_ACTIVE_LEGACY_SUBSCRIPTION"
    assert preview.action == "REVIEW_REQUIRED"
    db.add.assert_not_called()
    db.commit.assert_not_called()

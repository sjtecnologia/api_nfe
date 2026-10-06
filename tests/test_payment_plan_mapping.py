from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.payment_plan_mapping import PaymentPlanMappingService


def _version(code="START_V1", price="60.00"):
    return SimpleNamespace(plan_version_id=1, version_code=code, price=Decimal(price), currency="BRL", status="ACTIVE")


def test_test_mapping_requires_explicit_test_id_and_is_not_legacy():
    db = MagicMock()
    query = MagicMock()
    query.filter_by.return_value = query
    query.first.return_value = _version()
    db.query.return_value = query
    db.execute.return_value.first.return_value = None
    service = PaymentPlanMappingService(db)
    with pytest.raises(ValueError, match="PROVIDER_PLAN_ID_REQUIRED"):
        service.register_test_mapping(plan_code="START_V1", provider_plan_id="", amount=Decimal("60.00"))
    with pytest.raises(ValueError, match="PLAN_NOT_ELIGIBLE_FOR_TEST_CHECKOUT"):
        service.register_test_mapping(plan_code="LEGACY_60_V1", provider_plan_id="production-id", amount=Decimal("60.00"))


def test_missing_mapping_is_explicit_error():
    db = MagicMock()
    query = MagicMock()
    query.filter_by.return_value = query
    query.first.return_value = _version()
    db.query.return_value = query
    db.execute.return_value.first.return_value = None
    with pytest.raises(ValueError, match="PROVIDER_PLAN_MAPPING_NOT_FOUND"):
        PaymentPlanMappingService(db).resolve(plan_code="START_V1", environment="TEST")


def test_amount_and_currency_mismatch_are_rejected():
    db = MagicMock()
    query = MagicMock()
    query.filter_by.return_value = query
    query.first.return_value = _version()
    db.query.return_value = query
    db.execute.return_value.first.return_value = SimpleNamespace(
        billing_plan_version_id=1, version_code="START_V1", provider="MERCADOPAGO",
        provider_plan_id="TEST_START", environment="TEST", currency="BRL",
        amount=Decimal("61.00"), status="ACTIVE",
    )
    with pytest.raises(ValueError, match="PAYMENT_AMOUNT_MISMATCH"):
        PaymentPlanMappingService(db).resolve(plan_code="START_V1", environment="TEST")

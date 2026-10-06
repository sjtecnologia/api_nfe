from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.commercial_subscriptions import CommercialSubscriptionService, NewSubscriptionSpec


def test_legacy_plan_is_closed_for_new_subscriptions():
    db = MagicMock()

    with pytest.raises(ValueError, match="PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS"):
        CommercialSubscriptionService(db).create_new_subscription(
            NewSubscriptionSpec(cliente_id=99, plan_version_code="LEGACY_60_V1")
        )

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_new_subscription_uses_versioned_price_and_creates_expected_objects():
    db = MagicMock()
    version = SimpleNamespace(plan_version_id=4, version_code="START_V1", price=Decimal("60.00"), status="ACTIVE")
    db.query.return_value.filter_by.return_value.first.return_value = version
    result = CommercialSubscriptionService(db).create_new_subscription(
        NewSubscriptionSpec(cliente_id=21, plan_version_code="START_V1")
    )

    assert result.plan_version_id == 4
    assert result.contracted_price == Decimal("60.00")
    assert result.currency == "BRL"
    assert db.add.call_count == 3
    db.commit.assert_not_called()

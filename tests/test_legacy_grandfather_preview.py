from datetime import date
from decimal import Decimal

import pytest

from services.legacy_grandfather_preview import build_preview


@pytest.mark.parametrize(("cliente_id", "users"), [(11, 2), (13, 3)])
def test_approved_legacy_clients_are_grandfather_ready(cliente_id, users):
    preview = build_preview(
        cliente_id=cliente_id,
        current_status="ACTIVE",
        current_plan="Pacote Básico",
        subscription_id=cliente_id,
        subscription_start=date(2024, 1, 1),
        current_users=users,
        current_companies=1,
        decision_date="2026-08-25",
    )

    assert preview.decision == "GRANDFATHER_READY"
    assert preview.contracted_price == Decimal("60.00")
    assert preview.price_source == "MANUAL_BUSINESS_DECISION"
    assert preview.price_confidence == "CONFIRMED"
    assert preview.grandfathered is True
    assert preview.closed_to_new_subscriptions is True
    assert preview.nfe_quota_policy == "LEGACY_PRESERVED"
    assert preview.user_capacity_policy == "PRESERVE_CURRENT"
    assert preview.company_capacity_policy == "PRESERVE_CURRENT"
    assert preview.feature_policy == "PRESERVE_EXISTING_ACCESS"
    assert preview.current_users == users
    assert preview.current_plan != "START_V1"
    assert preview.historical_contract_evidence == "NOT_FOUND"


@pytest.mark.parametrize("cliente_id", [5, 12, 14])
def test_unapproved_clients_are_unchanged_and_have_no_price(cliente_id):
    preview = build_preview(
        cliente_id=cliente_id,
        current_status="ACTIVE",
        current_plan=None,
        subscription_id=None,
        subscription_start=None,
        current_users=3,
        current_companies=0,
        decision_date="2026-08-25",
    )

    assert preview.decision == "UNCHANGED_NO_COMMERCIAL_MIGRATION"
    assert preview.contracted_price is None
    assert preview.grandfathered is False
    assert preview.nfe_quota_policy == "UNCHANGED"
    assert preview.notes_required is True


def test_unknown_client_is_rejected_from_approved_scope():
    with pytest.raises(ValueError, match="CLIENT_NOT_IN_APPROVED_SCOPE"):
        build_preview(
            cliente_id=99,
            current_status="UNKNOWN",
            current_plan=None,
            subscription_id=None,
            subscription_start=None,
            current_users=0,
            current_companies=0,
            decision_date="2026-08-25",
        )


def test_preview_is_deterministic():
    kwargs = dict(
        cliente_id=11,
        current_status="ACTIVE",
        current_plan="Pacote Básico",
        subscription_id=1,
        subscription_start=date(2024, 1, 1),
        current_users=2,
        current_companies=1,
        decision_date="2026-08-25",
    )
    assert build_preview(**kwargs).to_dict() == build_preview(**kwargs).to_dict()

import pytest

from services.commercial_provisioning import CommercialProvisioningService


def test_start_provisioning_is_dry_run_only():
    preview = CommercialProvisioningService().preview(plan_version_code="START_V1", contracted_price="60.00")
    assert preview.status == "DRY_RUN"
    assert "BillingSubscription" in preview.objects_to_create


def test_legacy_provisioning_is_closed():
    with pytest.raises(ValueError, match="PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS"):
        CommercialProvisioningService().preview(plan_version_code="LEGACY_60_V1", contracted_price="60.00")

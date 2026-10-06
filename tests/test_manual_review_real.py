from scripts.manual_review_real import simulate_plan


def test_legacy_r60_with_extra_users_needs_contract_review():
    result, reasons = simulate_plan(
        nfe_30d=0,
        company_count=1,
        user_count=2,
        rights_known=False,
        plan="START_V1",
    )

    assert result == "CONTRACT_REVIEW"
    assert "RIGHTS_UNKNOWN" in reasons
    assert "USER_CAPACITY_CONFLICT" in reasons


def test_usage_above_start_limit_is_incompatible():
    result, reasons = simulate_plan(
        nfe_30d=51,
        company_count=1,
        user_count=1,
        rights_known=True,
        plan="START_V1",
    )

    assert result == "INCOMPATIBLE"
    assert reasons == ["NFE_CAPACITY_CONFLICT"]


def test_premium_has_explicit_company_capacity():
    result, reasons = simulate_plan(
        nfe_30d=0,
        company_count=6,
        user_count=1,
        rights_known=True,
        plan="PREMIUM_V1",
    )

    assert result == "INCOMPATIBLE"
    assert reasons == ["COMPANY_CAPACITY_CONFLICT"]

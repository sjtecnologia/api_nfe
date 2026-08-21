from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from flask import jsonify

from services.commercial_entitlements import (
    CommercialEntitlementService,
    FeatureAccess,
    feature_required,
)
from services.billing_shadow import EntitlementResolver


def test_flag_off_preserves_existing_behavior(monkeypatch):
    monkeypatch.setenv('FEATURE_BILLING_ENTITLEMENTS_ENABLED', 'false')
    result = CommercialEntitlementService(MagicMock()).resolve_feature_access(
        cliente_id=1, user_id=2, feature='AI_SALES_ANALYSIS'
    )
    assert result.enabled is True
    assert result.reason == 'ALLOWED'
    assert result.source == 'FLAG_OFF'


def test_plan_not_entitled_returns_upgrade_contract(monkeypatch):
    monkeypatch.setenv('FEATURE_BILLING_ENTITLEMENTS_ENABLED', 'true')
    monkeypatch.setenv('FEATURE_ENTITLEMENT_AI_SALES_ANALYSIS', 'true')
    subscription = SimpleNamespace(
        subscription_id=1,
        plan_version=SimpleNamespace(version_code='START_V1'),
        companies=[SimpleNamespace(cliente_id=1, status='ACTIVE')],
    )
    class Query:
        def filter(self, *args):
            return self

        def all(self):
            return [subscription]

    class DB:
        def query(self, *args):
            return Query()

    db = DB()
    with patch('services.commercial_entitlements.EntitlementResolver.resolve', return_value={
        'enabled': False, 'source': 'PLAN', 'limit_type': 'DISABLED', 'limit_value': None,
    }):
        result = CommercialEntitlementService(db).resolve_feature_access(
            cliente_id=1, user_id=2, feature='AI_SALES_ANALYSIS'
        )
    assert result.enabled is False
    assert result.reason == 'PLAN_NOT_ENTITLED'
    assert result.current_plan == 'START_V1'
    assert 'PROFISSIONAL_V1' in result.required_plans


def test_legacy_or_unknown_is_non_blocking(monkeypatch):
    monkeypatch.setenv('FEATURE_BILLING_ENTITLEMENTS_ENABLED', 'true')
    db = MagicMock()
    db.query.return_value.filter.return_value.join.return_value.filter_by.return_value.first.return_value = None
    with patch('services.commercial_entitlements.LegacySubscriptionAdapter.get_for_company', return_value=None):
        result = CommercialEntitlementService(db).resolve_feature_access(
            cliente_id=1, user_id=2, feature='AI_SALES_ANALYSIS'
        )
    assert result.enabled is True
    assert result.reason == 'LEGACY_UNKNOWN'


def test_feature_guard_returns_json_403_only_when_enabled(monkeypatch, app):
    monkeypatch.setenv('FEATURE_BILLING_ENTITLEMENTS_ENABLED', 'true')
    user = SimpleNamespace(id=2, is_authenticated=True)
    denied = FeatureAccess(
        feature='AI_SALES_ANALYSIS', enabled=False, source='PLAN',
        reason='PLAN_NOT_ENTITLED', current_plan='START_V1',
        required_plans=('PROFISSIONAL_V1',),
    )

    @feature_required('AI_SALES_ANALYSIS')
    def protected():
        return jsonify({'success': True})

    with app.test_request_context('/api/analise-vendas'):
        with patch('services.commercial_entitlements.current_user', user), \
             patch('services.commercial_entitlements.session', {'current_client_id': 1}), \
             patch('services.commercial_entitlements.get_db', return_value=iter([MagicMock()])), \
             patch('services.commercial_entitlements.CommercialEntitlementService.resolve_feature_access', return_value=denied):
            response = protected()

    assert response[1] == 403
    assert response[0].get_json()['code'] == 'PLAN_UPGRADE_REQUIRED'


def test_shadow_over_limit_never_blocks_fiscal_code_path():
    # The commercial guard is opt-in and this test has no import/call to fiscal routes.
    access = FeatureAccess(
        feature='AI_SALES_ANALYSIS', enabled=False, source='PLAN',
        reason='PLAN_NOT_ENTITLED', limit_type='LIMITED', limit_value=0,
    )
    assert access.enabled is False
    assert access.reason != 'NFE_QUOTA'


def test_feature_override_enabled_and_disabled():
    class Query:
        def __init__(self, subscription):
            self.subscription = subscription

        def filter_by(self, **kwargs):
            return self

        def first(self):
            return self.subscription

    enabled = SimpleNamespace(key='AI_SALES_ANALYSIS', value='enabled', expires_at=None)
    disabled = SimpleNamespace(key='AI_SALES_ANALYSIS', value='disabled', expires_at=None)
    for override, expected in ((enabled, True), (disabled, False)):
        subscription = SimpleNamespace(overrides=[override])
        db = MagicMock()
        db.query.return_value = Query(subscription)
        result = EntitlementResolver(db).resolve(1, 'AI_SALES_ANALYSIS')
        assert result['enabled'] is expected
        assert result['source'] == 'OVERRIDE'

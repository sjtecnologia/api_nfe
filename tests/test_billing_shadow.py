from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.billing_shadow import CapacityResolver, EntitlementResolver, LegacySubscriptionAdapter


def test_legacy_adapter_is_read_only_and_maps_active_subscription():
    db = MagicMock()
    legacy = SimpleNamespace(
        assinatura_id=10,
        cliente_id=7,
        plano_id=2,
        status='ATIVA',
        nfes_consumidas=12,
        updated_at=datetime.utcnow(),
    )
    plan = SimpleNamespace(plano_id=2, nome='Pacote Básico', quantidade_nfes=50)
    legacy_query = MagicMock()
    legacy_query.filter.return_value.order_by.return_value.first.return_value = legacy
    plan_query = MagicMock()
    plan_query.filter.return_value.first.return_value = plan
    db.query.side_effect = [legacy_query, plan_query]

    result = LegacySubscriptionAdapter(db).get_for_company(7)

    assert result['source'] == 'LEGACY'
    assert result['plan_code'] == 'LEGACY_START_V1'
    assert result['nfe_consumed'] == 12
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_roadmap_feature_is_never_enabled():
    db = MagicMock()
    plan_feature = SimpleNamespace(enabled=True, limit_type='ENABLED', limit_value=None)
    feature = SimpleNamespace(key='AI_INSIGHTS_CENTER', status='ROADMAP')
    db.query.return_value.join.return_value.join.return_value.filter.return_value.first.return_value = (plan_feature, feature)

    result = EntitlementResolver(db).resolve(1, 'AI_INSIGHTS_CENTER')

    assert result['enabled'] is False
    assert result['limit_type'] == 'DISABLED'
    assert result['reason'] == 'ROADMAP'


def test_capacity_over_limit_is_shadow_only():
    subscription = SimpleNamespace(
        subscription_id=1,
        companies=[SimpleNamespace(cliente_id=10, status='ACTIVE'), SimpleNamespace(cliente_id=11, status='ACTIVE')],
        overrides=[],
        plan_version=SimpleNamespace(features=[]),
    )
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = subscription
    db.query.return_value.filter_by.return_value.count.return_value = 2

    result = CapacityResolver(db).companies(1)

    assert result.status == 'OVER_LIMIT'
    assert result.used == 2
    assert result.limit == 0
    # Shadow result does not reject a fiscal operation or mutate any table.
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_unmetered_fair_use_is_explicit():
    subscription = SimpleNamespace(subscription_id=1, companies=[], overrides=[], plan_version=SimpleNamespace(features=[
        SimpleNamespace(feature=SimpleNamespace(key='MAX_COMPANIES'), limit_type='UNMETERED_WITH_FAIR_USE', limit_value=None),
    ]))
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = subscription
    db.query.return_value.filter_by.return_value.count.return_value = 9

    result = CapacityResolver(db).companies(1)

    assert result.status == 'UNMETERED_WITH_FAIR_USE'
    assert result.limit is None


def test_expiring_override_is_not_used():
    subscription = SimpleNamespace(subscription_id=1, companies=[], plan_version=SimpleNamespace(features=[]), overrides=[
        SimpleNamespace(key='MAX_COMPANIES', value='7', expires_at=datetime.utcnow() - timedelta(days=1)),
    ])
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = subscription
    db.query.return_value.filter_by.return_value.count.return_value = 0

    result = CapacityResolver(db).companies(1)

    assert result.status == 'OK'
    assert result.limit == 0

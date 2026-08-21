from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.billing_usage_shadow import (
    APIUsageAdapter,
    AIUsageAdapter,
    BillingPeriodResolver,
    BillingUsageShadowService,
)


def subscription():
    return SimpleNamespace(
        subscription_id=10,
        account_id=20,
        started_at=datetime(2026, 8, 10),
        billing_cycle='MONTHLY',
        companies=[SimpleNamespace(cliente_id=7, status='ACTIVE')],
    )


def test_feature_flag_off_does_not_write():
    service = BillingUsageShadowService(MagicMock())
    result = service.record(cliente_id=7, metric_key='AI_REQUEST', event_key='ai:1', source_type='AI')
    assert result['reason'] == 'FEATURE_FLAG_OFF'


def test_event_is_idempotent():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [subscription()]
    db.query.return_value.filter_by.return_value.first.return_value = SimpleNamespace(usage_event_id=99)
    service = BillingUsageShadowService(db)
    service.enabled = staticmethod(lambda: True)
    result = service.record(cliente_id=7, metric_key='AI_REQUEST', event_key='ai:1', source_type='AI')
    assert result['reason'] == 'DUPLICATE'
    db.add.assert_not_called()


def test_unknown_subscription_does_not_create_event():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    service = BillingUsageShadowService(db)
    service.enabled = staticmethod(lambda: True)
    result = service.record(cliente_id=7, metric_key='API_REQUEST', event_key='api:1', source_type='API')
    assert result['reason'] == 'NO_SHADOW_SUBSCRIPTION'
    db.add.assert_not_called()


def test_period_resolver_uses_subscription_cycle():
    period = BillingPeriodResolver().resolve(datetime(2026, 8, 10), today=date(2026, 8, 20))
    assert period.start == date(2026, 8, 10)
    assert period.end == date(2026, 9, 1)


def test_ai_and_api_adapters_use_distinct_metrics():
    service = MagicMock()
    AIUsageAdapter(service).record_request(cliente_id=7, source_id='m1', funcionalidade='AI_SALES_ANALYSIS', tokens=4, cost=0.1)
    APIUsageAdapter(service).record_request(cliente_id=7, source_id='r1', endpoint='/api/v2/nfes', status_code=200)
    assert service.record.call_args_list[0].kwargs['metric_key'] == 'AI_REQUEST'
    assert service.record.call_args_list[1].kwargs['metric_key'] == 'API_REQUEST'


def test_usage_failure_is_non_blocking():
    db = MagicMock()
    db.query.side_effect = RuntimeError('shadow unavailable')
    service = BillingUsageShadowService(db)
    service.enabled = staticmethod(lambda: True)
    result = service.record_safe(cliente_id=7, metric_key='AI_REQUEST', event_key='ai:2', source_type='AI')
    assert result['reason'] == 'USAGE_LOGGING_FAILED'

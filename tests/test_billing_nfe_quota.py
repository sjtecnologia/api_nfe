from types import SimpleNamespace

from services.billing_nfe_quota import BillingNFeQuotaAdapter


class FakeReservationService:
    def __init__(self, status="RESERVED"):
        self.status = status
        self.calls = []
        self.subscription = SimpleNamespace(
            subscription_id=10,
            plan_version=SimpleNamespace(version_code="START_V1"),
        )

    def _resolve_subscription(self, **kwargs):
        self.calls.append(("resolve", kwargs))
        return self.subscription

    def reserve(self, **kwargs):
        self.calls.append(("reserve", kwargs))
        return {"allowed": self.status != "QUOTA_EXCEEDED", "status": self.status, "code": "TEST"}

    def confirm(self, **kwargs):
        self.calls.append(("confirm", kwargs))
        return {"status": "CONFIRMED"}

    def release(self, **kwargs):
        self.calls.append(("release", kwargs))
        return {"status": "RELEASED"}

    def reconcile(self, **kwargs):
        self.calls.append(("reconcile", kwargs))
        return {"status": "PENDING_RECONCILIATION"}


def test_flag_off_preserves_baseline(monkeypatch):
    monkeypatch.delenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", raising=False)
    monkeypatch.delenv("FEATURE_BILLING_NFE_QUOTA_SHADOW", raising=False)
    service = FakeReservationService()

    result = BillingNFeQuotaAdapter(None, service).before_external_send(
        cliente_id=1, reservation_key="NFE:test:off", source_id="NFE:test:off"
    )

    assert result["allowed"] is True
    assert result["status"] == "FLAG_OFF"
    assert [call[0] for call in service.calls] == []


def test_rollout_enforces_only_start_tenant(monkeypatch):
    monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", "true")
    monkeypatch.setenv("BILLING_NFE_QUOTA_ROLLOUT_CLIENT_IDS", "1")
    service = FakeReservationService(status="QUOTA_EXCEEDED")

    result = BillingNFeQuotaAdapter(None, service).before_external_send(
        cliente_id=1, reservation_key="NFE:test:block", source_id="NFE:test:block"
    )

    assert result["allowed"] is False
    assert result["code"] == "TEST"
    assert [call[0] for call in service.calls] == ["resolve", "reserve"]


def test_shadow_observation_does_not_block(monkeypatch):
    monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_SHADOW", "true")
    monkeypatch.delenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", raising=False)
    service = FakeReservationService(status="QUOTA_EXCEEDED")

    result = BillingNFeQuotaAdapter(None, service).before_external_send(
        cliente_id=1, reservation_key="NFE:test:shadow", source_id="NFE:test:shadow"
    )

    assert result["allowed"] is True
    assert result["status"] == "SHADOW_QUOTA_EXCEEDED"


def test_lifecycle_delegates_without_fiscal_error(monkeypatch):
    monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", "true")
    service = FakeReservationService()
    adapter = BillingNFeQuotaAdapter(None, service)

    assert adapter.after_authorized(reservation_key="NFE:test", source_id="NFE:test")["status"] == "CONFIRMED"
    assert adapter.known_not_authorized(reservation_key="NFE:test", reason="REJEITADA")["status"] == "RELEASED"
    assert [call[0] for call in service.calls] == ["confirm", "release"]

from types import SimpleNamespace
from unittest.mock import patch

from services import webhook_service


class _Query:
    def __init__(self, model, item, webhook):
        self.model = model
        self.item = item
        self.webhook = webhook

    def filter_by(self, **kwargs):
        self.kwargs = kwargs
        return self

    def first(self):
        if self.model is webhook_service.WebhookQueue:
            return self.item
        return self.webhook


class _Db:
    def __init__(self, item, webhook):
        self.item = item
        self.webhook = webhook
        self.commits = 0
        self.closed = False

    def query(self, model):
        return _Query(model, self.item, self.webhook)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def test_send_webhook_reloads_queue_item_and_persists_success():
    item = SimpleNamespace(
        queue_id=42, webhook_id=7, evento='nfe.autorizada',
        payload='{"nfe_id": 99}', status='processing',
        processado_em=None,
    )
    webhook = SimpleNamespace(
        webhook_id=7, ativo=True, secret='secret', url='https://example.test/hook',
        timeout_seconds=3, ultimo_sucesso=None, total_sucessos=0,
    )
    db = _Db(item, webhook)
    response = SimpleNamespace(status_code=200, text='ok')

    with patch.object(webhook_service, 'get_db', return_value=iter([db])), \
         patch.object(webhook_service.socket, 'getaddrinfo', return_value=[(None, None, None, None, ('93.184.216.34', 443))]), \
         patch.object(webhook_service.requests, 'post', return_value=response):
        sucesso, erro = webhook_service.send_webhook(SimpleNamespace(queue_id=42))

    assert sucesso is True
    assert erro is None
    assert item.status == 'sent'
    assert item.processado_em is not None
    assert webhook.total_sucessos == 1
    assert db.commits == 1
    assert db.closed is True


def test_webhook_url_validation_rejects_internal_destinations():
    assert webhook_service.validate_webhook_url('https://example.com/hook')[0] is True
    assert webhook_service.validate_webhook_url('http://127.0.0.1/hook')[0] is False
    assert webhook_service.validate_webhook_url('http://localhost/hook')[0] is False
    assert webhook_service.validate_webhook_url('file:///tmp/hook')[0] is False


def test_webhook_url_validation_rejects_dns_resolving_to_private_network():
    with patch.object(webhook_service.socket, 'getaddrinfo', return_value=[
        (None, None, None, None, ('10.0.0.8', 443))
    ]):
        assert webhook_service.validate_webhook_url('https://public.example/hook', resolve_dns=True)[0] is False

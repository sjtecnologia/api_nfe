from flask import g

from auth.api_key_auth import generate_api_key
from auth.api_key_auth import check_ip_whitelist
from routes.api_v2_routes import _chave_pode_emitir_nfe, _validar_ambiente_api


def test_generate_api_key_has_explicit_environment_prefix():
    live, _, live_prefix = generate_api_key(1, 'erp', ambiente='producao')
    test, _, test_prefix = generate_api_key(1, 'erp', ambiente='teste')

    assert live.startswith('emx_live_')
    assert test.startswith('emx_test_')
    assert live_prefix == live[:12]
    assert test_prefix == test[:12]


def test_invalid_environment_falls_back_to_production_key():
    key, _, _ = generate_api_key(1, 'erp', ambiente='qualquer')
    assert key.startswith('emx_live_')


def test_test_api_key_cannot_request_production():
    with __import__('flask').Flask(__name__).app_context():
        g.api_environment = 'teste'
        assert _validar_ambiente_api('producao') == (False, 'producao')
        assert _validar_ambiente_api('homologacao') == (True, 'homologacao')


def test_test_key_is_rejected_for_production_nfe_configuration():
    with __import__('flask').Flask(__name__).app_context():
        g.api_environment = 'teste'
        assert _chave_pode_emitir_nfe(type('Cliente', (), {'ambiente': 1})()) is False
        assert _chave_pode_emitir_nfe(type('Cliente', (), {'ambiente': 2})()) is True


def test_production_api_key_can_request_homologation_or_production():
    with __import__('flask').Flask(__name__).app_context():
        g.api_environment = 'producao'
        assert _validar_ambiente_api('producao') == (True, 'producao')
        assert _validar_ambiente_api('homologacao') == (True, 'homologacao')


def test_ip_whitelist_supports_cidr_and_fails_closed_on_invalid_json():
    key = type('Key', (), {'ip_whitelist': '["203.0.113.0/24"]'})()
    assert check_ip_whitelist(key, '203.0.113.42') is True
    assert check_ip_whitelist(key, '198.51.100.42') is False

    invalid = type('Key', (), {'ip_whitelist': '{invalid'})()
    assert check_ip_whitelist(invalid, '203.0.113.42') is False

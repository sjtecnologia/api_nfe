from types import SimpleNamespace
from unittest.mock import patch


def _mock_logged_user(user_id: int = 99):
    return SimpleNamespace(
        id=user_id,
        username='tester',
        is_authenticated=True,
        is_active=True,
    )


def test_assistente_ia_rejeita_pergunta_fora_escopo(client):
    user = _mock_logged_user()

    with patch('flask_login.utils._get_user', return_value=user), \
         patch('routes.api_routes.AuditoriaService') as audit_mock:
        response = client.post(
            '/api/assistente-ia',
            json={
                'pergunta': 'Me conte uma piada de futebol',
                'contexto': {},
            },
        )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload['success'] is False
    assert 'escopo' in payload['error'].lower()
    audit_mock.registrar_acao.assert_called_once()
    kwargs = audit_mock.registrar_acao.call_args.kwargs
    assert kwargs['acao'] == 'AI_ASSISTENTE_BLOQUEADO'
    assert 'piada' in kwargs['dados_depois']['pergunta'].lower()


def test_assistente_ia_exige_pergunta(client):
    user = _mock_logged_user()

    with patch('flask_login.utils._get_user', return_value=user):
        response = client.post('/api/assistente-ia', json={'pergunta': '   '})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['success'] is False


def test_assistente_ia_pergunta_fiscal_com_fallback_local(client):
    user = _mock_logged_user()

    with patch('flask_login.utils._get_user', return_value=user), \
         patch('routes.api_routes.AIService', None):
        response = client.post(
            '/api/assistente-ia',
            json={
                'pergunta': 'Qual CFOP usar para venda dentro do estado?',
                'contexto': {'empresa': {'crt': 1, 'uf': 'SP', 'regime': 'Simples Nacional'}},
            },
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert isinstance(payload['resposta'], str)
    assert payload['resposta'].strip() != ''

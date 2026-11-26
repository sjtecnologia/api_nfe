from unittest.mock import MagicMock, patch

from services import consultor_vendas_service as svc


def test_gerar_insights_consultor_vendas_sem_notas():
    insights = svc._gerar_insights_consultor_vendas({
        'total_notas': 0,
        'faturamento': 0,
        'ticket_medio': 0,
        'taxa_autorizacao': 0,
        'delta_faturamento_pct': 0,
        'delta_notas_pct': 0,
    })
    assert len(insights) == 1
    assert 'Nenhuma nota autorizada' in insights[0]


def test_gerar_narrativa_ia_fallback_quando_ai_indisponivel():
    with patch.object(svc, 'AIService', None):
        out = svc._gerar_narrativa_ia_consultor_vendas(
            cliente_id=1,
            metricas={},
            insights=[],
            top_produtos=[],
            top_destinatarios=[],
        )
    assert out['enabled'] is False
    assert out['source'] == 'disabled'


def test_executar_envio_diario_consultor_vendas_dispara_emails(monkeypatch):
    monkeypatch.setenv('CONSULTOR_VENDAS_DAILY_DAYS', '1')
    monkeypatch.setenv('CONSULTOR_VENDAS_DAILY_USE_AI', 'false')
    monkeypatch.setenv('CONSULTOR_VENDAS_EMAIL_SUPORTE', 'suporte@emitemax.com.br')

    cliente_row = MagicMock(cliente_id=5, razao_social='Cliente Teste')

    db_mock = MagicMock()
    exec_clientes = MagicMock(); exec_clientes.fetchall.return_value = [cliente_row]
    exec_destinatarios = MagicMock(); exec_destinatarios.fetchall.return_value = [('cliente@teste.com',), ('admin@teste.com',)]
    db_mock.execute.side_effect = [exec_clientes, exec_destinatarios]

    email_service_mock = MagicMock()
    email_service_mock.enviar_email.return_value = {'success': True, 'message': 'ok'}

    resumo_fake = {
        'metricas': {'days': 1, 'total_notas': 2, 'faturamento': 100.0, 'ticket_medio': 50.0, 'taxa_autorizacao': 100.0, 'delta_faturamento_pct': 10.0, 'delta_notas_pct': 10.0},
        'insights': ['ok'],
        'top_produtos': [],
        'top_destinatarios': [],
        'narrativa_ia': {'enabled': False, 'source': 'disabled', 'text': ''},
    }

    with patch.object(svc, 'get_db', return_value=iter([db_mock])), \
         patch.object(svc, 'gerar_resumo_consultor_vendas', return_value=resumo_fake), \
         patch.object(svc, 'EmailService', return_value=email_service_mock), \
         patch.object(svc.AuditoriaService, 'registrar_acao', return_value=True):
        out = svc.executar_envio_diario_consultor_vendas()

    assert out['success'] is True
    assert out['clientes_processados'] == 1
    # cliente + admin + suporte
    assert out['emails_enviados'] == 3

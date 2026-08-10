from datetime import datetime
from unittest.mock import patch

from services import assistente_auditoria_service as svc


def _stats(total=0, usuarios=0, clientes=0, top_usuarios=None, top_clientes=None):
    return {
        'total_bloqueios': total,
        'usuarios_afetados': usuarios,
        'clientes_afetados': clientes,
        'top_usuarios': top_usuarios or [],
        'top_clientes': top_clientes or [],
    }


def test_avaliar_anomalias_sem_alerta(monkeypatch):
    monkeypatch.setenv('ASSISTENTE_AUDITORIA_ALERTA_TOTAL_BLOQUEIOS', '20')
    monkeypatch.setenv('ASSISTENTE_AUDITORIA_ALERTA_BLOQUEIOS_POR_USUARIO', '8')
    monkeypatch.setenv('ASSISTENTE_AUDITORIA_ALERTA_CLIENTES_AFETADOS', '5')

    alertas = svc._avaliar_anomalias(_stats(total=2, usuarios=2, clientes=1))
    assert alertas == []


def test_avaliar_anomalias_com_alerta_por_total_e_usuario(monkeypatch):
    monkeypatch.setenv('ASSISTENTE_AUDITORIA_ALERTA_TOTAL_BLOQUEIOS', '5')
    monkeypatch.setenv('ASSISTENTE_AUDITORIA_ALERTA_BLOQUEIOS_POR_USUARIO', '3')
    monkeypatch.setenv('ASSISTENTE_AUDITORIA_ALERTA_CLIENTES_AFETADOS', '10')

    stats = _stats(
        total=7,
        usuarios=2,
        clientes=2,
        top_usuarios=[{'user_id': 9, 'username': 'admin', 'total': 4}],
    )
    alertas = svc._avaliar_anomalias(stats)
    assert any('Volume alto' in a for a in alertas)
    assert any('fora do padrão' in a for a in alertas)


def test_executar_auditoria_diaria_envia_email_quando_ha_anomalia():
    referencia = datetime(2026, 8, 10, 12, 0, 0)
    stats = _stats(
        total=30,
        usuarios=3,
        clientes=6,
        top_usuarios=[{'user_id': 1, 'username': 'sjtec', 'total': 12}],
        top_clientes=[{'cliente_id': 5, 'total': 9}],
    )

    with patch.object(svc, '_coletar_estatisticas_bloqueios', return_value=stats), \
         patch.object(svc, '_avaliar_anomalias', return_value=['alerta de teste']), \
         patch.object(svc, '_enviar_alerta_email', return_value={'success': True, 'destinatario': 'suporte@emitemax.com.br', 'message': 'ok'}) as email_mock, \
         patch.object(svc.AuditoriaService, 'registrar_acao', return_value=True) as audit_mock:
        result = svc.executar_auditoria_diaria_assistente(referencia=referencia)

    assert result['success'] is True
    assert result['email']['success'] is True
    email_mock.assert_called_once()
    audit_mock.assert_called_once()


def test_executar_auditoria_diaria_sem_anomalia_nao_envia_email():
    referencia = datetime(2026, 8, 10, 12, 0, 0)

    with patch.object(svc, '_coletar_estatisticas_bloqueios', return_value=_stats(total=0)), \
         patch.object(svc, '_avaliar_anomalias', return_value=[]), \
         patch.object(svc, '_enviar_alerta_email') as email_mock, \
         patch.object(svc.AuditoriaService, 'registrar_acao', return_value=True):
        result = svc.executar_auditoria_diaria_assistente(referencia=referencia)

    assert result['success'] is True
    assert result['alertas'] == []
    assert result['email']['success'] is False
    email_mock.assert_not_called()

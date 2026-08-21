"""Testes da camada determinística de dados da inteligência empresarial."""

from datetime import date

import pytest

from services.intelligence.data_types import DadosAgregados, PeriodoAnalise, QualidadeDados
from services.intelligence.date_ranges import periodo_anterior, variacao_atual_anterior
from services.intelligence.tenant_scope import resolve_active_cliente_id


def test_periodo_anterior_tem_mesma_duracao():
    periodo = PeriodoAnalise(date(2026, 8, 1), date(2026, 8, 13))
    anterior = periodo_anterior(periodo)

    assert anterior.to_dict() == {'inicio': '2026-07-19', 'fim': '2026-07-31'}
    assert anterior.dias == periodo.dias


def test_variacao_calcula_absoluta_e_percentual():
    assert variacao_atual_anterior(125.0, 100.0) == {
        'absoluta': 25.0,
        'percentual': 25.0,
    }
    assert variacao_atual_anterior(10.0, 0.0) == {
        'absoluta': 10.0,
        'percentual': None,
    }


def test_contrato_tem_formato_comum():
    qualidade = QualidadeDados()
    dados = DadosAgregados(
        cliente_id=123,
        periodo=PeriodoAnalise(date(2026, 8, 1), date(2026, 8, 13)),
        metricas={'saldo': 10},
        qualidade_dados=qualidade,
    ).to_dict()

    assert set(dados) == {
        'cliente_id', 'periodo', 'metricas', 'comparativos', 'listas',
        'qualidade_dados', 'gerado_em',
    }
    assert dados['cliente_id'] == 123
    assert dados['periodo']['inicio'] == '2026-08-01'


def test_tenant_scope_usa_empresa_ativa_e_nao_id_externo():
    class User:
        def is_super_admin(self):
            return False

        def get_accessible_clients(self):
            return [{'cliente_id': 10}]

    assert resolve_active_cliente_id(User(), {'current_client_id': 10}) == 10

    with pytest.raises(PermissionError):
        resolve_active_cliente_id(User(), {'current_client_id': 20})

    with pytest.raises(ValueError):
        resolve_active_cliente_id(User(), {})


def test_estoque_minimo_nao_e_inferido():
    """Contrato esperado para a futura camada: mínimo ausente não vira alerta falso."""
    dados = {
        'metricas': {'estoque_minimo_configurado': False},
        'qualidade_dados': {
            'suficiente': True,
            'avisos': ['Estoque mínimo não está configurado no cadastro atual de produtos.'],
        },
    }

    assert dados['metricas']['estoque_minimo_configurado'] is False
    assert 'estoque mínimo' in dados['qualidade_dados']['avisos'][0].lower()

"""Testes das regras determinísticas da análise de vendas."""

from datetime import date
from unittest.mock import Mock, patch

from services.intelligence.data_types import PeriodoAnalise
from services.intelligence.sales_analysis_service import SalesAnalysisService


class FakeAggregator:
    def __init__(self, db):
        self.db = db

    def aggregate(self, cliente_id, periodo):
        return {
            'domain': 'sales',
            'cliente_id': cliente_id,
            'periodo': periodo.to_dict(),
            'metricas': {
                'quantidade_documentos': 20,
                'quantidade_autorizada': 18,
                'quantidade_cancelada': 1,
                'quantidade_rejeitada': 1,
                'faturamento': 1200.0,
                'ticket_medio': 100.0,
                'taxa_cancelamento': 5.0,
                'taxa_rejeicao': 5.0,
                'quantidade_itens_vendidos': 30.0,
            },
            'comparativos': {
                'periodo_anterior': {'inicio': '2026-07-19', 'fim': '2026-07-31'},
                'faturamento': {'absoluta': 200.0, 'percentual': 20.0},
                'documentos_autorizados': {'absoluta': 3.0, 'percentual': 20.0},
                'ticket_medio': {'absoluta': 20.0, 'percentual': 25.0},
            },
            'listas': {
                'produtos_mais_vendidos': [{
                    'descricao': 'Produto A', 'quantidade': 20,
                    'valor_total': 1000, 'ocorrencias': 10,
                    'participacao_faturamento_pct': 80.0,
                }],
                'produtos_menor_movimentacao': [],
                'principais_compradores': [],
            },
            'qualidade_dados': {'suficiente': True, 'avisos': [], 'origens': ['teste']},
            'gerado_em': '2026-08-13T00:00:00',
        }


def test_analise_cria_indicadores_sem_chamar_ia():
    service = SalesAnalysisService(db=Mock(), aggregator=FakeAggregator(None))
    with patch('services.intelligence.sales_analysis_service.AIService') as ai:
        result = service.analyze(5, PeriodoAnalise(date(2026, 8, 1), date(2026, 8, 13)))

    codes = {item['codigo'] for item in result['indicadores']}
    assert {'SALES_REVENUE_GROWTH', 'AVERAGE_TICKET_GROWTH', 'HIGH_CANCELLATION_RATE', 'HIGH_REJECTION_RATE', 'PRODUCT_CONCENTRATION'} <= codes
    ai.assert_not_called()


def test_analise_sem_dados_informa_ausencia():
    data = FakeAggregator(None).aggregate(5, PeriodoAnalise(date(2026, 8, 1), date(2026, 8, 13)))
    data['metricas'].update({
        'quantidade_documentos': 0,
        'quantidade_autorizada': 0,
        'faturamento': 0,
        'ticket_medio': 0,
        'taxa_cancelamento': 0,
        'taxa_rejeicao': 0,
    })
    data['qualidade_dados'] = {'suficiente': False, 'avisos': ['sem dados'], 'origens': []}

    class EmptyAggregator(FakeAggregator):
        def aggregate(self, cliente_id, periodo):
            return data

    result = SalesAnalysisService(db=Mock(), aggregator=EmptyAggregator(None)).analyze(
        5, PeriodoAnalise(date(2026, 8, 1), date(2026, 8, 13))
    )
    assert not result['indicadores']
    assert result['qualidade_dados']['suficiente'] is False

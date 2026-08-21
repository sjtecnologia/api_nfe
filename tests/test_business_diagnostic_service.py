"""Testes do MVP de diagnóstico empresarial."""

from datetime import date
from unittest.mock import Mock

from services.intelligence.business_diagnostic_service import BusinessDiagnosticService
from services.intelligence.data_types import PeriodoAnalise


class FakeService(BusinessDiagnosticService):
    def __init__(self):
        super().__init__(Mock())

    def diagnose(self, cliente_id, periodo):
        return super().diagnose(cliente_id, periodo)


def make_sales():
    return {
        'domain': 'sales', 'periodo': {'inicio': '2026-08-01', 'fim': '2026-08-13'},
        'metricas': {'faturamento': 1200, 'quantidade_autorizada': 10, 'quantidade_documentos': 10, 'quantidade_cancelada': 0, 'quantidade_rejeitada': 0, 'ticket_medio': 120, 'quantidade_itens_vendidos': 20, 'taxa_cancelamento': 0, 'taxa_rejeicao': 0},
        'comparativos': {}, 'indicadores': [], 'destaques': [], 'pontos_atencao': [], 'listas': {},
        'qualidade_dados': {'suficiente': True, 'avisos': [], 'origens': []}, 'narrativa': None,
    }


def make_inventory():
    return {'metricas': {'movimentacoes': 0, 'produtos_sem_movimentacao': 3, 'saldo': 0, 'estoque_minimo_configurado': False}, 'listas': {}, 'qualidade_dados': {'suficiente': False, 'avisos': ['sem estoque'], 'origens': []}}


def make_cash():
    return {'metricas': {'receitas': 100, 'despesas': 150, 'saldo': -50, 'quantidade_lancamentos': 3}, 'comparativos': {'receitas': {'percentual': 20}, 'despesas': {'percentual': 20}}, 'listas': {}, 'qualidade_dados': {'suficiente': True, 'avisos': [], 'origens': []}}


def make_customers():
    return {'metricas': {'quantidade_total_clientes': 10, 'clientes_com_compra': 4, 'clientes_recorrentes': 2, 'clientes_sem_compra_no_periodo': 6, 'notas_autorizadas': 4}, 'listas': {}, 'qualidade_dados': {'suficiente': True, 'avisos': [], 'origens': []}}


def test_diagnostico_reune_dominios_e_ordena_atencao():
    service = BusinessDiagnosticService(Mock())
    service._sales_signals = lambda data: []
    service._inventory_signals = lambda data: [service._signal_test('inventory', 'INVENTORY_NO_MOVEMENT', 'attention')]
    service._cash_signals = lambda data: [service._signal_test('cash_flow', 'CASH_FLOW_NEGATIVE', 'attention')]
    service._customer_signals = lambda data: [service._signal_test('customers', 'CUSTOMER_RECURRING_ACTIVITY', 'positive')]
    service_module = __import__('services.intelligence.business_diagnostic_service', fromlist=['SalesAnalysisService'])
    class StubSales:
        def analyze(self, *args): return make_sales()
    class StubAggregator:
        def __init__(self, data): self.data = data
        def aggregate(self, *args): return self.data
    originals = (
        service_module.SalesAnalysisService,
        service_module.InventoryDataAggregator,
        service_module.CashFlowDataAggregator,
        service_module.CustomerDataAggregator,
    )
    service_module.SalesAnalysisService = lambda db: StubSales()
    service_module.InventoryDataAggregator = lambda db: StubAggregator(make_inventory())
    service_module.CashFlowDataAggregator = lambda db: StubAggregator(make_cash())
    service_module.CustomerDataAggregator = lambda db: StubAggregator(make_customers())
    try:
        result = service.diagnose(5, PeriodoAnalise(date(2026, 8, 1), date(2026, 8, 13)))
    finally:
        (
            service_module.SalesAnalysisService,
            service_module.InventoryDataAggregator,
            service_module.CashFlowDataAggregator,
            service_module.CustomerDataAggregator,
        ) = originals

    assert result['summary']['total_signals'] == 3
    assert result['summary']['attention'] == 2
    assert result['signals'][0]['type'] == 'attention'
    assert set(result['domains']) == {'sales', 'inventory', 'cash_flow', 'customers'}


def test_signal_test_helper():
    signal = BusinessDiagnosticService._signal_test(BusinessDiagnosticService(Mock()), 'sales', 'X', 'positive')
    assert signal.code == 'X'


# Helper usado somente para tornar o teste de ordenação legível.
def _signal_test(self, domain, code, signal_type):
    from services.intelligence.data_types import BusinessSignal
    return BusinessSignal(domain, code, signal_type, 'info', code, code, {}, None, 1)


BusinessDiagnosticService._signal_test = _signal_test

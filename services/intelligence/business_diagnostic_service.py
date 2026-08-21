"""MVP do diagnóstico empresarial, calculado sob demanda e sem persistência."""

from __future__ import annotations

from typing import Any

from services.ai_service import AIService
from services.ai_providers import AIProviderError

from .business_diagnostic_rules import (
    CASH_VARIATION_THRESHOLD_PCT,
    CUSTOMER_INACTIVE_MIN_COUNT,
    CUSTOMER_RECURRING_MIN_COUNT,
    INVENTORY_NO_MOVEMENT_DAYS,
)
from .cash_flow_data_aggregator import CashFlowDataAggregator
from .customer_data_aggregator import CustomerDataAggregator
from .data_types import BusinessSignal, PeriodoAnalise
from .inventory_data_aggregator import InventoryDataAggregator
from .sales_analysis_service import SalesAnalysisService


class BusinessDiagnosticService:
    """Combina sinais dos quatro domínios sem chamar IA no diagnóstico padrão."""

    def __init__(self, db):
        self.db = db

    def diagnose(self, cliente_id: int, periodo: PeriodoAnalise) -> dict[str, Any]:
        sales = SalesAnalysisService(self.db).analyze(cliente_id, periodo)
        inventory = InventoryDataAggregator(self.db).aggregate(cliente_id, periodo)
        cash_flow = CashFlowDataAggregator(self.db).aggregate(cliente_id, periodo)
        customers = CustomerDataAggregator(self.db).aggregate(cliente_id, periodo)

        signals = []
        signals.extend(self._sales_signals(sales))
        signals.extend(self._inventory_signals(inventory))
        signals.extend(self._cash_signals(cash_flow))
        signals.extend(self._customer_signals(customers))
        signals.sort(key=lambda signal: (-self._severity_order(signal.severity), -signal.relevance, signal.title))

        domains = {
            'sales': sales,
            'inventory': inventory,
            'cash_flow': cash_flow,
            'customers': customers,
        }
        warnings = []
        for domain_data in domains.values():
            for warning in domain_data.get('qualidade_dados', {}).get('avisos', []):
                if warning not in warnings:
                    warnings.append(warning)

        summary = {
            'total_signals': len(signals),
            'positive': sum(signal.type == 'positive' for signal in signals),
            'attention': sum(signal.type == 'attention' for signal in signals),
            'informational': sum(signal.type == 'informational' for signal in signals),
        }
        return {
            'periodo': periodo.to_dict(),
            'summary': summary,
            'domains': domains,
            'signals': [signal.to_dict() for signal in signals],
            'data_quality': {
                'sufficient': any(domain.get('qualidade_dados', {}).get('suficiente') for domain in domains.values()),
                'warnings': warnings,
            },
            'narrative': None,
        }

    def summarize_with_ai(self, diagnosis: dict[str, Any], cliente_id: int, user_id: int | None) -> dict[str, Any]:
        context = {
            'periodo': diagnosis['periodo'],
            'summary': diagnosis['summary'],
            'signals': diagnosis['signals'],
            'data_quality': diagnosis['data_quality'],
        }
        try:
            result = AIService(db=self.db).chat(
                prompt_name='assistant_business',
                user_message='Resuma o diagnóstico empresarial com clareza, separando fatos observados de pontos que merecem atenção. Não recalcule nem invente números.',
                context=context,
                cliente_id=cliente_id,
                user_id=user_id,
                functionality='business_diagnostic_narrative',
                tools_scope='business',
                record=True,
            )
            return {'narrative': (result.get('content') or '').strip() or None, 'model': result.get('model')}
        except (AIProviderError, Exception) as exc:
            return {'narrative': None, 'error': str(exc)}

    def _sales_signals(self, data: dict[str, Any]) -> list[BusinessSignal]:
        return [self._from_sales_indicator(item) for item in data.get('indicadores', [])]

    @staticmethod
    def _from_sales_indicator(item: dict[str, Any]) -> BusinessSignal:
        type_map = {'positivo': 'positive', 'atencao': 'attention', 'informativo': 'informational'}
        return BusinessSignal(
            domain='sales', code=item['codigo'], type=type_map.get(item.get('tipo'), 'informational'),
            severity=item.get('severidade', 'info'), title=item['titulo'], description=item['descricao'],
            evidence=item.get('evidencias', {}), action={'label': 'Ver análise de vendas', 'url': '/admin/analise-vendas'}, relevance=3,
        )

    def _inventory_signals(self, data: dict[str, Any]) -> list[BusinessSignal]:
        metricas = data['metricas']
        signals = []
        sem_movimentacao = int(metricas.get('produtos_sem_movimentacao') or 0)
        if sem_movimentacao > 0:
            signals.append(BusinessSignal(
                'inventory', 'INVENTORY_NO_MOVEMENT', 'attention', 'info',
                'Produtos sem movimentação recente',
                f'{sem_movimentacao} produtos não possuem movimentação de estoque no período analisado.',
                {'quantidade_produtos': sem_movimentacao, 'periodo_dias': INVENTORY_NO_MOVEMENT_DAYS},
                {'label': 'Ver estoque', 'url': '/admin/estoque'}, 2,
            ))
        if int(metricas.get('movimentacoes') or 0) == 0:
            signals.append(BusinessSignal(
                'inventory', 'INVENTORY_DATA_INSUFFICIENT', 'informational', 'info',
                'Dados de estoque insuficientes',
                'Não existem movimentações de estoque no período selecionado.',
                {'movimentacoes': 0}, {'label': 'Ver estoque', 'url': '/admin/estoque'}, 1,
            ))
        if float(metricas.get('saldo') or 0) == 0 and int(metricas.get('movimentacoes') or 0) > 0:
            signals.append(BusinessSignal(
                'inventory', 'INVENTORY_ZERO_BALANCE', 'informational', 'info',
                'Saldo de movimentações zerado',
                'O saldo calculado de entradas e saídas no período é zero.',
                {'saldo': metricas['saldo']}, {'label': 'Ver estoque', 'url': '/admin/estoque'}, 1,
            ))
        return signals

    def _cash_signals(self, data: dict[str, Any]) -> list[BusinessSignal]:
        metricas, comparativos = data['metricas'], data['comparativos']
        if int(metricas.get('quantidade_lancamentos') or 0) == 0:
            return [BusinessSignal(
                'cash_flow', 'CASH_FLOW_DATA_INSUFFICIENT', 'informational', 'info',
                'Dados de caixa insuficientes', 'Não existem lançamentos de fluxo de caixa no período selecionado.',
                {'quantidade_lancamentos': 0}, {'label': 'Ver fluxo de caixa', 'url': '/admin/fluxo-caixa'}, 1,
            )]
        signals = []
        receitas, despesas = float(metricas['receitas']), float(metricas['despesas'])
        if receitas > despesas:
            signals.append(BusinessSignal('cash_flow', 'CASH_FLOW_POSITIVE', 'positive', 'info', 'Fluxo de caixa positivo', 'As receitas realizadas superaram as despesas no período.', {'receitas': receitas, 'despesas': despesas, 'saldo': metricas['saldo']}, {'label': 'Ver fluxo de caixa', 'url': '/admin/fluxo-caixa'}, 2))
        elif despesas > receitas:
            signals.append(BusinessSignal('cash_flow', 'CASH_FLOW_NEGATIVE', 'attention', 'Despesas acima das receitas', 'As despesas realizadas superaram as receitas no período.', {'receitas': receitas, 'despesas': despesas, 'saldo': metricas['saldo']}, {'label': 'Ver fluxo de caixa', 'url': '/admin/fluxo-caixa'}, 3))
        for key, code, title in [('receitas', 'CASH_REVENUE_GROWTH', 'Receitas em crescimento'), ('despesas', 'CASH_EXPENSES_GROWTH', 'Despesas em crescimento')]:
            pct = comparativos.get(key, {}).get('percentual')
            if pct is not None and pct >= CASH_VARIATION_THRESHOLD_PCT:
                signals.append(BusinessSignal('cash_flow', code, 'positive' if key == 'receitas' else 'attention', 'info' if key == 'receitas' else 'atencao', title, f'{title} {pct:.1f}% em relação ao período anterior.', {'variacao_percentual': pct}, {'label': 'Ver fluxo de caixa', 'url': '/admin/fluxo-caixa'}, 2))
        return signals

    def _customer_signals(self, data: dict[str, Any]) -> list[BusinessSignal]:
        metricas = data['metricas']
        signals = []
        recorrentes = int(metricas.get('clientes_recorrentes') or 0)
        inativos = int(metricas.get('clientes_sem_compra_no_periodo') or 0)
        if recorrentes >= CUSTOMER_RECURRING_MIN_COUNT:
            signals.append(BusinessSignal('customers', 'CUSTOMER_RECURRING_ACTIVITY', 'positive', 'info', 'Clientes recorrentes identificados', f'{recorrentes} clientes tiveram compras recorrentes no período.', {'clientes_recorrentes': recorrentes}, {'label': 'Ver clientes recorrentes', 'url': '/admin/inteligencia/clientes?tipo=recorrentes'}, 1))
        if inativos >= CUSTOMER_INACTIVE_MIN_COUNT:
            signals.append(BusinessSignal(
                'customers', 'CUSTOMER_INACTIVE_PERIOD', 'attention', 'info',
                'Clientes sem compra no período',
                f'{inativos} clientes cadastrados não tiveram compra no período analisado.',
                {'clientes_sem_compra_no_periodo': inativos},
                {'label': 'Ver clientes sem compra', 'url': '/admin/inteligencia/clientes?tipo=sem_compra'}, 2,
            ))
        if not int(metricas.get('notas_autorizadas') or 0):
            signals.append(BusinessSignal(
                'customers', 'CUSTOMER_DATA_INSUFFICIENT', 'informational', 'info',
                'Histórico de clientes insuficiente',
                'Não existem compras autorizadas suficientes para analisar recorrência.',
                {'notas_autorizadas': 0},
                {'label': 'Ver clientes sem compra', 'url': '/admin/inteligencia/clientes?tipo=sem_compra'}, 1,
            ))
        return signals

    @staticmethod
    def _severity_order(severity: str) -> int:
        return {'atencao': 3, 'info': 2}.get(severity, 1)

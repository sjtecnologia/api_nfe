"""Análise determinística de vendas e narrativa opcional sob demanda."""

from __future__ import annotations

import json
from typing import Any

from services.ai_service import AIService, AIResponseFormatError, AIUsageLimitExceeded
from services.ai_providers import AIProviderError

from .data_types import PeriodoAnalise
from .sales_analysis_rules import (
    AVERAGE_TICKET_DROP_THRESHOLD_PCT,
    AVERAGE_TICKET_GROWTH_THRESHOLD_PCT,
    HIGH_CANCELLATION_RATE_THRESHOLD_PCT,
    HIGH_REJECTION_RATE_THRESHOLD_PCT,
    MIN_COMPARISON_DOCUMENTS,
    PRODUCT_CONCENTRATION_THRESHOLD_PCT,
    SALES_REVENUE_DROP_THRESHOLD_PCT,
    SALES_REVENUE_GROWTH_THRESHOLD_PCT,
)


class SalesAnalysisService:
    def __init__(self, db, aggregator=None):
        self.db = db
        self.aggregator = aggregator

    def analyze(self, cliente_id: int, periodo: PeriodoAnalise) -> dict[str, Any]:
        from .sales_data_aggregator import SalesDataAggregator

        aggregator = self.aggregator or SalesDataAggregator(self.db)
        data = aggregator.aggregate(cliente_id, periodo)
        metricas = data['metricas']
        comparativos = data['comparativos']
        qualidade = data['qualidade_dados']
        indicadores: list[dict[str, Any]] = []

        comparison_allowed = (
            qualidade['suficiente']
            and metricas['quantidade_autorizada'] >= MIN_COMPARISON_DOCUMENTS
        )
        revenue_pct = comparativos['faturamento']['percentual']
        ticket_pct = comparativos['ticket_medio']['percentual']

        if comparison_allowed and revenue_pct is not None:
            if revenue_pct >= SALES_REVENUE_GROWTH_THRESHOLD_PCT:
                indicadores.append(self._indicator(
                    'SALES_REVENUE_GROWTH', 'positivo', 'info',
                    'Faturamento em crescimento',
                    f"O faturamento aumentou {revenue_pct:.1f}% em relação ao período anterior.",
                    {'atual': metricas['faturamento'], 'anterior': self._previous_value(comparativos, 'faturamento', metricas['faturamento']), 'variacao_percentual': revenue_pct},
                ))
            elif revenue_pct <= SALES_REVENUE_DROP_THRESHOLD_PCT:
                indicadores.append(self._indicator(
                    'SALES_REVENUE_DROP', 'atencao', 'atencao',
                    'Faturamento em queda',
                    f"O faturamento caiu {abs(revenue_pct):.1f}% em relação ao período anterior.",
                    {'atual': metricas['faturamento'], 'anterior': self._previous_value(comparativos, 'faturamento', metricas['faturamento']), 'variacao_percentual': revenue_pct},
                ))

        if comparison_allowed and ticket_pct is not None:
            if ticket_pct >= AVERAGE_TICKET_GROWTH_THRESHOLD_PCT:
                indicadores.append(self._indicator(
                    'AVERAGE_TICKET_GROWTH', 'positivo', 'info',
                    'Ticket médio em crescimento',
                    f"O ticket médio aumentou {ticket_pct:.1f}% em relação ao período anterior.",
                    {'atual': metricas['ticket_medio'], 'variacao_percentual': ticket_pct},
                ))
            elif ticket_pct <= AVERAGE_TICKET_DROP_THRESHOLD_PCT:
                indicadores.append(self._indicator(
                    'AVERAGE_TICKET_DROP', 'atencao', 'atencao',
                    'Ticket médio em queda',
                    f"O ticket médio caiu {abs(ticket_pct):.1f}% em relação ao período anterior.",
                    {'atual': metricas['ticket_medio'], 'variacao_percentual': ticket_pct},
                ))

        if metricas['taxa_cancelamento'] >= HIGH_CANCELLATION_RATE_THRESHOLD_PCT:
            indicadores.append(self._indicator(
                'HIGH_CANCELLATION_RATE', 'atencao', 'atencao',
                'Cancelamentos merecem atenção',
                f"Cancelamentos representam {metricas['taxa_cancelamento']:.1f}% dos documentos do período.",
                {'taxa_percentual': metricas['taxa_cancelamento'], 'quantidade': metricas['quantidade_cancelada']},
            ))

        if metricas['taxa_rejeicao'] >= HIGH_REJECTION_RATE_THRESHOLD_PCT:
            indicadores.append(self._indicator(
                'HIGH_REJECTION_RATE', 'atencao', 'atencao',
                'Rejeições merecem atenção',
                f"Rejeições representam {metricas['taxa_rejeicao']:.1f}% dos documentos do período.",
                {'taxa_percentual': metricas['taxa_rejeicao'], 'quantidade': metricas['quantidade_rejeitada']},
            ))

        produtos = data['listas'].get('produtos_mais_vendidos', [])
        if (
            metricas['quantidade_autorizada'] > 0
            and metricas['faturamento'] > 0
            and produtos
            and produtos[0].get('participacao_faturamento_pct', 0) >= PRODUCT_CONCENTRATION_THRESHOLD_PCT
        ):
            indicadores.append(self._indicator(
                'PRODUCT_CONCENTRATION', 'atencao', 'informacao',
                'Faturamento concentrado em um produto',
                f"{produtos[0]['descricao']} representa {produtos[0]['participacao_faturamento_pct']:.1f}% do faturamento dos produtos destacados.",
                {'produto': produtos[0]['descricao'], 'participacao_percentual': produtos[0]['participacao_faturamento_pct']},
            ))

        if metricas['quantidade_autorizada'] == 0:
            qualidade['avisos'].append('Não encontramos vendas autorizadas no período selecionado.')
        elif not comparison_allowed:
            qualidade['avisos'].append('Ainda não há dados suficientes para uma comparação confiável.')

        positivos = [item for item in indicadores if item['tipo'] == 'positivo']
        atencao = [item for item in indicadores if item['tipo'] == 'atencao']
        return {
            'domain': 'sales',
            'periodo': data['periodo'],
            'metricas': metricas,
            'comparativos': comparativos,
            'indicadores': indicadores,
            'destaques': positivos,
            'pontos_atencao': atencao,
            'listas': data['listas'],
            'qualidade_dados': qualidade,
            'narrativa': None,
        }

    def explain(self, analysis: dict[str, Any], cliente_id: int, user_id: int | None) -> dict[str, Any]:
        if not analysis['qualidade_dados']['suficiente']:
            return {'narrativa': None, 'warning': 'Dados insuficientes para gerar explicação com IA.'}

        context = {
            'faturamento': {
                'atual': analysis['metricas']['faturamento'],
                'anterior': self._previous_value(analysis['comparativos'], 'faturamento', analysis['metricas']['faturamento']),
                'variacao': analysis['comparativos']['faturamento'],
            },
            'ticket_medio': {
                'atual': analysis['metricas']['ticket_medio'],
                'variacao': analysis['comparativos']['ticket_medio'],
            },
            'documentos': {
                key: analysis['metricas'][key]
                for key in ('quantidade_documentos', 'quantidade_autorizada', 'quantidade_cancelada', 'quantidade_rejeitada')
            },
            'produtos': analysis['listas'].get('produtos_mais_vendidos', []),
            'indicadores': analysis['indicadores'],
        }
        try:
            result = AIService(db=self.db).chat(
                prompt_name='sales_analysis',
                user_message='Explique esta análise histórica de vendas em português-BR, separando observações de recomendações.',
                context=context,
                cliente_id=cliente_id,
                user_id=user_id,
                functionality='sales_analysis_narrative',
                tools_scope='business',
                record=True,
            )
            return {'narrativa': (result.get('content') or '').strip() or None, 'model': result.get('model')}
        except (AIProviderError, AIResponseFormatError, AIUsageLimitExceeded) as exc:
            return {'narrativa': None, 'error': str(exc)}

    @staticmethod
    def _indicator(codigo, tipo, severidade, titulo, descricao, evidencias):
        return {'codigo': codigo, 'tipo': tipo, 'severidade': severidade, 'titulo': titulo, 'descricao': descricao, 'evidencias': evidencias}

    @staticmethod
    def _previous_value(comparativos, key, current):
        variation = comparativos.get(key, {})
        absolute = variation.get('absoluta')
        return None if absolute is None else round(current - absolute, 2)

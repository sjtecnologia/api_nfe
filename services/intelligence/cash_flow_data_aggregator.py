"""Agregação histórica determinística do fluxo de caixa."""

from __future__ import annotations

from datetime import datetime, time
from sqlalchemy import text

from .data_types import DadosAgregados, PeriodoAnalise
from .date_ranges import periodo_anterior, variacao_atual_anterior
from .data_quality import qualidade_periodo


class CashFlowDataAggregator:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _bounds(periodo: PeriodoAnalise) -> dict[str, datetime]:
        return {
            'inicio': datetime.combine(periodo.inicio, time.min),
            'fim': datetime.combine(periodo.fim, time.max),
        }

    def _summary(self, cliente_id: int, periodo: PeriodoAnalise):
        return self.db.execute(text("""
            SELECT
                COALESCE(SUM(CASE WHEN tipo_lancamento = 'RECEITA' THEN valor ELSE 0 END), 0) AS receitas,
                COALESCE(SUM(CASE WHEN tipo_lancamento = 'DESPESA' THEN valor ELSE 0 END), 0) AS despesas,
                COUNT(*) AS lancamentos
            FROM fluxo_caixa_lancamentos
            WHERE cliente_id = :cliente_id
              AND data_lancamento BETWEEN :inicio AND :fim
        """), {'cliente_id': cliente_id, **self._bounds(periodo)}).fetchone()

    def _categories(self, cliente_id: int, periodo: PeriodoAnalise):
        rows = self.db.execute(text("""
            SELECT categoria, tipo_lancamento, COALESCE(SUM(valor), 0) AS valor, COUNT(*) AS quantidade
            FROM fluxo_caixa_lancamentos
            WHERE cliente_id = :cliente_id
              AND data_lancamento BETWEEN :inicio AND :fim
            GROUP BY categoria, tipo_lancamento
            ORDER BY valor DESC, categoria
        """), {'cliente_id': cliente_id, **self._bounds(periodo)}).fetchall()
        return [
            {'categoria': row.categoria, 'tipo_lancamento': row.tipo_lancamento,
             'valor': float(row.valor or 0), 'quantidade': int(row.quantidade or 0)}
            for row in rows
        ]

    def aggregate(self, cliente_id: int, periodo: PeriodoAnalise) -> dict:
        atual = self._summary(cliente_id, periodo)
        anterior_periodo = periodo_anterior(periodo)
        anterior = self._summary(cliente_id, anterior_periodo)
        receitas = float(atual.receitas or 0)
        despesas = float(atual.despesas or 0)
        receitas_anterior = float(anterior.receitas or 0)
        despesas_anterior = float(anterior.despesas or 0)

        qualidade = DadosAgregados(cliente_id, periodo).qualidade_dados
        qualidade.origens.extend(['fluxo_caixa_lancamentos', 'fluxo_caixa_categorias'])
        qualidade_periodo(qualidade, int(atual.lancamentos or 0), 'lançamentos de fluxo de caixa')

        resultado = DadosAgregados(
            cliente_id=cliente_id,
            periodo=periodo,
            metricas={
                'receitas': receitas,
                'despesas': despesas,
                'saldo': receitas - despesas,
                'quantidade_lancamentos': int(atual.lancamentos or 0),
            },
            comparativos={
                'periodo_anterior': anterior_periodo.to_dict(),
                'receitas': variacao_atual_anterior(receitas, receitas_anterior),
                'despesas': variacao_atual_anterior(despesas, despesas_anterior),
                'saldo': variacao_atual_anterior(receitas - despesas, receitas_anterior - despesas_anterior),
            },
            listas={
                'categorias_receita': [item for item in self._categories(cliente_id, periodo) if item['tipo_lancamento'] == 'RECEITA'],
                'categorias_despesa': [item for item in self._categories(cliente_id, periodo) if item['tipo_lancamento'] == 'DESPESA'],
            },
            qualidade_dados=qualidade,
        )
        return resultado.to_dict()

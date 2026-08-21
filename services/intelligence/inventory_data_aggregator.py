"""Agregação determinística de estoque por empresa."""

from __future__ import annotations

from datetime import datetime, time
from sqlalchemy import text

from .data_quality import qualidade_periodo
from .data_types import DadosAgregados, PeriodoAnalise


class InventoryDataAggregator:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _bounds(periodo: PeriodoAnalise) -> dict[str, datetime]:
        return {
            'inicio': datetime.combine(periodo.inicio, time.min),
            'fim': datetime.combine(periodo.fim, time.max),
        }

    def aggregate(self, cliente_id: int, periodo: PeriodoAnalise) -> dict:
        params = {'cliente_id': cliente_id, **self._bounds(periodo)}
        resumo = self.db.execute(text("""
            SELECT
                COALESCE(SUM(CASE WHEN tipo_movimentacao = 'ENTRADA' THEN quantidade ELSE 0 END), 0) AS entradas,
                COALESCE(SUM(CASE WHEN tipo_movimentacao = 'SAIDA' THEN quantidade ELSE 0 END), 0) AS saidas,
                COUNT(DISTINCT produto_id) AS produtos_movimentados,
                COUNT(*) AS movimentacoes
            FROM estoque_movimentacoes
            WHERE cliente_id = :cliente_id
              AND data_movimentacao BETWEEN :inicio AND :fim
        """), params).fetchone()

        produtos = self.db.execute(text("""
            SELECT p.produto_id, p.descricao, p.ativo,
                   COALESCE(SUM(CASE WHEN em.tipo_movimentacao = 'ENTRADA' THEN em.quantidade ELSE -em.quantidade END), 0) AS saldo,
                   COUNT(em.movimentacao_id) AS movimentacoes
            FROM produtos p
            LEFT JOIN estoque_movimentacoes em
              ON em.produto_id = p.produto_id
             AND em.cliente_id = :cliente_id
             AND em.data_movimentacao BETWEEN :inicio AND :fim
            WHERE p.cliente_id = :cliente_id
              AND p.ativo = true
            GROUP BY p.produto_id, p.descricao, p.ativo
            ORDER BY movimentacoes DESC, p.descricao
        """), params).fetchall()

        maior = [
            {'produto_id': int(row.produto_id), 'descricao': row.descricao,
             'saldo': float(row.saldo or 0), 'movimentacoes': int(row.movimentacoes or 0)}
            for row in produtos[:10] if int(row.movimentacoes or 0) > 0
        ]
        menor = [
            {'produto_id': int(row.produto_id), 'descricao': row.descricao,
             'saldo': float(row.saldo or 0), 'movimentacoes': int(row.movimentacoes or 0)}
            for row in sorted(produtos, key=lambda row: (int(row.movimentacoes or 0), row.descricao))[:10]
        ]
        sem_movimentacao = sum(1 for row in produtos if int(row.movimentacoes or 0) == 0)

        qualidade = DadosAgregados(cliente_id, periodo).qualidade_dados
        qualidade.origens.extend(['estoque_movimentacoes', 'produtos'])
        qualidade_periodo(qualidade, int(resumo.movimentacoes or 0), 'movimentações de estoque')
        qualidade.suficiente = True if int(resumo.movimentacoes or 0) > 0 else False
        qualidade.avisos.append('Estoque mínimo não está configurado no cadastro atual de produtos.')

        resultado = DadosAgregados(
            cliente_id=cliente_id,
            periodo=periodo,
            metricas={
                'entradas': float(resumo.entradas or 0),
                'saidas': float(resumo.saidas or 0),
                'saldo': float(resumo.entradas or 0) - float(resumo.saidas or 0),
                'produtos_movimentados': int(resumo.produtos_movimentados or 0),
                'produtos_sem_movimentacao': sem_movimentacao,
                'movimentacoes': int(resumo.movimentacoes or 0),
                'estoque_minimo_configurado': False,
            },
            listas={'produtos_maior_movimentacao': maior, 'produtos_menor_movimentacao': menor},
            qualidade_dados=qualidade,
        )
        return resultado.to_dict()

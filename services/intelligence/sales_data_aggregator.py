"""Agregação determinística de vendas a partir de NF-e/NFC-e autorizadas."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from sqlalchemy import text

from .data_quality import marcar_historico_insuficiente, qualidade_periodo
from .data_types import DadosAgregados, PeriodoAnalise
from .date_ranges import periodo_anterior, variacao_atual_anterior


class SalesDataAggregator:
    """Calcula indicadores comerciais sem enviar registros crus para a IA."""

    def __init__(self, db):
        self.db = db

    @staticmethod
    def _bounds(periodo: PeriodoAnalise) -> dict[str, datetime]:
        return {
            'inicio': datetime.combine(periodo.inicio, time.min),
            'fim': datetime.combine(periodo.fim, time.max),
        }

    @staticmethod
    def _operation_filter() -> str:
        # O legado usa 1 para saída; valores textuais são aceitos para compatibilidade.
        return "COALESCE(UPPER(n.tipo_nfe::text), '1') NOT IN ('0', 'ENTRADA', 'E')"

    def _summary(self, cliente_id: int, periodo: PeriodoAnalise) -> Any:
        params = {'cliente_id': cliente_id, **self._bounds(periodo)}
        return self.db.execute(text(f"""
            SELECT
                COUNT(*) AS documentos,
                COUNT(*) FILTER (WHERE UPPER(COALESCE(n.status, '')) = 'AUTORIZADA') AS autorizados,
                COUNT(*) FILTER (WHERE UPPER(COALESCE(n.status, '')) = 'CANCELADA') AS cancelados,
                COUNT(*) FILTER (WHERE UPPER(COALESCE(n.status, '')) IN ('REJEITADA', 'DENEGADA')) AS rejeitados,
                COALESCE(SUM(CASE WHEN UPPER(COALESCE(n.status, '')) = 'AUTORIZADA' THEN COALESCE(n.valor_total, 0) ELSE 0 END), 0) AS faturamento,
                COALESCE(AVG(CASE WHEN UPPER(COALESCE(n.status, '')) = 'AUTORIZADA' THEN n.valor_total END), 0) AS ticket_medio
            FROM nfe_emitidas n
            WHERE n.cliente_id = :cliente_id
              AND COALESCE(n.data_emissao, n.data_criacao) BETWEEN :inicio AND :fim
              AND {self._operation_filter()}
        """), params).fetchone()

    def _items(self, cliente_id: int, periodo: PeriodoAnalise, order: str) -> list[dict[str, Any]]:
        params = {'cliente_id': cliente_id, **self._bounds(periodo)}
        rows = self.db.execute(text(f"""
            SELECT
                COALESCE(NULLIF(item->>'produto_id', ''), NULLIF(item->>'codigo_produto', ''), '') AS produto_id,
                COALESCE(item->>'descricao', 'Produto não informado') AS descricao,
                COALESCE(SUM(COALESCE(NULLIF(item->>'quantidade', '')::numeric, 0)), 0) AS quantidade,
                COALESCE(SUM(COALESCE(NULLIF(item->>'valor_total', '')::numeric, 0)), 0) AS valor_total,
                COUNT(*) AS ocorrencias
            FROM nfe_emitidas n
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(n.json_nfe->'items', '[]'::jsonb)) AS item
            WHERE n.cliente_id = :cliente_id
              AND COALESCE(n.data_emissao, n.data_criacao) BETWEEN :inicio AND :fim
              AND UPPER(COALESCE(n.status, '')) = 'AUTORIZADA'
              AND {self._operation_filter()}
              AND item->>'descricao' IS NOT NULL
            GROUP BY 1, 2
            ORDER BY {order}
            LIMIT 10
        """), params).fetchall()
        items = [
            {
                'produto_id': row.produto_id or None,
                'descricao': row.descricao,
                'quantidade': float(row.quantidade or 0),
                'valor_total': float(row.valor_total or 0),
                'ocorrencias': int(row.ocorrencias or 0),
            }
            for row in rows
        ]
        total_valor = sum(item['valor_total'] for item in items)
        for item in items:
            item['participacao_faturamento_pct'] = round(
                (item['valor_total'] / total_valor * 100) if total_valor else 0,
                2,
            )
        return items

    def _buyers(self, cliente_id: int, periodo: PeriodoAnalise) -> list[dict[str, Any]]:
        params = {'cliente_id': cliente_id, **self._bounds(periodo)}
        rows = self.db.execute(text(f"""
            SELECT
                COALESCE(NULLIF(n.destinatario_razao_social, ''), 'Comprador não informado') AS nome,
                COUNT(*) AS documentos,
                COALESCE(SUM(n.valor_total), 0) AS faturamento
            FROM nfe_emitidas n
            WHERE n.cliente_id = :cliente_id
              AND COALESCE(n.data_emissao, n.data_criacao) BETWEEN :inicio AND :fim
              AND UPPER(COALESCE(n.status, '')) = 'AUTORIZADA'
              AND {self._operation_filter()}
            GROUP BY 1
            ORDER BY faturamento DESC
            LIMIT 5
        """), params).fetchall()
        return [
            {
                'nome': row.nome,
                'documentos': int(row.documentos or 0),
                'faturamento': float(row.faturamento or 0),
            }
            for row in rows
        ]

    def aggregate(self, cliente_id: int, periodo: PeriodoAnalise) -> dict[str, Any]:
        atual = self._summary(cliente_id, periodo)
        anterior_periodo = periodo_anterior(periodo)
        anterior = self._summary(cliente_id, anterior_periodo)

        top = self._items(cliente_id, periodo, 'quantidade DESC, valor_total DESC')
        bottom = self._items(cliente_id, periodo, 'quantidade ASC, valor_total ASC')
        compradores = self._buyers(cliente_id, periodo)
        params = {'cliente_id': cliente_id, **self._bounds(periodo)}
        total_itens = self.db.execute(text(f"""
            SELECT COALESCE(SUM(COALESCE(NULLIF(item->>'quantidade', '')::numeric, 0)), 0) AS total
            FROM nfe_emitidas n
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(n.json_nfe->'items', '[]'::jsonb)) AS item
            WHERE n.cliente_id = :cliente_id
              AND COALESCE(n.data_emissao, n.data_criacao) BETWEEN :inicio AND :fim
              AND UPPER(COALESCE(n.status, '')) = 'AUTORIZADA'
              AND {self._operation_filter()}
        """), params).scalar() or 0

        qualidade = DadosAgregados(cliente_id, periodo).qualidade_dados
        qualidade.origens.extend(['nfe_emitidas', 'nfe_emitidas.json_nfe.items'])
        qualidade_periodo(qualidade, int(atual.documentos or 0), 'vendas')
        marcar_historico_insuficiente(
            qualidade,
            int(atual.autorizados or 0),
            1,
            'Não existem documentos autorizados suficientes para análise comercial.',
        )

        faturamento = float(atual.faturamento or 0)
        faturamento_anterior = float(anterior.faturamento or 0)
        ticket_medio = float(atual.ticket_medio or 0)
        ticket_medio_anterior = float(anterior.ticket_medio or 0)
        documentos = int(atual.documentos or 0)
        autorizados = int(atual.autorizados or 0)
        cancelados = int(atual.cancelados or 0)
        rejeitados = int(atual.rejeitados or 0)
        resultado = DadosAgregados(
            cliente_id=cliente_id,
            periodo=periodo,
            metricas={
                'quantidade_documentos': documentos,
                'quantidade_autorizada': autorizados,
                'quantidade_cancelada': cancelados,
                'quantidade_rejeitada': rejeitados,
                'faturamento': faturamento,
                'ticket_medio': ticket_medio,
                'taxa_cancelamento': round(cancelados / documentos * 100, 2) if documentos else 0,
                'taxa_rejeicao': round(rejeitados / documentos * 100, 2) if documentos else 0,
                'quantidade_itens_vendidos': float(total_itens),
            },
            comparativos={
                'periodo_anterior': anterior_periodo.to_dict(),
                'faturamento': variacao_atual_anterior(faturamento, faturamento_anterior),
                'documentos_autorizados': variacao_atual_anterior(autorizados, int(anterior.autorizados or 0)),
                'ticket_medio': variacao_atual_anterior(ticket_medio, ticket_medio_anterior),
            },
            listas={
                'produtos_mais_vendidos': top,
                'produtos_menor_movimentacao': bottom,
                'principais_compradores': compradores,
            },
            qualidade_dados=qualidade,
        )
        return resultado.to_dict()

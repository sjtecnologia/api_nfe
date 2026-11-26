"""Agregação de relacionamento de clientes sem expor dados pessoais."""

from __future__ import annotations

from datetime import datetime, time
from sqlalchemy import text

from .data_quality import qualidade_periodo
from .data_types import DadosAgregados, PeriodoAnalise


class CustomerDataAggregator:
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
        total = self.db.execute(text("""
            SELECT COUNT(*) FROM destinatarios_nfe
            WHERE cliente_id = :cliente_id
        """), {'cliente_id': cliente_id}).scalar() or 0

        compras = self.db.execute(text("""
            SELECT
                COUNT(DISTINCT NULLIF(regexp_replace(COALESCE(destinatario_cnpj_cpf, ''), '[^0-9]', '', 'g'), '')) AS clientes_com_compra,
                COUNT(*) AS notas
            FROM nfe_emitidas
            WHERE cliente_id = :cliente_id
              AND COALESCE(data_emissao, data_criacao) BETWEEN :inicio AND :fim
              AND UPPER(COALESCE(status, '')) = 'AUTORIZADA'
              AND COALESCE(UPPER(tipo_nfe::text), '1') NOT IN ('0', 'ENTRADA', 'E')
              AND NULLIF(regexp_replace(COALESCE(destinatario_cnpj_cpf, ''), '[^0-9]', '', 'g'), '') IS NOT NULL
        """), params).fetchone()

        recorrentes = self.db.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT regexp_replace(destinatario_cnpj_cpf, '[^0-9]', '', 'g') AS documento
                FROM nfe_emitidas
                WHERE cliente_id = :cliente_id
                  AND COALESCE(data_emissao, data_criacao) BETWEEN :inicio AND :fim
                  AND UPPER(COALESCE(status, '')) = 'AUTORIZADA'
                  AND COALESCE(UPPER(tipo_nfe::text), '1') NOT IN ('0', 'ENTRADA', 'E')
                  AND NULLIF(regexp_replace(COALESCE(destinatario_cnpj_cpf, ''), '[^0-9]', '', 'g'), '') IS NOT NULL
                GROUP BY documento
                HAVING COUNT(*) >= 2
            ) recorrentes
        """), params).scalar() or 0

        ultima = self.db.execute(text("""
            SELECT COUNT(*) FROM destinatarios_nfe d
            WHERE d.cliente_id = :cliente_id
              AND NOT EXISTS (
                  SELECT 1 FROM nfe_emitidas n
                  WHERE n.cliente_id = d.cliente_id
                    AND regexp_replace(COALESCE(n.destinatario_cnpj_cpf, ''), '[^0-9]', '', 'g') = regexp_replace(COALESCE(d.cpf_cnpj, ''), '[^0-9]', '', 'g')
                    AND UPPER(COALESCE(n.status, '')) = 'AUTORIZADA'
                    AND COALESCE(n.data_emissao, n.data_criacao) BETWEEN :inicio AND :fim
              )
        """), params).scalar() or 0

        qualidade = DadosAgregados(cliente_id, periodo).qualidade_dados
        qualidade.origens.extend(['destinatarios_nfe', 'nfe_emitidas'])
        qualidade_periodo(qualidade, int(compras.notas or 0), 'compras de clientes')
        qualidade.avisos.append('CPF/CNPJ é usado apenas para relacionamento interno e não é retornado no contrato.')

        resultado = DadosAgregados(
            cliente_id=cliente_id,
            periodo=periodo,
            metricas={
                'quantidade_total_clientes': int(total),
                'clientes_com_compra': int(compras.clientes_com_compra or 0),
                'clientes_sem_compra_no_periodo': max(int(total) - int(compras.clientes_com_compra or 0), 0),
                'clientes_recorrentes': int(recorrentes),
                'clientes_sem_compra_no_periodo_cadastrados': int(ultima),
                'notas_autorizadas': int(compras.notas or 0),
            },
            listas={},
            qualidade_dados=qualidade,
        )
        return resultado.to_dict()

    def identified_customers(self, cliente_id: int, periodo: PeriodoAnalise, tipo: str = 'todos') -> list[dict]:
        """Retorna apenas dados comerciais seguros para a listagem do diagnóstico."""
        params = {'cliente_id': cliente_id, **self._bounds(periodo)}
        if tipo == 'sem_compra':
            query = text("""
            SELECT d.nome_razao_social AS nome, 0 AS compras, NULL AS ultima_compra
            FROM destinatarios_nfe d
            WHERE d.cliente_id = :cliente_id
              AND NOT EXISTS (
                  SELECT 1 FROM nfe_emitidas n
                  WHERE n.cliente_id = d.cliente_id
                    AND regexp_replace(COALESCE(n.destinatario_cnpj_cpf, ''), '[^0-9]', '', 'g') = regexp_replace(COALESCE(d.cpf_cnpj, ''), '[^0-9]', '', 'g')
                    AND UPPER(COALESCE(n.status, '')) = 'AUTORIZADA'
                    AND COALESCE(n.data_emissao, n.data_criacao) BETWEEN :inicio AND :fim
                    AND COALESCE(UPPER(n.tipo_nfe::text), '1') NOT IN ('0', 'ENTRADA', 'E')
              )
            ORDER BY d.nome_razao_social
            LIMIT 500
            """)
        elif tipo == 'recorrentes':
            query = text("""
            SELECT COALESCE(NULLIF(n.destinatario_razao_social, ''), 'Cliente não informado') AS nome,
                   COUNT(*) AS compras, MAX(COALESCE(n.data_emissao, n.data_criacao)) AS ultima_compra
            FROM nfe_emitidas n
            WHERE n.cliente_id = :cliente_id
              AND COALESCE(n.data_emissao, n.data_criacao) BETWEEN :inicio AND :fim
              AND UPPER(COALESCE(n.status, '')) = 'AUTORIZADA'
              AND COALESCE(UPPER(n.tipo_nfe::text), '1') NOT IN ('0', 'ENTRADA', 'E')
            GROUP BY 1
            HAVING COUNT(*) >= 2
            ORDER BY compras DESC, ultima_compra DESC
            LIMIT 500
            """)
        else:
            query = text("""
            SELECT
                COALESCE(NULLIF(n.destinatario_razao_social, ''), 'Cliente não informado') AS nome,
                COUNT(*) AS compras,
                MAX(COALESCE(n.data_emissao, n.data_criacao)) AS ultima_compra
            FROM nfe_emitidas n
            WHERE n.cliente_id = :cliente_id
              AND COALESCE(n.data_emissao, n.data_criacao) BETWEEN :inicio AND :fim
              AND UPPER(COALESCE(n.status, '')) = 'AUTORIZADA'
              AND COALESCE(UPPER(n.tipo_nfe::text), '1') NOT IN ('0', 'ENTRADA', 'E')
            GROUP BY 1
            ORDER BY ultima_compra DESC, nome
            LIMIT 500
            """)
        rows = self.db.execute(query, params).fetchall()
        return [
            {
                'nome': row.nome,
                'compras': int(row.compras or 0),
                'ultima_compra': row.ultima_compra.isoformat() if row.ultima_compra else None,
                'recorrente': int(row.compras or 0) >= 2,
                'status_periodo': 'Sem compra no período' if tipo == 'sem_compra' else ('Recorrente' if int(row.compras or 0) >= 2 else 'Compra no período'),
            }
            for row in rows
        ]

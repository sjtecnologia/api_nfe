"""
Service de Relatórios - EmiteMax
Geração de relatórios gerenciais e operacionais para usuários

Relatórios Disponíveis:
1. Notas Emitidas (por período, cliente, status)
2. Faturamento (por período, produto, cliente)
3. Produtos/Serviços (ranking, análise tributária)
4. Impostos (consolidado tributário)
5. Exportação (Excel, PDF, CSV)

Desenvolvido por: EmiteMax
Data: 11/02/2026
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import text
from decimal import Decimal
import json


class RelatorioService:
    """Service para geração de relatórios do sistema"""
    
    def __init__(self, db):
        """
        Inicializa o service de relatórios
        
        Args:
            db: Sessão do banco de dados
        """
        self.db = db
    
    def relatorio_notas_emitidas(
        self,
        cliente_ids: List[int],
        data_inicio: datetime,
        data_fim: datetime,
        tipo_nota: Optional[str] = None,
        status: Optional[str] = None,
        modelo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera relatório de notas emitidas com filtros
        
        Args:
            cliente_ids: Lista de IDs dos clientes
            data_inicio: Data inicial do período
            data_fim: Data final do período
            tipo_nota: Filtro por tipo (entrada/saida)
            status: Filtro por status
            modelo: Filtro por modelo (55=NFe, 65=NFCe, etc)
        
        Returns:
            Dict com dados do relatório
        """
        # Construir query com filtros
        where_clauses = ["cliente_id IN :cliente_ids"]
        where_clauses.append("data_emissao BETWEEN :data_inicio AND :data_fim")
        
        params = {
            'cliente_ids': tuple(cliente_ids),
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }
        
        if tipo_nota:
            where_clauses.append("tipo_nfe = :tipo_nota")
            params['tipo_nota'] = tipo_nota
        
        if status:
            where_clauses.append("lower(status) = lower(:status)")
            params['status'] = status
        
        if modelo:
            where_clauses.append("modelo = :modelo")
            params['modelo'] = modelo
        
        where_sql = " AND ".join(where_clauses)
        
        # Query principal - notas
        query = text(f"""
            SELECT 
                nfe_emitida_id,
                numero as numero_nfe,
                serie,
                modelo,
                data_emissao,
                tipo_nfe as tipo_nota,
                status,
                chave_acesso,
                COALESCE(NULLIF(destinatario_razao_social, ''), 'Não informado') as nome_destinatario,
                destinatario_cnpj_cpf as cpf_cnpj_destinatario,
                valor_total,
                COALESCE(
                    (
                        SELECT SUM(CAST(item->>'valor_total' AS NUMERIC))
                        FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                    ),
                    valor_total
                ) as valor_produtos,
                COALESCE(
                    (
                        SELECT SUM(CAST(item->>'valor_icms' AS NUMERIC))
                        FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                        WHERE item->>'valor_icms' IS NOT NULL
                    ),
                    0
                ) as valor_icms,
                COALESCE(
                    (
                        SELECT SUM(CAST(item->>'valor_ipi' AS NUMERIC))
                        FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                        WHERE item->>'valor_ipi' IS NOT NULL
                    ),
                    0
                ) as valor_ipi,
                COALESCE(
                    (
                        SELECT SUM(CAST(item->>'valor_pis' AS NUMERIC))
                        FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                        WHERE item->>'valor_pis' IS NOT NULL
                    ),
                    0
                ) as valor_pis,
                COALESCE(
                    (
                        SELECT SUM(CAST(item->>'valor_cofins' AS NUMERIC))
                        FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                        WHERE item->>'valor_cofins' IS NOT NULL
                    ),
                    0
                ) as valor_cofins,
                data_criacao,
                'N' as contingencia
            FROM nfe_emitidas
            WHERE {where_sql}
            ORDER BY data_emissao DESC, numero DESC
        """)
        
        result = self.db.execute(query, params)
        notas = []
        
        for row in result:
            notas.append({
                'id': row.nfe_emitida_id,
                'numero_nfe': row.numero_nfe,
                'serie': row.serie,
                'modelo': row.modelo or '55',
                'data_emissao': row.data_emissao.strftime('%d/%m/%Y %H:%M') if row.data_emissao else '',
                'tipo_nota': row.tipo_nota,
                'status': row.status,
                'chave_acesso': row.chave_acesso,
                'destinatario': row.nome_destinatario,
                'cpf_cnpj': row.cpf_cnpj_destinatario,
                'valor_total': float(row.valor_total) if row.valor_total else 0.0,
                'valor_produtos': float(row.valor_produtos) if row.valor_produtos else 0.0,
                'valor_icms': float(row.valor_icms) if row.valor_icms else 0.0,
                'valor_ipi': float(row.valor_ipi) if row.valor_ipi else 0.0,
                'valor_pis': float(row.valor_pis) if row.valor_pis else 0.0,
                'valor_cofins': float(row.valor_cofins) if row.valor_cofins else 0.0,
                'contingencia': row.contingencia or False
            })
        
        # Calcular totalizadores
        totais = self._calcular_totais_notas(notas)
        
        # Estatísticas
        stats = self._calcular_estatisticas_notas(where_sql, params)
        
        return {
            'periodo': {
                'data_inicio': data_inicio.strftime('%d/%m/%Y'),
                'data_fim': data_fim.strftime('%d/%m/%Y')
            },
            'filtros': {
                'tipo_nota': tipo_nota,
                'status': status,
                'modelo': modelo
            },
            'notas': notas,
            'totais': totais,
            'estatisticas': stats,
            'total_registros': len(notas)
        }
    
    def relatorio_faturamento(
        self,
        cliente_ids: List[int],
        data_inicio: datetime,
        data_fim: datetime,
        agrupar_por: str = 'mes'  # 'dia', 'semana', 'mes'
    ) -> Dict[str, Any]:
        """
        Gera relatório de faturamento agrupado
        
        Args:
            cliente_ids: Lista de IDs dos clientes
            data_inicio: Data inicial do período
            data_fim: Data final do período
            agrupar_por: Tipo de agrupamento (dia/semana/mes)
        
        Returns:
            Dict com dados de faturamento
        """
        # Definir formato de agrupamento
        if agrupar_por == 'dia':
            date_format = '%Y-%m-%d'
            date_label = 'DATE(data_emissao)'
        elif agrupar_por == 'semana':
            date_format = '%Y-W%W'
            date_label = "TO_CHAR(data_emissao, 'IYYY-IW')"
        else:  # mes
            date_format = '%Y-%m'
            date_label = "TO_CHAR(data_emissao, 'YYYY-MM')"
        
        query = text(f"""
            WITH totais_nota AS (
                SELECT 
                    nfe_emitida_id,
                    data_emissao,
                    valor_total,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_total' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                        ),
                        valor_total
                    ) as valor_produtos,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_icms' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                            WHERE item->>'valor_icms' IS NOT NULL
                        ),
                        0
                    ) as total_icms,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_ipi' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                            WHERE item->>'valor_ipi' IS NOT NULL
                        ),
                        0
                    ) as total_ipi,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_pis' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                            WHERE item->>'valor_pis' IS NOT NULL
                        ),
                        0
                    ) as total_pis,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_cofins' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                            WHERE item->>'valor_cofins' IS NOT NULL
                        ),
                        0
                    ) as total_cofins
                FROM nfe_emitidas
                WHERE cliente_id IN :cliente_ids
                    AND data_emissao BETWEEN :data_inicio AND :data_fim
                    AND UPPER(status) = 'AUTORIZADA'
            )
            SELECT 
                {date_label} as periodo,
                COUNT(*) as quantidade_notas,
                SUM(valor_total) as valor_total,
                SUM(valor_produtos) as valor_produtos,
                SUM(total_icms) as total_icms,
                SUM(total_ipi) as total_ipi,
                SUM(total_pis) as total_pis,
                SUM(total_cofins) as total_cofins,
                AVG(valor_total) as ticket_medio
            FROM totais_nota
            GROUP BY {date_label}
            ORDER BY periodo
        """)
        
        result = self.db.execute(query, {
            'cliente_ids': tuple(cliente_ids),
            'data_inicio': data_inicio,
            'data_fim': data_fim
        })
        
        dados = []
        for row in result:
            dados.append({
                'periodo': str(row.periodo),
                'quantidade_notas': row.quantidade_notas,
                'valor_total': float(row.valor_total) if row.valor_total else 0.0,
                'valor_produtos': float(row.valor_produtos) if row.valor_produtos else 0.0,
                'total_icms': float(row.total_icms) if row.total_icms else 0.0,
                'total_ipi': float(row.total_ipi) if row.total_ipi else 0.0,
                'total_pis': float(row.total_pis) if row.total_pis else 0.0,
                'total_cofins': float(row.total_cofins) if row.total_cofins else 0.0,
                'ticket_medio': float(row.ticket_medio) if row.ticket_medio else 0.0
            })
        
        # Calcular totais gerais
        total_geral = sum(d['valor_total'] for d in dados)
        total_notas = sum(d['quantidade_notas'] for d in dados)
        total_impostos = sum(
            d['total_icms'] + d['total_ipi'] + d['total_pis'] + d['total_cofins']
            for d in dados
        )
        
        return {
            'periodo': {
                'data_inicio': data_inicio.strftime('%d/%m/%Y'),
                'data_fim': data_fim.strftime('%d/%m/%Y'),
                'agrupamento': agrupar_por
            },
            'dados': dados,
            'totais': {
                'valor_total': total_geral,
                'quantidade_notas': total_notas,
                'total_impostos': total_impostos,
                'ticket_medio': total_geral / total_notas if total_notas > 0 else 0.0
            }
        }
    
    def relatorio_produtos(
        self,
        cliente_ids: List[int],
        data_inicio: datetime,
        data_fim: datetime,
        limite: int = 50
    ) -> Dict[str, Any]:
        """
        Gera relatório de produtos/serviços mais vendidos
        
        Args:
            cliente_ids: Lista de IDs dos clientes
            data_inicio: Data inicial do período
            data_fim: Data final do período
            limite: Número máximo de produtos no ranking
        
        Returns:
            Dict com ranking de produtos
        """
        # Query para extrair produtos do JSON e agregar
        query = text("""
            WITH produtos_expandidos AS (
                SELECT 
                    n.nfe_emitida_id,
                    item->>'codigo_produto' as codigo,
                    item->>'descricao' as descricao,
                    item->>'ncm' as ncm,
                    item->>'unidade' as unidade,
                    CAST(item->>'quantidade' AS NUMERIC) as quantidade,
                    CAST(item->>'valor_unitario' AS NUMERIC) as valor_unitario,
                    CAST(item->>'valor_total' AS NUMERIC) as valor_total,
                    CAST(COALESCE(item->>'valor_icms', '0') AS NUMERIC) as valor_icms
                FROM nfe_emitidas n,
                     jsonb_array_elements(COALESCE(n.json_nfe->'items', '[]'::jsonb)) AS item
                WHERE n.cliente_id IN :cliente_ids
                    AND n.data_emissao BETWEEN :data_inicio AND :data_fim
                    AND UPPER(n.status) = 'AUTORIZADA'
                    AND item->>'codigo_produto' IS NOT NULL
            )
            SELECT 
                codigo,
                descricao,
                ncm,
                unidade,
                COUNT(DISTINCT nfe_emitida_id) as quantidade_notas,
                SUM(quantidade) as quantidade_total,
                AVG(valor_unitario) as valor_medio_unitario,
                SUM(valor_total) as valor_total_vendas,
                SUM(valor_icms) as total_icms
            FROM produtos_expandidos
            GROUP BY codigo, descricao, ncm, unidade
            ORDER BY valor_total_vendas DESC
            LIMIT :limite
        """)
        
        params = {
            'cliente_ids': tuple(cliente_ids),
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'limite': limite
        }
        
        result = self.db.execute(query, params)
        
        produtos = []
        total_vendas = 0.0
        
        for row in result:
            valor_total = float(row.valor_total_vendas) if row.valor_total_vendas else 0.0
            total_vendas += valor_total
            
            produtos.append({
                'codigo': row.codigo,
                'descricao': row.descricao,
                'ncm': row.ncm,
                'unidade': row.unidade,
                'quantidade_notas': row.quantidade_notas,
                'quantidade_total': float(row.quantidade_total) if row.quantidade_total else 0.0,
                'valor_medio_unitario': float(row.valor_medio_unitario) if row.valor_medio_unitario else 0.0,
                'valor_total_vendas': valor_total,
                'total_icms': float(row.total_icms) if row.total_icms else 0.0,
                'percentual_vendas': 0.0  # Será calculado depois
            })
        
        # Calcular percentuais
        for produto in produtos:
            if total_vendas > 0:
                produto['percentual_vendas'] = (produto['valor_total_vendas'] / total_vendas) * 100
        
        # Query para resumo geral
        query_resumo = text("""
            SELECT 
                COUNT(DISTINCT n.nfe_emitida_id) as total_notas,
                SUM(n.valor_total) as valor_total_vendas,
                AVG(n.valor_total) as ticket_medio
            FROM nfe_emitidas n
            WHERE n.cliente_id IN :cliente_ids
                AND n.data_emissao BETWEEN :data_inicio AND :data_fim
                AND UPPER(n.status) = 'AUTORIZADA'
        """)
        
        result_resumo = self.db.execute(query_resumo, {
            'cliente_ids': tuple(cliente_ids),
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }).fetchone()
        
        return {
            'periodo': {
                'data_inicio': data_inicio.strftime('%d/%m/%Y'),
                'data_fim': data_fim.strftime('%d/%m/%Y')
            },
            'produtos': produtos,
            'resumo': {
                'total_notas': result_resumo.total_notas if result_resumo else 0,
                'total_produtos': len(produtos),
                'valor_total_vendas': float(result_resumo.valor_total_vendas) if result_resumo and result_resumo.valor_total_vendas else 0.0,
                'ticket_medio': float(result_resumo.ticket_medio) if result_resumo and result_resumo.ticket_medio else 0.0
            }
        }
    
    def relatorio_impostos(
        self,
        cliente_ids: List[int],
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """
        Gera relatório consolidado de impostos
        
        Args:
            cliente_ids: Lista de IDs dos clientes
            data_inicio: Data inicial do período
            data_fim: Data final do período
        
        Returns:
            Dict com consolidado tributário
        """
        # Query para extrair impostos do JSON
        query = text("""
            WITH impostos_notas AS (
                SELECT 
                    nfe_emitida_id,
                    valor_total,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_icms' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                            WHERE item->>'valor_icms' IS NOT NULL
                        ),
                        0
                    ) as total_icms,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_ipi' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                            WHERE item->>'valor_ipi' IS NOT NULL
                        ),
                        0
                    ) as total_ipi,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_pis' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                            WHERE item->>'valor_pis' IS NOT NULL
                        ),
                        0
                    ) as total_pis,
                    COALESCE(
                        (
                            SELECT SUM(CAST(item->>'valor_cofins' AS NUMERIC))
                            FROM jsonb_array_elements(COALESCE(json_nfe->'items', '[]'::jsonb)) AS item
                            WHERE item->>'valor_cofins' IS NOT NULL
                        ),
                        0
                    ) as total_cofins,
                    total_ibs,
                    total_cbs
                FROM nfe_emitidas
                WHERE cliente_id IN :cliente_ids
                    AND data_emissao BETWEEN :data_inicio AND :data_fim
                    AND UPPER(status) = 'AUTORIZADA'
            )
            SELECT 
                COUNT(*) as total_notas,
                SUM(valor_total) as base_calculo,
                SUM(total_icms) as total_icms,
                SUM(total_ipi) as total_ipi,
                SUM(total_pis) as total_pis,
                SUM(total_cofins) as total_cofins,
                SUM(total_ibs) as total_ibs,
                SUM(total_cbs) as total_cbs
            FROM impostos_notas
        """)
        
        result = self.db.execute(query, {
            'cliente_ids': tuple(cliente_ids),
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }).fetchone()
        
        total_icms = float(result.total_icms) if result.total_icms else 0.0
        total_ipi = float(result.total_ipi) if result.total_ipi else 0.0
        total_pis = float(result.total_pis) if result.total_pis else 0.0
        total_cofins = float(result.total_cofins) if result.total_cofins else 0.0
        total_ibs = float(result.total_ibs) if result.total_ibs else 0.0
        total_cbs = float(result.total_cbs) if result.total_cbs else 0.0
        base_calculo = float(result.base_calculo) if result.base_calculo else 0.0
        
        total_impostos = total_icms + total_ipi + total_pis + total_cofins + total_ibs + total_cbs
        
        # Calcular alíquotas efetivas
        aliquota_efetiva_icms = (total_icms / base_calculo * 100) if base_calculo > 0 else 0.0
        aliquota_efetiva_ipi = (total_ipi / base_calculo * 100) if base_calculo > 0 else 0.0
        aliquota_efetiva_pis = (total_pis / base_calculo * 100) if base_calculo > 0 else 0.0
        aliquota_efetiva_cofins = (total_cofins / base_calculo * 100) if base_calculo > 0 else 0.0
        carga_tributaria = (total_impostos / base_calculo * 100) if base_calculo > 0 else 0.0
        
        # Query para detalhamento por CFOP
        query_cfop = text("""
            WITH cfop_impostos AS (
                SELECT 
                    n.nfe_emitida_id,
                    n.valor_total,
                    item->>'cfop' as cfop,
                    CAST(item->>'valor_total' AS NUMERIC) as valor_item,
                    CAST(COALESCE(item->>'valor_icms', '0') AS NUMERIC) as icms,
                    CAST(COALESCE(item->>'valor_ipi', '0') AS NUMERIC) as ipi,
                    CAST(COALESCE(item->>'valor_pis', '0') AS NUMERIC) as pis,
                    CAST(COALESCE(item->>'valor_cofins', '0') AS NUMERIC) as cofins
                FROM nfe_emitidas n,
                     jsonb_array_elements(COALESCE(n.json_nfe->'items', '[]'::jsonb)) AS item
                WHERE n.cliente_id IN :cliente_ids
                    AND n.data_emissao BETWEEN :data_inicio AND :data_fim
                    AND UPPER(n.status) = 'AUTORIZADA'
                    AND item->>'cfop' IS NOT NULL
            )
            SELECT 
                cfop,
                COUNT(DISTINCT nfe_emitida_id) as quantidade_notas,
                SUM(valor_item) as valor_total,
                SUM(icms) as total_icms,
                SUM(ipi) as total_ipi,
                SUM(pis) as total_pis,
                SUM(cofins) as total_cofins
            FROM cfop_impostos
            GROUP BY cfop
            ORDER BY cfop
        """)
        
        result_cfop = self.db.execute(query_cfop, {
            'cliente_ids': tuple(cliente_ids),
            'data_inicio': data_inicio,
            'data_fim': data_fim
        })
        
        detalhamento_cfop = []
        for row in result_cfop:
            detalhamento_cfop.append({
                'cfop': row.cfop,
                'quantidade_notas': row.quantidade_notas,
                'valor_total': float(row.valor_total) if row.valor_total else 0.0,
                'icms': float(row.total_icms) if row.total_icms else 0.0,
                'ipi': float(row.total_ipi) if row.total_ipi else 0.0,
                'pis': float(row.total_pis) if row.total_pis else 0.0,
                'cofins': float(row.total_cofins) if row.total_cofins else 0.0
            })
        
        return {
            'periodo': {
                'data_inicio': data_inicio.strftime('%d/%m/%Y'),
                'data_fim': data_fim.strftime('%d/%m/%Y')
            },
            'resumo': {
                'total_notas': result.total_notas if result else 0,
                'base_calculo': base_calculo,
                'total_impostos': total_impostos,
                'carga_tributaria_percentual': round(carga_tributaria, 2)
            },
            'impostos': {
                'icms': {
                    'valor': total_icms,
                    'aliquota_efetiva': round(aliquota_efetiva_icms, 2),
                    'percentual_total': round((total_icms / total_impostos * 100) if total_impostos > 0 else 0.0, 2)
                },
                'ipi': {
                    'valor': total_ipi,
                    'aliquota_efetiva': round(aliquota_efetiva_ipi, 2),
                    'percentual_total': round((total_ipi / total_impostos * 100) if total_impostos > 0 else 0.0, 2)
                },
                'pis': {
                    'valor': total_pis,
                    'aliquota_efetiva': round(aliquota_efetiva_pis, 2),
                    'percentual_total': round((total_pis / total_impostos * 100) if total_impostos > 0 else 0.0, 2)
                },
                'cofins': {
                    'valor': total_cofins,
                    'aliquota_efetiva': round(aliquota_efetiva_cofins, 2),
                    'percentual_total': round((total_cofins / total_impostos * 100) if total_impostos > 0 else 0.0, 2)
                },
                'ibs': {
                    'valor': total_ibs,
                    'percentual_total': round((total_ibs / total_impostos * 100) if total_impostos > 0 else 0.0, 2)
                },
                'cbs': {
                    'valor': total_cbs,
                    'percentual_total': round((total_cbs / total_impostos * 100) if total_impostos > 0 else 0.0, 2)
                }
            },
            'detalhamento_cfop': detalhamento_cfop
        }
    
    def _calcular_totais_notas(self, notas: List[Dict]) -> Dict[str, float]:
        """Calcula totalizadores de uma lista de notas"""
        return {
            'quantidade': len(notas),
            'valor_total': sum(n['valor_total'] for n in notas),
            'valor_produtos': sum(n['valor_produtos'] for n in notas),
            'valor_icms': sum(n['valor_icms'] for n in notas),
            'valor_ipi': sum(n['valor_ipi'] for n in notas),
            'valor_pis': sum(n['valor_pis'] for n in notas),
            'valor_cofins': sum(n['valor_cofins'] for n in notas)
        }
    
    def _calcular_estatisticas_notas(self, where_sql: str, params: Dict) -> Dict[str, Any]:
        """Calcula estatísticas adicionais das notas"""
        # Por status
        query_status = text(f"""
            SELECT 
                status,
                COUNT(*) as quantidade
            FROM nfe_emitidas
            WHERE {where_sql}
            GROUP BY status
        """)
        
        result_status = self.db.execute(query_status, params)
        por_status = {row.status: row.quantidade for row in result_status}
        
        # Por modelo
        query_modelo = text(f"""
            SELECT 
                COALESCE(modelo, '55') as modelo,
                COUNT(*) as quantidade
            FROM nfe_emitidas
            WHERE {where_sql}
            GROUP BY modelo
        """)
        
        result_modelo = self.db.execute(query_modelo, params)
        por_modelo = {row.modelo: row.quantidade for row in result_modelo}
        
        return {
            'por_status': por_status,
            'por_modelo': por_modelo
        }

"""
Serviço de Cálculo IBS/CBS - Versão 2.0
----------------------------------------
Implementa lógica de cálculo de tributos da Reforma Tributária (LC 214/2023)

Este módulo é uma estrutura preparatória. Os cálculos retornam valores
zerados até que as alíquotas oficiais sejam publicadas (2026+).

Autor: Sistema NFe
Data: 17/11/2025
Referência: Lei Complementar 214/2023 e Cartilha IBS FENACON
"""

from typing import Optional
from sqlalchemy import text
from database.connection import get_db


class CalculoIBS:
    """
    Serviço de cálculo IBS/CBS
    
    IBS = Imposto sobre Bens e Serviços (substitui ICMS + ISS)
    CBS = Contribuição sobre Bens e Serviços (substitui PIS + COFINS)
    """
    
    def __init__(self):
        """Inicializa calculadora com alíquotas padrão (placeholders)"""
        self.aliquota_ibs_padrao = 0.00  # Aguardando regulamentação
        self.aliquota_cbs_padrao = 0.00  # Aguardando regulamentação
    
    def calcular(
        self,
        valor_base: float,
        codigo_servico: str,
        municipio_origem: str,
        municipio_destino: Optional[str] = None,
        regime_tributario: str = 'normal'
    ) -> dict:
        """
        Calcula IBS e CBS para uma operação
        
        Args:
            valor_base: Valor base para cálculo
            codigo_servico: Código do serviço LC 116/2003 (ex: '01.01')
            municipio_origem: Código IBGE do município de origem
            municipio_destino: Código IBGE do município de destino (opcional)
            regime_tributario: 'normal' ou 'simples'
        
        Returns:
            dict com:
                - valor_base: Valor base
                - aliquota_ibs: Alíquota IBS aplicada (%)
                - valor_ibs: Valor IBS calculado
                - aliquota_cbs: Alíquota CBS aplicada (%)
                - valor_cbs: Valor CBS calculado
                - total_tributos: Soma IBS + CBS
                - observacoes: Observações sobre o cálculo
        """
        
        # FASE 1: Retorna estrutura preparatória (valores zerados)
        # FASE 2: Implementar cálculo real quando alíquotas disponíveis
        
        resultado = {
            'valor_base': valor_base,
            'aliquota_ibs': self.aliquota_ibs_padrao,
            'valor_ibs': 0.00,
            'aliquota_cbs': self.aliquota_cbs_padrao,
            'valor_cbs': 0.00,
            'total_tributos': 0.00,
            'observacoes': 'Cálculo preparatório - aguardando alíquotas oficiais (2026)'
        }
        
        return resultado
    
    def buscar_aliquota_municipio(
        self,
        codigo_municipio: str,
        data_referencia: Optional[str] = None
    ) -> Optional[float]:
        """
        Busca alíquota IBS vigente para um município
        
        Args:
            codigo_municipio: Código IBGE do município
            data_referencia: Data de referência (formato ISO)
        
        Returns:
            Alíquota IBS ou None se não encontrada
        """
        
        if data_referencia is None:
            from datetime import date
            data_referencia = date.today().isoformat()
        
        db = next(get_db())
        try:
            query = text("""
                SELECT aliquota_ibs 
                FROM aliquotas_ibs_municipio
                WHERE codigo_municipio = :codigo_municipio
                  AND ativo = TRUE
                  AND vigencia_inicio <= :data_referencia
                  AND (vigencia_fim IS NULL OR vigencia_fim >= :data_referencia)
                ORDER BY vigencia_inicio DESC
                LIMIT 1
            """)
            
            result = db.execute(query, {
                'codigo_municipio': codigo_municipio,
                'data_referencia': data_referencia
            }).fetchone()
            
            if result:
                return float(result[0])
            
            return None
        
        except Exception as e:
            print(f"[AVISO] Erro ao buscar alíquota: {e}")
            return None
        finally:
            db.close()
    
    def aplicar_regras_especiais(
        self,
        valor_base: float,
        aliquota_base: float,
        regime_tributario: str
    ) -> tuple:
        """
        Aplica regras especiais de tributação
        
        Args:
            valor_base: Valor base
            aliquota_base: Alíquota base
            regime_tributario: Regime tributário
        
        Returns:
            (aliquota_final, observacoes)
        """
        
        observacoes = []
        
        # Simples Nacional (placeholder)
        if regime_tributario == 'simples':
            aliquota_final = aliquota_base * 0.7  # 30% de redução (exemplo)
            observacoes.append("Redução Simples Nacional aplicada")
        else:
            aliquota_final = aliquota_base
        
        return (aliquota_final, '; '.join(observacoes) if observacoes else '')
    
    def registrar_calculo(
        self,
        nfe_id: Optional[int],
        tipo_operacao: str,
        codigo_servico: str,
        valor_base: float,
        aliquota_ibs: float,
        valor_ibs: float,
        aliquota_cbs: float,
        valor_cbs: float,
        municipio_origem: str,
        municipio_destino: Optional[str] = None,
        regime_tributario: str = 'normal',
        observacoes: Optional[str] = None
    ) -> bool:
        """
        Registra cálculo no histórico para auditoria
        
        Args:
            nfe_id: ID da NFe (pode ser None)
            tipo_operacao: Tipo de operação ('servico', 'produto', 'misto')
            codigo_servico: Código do serviço
            valor_base: Valor base do cálculo
            aliquota_ibs: Alíquota IBS aplicada
            valor_ibs: Valor IBS calculado
            aliquota_cbs: Alíquota CBS aplicada
            valor_cbs: Valor CBS calculado
            municipio_origem: Município de origem
            municipio_destino: Município de destino (opcional)
            regime_tributario: Regime tributário
            observacoes: Observações sobre o cálculo
        
        Returns:
            True se registrado com sucesso
        """
        
        db = next(get_db())
        try:
            query = text("""
                INSERT INTO historico_calculo_ibs (
                    nfe_id, tipo_operacao, codigo_servico,
                    valor_base, aliquota_ibs, valor_ibs,
                    aliquota_cbs, valor_cbs,
                    municipio_origem, municipio_destino,
                    regime_tributario, observacoes
                ) VALUES (
                    :nfe_id, :tipo_operacao, :codigo_servico,
                    :valor_base, :aliquota_ibs, :valor_ibs,
                    :aliquota_cbs, :valor_cbs,
                    :municipio_origem, :municipio_destino,
                    :regime_tributario, :observacoes
                )
            """)
            
            db.execute(query, {
                'nfe_id': nfe_id,
                'tipo_operacao': tipo_operacao,
                'codigo_servico': codigo_servico,
                'valor_base': valor_base,
                'aliquota_ibs': aliquota_ibs,
                'valor_ibs': valor_ibs,
                'aliquota_cbs': aliquota_cbs,
                'valor_cbs': valor_cbs,
                'municipio_origem': municipio_origem,
                'municipio_destino': municipio_destino,
                'regime_tributario': regime_tributario,
                'observacoes': observacoes
            })
            
            db.commit()
            return True
        
        except Exception as e:
            print(f"[AVISO] Erro ao registrar cálculo: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def validar_codigo_servico(self, codigo: str) -> bool:
        """
        Valida se código de serviço existe na tabela
        
        Args:
            codigo: Código do serviço (ex: '01.01')
        
        Returns:
            True se código válido
        """
        
        db = next(get_db())
        try:
            query = text("""
                SELECT COUNT(*) 
                FROM codigos_servico 
                WHERE codigo = :codigo AND ativo = TRUE
            """)
            
            result = db.execute(query, {'codigo': codigo}).fetchone()
            
            return result[0] > 0 if result else False
        
        except Exception as e:
            print(f"[AVISO] Erro ao validar código: {e}")
            return False
        finally:
            db.close()


# Instância singleton para uso em toda a aplicação
calculo_ibs = CalculoIBS()

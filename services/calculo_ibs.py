"""
Serviço de Cálculo IBS/CBS
---------------------------
Implementa lógica de cálculo de tributos da Reforma Tributária (LC 214/2023)

Este módulo será expandido conforme regulamentações forem publicadas.
Versão inicial contém estrutura básica e placeholders.

Autor: Sistema NFe
Data: 17/11/2025
Referência: Lei Complementar 214/2023 e Cartilha IBS FENACON
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from datetime import date
from sqlalchemy import text
from database.connection import get_db
from utils.reforma_tributaria import vigencia_reforma


class CalculadoraIBS:
    """
    Calculadora de IBS (Imposto sobre Bens e Serviços) e CBS (Contribuição sobre Bens e Serviços)
    
    IBS = Imposto estadual/municipal unificado (substitui ICMS e ISS)
    CBS = Contribuição federal unificada (substitui PIS e COFINS)
    """
    
    # Constantes (placeholders - aguardando definição oficial)
    ALIQUOTA_CBS_FEDERAL_PADRAO = Decimal('12.00')  # Estimativa
    ALIQUOTA_IBS_PADRAO = Decimal('25.00')  # Média estimada
    
    def __init__(self):
        """Inicializa calculadora IBS/CBS"""
        self.cache_aliquotas = {}  # Cache para otimizar consultas
    
    def calcular_ibs_servico(
        self,
        valor_servico: Decimal,
        codigo_municipio: str,
        dhEmi: date,
        tem_credito: bool = False,
        valor_credito: Decimal = Decimal('0.00')
    ) -> Dict:
        """
        Calcula IBS sobre serviço prestado
        
        Args:
            valor_servico: Valor do serviço
            codigo_municipio: Código IBGE do município de prestação
            dhEmi: Data de emissão para vigência e busca da alíquota
            tem_credito: Se há crédito IBS de insumos
            valor_credito: Valor do crédito IBS a compensar
            
        Returns:
            Dict com cálculos: {
                'base_calculo': Decimal,
                'aliquota_ibs': Decimal,
                'valor_ibs_bruto': Decimal,
                'credito_aplicado': Decimal,
                'valor_ibs_liquido': Decimal,
                'municipio': str
            }
        """
        vigencia_reforma(dhEmi)
        
        # 1. Determinar base de cálculo
        base_calculo = self._calcular_base_ibs(valor_servico)
        
        # 2. Buscar alíquota vigente do município
        aliquota = self._buscar_aliquota_ibs(codigo_municipio, dhEmi)
        
        # 3. Calcular IBS bruto
        valor_ibs_bruto = base_calculo * (aliquota / Decimal('100'))
        valor_ibs_bruto = valor_ibs_bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # 4. Aplicar crédito se houver
        credito_aplicado = Decimal('0.00')
        if tem_credito and valor_credito > 0:
            credito_aplicado = min(valor_credito, valor_ibs_bruto)
        
        # 5. Calcular IBS líquido (a recolher)
        valor_ibs_liquido = valor_ibs_bruto - credito_aplicado
        
        return {
            'base_calculo': base_calculo,
            'aliquota_ibs': aliquota,
            'valor_ibs_bruto': valor_ibs_bruto,
            'credito_aplicado': credito_aplicado,
            'valor_ibs_liquido': valor_ibs_liquido,
            'municipio': codigo_municipio
        }
    
    def calcular_cbs_servico(
        self,
        valor_servico: Decimal,
        dhEmi: date,
        tem_credito: bool = False,
        valor_credito: Decimal = Decimal('0.00')
    ) -> Dict:
        """
        Calcula CBS sobre serviço prestado
        
        Args:
            valor_servico: Valor do serviço
            tem_credito: Se há crédito CBS de insumos
            valor_credito: Valor do crédito CBS a compensar
            
        Returns:
            Dict com cálculos: {
                'base_calculo': Decimal,
                'aliquota_cbs': Decimal,
                'valor_cbs_bruto': Decimal,
                'credito_aplicado': Decimal,
                'valor_cbs_liquido': Decimal
            }
        """
        vigencia_reforma(dhEmi)

        # 1. Determinar base de cálculo
        base_calculo = self._calcular_base_cbs(valor_servico)
        
        # 2. Alíquota CBS (federal única)
        aliquota = self.ALIQUOTA_CBS_FEDERAL_PADRAO
        
        # 3. Calcular CBS bruto
        valor_cbs_bruto = base_calculo * (aliquota / Decimal('100'))
        valor_cbs_bruto = valor_cbs_bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # 4. Aplicar crédito se houver
        credito_aplicado = Decimal('0.00')
        if tem_credito and valor_credito > 0:
            credito_aplicado = min(valor_credito, valor_cbs_bruto)
        
        # 5. Calcular CBS líquido (a recolher)
        valor_cbs_liquido = valor_cbs_bruto - credito_aplicado
        
        return {
            'base_calculo': base_calculo,
            'aliquota_cbs': aliquota,
            'valor_cbs_bruto': valor_cbs_bruto,
            'credito_aplicado': credito_aplicado,
            'valor_cbs_liquido': valor_cbs_liquido
        }
    
    def calcular_completo(
        self,
        valor_servico: Decimal,
        codigo_municipio: str,
        dhEmi: date,
        tem_credito_ibs: bool = False,
        valor_credito_ibs: Decimal = Decimal('0.00'),
        tem_credito_cbs: bool = False,
        valor_credito_cbs: Decimal = Decimal('0.00'),
        aplicar_beneficio: Optional[str] = None
    ) -> Dict:
        """
        Calcula IBS + CBS completo sobre serviço
        
        Args:
            valor_servico: Valor do serviço
            codigo_municipio: Código IBGE do município
            data_referencia: Data de referência
            tem_credito_ibs: Se há crédito IBS
            valor_credito_ibs: Valor do crédito IBS
            tem_credito_cbs: Se há crédito CBS
            valor_credito_cbs: Valor do crédito CBS
            aplicar_beneficio: Código do benefício fiscal (se aplicável)
            
        Returns:
            Dict com todos os cálculos de IBS e CBS
        """
        vigencia_reforma(dhEmi)

        # Aplicar benefício fiscal se houver
        valor_ajustado = valor_servico
        beneficio_aplicado = None
        
        if aplicar_beneficio:
            beneficio_info = self._buscar_beneficio_fiscal(aplicar_beneficio, dhEmi)
            if beneficio_info:
                valor_ajustado = self._aplicar_beneficio(valor_servico, beneficio_info)
                beneficio_aplicado = beneficio_info
        
        # Calcular IBS
        resultado_ibs = self.calcular_ibs_servico(
            valor_ajustado,
            codigo_municipio,
            dhEmi,
            tem_credito_ibs,
            valor_credito_ibs
        )
        
        # Calcular CBS
        resultado_cbs = self.calcular_cbs_servico(
            valor_ajustado,
            dhEmi,
            tem_credito_cbs,
            valor_credito_cbs
        )
        
        # Total de tributos
        total_tributos = resultado_ibs['valor_ibs_liquido'] + resultado_cbs['valor_cbs_liquido']
        
        return {
            'valor_servico': valor_servico,
            'valor_ajustado': valor_ajustado,
            'beneficio_aplicado': beneficio_aplicado,
            'ibs': resultado_ibs,
            'cbs': resultado_cbs,
            'total_tributos': total_tributos,
            'carga_tributaria_percentual': (total_tributos / valor_servico * 100) if valor_servico > 0 else Decimal('0.00')
        }
    
    # ===========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ===========================================
    
    def _calcular_base_ibs(self, valor_servico: Decimal) -> Decimal:
        """
        Calcula base de cálculo do IBS
        
        Base = Valor do Serviço - Deduções Permitidas
        
        TODO: Implementar deduções quando regulamentação definir:
        - Descontos incondicionais
        - Materiais fornecidos pelo Tomadores
        - Subempreitadas (depende do caso)
        """
        # Por enquanto, base = valor do serviço (sem deduções)
        return valor_servico
    
    def _calcular_base_cbs(self, valor_servico: Decimal) -> Decimal:
        """
        Calcula base de cálculo do CBS
        
        Base = Valor do Serviço - Deduções Permitidas
        """
        # Por enquanto, base = valor do serviço (sem deduções)
        return valor_servico
    
    def _buscar_aliquota_ibs(
        self,
        codigo_municipio: str,
        data_referencia: date
    ) -> Decimal:
        """
        Busca alíquota IBS vigente para município
        
        Returns:
            Alíquota em percentual (ex: 25.00)
        """
        # Verificar cache
        cache_key = f"{codigo_municipio}_{data_referencia}"
        if cache_key in self.cache_aliquotas:
            return self.cache_aliquotas[cache_key]
        
        try:
            # Buscar no banco usando função SQL
            db = next(get_db())
            query = text("""
                SELECT aliquota_ibs FROM aliquotas_ibs_municipio
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
            db.close()
            
            if result and result[0]:  # result[0] = aliquota_ibs
                aliquota = Decimal(str(result[0]))
                self.cache_aliquotas[cache_key] = aliquota
                return aliquota
            
        except Exception as e:
            print(f"[!] Erro ao buscar alíquota IBS: {e}")
        
        # Fallback: alíquota padrão
        print(f"[!] Usando alíquota IBS padrão para {codigo_municipio}")
        return self.ALIQUOTA_IBS_PADRAO
    
    def _buscar_beneficio_fiscal(
        self,
        codigo_beneficio: str,
        data_referencia: date
    ) -> Optional[Dict]:
        """
        Busca benefício fiscal no banco
        
        Returns:
            Dict com informações do benefício ou None
        """
        try:
            db = next(get_db())
            query = text("""
                SELECT 
                    codigo,
                    descricao,
                    tipo,
                    percentual_reducao,
                    requisitos
                FROM beneficios_fiscais_ibs
                WHERE codigo = :codigo
                  AND ativo = TRUE
                  AND vigencia_inicio <= :data_ref
                  AND (vigencia_fim IS NULL OR vigencia_fim >= :data_ref)
                LIMIT 1
            """)
            
            result = db.execute(query, {
                'codigo': codigo_beneficio,
                'data_ref': data_referencia
            }).fetchone()
            db.close()
            
            if result:
                return {
                    'codigo': result[0],
                    'descricao': result[1],
                    'tipo': result[2],
                    'percentual_reducao': Decimal(str(result[3])) if result[3] else None,
                    'requisitos': result[4]
                }
        
        except Exception as e:
            print(f"[!] Erro ao buscar benefício fiscal: {e}")
        
        return None
    
    def _aplicar_beneficio(
        self,
        valor_original: Decimal,
        beneficio: Dict
    ) -> Decimal:
        """
        Aplica benefício fiscal ao valor
        
        Returns:
            Valor ajustado após aplicação do benefício
        """
        tipo = beneficio['tipo']
        
        if tipo == 'ISENCAO':
            # Isenção total
            return Decimal('0.00')
        
        elif tipo == 'REDUCAO':
            # Redução percentual
            percentual = beneficio['percentual_reducao'] or Decimal('0.00')
            fator_reducao = Decimal('1.00') - (percentual / Decimal('100'))
            return valor_original * fator_reducao
        
        elif tipo == 'DIFERIMENTO':
            # Diferimento (postergação) - não altera valor, apenas muda momento do recolhimento
            # TODO: Implementar lógica de diferimento quando regulamentação definir
            return valor_original
        
        elif tipo == 'SUSPENSAO':
            # Suspensão temporária
            return Decimal('0.00')
        
        else:
            # Tipo desconhecido
            return valor_original
    
    def limpar_cache(self):
        """Limpa cache de alíquotas (útil após atualizações no banco)"""
        self.cache_aliquotas.clear()


class ConversorTributacaoHistorica:
    """
    Converte tributação antiga (ICMS/IPI/PIS/COFINS) para IBS/CBS
    Útil para relatórios comparativos e análises históricas
    """
    
    @staticmethod
    def converter_nfe_para_ibs(nfe_id: int) -> Dict:
        """
        Converte valores de uma NFe antiga para estimativa IBS/CBS
        
        Args:
            nfe_id: ID da NFe a converter
            
        Returns:
            Dict com valores convertidos
        """
        try:
            # Buscar totais da NFe
            query = text("""
                SELECT 
                    n.id,
                    n.numero,
                    COALESCE(SUM(i.valor_icms), 0) AS total_icms,
                    COALESCE(SUM(i.valor_ipi), 0) AS total_ipi,
                    COALESCE(SUM(i.valor_pis), 0) AS total_pis,
                    COALESCE(SUM(i.valor_cofins), 0) AS total_cofins
                FROM nfes n
                LEFT JOIN nfe_itens i ON n.id = i.nfe_id
                WHERE n.id = :nfe_id
                GROUP BY n.id, n.numero
            """)
            
            db = next(get_db())
            result = db.execute(query, {'nfe_id': nfe_id}).fetchone()
            db.close()
            
            if not result:
                return {'erro': 'NFe não encontrada'}
            
            # Conversão aproximada (método simplificado)
            # IBS ≈ ICMS + IPI (impostos sobre consumo)
            # CBS ≈ PIS + COFINS (contribuições federais)
            
            icms = Decimal(str(result[2]))
            ipi = Decimal(str(result[3]))
            pis = Decimal(str(result[4]))
            cofins = Decimal(str(result[5]))
            
            valor_ibs_estimado = icms + ipi
            valor_cbs_estimado = pis + cofins
            
            return {
                'nfe_id': result[0],
                'numero': result[1],
                'tributacao_antiga': {
                    'icms': icms,
                    'ipi': ipi,
                    'pis': pis,
                    'cofins': cofins,
                    'total': icms + ipi + pis + cofins
                },
                'tributacao_ibs_estimada': {
                    'ibs': valor_ibs_estimado,
                    'cbs': valor_cbs_estimado,
                    'total': valor_ibs_estimado + valor_cbs_estimado
                },
                'diferenca': (valor_ibs_estimado + valor_cbs_estimado) - (icms + ipi + pis + cofins),
                'metodo': 'SOMA_SIMPLES',
                'observacao': 'Conversão aproximada para fins analíticos'
            }
        
        except Exception as e:
            return {'erro': f'Erro ao converter: {str(e)}'}


# ===========================================
# FUNÇÕES AUXILIARES PÚBLICAS
# ===========================================

def calcular_ibs_simples(
    valor: Decimal,
    codigo_municipio: str,
    dhEmi: date
) -> Decimal:
    """
    Função simplificada para cálculo rápido de IBS
    
    Args:
        valor: Valor do serviço
        codigo_municipio: Código IBGE do município
        
    Returns:
        Valor do IBS calculado
    """
    calc = CalculadoraIBS()
    resultado = calc.calcular_ibs_servico(valor, codigo_municipio, dhEmi)
    return resultado['valor_ibs_liquido']


def calcular_cbs_simples(valor: Decimal, dhEmi: date) -> Decimal:
    """
    Função simplificada para cálculo rápido de CBS
    
    Args:
        valor: Valor do serviço
        
    Returns:
        Valor do CBS calculado
    """
    calc = CalculadoraIBS()
    resultado = calc.calcular_cbs_servico(valor, dhEmi)
    return resultado['valor_cbs_liquido']


def validar_aliquota_ibs(aliquota: Decimal) -> bool:
    """
    Valida se alíquota IBS está dentro dos limites legais
    
    LC 214/2023: Alíquota máxima ainda a ser definida
    """
    # TODO: Atualizar limites quando regulamentação definir
    ALIQUOTA_MINIMA = Decimal('0.00')
    ALIQUOTA_MAXIMA = Decimal('35.00')  # Estimativa
    
    return ALIQUOTA_MINIMA <= aliquota <= ALIQUOTA_MAXIMA


# ===========================================
# EXEMPLO DE USO
# ===========================================

if __name__ == '__main__':
    """
    Exemplos de uso da calculadora IBS/CBS
    """
    
    # Exemplo 1: Cálculo básico IBS
    calc = CalculadoraIBS()
    
    resultado_ibs = calc.calcular_ibs_servico(
        valor_servico=Decimal('1000.00'),
        codigo_municipio='3550308',  # São Paulo/SP
        dhEmi=date.today(),
    )
    
    print("=== Exemplo 1: Cálculo IBS ===")
    print(f"Base de Cálculo: R$ {resultado_ibs['base_calculo']}")
    print(f"Alíquota IBS: {resultado_ibs['aliquota_ibs']}%")
    print(f"Valor IBS: R$ {resultado_ibs['valor_ibs_liquido']}")
    print()
    
    # Exemplo 2: Cálculo completo IBS + CBS
    resultado_completo = calc.calcular_completo(
        valor_servico=Decimal('1000.00'),
        codigo_municipio='3550308',
        dhEmi=date.today(),
        tem_credito_ibs=True,
        valor_credito_ibs=Decimal('50.00')
    )
    
    print("=== Exemplo 2: Cálculo Completo IBS + CBS ===")
    print(f"Valor do Serviço: R$ {resultado_completo['valor_servico']}")
    print(f"IBS Líquido: R$ {resultado_completo['ibs']['valor_ibs_liquido']}")
    print(f"CBS Líquido: R$ {resultado_completo['cbs']['valor_cbs_liquido']}")
    print(f"Total Tributos: R$ {resultado_completo['total_tributos']}")
    print(f"Carga Tributária: {resultado_completo['carga_tributaria_percentual']:.2f}%")
    print()
    
    # Exemplo 3: Conversão histórica
    conversor = ConversorTributacaoHistorica()
    # resultado_conversao = conversor.converter_nfe_para_ibs(nfe_id=1)
    # print("=== Exemplo 3: Conversão Histórica ===")
    # print(resultado_conversao)

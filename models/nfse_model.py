"""
Model para NFS-e Nacional - Nota Fiscal de Serviço Eletrônica
Padrão Nacional conforme documentação gov.br/nfse
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class PrestadorNFSe:
    """Dados do prestador de serviço (emitente)"""
    cnpj: str
    inscricao_municipal: str
    razao_social: str
    nome_fantasia: Optional[str] = None
    endereco_logradouro: str = ""
    endereco_numero: str = ""
    endereco_complemento: str = ""
    endereco_bairro: str = ""
    endereco_codigo_municipio: str = ""  # Código IBGE
    endereco_uf: str = ""
    endereco_cep: str = ""
    telefone: str = ""
    email: str = ""
    # Regime tributário
    regime_especial_tributacao: Optional[str] = None  # 1-ME, 2-EPP, 3-Cooperativa, etc.
    optante_simples_nacional: bool = True
    incentivo_fiscal: bool = False


@dataclass
class TomadoresNFSe:
    """Dados do Tomadores do serviço (destinatário)"""
    tipo_documento: str  # 'CPF' ou 'CNPJ'
    cpf_cnpj: str
    razao_social: str
    inscricao_municipal: Optional[str] = None
    endereco_logradouro: str = ""
    endereco_numero: str = ""
    endereco_complemento: str = ""
    endereco_bairro: str = ""
    endereco_codigo_municipio: str = ""  # Código IBGE
    endereco_uf: str = ""
    endereco_cep: str = ""
    telefone: str = ""
    email: str = ""


@dataclass
class ServicoNFSe:
    """Dados do serviço prestado"""
    # Código do serviço conforme LC 116/2003
    codigo_tributacao_nacional: str  # Código LC 116 (ex: "01.01", "07.02")
    codigo_cnae: Optional[str] = None
    codigo_nbs: str = "101010000"  # Código NBS obrigatório GISS (máximo 9 dígitos sem pontos)
    discriminacao: str = ""  # Descrição detalhada do serviço
    
    # Valores
    valor_servicos: float = 0.0
    valor_deducoes: float = 0.0
    valor_pis: float = 0.0
    valor_cofins: float = 0.0
    valor_inss: float = 0.0
    valor_ir: float = 0.0
    valor_csll: float = 0.0
    valor_pis_operacao: float = 0.0
    valor_cofins_operacao: float = 0.0
    valor_iss: float = 0.0
    valor_iss_retido: float = 0.0
    outras_retencoes: float = 0.0
    desconto_incondicionado: float = 0.0
    desconto_condicionado: float = 0.0
    
    # Alíquotas
    aliquota_iss: float = 0.0
    aliquota_pis: float = 0.0
    aliquota_cofins: float = 0.0
    base_calculo: float = 0.0
    base_calculo_pis_cofins: float = 0.0
    valor_liquido: float = 0.0
    
    # ISS
    iss_retido: bool = False  # 1-Sim, 2-Não
    csll_retida: bool = False
    cst_pis_cofins: str = "00"
    tipo_retencao_pis_cofins: str = "2"  # 1-Retido, 2-Não Retido
    
    # Local da prestação
    codigo_municipio_prestacao: str = ""  # Código IBGE
    codigo_pais: str = "1058"  # Brasil
    
    # Tributos Totais (Reforma Tributária - obrigatório GISS)
    percentual_total_tributos_federais: float = 0.0  # pTotTribFed
    percentual_total_tributos_estaduais: float = 0.0  # pTotTribEst
    percentual_total_tributos_municipais: float = 0.0  # pTotTribMun
    
    # IBS/CBS - Reforma Tributária (obrigatório GISS)
    finalidade_nfse: str = "0"  # 0-Normal, 1-Complementar, 2-Ajuste, 3-Substituição
    indicador_consumidor_final: str = "0"  # 0-Não, 1-Sim
    codigo_indicador_operacao: str = "000001"  # Código da operação (6 dígitos)
    indicador_destinatario: str = "0"  # 0-Interno, 1-Interestadual, 2-Exterior
    cst_ibs_cbs: str = "001"  # Código Situação Tributária IBS/CBS (3 dígitos)
    codigo_classificacao_tributaria: str = "000001"  # cClassTrib - 6 dígitos
    codigo_localidade_incidencia: str = "3549805"  # Código município SJRP
    percentual_redutor: float = 0.0  # Percentual de redução da base


@dataclass
class NFSeNacional:
    """
    NFS-e Nacional - Modelo de dados completo
    Baseado no padrão nacional da Receita Federal
    """
    
    # Identificação
    id: Optional[int] = None
    cliente_id: int = 0
    numero_nfse: Optional[str] = None
    codigo_verificacao: Optional[str] = None
    
    # Série e número RPS
    numero_rps: Optional[int] = None
    serie_rps: str = "1"
    tipo_rps: str = "1"  # 1-RPS, 2-NF Conjugada, 3-Cupom
    
    # Datas
    data_emissao: datetime = field(default_factory=datetime.now)
    data_competencia: Optional[datetime] = None
    
    # Natureza da operação
    # 1-Tributação no município
    # 2-Tributação fora do município
    # 3-Isenção
    # 4-Imune
    # 5-Exigibilidade suspensa por decisão judicial
    # 6-Exigibilidade suspensa por procedimento administrativo
    natureza_operacao: str = "1"
    
    # Regime especial de tributação
    # 1-Microempresa Municipal
    # 2-Estimativa
    # 3-Sociedade de Profissionais
    # 4-Cooperativa
    # 5-MEI
    # 6-ME/EPP Simples Nacional
    regime_especial_tributacao: Optional[str] = None
    
    # Simples Nacional
    optante_simples_nacional: bool = True
    incentivador_cultural: bool = False
    
    # Status
    # 1-Normal, 2-Cancelada, 3-Substituída
    status: str = "1"
    
    # Ambiente
    ambiente: str = "homologacao"  # homologacao ou producao
    
    # Participantes
    prestador: Optional[PrestadorNFSe] = None
    Tomadores: Optional[TomadoresNFSe] = None
    
    # Serviço
    servico: Optional[ServicoNFSe] = None
    
    # Construção Civil (opcional)
    codigo_obra: Optional[str] = None
    art: Optional[str] = None
    
    # Informações adicionais
    informacoes_complementares: str = ""
    
    # XML
    xml_rps: Optional[str] = None  # XML do RPS enviado
    xml_nfse: Optional[str] = None  # XML da NFS-e retornada
    
    # Protocolo
    protocolo: Optional[str] = None
    lote: Optional[str] = None
    
    # Erros
    codigo_erro: Optional[str] = None
    mensagem_erro: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def calcular_valores(self):
        """Calcula valores derivados do serviço"""
        if self.servico:
            # Base de cálculo
            self.servico.base_calculo = (
                self.servico.valor_servicos 
                - self.servico.valor_deducoes 
                - self.servico.desconto_incondicionado
            )
            
            # ISS
            if self.servico.aliquota_iss > 0:
                self.servico.valor_iss = round(
                    self.servico.base_calculo * (self.servico.aliquota_iss / 100), 2
                )
            
            # Valor líquido
            total_retencoes = (
                self.servico.valor_pis +
                self.servico.valor_cofins +
                self.servico.valor_inss +
                self.servico.valor_ir +
                self.servico.outras_retencoes
            )

            if self.servico.csll_retida:
                total_retencoes += self.servico.valor_csll
            
            if self.servico.iss_retido:
                total_retencoes += self.servico.valor_iss
                self.servico.valor_iss_retido = self.servico.valor_iss
            
            self.servico.valor_liquido = round(
                self.servico.valor_servicos 
                - self.servico.desconto_incondicionado 
                - total_retencoes, 2
            )


# Códigos de serviço LC 116/2003 - Lista resumida
CODIGOS_SERVICO_LC116 = {
    "1.01": "Análise e desenvolvimento de sistemas",
    "1.02": "Programação",
    "1.03": "Processamento de dados e congêneres",
    "1.04": "Elaboração de programas de computadores",
    "1.05": "Licenciamento ou cessão de direito de uso de programas",
    "1.06": "Assessoria e consultoria em informática",
    "1.07": "Suporte técnico em informática",
    "1.08": "Planejamento, confecção, manutenção e atualização de páginas",
    "1.09": "Disponibilização de conteúdos de áudio, vídeo, etc.",
    "7.01": "Engenharia, agronomia, agrimensura, arquitetura, etc.",
    "7.02": "Execução de obras de construção civil",
    "7.03": "Elaboração de planos diretores, estudos de viabilidade",
    "7.04": "Demolição",
    "7.05": "Reparação, conservação e reforma de edifícios",
    "17.01": "Assessoria ou consultoria de qualquer natureza",
    "17.02": "Datilografia, digitação, estenografia, expediente",
    "17.03": "Planejamento, coordenação, programação ou organização técnica",
    "17.04": "Recrutamento, agenciamento, seleção e colocação de mão-de-obra",
    "17.05": "Fornecimento de mão-de-obra",
    # Adicionar mais conforme necessário
}


# Códigos de municípios IBGE - São Paulo
CODIGOS_MUNICIPIO_SP = {
    "3549805": "São José do Rio Preto",
    "3550308": "São Paulo",
    "3509502": "Campinas",
    "3547809": "Santos",
    "3518800": "Guarulhos",
    # Adicionar mais conforme necessário
}


# URLs dos webservices NFS-e Nacional
URLS_NFSE_NACIONAL = {
    "homologacao": {
        "base_url": "https://www.nfse.gov.br/Homolog",
        "recepcao_rps": "/RecepcionarLoteRps",
        "consulta_situacao_lote": "/ConsultarSituacaoLoteRps",
        "consulta_nfse_rps": "/ConsultarNfsePorRps",
        "consulta_lote_rps": "/ConsultarLoteRps",
        "consulta_nfse": "/ConsultarNfse",
        "cancelamento": "/CancelarNfse",
    },
    "producao": {
        "base_url": "https://www.nfse.gov.br",
        "recepcao_rps": "/RecepcionarLoteRps",
        "consulta_situacao_lote": "/ConsultarSituacaoLoteRps",
        "consulta_nfse_rps": "/ConsultarNfsePorRps",
        "consulta_lote_rps": "/ConsultarLoteRps",
        "consulta_nfse": "/ConsultarNfse",
        "cancelamento": "/CancelarNfse",
    }
}


# Alíquotas ISS por município (São José do Rio Preto)
ALIQUOTAS_ISS_SJRP = {
    "1.01": 2.0,  # Sistemas
    "1.02": 2.0,  # Programação
    "1.03": 2.0,  # Processamento de dados
    "1.04": 2.0,  # Programas
    "1.05": 2.0,  # Licenciamento
    "1.06": 2.0,  # Consultoria
    "1.07": 2.0,  # Suporte técnico
    "7.02": 2.0,  # Construção civil
    "17.01": 5.0, # Consultoria geral
    "default": 5.0,  # Alíquota padrão
}

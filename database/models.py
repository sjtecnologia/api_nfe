# database/models.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, Date, ForeignKey, Numeric, LargeBinary, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
# Importa JSONB se for usar PostgreSQL. Se não for usar PgSQL, remova ou comente esta linha.
from sqlalchemy.dialects.postgresql import JSONB

from datetime import datetime, date
import os # Para usar variáveis de ambiente, se necessário na string de conexão

# Define a base para os modelos declarativos
Base = declarative_base()

# --- Tabela de Apoio ---
class RegimeTributario(Base):
    """
    Modelo para os regimes tributários (ex: Simples Nacional, Lucro Presumido, Lucro Real).
    """
    __tablename__ = 'regimes_tributarios'

    regime_tributario_id = Column(Integer, primary_key=True)
    nome = Column(String(100), unique=True, nullable=False)
    descricao = Column(Text, nullable=True)

    # Relacionamentos (bidirecionais)
    clientes = relationship("Cliente", back_populates="regime_tributario")
    regras_tributacao = relationship("RegraTributacao", back_populates="regime_tributario")

    def __repr__(self):
        return f"<RegimeTributario(id={self.regime_tributario_id}, nome='{self.nome}')>"

# --- Tabelas Principais ---

class Cliente(Base):
    """
    Modelo para os clientes (emissores de NF-e) da sua plataforma.
    """
    __tablename__ = 'clientes'

    cliete_id = Column(Integer, primary_key=True)
    cnpj = Column(String(14), unique=True, nullable=False)
    razao_social = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255), nullable=True)
    inscricao_estadual = Column(String(14), nullable=True)
    inscricao_municipal = Column(String(14), nullable=True)

    regime_tributario_id = Column(Integer, ForeignKey('regimes_tributarios.regime_tributario_id'), nullable=False)
    regime_tributario = relationship("RegimeTributario", back_populates="clientes")

    cnae = Column(String(7), nullable=True) # CNAE principal

    # Endereço
    logradouro = Column(String(255), nullable=False)
    numero = Column(String(10), nullable=False)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=False)
    codigo_municipio = Column(String(7), nullable=False) # Código IBGE
    nome_municipio = Column(String(100), nullable=False)
    uf = Column(String(2), nullable=False)
    cep = Column(String(8), nullable=False)

    # Contato
    email_contato = Column(String(255), nullable=True)
    telefone_contato = Column(String(20), nullable=True)

    ativo = Column(Boolean, default=True, nullable=False)
    data_cadastro = Column(DateTime, default=datetime.now, nullable=False)
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Relacionamentos (bidirecionais)
    certificados = relationship("CertificadoDigital", back_populates="cliente")
    nfe_emitidas = relationship("NFeEmitidas", back_populates="cliente")
    produtos = relationship("Produto", back_populates="cliente")
    regras_tributacao_cliente = relationship("RegraTributacao", back_populates="cliente_responsavel")

    def __repr__(self):
        return f"<Cliente(id={self.cliente_id}, razao_social='{self.razao_social}', cnpj='{self.cnpj}')>"


class CertificadoDigital(Base):
    """
    Modelo para armazenar certificados digitais.
    ATENÇÃO: conteudo_certificado e senha_certificado DEVEM ser criptografados ANTES de serem salvos.
    LargeBinary é usado para armazenar bytes criptografados.
    """
    __tablename__ = 'certificados_digitais'

    certificado_digital_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    fingerprint = Column(String(64), unique=True, nullable=True) # SHA1 ou SHA256 do certificado, para identificação
    
    # Conteúdo do certificado e senha devem ser criptografados antes de salvar!
    conteudo_certificado = Column(LargeBinary, nullable=False) # Armazena bytes criptografados
    senha_certificado = Column(LargeBinary, nullable=False) # Armazena bytes criptografados

    validade_inicio = Column(DateTime, nullable=False)
    validade_fim = Column(DateTime, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    data_upload = Column(DateTime, default=datetime.now, nullable=False)
    nome_arquivo_original = Column(String(255), nullable=True)

    # Relacionamento (bidirecional)
    cliente = relationship("Cliente", back_populates="certificados")

    def __repr__(self):
        return f"<CertificadoDigital(id={self.certificado_digital_id}, cliente_id={self.cliente_id}, ativo={self.ativo}, validade_fim='{self.validade_fim}')>"


class NFeEmitidas(Base):
    """
    Modelo para templates de NF-e recorrentes. O JSON da NFE é salvo para clonagem.
    """
    __tablename__ = 'nfe_emitidas'

    nfe_emitida_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    nome_modelo = Column(String(255), nullable=False)
    tipo_nfe = Column(String(10), nullable=False) # Ex: "NFe", "NFCe"
    finalidade_emissao = Column(Integer, nullable=False)
    natureza_operacao = Column(String(255), nullable=False)
    informacoes_adicionais = Column(Text, nullable=True)

    # Armazena a estrutura JSON/XML da NFE (ou partes dela) que será clonada.
    # Baseado no bind do engine, usará JSONB para PostgreSQL, ou Text para outros (SQLite, MySQL)
    json_modelo_nfe = Column(JSONB if os.getenv('DB_TYPE') == 'postgresql' else Text, nullable=False)
    
    data_criacao = Column(DateTime, default=datetime.now, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    # Relacionamento (bidirecional)
    cliente = relationship("Cliente", back_populates="modelos_nfe")

    def __repr__(self):
        return f"<NFeModelo(id={self.nfe_emitida_id}, nome='{self.nome_modelo}', cliente_id={self.cliente_id})>"


class Cfop(Base):
    """
    Catálogo dos Códigos Fiscais de Operações e Prestações (CFOP).
    """
    __tablename__ = 'cfops'

    cfop_id = Column(Integer, primary_key=True)
    codigo = Column(String(5), unique=True, nullable=False) # Ex: "1.101"
    descricao = Column(Text, nullable=False)
    tipo = Column(String(10), nullable=True) # Ex: "ENTRADA", "SAIDA"
    data_vigencia_inicio = Column(Date, nullable=True)
    data_vigencia_fim = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)

    # Relacionamento (bidirecional)
    regras_tributacao = relationship("RegraTributacao", back_populates="cfop")

    def __repr__(self):
        return f"<Cfop(id={self.cfop_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"


class Ncm(Base):
    """
    Catálogo da Nomenclatura Comum do Mercosul (NCM).
    """
    __tablename__ = 'ncms'

    ncm_id = Column(Integer, primary_key=True)
    codigo = Column(String(8), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)
    data_vigencia_inicio = Column(Date, nullable=True)
    data_vigencia_fim = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)

    # Relacionamentos (bidirecionais)
    produtos = relationship("Produto", back_populates="ncm")
    regras_tributacao = relationship("RegraTributacao", back_populates="ncm")

    def __repr__(self):
        return f"<Ncm(id={self.ncm_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"


class Produto(Base):
    """
    Armazena os produtos e serviços que o cliente pode emitir na NF-e.
    """
    __tablename__ = 'produtos'

    produto_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=True) # Nullable: produtos globais ou de um cliente específico
    codigo_interno = Column(String(50), nullable=False) # SKU ou código próprio do cliente
    descricao = Column(Text, nullable=False)

    ncm_id = Column(Integer, ForeignKey('ncms.ncm_id'), nullable=False)
    ncm = relationship("Ncm", back_populates="produtos")

    cest = Column(String(7), nullable=True) # Código CEST
    unidade_comercial = Column(String(6), nullable=False)
    preco_unitario_padrao = Column(Numeric(15, 2), nullable=False)
    origem_mercadoria = Column(Integer, nullable=False) # 0-Nacional, 1-Estrangeira, etc.
    tipo_item = Column(String(10), nullable=False) # "PRODUTO" ou "SERVICO"
    ativo = Column(Boolean, default=True, nullable=False)

    # Relacionamento (bidirecional)
    cliente = relationship("Cliente", back_populates="produtos")

    # Garante que codigo_interno é único por cliente (ou global se cliente_id for NULL)
    # Exemplo de UniqueConstraint para campos múltiplos
    # Opcional: Se 'codigo_interno' é único globalmente, remova cliente_id da UniqueConstraint e torne 'codigo_interno' unique=True acima.
    __table_args__ = (
        UniqueConstraint('cliente_id', 'codigo_interno', name='_cliente_codigo_interno_uc'),
    )

    def __repr__(self):
        return f"<Produto(id={self.produto_id}, codigo='{self.codigo_interno}', descricao='{self.descricao[:30]}...')>"


class RegraTributacao(Base):
    """
    Parametrização das regras de tributação.
    """
    __tablename__ = 'regras_tributacao'

    regra_tributacao_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=True) # Nullable: regra global
    regime_tributario_id = Column(Integer, ForeignKey('regimes_tributarios.regime_tributario_id'), nullable=False)
    cfop_id = Column(Integer, ForeignKey('cfops.cfop_id'), nullable=False)
    ncm_id = Column(Integer, ForeignKey('ncms.ncm_id'), nullable=True) # Nullable: qualquer NCM

    uf_origem = Column(String(2), nullable=True)
    uf_destino = Column(String(2), nullable=True)
    tipo_item = Column(String(10), nullable=True) # "PRODUTO" ou "SERVICO"

    prioridade = Column(Integer, default=100, nullable=False) # Menor número = maior prioridade

    # ICMS
    cst_icms = Column(String(2), nullable=True)
    csosn_icms = Column(String(3), nullable=True)
    aliquota_icms = Column(Numeric(5, 2), nullable=True)
    reducao_base_icms = Column(Numeric(5, 2), nullable=True)
    modalidade_bc_icms = Column(Integer, nullable=True)
    motivo_desoneracao_icms = Column(Integer, nullable=True)

    # PIS
    cst_pis = Column(String(2), nullable=True)
    aliquota_pis = Column(Numeric(5, 4), nullable=True)

    # COFINS
    cst_cofins = Column(String(2), nullable=True)
    aliquota_cofins = Column(Numeric(5, 4), nullable=True)

    # IPI
    cst_ipi = Column(String(2), nullable=True)
    aliquota_ipi = Column(Numeric(5, 2), nullable=True)

    descricao_regra = Column(Text, nullable=True)
    data_criacao = Column(DateTime, default=datetime.now, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    # Relacionamentos (bidirecionais)
    cliente_responsavel = relationship("Cliente", back_populates="regras_tributacao_cliente")
    regime_tributario = relationship("RegimeTributario", back_populates="regras_tributacao")
    cfop = relationship("Cfop", back_populates="regras_tributacao")
    ncm = relationship("Ncm", back_populates="regras_tributacao")

    def __repr__(self):
        return f"<RegraTributacao(id={self.regime_tributario_id}, cliente_id={self.cliente_id}, cfop_id={self.cfop_id}, ncm_id={self.ncm_id}, prioridade={self.prioridade})>"



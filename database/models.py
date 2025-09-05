from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, Date, ForeignKey, Numeric, LargeBinary, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship # Adicionado relationship
from sqlalchemy.dialects.postgresql import JSONB # Mantenha esta linha se usar PostgreSQL

from datetime import datetime, date
import os
import base64 # Importe para lidar com LargeBinary
from decimal import Decimal # Importe para lidar com Numeric

Base = declarative_base()

# Helper para converter objetos SQLAlchemy em dicionários
def serialize_sqla_object(obj):
    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            data[column.name] = value.isoformat()
        elif isinstance(value, date):
            data[column.name] = value.isoformat()
        elif isinstance(value, Decimal):
            data[column.name] = float(value) # Ou str(value) se precisar de precisão total
        elif isinstance(value, bytes): # Para LargeBinary
            try:
                data[column.name] = base64.b64encode(value).decode('utf-8')
            except TypeError: # Se value for None ou algo não passível de b64encode
                data[column.name] = None
        else:
            data[column.name] = value
    return data

# --- Tabelas de Apoio / Configuração ---

class RegimeTributario(Base):
    __tablename__ = 'regimes_tributarios'
    regime_tributario_id = Column(Integer, primary_key=True)
    nome = Column(String(255), unique=True, nullable=False)
    descricao = Column(String(255), nullable=True) # script db mostra varchar(255)
    
    # Relacionamento de volta para Cliente
    clientes = relationship('Cliente', back_populates='regime_tributario')

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<RegimeTributario(id={self.regime_tributario_id}, nome='{self.nome}')>"

class Csosnicms(Base):
    __tablename__ = 'csosn_icms'
    csosn_id = Column(Integer, primary_key=True)
    codigo = Column(String(3), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<Csosnicms(id={self.csosn_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"
    
class Csticms(Base):
    __tablename__ = 'cst_icms'
    cst_id = Column(Integer, primary_key=True)
    codigo = Column(String(2), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<Csticms(id={self.cst_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"

class OrigemMercadoria(Base):
    __tablename__ = 'origens_mercadoria'
    origem_id = Column(Integer, primary_key=True)
    codigo = Column(String(1), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<OrigemMercadoria(id={self.origem_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"

# --- Tabelas Principais de Negócio ---

class Cliente(Base):
    __tablename__ = 'clientes'
    cliente_id = Column(Integer, primary_key=True)
    cnpj = Column(String(18), unique=True, nullable=False) # Ajustado para 18 caracteres conforme o script
    razao_social = Column(String(255), nullable=True) # Removido NOT NULL conforme script
    nome_fantasia = Column(String(255), nullable=True)
    inscricao_estadual = Column(String(14), nullable=True)
    inscricao_municipal = Column(String(14), nullable=True)
    regime_tributario_id = Column(Integer, ForeignKey('regimes_tributarios.regime_tributario_id'), nullable=False)
    cnae = Column(String(7), nullable=True)
    logradouro = Column(String(255), nullable=True) # Removido NOT NULL conforme script
    numero = Column(String(10), nullable=True) # Removido NOT NULL conforme script
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True) # Removido NOT NULL conforme script
    codigo_municipio = Column(String(7), nullable=True) # Removido NOT NULL conforme script
    nome_municipio = Column(String(100), nullable=True) # Removido NOT NULL conforme script
    uf = Column(String(2), nullable=True) # Removido NOT NULL conforme script
    cep = Column(String(9), nullable=True) # Removido NOT NULL conforme script
    email_contato = Column(String(255), nullable=True)
    telefone_contato = Column(String(20), nullable=True)
    ativo = Column(Boolean, default=True, nullable=True) # Removido NOT NULL conforme script
    data_cadastro = Column(DateTime, default=datetime.now, nullable=True) # Removido NOT NULL conforme script
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=True) # Removido NOT NULL conforme script

    # Relacionamentos
    regime_tributario = relationship('RegimeTributario', back_populates='clientes')
    certificados = relationship('CertificadoDigital', back_populates='cliente', cascade='all, delete-orphan')
    nfes_emitidas = relationship('NFeEmitidas', back_populates='cliente', cascade='all, delete-orphan')
    produtos = relationship('Produto', back_populates='cliente', cascade='all, delete-orphan')
    regras_tributacao = relationship('RegraTributacao', back_populates='cliente', cascade='all, delete-orphan')

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<Cliente(id={self.cliente_id}, razao_social='{self.razao_social}', cnpj='{self.cnpj}')>"

class CertificadoDigital(Base):
    __tablename__ = 'certificados_digitais'
    certificado_digital_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    fingerprint = Column(String(64), unique=True, nullable=True) # No script é unique, mas include(cliente_id, fingerprint)
    conteudo_certificado = Column(LargeBinary, nullable=True) # No script é bytea, mas sem not null
    senha_certificado = Column(LargeBinary, nullable=True) # No script é bytea, mas sem not null
    validade_inicio = Column(DateTime, nullable=True) # No script é sem not null
    validade_fim = Column(DateTime, nullable=True) # No script é sem not null
    ativo = Column(Boolean, nullable=True) # No script é boolean, mas sem default
    data_upload = Column(DateTime, nullable=True) # No script é sem not null
    nome_arquivo_original = Column(String(255), nullable=True)

    __table_args__ = (
        # A unique constraint no script é (fingerprint) INCLUDE (cliente_id, fingerprint),
        # mas SQLAlchemy UniqueConstraint não suporta INCLUDE.
        # Se precisar de unicidade composta por fingerprint e cliente_id, seria:
        # UniqueConstraint('fingerprint', 'cliente_id', name='fingerprint_cliente_uc'),
        # Mantenho apenas 'fingerprint' unique como no script para compatibilidade direta.
    )

    # Relacionamento
    cliente = relationship('Cliente', back_populates='certificados')

    def to_dict(self):
        return serialize_sqla_object(self)
        
    def __repr__(self):
        return f"<CertificadoDigital(id={self.certificado_digital_id}, cliente_id={self.cliente_id}, ativo={self.ativo}, validade_fim='{self.validade_fim}')>"

class NFeEmitidas(Base):
    __tablename__ = 'nfe_emitidas'
    nfe_emitida_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    tipo_nfe = Column(String(10), nullable=True) # Removido NOT NULL conforme script
    finalidade_emissao = Column(Integer, nullable=True) # Removido NOT NULL conforme script
    natureza_operacao = Column(String(255), nullable=True) # Removido NOT NULL conforme script
    informacoes_adicionais = Column(Text, nullable=True)
    destinatario_razao_social = Column(String(255), nullable=True)
    destinatario_cnpj_cpf = Column(String(14), nullable=True)
    json_nfe = Column(JSONB if os.getenv('DB_TYPE') == 'postgresql' else Text, nullable=True) # Removido NOT NULL conforme script
    data_criacao = Column(DateTime, default=datetime.now, nullable=True) # Removido NOT NULL conforme script

    __table_args__ = (
        UniqueConstraint('nfe_emitida_id', 'cliente_id', name='nfe_cliente_pk'), # PK composta
    )

    # Relacionamento
    cliente = relationship('Cliente', back_populates='nfes_emitidas')

    def to_dict(self):
        data = serialize_sqla_object(self)
        # JSONB é serializado diretamente, mas se for Text em outro DB, pode precisar de json.loads()
        return data

    def __repr__(self):
        return f"<NFeEmitidas(id={self.nfe_emitida_id}, tipo_nfe='{self.tipo_nfe}', cliente_id={self.cliente_id})>"

class Cfop(Base):
    __tablename__ = 'cfops'
    cfop_id = Column(Integer, primary_key=True)
    cfop = Column(String(5), unique=True, nullable=True) # Removido NOT NULL conforme script
    descricao = Column(Text, nullable=True) # Removido NOT NULL conforme script
    observacao = Column(Text, nullable=True) # Removido NOT NULL conforme script
    tipooperacao = Column(String(50), nullable=True)
    identificadordestinooperacao = Column(String(50), nullable=True)

    # Relacionamento
    regras_tributacao = relationship('RegraTributacao', back_populates='cfop_obj') # Renomeado para cfop_obj para não conflitar com atributo 'cfop'

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<Cfop(id={self.cfop_id}, codigo='{self.cfop}', descricao='{self.descricao[:30]}...')>"

class Ncm(Base):
    __tablename__ = 'ncms'
    ncm_id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=True) # Removido NOT NULL conforme script
    descricao = Column(Text, nullable=True) # Removido NOT NULL conforme script
    data_Fim = Column(DateTime, nullable=True) # No script é timestamp without time zone
    data_Inicio = Column(DateTime, nullable=True) # No script é timestamp without time zone
    tipo_ato = Column(Text, nullable=True)
    numero_ato = Column(String(20), nullable=True)
    ano_ato = Column(String(4), nullable=True)

    # Relacionamento
    produtos = relationship('Produto', back_populates='ncm')
    regras_tributacao = relationship('RegraTributacao', back_populates='ncm')

    def to_dict(self):
        return serialize_sqla_object(self)
    
    def __repr__(self):
        return f"<Ncm(id={self.ncm_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"

class Produto(Base):
    __tablename__ = 'produtos'
    produto_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    codigo_interno = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=True) # Removido NOT NULL conforme script
    ncm_id = Column(Integer, ForeignKey('ncms.ncm_id'), nullable=True) # Removido NOT NULL conforme script
    cest = Column(String(7), nullable=True)
    unidade_comercial = Column(String(6), nullable=True) # Removido NOT NULL conforme script
    preco_unitario_padrao = Column(Numeric(15, 2), nullable=True) # Removido NOT NULL conforme script
    origem_mercadoria = Column(Integer, nullable=True) # Removido NOT NULL conforme script. No script é integer, que assume ser FK para codigo da origens_mercadoria, mas o tipo não indica isso diretamente.
    tipo_item = Column(String(10), nullable=True) # Removido NOT NULL conforme script
    ativo = Column(Boolean, default=True, nullable=True) # Removido NOT NULL conforme script

    __table_args__ = (
        UniqueConstraint('cliente_id', 'codigo_interno', name='codigo_interno_u'), # Ajustado nome
    )

    # Relacionamentos
    cliente = relationship('Cliente', back_populates='produtos')
    ncm = relationship('Ncm', back_populates='produtos')

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<Produto(id={self.produto_id}, codigo='{self.codigo_interno}', descricao='{self.descricao[:30]}...')>"

class RegraTributacao(Base):
    __tablename__ = 'regras_tributacao'
    regra_tributacao_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    regime_tributario_id = Column(Integer, ForeignKey('regimes_tributarios.regime_tributario_id'), nullable=False)
    cfop_id = Column(Integer, ForeignKey('cfops.cfop_id'), nullable=False)
    ncm_id = Column(Integer, ForeignKey('ncms.ncm_id'), nullable=False) # No script é not null
    uf_origem = Column(String(2), nullable=True)
    uf_destino = Column(String(2), nullable=True)
    tipo_item = Column(String(10), nullable=True)
    prioridade = Column(Integer, nullable=True) # No script é integer sem default
    cst_icms = Column(String(2), nullable=True) # No script é varchar(2)
    csosn_icms = Column(String(3), nullable=True) # No script é varchar(3)
    aliquota_icms = Column(Numeric(5, 2), nullable=True)
    reducao_base_icms = Column(Numeric(5, 2), nullable=True)
    modalidade_bc_icms = Column(Integer, nullable=True)
    motivo_desoneracao_icms = Column(Integer, nullable=True)
    cst_pis = Column(String(3), nullable=True) # No script é varchar(3)
    aliquota_pis = Column(Numeric(5, 2), nullable=True)
    cst_cofins = Column(String(3), nullable=True) # No script é varchar(3)
    aliquota_cofins = Column(Numeric(5, 2), nullable=True)
    cst_ipi = Column(String(3), nullable=True) # No script é varchar(3)
    aliquota_ipi = Column(Numeric(5, 2), nullable=True)
    descricao_regra = Column(Text, nullable=True)
    data_criacao = Column(DateTime, nullable=True) # No script é timestamp sem default
    ativo = Column(Boolean, nullable=True) # No script é boolean sem default

    # Relacionamentos
    cliente = relationship('Cliente', back_populates='regras_tributacao')
    regime_tributario_obj = relationship('RegimeTributario') # Relacionamento para RegimeTributario
    cfop_obj = relationship('Cfop', back_populates='regras_tributacao') # Renomeado para cfop_obj
    ncm = relationship('Ncm', back_populates='regras_tributacao')

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<RegraTributacao(id={self.regra_tributacao_id}, cliente_id={self.cliente_id}, cfop_id={self.cfop_id}, ncm_id={self.ncm_id}, prioridade={self.prioridade})>"
from sqlalchemy import BigInteger, create_engine, Column, Integer, String, Boolean, Text, DateTime, Date, ForeignKey, Numeric, LargeBinary, UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB 

from datetime import datetime, date, timezone, timedelta
import os
import base64 
from decimal import Decimal 
from flask_login import UserMixin

# Timezone de Brasília para defaults
def datetime_now_brt():
    """Retorna datetime atual em BRT (America/Sao_Paulo)"""
    brasilia_tz = timezone(timedelta(hours=-3))
    return datetime.now(brasilia_tz)
from sqlalchemy import text

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
            data[column.name] = float(value) 
        elif isinstance(value, bytes): 
            try:
                data[column.name] = base64.b64encode(value).decode('utf-8')
            except (TypeError, AttributeError):
                data[column.name] = None
        else:
            data[column.name] = value
    return data

# --- SISTEMA DE USUÁRIOS E PERMISSÕES ---

class UserModel(Base):
    """Modelo SQLAlchemy para a tabela users"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    _is_active = Column('is_active', Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # [OK] Relacionamentos usando strings para evitar import circular
    user_roles = relationship("UserRole", back_populates="user")
    user_clients = relationship("UserClient", back_populates="user")

class User(UserMixin):
    """Classe de usuário para Flask-Login (não é um modelo SQLAlchemy)"""
    def __init__(self, id, username, email, _is_active, roles=None, clients=None):
        self.id = id
        self.username = username
        self.email = email
        self._is_active = _is_active
        self.roles = roles or []
        self.clients = clients or []

    @property
    def is_active(self):
        return self._is_active

    def is_admin(self):
        """Verifica se o usuário é administrador da plataforma"""
        admin_roles = ['admin', 'super_admin']
        return any(role.get('name', '').lower() in admin_roles for role in self.roles)
    
    
    
    def is_super_admin(self):
        """Verifica se o usuário tem a role super_admin"""
        return any(role.get('name', '').lower() == 'super_admin' for role in self.roles)

    def get_accessible_clients(self):
        """Retorna lista de clientes que o usuário pode acessar"""
        if self.is_super_admin():
            # Admin pode acessar todos os clientes
            from database.connection import get_db  # [OK] CORREÇÃO: Import correto
            db = next(get_db())
            result = db.execute(text("""
                SELECT c.cliente_id, c.razao_social, c.nome_fantasia, c.cnpj
                FROM clientes c
                WHERE c.ativo = true
                ORDER BY c.razao_social
            """))
            return [dict(row._mapping) for row in result]
        else:
            # Usuário comum só acessa clientes vinculados
            return self.clients

    def can_access_client(self, cliente_id):
        """Verifica se o usuário pode acessar um cliente específico"""
        if self.is_super_admin():
            return True
        
        return any(client['cliente_id'] == cliente_id for client in self.clients)

    def has_permission(self, permission_name):
        """Verifica se o usuário tem uma permissão específica"""
        if self.is_super_admin():
            return True
        
        for role in self.roles:
            if hasattr(role, 'permissions'):
                for perm in role.permissions:
                    if perm.name == permission_name:
                        return True
        return False

    @staticmethod
    def get(user_id):
        """Carrega usuário com roles e clientes"""
        from database.connection import get_db  # [OK] CORREÇÃO: Import correto
        db = next(get_db())
        
        # Buscar dados do usuário
        user_result = db.execute(text("""
            SELECT id, username, email, is_active as _is_active
            FROM users 
            WHERE id = :user_id AND is_active = true
        """), {"user_id": user_id})
        
        user_data = user_result.first()
        if not user_data:
            return None

        # Buscar roles do usuário
        roles_result = db.execute(text("""
            SELECT r.id, r.name, r.description,
                   p.id as perm_id, p.name as perm_name, p.description as perm_desc
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            JOIN roles r ON ur.role_id = r.id
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN permissions p ON rp.permission_id = p.id
            WHERE u.id = :user_id
        """), {"user_id": user_id})

        # Organizar roles e permissões
        roles_dict = {}
        for row in roles_result:
            role_id = row.id
            if role_id not in roles_dict:
                roles_dict[role_id] = {
                    'id': role_id,
                    'name': row.name,
                    'description': row.description,
                    'permissions': []
                }
            
            if row.perm_id:
                perm = {
                    'id': row.perm_id,
                    'name': row.perm_name,
                    'description': row.perm_desc
                }
                if perm not in roles_dict[role_id]['permissions']:
                    roles_dict[role_id]['permissions'].append(perm)

        # Buscar clientes do usuário
        clients_result = db.execute(text("""
            SELECT c.cliente_id, c.razao_social, c.nome_fantasia, c.cnpj
            FROM user_clients uc
            JOIN clientes c ON uc.client_id = c.cliente_id
            WHERE uc.user_id = :user_id AND c.ativo = true
            ORDER BY c.razao_social
        """), {"user_id": user_id})

        clients = [dict(row._mapping) for row in clients_result]

        # Criar objeto User
        user = User(
            id=user_data.id,
            username=user_data.username,
            email=user_data.email,
            _is_active=user_data._is_active,
            roles=[type('Role', (), role) for role in roles_dict.values()],
            clients=clients
        )

        return user

    @staticmethod
    def authenticate(username, password):
        """Autentica usuário e retorna objeto User completo"""
        from werkzeug.security import check_password_hash
        from database.connection import get_db  # [OK] CORREÇÃO: Import correto
        
        db = next(get_db())
        result = db.execute(text("""
            SELECT id, username, password_hash, email, is_active as _is_active
            FROM users 
            WHERE username = :username AND is_active = true
        """), {"username": username})
        
        user_data = result.first()
        if user_data and check_password_hash(user_data.password_hash, password):
            return User.get(user_data.id)
        
        return None

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False) 
    description = Column(Text, nullable=True) 

    # [OK] Relacionamentos usando strings
    user_roles = relationship('UserRole', back_populates='role')
    role_permissions = relationship('RolePermission', back_populates='role')

class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False) 
    description = Column(Text, nullable=True) 

    # [OK] Relacionamentos usando strings
    role_permissions = relationship('RolePermission', back_populates='permission')

class UserRole(Base):
    __tablename__ = 'user_roles'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)

    # [OK] Relacionamentos corrigidos
    user = relationship('UserModel', back_populates='user_roles')
    role = relationship('Role', back_populates='user_roles')

class RolePermission(Base):
    __tablename__ = 'role_permissions'
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(Integer, ForeignKey('permissions.id'), primary_key=True)

    # [OK] Relacionamentos corrigidos
    role = relationship('Role', back_populates='role_permissions')
    permission = relationship('Permission', back_populates='role_permissions')

class UserClient(Base):
    __tablename__ = 'user_clients'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    client_id = Column(Integer, ForeignKey('clientes.cliente_id'), primary_key=True)

    # [OK] Relacionamentos corrigidos
    user = relationship('UserModel', back_populates='user_clients')
    client = relationship('Cliente', back_populates='user_clients')

# --- TABELAS DE APOIO / CONFIGURAÇÃO ---

class RegimeTributario(Base):
    __tablename__ = 'regimes_tributarios'
    regime_tributario_id = Column(Integer, primary_key=True)
    nome = Column(String(255), unique=True, nullable=False)
    descricao = Column(String(255), nullable=True)
    crt = Column(Integer, default=1, nullable=False)  # 1=Simples Nacional, 3=Lucro Real/Presumido
    
    # Relacionamento de volta para Cliente
    clientes = relationship('Cliente', back_populates='regime_tributario')

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<RegimeTributario(id={self.regime_tributario_id}, nome='{self.nome}', crt={self.crt})>"

class ClassificacaoIBSCBS(Base):
    """Classificações tributárias IBS/CBS da Reforma Tributária"""
    __tablename__ = 'classificacoes_ibs_cbs'
    
    classificacao_id = Column(Integer, primary_key=True)
    codigo = Column(String(10), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)
    aliquota_ibs_uf = Column(Numeric(5, 2), default=0.10, nullable=False)
    aliquota_ibs_mun = Column(Numeric(5, 2), default=0.00, nullable=False)
    aliquota_cbs = Column(Numeric(5, 2), default=0.90, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # Relacionamento com produtos
    produtos = relationship('Produto', back_populates='classificacao_ibs_cbs')

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<ClassificacaoIBSCBS(id={self.classificacao_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"

class AutorizacaoXMLNFe(Base):
    """CPFs/CNPJs autorizados a baixar o XML da NFe"""
    __tablename__ = 'autorizacoes_xml_nfe'
    
    autorizacao_id = Column(Integer, primary_key=True)
    nfe_emitida_id = Column(BigInteger, nullable=False)
    cliente_id = Column(BigInteger, nullable=False)
    cpf_cnpj = Column(String(14), nullable=False)
    tipo = Column(String(3), nullable=False)  # 'CPF' ou 'CNPJ'
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # Foreign key composta
    __table_args__ = (
        ForeignKeyConstraint(
            ['nfe_emitida_id', 'cliente_id'],
            ['nfe_emitidas.nfe_emitida_id', 'nfe_emitidas.cliente_id'],
            ondelete='CASCADE'
        ),
    )
    
    # Relacionamento com NFe
    nfe = relationship('NFeEmitidas', foreign_keys=[nfe_emitida_id, cliente_id])

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<AutorizacaoXMLNFe(id={self.autorizacao_id}, tipo='{self.tipo}', cpf_cnpj='{self.cpf_cnpj}')>"

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
    
class Cfop(Base):
    __tablename__ = 'cfops'
    cfop_id = Column(Integer, primary_key=True)
    cfop = Column(String(5), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)
    observacao = Column(Text, nullable=False)
    tipooperacao = Column(String(50), nullable=True)
    identificadordestinooperacao = Column(String(50), nullable=True)

    # [OK] Relacionamentos corrigidos
    regras_tributacao = relationship('RegraTributacao', back_populates='cfop')

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<Cfop(id={self.cfop_id}, codigo='{self.cfop}', descricao='{self.descricao[:30]}...')>"

class OrigemMercadoria(Base):
    __tablename__ = 'origens_mercadoria'
    origem_id = Column(Integer, primary_key=True)
    codigo = Column(String(1), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<OrigemMercadoria(id={self.origem_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"

class MotivoDesoneracao(Base):
    __tablename__ = 'motivos_desoneracao_icms'

    motivo_id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(2), unique=True, nullable=False) 
    descricao = Column(String(255), nullable=False) 

    def to_dict(self):
        data = {}
        for col in self.__table__.columns:
            value = getattr(self, col.name)
            if isinstance(value, (datetime, date)):
                data[col.name] = value.isoformat()
            elif isinstance(value, Decimal):
                data[col.name] = float(value)
            else:
                data[col.name] = value
        return data

    def __repr__(self):
        return f"<MotivoDesoneracao(id={self.motivo_id}, codigo='{self.codigo}', descricao='{self.descricao[:30]}...')>"

# --- TABELAS PRINCIPAIS DE NEGÓCIO ---

class Cliente(Base):
    __tablename__ = 'clientes'
    cliente_id = Column(Integer, primary_key=True)
    cnpj = Column(String(18), unique=True, nullable=False) 
    razao_social = Column(String(255), nullable=False) 
    nome_fantasia = Column(String(255), nullable=True)
    inscricao_estadual = Column(String(14), nullable=True)
    inscricao_municipal = Column(String(14), nullable=True)
    regime_tributario_id = Column(Integer, ForeignKey('regimes_tributarios.regime_tributario_id'), nullable=False)
    cnae = Column(String(7), nullable=True)
    logradouro = Column(String(255), nullable=False) 
    numero = Column(String(10), nullable=False) 
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=False) 
    codigo_municipio = Column(String(7), nullable=False) 
    nome_municipio = Column(String(100), nullable=False) 
    uf = Column(String(2), nullable=False) 
    cep = Column(String(9), nullable=False) 
    email_contato = Column(String(255), nullable=True)
    telefone_contato = Column(String(20), nullable=True)
    ambiente = Column(Integer, default=1, nullable=False)  # 1=Homologação, 2=Produção
    logo_path = Column(String(255), nullable=True)  # Caminho do arquivo de logo
    ativo = Column(Boolean, default=True, nullable=False) 
    data_cadastro = Column(DateTime, default=datetime.now, nullable=False) 
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False) 

    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # [OK] Relacionamentos corrigidos
    regime_tributario = relationship('RegimeTributario', back_populates='clientes')
    certificados = relationship('CertificadoDigital', back_populates='cliente', cascade='all, delete-orphan')
    nfes_emitidas = relationship('NFeEmitidas', back_populates='cliente', cascade='all, delete-orphan')
    produtos = relationship('Produto', back_populates='cliente', cascade='all, delete-orphan')
    regras_tributacao = relationship('RegraTributacao', back_populates='cliente', cascade='all, delete-orphan')
    regras_servicos = relationship('RegraTributacaoServico', back_populates='cliente', cascade='all, delete-orphan')
    destinatarios_nfe = relationship('DestinatarioNFe', back_populates='cliente', cascade='all, delete-orphan')
    assinaturas = relationship('AssinaturaCliente', back_populates='cliente', cascade='all, delete-orphan')

    # [OK] Relacionamento para multi-tenancy corrigido
    user_clients = relationship('UserClient', back_populates='client', cascade='all, delete-orphan')

    # [OK] Relacionamento com o usuário que criou - usando string
    created_by_user = relationship('UserModel', foreign_keys=[created_by_user_id])

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<Cliente(id={self.cliente_id}, razao_social='{self.razao_social}', cnpj='{self.cnpj}')>"

class DestinatarioNFe(Base):
    __tablename__ = 'destinatarios_nfe'

    destinatario_id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False) 
    
    # Dados Básicos
    tipo_pessoa = Column(String(1), nullable=False)
    nome_razao_social = Column(String(255), nullable=False)
    cpf_cnpj = Column(String(14), unique=True, nullable=False)
    ie = Column(String(14), nullable=True) 
    ie_indicador_nfe = Column(String(1), default='C', nullable=False) 
    email = Column(String(255), nullable=True)
    telefone = Column(String(20), nullable=True)

    # Endereço
    logradouro = Column(String(255), nullable=False)
    numero = Column(String(60), nullable=False)
    complemento = Column(String(255), nullable=True)
    bairro = Column(String(255), nullable=False)
    cep = Column(String(8), nullable=False)
    codigo_municipio = Column(String(7), nullable=False)
    nome_municipio = Column(String(255), nullable=False)
    uf = Column(String(2), nullable=False)
    codigo_uf = Column(String(2), nullable=False)
    codigo_pais = Column(String(4), default='1058', nullable=False)
    nome_pais = Column(String(255), default='Brasil', nullable=False)

    data_cadastro = Column(DateTime, default=datetime.now, nullable=False)
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # [OK] Relacionamentos corrigidos
    cliente = relationship('Cliente', back_populates='destinatarios_nfe')
    created_by_user = relationship('UserModel', foreign_keys=[created_by_user_id])

    def to_dict(self):
        data = {}
        for col in self.__table__.columns:
            value = getattr(self, col.name)
            if isinstance(value, (datetime, date)):
                data[col.name] = value.isoformat()
            elif isinstance(value, Decimal):
                data[col.name] = float(value) 
            else:
                data[col.name] = value
        return data

    def __repr__(self):
        return f"<DestinatarioNFe(id={self.destinatario_id}, nome='{self.nome_razao_social}', cnpj='{self.cpf_cnpj}')>"

class CertificadoDigital(Base):
    __tablename__ = 'certificados_digitais'
    certificado_digital_id = Column(BigInteger, primary_key=True, index=True)
    cliente_id = Column(BigInteger, ForeignKey('clientes.cliente_id'), nullable=False)
    
    fingerprint = Column(String(64), unique=True, nullable=False) 
    conteudo_certificado = Column(Text, nullable=False)
    senha_certificado = Column(Text, nullable=False)
    validade_inicio = Column(DateTime, nullable=False) 
    validade_fim = Column(DateTime, nullable=False) 
    ativo = Column(Boolean, nullable=False, default=True) 
    data_upload = Column(DateTime, nullable=False, default=datetime.now) 
    nome_arquivo_original = Column(String(255), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Suporte A1/A3
    tipo_certificado = Column(String(10), default='A1', nullable=False)  # 'A1' ou 'A3'
    token_slot_id = Column(Integer, nullable=True)  # Slot ID do token (apenas A3)
    token_label = Column(String(255), nullable=True)  # Label no token (apenas A3)
    pkcs11_library = Column(String(500), nullable=True)  # Biblioteca PKCS#11 (apenas A3)

    # [OK] Relacionamentos corrigidos
    cliente = relationship('Cliente', back_populates='certificados')
    created_by_user = relationship('UserModel', foreign_keys=[created_by_user_id])

    def to_dict(self):
        return serialize_sqla_object(self)
        
    def __repr__(self):
        return f"<CertificadoDigital(id={self.certificado_digital_id}, cliente_id={self.cliente_id}, ativo={self.ativo}, validade_fim='{self.validade_fim}')>"

class NFeEmitidas(Base):
    __tablename__ = 'nfe_emitidas'
    nfe_emitida_id = Column(BigInteger, primary_key=True, index=True)
    cliente_id = Column(BigInteger, ForeignKey('clientes.cliente_id'), nullable=False)
    tipo_nfe = Column(String(10), nullable=False)  # 0=Entrada, 1=Saída
    modelo = Column(String(2), nullable=True)  # 55=NFe, 65=NFCe
    serie = Column(Integer, default=1, nullable=True)  # Série da NFe
    numero = Column(Integer, nullable=True)  # Número sequencial da NFe
    finalidade_emissao = Column(Integer, nullable=False) 
    natureza_operacao = Column(String(255), nullable=False) 
    informacoes_adicionais = Column(Text, nullable=True)
    destinatario_razao_social = Column(String(255), nullable=True)
    destinatario_cnpj_cpf = Column(String(14), nullable=True)
    json_nfe = Column(JSONB if os.getenv('DB_TYPE') == 'postgresql' else Text, nullable=True) 
    data_criacao = Column(DateTime, default=datetime_now_brt, nullable=False)  # Usando timezone BRT
    data_emissao = Column(DateTime, nullable=True)  # Data de emissão da NFe
    valor_total = Column(Numeric(15, 2), nullable=True)  # Valor total da NFe
    created_by_user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True)

    # Campos IBS/CBS (Reforma Tributária - apenas para CRT=3)
    total_ibs = Column(Numeric(15, 2), default=0, nullable=True)  # Total IBS
    total_cbs = Column(Numeric(15, 2), default=0, nullable=True)  # Total CBS
    total_ibs_bc = Column(Numeric(15, 2), default=0, nullable=True)  # Base cálculo IBS/CBS
    valor_icms_st_retido = Column(Numeric(15, 2), default=0, nullable=True)  # ICMS ST Retido

    status = Column(String(50), default='RASCUNHO')
    chave_acesso = Column(String(44))
    protocolo_sefaz = Column(String(15))
    data_autorizacao = Column(DateTime)
    mensagem_sefaz = Column(Text)

    __table_args__ = (
        UniqueConstraint('nfe_emitida_id', 'cliente_id', name='nfe_cliente_pk'), 
    )

    def __init__(self, **kwargs):
        super(NFeEmitidas, self).__init__(**kwargs)

    # [OK] Relacionamento corrigido
    cliente = relationship('Cliente', back_populates='nfes_emitidas')

    def to_dict(self):
        data = serialize_sqla_object(self)
        return data

    def __repr__(self):
        return f"<NFeEmitidas(id={self.nfe_emitida_id}, tipo_nfe='{self.tipo_nfe}', cliente_id={self.cliente_id})>"

class Ncm(Base):
    __tablename__ = 'ncms'
    ncm_id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)
    data_fim = Column(DateTime, nullable=True) 
    data_inicio = Column(DateTime, nullable=True)
    tipo_ato = Column(Text, nullable=True)
    numero_ato = Column(String(20), nullable=True)
    ano_ato = Column(String(4), nullable=True)

    # [OK] Relacionamentos corrigidos
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
    descricao = Column(Text, nullable=False)
    ncm_id = Column(Integer, ForeignKey('ncms.ncm_id'), nullable=False)
    cest = Column(String(7), nullable=True)
    unidade_comercial = Column(String(6), nullable=False)
    preco_unitario_padrao = Column(Numeric(15, 2), nullable=False)
    origem_mercadoria = Column(Integer, ForeignKey('origens_mercadoria.origem_id'), nullable=False)
    tipo_item = Column(String(10), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Campos adicionais
    cfop_id = Column(Integer, ForeignKey('cfops.cfop_id'), nullable=True)
    cst_id = Column(Integer, ForeignKey('cst_icms.cst_id'), nullable=True)
    csosn_id = Column(Integer, ForeignKey('csosn_icms.csosn_id'), nullable=True)
    classificacao_ibs_cbs_id = Column(Integer, ForeignKey('classificacoes_ibs_cbs.classificacao_id'), nullable=True)
    
    __table_args__ = (
        UniqueConstraint('cliente_id', 'codigo_interno', name='codigo_interno_u'),
    )

    # [OK] Relacionamentos corrigidos
    cliente = relationship('Cliente', back_populates='produtos')
    ncm = relationship('Ncm', back_populates='produtos')
    cfop = relationship('Cfop', foreign_keys=[cfop_id])
    origem = relationship('OrigemMercadoria')
    csts_icms = relationship('Csticms', foreign_keys=[cst_id])
    csosns_icms = relationship('Csosnicms', foreign_keys=[csosn_id])
    classificacao_ibs_cbs = relationship('ClassificacaoIBSCBS', back_populates='produtos')
    created_by_user = relationship('UserModel', foreign_keys=[created_by_user_id])

    def to_dict(self):
        data = serialize_sqla_object(self)
        # Adiciona dados dos relacionamentos necessários para o frontend
        if self.ncm:
            data['ncm'] = {'codigo': self.ncm.codigo, 'descricao': self.ncm.descricao}
        else:
            data['ncm'] = None
        if self.cfop:
            data['cfop'] = {'cfop': self.cfop.cfop, 'descricao': self.cfop.descricao}
        else:
            data['cfop'] = None
        if self.origem:
            data['origem'] = {'codigo': self.origem.codigo, 'descricao': self.origem.descricao}
        else:
            data['origem'] = None
        if self.csts_icms:
            data['csts_icms'] = {'codigo': self.csts_icms.codigo, 'descricao': self.csts_icms.descricao}
        else:
            data['csts_icms'] = None
        if self.csosns_icms:
            data['csosns_icms'] = {'codigo': self.csosns_icms.codigo, 'descricao': self.csosns_icms.descricao}
        else:
            data['csosns_icms'] = None

        return data

    def __repr__(self):
        return f"<Produto(id={self.produto_id}, codigo='{self.codigo_interno}', descricao='{self.descricao[:30]}...')>"

class RegraTributacao(Base):
    __tablename__ = 'regras_tributacao'
    regra_tributacao_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    regime_tributario_id = Column(Integer, ForeignKey('regimes_tributarios.regime_tributario_id'), nullable=False)
    cfop_id = Column(Integer, ForeignKey('cfops.cfop_id'), nullable=True)  # [OK] CORRIGIDO: pode ser NULL
    ncm_id = Column(Integer, ForeignKey('ncms.ncm_id'), nullable=True)     # [OK] CORRIGIDO: pode ser NULL
    uf_origem = Column(String(2), nullable=True)
    uf_destino = Column(String(2), nullable=True)
    tipo_item = Column(String(10), nullable=True)
    prioridade = Column(Integer, nullable=True, default=100) 
    cst_icms = Column(String(2), ForeignKey('cst_icms.codigo'), nullable=True) 
    csosn_icms = Column(String(3), ForeignKey('csosn_icms.codigo'), nullable=True)  
    aliquota_icms = Column(Numeric(5, 2), nullable=True)
    reducao_base_icms = Column(Numeric(5, 2), nullable=True)
    modalidade_bc_icms = Column(Integer, nullable=True)
    motivo_desoneracao_icms = Column(Integer, ForeignKey('motivos_desoneracao_icms.motivo_id'), nullable=True) 
    cst_pis = Column(String(3), nullable=True)
    aliquota_pis = Column(Numeric(5, 2), nullable=True)
    cst_cofins = Column(String(3), nullable=True)
    aliquota_cofins = Column(Numeric(5, 2), nullable=True)
    cst_ipi = Column(String(3), nullable=True)
    aliquota_ipi = Column(Numeric(5, 2), nullable=True)
    descricao_regra = Column(Text, nullable=True)
    data_criacao = Column(DateTime, nullable=False, default=datetime_now_brt)  # Usando timezone BRT
    ativo = Column(Boolean, nullable=False, default=True) 
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # [OK] Relacionamentos corrigidos
    cliente = relationship('Cliente', back_populates='regras_tributacao')
    regime_tributario = relationship('RegimeTributario')
    cfop = relationship('Cfop', back_populates='regras_tributacao')
    ncm = relationship('Ncm', back_populates='regras_tributacao')
    cst_icms_obj = relationship('Csticms', foreign_keys='RegraTributacao.cst_icms')
    csosn_icms_obj = relationship('Csosnicms', foreign_keys='RegraTributacao.csosn_icms')
    motivo_desoneracao = relationship('MotivoDesoneracao')
    created_by_user = relationship('UserModel', foreign_keys=[created_by_user_id])

    def to_dict(self):
        data = {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
        # Converter tipos específicos para JSON-serializáveis
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, date):
                data[key] = value.isoformat()
            elif isinstance(value, Decimal):
                data[key] = float(value)

        # Adicionar dados de relacionamentos
        if self.regime_tributario:
            data['regime_tributario_nome'] = self.regime_tributario.nome
        if self.cfop:
            data['cfop_codigo'] = self.cfop.cfop
        if self.ncm:
            data['ncm_codigo'] = self.ncm.codigo
        if self.cst_icms_obj:
            data['cst_icms_codigo'] = self.cst_icms_obj.codigo
        if self.csosn_icms_obj:
            data['csosn_icms_codigo'] = self.csosn_icms_obj.codigo
        if self.motivo_desoneracao:
            data['motivo_desoneracao_codigo'] = self.motivo_desoneracao.codigo
        
        return data

    def __repr__(self):
        return f"<RegraTributacao(id={self.regra_tributacao_id}, cliente_id={self.cliente_id}, cfop_id={self.cfop_id}, ncm_id={self.ncm_id}, prioridade={self.prioridade})>"


class RegraTributacaoServico(Base):
    """Regras tributárias específicas para NFS-e (serviços)"""
    __tablename__ = 'regras_tributacao_servicos'
    
    regra_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    regime_tributario_id = Column(Integer, ForeignKey('regimes_tributarios.regime_tributario_id'), nullable=False)
    
    # Identificação do serviço
    codigo_servico_lc116 = Column(String(5), nullable=False)
    codigo_nbs = Column(String(9), nullable=False, default='101010000')
    descricao_servico = Column(Text, nullable=True)
    
    # ISS (Imposto Sobre Serviços)
    aliquota_iss = Column(Numeric(5, 2), nullable=False, default=5.00)
    iss_retido = Column(Boolean, default=False)
    responsavel_retencao = Column(String(1), nullable=True)
    
    # Reforma Tributária LC 214/2025
    cst_ibs_cbs = Column(String(3), default='001')
    codigo_indicador_operacao = Column(String(6), default='000001')
    codigo_classificacao_tributaria = Column(String(6), default='000001')
    codigo_localidade_incidencia = Column(String(7), default='3549805')
    percentual_redutor = Column(Numeric(5, 2), default=0.00)
    
    # Percentuais de Tributos
    percentual_total_tributos_federais = Column(Numeric(5, 2), default=0.00)
    percentual_total_tributos_estaduais = Column(Numeric(5, 2), default=0.00)
    percentual_total_tributos_municipais = Column(Numeric(5, 2), default=5.00)
    
    # Regime Especial
    regime_especial_tributacao = Column(String(1), nullable=True)
    optante_simples_nacional = Column(Boolean, default=True)
    incentivador_cultural = Column(Boolean, default=False)
    
    # Condições de aplicação
    uf_origem = Column(String(2), nullable=True)
    uf_destino = Column(String(2), nullable=True)
    indicador_destinatario = Column(String(1), default='0')
    indicador_consumidor_final = Column(String(1), default='0')
    finalidade_nfse = Column(String(1), default='0')
    
    # Controle e auditoria
    prioridade = Column(Integer, default=100)
    descricao_regra = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime, nullable=False, default=datetime_now_brt)
    data_atualizacao = Column(DateTime, nullable=False, default=datetime_now_brt, onupdate=datetime_now_brt)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relacionamentos
    cliente = relationship('Cliente', back_populates='regras_servicos')
    regime_tributario = relationship('RegimeTributario')
    created_by_user = relationship('UserModel', foreign_keys=[created_by_user_id])
    updated_by_user = relationship('UserModel', foreign_keys=[updated_by_user_id])
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        data = {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
        # Converter tipos específicos para JSON-serializáveis
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, date):
                data[key] = value.isoformat()
            elif isinstance(value, Decimal):
                data[key] = float(value)
        
        # Adicionar dados de relacionamentos
        if self.regime_tributario:
            data['regime_tributario_nome'] = self.regime_tributario.nome
        if self.cliente:
            data['cliente_razao_social'] = self.cliente.razao_social
        if self.created_by_user:
            data['created_by_username'] = self.created_by_user.username
        
        return data
    
    def __repr__(self):
        return f"<RegraTributacaoServico(id={self.regra_id}, cliente_id={self.cliente_id}, codigo_servico={self.codigo_servico_lc116}, aliquota_iss={self.aliquota_iss})>"


# --- SISTEMA DE PLANOS E ASSINATURAS ---

class PlanoNFe(Base):
    """Planos de cobrança para emissão de NFe"""
    __tablename__ = 'planos_nfe'
    
    plano_id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    tipo_plano = Column(String(20), nullable=False)  # 'AVULSO' ou 'PACOTE'
    quantidade_nfes = Column(Integer)  # NULL para avulso ou ilimitado
    valor_mensal = Column(Numeric(10, 2), nullable=False)
    valor_por_nfe = Column(Numeric(10, 2))  # Valor unitário
    ativo = Column(Boolean, default=True)
    ordem_exibicao = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamentos
    assinaturas = relationship('AssinaturaCliente', back_populates='plano')
    
    def __init__(self, **kwargs):
        super(PlanoNFe, self).__init__(**kwargs)
    
    def to_dict(self):
        return serialize_sqla_object(self)
    
    def __repr__(self):
        return f"<PlanoNFe(id={self.plano_id}, nome='{self.nome}', tipo='{self.tipo_plano}')>"


class AssinaturaCliente(Base):
    """Assinaturas dos clientes aos planos de NFe"""
    __tablename__ = 'assinaturas_cliente'
    
    assinatura_id = Column(Integer, primary_key=True)
    cliente_id = Column(BigInteger, ForeignKey('clientes.cliente_id'), nullable=False)
    plano_id = Column(Integer, ForeignKey('planos_nfe.plano_id'), nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date)  # NULL = sem data de término
    status = Column(String(20), default='ATIVA')  # ATIVA, SUSPENSA, CANCELADA
    dia_vencimento = Column(Integer, default=10)
    nfes_consumidas = Column(Integer, default=0)
    periodo_ref_inicio = Column(Date)
    periodo_ref_fim = Column(Date)
    observacoes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamentos
    cliente = relationship('Cliente', back_populates='assinaturas')
    plano = relationship('PlanoNFe', back_populates='assinaturas')
    
    def __init__(self, **kwargs):
        super(AssinaturaCliente, self).__init__(**kwargs)
    
    def to_dict(self):
        data = serialize_sqla_object(self)
        if self.plano:
            data['plano_nome'] = self.plano.nome
            data['plano_tipo'] = self.plano.tipo_plano
            data['plano_quantidade'] = self.plano.quantidade_nfes
        if self.cliente:
            data['cliente_nome'] = self.cliente.nome_razao_social
        return data
    
    def pode_emitir(self):
        """Verifica se pode emitir NFe baseado no plano e consumo"""
        if self.status != 'ATIVA':
            return False, f'Assinatura {self.status.lower()}'
        
        if self.data_fim and self.data_fim < date.today():
            return False, 'Assinatura expirada'
        
        # Avulso sempre pode
        if self.plano.tipo_plano == 'AVULSO':
            return True, 'Plano avulso'
        
        # Ilimitado sempre pode
        if self.plano.quantidade_nfes is None:
            return True, 'Plano ilimitado'
        
        # Verificar limite do pacote
        if self.nfes_consumidas >= self.plano.quantidade_nfes:
            return False, f'Limite atingido ({self.nfes_consumidas}/{self.plano.quantidade_nfes})'
        
        return True, f'Disponíveis: {self.plano.quantidade_nfes - self.nfes_consumidas}'
    
    def registrar_emissao(self):
        """Incrementa contador de NFes consumidas"""
        self.nfes_consumidas += 1
        self.updated_at = datetime.now()
    
    def __repr__(self):
        return f"<AssinaturaCliente(id={self.assinatura_id}, cliente_id={self.cliente_id}, plano='{self.plano.nome if self.plano else 'N/A'}', status='{self.status}')>"


# --- API KEYS E WEBHOOKS ---

class ApiKey(Base):
    """Modelo para API Keys de integração"""
    __tablename__ = 'api_keys'
    
    api_key_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id', ondelete='CASCADE'), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    key_prefix = Column(String(20), nullable=False)
    nome = Column(String(100), nullable=False)
    ativa = Column(Boolean, default=True)
    criada_em = Column(DateTime, default=datetime.now)
    ultima_utilizacao = Column(DateTime)
    expira_em = Column(DateTime)
    rate_limit = Column(Integer, default=1000)
    ip_whitelist = Column(Text)  # JSON
    permissoes = Column(Text)  # JSON
    
    # Relacionamentos
    cliente = relationship('Cliente')
    
    def to_dict(self):
        import json
        data = serialize_sqla_object(self)
        # Converter JSON strings em objetos
        if self.ip_whitelist:
            try:
                data['ip_whitelist'] = json.loads(self.ip_whitelist)
            except:
                data['ip_whitelist'] = []
        if self.permissoes:
            try:
                data['permissoes'] = json.loads(self.permissoes)
            except:
                data['permissoes'] = {}
        return data
    
    def is_valid(self):
        """Verifica se a chave está válida"""
        if not self.ativa:
            return False
        if self.expira_em and self.expira_em < datetime.now():
            return False
        return True
    
    def has_permission(self, permission):
        """Verifica se tem uma permissão específica"""
        import json
        if not self.permissoes:
            return True  # Sem restrições
        try:
            perms = json.loads(self.permissoes)
            return permission in perms.get('allowed', [])
        except:
            return True
    
    def __repr__(self):
        return f"<ApiKey(id={self.api_key_id}, cliente_id={self.cliente_id}, nome='{self.nome}', ativa={self.ativa})>"


class ApiUsageLog(Base):
    """Modelo para logs de uso da API"""
    __tablename__ = 'api_usage_logs'
    
    log_id = Column(BigInteger, primary_key=True)
    api_key_id = Column(Integer, ForeignKey('api_keys.api_key_id', ondelete='SET NULL'))
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id', ondelete='CASCADE'), nullable=False)
    endpoint = Column(String(255), nullable=False)
    metodo = Column(String(10), nullable=False)
    status_code = Column(Integer)
    ip_origem = Column(String(45))
    user_agent = Column(Text)
    request_time = Column(DateTime, default=datetime.now)
    response_time_ms = Column(Integer)
    erro = Column(Text)
    
    # Relacionamentos
    api_key = relationship('ApiKey')
    cliente = relationship('Cliente')
    
    def to_dict(self):
        return serialize_sqla_object(self)
    
    def __repr__(self):
        return f"<ApiUsageLog(id={self.log_id}, endpoint='{self.endpoint}', status={self.status_code})>"


class Webhook(Base):
    """Modelo para webhooks de notificação"""
    __tablename__ = 'webhooks'
    
    webhook_id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id', ondelete='CASCADE'), nullable=False)
    url = Column(String(500), nullable=False)
    eventos = Column(Text, nullable=False)  # JSON array
    ativo = Column(Boolean, default=True)
    secret = Column(String(255))
    retry_count = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=30)
    criado_em = Column(DateTime, default=datetime.now)
    ultima_tentativa = Column(DateTime)
    ultimo_sucesso = Column(DateTime)
    total_sucessos = Column(Integer, default=0)
    total_falhas = Column(Integer, default=0)
    
    # Relacionamentos
    cliente = relationship('Cliente')
    
    def to_dict(self):
        import json
        data = serialize_sqla_object(self)
        if self.eventos:
            try:
                data['eventos'] = json.loads(self.eventos)
            except:
                data['eventos'] = []
        return data
    
    def supports_event(self, event):
        """Verifica se o webhook está inscrito neste evento"""
        import json
        try:
            eventos_list = json.loads(self.eventos)
            return event in eventos_list
        except:
            return False
    
    def __repr__(self):
        return f"<Webhook(id={self.webhook_id}, cliente_id={self.cliente_id}, url='{self.url}', ativo={self.ativo})>"


class WebhookQueue(Base):
    """Modelo para fila de webhooks"""
    __tablename__ = 'webhook_queue'
    
    queue_id = Column(BigInteger, primary_key=True)
    webhook_id = Column(Integer, ForeignKey('webhooks.webhook_id', ondelete='CASCADE'), nullable=False)
    evento = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)  # JSON
    tentativas = Column(Integer, default=0)
    max_tentativas = Column(Integer, default=3)
    proximo_retry = Column(DateTime)
    status = Column(String(20), default='pending')
    criado_em = Column(DateTime, default=datetime.now)
    processado_em = Column(DateTime)
    erro = Column(Text)
    
    # Relacionamentos
    webhook = relationship('Webhook')
    
    def to_dict(self):
        import json
        data = serialize_sqla_object(self)
        if self.payload:
            try:
                data['payload'] = json.loads(self.payload)
            except:
                data['payload'] = {}
        return data
    
    def __repr__(self):
        return f"<WebhookQueue(id={self.queue_id}, evento='{self.evento}', status='{self.status}', tentativas={self.tentativas})>"
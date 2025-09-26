from sqlalchemy import BigInteger, create_engine, Column, Integer, String, Boolean, Text, DateTime, Date, ForeignKey, Numeric, LargeBinary, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB 

from datetime import datetime, date
import os
import base64 
from decimal import Decimal 
from flask_login import UserMixin
from database.connection import get_db
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
            except (TypeError, AttributeError): # Captura caso value seja None ou não tenha .encode()
                data[column.name] = None
        else:
            data[column.name] = value
    return data

# --- NOVAS TABELAS ---

class User(UserMixin):
    def __init__(self, id, username, email, _is_active, roles=None, clients=None):
        self.id = id
        self.username = username
        self.email = email
        self._is_active = _is_active
        self.roles = roles or []
        self.clients = clients or []

    def is_active(self):
        return self._is_active

    def is_admin(self):
        """Verifica se o usuário é administrador da plataforma"""
        admin_roles = ['admin', 'super_admin', 'platform_admin']
        return any(role.name.lower() in admin_roles for role in self.roles)

    def get_accessible_clients(self):
        """Retorna lista de clientes que o usuário pode acessar"""
        if self.is_admin():
            # Admin pode acessar todos os clientes
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
        if self.is_admin():
            return True
        
        return any(client['cliente_id'] == cliente_id for client in self.clients)

    def has_permission(self, permission_name):
        """Verifica se o usuário tem uma permissão específica"""
        if self.is_admin():
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
        db = next(get_db())
        
        # Buscar dados do usuário
        user_result = db.execute(text("""
            SELECT id, username, email, _is_active
            FROM users 
            WHERE id = :user_id AND _is_active = true
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
        
        db = next(get_db())
        result = db.execute(text("""
            SELECT id, username, password_hash, email, _is_active
            FROM users 
            WHERE username = :username AND _is_active = true
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

    # Relacionamentos
    users = relationship('UserRole', back_populates='role')
    permissions = relationship('RolePermission', back_populates='role')

class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False) 
    description = Column(Text, nullable=True) 

    # Relacionamentos
    roles = relationship('RolePermission', back_populates='permission')

class UserRole(Base):
    __tablename__ = 'user_roles'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)

    user = relationship('User', back_populates='roles')
    role = relationship('Role', back_populates='users')

class RolePermission(Base):
    __tablename__ = 'role_permissions'
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(Integer, ForeignKey('permissions.id'), primary_key=True)

    role = relationship('Role', back_populates='permissions')
    permission = relationship('Permission', back_populates='roles')

class UserClient(Base):
    __tablename__ = 'user_clients'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    client_id = Column(Integer, ForeignKey('clientes.cliente_id'), primary_key=True)

    user = relationship('User', back_populates='clients')
    client = relationship('Cliente', back_populates='users_access')

# --- Tabelas de Apoio / Configuração ---

class RegimeTributario(Base):
    __tablename__ = 'regimes_tributarios'
    regime_tributario_id = Column(Integer, primary_key=True)
    nome = Column(String(255), unique=True, nullable=False)
    descricao = Column(String(255), nullable=True)
    
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
    
class Cfop(Base):
    __tablename__ = 'cfops'
    cfop_id = Column(Integer, primary_key=True)
    cfop = Column(String(5), unique=True, nullable=False) # No script db sjtnfe.txt é NOT NULL
    descricao = Column(Text, nullable=False) # No script db sjtnfe.txt é NOT NULL
    observacao = Column(Text, nullable=False) # No script db sjtnfe.txt é NOT NULL
    tipooperacao = Column(String(50), nullable=True)
    identificadordestinooperacao = Column(String(50), nullable=True)

    # Relacionamento
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

# --- Tabelas Principais de Negócio ---

class DestinatarioNFe(Base):
    __tablename__ = 'destinatarios_nfe'

    destinatario_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # cliente_id é NOT NULL no script db sjtnfe.txt
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

    # Relacionamento com Cliente
    cliente = relationship('Cliente', back_populates='destinatarios_nfe')
    created_by_user = relationship('User')

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
    ativo = Column(Boolean, default=True, nullable=False) 
    data_cadastro = Column(DateTime, default=datetime.now, nullable=False) 
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False) 

    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relacionamentos
    regime_tributario = relationship('RegimeTributario', back_populates='clientes')
    certificados = relationship('CertificadoDigital', back_populates='cliente', cascade='all, delete-orphan')
    nfes_emitidas = relationship('NFeEmitidas', back_populates='cliente', cascade='all, delete-orphan')
    produtos = relationship('Produto', back_populates='cliente', cascade='all, delete-orphan')
    regras_tributacao = relationship('RegraTributacao', back_populates='cliente', cascade='all, delete-orphan')
    destinatarios_nfe = relationship('DestinatarioNFe', back_populates='cliente', cascade='all, delete-orphan')

    # Novo relacionamento para multi-tenancy
    users_access = relationship('UserClient', back_populates='client', cascade='all, delete-orphan')

    # Relacionamento com o usuário que criou
    created_by_user = relationship('User')

    def to_dict(self):
        return serialize_sqla_object(self)

    def __repr__(self):
        return f"<Cliente(id={self.cliente_id}, razao_social='{self.razao_social}', cnpj='{self.cnpj}')>"

class CertificadoDigital(Base):
    __tablename__ = 'certificados_digitais'
    certificado_digital_id = Column(BigInteger, primary_key=True, index=True)
    cliente_id = Column(BigInteger, ForeignKey('clientes.cliente_id'), nullable=False)
    
    # fingerprint é UNIQUE e NOT NULL no script db sjtnfe.txt
    fingerprint = Column(String(64), unique=True, nullable=False) 
    # conteudo_certificado e senha_certificado são bytea NOT NULL no script db sjtnfe.txt
    conteudo_certificado = Column(Text, nullable=False)
    senha_certificado = Column(Text, nullable=False)
    # validade_inicio, validade_fim, ativo, data_upload são NOT NULL no script db sjtnfe.txt
    validade_inicio = Column(DateTime, nullable=False) 
    validade_fim = Column(DateTime, nullable=False) 
    ativo = Column(Boolean, nullable=False, default=True) 
    data_upload = Column(DateTime, nullable=False, default=datetime.now) 
    nome_arquivo_original = Column(String(255), nullable=True) # Este pode ser nullable, pois o script não o marca como NOT NULL
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        # UniqueConstraint('fingerprint', 'cliente_id', name='fingerprint_cliente_uc'), # Composto, se necessário
        # Mantendo apenas 'fingerprint' unique como no script para compatibilidade direta.
    )

    cliente = relationship('Cliente', back_populates='certificados')
    created_by_user = relationship('User')

    def to_dict(self):
        return serialize_sqla_object(self)
        
    def __repr__(self):
        return f"<CertificadoDigital(id={self.certificado_digital_id}, cliente_id={self.cliente_id}, ativo={self.ativo}, validade_fim='{self.validade_fim}')>"

class NFeEmitidas(Base):
    __tablename__ = 'nfe_emitidas'
    nfe_emitida_id = Column(BigInteger, primary_key=True, index=True)
    cliente_id = Column(BigInteger, ForeignKey('clientes.cliente_id'), nullable=False)
    # Estas colunas eram NOT NULL no script db sjtnfe.txt
    tipo_nfe = Column(String(10), nullable=False) 
    finalidade_emissao = Column(Integer, nullable=False) 
    natureza_operacao = Column(String(255), nullable=False) 
    informacoes_adicionais = Column(Text, nullable=True) # No script é Text, que pode ser NULL
    destinatario_razao_social = Column(String(255), nullable=True) # No script é varchar(255), que pode ser NULL
    destinatario_cnpj_cpf = Column(String(14), nullable=True) # No script é varchar(14), que pode ser NULL
    json_nfe = Column(JSONB if os.getenv('DB_TYPE') == 'postgresql' else Text, nullable=True) 
    data_criacao = Column(DateTime, default=datetime.now, nullable=False) 
    created_by_user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True) # Auditoria

    status = Column(String(50), default='RASCUNHO') # Ex: 'RASCUNHO', 'AUTORIZADA', 'REJEITADA', 'CANCELADA'
    chave_acesso = Column(String(44)) # Chave de acesso da NF-e (44 dígitos)
    protocolo_sefaz = Column(String(15)) # Protocolo de autorização da SEFAZ
    data_autorizacao = Column(DateTime) # Data e hora da autorização pela SEFAZ
    mensagem_sefaz = Column(Text) # Mensagem de retorno da SEFAZ (em caso de rejeição, por exemplo)


    __table_args__ = (
        UniqueConstraint('nfe_emitida_id', 'cliente_id', name='nfe_cliente_pk'), 
    )

    # Relacionamento
    cliente = relationship('Cliente', back_populates='nfes_emitidas')

    def to_dict(self):
        data = serialize_sqla_object(self)
        return data

    def __repr__(self):
        return f"<NFeEmitidas(id={self.nfe_emitida_id}, tipo_nfe='{self.tipo_nfe}', cliente_id={self.cliente_id})>"



class Ncm(Base):
    __tablename__ = 'ncms'
    ncm_id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False) # No script db sjtnfe.txt é NOT NULL
    descricao = Column(Text, nullable=False) # No script db sjtnfe.txt é NOT NULL
    data_Fim = Column(DateTime, nullable=True) 
    data_Inicio = Column(DateTime, nullable=True)
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
    descricao = Column(Text, nullable=False)
    ncm_id = Column(Integer, ForeignKey('ncms.ncm_id'), nullable=False)
    cest = Column(String(7), nullable=True)
    unidade_comercial = Column(String(6), nullable=False)
    preco_unitario_padrao = Column(Numeric(15, 2), nullable=False)
    origem_mercadoria = Column(Integer, ForeignKey('origens_mercadoria.origem_id'), nullable=False)
    tipo_item = Column(String(10), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    __table_args__ = (
        UniqueConstraint('cliente_id', 'codigo_interno', name='codigo_interno_u'),
    )

    # --- CAMPOS ADICIONADOS AQUI ---
    cfop_id = Column(Integer, ForeignKey('cfops.cfop_id'), nullable=True) # Pode ser nulo se não houver um CFOP padrão
    cst_id = Column(Integer, ForeignKey('cst_icms.cst_id'), nullable=True) # Pode ser nulo
    csosn_id = Column(Integer, ForeignKey('csosn_icms.csosn_id'), nullable=True) # Pode ser nulo
    # -------------------------------

    # Relacionamentos
    cliente = relationship('Cliente', back_populates='produtos')
    ncm = relationship('Ncm', back_populates='produtos')
    cfop = relationship('Cfop', foreign_keys=[cfop_id]) # Adicionado foreign_keys para evitar ambiguidade com a RegraTributacao
    origem = relationship('OrigemMercadoria')
    csts_icms = relationship('Csticms', foreign_keys=[cst_id]) # Novo relacionamento para CST
    csosns_icms = relationship('Csosnicms', foreign_keys=[csosn_id]) # Novo relacionamento para CSOSN
    created_by_user = relationship('User')

    def to_dict(self):
        data = serialize_sqla_object(self)
        # Adiciona dados dos relacionamentos necessários para o frontend
        if self.ncm:
            data['ncm'] = {'codigo': self.ncm.codigo, 'descricao': self.ncm.descricao}
        else:
            data['ncm'] = None
        if self.cfop: # AGORA PEGA DO PRODUTO
            data['cfop'] = {'cfop': self.cfop.cfop, 'descricao': self.cfop.descricao}
        else:
            data['cfop'] = None
        if self.origem:
            data['origem'] = {'codigo': self.origem.codigo, 'descricao': self.origem.descricao}
        else:
            data['origem'] = None
        if self.csts_icms: # NOVO
            data['csts_icms'] = {'codigo': self.csts_icms.codigo, 'descricao': self.csts_icms.descricao}
        else:
            data['csts_icms'] = None
        if self.csosns_icms: # NOVO
            data['csosns_icms'] = {'codigo': self.csosns_icms.codigo, 'descricao': self.csosns_icms.descricao}
        else:
            data['csosns_icms'] = None

        return data

    def __repr__(self):
        return f"<Produto(id={self.produto_id}, codigo='{self.codigo_interno}', descricao='{self.descricao[:30]}...')>"

class RegraTributacao(Base):
    __tablename__ = 'regras_tributacao'
    regra_tributacao_id = Column(Integer, primary_key=True)
    
    # cliente_id é NOT NULL no script db sjtnfe.txt
    cliente_id = Column(Integer, ForeignKey('clientes.cliente_id'), nullable=False)
    
    regime_tributario_id = Column(Integer, ForeignKey('regimes_tributarios.regime_tributario_id'), nullable=False)
    cfop_id = Column(Integer, ForeignKey('cfops.cfop_id'), nullable=False)
    ncm_id = Column(Integer, ForeignKey('ncms.ncm_id'), nullable=False) # No script é not null
    uf_origem = Column(String(2), nullable=True)
    uf_destino = Column(String(2), nullable=True)
    tipo_item = Column(String(10), nullable=True)
    prioridade = Column(Integer, nullable=True, default=100) 
    cst_icms = Column(String(2), ForeignKey('cst_icms.codigo'), nullable=True) 
    csosn_icms = Column(String(3), ForeignKey('csosn_icms.codigo'), nullable=True)  
    aliquota_icms = Column(Numeric(5, 2), nullable=True)
    reducao_base_icms = Column(Numeric(5, 2), nullable=True)
    modalidade_bc_icms = Column(Integer, nullable=True)
    # CORREÇÃO CRÍTICA: motivo_desoneracao_icms deve ser um ForeignKey
    motivo_desoneracao_icms = Column(Integer, ForeignKey('motivos_desoneracao_icms.motivo_id'), nullable=True) 
    cst_pis = Column(String(3), nullable=True)
    aliquota_pis = Column(Numeric(5, 2), nullable=True)
    cst_cofins = Column(String(3), nullable=True)
    aliquota_cofins = Column(Numeric(5, 2), nullable=True)
    cst_ipi = Column(String(3), nullable=True)
    aliquota_ipi = Column(Numeric(5, 2), nullable=True)
    descricao_regra = Column(Text, nullable=True)
    data_criacao = Column(DateTime, nullable=False, default=datetime.now) 
    ativo = Column(Boolean, nullable=False, default=True) 
    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relacionamentos
    cliente = relationship('Cliente', back_populates='regras_tributacao')
    regime_tributario = relationship('RegimeTributario')
    cfop = relationship('Cfop') # Ajustado para 'cfop' que é o nome da relação em Cfop
    ncm = relationship('Ncm')
    cst_icms_obj = relationship('Csticms', foreign_keys='RegraTributacao.cst_icms')
    csosn_icms_obj = relationship('Csosnicms', foreign_keys='RegraTributacao.csosn_icms')
    motivo_desoneracao = relationship('MotivoDesoneracao')
    created_by_user = relationship('User')

    def to_dict(self):
        data = {
            # Serializa todas as colunas diretas
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
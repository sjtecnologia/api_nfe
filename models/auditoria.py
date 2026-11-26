"""
Modelo de Auditoria para rastreamento de ações no sistema
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from database.models import Base  # Corrigido: importar de database.models

class Auditoria(Base):
    """
    Modelo para registro de auditoria de ações no sistema
    
    Campos:
    - auditoria_id: ID único do registro
    - user_id: ID do usuário que realizou a ação
    - acao: Tipo de ação (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.)
    - tabela_afetada: Nome da tabela afetada pela ação
    - registro_id: ID do registro afetado
    - timestamp: Data/hora da ação
    - dados_antes: Estado anterior do registro (JSON)
    - dados_depois: Estado posterior do registro (JSON)
    - ip_address: IP do cliente
    - user_agent: User agent do navegador
    - descricao: Descrição adicional da ação
    """
    
    __tablename__ = 'auditoria'
    
    auditoria_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Corrigido: 'users' não 'usuarios'
    acao = Column(String(50), nullable=False, index=True)
    tabela_afetada = Column(String(100), nullable=True, index=True)
    registro_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))
    dados_antes = Column(JSONB, nullable=True)
    dados_depois = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 pode ter até 45 caracteres
    user_agent = Column(Text, nullable=True)
    descricao = Column(Text, nullable=True)
    
    # Relacionamento com User (opcional, já que pode ser None para ações do sistema)
    # user = relationship("User", backref="auditorias")
    
    def __repr__(self):
        return f'<Auditoria {self.auditoria_id}: {self.acao} em {self.tabela_afetada} por user {self.user_id}>'
    
    def to_dict(self):
        """Converte o registro para dicionário"""
        return {
            'auditoria_id': self.auditoria_id,
            'user_id': self.user_id,
            'acao': self.acao,
            'tabela_afetada': self.tabela_afetada,
            'registro_id': self.registro_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp is not None else None,
            'dados_antes': self.dados_antes,
            'dados_depois': self.dados_depois,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'descricao': self.descricao
        }

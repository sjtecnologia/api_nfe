#!/usr/bin/env python3
"""
Fix para o erro 'NoneType' object is not subscriptable no dashboard.
Causa: cliente.cnpj é NULL para produtor rural, mas o template faz cliente.cnpj[:2]
Fix 1: Adicionar cpf e produtor_rural ao modelo Cliente em models.py
Fix 2: Corrigir template dashboard.html para tratar cnpj nulo
"""
import re

def apply_fix(filepath, old, new, descricao):
    with open(filepath, 'r') as f:
        content = f.read()
    if old not in content:
        print(f"  [!]  AVISO: trecho não encontrado em {filepath}: {descricao}")
        return False
    if new in content:
        print(f"  [~]  JÁ APLICADO: {descricao}")
        return True
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  [OK]  {descricao}")
    return True


print("\n=== Fix 1: models.py - adicionar cpf e produtor_rural ao modelo Cliente ===")

apply_fix(
    '/home/ubuntu/api_nfe/database/models.py',
    '''    ativo = Column(Boolean, default=True, nullable=False)
    data_cadastro = Column(DateTime, default=datetime.now, nullable=False)
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)''',
    '''    cpf = Column(String(14), unique=True, nullable=True)
    produtor_rural = Column(Boolean, default=False, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    data_cadastro = Column(DateTime, default=datetime.now, nullable=False)
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    created_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)''',
    'models.py: adicionar cpf e produtor_rural ao Cliente'
)

print("\n=== Fix 2: dashboard.html - exibir CPF ou CNPJ condicionalmente ===")

apply_fix(
    '/home/ubuntu/api_nfe/templates/cliente/dashboard.html',
    '''                                    <strong>CNPJ:</strong> {{ cliente.cnpj[:2] }}.{{ cliente.cnpj[2:5] }}.{{ cliente.cnpj[5:8] }}/{{ cliente.cnpj[8:12] }}-{{ cliente.cnpj[12:] }}''',
    '''                                    {% if cliente.produtor_rural and cliente.cpf %}
                                    <strong>CPF:</strong> {{ cliente.cpf[:3] }}.{{ cliente.cpf[3:6] }}.{{ cliente.cpf[6:9] }}-{{ cliente.cpf[9:] }}
                                    {% elif cliente.cnpj %}
                                    <strong>CNPJ:</strong> {{ cliente.cnpj[:2] }}.{{ cliente.cnpj[2:5] }}.{{ cliente.cnpj[5:8] }}/{{ cliente.cnpj[8:12] }}-{{ cliente.cnpj[12:] }}
                                    {% endif %}''',
    'dashboard.html: exibir CPF ou CNPJ condicionalmente'
)

print("\n=== Fix concluido! ===\n")

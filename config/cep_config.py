"""
Configuração para busca de CEP
Permite modo offline para desenvolvimento
"""

import os

# Modo de desenvolvimento (permite CEPs de teste sem internet)
DEV_MODE = os.getenv('CEP_DEV_MODE', 'false').lower() == 'true'

# CEPs de teste para desenvolvimento (quando sem internet)
CEPS_TESTE = {
    '01310100': {
        'cep': '01310-100',
        'logradouro': 'Avenida Paulista',
        'complemento': 'lado ímpar',
        'bairro': 'Bela Vista',
        'localidade': 'São Paulo',
        'uf': 'SP',
        'ibge': '3550308',
        'ddd': '11'
    },
    '20040020': {
        'cep': '20040-020',
        'logradouro': 'Avenida Rio Branco',
        'complemento': '',
        'bairro': 'Centro',
        'localidade': 'Rio de Janeiro',
        'uf': 'RJ',
        'ibge': '3304557',
        'ddd': '21'
    },
    '30130100': {
        'cep': '30130-100',
        'logradouro': 'Avenida Afonso Pena',
        'complemento': '',
        'bairro': 'Centro',
        'localidade': 'Belo Horizonte',
        'uf': 'MG',
        'ibge': '3106200',
        'ddd': '31'
    },
    '40020000': {
        'cep': '40020-000',
        'logradouro': 'Praça da Sé',
        'complemento': '',
        'bairro': 'Centro',
        'localidade': 'Salvador',
        'uf': 'BA',
        'ibge': '2927408',
        'ddd': '71'
    },
    '80010000': {
        'cep': '80010-000',
        'logradouro': 'Praça Tiradentes',
        'complemento': '',
        'bairro': 'Centro',
        'localidade': 'Curitiba',
        'uf': 'PR',
        'ibge': '4106902',
        'ddd': '41'
    }
}

def get_cep_teste(cep_limpo):
    """Retorna dados de CEP de teste se disponível"""
    if cep_limpo in CEPS_TESTE:
        return CEPS_TESTE[cep_limpo]
    return None

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.nfce_generator import gerar_xml_nfce, validar_nfce
from utils.nfce_validators import validar_dados_nfce


def test_nfce_generate_ibscbs_when_classificacao_exists():
    dados = {
        'emitente': {
            'cnpj': '12345678000190',
            'razao_social': 'Emitente Teste LTDA',
            'nome_fantasia': 'Emitente Teste',
            'inscricao_estadual': '123456789',
            'regime_tributario': 3,
            'logradouro': 'Rua A',
            'numero': '100',
            'bairro': 'Centro',
            'codigo_municipio': '3550308',
            'municipio': 'Sao Paulo',
            'uf': 'SP',
            'uf_codigo': 35,
            'cep': '01001000',
        },
        'nfce_info': {
            'numero': 1,
            'serie': 1,
            'modelo': '65',
            'tipo_emissao': '1',
            'finalidade': '1',
            'destino_operacao': '1',
            'tipo_impressao': '4',
            'ambiente': '2',
        },
        'itens': [{
            'codigo': 'PROD1',
            'descricao': 'Produto teste',
            'ncm': '12345678',
            'cfop': '5102',
            'unidade': 'UN',
            'quantidade': 1,
            'valor_unitario': 100.0,
            'valor_total': 100.0,
            'csosn': '102',
            'origem': '0',
            'classificacao_ibs_cbs': {
                'classificacao_id': 1,
                'codigo': '00-00001',
                'aliquota_ibs_uf': 1.0,
                'aliquota_ibs_mun': 0.5,
                'aliquota_cbs': 2.0,
            },
        }],
        'totais': {
            'valor_produtos': 100.0,
            'valor_desconto': 0.0,
            'valor_total': 100.0,
            'base_calculo': 0,
            'valor_icms': 0,
        },
        'pagamento': {
            'forma_pagamento': '01',
            'valor': 100.0,
        },
        'emitente_crt': 3,
    }

    valido, erros = validar_nfce(dados)
    assert valido, erros

    xml = gerar_xml_nfce(dados)
    assert '<IBSCBS>' in xml
    assert '<IBSCBSTot>' in xml
    assert '<cClassTrib>000001</cClassTrib>' in xml


def test_nfce_requires_classificacao_for_crt3():
    dados = {
        'emitente_id': 1,
        'emitente_crt': 3,
        'produtos': [{
            'produto': type('ProdutoFake', (), {'classificacao_ibs_cbs': None})(),
            'quantidade': 1,
            'valor_unitario': 10,
            'desconto': 0,
        }],
        'forma_pagamento': '01',
        'valor_pago': 10,
        'troco': 0,
        'informacoes_adicionais': '',
        'destinatario': {},
    }

    erros = validar_dados_nfce(dados)
    assert any('Classificação IBS/CBS obrigatória para CRT=3' in erro for erro in erros)
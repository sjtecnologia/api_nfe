import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.nfe_validators import validar_dados_nfe


def _emitente_base():
    return {
        'cnpj': '12345678000190',
        'razao_social': 'Emitente Teste LTDA',
        'inscricao_estadual': '123456789',
        'logradouro': 'Rua A',
        'uf': 'SP',
    }


def _destinatario_base():
    return {
        'cpf_cnpj': '12345678901',
        'nome_razao_social': 'Consumidor Teste',
        'logradouro': 'Rua B',
        'uf': 'SP',
    }


def _form_base():
    return {
        'natOp': 'Venda',
        'serie': '1',
        'formaPagamento': '01',
        'regime_tributario_id': 3,
    }


def _item_base():
    return {
        'quantidade': 1,
        'valor_unitario': 100.0,
        'ncm': '12345678',
        'cfop': '5102',
        'cst_icms': '00',
        'origem': '0',
    }


def test_nfe_requires_ibs_cbs_classification_for_crt3():
    erros = validar_dados_nfe(
        _form_base(),
        _emitente_base(),
        _destinatario_base(),
        [_item_base()],
    )

    assert any('Classificação IBS/CBS é obrigatória para CRT=3' in erro for erro in erros)


def test_nfe_accepts_ibs_cbs_classification_for_crt3():
    item = _item_base()
    item['classificacao_ibs_cbs_id'] = 10

    erros = validar_dados_nfe(
        _form_base(),
        _emitente_base(),
        _destinatario_base(),
        [item],
    )

    assert not any('Classificação IBS/CBS é obrigatória para CRT=3' in erro for erro in erros)
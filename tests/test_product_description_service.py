"""Testes da geração assistida de descrição comercial."""

from unittest.mock import patch

import pytest

from services.product_description_service import ProductDescriptionError, ProductDescriptionService


def test_contexto_usa_apenas_campos_comerciais_permitidos():
    context = ProductDescriptionService._build_context(
        {
            'produto_id': 10,
            'cliente_id': 5,
            'descricao': 'Mouse sem fio',
            'codigo_interno': 'M001',
            'ncm_codigo': '84716053',
            'senha': 'nao deveria',
            'cpf_cnpj': '12345678900',
        },
        'Cor preta',
    )

    assert context == {
        'produto_id': 10,
        'descricao': 'Mouse sem fio',
        'codigo_interno': 'M001',
        'ncm_codigo': '84716053',
        'informacoes_adicionais': 'Cor preta',
    }


def test_resposta_estruturada_e_validada():
    service = ProductDescriptionService(db=None)
    result = service._validate_result({
        'titulo': 'Mouse sem fio',
        'descricao_curta': 'Mouse sem fio para uso diário.',
        'descricao_completa': 'Descrição comercial baseada nos dados fornecidos.',
        'caracteristicas': ['Sem fio'],
        'beneficios': ['Liberdade de movimentação'],
        'palavras_chave': ['mouse', 'sem fio'],
        'avisos': [],
    })

    assert result['caracteristicas'] == ['Sem fio']
    assert result['beneficios'] == ['Liberdade de movimentação']


def test_resposta_sem_campo_obrigatorio_falha():
    with pytest.raises(ProductDescriptionError):
        ProductDescriptionService(db=None)._validate_result({
            'titulo': 'Produto',
            'descricao_curta': 'Curta',
        })


def test_informacao_adicional_respeita_limite():
    with pytest.raises(ProductDescriptionError):
        ProductDescriptionService(db=None).generate(
            product_data={'descricao': 'Produto'},
            additional_info='x' * 2001,
            cliente_id=1,
            user_id=1,
        )

from services.nfe_service import validar_tributacao_nfe


EMITENTE_SIMPLES = {'regime_tributario_id': 1}
DESTINATARIO_NAO_CONTRIBUINTE = {
    'cpf_cnpj': '12345678909',
    'ie_indicador_nfe': 'N',
    'inscricao_estadual': '',
}


def test_bloqueia_csosn_101_para_nao_contribuinte():
    valido, erros = validar_tributacao_nfe(
        EMITENTE_SIMPLES,
        [{'descricao': 'Produto', 'cfop': '5101', 'csosn_icms': '101'}],
        DESTINATARIO_NAO_CONTRIBUINTE,
    )

    assert not valido
    assert any('código 600' in erro for erro in erros)


def test_permite_csosn_102_para_nao_contribuinte():
    valido, erros = validar_tributacao_nfe(
        EMITENTE_SIMPLES,
        [{'descricao': 'Produto', 'cfop': '5101', 'csosn_icms': '102'}],
        DESTINATARIO_NAO_CONTRIBUINTE,
    )

    assert valido
    assert not erros


def test_nao_bloqueia_csosn_101_para_contribuinte_com_ie():
    valido, erros = validar_tributacao_nfe(
        EMITENTE_SIMPLES,
        [{'descricao': 'Produto', 'cfop': '5101', 'csosn_icms': '101'}],
        {'cpf_cnpj': '12345678000195', 'ie_indicador_nfe': 'C', 'inscricao_estadual': '110042490114'},
    )

    assert valido
    assert not erros

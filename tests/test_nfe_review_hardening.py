from utils.nfe_validators import _mascarar_documento


def test_mascarar_documento_vazio():
    assert _mascarar_documento("") == ""


def test_mascarar_documento_cnpj_mostra_so_final():
    assert _mascarar_documento("12.345.678/0001-95") == "**********0195"


def test_mascarar_documento_cpf_mostra_so_final():
    assert _mascarar_documento("123.456.789-09") == "*******8909"


def test_mascarar_documento_curto_mascara_tudo():
    assert _mascarar_documento("123") == "***"

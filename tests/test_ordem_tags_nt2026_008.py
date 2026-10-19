from pathlib import Path

import pytest
from lxml import etree

from services.nfe_nfelib_service import generate_nfe_xml_nfelib

NS = {"n": "http://www.portalfiscal.inf.br/nfe"}
FIXTURE = Path(__file__).parent / "fixtures" / "xml_nt2026_008_minimo.xml"

EMITENTE = {
    "cnpj": "11222333000181", "razao_social": "EMITENTE TESTE LTDA", "inscricao_estadual": "110042490114",
    "logradouro": "Rua A", "numero": "10", "bairro": "Centro", "codigo_municipio": "3550308",
    "municipio": "Sao Paulo", "uf": "SP", "cep": "01001000", "regime_tributario": "1",
}
DESTINATARIO = {
    "cpf_cnpj": "52998224725", "nome": "CLIENTE TESTE", "uf": "SP", "logradouro": "Rua B", "numero": "20",
    "bairro": "Centro", "codigo_municipio": "3550308", "municipio": "Sao Paulo", "cep": "01001000",
}
ITEM = {
    "codigo_produto": "P1", "descricao": "Produto", "ncm": "12345678", "cfop": "5102", "unidade": "UN",
    "quantidade": "2", "valor_unitario": "50.00", "valor_total": "100.00", "csosn_icms": "102", "origem": "0",
}


def _gerar(**extra_form):
    form_data = {
        "tpAmb": 2, "serie": "1", "natOp": "VENDA", "dataEmissao": "2026-10-01T10:00:00",
        "formaPagamento": "01", "valorPagamento": "100.00", "codigo_numerico": "12345678",
        **extra_form,
    }
    xml = generate_nfe_xml_nfelib(EMITENTE, DESTINATARIO, [dict(ITEM)], form_data, 1, {})
    return etree.fromstring(xml.encode("utf-8"))


def _nomes(elemento):
    return [etree.QName(filho).localname for filho in elemento]


def _verificar_item_e_total(raiz):
    prod = raiz.find(".//n:det/n:prod", NS)
    filhos = _nomes(prod)
    i_vprod = filhos.index("vProd")
    assert set(filhos[i_vprod + 1:i_vprod + 3]) == {"vUnComLiq", "vProdLiq"}
    assert filhos[i_vprod + 3] == "cEANTrib"

    total = raiz.find(".//n:total/n:ICMSTot", NS)
    filhos_total = _nomes(total)
    i_total = filhos_total.index("vProd")
    assert filhos_total[i_total + 1] == "vProdLiqTot"
    assert filhos_total[i_total + 2] == "vFrete"


def test_gerador_sem_banco_posiciona_valores_liquidos():
    _verificar_item_e_total(_gerar())


def test_fixture_mantem_a_ordem_validada():
    _verificar_item_e_total(etree.parse(str(FIXTURE)).getroot())


def test_vprodliqtot_e_a_soma_dos_vprodliq():
    raiz = _gerar()
    soma = sum(float(e.text) for e in raiz.findall(".//n:det/n:prod/n:vProdLiq", NS))
    assert float(raiz.find(".//n:total/n:ICMSTot/n:vProdLiqTot", NS).text) == pytest.approx(soma)


def test_icms_previsto_fica_no_grupo_icms_do_imposto_quando_tpnfdebito_06():
    raiz = _gerar(tpNFDebito="06")

    grupo = raiz.find(".//n:det/n:imposto/n:ICMS/n:ICMSPrevistoPagtoAntecip", NS)
    assert grupo is not None
    assert grupo.getparent().tag == f"{{{NS['n']}}}ICMS"
    assert grupo.getparent().getparent().tag == f"{{{NS['n']}}}imposto"
    assert _nomes(grupo) == ["vICMSPrevisto"]


def test_icms_previsto_ausente_sem_gatilho():
    assert _gerar().find(".//n:ICMSPrevistoPagtoAntecip", NS) is None


def test_icms_previsto_ausente_no_modelo_65():
    raiz = _gerar(tpNFDebito="06", modelo="65")

    assert raiz.find(".//n:ICMSPrevistoPagtoAntecip", NS) is None

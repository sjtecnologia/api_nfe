from datetime import datetime
from urllib.parse import urlsplit

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from services.danfe_simplificado_tipo2_service import (
    DanfeSimplificadoTipo2Service,
    _money_br,
    gerar_qrcode_tipo2,
)


CHAVE = "12345678901234567890123456789012345678901234"
URL_CONSULTA = "https://example.test/consulta"


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _xml_nfe(tp_amb="1", tp_emis="1"):
    return f"""<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe Id="NFe{CHAVE}">
    <ide><tpAmb>{tp_amb}</tpAmb><tpEmis>{tp_emis}</tpEmis><indPres>1</indPres><dhEmi>2026-01-06T10:00:00-03:00</dhEmi><nNF>257</nNF><serie>1</serie></ide>
    <emit><CNPJ>12345678000190</CNPJ><xNome>Emitente de Teste</xNome><enderEmit><xLgr>Rua Teste</xLgr><nro>10</nro><xBairro>Centro</xBairro><xMun>São Paulo</xMun><UF>SP</UF><CEP>01000000</CEP></enderEmit></emit>
    <dest><CNPJ>98765432000110</CNPJ><xNome>Destinatário de Teste</xNome></dest>
    <det nItem="1"><prod><cProd>A1</cProd><xProd>Produto de Teste</xProd><qCom>2.0000</qCom><uCom>UN</uCom><vUnCom>50.00</vUnCom><vProd>100.00</vProd></prod><imposto><IBSCBS><gIBSCBS><vIBS>1.00</vIBS><vCBS>2.00</vCBS><vIS>0.50</vIS></gIBSCBS></IBSCBS></imposto></det>
    <total><ICMSTot><vProd>100.00</vProd><vFrete>0.00</vFrete><vSeg>0.00</vSeg><vDesc>0.00</vDesc><vOutro>0.00</vOutro><vNF>100.00</vNF></ICMSTot></total>
    <pag><detPag><tPag>01</tPag><vPag>100.00</vPag></detPag></pag>
    <infAdic><infAdFisco>Observação fiscal</infAdFisco><infCpl>Informação complementar</infCpl></infAdic>
  </infNFe>
  <urlChave>{URL_CONSULTA}</urlChave>
</NFe>"""


def _gerar(tmp_path, xml, private_key=None, protocolo=None):
    service = DanfeSimplificadoTipo2Service(output_dir=str(tmp_path))
    result = service.gerar_danfe_tipo2_html(
        {"xml": xml, "certificado": private_key},
        protocolo=protocolo,
    )
    assert result
    with open(result, encoding="utf-8") as html_file:
        return html_file.read()


def test_gerar_danfe_tipo2_com_itens_totais_pagamento_e_protocolo(tmp_path):
    html = _gerar(
        tmp_path,
        _xml_nfe(),
        protocolo={"nProt": "135260000000001", "dhRecbto": "2026-01-06T13:00:00-03:00"},
    )

    assert "DANFE Simplificado Tipo 2" in html
    assert "Consulte pela Chave" in html
    assert "Protocolo de autorização" in html
    assert "Produto de Teste" in html
    assert "Pagamento 01" in html


def test_danfe_tipo2_contingencia_mostra_avisos(tmp_path, private_key):
    html = _gerar(tmp_path, _xml_nfe(tp_emis="9"), private_key=private_key)

    assert "EMITIDA EM CONTINGÊNCIA" in html
    assert "Via do Estabelecimento" in html


def test_danfe_tipo2_homologacao_mostra_aviso(tmp_path):
    html = _gerar(tmp_path, _xml_nfe(tp_amb="2"))

    assert "EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO - SEM VALOR FISCAL" in html


def test_gerar_danfe_tipo2_retorna_pdf_valido(tmp_path):
    service = DanfeSimplificadoTipo2Service(output_dir=str(tmp_path))
    output_path = tmp_path / "danfe_tipo2.pdf"

    result = service.gerar_danfe_tipo2(
        {"xml": _xml_nfe()},
        caminho_pdf=str(output_path),
    )

    assert result == str(output_path)
    pdf_bytes = output_path.read_bytes()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 0


def test_qrcode_tipo2_online_tem_parametros_v3():
    url = gerar_qrcode_tipo2(CHAVE, "2", URL_CONSULTA)

    assert url == f"{URL_CONSULTA}?p={CHAVE}|3|2"


def test_qrcode_tipo2_offline_formata_e_assina_parametros(private_key):
    url = gerar_qrcode_tipo2(
        CHAVE,
        "1",
        URL_CONSULTA,
        contingencia=True,
        vnf="12.34",
        tipo_dest="3",
        id_dest="ID-EXTERIOR",
        data_emissao=datetime(2026, 1, 6, 10, 0),
        certificado=private_key,
    )
    parameters = urlsplit(url).query.removeprefix("p=").split("|")

    assert parameters[:4] == [CHAVE, "3", "1", "06"]
    assert len(parameters[4]) == 15
    assert parameters[4].endswith("12.34")
    assert parameters[5:7] == ["3", ""]
    assert parameters[7]
    private_key.public_key().verify(
        __import__("base64").b64decode(parameters[7]),
        "|".join(parameters[:7]).encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA1(),
    )


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(1234.56, "1.234,56"), ("999.9", "999,90"), (0, "0,00"), (None, "0,00"), ("", "0,00"), ("abc", "0,00")],
)
def test_money_br_formata_com_virgula_decimal_e_ponto_de_milhar(valor, esperado):
    assert _money_br(valor) == esperado


def test_cupom_exibe_valores_em_formato_br_e_qr_mantem_ponto_decimal(tmp_path, private_key):
    xml = _xml_nfe(tp_emis="9").replace("<vUnCom>50.00</vUnCom>", "<vUnCom>1234.56</vUnCom>")
    xml = xml.replace("<vProd>100.00</vProd></prod>", "<vProd>2469.12</vProd></prod>")
    xml = xml.replace("<vNF>100.00</vNF>", "<vNF>2469.12</vNF>")

    html = _gerar(tmp_path, xml, private_key=private_key)

    assert "1.234,56" in html
    assert "2.469,12" in html
    assert "|000000002469.12|" in html

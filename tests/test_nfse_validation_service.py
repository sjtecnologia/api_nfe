from services.nfse_validation_service import NFSeValidationService


def test_validar_xml_contra_xsd_valido(tmp_path):
    xsd = tmp_path / "simple.xsd"
    xml = tmp_path / "ok.xml"

    xsd.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xs:schema xmlns:xs=\"http://www.w3.org/2001/XMLSchema\">
  <xs:element name=\"root\">
    <xs:complexType>
      <xs:sequence>
        <xs:element name=\"item\" type=\"xs:string\"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
""",
        encoding="utf-8",
    )
    xml.write_text("<root><item>ok</item></root>", encoding="utf-8")

    result = NFSeValidationService.validar_xml_contra_xsd(
        xml_content=xml.read_text(encoding="utf-8"),
        xsd_path=str(xsd),
    )

    assert result["valido"] is True
    assert result["erros"] == []
    assert "XML válido" in result["mensagem"]


def test_validar_xml_contra_xsd_invalido(tmp_path):
    xsd = tmp_path / "simple.xsd"

    xsd.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xs:schema xmlns:xs=\"http://www.w3.org/2001/XMLSchema\">
  <xs:element name=\"root\">
    <xs:complexType>
      <xs:sequence>
        <xs:element name=\"item\" type=\"xs:string\"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
""",
        encoding="utf-8",
    )

    result = NFSeValidationService.validar_xml_contra_xsd(
        xml_content="<root><other>erro</other></root>",
        xsd_path=str(xsd),
    )

    assert result["valido"] is False
    assert result["erros"]
    assert "XML inválido" in result["mensagem"]


def test_validar_xml_contra_xsd_arquivo_inexistente():
    result = NFSeValidationService.validar_xml_contra_xsd(
        xml_content="<root/>",
        xsd_path="/tmp/arquivo-inexistente-nfse.xsd",
    )

    assert result["valido"] is False
    assert any("não encontrado" in msg for msg in result["erros"])

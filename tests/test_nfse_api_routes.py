from unittest.mock import patch


def test_validar_xml_xsd_nfse_retorna_200_quando_valido(client):
    fake_result = {
        "valido": True,
        "xsd_path": "/tmp/test.xsd",
        "erros": [],
        "mensagem": "XML válido conforme XSD",
    }

    with patch("services.nfse_validation_service.NFSeValidationService.validar_xml_contra_xsd", return_value=fake_result):
        response = client.post(
            "/api/nfse/validar-xml-xsd",
            json={"xml_content": "<root/>"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["valido"] is True


def test_validar_xml_xsd_nfse_retorna_422_quando_invalido(client):
    fake_result = {
        "valido": False,
        "xsd_path": "/tmp/test.xsd",
        "erros": ["Linha 1: erro"],
        "mensagem": "XML inválido conforme XSD",
    }

    with patch("services.nfse_validation_service.NFSeValidationService.validar_xml_contra_xsd", return_value=fake_result):
        response = client.post(
            "/api/nfse/validar-xml-xsd",
            json={"xml_content": "<root/>"},
        )

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["valido"] is False
    assert payload["erros"]


def test_validar_xml_xsd_nfse_retorna_400_sem_xml(client):
    response = client.post("/api/nfse/validar-xml-xsd", json={})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["valido"] is False
    assert "xml_content" in payload["erros"][0]

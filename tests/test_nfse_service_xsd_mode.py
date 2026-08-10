from unittest.mock import patch

from services.nfse_service import NFSeService


def test_xsd_mode_off_ignora_validacao(monkeypatch):
    monkeypatch.setenv("NFSE_XSD_VALIDATION_MODE", "off")
    service = NFSeService(ambiente="homologacao")

    with patch("services.nfse_validation_service.NFSeValidationService.validar_xml_contra_xsd", side_effect=RuntimeError("não deveria chamar")):
        ok, detalhes = service._validar_xml_rps_antes_envio("<xml/>")

    assert ok is True
    assert detalhes is None


def test_xsd_mode_warn_nao_bloqueia(monkeypatch):
    monkeypatch.setenv("NFSE_XSD_VALIDATION_MODE", "warn")
    service = NFSeService(ambiente="homologacao")

    fake_result = {
        "valido": False,
        "xsd_path": "/tmp/schema.xsd",
        "erros": ["Linha 1: erro"],
        "mensagem": "XML inválido conforme XSD",
    }

    with patch("services.nfse_validation_service.NFSeValidationService.validar_xml_contra_xsd", return_value=fake_result):
        ok, detalhes = service._validar_xml_rps_antes_envio("<xml/>")

    assert ok is True
    assert detalhes is not None
    assert detalhes["tipo"] == "xsd_warning"
    assert detalhes["xsd_result"]["valido"] is False


def test_xsd_mode_strict_bloqueia(monkeypatch):
    monkeypatch.setenv("NFSE_XSD_VALIDATION_MODE", "strict")
    service = NFSeService(ambiente="homologacao")

    fake_result = {
        "valido": False,
        "xsd_path": "/tmp/schema.xsd",
        "erros": ["Linha 1: erro"],
        "mensagem": "XML inválido conforme XSD",
    }

    with patch("services.nfse_validation_service.NFSeValidationService.validar_xml_contra_xsd", return_value=fake_result):
        ok, detalhes = service._validar_xml_rps_antes_envio("<xml/>")

    assert ok is False
    assert detalhes is not None
    assert detalhes["xsd_validation_mode"] == "strict"
    assert "Validação XSD" in detalhes["erro"]

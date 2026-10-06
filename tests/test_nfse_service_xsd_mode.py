from unittest.mock import patch

from services.nfse_service import NFSeService, _salvar_dump_debug_nfse
from services.nfse_validation_service import NFSeValidationService


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


def test_homologacao_usa_rtc_e_xsd_estrito_por_padrao(monkeypatch):
    monkeypatch.delenv("GISS_SCHEMA_RTC_HOMOLOGACAO", raising=False)
    monkeypatch.delenv("GISS_SCHEMA_RTC", raising=False)
    monkeypatch.delenv("NFSE_XSD_VALIDATION_MODE", raising=False)

    service = NFSeService(ambiente="homologacao")
    assert service._usar_schema_rtc() is True
    assert service._usar_tomador_plural_rtc() is False

    with patch(
        "services.nfse_validation_service.NFSeValidationService.validar_xml_contra_xsd",
        return_value={"valido": False, "erros": ["Linha 1: erro"]},
    ):
        ok, detalhes = service._validar_xml_rps_antes_envio("<xml/>")

    assert ok is False
    assert detalhes["xsd_validation_mode"] == "strict"


def test_xml_rps_gerado_valida_no_schema_de_envio_padrao(monkeypatch):
    """O modo strict deve aceitar o RPS que será enviado ao GISS."""
    monkeypatch.setenv("GISS_SCHEMA_RTC_HOMOLOGACAO", "true")

    prestador = {
        "cnpj": "12345678000190",
        "inscricao_municipal": "12345",
        "razao_social": "Empresa Teste Ltda",
        "optante_simples": True,
    }
    dados = {
        "cliente_id": 1,
        "numero_rps": 1,
        "serie_rps": "1",
        "tipo_rps": "1",
        "data_competencia": "2026-01-30",
        "tomador_cpf_cnpj": "12345678000190",
        "tomador_razao_social": "Cliente Teste",
        "tomador_logradouro": "Rua Teste",
        "tomador_numero": "1",
        "tomador_bairro": "Centro",
        "tomador_codigo_municipio": "3549805",
        "tomador_uf": "SP",
        "tomador_cep": "15015000",
        "codigo_servico": "01.01",
        "discriminacao": "Teste de envio para homologacao",
        "valor_servico": 1000.0,
        "aliquota_iss": 5.0,
        "codigo_municipio_prestacao": "3549805",
        "codigo_nbs": "101010000",
        "finalidade_nfse": "0",
        "indicador_consumidor_final": "1",
        "codigo_indicador_operacao": "000001",
        "indicador_destinatario": "0",
        "cst_ibs_cbs": "001",
        "codigo_classificacao_tributaria": "000001",
        "codigo_localidade_incidencia": "3549805",
        "percentual_redutor": 0.0,
        "percentual_total_tributos_federais": 9.25,
        "percentual_total_tributos_estaduais": 0.0,
        "percentual_total_tributos_municipais": 5.0,
        "regime_especial_tributacao": "6",
        "optante_simples_nacional": True,
        "incentivador_cultural": False,
    }

    from services.nfse_service import criar_nfse_de_formulario

    xml = NFSeService(ambiente="homologacao").gerar_xml_rps(
        criar_nfse_de_formulario(dados, prestador)
    )
    resultado = NFSeValidationService.validar_xml_contra_xsd(xml)

    assert resultado["valido"] is True, resultado["erros"]
    assert resultado["xsd_path"].endswith("enviar-lote-rps-envio-v2_04.xsd")
    assert "<p1:TomadorServico>" in xml
    assert "<p1:TomadoresServico>" not in xml


def test_assinaturas_ausentes_bloqueiam_envio():
    service = NFSeService(ambiente="homologacao")
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <p:EnviarLoteRpsEnvio xmlns:p="http://www.giss.com.br/enviar-lote-rps-envio-v2_04.xsd"
        xmlns:p1="http://www.giss.com.br/tipos-v2_04.xsd">
      <p:LoteRps Id="lote1" versao="2.04">
        <p1:ListaRps><p1:Rps/></p1:ListaRps>
      </p:LoteRps>
    </p:EnviarLoteRpsEnvio>"""

    ok, erro = service._validar_assinaturas_xml(xml)

    assert ok is False
    assert erro == "Assinatura digital do lote ausente"


def test_dump_de_xml_fica_desabilitado_por_padrao(monkeypatch):
    monkeypatch.delenv("NFSE_DEBUG_XML_DUMP", raising=False)

    with patch("builtins.open") as arquivo, patch("os.chmod") as chmod:
        _salvar_dump_debug_nfse("teste.xml", "<xml/>")

    arquivo.assert_not_called()
    chmod.assert_not_called()

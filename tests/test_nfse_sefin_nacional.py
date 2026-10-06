from unittest.mock import patch

from services.nfse_sefin_nacional import emitir_dps, validar_dps_assinada, _certificate_material, gerar_dps


XML_DPS = '''<DPS xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infDPS Id="DPS123" />
  <Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignedInfo /></Signature>
</DPS>'''


def test_dps_nacional_requires_signature():
    validar_dps_assinada(XML_DPS)


def test_emitir_dps_sends_gzip_base64_payload():
    with patch('services.nfse_sefin_nacional._request_json', return_value=(201, {
        'tipoAmbiente': 2, 'chaveAcesso': '1' * 50,
    })) as request:
        success, response = emitir_dps(XML_DPS, 'homologacao', {'cert_data': b'x', 'password': 'p'})

    assert success is True
    assert response['chaveAcesso'] == '1' * 50
    sent = request.call_args.kwargs['json']['dpsXmlGZipB64']
    assert isinstance(sent, str) and sent


def test_dps_nacional_rejects_unsigned_xml():
    try:
        validar_dps_assinada(XML_DPS.replace('<Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignedInfo /></Signature>', ''))
    except ValueError as exc:
        assert 'assinada' in str(exc)
    else:
        raise AssertionError('XML sem assinatura deveria ser rejeitado')


def test_certificate_material_accepts_system_certificate_field_names():
    raw, password = _certificate_material({
        'arquivo_certificado': b'pkcs12',
        'senha_certificado': 'segredo',
    })
    assert raw == b'pkcs12'
    assert password == 'segredo'


def test_dps_rejects_non_numeric_series():
    try:
        gerar_dps({
            'cnpj_prestador': '46840224000102', 'numero_dps': 1,
            'serie': 'TESTE', 'codigo_municipio': '3549805',
            'codigo_servico': '170101', 'discriminacao': 'teste',
            'valor_servico': '1.00',
        })
    except ValueError as exc:
        assert 'serie' in str(exc)
    else:
        raise AssertionError('Série não numérica deveria ser rejeitada')

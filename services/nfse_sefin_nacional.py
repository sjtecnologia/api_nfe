"""Adapter da API oficial da SEFIN Nacional NFS-e.

Baseado no manual de contribuintes do Portal NFS-e: JSON, DPS XML em
GZip/Base64, XMLDSIG e autenticação mútua com certificado ICP-Brasil.
"""
import base64
import gzip
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, Tuple

import requests
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12
from lxml import etree
from signxml import XMLSigner, methods


BASE_URLS = {
    'homologacao': 'https://sefin.producaorestrita.nfse.gov.br/SefinNacional',
    'producao': 'https://sefin.nfse.gov.br/SefinNacional',
}

NS = 'http://www.sped.fazenda.gov.br/nfse'


def _certificate_material(certificado: Dict[str, Any]):
    """Obtém o A1 tanto no formato do adaptador quanto no formato do sistema.

    ``get_active_certificate_for_client`` usa os nomes legados
    ``arquivo_certificado`` e ``senha_certificado``; integrações diretas usam
    ``cert_data`` e ``password``. Manter a normalização aqui evita que a rota
    dependa de detalhes internos do armazenamento de certificados.
    """
    if not certificado:
        return None, None
    raw = certificado.get('cert_data') or certificado.get('arquivo_certificado')
    password = certificado.get('password') or certificado.get('senha_certificado')
    if isinstance(password, bytes):
        password = password.decode()
    return raw, password


def gerar_dps(dados: Dict[str, Any]) -> str:
    """Monta a DPS mínima nacional a partir dos dados do formulário/API.

    A validação definitiva continua sendo feita pelo XSD e pela SEFIN; campos
    tributários específicos devem ser enviados quando aplicáveis.
    """
    required = ('cnpj_prestador', 'numero_dps', 'serie', 'codigo_municipio',
                'codigo_servico', 'discriminacao', 'valor_servico')
    missing = [key for key in required if dados.get(key) in (None, '')]
    if missing:
        raise ValueError('Campos obrigatórios ausentes: ' + ', '.join(missing))
    cnpj = ''.join(ch for ch in str(dados['cnpj_prestador']) if ch.isdigit())
    if len(cnpj) != 14:
        raise ValueError('cnpj_prestador deve conter 14 dígitos')
    serie_raw = str(dados['serie'])
    if not serie_raw.isdigit() or len(serie_raw) > 5:
        raise ValueError('serie deve conter até 5 dígitos')
    root = etree.Element('{%s}DPS' % NS, nsmap={None: NS})
    root.set('versao', '1.01')
    ident = etree.SubElement(root, '{%s}infDPS' % NS)
    # O IdDPS e o campo XML usam a série nacional fixa de 5 posições.
    serie = serie_raw.zfill(5)
    numero = str(dados['numero_dps']).zfill(15)
    tipo_inscricao = '2' if len(cnpj) == 14 else '1'
    ident.set('Id', 'DPS' + str(dados['codigo_municipio']).zfill(7) + tipo_inscricao + cnpj + serie + numero)
    def put(parent, name, value):
        etree.SubElement(parent, '{%s}%s' % (NS, name)).text = str(value)
    put(ident, 'tpAmb', 1 if dados.get('ambiente') == 'producao' else 2)
    put(ident, 'dhEmi', dados.get('data_emissao') or datetime.now().astimezone().isoformat(timespec='seconds'))
    put(ident, 'verAplic', dados.get('versao_aplicativo', 'EmiteMax-1.0'))
    put(ident, 'serie', serie); put(ident, 'nDPS', str(dados['numero_dps']))
    put(ident, 'dCompet', dados.get('competencia') or datetime.now().date().isoformat())
    put(ident, 'tpEmit', 1); put(ident, 'cLocEmi', dados['codigo_municipio'])
    prest = etree.SubElement(ident, '{%s}prest' % NS); put(prest, 'CNPJ', cnpj)
    if dados.get('razao_social'): put(prest, 'xNome', dados['razao_social'])
    reg = etree.SubElement(prest, '{%s}regTrib' % NS)
    optante = 3 if dados.get('optante_simples', True) else 1
    put(reg, 'opSimpNac', optante)
    if optante == 3: put(reg, 'regApTribSN', dados.get('regime_apuracao_sn', 1))
    put(reg, 'regEspTrib', dados.get('regime_especial_tributacao', 0))
    serv = etree.SubElement(ident, '{%s}serv' % NS)
    loc = etree.SubElement(serv, '{%s}locPrest' % NS); put(loc, 'cLocPrestacao', dados['codigo_municipio'])
    cs = etree.SubElement(serv, '{%s}cServ' % NS)
    put(cs, 'cTribNac', dados['codigo_servico']); put(cs, 'xDescServ', dados['discriminacao'])
    nbs = ''.join(ch for ch in str(dados.get('codigo_nbs', '')) if ch.isdigit())
    if len(nbs) == 9: put(cs, 'cNBS', nbs)
    valores = etree.SubElement(ident, '{%s}valores' % NS)
    prest_val = etree.SubElement(valores, '{%s}vServPrest' % NS)
    put(prest_val, 'vServ', format(float(dados['valor_servico']), '.2f'))
    trib = etree.SubElement(valores, '{%s}trib' % NS)
    trib_mun = etree.SubElement(trib, '{%s}tribMun' % NS)
    put(trib_mun, 'tribISSQN', 1)
    put(trib_mun, 'tpRetISSQN', 1)
    if dados.get('aliquota_iss') is not None:
        put(trib_mun, 'pAliq', format(float(dados['aliquota_iss']), '.2f'))
    tot = etree.SubElement(trib, '{%s}totTrib' % NS)
    put(tot, 'indTotTrib', 0)
    return etree.tostring(root, encoding='utf-8', xml_declaration=True).decode()


def assinar_dps(xml_dps: str, certificado: Dict[str, Any]) -> str:
    raw, password_value = _certificate_material(certificado)
    password = (password_value or '').encode()
    if not raw or not password: raise ValueError('Certificado A1 e senha são obrigatórios')
    key, cert, _ = pkcs12.load_key_and_certificates(raw, password)
    if not key or not cert: raise ValueError('Certificado A1 inválido')
    signer = XMLSigner(method=methods.enveloped, signature_algorithm='rsa-sha256', digest_algorithm='sha256',
                       c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
    # A SEFIN Nacional rejeita DPS quando a assinatura XMLDSIG é serializada
    # com prefixo (por exemplo, ``ds:Signature``). O leiaute nacional espera
    # a namespace XMLDSIG como namespace padrão no elemento Signature.
    signer.namespaces = {None: 'http://www.w3.org/2000/09/xmldsig#'}
    root = etree.fromstring(xml_dps.encode())
    info = root.find('.//{%s}infDPS' % NS)
    if info is None or not info.get('Id'): raise ValueError('infDPS com Id é obrigatório')
    signed = signer.sign(root, key=key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()), cert=cert.public_bytes(Encoding.PEM), reference_uri='#' + info.get('Id'))
    return etree.tostring(signed, encoding='utf-8', xml_declaration=True).decode()


def _cert_files(certificado: Dict[str, Any]):
    raw, password_value = _certificate_material(certificado)
    password = (password_value or '').encode()
    if not raw or not password:
        raise ValueError('Certificado A1 e senha são obrigatórios para a SEFIN Nacional')
    key, cert, chain = pkcs12.load_key_and_certificates(raw, password)
    if not key or not cert:
        raise ValueError('Certificado A1 inválido ou sem chave privada')
    cert_file = tempfile.NamedTemporaryFile(suffix='.pem', delete=False)
    key_file = tempfile.NamedTemporaryFile(suffix='.key', delete=False)
    cert_file.write(cert.public_bytes(Encoding.PEM))
    for item in chain or ():
        cert_file.write(item.public_bytes(Encoding.PEM))
    key_file.write(key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))
    cert_file.close(); key_file.close()
    return cert_file.name, key_file.name


def _request_json(ambiente, method, path, certificado, **kwargs):
    base = BASE_URLS.get(ambiente)
    if not base:
        raise ValueError('Ambiente inválido')
    cert_path = key_path = None
    try:
        cert_path, key_path = _cert_files(certificado)
        response = requests.request(method, base.rstrip('/') + '/' + path.lstrip('/'),
                                    cert=(cert_path, key_path), timeout=60, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = {'raw': response.text[:2000]}
        return response.status_code, body
    finally:
        for path_value in (cert_path, key_path):
            if path_value and os.path.exists(path_value):
                os.unlink(path_value)


def validar_dps_assinada(xml_dps: str) -> None:
    root = etree.fromstring(xml_dps.encode('utf-8'))
    if 'DPS' not in etree.QName(root).localname:
        raise ValueError('XML não aparenta ser uma DPS nacional')
    if root.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature') is None:
        raise ValueError('DPS deve estar assinada com XMLDSIG')


def emitir_dps(xml_dps: str, ambiente: str, certificado: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    validar_dps_assinada(xml_dps)
    compactado = base64.b64encode(gzip.compress(xml_dps.encode('utf-8'))).decode('ascii')
    status, body = _request_json(ambiente, 'POST', '/nfse', certificado,
                                 json={'dpsXmlGZipB64': compactado},
                                 headers={'Content-Type': 'application/json'})
    return 200 <= status < 300, body


def consultar_nfse(chave_acesso: str, ambiente: str, certificado: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    if not chave_acesso or len(chave_acesso) != 50 or not chave_acesso.isdigit():
        raise ValueError('Chave de acesso deve conter 50 dígitos')
    status, body = _request_json(ambiente, 'GET', f'/nfse/{chave_acesso}', certificado,
                                 headers={'Accept': 'application/json'})
    return 200 <= status < 300, body


def registrar_evento(chave_acesso: str, evento_xml: str, ambiente: str, certificado: Dict[str, Any]):
    validar_dps_assinada(evento_xml)
    compactado = base64.b64encode(gzip.compress(evento_xml.encode('utf-8'))).decode('ascii')
    status, body = _request_json(ambiente, 'POST', f'/nfse/{chave_acesso}/eventos', certificado,
                                 json={'pedidoRegistroEventoXmlGZipB64': compactado},
                                 headers={'Content-Type': 'application/json'})
    return 200 <= status < 300, body

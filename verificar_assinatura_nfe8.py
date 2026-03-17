from lxml import etree
import hashlib
import base64
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Carregar XML
xml_nfe8 = open('nfe_8_com_infresptec.xml', 'rb').read()
tree = etree.fromstring(xml_nfe8)

# Extrair SignedInfo
signed_info = tree.find('.//{http://www.w3.org/2000/09/xmldsig#}SignedInfo')

# Canonicalizar SignedInfo
signed_info_c14n = etree.tostring(signed_info, method='c14n', exclusive=False, with_comments=False)

print(f'Tamanho SignedInfo canonicalizado: {len(signed_info_c14n)} bytes')

# Extrair assinatura
signature_value = tree.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue').text
signature_bytes = base64.b64decode(signature_value)

# Extrair certificado
cert_text = tree.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate').text
cert_der = base64.b64decode(cert_text)
cert = x509.load_der_x509_certificate(cert_der, default_backend())
public_key = cert.public_key()

# Verificar assinatura
try:
    public_key.verify(signature_bytes, signed_info_c14n, padding.PKCS1v15(), hashes.SHA1())
    print('\n✅ ASSINATURA VÁLIDA LOCALMENTE!')
    print('\n🔍 MAS O SEFAZ REJEITA COM ERRO 297...')
    print('\nPossíveis causas:')
    print('1. Certificado não é o correto para este emissor')
    print('2. Certificado expirou ou foi revogado')
    print('3. Cadeia de certificação não está completa')
    print('4. SEFAZ está validando algo a mais que não estamos checando')
except Exception as e:
    print(f'\n❌ ASSINATURA INVÁLIDA: {e}')

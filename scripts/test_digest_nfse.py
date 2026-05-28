#!/usr/bin/env python3
"""
Script para testar o cálculo de digest do LoteRps e validar a assinatura
"""
from lxml import etree
import hashlib
import base64

# Ler o XML assinado
with open('/tmp/last_signed_nfse.xml', 'r', encoding='utf-8') as f:
    xml_content = f.read()

root = etree.fromstring(xml_content.encode('utf-8'))

# Namespaces
ns = {
    'p': 'http://www.giss.com.br/nfse',
    'p1': 'http://www.giss.com.br/tipos',
    'ds': 'http://www.w3.org/2000/09/xmldsig#'
}

# Extrair LoteRps
lote_rps = root.find('.//p:LoteRps', ns)
if lote_rps is None:
    print("❌ LoteRps não encontrado")
    exit(1)

lote_id = lote_rps.get('Id')
print(f"✅ LoteRps encontrado com Id='{lote_id}'")

# Canonicalizar o LoteRps
lote_rps_c14n = etree.tostring(
    lote_rps, 
    method='c14n', 
    exclusive=False, 
    with_comments=False
)

# Salvar canonicalizado
with open('/tmp/lote_rps_c14n_test.xml', 'wb') as f:
    f.write(lote_rps_c14n)

print(f"✅ LoteRps canonicalizado: {len(lote_rps_c14n)} bytes")

# Calcular digest SHA1
digest_calculado = hashlib.sha1(lote_rps_c14n).digest()
digest_base64 = base64.b64encode(digest_calculado).decode('utf-8')

print(f"✅ Digest calculado: {digest_base64}")

# Extrair digest da assinatura
signature = root.find('.//ds:Signature', ns)
if signature is None:
    print("❌ Assinatura não encontrada")
    exit(1)

digest_na_assinatura = signature.find('.//ds:DigestValue', ns)
if digest_na_assinatura is None:
    print("❌ DigestValue não encontrado na assinatura")
    exit(1)

digest_assinatura_text = digest_na_assinatura.text.strip()
print(f"✅ Digest na assinatura: {digest_assinatura_text}")

# Comparar
if digest_base64 == digest_assinatura_text:
    print("✅ ✅ ✅ DIGESTS CONFEREM!")
else:
    print("❌ ❌ ❌ DIGESTS NÃO CONFEREM!")
    print(f"   Esperado: {digest_base64}")
    print(f"   Na assinatura: {digest_assinatura_text}")
    
# Verificar Reference URI
reference = signature.find('.//ds:Reference', ns)
if reference is not None:
    uri = reference.get('URI')
    print(f"✅ Reference URI: {uri}")
    if uri != f"#{lote_id}":
        print(f"⚠️  ATENÇÃO: URI {uri} diferente de #{lote_id}")
        
# Verificar transforms
transforms = signature.findall('.//ds:Transform', ns)
print(f"✅ Transforms encontrados: {len(transforms)}")
for t in transforms:
    alg = t.get('Algorithm')
    print(f"   - {alg}")
    if 'enveloped' in alg.lower():
        print("   ⚠️  ATENÇÃO: Transform enveloped-signature não deveria estar aqui!")

print("\n" + "="*60)
print("Resumo:")
print("="*60)
print(f"LoteRps Id: {lote_id}")
print(f"LoteRps bytes (c14n): {len(lote_rps_c14n)}")
print(f"Digest calculado: {digest_base64}")
print(f"Digest assinatura: {digest_assinatura_text}")
print(f"Match: {'SIM ✅' if digest_base64 == digest_assinatura_text else 'NÃO ❌'}")

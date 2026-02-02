#!/usr/bin/env python3
"""
Script de diagnóstico para E172 - Erro na assinatura
Execute no servidor: python3 diagnostico_assinatura.py
"""
import sys
import os
from lxml import etree
import hashlib
import base64

print("="*70)
print("DIAGNÓSTICO E172 - Erro na Assinatura")
print("="*70)

# Verificar arquivos
arquivos = {
    '/tmp/last_generated_nfse.xml': 'XML gerado (antes da assinatura)',
    '/tmp/last_signed_nfse.xml': 'XML assinado (após assinatura)',
    '/tmp/last_nfse_response.xml': 'Resposta do GISS'
}

arquivos_existentes = []
for caminho, descricao in arquivos.items():
    if os.path.exists(caminho):
        tamanho = os.path.getsize(caminho)
        print(f"✅ {descricao}: {caminho} ({tamanho} bytes)")
        arquivos_existentes.append(caminho)
    else:
        print(f"❌ {descricao}: {caminho} NÃO ENCONTRADO")

if '/tmp/last_signed_nfse.xml' not in arquivos_existentes:
    print("\n❌ Arquivo assinado não encontrado. Execute uma emissão primeiro.")
    sys.exit(1)

print("\n" + "="*70)
print("ANÁLISE DO XML ASSINADO")
print("="*70)

# Ler XML assinado
with open('/tmp/last_signed_nfse.xml', 'r', encoding='utf-8') as f:
    xml_content = f.read()

try:
    root = etree.fromstring(xml_content.encode('utf-8'))
except Exception as e:
    print(f"❌ Erro ao parsear XML: {e}")
    sys.exit(1)

# Namespaces
ns = {
    'p': 'http://www.giss.com.br/enviar-lote-rps-envio-v2_04.xsd',
    'p1': 'http://www.giss.com.br/tipos-v2_04.xsd',
    'ds': 'http://www.w3.org/2000/09/xmldsig#'
}

# 1. Verificar estrutura
print("\n1️⃣ ESTRUTURA DO XML")
print("-" * 70)

lote_rps = root.find('.//p:LoteRps', ns)
if lote_rps is None:
    print("❌ LoteRps não encontrado")
    sys.exit(1)

lote_id = lote_rps.get('Id')
print(f"✅ LoteRps encontrado com Id='{lote_id}'")

signature = root.find('.//ds:Signature', ns)
if signature is None:
    print("❌ Signature não encontrada")
    sys.exit(1)
print(f"✅ Signature encontrada")

# Verificar posição da assinatura
lote_index = list(root).index(lote_rps)
sig_index = list(root).index(signature)
print(f"✅ LoteRps está na posição {lote_index}, Signature na posição {sig_index}")
if sig_index != lote_index + 1:
    print(f"⚠️  ATENÇÃO: Signature deveria estar logo após LoteRps")

# 2. Verificar Reference URI
print("\n2️⃣ REFERENCE URI")
print("-" * 70)

reference = signature.find('.//ds:Reference', ns)
if reference is None:
    print("❌ Reference não encontrado")
    sys.exit(1)

uri = reference.get('URI')
print(f"Reference URI: {uri}")
print(f"LoteRps Id: #{lote_id}")

if uri == f"#{lote_id}":
    print(f"✅ URI correto: {uri} = #{lote_id}")
else:
    print(f"❌ URI incorreto: {uri} ≠ #{lote_id}")

# 3. Verificar Transforms
print("\n3️⃣ TRANSFORMS")
print("-" * 70)

transforms = reference.findall('.//ds:Transform', ns)
print(f"Total de transforms: {len(transforms)}")

transforms_esperados = 1  # Apenas canonicalization
if len(transforms) != transforms_esperados:
    print(f"⚠️  ATENÇÃO: Esperado {transforms_esperados} transform, encontrado {len(transforms)}")

for i, t in enumerate(transforms, 1):
    alg = t.get('Algorithm')
    print(f"  Transform {i}: {alg}")
    
    if 'enveloped' in alg.lower():
        print("    ❌ PROBLEMA: enveloped-signature não deve estar aqui!")
    elif 'c14n' in alg.lower() or 'xml-c14n' in alg.lower():
        print("    ✅ Canonicalization correto")
    else:
        print("    ⚠️  Transform inesperado")

# 4. Verificar DigestMethod
print("\n4️⃣ DIGEST METHOD")
print("-" * 70)

digest_method = reference.find('.//ds:DigestMethod', ns)
if digest_method is None:
    print("❌ DigestMethod não encontrado")
else:
    alg = digest_method.get('Algorithm')
    print(f"DigestMethod: {alg}")
    if 'sha1' in alg.lower():
        print("✅ SHA1 correto")
    else:
        print(f"⚠️  ATENÇÃO: Esperado SHA1, encontrado {alg}")

# 5. RECALCULAR DIGEST
print("\n5️⃣ RECALCULAR DIGEST")
print("-" * 70)

# Canonicalizar LoteRps
lote_rps_c14n = etree.tostring(
    lote_rps, 
    method='c14n', 
    exclusive=False, 
    with_comments=False
)

# Salvar para inspeção
with open('/tmp/lote_rps_canonicalizado.xml', 'wb') as f:
    f.write(lote_rps_c14n)
print(f"✅ LoteRps canonicalizado salvo em: /tmp/lote_rps_canonicalizado.xml")
print(f"   Tamanho: {len(lote_rps_c14n)} bytes")

# Calcular digest
digest_calculado = hashlib.sha1(lote_rps_c14n).digest()
digest_base64 = base64.b64encode(digest_calculado).decode('utf-8')

# Obter digest da assinatura
digest_na_assinatura = reference.find('.//ds:DigestValue', ns)
if digest_na_assinatura is None:
    print("❌ DigestValue não encontrado")
    sys.exit(1)

digest_assinatura_text = digest_na_assinatura.text.strip()

print(f"\nDigest calculado:    {digest_base64}")
print(f"Digest na assinatura: {digest_assinatura_text}")

if digest_base64 == digest_assinatura_text:
    print("✅✅✅ DIGESTS CONFEREM! O problema não é o digest.")
else:
    print("❌❌❌ DIGESTS DIFERENTES! Este é o problema!")
    print("\nIsso significa que o signxml está canonicalizando diferente do esperado.")
    print("Verifique o arquivo /tmp/lote_rps_canonicalizado.xml para detalhes.")

# 6. Verificar SignatureMethod
print("\n6️⃣ SIGNATURE METHOD")
print("-" * 70)

signed_info = signature.find('.//ds:SignedInfo', ns)
if signed_info is None:
    print("❌ SignedInfo não encontrado")
else:
    sig_method = signed_info.find('.//ds:SignatureMethod', ns)
    if sig_method is None:
        print("❌ SignatureMethod não encontrado")
    else:
        alg = sig_method.get('Algorithm')
        print(f"SignatureMethod: {alg}")
        if 'rsa-sha1' in alg.lower():
            print("✅ RSA-SHA1 correto")
        else:
            print(f"⚠️  ATENÇÃO: Esperado RSA-SHA1, encontrado {alg}")

# 7. Verificar certificado
print("\n7️⃣ CERTIFICADO")
print("-" * 70)

key_info = signature.find('.//ds:KeyInfo', ns)
if key_info is None:
    print("❌ KeyInfo não encontrado")
else:
    x509_cert = key_info.find('.//ds:X509Certificate', ns)
    if x509_cert is None:
        print("❌ X509Certificate não encontrado")
    else:
        cert_text = x509_cert.text.strip()
        print(f"✅ Certificado presente: {len(cert_text)} caracteres")
        
        # Tentar decodificar
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            cert_der = base64.b64decode(cert_text)
            cert = x509.load_der_x509_certificate(cert_der, default_backend())
            
            print(f"   Subject: {cert.subject.rfc4514_string()}")
            print(f"   Issuer: {cert.issuer.rfc4514_string()}")
            print(f"   Válido de: {cert.not_valid_before}")
            print(f"   Válido até: {cert.not_valid_after}")
            
            from datetime import datetime
            agora = datetime.now()
            if cert.not_valid_before <= agora <= cert.not_valid_after:
                print(f"   ✅ Certificado válido (dentro da validade)")
            else:
                print(f"   ❌ Certificado fora da validade!")
                
        except Exception as e:
            print(f"   ⚠️  Não foi possível analisar certificado: {e}")

# 8. Verificar resposta do GISS
print("\n8️⃣ RESPOSTA DO GISS")
print("-" * 70)

if os.path.exists('/tmp/last_nfse_response.xml'):
    with open('/tmp/last_nfse_response.xml', 'r', encoding='utf-8') as f:
        response = f.read()
    
    print(f"Resposta: {len(response)} caracteres")
    
    # Procurar mensagens de erro
    if 'E172' in response:
        print("❌ Erro E172 confirmado na resposta")
    
    if 'mensagem' in response.lower() or 'erro' in response.lower():
        print("\nTrecho da resposta:")
        print("-" * 70)
        # Mostrar primeiros 500 caracteres
        print(response[:500])

# RESUMO FINAL
print("\n" + "="*70)
print("RESUMO DO DIAGNÓSTICO")
print("="*70)

problemas = []
if len(transforms) != 1:
    problemas.append("Número incorreto de transforms")
if any('enveloped' in t.get('Algorithm', '').lower() for t in transforms):
    problemas.append("Transform enveloped-signature presente (não deveria)")
if digest_base64 != digest_assinatura_text:
    problemas.append("DigestValue incorreto (CRÍTICO)")
if uri != f"#{lote_id}":
    problemas.append("Reference URI incorreto")

if not problemas:
    print("✅ Estrutura da assinatura parece correta")
    print("\nPossíveis causas do E172:")
    print("  1. Certificado não confiável no ambiente de homologação")
    print("  2. Certificado não autorizado para emissão de NFS-e")
    print("  3. CNPJ do certificado diferente do CNPJ do prestador")
    print("  4. Problema na transmissão SOAP (encoding)")
else:
    print("❌ PROBLEMAS ENCONTRADOS:")
    for i, p in enumerate(problemas, 1):
        print(f"  {i}. {p}")

print("\n" + "="*70)
print("Para mais detalhes, verifique:")
print("  - /tmp/lote_rps_canonicalizado.xml (LoteRps canonicalizado)")
print("  - /tmp/last_signed_nfse.xml (XML completo assinado)")
print("  - /tmp/last_nfse_response.xml (Resposta do GISS)")
print("="*70)

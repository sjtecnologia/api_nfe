#!/usr/bin/env python3
from lxml import etree

# Testar com namespace herdado (como SEFAZ verá)
signature_xml = '''<Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignedInfo><CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315" /><SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" /><Reference URI="#NFe35260199999999000191550010000000031184696574"><Transforms><Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature" /><Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315" /></Transforms><DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" /><DigestValue>2H15/O52GO1YVXZ9QK8e1ylqE8g=</DigestValue></Reference></SignedInfo></Signature>'''

sig_elem = etree.fromstring(signature_xml.encode('utf-8'))
signed_info = sig_elem[0]  # Pega SignedInfo filho

c14n_from_tree = etree.tostring(signed_info, method='c14n', exclusive=False, with_comments=False)

print("Tamanho com namespace herdado:", len(c14n_from_tree))
print("\nPrimeiros 400 chars:")
print(c14n_from_tree[:400].decode('utf-8'))
print("\nÚltimos 100 chars:")
print(c14n_from_tree[-100:].decode('utf-8'))

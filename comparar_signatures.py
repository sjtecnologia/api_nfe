from lxml import etree

# Carregar ambos XMLs
nfe8 = etree.parse('nfe_8_com_infresptec.xml')
nfe106 = etree.parse('/Users/renato/Downloads/35260143101347000133550010000001061300000413.xml')

# Comparar estrutura de Signature
sig8 = nfe8.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
sig106 = nfe106.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')

print('=== COMPARAÇÃO SIGNATURE ===')
print(f'NFe 8 Signature children: {[e.tag.split("}")[1] for e in sig8]}')
print(f'NFe 106 Signature children: {[e.tag.split("}")[1] for e in sig106]}')

# Comparar SignedInfo
si8 = sig8.find('.//{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
si106 = sig106.find('.//{http://www.w3.org/2000/09/xmldsig#}SignedInfo')

si8_c14n = etree.tostring(si8, method='c14n', exclusive=False, with_comments=False)
si106_c14n = etree.tostring(si106, method='c14n', exclusive=False, with_comments=False)

print(f'\nNFe 8 SignedInfo: {len(si8_c14n)} bytes')
print(f'NFe 106 SignedInfo: {len(si106_c14n)} bytes')

# Comparar CanonicalizationMethod
canon8 = si8.find('.//{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod')
canon106 = si106.find('.//{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod')

print(f'\nNFe 8 CanonicalizationMethod: {canon8.get("Algorithm")}')
print(f'NFe 106 CanonicalizationMethod: {canon106.get("Algorithm")}')

# Comparar posição da Signature
nfe_elem8 = nfe8.getroot()
nfe_elem106 = nfe106.getroot()

children8 = [e.tag.split("}")[1] if "}" in e.tag else e.tag for e in nfe_elem8]
children106 = [e.tag.split("}")[1] if "}" in e.tag else e.tag for e in nfe_elem106]

print(f'\nNFe 8 children: {children8}')
print(f'NFe 106 children: {children106}')

# Verificar se Signature está dentro ou fora de infNFe
inf_nfe8 = nfe8.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
inf_nfe106 = nfe106.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')

sig_within_inf8 = inf_nfe8.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature') is not None
sig_within_inf106 = inf_nfe106.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature') is not None

print(f'\nNFe 8 - Signature dentro de infNFe: {sig_within_inf8}')
print(f'NFe 106 - Signature dentro de infNFe: {sig_within_inf106}')

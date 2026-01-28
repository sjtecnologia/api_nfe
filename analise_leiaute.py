#!/usr/bin/env python3
"""
Análise de conformidade do XML NFe com o leiaute oficial
"""
import subprocess
from lxml import etree

# Buscar XML do servidor
result = subprocess.run(
    ['ssh', '-i', '/Users/renato/Downloads/nfe-new-api-key.pem', 
     'ubuntu@3.87.73.106', 'cat /tmp/last_signed_nfe.xml'],
    capture_output=True,
    text=True
)

xml_content = result.stdout

# Parse XML
tree = etree.fromstring(xml_content.encode('utf-8'))
ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe', 'ds': 'http://www.w3.org/2000/09/xmldsig#'}

print("=== ANÁLISE DE CONFORMIDADE NFe ===\n")

# Verificar estrutura principal
nfe = tree
inf_nfe = tree.find('.//nfe:infNFe', ns)
signature = tree.find('.//ds:Signature', ns)

print(f"✓ NFe: {nfe.tag}")
print(f"✓ infNFe ID: {inf_nfe.get('Id')}")
print(f"✓ Signature: {'Presente' if signature is not None else 'AUSENTE'}")

# Grupos obrigatórios do leiaute
grupos_obrigatorios = {
    'ide': 'Identificação',
    'emit': 'Emitente',
    'dest': 'Destinatário',
    'det': 'Detalhamento (itens)',
    'total': 'Totais',
    'transp': 'Transporte',
    'pag': 'Pagamento',
    'infAdic': 'Informações Adicionais',
    'infRespTec': 'Responsável Técnico'
}

print("\n=== GRUPOS PRESENTES ===")
for grupo, descricao in grupos_obrigatorios.items():
    elemento = inf_nfe.find(f'.//nfe:{grupo}', ns)
    status = "✓" if elemento is not None else "✗ FALTANDO"
    print(f"{status} {grupo}: {descricao}")

# Verificar campos específicos em ide
print("\n=== CAMPOS IDE ===")
ide = inf_nfe.find('.//nfe:ide', ns)
if ide is not None:
    campos_ide_obrigatorios = ['cUF', 'cNF', 'natOp', 'mod', 'serie', 'nNF', 
                                'dhEmi', 'tpNF', 'idDest', 'cMunFG', 'tpImp', 
                                'tpEmis', 'cDV', 'tpAmb', 'finNFe', 'indFinal', 
                                'indPres', 'indIntermed', 'procEmi', 'verProc']
    
    for campo in campos_ide_obrigatorios:
        elem = ide.find(f'nfe:{campo}', ns)
        valor = elem.text if elem is not None else None
        status = "✓" if elem is not None else "✗"
        print(f"{status} {campo}: {valor}")

# Verificar campos em emit
print("\n=== CAMPOS EMIT ===")
emit = inf_nfe.find('.//nfe:emit', ns)
if emit is not None:
    campos_emit = ['CNPJ', 'xNome', 'xFant', 'IE', 'CRT']
    for campo in campos_emit:
        elem = emit.find(f'nfe:{campo}', ns) or emit.find(f'.//nfe:{campo}', ns)
        valor = elem.text if elem is not None else None
        status = "✓" if elem is not None else "✗"
        print(f"{status} {campo}: {valor}")

# Verificar Signature
print("\n=== ASSINATURA ===")
if signature is not None:
    signed_info = signature.find('.//ds:SignedInfo', ns)
    signature_value = signature.find('.//ds:SignatureValue', ns)
    key_info = signature.find('.//ds:KeyInfo', ns)
    x509_cert = signature.find('.//ds:X509Certificate', ns)
    
    print(f"✓ SignedInfo: {'Presente' if signed_info is not None else 'AUSENTE'}")
    print(f"✓ SignatureValue: {'Presente' if signature_value is not None else 'AUSENTE'}")
    print(f"✓ KeyInfo: {'Presente' if key_info is not None else 'AUSENTE'}")
    print(f"✓ X509Certificate: {'Presente' if x509_cert is not None else 'AUSENTE'}")
    
    # Verificar Reference URI
    if signed_info is not None:
        reference = signed_info.find('.//ds:Reference', ns)
        if reference is not None:
            uri = reference.get('URI')
            print(f"  Reference URI: {uri}")
            
            # Verificar se URI bate com Id do infNFe
            inf_nfe_id = inf_nfe.get('Id')
            expected_uri = f"#{inf_nfe_id}"
            if uri == expected_uri:
                print(f"  ✓ URI correto")
            else:
                print(f"  ✗ URI incorreto! Esperado: {expected_uri}, Atual: {uri}")

# Verificar infAdic (pode ser opcional mas é importante)
print("\n=== INFORMAÇÕES ADICIONAIS ===")
inf_adic = inf_nfe.find('.//nfe:infAdic', ns)
if inf_adic is not None:
    inf_cpl = inf_adic.find('nfe:infCpl', ns)
    print(f"✓ infAdic presente")
    print(f"  infCpl: {inf_cpl.text if inf_cpl is not None else 'AUSENTE'}")
else:
    print("✗ infAdic AUSENTE (recomendado adicionar)")

# Verificar infRespTec
print("\n=== RESPONSÁVEL TÉCNICO ===")
inf_resp_tec = inf_nfe.find('.//nfe:infRespTec', ns)
if inf_resp_tec is not None:
    cnpj = inf_resp_tec.find('nfe:CNPJ', ns)
    x_contato = inf_resp_tec.find('nfe:xContato', ns)
    email = inf_resp_tec.find('nfe:email', ns)
    fone = inf_resp_tec.find('nfe:fone', ns)
    
    print(f"✓ infRespTec presente")
    print(f"  CNPJ: {cnpj.text if cnpj is not None else 'AUSENTE'}")
    print(f"  xContato: {x_contato.text if x_contato is not None else 'AUSENTE'}")
    print(f"  email: {email.text if email is not None else 'AUSENTE'}")
    print(f"  fone: {fone.text if fone is not None else 'AUSENTE'}")
else:
    print("✗ infRespTec AUSENTE")

print("\n=== RESUMO ===")
print(f"Total elementos em infNFe: {len(list(inf_nfe.iter()))}")
print(f"Tamanho XML: {len(xml_content)} bytes")

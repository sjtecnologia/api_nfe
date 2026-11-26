#!/usr/bin/env python3
"""
Verificar digest da NFe 107 com infAdic
"""
import hashlib
from lxml import etree

xml_nfe107 = '''<?xml version="1.0" encoding="UTF-8"?><NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe versao="4.00" Id="NFe35260143101347000133550010000001061696467348"><ide><cUF>35</cUF><cNF>69646734</cNF><natOp>VENDA</natOp><mod>55</mod><serie>1</serie><nNF>106</nNF><dhEmi>2026-01-28T09:33:00-03:00</dhEmi><tpNF>1</tpNF><idDest>1</idDest><cMunFG>3549805</cMunFG><tpImp>1</tpImp><tpEmis>1</tpEmis><cDV>8</cDV><tpAmb>2</tpAmb><finNFe>1</finNFe><indFinal>1</indFinal><indPres>1</indPres><indIntermed>0</indIntermed><procEmi>0</procEmi><verProc>EmiteMax_1.0</verProc></ide><emit><CNPJ>43101347000133</CNPJ><xNome>POP DRI COMERCIO DE PRODUTOS ALIMENTICIOS LTDA</xNome><xFant>POP DRI PIPOCA GOURMET</xFant><enderEmit><xLgr>Rua Veniz Thome Chaddad</xLgr><nro>40</nro><xBairro>Jardim Tarraf</xBairro><cMun>3549805</cMun><xMun>Sao Jose do Rio Preto</xMun><UF>SP</UF><CEP>15091480</CEP><cPais>1058</cPais><xPais>BRASIL</xPais></enderEmit><IE>ISENTO</IE><CRT>1</CRT></emit><dest><CNPJ>11562880000106</CNPJ><xNome>ASSOCIACAO PARQUE RESIDENCIAL DAMHA V</xNome><enderDest><xLgr>Avenida Miguel Damha</xLgr><nro>1901</nro><xBairro>Parque Residencial Damha IV</xBairro><cMun>3549805</cMun><xMun>Sao Jose do Rio Preto</xMun><UF>SP</UF><CEP>15061850</CEP><cPais>1058</cPais><xPais>BRASIL</xPais></enderDest><indIEDest>9</indIEDest></dest><det nItem="1"><prod><cProd>1</cProd><cEAN>SEM GTIN</cEAN><xProd>PRODUTO</xProd><NCM>21050010</NCM><CFOP>5101</CFOP><uCom>UN</uCom><qCom>100.0000</qCom><vUnCom>5.5000</vUnCom><vProd>550.00</vProd><cEANTrib>SEM GTIN</cEANTrib><uTrib>UN</uTrib><qTrib>100.0000</qTrib><vUnTrib>5.5000</vUnTrib><indTot>1</indTot></prod><imposto><vTotTrib>0.00</vTotTrib><ICMS><ICMSSN102><orig>0</orig><CSOSN>102</CSOSN></ICMSSN102></ICMS><PIS><PISNT><CST>07</CST></PISNT></PIS><COFINS><COFINSNT><CST>07</CST></COFINSNT></COFINS></imposto></det><total><ICMSTot><vBC>0.00</vBC><vICMS>0.00</vICMS><vICMSDeson>0.00</vICMSDeson><vFCPUFDest>0.00</vFCPUFDest><vICMSUFDest>0.00</vICMSUFDest><vICMSUFRemet>0.00</vICMSUFRemet><vFCP>0.00</vFCP><vBCST>0.00</vBCST><vST>0.00</vST><vFCPST>0.00</vFCPST><vFCPSTRet>0.00</vFCPSTRet><vProd>550.00</vProd><vFrete>0.00</vFrete><vSeg>0.00</vSeg><vDesc>0.00</vDesc><vII>0.00</vII><vIPI>0.00</vIPI><vIPIDevol>0.00</vIPIDevol><vPIS>0.00</vPIS><vCOFINS>0.00</vCOFINS><vOutro>0.00</vOutro><vNF>550.00</vNF><vTotTrib>0.00</vTotTrib></ICMSTot></total><transp><modFrete>9</modFrete></transp><pag><detPag><indPag>0</indPag><tPag>01</tPag><vPag>550.00</vPag></detPag></pag><infAdic><infCpl>pix - 43101347000133</infCpl></infAdic><infRespTec><CNPJ>46840224000102</CNPJ><xContato>Carlos Renato</xContato><email>contato@emitemax.com.br</email><fone>1732118981</fone></infRespTec></infNFe><Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignedInfo><CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/><SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/><Reference URI="#NFe35260143101347000133550010000001061696467348"><Transforms><Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/><Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/></Transforms><DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/><DigestValue>XP+aGxCh3aRZ2sIORdidF3JYJxc=</DigestValue></Reference></SignedInfo><SignatureValue>p/svbFEb5mqE5aj4X1nTMFA+HL5+4C5TE/JwbjQUmvhCW6EZYTeaP2tO6y+rWLFn5Rxs8vaik4dRxsU1/FkYB0Bt8mqMNtKYwJ0Qa48ZkQ/zxJSzCcFulmP18/LuqwELq3ZHZGR6b9MeR129BKHjoGisI3WRVh0cLgrkIj28mHsyibBcUDItUoD/O7no7gMo9ay+wU83yMWfcokFmeEBB1Z6OekUkVojA/bRjgO1oRfEZQfDHRbkP6buETjOMc73gFqYQ7YqSJW5weu9mk1As6PhsBcJXqgm3+N4zB6/n2GA2Hi4MQhqKgYOkAQ3/KjPg9v4Jj/QNztmh2ljtW1gnw==</SignatureValue><KeyInfo><X509Data><X509Certificate>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</X509Certificate></X509Data></KeyInfo></Signature></NFe>'''

# Parse XML
tree = etree.fromstring(xml_nfe107.encode('utf-8'))
ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

# Localizar infNFe
inf_nfe = tree.find('.//nfe:infNFe', ns)

print("=== VERIFICAÇÃO DO DIGEST NFe 107 ===\n")

# Canonicalizar infNFe (simula enveloped-signature transform)
inf_nfe_c14n = etree.tostring(inf_nfe, method='c14n', exclusive=False, with_comments=False)

print(f"✓ Tamanho infNFe canonicalizado: {len(inf_nfe_c14n)} bytes")

# Calcular digest SHA1
digest_calculado = hashlib.sha1(inf_nfe_c14n).digest()
import base64
digest_base64 = base64.b64encode(digest_calculado).decode('utf-8')

print(f"✓ Digest calculado (base64): {digest_base64}")
print(f"✓ Digest no XML (SEFAZ):     XP+aGxCh3aRZ2sIORdidF3JYJxc=")

if digest_base64 == "XP+aGxCh3aRZ2sIORdidF3JYJxc=":
    print("\n✅ DIGEST CORRETO! Assinatura válida.")
else:
    print("\n❌ DIGEST INCORRETO! Problema na canonicalização.")
    
# Verificar se infAdic está presente
inf_adic = inf_nfe.find('.//nfe:infAdic', ns)
if inf_adic is not None:
    inf_cpl = inf_adic.find('.//nfe:infCpl', ns)
    print(f"\n✓ infAdic presente: {inf_cpl.text if inf_cpl is not None else 'SEM infCpl'}")
else:
    print("\n❌ infAdic AUSENTE!")

# Verificar ordem dos elementos
elementos = [elem.tag.split('}')[-1] for elem in inf_nfe]
print(f"\n✓ Ordem dos elementos no infNFe:")
for i, elem in enumerate(elementos[-5:], start=len(elementos)-4):
    print(f"  {i}. {elem}")

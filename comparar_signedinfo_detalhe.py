from lxml import etree

# Carregar XMLs
nfe8 = etree.parse('nfe_8_com_infresptec.xml')
nfe106_tree = etree.parse('/Users/renato/Downloads/35260143101347000133550010000001061300000413.xml')

# Extrair apenas o NFe interno do nfeProc
ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
nfe106_internal = nfe106_tree.find('.//nfe:NFe', ns)

# Salvar NFe 106 interno separadamente
if nfe106_internal is not None:
    with open('nfe_106_internal.xml', 'wb') as f:
        f.write(etree.tostring(nfe106_internal, encoding='utf-8', xml_declaration=True))
    print('✅ NFe 106 interno extraído')
    
    # Comparar SignedInfo detalhadamente
    si8 = nfe8.find('.//{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
    si106 = nfe106_internal.find('.//{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
    
    si8_c14n = etree.tostring(si8, method='c14n', exclusive=False, with_comments=False)
    si106_c14n = etree.tostring(si106, method='c14n', exclusive=False, with_comments=False)
    
    print(f'\nNFe 8 SignedInfo (primeiros 300 chars):')
    print(si8_c14n[:300])
    print(f'\nNFe 106 SignedInfo (primeiros 300 chars):')
    print(si106_c14n[:300])
    
    # Verificar diferenças
    if si8_c14n == si106_c14n:
        print('\n✅ SignedInfo IDÊNTICOS!')
    else:
        print('\n❌ SignedInfo DIFERENTES!')
        # Encontrar primeira diferença
        for i, (b8, b106) in enumerate(zip(si8_c14n, si106_c14n)):
            if b8 != b106:
                print(f'Primeira diferença no byte {i}:')
                print(f'  NFe 8:   {chr(b8)} (0x{b8:02x})')
                print(f'  NFe 106: {chr(b106)} (0x{b106:02x})')
                print(f'  Contexto: ...{si8_c14n[max(0,i-20):i+20]}...')
                break
else:
    print('❌ NFe interno não encontrado em nfeProc')

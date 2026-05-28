#!/usr/bin/env python3
"""Teste completo da geração de NFe com nfelib"""

from services.nfe_nfelib_service import generate_nfe_xml_nfelib

emitente = {
    'uf': 'SP',
    'cnpj': '12345678000199',
    'razao_social': 'Empresa Teste LTDA',
    'ie': '123456789',
    'regime_tributario': '1',
    'codigo_municipio': '3550308',
    'logradouro': 'Rua Teste',
    'numero': '123',
    'bairro': 'Centro',
    'municipio': 'Sao Paulo',
    'cep': '01234567'
}

destinatario = {
    'cpf_cnpj': '12345678909',
    'nome': 'Cliente Teste',
    'logradouro': 'Av Teste',
    'numero': '456',
    'bairro': 'Vila Nova',
    'municipio': 'Sao Paulo',
    'uf': 'SP',
    'cep': '01234567',
    'codigo_municipio': '3550308'
}

items = [{
    'codigo': 'PROD001',
    'descricao': 'Produto Teste',
    'ncm': '12345678',
    'cfop': '5102',
    'unidade': 'UN',
    'quantidade': '2.0000',
    'valor_unitario': '50.00',
    'valor_total': '100.00',
    'ean': 'SEM GTIN'
}]

form_data = {
    'serie': '1',
    'natOp': 'VENDA',
    'tpNF': '1',
    'tpAmb': 2,
    'finNFe': '1',
    'indPres': '1'
}

try:
    xml = generate_nfe_xml_nfelib(emitente, destinatario, items, form_data, 1, {})
    print('\n✅ XML COMPLETO gerado!')
    print(f'Tamanho: {len(xml)} caracteres')
    
    # Verificar elementos principais
    checks = [
        ('<NFe', 'NFe'),
        ('<ide>', 'IDE'),
        ('<emit>', 'EMIT'),
        ('<enderEmit>', 'enderEmit'),
        ('<dest>', 'DEST'),
        ('<enderDest>', 'enderDest'),
        ('<det ', 'DET (itens)'),
        ('<prod>', 'PROD'),
        ('<imposto>', 'IMPOSTO'),
        ('<total>', 'TOTAL'),
        ('<ICMSTot>', 'ICMSTot'),
        ('<transp>', 'TRANSP'),
        ('<pag>', 'PAG'),
        ('<vNF>100.00</vNF>', 'Valor NF correto')
    ]
    
    print('\n📋 Verificação dos elementos:')
    for tag, name in checks:
        if tag in xml:
            print(f'  ✅ {name}')
        else:
            print(f'  ❌ {name} FALTANDO!')
    
    # Salvar XML para inspeção
    with open('/tmp/nfe_test.xml', 'w') as f:
        f.write(xml)
    print('\n💾 XML salvo em /tmp/nfe_test.xml')
    
except Exception as e:
    print(f'❌ Erro: {e}')
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
"""Teste de integração da nova função generate_nfe_xml com nfelib"""

from services.nfe_service import generate_nfe_xml

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
    'numero_nfe': 123,
    'serie': '1',
    'natOp': 'VENDA',
    'tpNF': '1',
    'finNFe': '1',
    'indPres': '1'
}

print("=" * 60)
print("TESTE DE INTEGRAÇÃO - generate_nfe_xml() com nfelib")
print("=" * 60)

try:
    xml = generate_nfe_xml(form_data, emitente, destinatario, items, tp_amb=2)
    print('\n✅ Integração com nfe_service.py funcionando!')
    print(f'Tamanho do XML: {len(xml)} caracteres')
    
    if '<NFe' in xml and '<total>' in xml and '<ICMSTot>' in xml:
        print('✅ XML completo e válido!')
    else:
        print('❌ XML incompleto')
        
    print(f'\nPrimeiros 500 chars do XML:')
    print(xml[:500])
    
except Exception as e:
    print(f'\n❌ Erro na integração: {e}')
    import traceback
    traceback.print_exc()

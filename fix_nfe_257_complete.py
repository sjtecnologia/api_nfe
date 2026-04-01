#!/usr/bin/env python3
"""
Corrigir NFe 257 manualmente antes de emitir
"""
import psycopg2
import json

DB_HOST = "nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "sjtnfe"
DB_USER = "postgres"
DB_PASS = "gMGM!#)NW$nH1w(wrVIdcmn5"

print("="*80)
print("CORRIGINDO NFe 257 - DESCRIÇÕES E DESTINATÁRIO")
print("="*80)

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    cur = conn.cursor()
    
    # 1. Buscar descrições reais dos produtos
    print("\n1. Buscando descrições reais dos produtos...")
    
    # Primeiro, verificar colunas da tabela produtos
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'produtos'
        ORDER BY ordinal_position
    """)
    cols_produtos = [row[0] for row in cur.fetchall()]
    print(f"   Colunas produtos: {', '.join(cols_produtos)}")
    
    codigos = ['30', '32', '31', '23', '18', '17']
    descricoes = {}
    
    for codigo in codigos:
        cur.execute("""
            SELECT descricao 
            FROM produtos 
            WHERE (codigo_interno = %s OR produto_id::text = %s)
            AND cliente_id = 25
            LIMIT 1
        """, (codigo, codigo))
        
        row = cur.fetchone()
        if row:
            descricoes[codigo] = row[0]
            print(f"   ✅ Produto {codigo}: {row[0][:60]}...")
        else:
            print(f"   ❌ Produto {codigo}: NÃO ENCONTRADO")
    
    # 2. Buscar json_nfe atual
    print("\n2. Buscando json_nfe atual...")
    cur.execute("SELECT json_nfe FROM nfe_emitidas WHERE nfe_emitida_id = 257")
    row = cur.fetchone()
    
    if not row or not row[0]:
        print("   ❌ json_nfe vazio!")
        exit(1)
    
    json_nfe = row[0]
    print(f"   ✅ json_nfe carregado: {len(json_nfe.get('items', []))} itens")
    
    # 3. Atualizar descrições nos itens
    print("\n3. Atualizando descrições...")
    items = json_nfe.get('items', [])
    itens_atualizados = 0
    
    for item in items:
        codigo = item.get('codigo_produto', '')
        if codigo in descricoes:
            item['descricao'] = descricoes[codigo]
            itens_atualizados += 1
            print(f"   ✅ Item {codigo}: {descricoes[codigo][:50]}...")
    
    print(f"\n   Total atualizado: {itens_atualizados}/{len(items)} itens")
    
    # 4. Adicionar destinatário ao form_data
    print("\n4. Adicionando destinatário ao form_data...")
    if 'form_data' not in json_nfe:
        json_nfe['form_data'] = {}
    
    json_nfe['form_data']['destinatario'] = '14'
    print("   ✅ Destinatário ID 14 adicionado")
    
    # 5. Salvar no banco
    print("\n5. Salvando alterações no banco...")
    cur.execute("""
        UPDATE nfe_emitidas 
        SET json_nfe = %s
        WHERE nfe_emitida_id = 257
    """, (json.dumps(json_nfe),))
    
    conn.commit()
    print(f"   ✅ Atualizado: {cur.rowcount} registro(s)")
    
    # 6. Verificar resultado
    print("\n6. Verificando resultado...")
    cur.execute("""
        SELECT json_nfe
        FROM nfe_emitidas 
        WHERE nfe_emitida_id = 257
    """)
    
    row = cur.fetchone()
    if row and row[0]:
        json_check = row[0]
        dest_id = json_check.get('form_data', {}).get('destinatario', 'NÃO ENCONTRADO')
        items_check = json_check.get('items', [])
        
        print(f"   Destinatário ID: {dest_id}")
        print(f"   Número de itens: {len(items_check)}")
        
        if items_check:
            print(f"   Primeira descrição: {items_check[0].get('descricao', 'VAZIO')[:60]}...")
    
    print("\n✅ SUCESSO! NFe 257 corrigida.")
    print("\nAgora você pode:")
    print("1. Atualizar a página (F5)")
    print("2. Clicar em 'Emitir' na NFe 257")
    print("3. A emissão deve funcionar com dados corretos!")
    
    cur.close()
    conn.close()
    print("\n" + "="*80)
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
"""
Verificar estado atual da NFe 257
"""
import psycopg2
import json

DB_HOST = "nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "sjtnfe"
DB_USER = "postgres"
DB_PASS = "gMGM!#)NW$nH1w(wrVIdcmn5"

print("="*80)
print("VERIFICANDO NFe 257")
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
    
    # Buscar colunas disponíveis
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'nfe_emitidas'
        ORDER BY ordinal_position
    """)
    colunas = [row[0] for row in cur.fetchall()]
    print(f"\n📋 Colunas disponíveis: {', '.join(colunas)}")
    
    # Buscar NFe completa
    cur.execute("""
        SELECT 
            nfe_emitida_id,
            status,
            mensagem_sefaz,
            json_nfe
        FROM nfe_emitidas 
        WHERE nfe_emitida_id = 257
    """)
    
    row = cur.fetchone()
    
    if row:
        nfe_id = row[0]
        status = row[1]
        mensagem = row[2]
        json_nfe = row[3]
        
        print(f"\n📋 NFe ID: {nfe_id}")
        print(f"📊 Status: {status}")
        print(f"💬 Mensagem: {mensagem}")
        
        if json_nfe:
            print(f"\n📦 JSON NFe:")
            print(f"   - Destinatário ID: {json_nfe.get('form_data', {}).get('destinatario', 'NÃO ENCONTRADO')}")
            print(f"   - Ambiente: {json_nfe.get('ambiente', 'NÃO ENCONTRADO')}")
            print(f"   - Número itens: {len(json_nfe.get('items', []))}")
            print(f"   - Emitente no JSON: {'SIM' if json_nfe.get('emitente') else 'NÃO'}")
            
            # Verificar descrições
            items = json_nfe.get('items', [])
            if items:
                print(f"\n🔍 Primeiros 3 itens:")
                for i, item in enumerate(items[:3], 1):
                    desc = item.get('descricao', '')
                    codigo = item.get('codigo_produto', '')
                    print(f"   {i}. Código: {codigo} | Descrição: {desc[:50]}...")
        else:
            print("\n⚠️ json_nfe está vazio!")
    else:
        print("\n❌ NFe 257 não encontrada!")
    
    cur.close()
    conn.close()
    print("\n" + "="*80)
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

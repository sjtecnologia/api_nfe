#!/usr/bin/env python3
"""
Script para corrigir status da NFe 257 e adicionar destinatário no json_nfe
"""
import psycopg2
import json

# Credenciais RDS
DB_HOST = "nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "sjtnfe"
DB_USER = "postgres"
DB_PASS = "gMGM!#)NW$nH1w(wrVIdcmn5"

print("="*70)
print("Conectando ao banco de dados RDS...")
print("="*70)

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    cur = conn.cursor()
    
    # 1. Verificar status atual
    print("\n1. Status atual da NFe 257:")
    cur.execute("SELECT nfe_emitida_id, status, mensagem_sefaz FROM nfe_emitidas WHERE nfe_emitida_id = 257")
    row = cur.fetchone()
    if row:
        print(f"   ID: {row[0]}")
        print(f"   Status: {row[1]}")
        print(f"   Mensagem: {row[2]}")
    else:
        print("   NFe 257 não encontrada!")
        exit(1)
    
    # 2. Atualizar status para RASCUNHO
    print("\n2. Atualizando status para RASCUNHO...")
    cur.execute("""
        UPDATE nfe_emitidas 
        SET status = 'RASCUNHO',
            mensagem_sefaz = 'Rascunho - Aguardando edição'
        WHERE nfe_emitida_id = 257
    """)
    print(f"   ✅ Status atualizado: {cur.rowcount} registro(s)")
    
    # 3. Adicionar destinatario no json_nfe
    print("\n3. Atualizando json_nfe com destinatário ID 14...")
    cur.execute("""
        UPDATE nfe_emitidas 
        SET json_nfe = jsonb_set(
            COALESCE(json_nfe, '{}'::jsonb),
            '{form_data,destinatario}',
            '"14"',
            true
        )
        WHERE nfe_emitida_id = 257
    """)
    print(f"   ✅ json_nfe atualizado: {cur.rowcount} registro(s)")
    
    # 4. Verificar resultado
    print("\n4. Verificando mudanças:")
    cur.execute("""
        SELECT status, 
               mensagem_sefaz,
               json_nfe->'form_data'->>'destinatario' as destinatario_id
        FROM nfe_emitidas 
        WHERE nfe_emitida_id = 257
    """)
    row = cur.fetchone()
    if row:
        print(f"   Status: {row[0]}")
        print(f"   Mensagem: {row[1]}")
        print(f"   Destinatário ID: {row[2]}")
    
    # Commit
    conn.commit()
    print("\n✅ SUCESSO! Mudanças salvas no banco.")
    print("\nAgora você pode:")
    print("1. Editar a NFe 257 (status = RASCUNHO)")
    print("2. Os produtos terão descrições corretas do banco")
    print("3. Destinatário PE já está configurado")
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()
    print("\n" + "="*70)

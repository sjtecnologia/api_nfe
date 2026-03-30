#!/usr/bin/env python3
"""
Verificar dados completos do emitente cliente_id 25
"""
import psycopg2
import json

DB_HOST = "nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "sjtnfe"
DB_USER = "postgres"
DB_PASS = "gMGM!#)NW$nH1w(wrVIdcmn5"

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    cur = conn.cursor()
    
    print("="*80)
    print("DADOS DO EMITENTE - Cliente ID 25")
    print("="*80)
    
    cur.execute("""
        SELECT 
            c.cliente_id,
            c.razao_social,
            c.cnpj,
            c.regime_tributario_id,
            rt.nome as regime_nome
        FROM clientes c
        LEFT JOIN regimes_tributarios rt ON c.regime_tributario_id = rt.regime_tributario_id
        WHERE c.cliente_id = 25
    """)
    
    row = cur.fetchone()
    if row:
        print(f"\nCliente ID: {row[0]}")
        print(f"Razão Social: {row[1]}")
        print(f"CNPJ: {row[2]}")
        print(f"Regime Tributário ID: {row[3]}")
        print(f"Regime Nome: {row[4]}")
        
        # Mostrar mapeamento CRT
        print(f"\n📋 MAPEAMENTO CRT:")
        print(f"   • Regime ID 1 = Simples Nacional → CRT 1")
        print(f"   • Regime ID 2 = Simples Nacional Sublimite → CRT 2")  
        print(f"   • Regime ID 3 = Lucro Presumido → CRT 3")
        print(f"   • Regime ID 4 = Lucro Real → CRT 3")
        
        regime_id = row[3]
        if regime_id in [1, 2]:
            crt = regime_id
            print(f"\n✅ Emitente é CRT {crt} - USA CSOSN")
        else:
            crt = 3
            print(f"\n✅ Emitente é CRT {crt} - USA CST")
    
    # Verificar regimes cadastrados
    print(f"\n" + "="*80)
    print("REGIMES TRIBUTÁRIOS CADASTRADOS")
    print("="*80)
    
    cur.execute("SELECT regime_tributario_id, nome, descricao FROM regimes_tributarios ORDER BY regime_tributario_id")
    for row in cur.fetchall():
        print(f"  ID {row[0]}: {row[1]} - {row[2] or 'Sem descrição'}")
    
    cur.close()
    conn.close()
    print("\n" + "="*80)
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

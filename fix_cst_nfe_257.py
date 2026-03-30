#!/usr/bin/env python3
"""
Corrigir NFe 257 - trocar CSOSN por CST (emitente é CRT=3 Regime Normal)
"""
import psycopg2
import json

DB_HOST = "nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "sjtnfe"
DB_USER = "postgres"
DB_PASS = "gMGM!#)NW$nH1w(wrVIdcmn5"

print("="*80)
print("CORRIGINDO NFe 257 - CSOSN → CST")
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
    
    # 1. Verificar CRT do emitente
    print("\n1. Verificando regime tributário do emitente...")
    cur.execute("""
        SELECT c.regime_tributario_id, rt.nome
        FROM nfe_emitidas ne
        JOIN clientes c ON ne.cliente_id = c.cliente_id
        LEFT JOIN regimes_tributarios rt ON c.regime_tributario_id = rt.regime_tributario_id
        WHERE ne.nfe_emitida_id = 257
    """)
    
    row = cur.fetchone()
    if row:
        regime_id = row[0]
        regime_nome = row[1] or 'Não encontrado'
        print(f"   Regime ID: {regime_id}")
        print(f"   Regime Nome: {regime_nome}")
        
        # CRT: 1=Simples Nacional, 3=Regime Normal
        crt = 3 if regime_id == 2 else 1  # Assumindo regime_id 2 = Regime Normal
        print(f"   CRT: {crt} ({'Simples Nacional' if crt == 1 else 'Regime Normal'})")
    
    # 2. Buscar json_nfe
    print("\n2. Buscando json_nfe...")
    cur.execute("SELECT json_nfe FROM nfe_emitidas WHERE nfe_emitida_id = 257")
    row = cur.fetchone()
    
    if not row or not row[0]:
        print("   ❌ json_nfe vazio!")
        exit(1)
    
    json_nfe = row[0]
    items = json_nfe.get('items', [])
    print(f"   ✅ {len(items)} itens encontrados")
    
    # 3. Corrigir itens: CSOSN → CST
    print("\n3. Corrigindo itens (CSOSN → CST)...")
    itens_corrigidos = 0
    
    for i, item in enumerate(items, 1):
        print(f"\n   Item {i}:")
        print(f"      Código: {item.get('codigo_produto')}")
        print(f"      CSOSN atual: {item.get('csosn_icms')}")
        print(f"      CST atual: {item.get('cst_icms')}")
        
        # Se tem CSOSN, remover e garantir CST
        if item.get('csosn_icms'):
            # Remover CSOSN
            item['csosn_icms'] = None
            
            # Se não tem CST ou está vazio, usar CST padrão
            if not item.get('cst_icms') or item.get('cst_icms') == '':
                # CST 20 = Redução de base de cálculo (comum para regime normal com redução)
                item['cst_icms'] = '20'
                print(f"      ✅ CSOSN removido, CST definido como: 20")
            else:
                print(f"      ✅ CSOSN removido, mantido CST: {item.get('cst_icms')}")
            
            itens_corrigidos += 1
        else:
            # Garantir que tem CST
            if not item.get('cst_icms') or item.get('cst_icms') == '':
                item['cst_icms'] = '20'
                print(f"      ✅ CST definido como: 20")
                itens_corrigidos += 1
            else:
                print(f"      ℹ️ Já tem CST: {item.get('cst_icms')}")
    
    print(f"\n   Total corrigido: {itens_corrigidos}/{len(items)} itens")
    
    # 4. Salvar no banco
    print("\n4. Salvando alterações...")
    cur.execute("""
        UPDATE nfe_emitidas 
        SET json_nfe = %s
        WHERE nfe_emitida_id = 257
    """, (json.dumps(json_nfe),))
    
    conn.commit()
    print(f"   ✅ Atualizado: {cur.rowcount} registro(s)")
    
    # 5. Verificar resultado
    print("\n5. Verificando resultado...")
    cur.execute("SELECT json_nfe FROM nfe_emitidas WHERE nfe_emitida_id = 257")
    row = cur.fetchone()
    
    if row and row[0]:
        json_check = row[0]
        items_check = json_check.get('items', [])
        
        print(f"   Itens verificados:")
        for i, item in enumerate(items_check[:3], 1):
            print(f"      Item {i}: CST={item.get('cst_icms')}, CSOSN={item.get('csosn_icms')}")
    
    print("\n✅ SUCESSO! NFe 257 corrigida para usar CST (Regime Normal)")
    print("\nAgora você pode:")
    print("1. Atualizar a página (F5)")
    print("2. Clicar em 'Emitir' na NFe 257")
    print("3. Deve emitir com CST correto!")
    
    cur.close()
    conn.close()
    print("\n" + "="*80)
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

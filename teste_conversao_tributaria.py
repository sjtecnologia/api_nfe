#!/usr/bin/env python3
"""
Teste de conversão de códigos tributários para IDs do banco
"""

from sqlalchemy import text
from routes.admin_routes import _get_db

def testar_conversoes():
    db = _get_db()
    
    print("=" * 70)
    print("TESTE DE CONVERSÃO: CÓDIGOS → IDs DO BANCO")
    print("=" * 70)
    
    # Teste 1: NCM
    print("\n📦 Teste 1: NCM")
    ncm_codigo = "38210000"
    result = db.execute(text("""
        SELECT ncm_id, codigo, descricao 
        FROM ncms 
        WHERE REPLACE(codigo, '.', '') = :codigo
        LIMIT 1
    """), {'codigo': ncm_codigo})
    row = result.fetchone()
    if row:
        print(f"   ✅ NCM {ncm_codigo} → ID {row.ncm_id}")
    else:
        print(f"   ❌ NCM {ncm_codigo} NÃO encontrado")
    
    # Teste 2: CFOP (testando vários formatos)
    print("\n🚚 Teste 2: CFOP")
    cfops_teste = ["5101", "5.101", "1102", "1.102"]
    for cfop_codigo in cfops_teste:
        result = db.execute(text("""
            SELECT cfop_id, cfop, descricao 
            FROM cfops 
            WHERE REPLACE(cfop, '.', '') = :cfop OR cfop = :cfop
            LIMIT 1
        """), {'cfop': cfop_codigo})
        row = result.fetchone()
        if row:
            print(f"   ✅ CFOP {cfop_codigo} → ID {row.cfop_id} ({row.cfop})")
        else:
            print(f"   ❌ CFOP {cfop_codigo} NÃO encontrado")
    
    # Teste 3: CST
    print("\n💰 Teste 3: CST")
    csts_teste = ["00", "10", "20", "40", "41"]
    for cst_codigo in csts_teste:
        result = db.execute(text("""
            SELECT cst_id, codigo, descricao 
            FROM cst_icms 
            WHERE codigo = :cst
            LIMIT 1
        """), {'cst': cst_codigo})
        row = result.fetchone()
        if row:
            print(f"   ✅ CST {cst_codigo} → ID {row.cst_id}")
        else:
            print(f"   ❌ CST {cst_codigo} NÃO encontrado")
    
    # Teste 4: CSOSN
    print("\n🏢 Teste 4: CSOSN")
    csosns_teste = ["101", "102", "201", "400"]
    for csosn_codigo in csosns_teste:
        result = db.execute(text("""
            SELECT csosn_id, codigo, descricao 
            FROM csosn_icms 
            WHERE codigo = :csosn
            LIMIT 1
        """), {'csosn': csosn_codigo})
        row = result.fetchone()
        if row:
            print(f"   ✅ CSOSN {csosn_codigo} → ID {row.csosn_id}")
        else:
            print(f"   ❌ CSOSN {csosn_codigo} NÃO encontrado")
    
    print("\n" + "=" * 70)
    
    # Teste 5: Simula resposta da API IA
    print("\n🤖 Teste 5: Simulação de resposta da API IA")
    print("   Produto: 'Desenvolvimento de sistema personalizado'")
    
    classificacao = {
        'ncm': '38210000',
        'cfop': '5101',
        'cst': '00',
        'cest': None,
        'csosn': None
    }
    
    resultado = {
        'ids': {},
        'classificacao': classificacao
    }
    
    # NCM
    if classificacao.get('ncm'):
        result = db.execute(text("""
            SELECT ncm_id, codigo FROM ncms 
            WHERE REPLACE(codigo, '.', '') = :codigo LIMIT 1
        """), {'codigo': classificacao['ncm']})
        row = result.fetchone()
        if row:
            resultado['ids']['ncm_id'] = row.ncm_id
            print(f"   ✅ NCM convertido: {classificacao['ncm']} → ID {row.ncm_id}")
        else:
            print(f"   ❌ NCM {classificacao['ncm']} não convertido")
    
    # CFOP
    if classificacao.get('cfop'):
        result = db.execute(text("""
            SELECT cfop_id, cfop FROM cfops 
            WHERE REPLACE(cfop, '.', '') = :cfop OR cfop = :cfop LIMIT 1
        """), {'cfop': classificacao['cfop']})
        row = result.fetchone()
        if row:
            resultado['ids']['cfop_id'] = row.cfop_id
            print(f"   ✅ CFOP convertido: {classificacao['cfop']} → ID {row.cfop_id} ({row.cfop})")
        else:
            print(f"   ❌ CFOP {classificacao['cfop']} não convertido")
    
    # CST
    if classificacao.get('cst'):
        result = db.execute(text("""
            SELECT cst_id, codigo FROM cst_icms 
            WHERE codigo = :cst LIMIT 1
        """), {'cst': classificacao['cst']})
        row = result.fetchone()
        if row:
            resultado['ids']['cst_id'] = row.cst_id
            print(f"   ✅ CST convertido: {classificacao['cst']} → ID {row.cst_id}")
        else:
            print(f"   ❌ CST {classificacao['cst']} não convertido")
    
    print(f"\n   📊 Resultado final:")
    print(f"      IDs: {resultado['ids']}")
    print(f"      Classificação: {resultado['classificacao']}")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    testar_conversoes()

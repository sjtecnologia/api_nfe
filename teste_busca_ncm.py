#!/usr/bin/env python3
"""Testa busca de NCMs para verificar se está retornando dados"""

from sqlalchemy import text
from routes.admin_routes import _get_db

def testar_busca_ncm():
    db = _get_db()
    
    print("=" * 70)
    print("TESTE: BUSCA DE NCMs NO BANCO")
    print("=" * 70)
    
    # Testa busca vazia (deve retornar os primeiros 50)
    print("\n1️⃣ Busca SEM filtro (primeiros 10 NCMs):")
    print("-" * 70)
    
    result = db.execute(text("""
        SELECT ncm_id, codigo, descricao 
        FROM ncms 
        WHERE tipo = 'analitico'
        ORDER BY codigo 
        LIMIT 10
    """))
    
    count = 0
    for row in result:
        count += 1
        print(f"  {count:2}. ID: {row.ncm_id:6} | {row.codigo} | {row.descricao[:60]}...")
    
    if count == 0:
        print("  ❌ Nenhum NCM encontrado!")
    else:
        print(f"\n  ✅ {count} NCMs encontrados!")
    
    # Testa busca com termo
    print("\n2️⃣ Busca COM filtro ('mouse'):")
    print("-" * 70)
    
    result = db.execute(text("""
        SELECT ncm_id, codigo, descricao 
        FROM ncms 
        WHERE tipo = 'analitico'
        AND (
            LOWER(descricao) LIKE :termo
            OR codigo LIKE :termo
        )
        ORDER BY codigo 
        LIMIT 10
    """), {'termo': '%mouse%'})
    
    count = 0
    for row in result:
        count += 1
        print(f"  {count:2}. ID: {row.ncm_id:6} | {row.codigo} | {row.descricao[:60]}...")
    
    if count == 0:
        print("  ❌ Nenhum NCM encontrado!")
    else:
        print(f"\n  ✅ {count} NCMs encontrados!")
    
    # Conta total de NCMs
    print("\n3️⃣ Total de NCMs no banco:")
    print("-" * 70)
    
    result = db.execute(text("""
        SELECT COUNT(*) as total FROM ncms WHERE tipo = 'analitico'
    """))
    row = result.fetchone()
    total = row.total if row else 0
    
    print(f"  📊 Total de NCMs analíticos: {total:,}")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    testar_busca_ncm()

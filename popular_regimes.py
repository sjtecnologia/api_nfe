#!/usr/bin/env python3
"""Popular tabela regimes_tributarios (tabela de referência)"""
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, '/home/ubuntu/api_nfe')

from sqlalchemy import create_engine, text
from database.connection import SessionLocal

print("Conectando ao banco...")
db = SessionLocal()

try:
    # Verificar regimes existentes
    print("\n1. Verificando regimes existentes...")
    result = db.execute(text("SELECT * FROM regimes_tributarios ORDER BY regime_tributario_id")).fetchall()
    if result:
        print(f"   Encontrados {len(result)} regimes:")
        for row in result:
            print(f"     ID {row[0]}: {row[1]}")
    else:
        print("   Tabela vazia!")
    
    # Inserir regimes padrão
    print("\n2. Inserindo regimes tributários padrão...")
    db.execute(text("""
        INSERT INTO regimes_tributarios (regime_tributario_id, nome, descricao, ativo)
        VALUES 
            (1, 'Simples Nacional', 'Regime Tributário do Simples Nacional', true),
            (2, 'Lucro Presumido', 'Regime Tributário do Lucro Presumido', true),
            (3, 'Lucro Real', 'Regime Tributário do Lucro Real', true)
        ON CONFLICT (regime_tributario_id) DO NOTHING
    """))
    db.commit()
    print("   ✅ Regimes inseridos!")
    
    # Verificar resultado
    print("\n3. Verificando resultado final...")
    result = db.execute(text("SELECT * FROM regimes_tributarios ORDER BY regime_tributario_id")).fetchall()
    print(f"   Total de regimes: {len(result)}")
    for row in result:
        print(f"     ID {row[0]}: {row[1]}")
    
    print("\n✅ Concluído!")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()

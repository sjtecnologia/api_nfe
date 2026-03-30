#!/usr/bin/env python3
"""Verifica estrutura da tabela produtos"""

from database.connection import get_db
from sqlalchemy import text

db = next(get_db())
try:
    # Verifica chaves primárias
    result = db.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'produtos' 
        ORDER BY ordinal_position
    """)).fetchall()
    
    print("Colunas da tabela produtos:")
    for row in result:
        print(f"  - {row[0]}: {row[1]}")
        
    # Verifica constraints
    constraints = db.execute(text("""
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints
        WHERE table_name = 'produtos'
    """)).fetchall()
    
    print("\nConstraints:")
    for row in constraints:
        print(f"  - {row[0]}: {row[1]}")
        
finally:
    db.close()

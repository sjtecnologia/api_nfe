#!/usr/bin/env python3
"""Script temporário para verificar tabelas do banco de dados"""

from sqlalchemy import text
from routes.admin_routes import _get_db

def verificar_tabelas():
    db = _get_db()
    
    # Lista todas as tabelas
    result = db.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """))
    
    print("=" * 60)
    print("TABELAS NO BANCO DE DADOS:")
    print("=" * 60)
    
    tables = []
    for row in result:
        table_name = row[0]
        tables.append(table_name)
        print(f"  ✓ {table_name}")
    
    print(f"\nTotal: {len(tables)} tabelas\n")
    
    # Verifica especificamente as tabelas que estamos procurando
    print("=" * 60)
    print("VERIFICAÇÃO DE TABELAS ESPECÍFICAS:")
    print("=" * 60)
    
    tables_to_check = ['ncms', 'cfops', 'cfop', 'csts', 'cst', 'csosns', 'csosn', 'cests', 'cest']
    
    for table_name in tables_to_check:
        exists = table_name in tables
        status = "[OK] EXISTE" if exists else "[X] NÃO EXISTE"
        print(f"  {table_name:15} → {status}")
    
    # Se encontrou alguma tabela relacionada a CST, mostra alguns registros
    print("\n" + "=" * 60)
    print("VERIFICAÇÃO DE DADOS:")
    print("=" * 60)
    
    # Verifica CFOP
    cfop_table = None
    for name in ['cfops', 'cfop']:
        if name in tables:
            cfop_table = name
            break
    
    if cfop_table:
        print(f"\n[LIST] Registros da tabela '{cfop_table}':")
        result = db.execute(text(f"SELECT * FROM {cfop_table} LIMIT 5"))
        cols = result.keys()
        print(f"   Colunas: {', '.join(cols)}")
        
        for row in result:
            print(f"   {dict(row)}")
        
        # Verifica se existe CFOP 5101
        result = db.execute(text(f"SELECT * FROM {cfop_table} WHERE codigo = '5101'"))
        row = result.fetchone()
        if row:
            print(f"\n   [OK] CFOP 5101 encontrado: {dict(row)}")
        else:
            print(f"\n   [X] CFOP 5101 NÃO encontrado")
            # Mostra CFOPs que começam com 5
            result = db.execute(text(f"SELECT * FROM {cfop_table} WHERE codigo LIKE '5%' LIMIT 5"))
            print(f"   CFOPs começando com 5:")
            for row in result:
                print(f"      {dict(row)}")
    
    # Verifica CST
    cst_table = None
    for name in ['csts', 'cst']:
        if name in tables:
            cst_table = name
            break
    
    if cst_table:
        print(f"\n[LIST] Registros da tabela '{cst_table}':")
        result = db.execute(text(f"SELECT * FROM {cst_table} LIMIT 5"))
        cols = result.keys()
        print(f"   Colunas: {', '.join(cols)}")
        
        for row in result:
            print(f"   {dict(row)}")
    
    # Verifica CSOSN
    csosn_table = None
    for name in ['csosns', 'csosn']:
        if name in tables:
            csosn_table = name
            break
    
    if csosn_table:
        print(f"\n[LIST] Registros da tabela '{csosn_table}':")
        result = db.execute(text(f"SELECT * FROM {csosn_table} LIMIT 5"))
        cols = result.keys()
        print(f"   Colunas: {', '.join(cols)}")
        
        for row in result:
            print(f"   {dict(row)}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    verificar_tabelas()

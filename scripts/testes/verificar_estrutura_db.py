#!/usr/bin/env python3
"""Script para verificar estrutura tributária do banco de dados"""

from sqlalchemy import text
from routes.admin_routes import _get_db

db = _get_db()

print("=" * 70)
print("ESTRUTURA DAS TABELAS TRIBUTÁRIAS")
print("=" * 70)

# 1. CFOPS
print(f"\n[LIST] Tabela 'cfops':")
result = db.execute(text("SELECT * FROM cfops LIMIT 3"))
cols = list(result.keys())
print(f"   Colunas: {cols}")

for row in result:
    print(f"   {list(row)}")

# Verifica CFOP 5101
result = db.execute(text("SELECT * FROM cfops WHERE cfop = '5101' LIMIT 1"))
row = result.fetchone()
if row:
    print(f"\n   [OK] CFOP 5101 encontrado: {list(row)}")
else:
    print(f"\n   [X] CFOP 5101 NÃO encontrado")
    result = db.execute(text("SELECT * FROM cfops WHERE cfop LIKE '51%' LIMIT 5"))
    print(f"   CFOPs começando com 51:")
    for row in result:
        print(f"      {list(row)}")

# 2. CST ICMS
print(f"\n[LIST] Tabela 'cst_icms':")
result = db.execute(text("SELECT * FROM cst_icms LIMIT 5"))
cols = list(result.keys())
print(f"   Colunas: {cols}")

for row in result:
    print(f"   {list(row)}")

# 3. CSOSN ICMS
print(f"\n[LIST] Tabela 'csosn_icms':")
result = db.execute(text("SELECT * FROM csosn_icms LIMIT 5"))
cols = list(result.keys())
print(f"   Colunas: {cols}")

for row in result:
    print(f"   {list(row)}")

# 4. NCMs (apenas verificação)
print(f"\n[LIST] Verificação NCM 38210000:")
result = db.execute(text("SELECT ncm_id, codigo, descricao FROM ncms WHERE codigo = '38210000' LIMIT 1"))
row = result.fetchone()
if row:
    print(f"   [OK] NCM encontrado: {list(row)}")

print("\n" + "=" * 70)

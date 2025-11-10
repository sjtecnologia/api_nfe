#!/usr/bin/env python3
"""Verifica a diferença entre CEST e CST no banco de dados"""

from sqlalchemy import text
from routes.admin_routes import _get_db

db = _get_db()

print('=' * 70)
print('📊 DIFERENÇA ENTRE CEST E CST')
print('=' * 70)

# 1. Lista tabelas relacionadas
print('\n🗂️  TABELAS NO BANCO:')
print('-' * 70)
result = db.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND (table_name LIKE '%cest%' OR table_name LIKE '%cst%')
    ORDER BY table_name
"""))

for row in result:
    print(f'  ✓ {row[0]}')

# 2. Verifica colunas na tabela produtos
print('\n📦 COLUNAS NA TABELA "produtos":')
print('-' * 70)
result = db.execute(text("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns 
    WHERE table_name = 'produtos' 
    AND (column_name LIKE '%cest%' OR column_name LIKE '%cst%')
    ORDER BY column_name
"""))

for row in result:
    tipo = row[1]
    if row[2]:
        tipo += f'({row[2]})'
    print(f'  ✓ {row[0]:20} → {tipo}')

# 3. Mostra dados da tabela cst_icms
print('\n💰 TABELA "cst_icms" (CST):')
print('-' * 70)
result = db.execute(text("""
    SELECT cst_id, codigo, descricao 
    FROM cst_icms 
    LIMIT 3
"""))

for row in result:
    print(f'  ID: {row[0]:3} | Código: {row[1]:3} | {row[2][:50]}...')

# 4. Verifica se existe tabela cest
print('\n🏷️  TABELA "cest" (existe?):')
print('-' * 70)
try:
    result = db.execute(text("SELECT * FROM cest LIMIT 1"))
    row = result.fetchone()
    if row:
        print(f'  ✅ Tabela CEST existe!')
        print(f'  Colunas: {list(result.keys())}')
except Exception as e:
    print(f'  ❌ Tabela CEST NÃO existe')
    print(f'  Erro: {str(e)[:60]}...')

# 5. Verifica produtos com CEST preenchido
print('\n📋 PRODUTOS COM CEST PREENCHIDO:')
print('-' * 70)
result = db.execute(text("""
    SELECT produto_id, descricao, cest, cst_id
    FROM produtos 
    WHERE cest IS NOT NULL
    LIMIT 3
"""))

count = 0
for row in result:
    print(f'  ID: {row[0]:4} | CEST: {row[2]:10} | CST_ID: {row[3]} | {row[1][:30]}...')
    count += 1

if count == 0:
    print('  ⚠️  Nenhum produto tem CEST preenchido ainda')

print('\n' + '=' * 70)
print('📖 EXPLICAÇÃO:')
print('=' * 70)
print("""
CST (Código de Situação Tributária):
  - Define como o ICMS é calculado (tributado, isento, substituição, etc.)
  - Tem TABELA no banco: cst_icms
  - É um SELECT (escolhe de uma lista fixa)
  - Exemplos: 00, 10, 20, 40, 41, 60, 90

CEST (Código Especificador da Substituição Tributária):
  - Identifica produtos sujeitos a ST (Substituição Tributária)
  - NÃO tem tabela no banco (é campo livre)
  - É um INPUT TEXT (digita o código)
  - Formato: XX.XXX.XX (ex: 01.001.00)
  - Obrigatório apenas para produtos com ST

➡️  SÃO CAMPOS DIFERENTES! CST é obrigatório, CEST é opcional.
""")
print('=' * 70)

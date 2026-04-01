#!/usr/bin/env python3
"""Script para remover aspas tipográficas dos produtos"""
import psycopg2

# Conectar ao banco RDS AWS
conn = psycopg2.connect(
    host="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com",
    port=5432,
    database="sjtnfe",
    user="postgres",
    password="gMGM!#)NW$nH1w(wrVIdcmn5"
)

cur = conn.cursor()

# Atualizar descrições removendo aspas tipográficas (Unicode)
cur.execute("""
    UPDATE produtos 
    SET descricao = REPLACE(REPLACE(descricao, CHR(8220), CHR(34)), CHR(8221), CHR(34))
    WHERE descricao ~ CHR(8220) OR descricao ~ CHR(8221)
    RETURNING produto_id, descricao
""")

updated = cur.fetchall()
conn.commit()

print(f'✅ {len(updated)} produto(s) atualizado(s):')
for prod_id, desc in updated:
    print(f'  - ID {prod_id}: {desc}')

cur.close()
conn.close()

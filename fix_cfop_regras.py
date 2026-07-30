"""
Ajusta as regras restauradas de SJ Tecnologia:
- Regras inter-estaduais: cfop_id → NULL (aceita qualquer CFOP buscado)
- Isso corrige o problema do produto ter CFOP 5102 mas a regra precisar de 6102
"""
import os
os.environ['DATABASE_URL'] = open('/home/ubuntu/api_nfe/.env').read().split('DATABASE_URL=')[1].split()[0]

from database.connection import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Verificar regras atuais
rows = db.execute(text("""
SELECT regra_tributacao_id, descricao_regra, cfop_id, uf_origem, uf_destino, aliquota_icms
FROM regras_tributacao WHERE cliente_id = 5 ORDER BY regra_tributacao_id
""")).fetchall()
print("Regras atuais de SJ Tecnologia:")
for r in rows:
    print(f"  ID={r[0]}: '{r[1]}' cfop_id={r[2]} | {r[3]}->{r[4]} aliq={r[5]}")

# Atualizar regras inter-estaduais (uf_destino != 'SP') para cfop_id = NULL
result = db.execute(text("""
UPDATE regras_tributacao
SET cfop_id = NULL
WHERE cliente_id = 5
  AND uf_destino IS NOT NULL
  AND uf_destino != 'SP'
"""))
db.commit()
print(f"\nRegras inter-estaduais atualizadas (cfop_id=NULL): {result.rowcount}")

# Verificar resultado
rows2 = db.execute(text("""
SELECT regra_tributacao_id, descricao_regra, cfop_id, uf_origem, uf_destino, aliquota_icms
FROM regras_tributacao WHERE cliente_id = 5 ORDER BY regra_tributacao_id
""")).fetchall()
print("\nRegras APÓS ajuste:")
for r in rows2:
    print(f"  ID={r[0]}: '{r[1]}' cfop_id={r[2]} | {r[3]}->{r[4]} aliq={r[5]}")

db.close()
print("\nCONCLUIDO")

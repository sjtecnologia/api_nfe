#!/usr/bin/env python3
"""
Atualiza o campo 'descricao' da tabela produtos no RDS
usando o campo IdForn da planilha Produtoimp.xlsx
como chave (corresponde a codigo_interno na tabela produtos).
"""

import sys
import openpyxl
import psycopg2
from psycopg2.extras import execute_batch

# ─── Configuração do banco ───────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com",
    "port":     5432,
    "dbname":   "sjtnfe",
    "user":     "postgres",
    "password": "***SENHA_RDS_ROTACIONADA***",
    "connect_timeout": 10,
}

PLANILHA = "Produtoimp.xlsx"

# ─── Leitura da planilha ─────────────────────────────────────────────────────
print(f"Lendo planilha: {PLANILHA}")
wb = openpyxl.load_workbook(PLANILHA, read_only=True, data_only=True)
ws = wb.active

# Mapeia cabeçalhos → índice de coluna
headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
idx_id   = headers.index("IdForn")
idx_desc = headers.index("Descricao")

dados = []
for row in ws.iter_rows(min_row=2, values_only=True):
    id_forn  = row[idx_id]
    descricao = row[idx_desc]
    if id_forn is None:
        continue
    dados.append((str(descricao).strip() if descricao is not None else "", str(id_forn).strip()))

wb.close()
print(f"Registros lidos da planilha: {len(dados)}")

# ─── Conexão e atualização ───────────────────────────────────────────────────
print("Conectando ao RDS...")
conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = False
cur = conn.cursor()

# Quantos registros serão afetados
idforn_list = [d[1] for d in dados]
cur.execute(
    "SELECT COUNT(*) FROM produtos WHERE codigo_interno = ANY(%s)",
    (idforn_list,)
)
total_match = cur.fetchone()[0]
print(f"Registros na tabela que coincidem com IdForn: {total_match}")

if total_match == 0:
    print("Nenhum registro encontrado para atualizar. Encerrando.")
    cur.close()
    conn.close()
    sys.exit(0)

# Executa o UPDATE em lote
SQL = "UPDATE produtos SET descricao = %s WHERE codigo_interno = %s"
print("Executando atualizações...")
execute_batch(cur, SQL, dados, page_size=500)

updated = cur.rowcount
# rowcount via execute_batch não é confiável; usa SELECT COUNT após
conn.commit()

# Confirma quantos foram de fato atualizados
cur.execute(
    "SELECT COUNT(*) FROM produtos WHERE codigo_interno = ANY(%s)",
    (idforn_list,)
)
total_after = cur.fetchone()[0]

print(f"\nResumo:")
print(f"  Linhas da planilha processadas : {len(dados)}")
print(f"  Registros encontrados no banco : {total_match}")
print(f"  Atualização concluída com sucesso!")

cur.close()
conn.close()
print("\nConexão encerrada.")

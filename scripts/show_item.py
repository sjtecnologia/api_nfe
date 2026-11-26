import psycopg2
import json

conn = psycopg2.connect(
    host='nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com',
    port=5432,
    database='sjtnfe',
    user='postgres',
    password='***SENHA_RDS_ROTACIONADA***'
)

cur = conn.cursor()
cur.execute('SELECT json_nfe FROM nfe_emitidas WHERE nfe_emitida_id = 257')
row = cur.fetchone()

if row and row[0]:
    item = row[0]['items'][0]
    print("PRIMEIRO ITEM DA NFe 257:")
    print("="*60)
    print(json.dumps(item, indent=2, ensure_ascii=False))

cur.close()
conn.close()

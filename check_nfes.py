import psycopg2

conn = psycopg2.connect(
    host='nfse-teste.cfmplvwvkswo.us-east-1.rds.amazonaws.com',
    database='db_nfse_homolog',
    user='sj_user',
    password='12asdWE@!'
)
cur = conn.cursor()
cur.execute("SELECT numero, status, LEFT(chave_acesso, 30) FROM nfe_emitidas WHERE cliente_id = 5 ORDER BY numero DESC LIMIT 10")
for row in cur.fetchall():
    print(f'Número: {row[0]}, Status: {row[1]}, Chave: {row[2]}')
cur.close()
conn.close()

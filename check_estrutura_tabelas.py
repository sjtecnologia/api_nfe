import psycopg2

conn = psycopg2.connect(
    host="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com",
    database="sjtnfe",
    user="postgres",
    password="gMGM!#)NW$nH1w(wrVIdcmn5",
    port=5432
)
cur = conn.cursor()

# Descobrir estrutura da tabela clientes
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'clientes'
    ORDER BY ordinal_position
""")

print("COLUNAS DA TABELA CLIENTES:")
for col in cur.fetchall():
    print(f"  {col[0]} ({col[1]})")

print("\n" + "=" * 80)

# Descobrir estrutura da tabela regras_tributarias
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'regras_tributarias'
    ORDER BY ordinal_position
""")

print("\nCOLUNAS DA TABELA REGRAS_TRIBUTARIAS:")
for col in cur.fetchall():
    print(f"  {col[0]} ({col[1]})")

print("\n" + "=" * 80)

# Buscar dados do cliente 29
cur.execute("SELECT * FROM clientes WHERE cliente_id = 29")
cliente = cur.fetchone()
if cliente:
    # Obter os nomes das colunas
    col_names = [desc[0] for desc in cur.description]
    print("\nDADOS DO CLIENTE 29:")
    for i, name in enumerate(col_names):
        if cliente[i]:
            print(f"  {name}: {cliente[i]}")

print("\n" + "=" * 80)

# Buscar regras tributárias do cliente 29
cur.execute("SELECT * FROM regras_tributarias WHERE cliente_id = 29")
regras = cur.fetchall()
if regras:
    col_names = [desc[0] for desc in cur.description]
    print(f"\nR EGRAS TRIBUTÁRIAS DO CLIENTE 29 ({len(regras)} regras):")
    for regra in regras:
        print("\n  Regra:")
        for i, name in enumerate(col_names):
            if regra[i] is not None:
                print(f"    {name}: {regra[i]}")
else:
    print("\n❌ NENHUMA REGRA TRIBUTÁRIA ENCONTRADA")

cur.close()
conn.close()

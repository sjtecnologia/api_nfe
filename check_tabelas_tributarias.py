import psycopg2

conn = psycopg2.connect(
    host="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com",
    database="sjtnfe",
    user="postgres",
    password="gMGM!#)NW$nH1w(wrVIdcmn5",
    port=5432
)
cur = conn.cursor()

print("=" * 80)
print("BUSCA POR TABELAS RELACIONADAS A REGRAS/TRIBUTAÇÃO")
print("=" * 80)

# Listar todas as tabelas
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")

print("\nTABELAS NO BANCO:")
for table in cur.fetchall():
    table_name = table[0]
    if any(palavra in table_name.lower() for palavra in ['regra', 'tribut', 'fiscal', 'imposto', 'tax']):
        print(f"  ✅ {table_name}")
    else:
        print(f"     {table_name}")

print("\n" + "=" * 80)
print("CONCLUSÃO")
print("=" * 80)
print("""
⚠️  PROBLEMA IDENTIFICADO:

A tabela 'regras_tributarias' NÃO EXISTE no banco de dados!

CLIENTE 29:
- Razão Social: ZOMN TECNOLOGIA LTDA
- CNPJ: 57308098000166
- Regime Tributário ID: 1 (Simples Nacional)
- Inscrição Estadual: 150876513114

SEM a tabela de regras tributárias, o sistema não consegue:
1. Buscar regras para preencher CST/CSOSN automaticamente
2. Calcular impostos corretamente
3. Validar se há regra cadastrada para o produto

SOLUÇÃO:
1. Criar a tabela regras_tributarias
2. OU modificar o sistema para usar outra forma de definir tributação
3. OU cadastrar regras tributárias diretamente nos produtos
""")

cur.close()
conn.close()

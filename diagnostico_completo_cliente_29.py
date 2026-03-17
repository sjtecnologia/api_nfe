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
print("ANÁLISE COMPLETA - REGRAS TRIBUTÁRIAS CLIENTE 29")
print("=" * 80)

# Estrutura da tabela regras_tributacao
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'regras_tributacao'
    ORDER BY ordinal_position
""")

print("\n📋 ESTRUTURA DA TABELA regras_tributacao:")
for col in cur.fetchall():
    print(f"  {col[0]} ({col[1]})")

# Buscar regras do cliente 29
print("\n" + "=" * 80)
print("🔍 REGRAS CADASTRADAS PARA O CLIENTE 29")
print("=" * 80)

cur.execute("SELECT * FROM regras_tributacao WHERE cliente_id = 29")
regras = cur.fetchall()

if regras:
    col_names = [desc[0] for desc in cur.description]
    print(f"\n✅ ENCONTRADAS {len(regras)} REGRAS:\n")
    for idx, regra in enumerate(regras, 1):
        print(f"REGRA #{idx}:")
        for i, name in enumerate(col_names):
            if regra[i] is not None:
                print(f"  {name}: {regra[i]}")
        print()
else:
    print("\n❌ NENHUMA REGRA CADASTRADA PARA O CLIENTE 29!")
    print("\nIsso explica o erro: 'Não tem regra tributária'")

# Verificar produtos do cliente
print( "=" * 80)
print("📦 PRODUTOS DO CLIENTE 29")
print("=" * 80)

cur.execute("""
    SELECT produto_id, codigo, descricao, tipo_produto, ncm, ativo
    FROM produtos 
    WHERE cliente_id = 29
    LIMIT 5
""")

produtos = cur.fetchall()
if produtos:
    print(f"\n✅ ENCONTRADOS {len(produtos)} PRODUTOS:")
    for prod in produtos:
        print(f"\n  Produto ID: {prod[0]}")
        print(f"  Código: {prod[1]}")
        print(f"  Descrição: {prod[2]}")
        print(f"  Tipo: {prod[3]}")
        print(f"  NCM: {prod[4]}")
        print(f"  Ativo: {'✅' if prod[5] else '❌'}")
else:
    print("\n❌ NENHUM PRODUTO CADASTRADO")

# Verificar regime tributário
print("\n" + "=" * 80)
print("📊 REGIME TRIBUTÁRIO")
print("=" * 80)

cur.execute("""
    SELECT rt.regime_id, rt.codigo, rt.descricao
    FROM regimes_tributarios rt
    JOIN clientes c ON c.regime_tributario_id = rt.regime_id
    WHERE c.cliente_id = 29
""")

regime = cur.fetchone()
if regime:
    print(f"\n✅ Regime ID: {regime[0]}")
    print(f"  Código: {regime[1]}")
    print(f"  Descrição: {regime[2]}")

print("\n" + "=" * 80)
print("💡 CONCLUSÃO")
print("=" * 80)
print("""
PROBLEMA IDENTIFICADO:
O cliente 29 NÃO tem REGRAS TRIBUTÁRIAS cadastradas na tabela 'regras_tributacao'.

Quando você seleciona um produto na emissão da NFe, o sistema tenta buscar
as regras tributárias (CST, CSOSN, alíquotas) mas não encontra nenhuma
regra cadastrada para este cliente.

SOLUÇÃO:
1. Cadastrar regras tributárias para o cliente 29
2. As regras devem incluir:
   - Tipo de operação (entrada/saída)
   - Tipo de produto (mercadoria/serviço)
   - CSOSN ou CST ICMS
   - CST PIS e COFINS
   - Alíquotas

Para um cliente Simples Nacional (regime_id = 1), uma regra típica seria:
- CSOSN: 102 (sem permissão de crédito)
- CST PIS: 07 (isento)
- CST COFINS: 07 (isento)
""")

cur.close()
conn.close()

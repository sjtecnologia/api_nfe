import psycopg2
import json

conn = psycopg2.connect(
    host="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com",
    database="sjtnfe",
    user="postgres",
    password="gMGM!#)NW$nH1w(wrVIdcmn5",
    port=5432
)
cur = conn.cursor()

print("=" * 80)
print("ANÁLISE DE REGRAS TRIBUTÁRIAS - CLIENTE 29")
print("=" * 80)

# Buscar informações do cliente
cur.execute("""
    SELECT cliente_id, razao_social, cnpj_cpf
    FROM clientes 
    WHERE cliente_id = 29
""")

cliente = cur.fetchone()
if cliente:
    print(f"\n📋 CLIENTE:")
    print(f"  ID: {cliente[0]}")
    print(f"  Razão Social: {cliente[1]}")
    print(f"  CNPJ: {cliente[2]}")
else:
    print("❌ Cliente 29 não encontrado")
    cur.close()
    conn.close()
    exit()

# Buscar regras tributárias do cliente
print("\n" + "=" * 80)
print("🔍 REGRAS TRIBUTÁRIAS CADASTRADAS")
print("=" * 80)

cur.execute("""
    SELECT 
        regra_id,
        cliente_id,
        tipo_operacao,
        tipo_produto,
        regime_tributario_id,
        cst_icms,
        csosn,
        aliquota_icms,
        cst_pis,
        aliquota_pis,
        cst_cofins,
        aliquota_cofins,
        cst_ipi,
        aliquota_ipi,
        ativo
    FROM regras_tributarias 
    WHERE cliente_id = 29
    ORDER BY regra_id
""")

regras = cur.fetchall()
if regras:
    print(f"\n✅ ENCONTRADAS {len(regras)} REGRAS:")
    for regra in regras:
        print(f"\n  📌 Regra ID: {regra[0]}")
        print(f"     Tipo Operação: {regra[2]}")
        print(f"     Tipo Produto: {regra[3]}")
        print(f"     Regime ID: {regra[4]}")
        print(f"     CST ICMS: {regra[5]}")
        print(f"     CSOSN: {regra[6]}")
        print(f"     Alíquota ICMS: {regra[7]}%")
        print(f"     CST PIS: {regra[8]} (Aliq: {regra[9]}%)")
        print(f"     CST COFINS: {regra[10]} (Aliq: {regra[11]}%)")
        print(f"     CST IPI: {regra[12]} (Aliq: {regra[13]}%)")
        print(f"     Ativa: {'✅ SIM' if regra[14] else '❌ NÃO'}")
else:
    print("❌ NENHUMA REGRA TRIBUTÁRIA ENCONTRADA PARA O CLIENTE 29")

# Buscar produtos do cliente
print("\n" + "=" * 80)
print("📦 PRODUTOS CADASTRADOS")
print("=" * 80)

cur.execute("""
    SELECT 
        produto_id,
        codigo,
        descricao,
        ncm,
        tipo_produto,
        valor_unitario,
        ativo
    FROM produtos 
    WHERE cliente_id = 29
    ORDER BY codigo
    LIMIT 10
""")

produtos = cur.fetchall()
if produtos:
    print(f"\n✅ ENCONTRADOS {len(produtos)} PRODUTOS:")
    for prod in produtos:
        print(f"\n  📦 Produto ID: {prod[0]}")
        print(f"     Código: {prod[1]}")
        print(f"     Descrição: {prod[2]}")
        print(f"     NCM: {prod[3]}")
        print(f"     Tipo: {prod[4]}")
        print(f"     Valor: R$ {prod[5]}")
        print(f"     Ativo: {'✅' if prod[6] else '❌'}")
else:
    print("❌ NENHUM PRODUTO ENCONTRADO PARA O CLIENTE 29")

# Buscar última NFe do cliente para ver como foram preenchidos os campos
print("\n" + "=" * 80)
print("📄 ÚLTIMA NFe DO CLIENTE")
print("=" * 80)

cur.execute("""
    SELECT 
        nfe_emitida_id,
        numero,
        serie,
        status,
        data_emissao,
        json_nfe
    FROM nfe_emitidas 
    WHERE cliente_id = 29
    ORDER BY nfe_emitida_id DESC
    LIMIT 1
""")

nfe = cur.fetchone()
if nfe:
    print(f"\n  NFe ID: {nfe[0]}")
    print(f"  Número: {nfe[1]}, Série: {nfe[2]}")
    print(f"  Status: {nfe[3]}")
    print(f"  Data: {nfe[4]}")
    
    if nfe[5]:
        try:
            json_data = json.loads(nfe[5]) if isinstance(nfe[5], str) else nfe[5]
            if 'items' in json_data and len(json_data['items']) > 0:
                item = json_data['items'][0]
                print(f"\n  📦 Primeiro Produto:")
                print(f"     Código: {item.get('codigo_produto', 'N/A')}")
                print(f"     Descrição: {item.get('descricao', 'N/A')}")
                print(f"     CSOSN: {item.get('csosn', 'N/A')}")
                print(f"     CST PIS: {item.get('cst_pis', 'N/A')}")
                print(f"     CST COFINS: {item.get('cst_cofins', 'N/A')}")
        except:
            print("  ⚠️ Erro ao processar JSON")
else:
    print("❌ NENHUMA NFe ENCONTRADA")

print("\n" + "=" * 80)
print("💡 DIAGNÓSTICO")
print("=" * 80)

cur.close()
conn.close()

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
print("ANÁLISE DA NFe 275 - ERRO DE DUPLICIDADE")
print("=" * 80)

# Buscar informações da NFe 275
cur.execute("""
    SELECT 
        nfe_emitida_id,
        numero,
        serie,
        chave_acesso,
        status,
        mensagem_sefaz,
        protocolo_sefaz,
        cliente_id,
        data_emissao,
        data_criacao,
        json_nfe
    FROM nfe_emitidas 
    WHERE nfe_emitida_id = 275
""")

result = cur.fetchone()
if result:
    print(f"\n📄 DADOS DA NFe 275:")
    print(f"  ID: {result[0]}")
    print(f"  Número: {result[1]}")
    print(f"  Série: {result[2]}")
    print(f"  Chave: {result[3]}")
    print(f"  Status: {result[4]}")
    print(f"  Cliente ID: {result[7]}")
    print(f"  Data Emissão: {result[8]}")
    print(f"  Data Criação: {result[9]}")
    print(f"  Protocolo SEFAZ: {result[6]}")
    print(f"\n📋 Mensagem SEFAZ:")
    print(f"  {result[5]}")
    
    chave = result[3]
    numero = result[1]
    serie = result[2]
    cliente_id = result[7]
    json_nfe = result[10]
    
    # Buscar outras notas com mesma chave
    print("\n" + "=" * 80)
    print("🔍 DUPLICIDADE #1: Mesma Chave de Acesso")
    print("=" * 80)
    cur.execute("""
        SELECT nfe_emitida_id, numero, serie, status, data_emissao, data_criacao 
        FROM nfe_emitidas 
        WHERE chave_acesso = %s
        ORDER BY nfe_emitida_id
    """, (chave,))
    
    duplicatas_chave = cur.fetchall()
    if len(duplicatas_chave) > 1:
        print(f"⚠️  ENCONTRADAS {len(duplicatas_chave)} NOTAS COM A MESMA CHAVE:")
        for dup in duplicatas_chave:
            print(f"  • NFe {dup[0]}: Número {dup[1]}, Série {dup[2]}")
            print(f"    Status: {dup[3]}")
            print(f"    Data Emissão: {dup[4]}, Data Criação: {dup[5]}")
            print()
    else:
        print("✅ Nenhuma duplicidade de chave encontrada no banco local")
    
    # Buscar outras notas com mesmo número/série do mesmo emitente
    print("\n" + "=" * 80)
    print("🔍 DUPLICIDADE #2: Mesmo Número/Série/Cliente")
    print("=" * 80)
    cur.execute("""
        SELECT nfe_emitida_id, numero, serie, chave_acesso, status, 
               data_emissao, mensagem_sefaz, data_criacao
        FROM nfe_emitidas 
        WHERE numero = %s AND serie = %s AND cliente_id = %s
        ORDER BY data_criacao
    """, (numero, serie, cliente_id))
    
    duplicatas_numero = cur.fetchall()
    if len(duplicatas_numero) > 1:
        print(f"⚠️  ENCONTRADAS {len(duplicatas_numero)} NOTAS COM MESMO NÚMERO/SÉRIE:")
        for dup in duplicatas_numero:
            print(f"  • NFe {dup[0]}: Número {dup[1]}, Série {dup[2]}")
            print(f"    Chave: {dup[3]}")
            print(f"    Status: {dup[4]}")
            print(f"    Data Emissão: {dup[5]}")
            print(f"    Data Criação: {dup[7]}")
            print(f"    Mensagem: {dup[6][:100] if dup[6] else 'N/A'}...")
            print()
    else:
        print("✅ Nenhuma duplicidade de número/série encontrada no banco local")
    
    # Analisar JSON da NFe
    if json_nfe:
        print("\n" + "=" * 80)
        print("📄 INFORMAÇÕES DO JSON DA NFe")
        print("=" * 80)
        try:
            nfe_data = json.loads(json_nfe) if isinstance(json_nfe, str) else json_nfe
            if 'xml_content' in nfe_data:
                print("✅ XML presente no JSON")
            if 'form_data' in nfe_data:
                form = nfe_data['form_data']
                print(f"  Natureza: {form.get('natureza_operacao', 'N/A')}")
                print(f"  Emitente CNPJ: {form.get('cnpj_emitente', 'N/A')}")
        except:
            print("⚠️  Erro ao processar JSON")
else:
    print("❌ NFe 275 não encontrada no banco")

print("\n" + "=" * 80)
print("💡 CONCLUSÃO")
print("=" * 80)
print("""
A SEFAZ retornou erro de "Duplicidade de NF-e" [nRec:351022311153647].

Isto significa que a SEFAZ já tem uma nota autorizada com:
  • Mesmo CNPJ emitente (57308098000166)
  • Mesma Série (1)
  • Mesmo Número (1)

POSSÍVEIS CAUSAS:
1. Esta nota já foi autorizada anteriormente (talvez em outro sistema)
2. Houve uma tentativa anterior que foi autorizada mas não registrada no sistema
3. O contador de numeração não está sincronizado com a SEFAZ

SOLUÇÃO:
- Verificar no Portal da SEFAZ se há nota Série 1 Número 1 já autorizada
- Se existir, alterar o número da nota para o próximo disponível
- Atualizar o último número usado no sistema para evitar novas duplicidades
""")

cur.close()
conn.close()

"""
Importação de produtos do arquivo Produtoimp.xlsx para o cliente 27.
Valores fixos: tipo_item=Produto, CFOP=5102, origem=0, CST ICMS=00
"""
import os
import sys
import openpyxl
import psycopg2
from psycopg2.extras import execute_values

# ── Configuração ──────────────────────────────────────────────────────────────
XLSX_PATH   = os.path.join(os.path.dirname(__file__), 'Produtoimp.xlsx')
DB_HOST     = 'nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com'
DB_NAME     = 'sjtnfe'
DB_USER     = 'postgres'
DB_PASS     = 'gMGM!#)NW$nH1w(wrVIdcmn5'

CLIENTE_ID      = 27
TIPO_ITEM       = 'Produto'
CFOP_CODIGO     = '5102'
ORIGEM          = 0          # 0 = Nacional
CST_ICMS_CODIGO = '00'
CREATED_BY      = 1          # user_id padrão (admin)
# ─────────────────────────────────────────────────────────────────────────────


def conectar():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )


def buscar_ids_fixos(cur):
    """Resolve cfop_id e cst_id uma única vez."""
    cur.execute("SELECT cfop_id FROM cfops WHERE cfop = %s LIMIT 1", (CFOP_CODIGO,))
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"[ERRO] CFOP {CFOP_CODIGO} não encontrado na tabela cfops")
    cfop_id = row[0]
    print(f"  CFOP {CFOP_CODIGO} → cfop_id={cfop_id}")

    cur.execute("SELECT cst_id FROM cst_icms WHERE codigo = %s LIMIT 1", (CST_ICMS_CODIGO,))
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"[ERRO] CST ICMS {CST_ICMS_CODIGO} não encontrado na tabela cst")
    cst_id = row[0]
    print(f"  CST ICMS {CST_ICMS_CODIGO} → cst_id={cst_id}")

    return cfop_id, cst_id


def carregar_ncms(cur):
    """Retorna dict {codigo_ncm: ncm_id}."""
    cur.execute("SELECT ncm_id, codigo FROM ncms")
    return {str(r[1]).strip().zfill(8): r[0] for r in cur.fetchall()}


def ler_xlsx():
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()
    return rows


def main():
    print("=" * 60)
    print("Importação de Produtos — Cliente 27")
    print("=" * 60)

    print("\n[1] Lendo Excel...")
    rows = ler_xlsx()
    print(f"  {len(rows)} linhas encontradas")

    print("\n[2] Conectando ao banco...")
    conn = conectar()
    cur = conn.cursor()

    print("\n[3] Buscando IDs fixos...")
    cfop_id, cst_id = buscar_ids_fixos(cur)

    print("\n[4] Carregando tabela NCM...")
    ncm_map = carregar_ncms(cur)
    print(f"  {len(ncm_map)} NCMs carregados")

    print("\n[5] Processando produtos...")
    registros = []
    ignorados = 0
    erros     = []

    for i, row in enumerate(rows, start=2):
        try:
            id_forn   = str(row[0]).strip() if row[0] is not None else None
            descricao = str(row[1]).strip() if row[1] is not None else None
            unidade   = str(row[2]).strip() if row[2] is not None else 'UN'
            preco     = float(row[3]) if row[3] is not None else 0.0
            ncm_raw   = str(row[4]).strip() if row[4] is not None else ''

            if not descricao:
                ignorados += 1
                continue

            ncm_str = ncm_raw.replace('.', '').replace('-', '').zfill(8)
            ncm_id  = ncm_map.get(ncm_str)
            if not ncm_id:
                erros.append(f"Linha {i}: NCM '{ncm_raw}' não encontrado — '{descricao}' ignorado")
                ignorados += 1
                continue

            registros.append((
                CLIENTE_ID, id_forn, descricao, unidade,
                TIPO_ITEM, preco,
                ncm_id, cfop_id, ORIGEM,
                cst_id, CREATED_BY, True
            ))

        except Exception as e:
            erros.append(f"Linha {i}: {e}")
            continue

    print(f"  {len(registros)} registros válidos, {ignorados} ignorados")

    if not registros:
        print("[AVISO] Nenhum registro para inserir.")
        return

    print(f"\n[6] Inserindo em lote no banco...")
    execute_values(cur, """
        INSERT INTO produtos (
            cliente_id, codigo_interno, descricao, unidade_comercial,
            tipo_item, preco_unitario_padrao,
            ncm_id, cfop_id, origem_mercadoria,
            cst_id, created_by_user_id, ativo
        ) VALUES %s
        ON CONFLICT DO NOTHING
    """, registros, page_size=500)
    conn.commit()
    sucessos = len(registros)

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print(f"  Inseridos com sucesso : {sucessos}")
    print(f"  Ignorados/sem NCM     : {ignorados}")
    print(f"  Erros                 : {len(erros)}")
    if erros:
        print("\nPrimeiros 20 erros:")
        for e in erros[:20]:
            print(f"  {e}")
    print("=" * 60)


if __name__ == '__main__':
    main()

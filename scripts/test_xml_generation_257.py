#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar geração de XML da NFe 257
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import get_connection

def main():
    conn = get_connection()
    cur = conn.cursor()
    
    # Busca NFe 257
    cur.execute("""
        SELECT 
            id, numero, serie, modelo, tipo_emissao, ambiente,
            status, json_nfe, xml_assinado
        FROM nfe_emitidas
        WHERE id = 257
    """)
    
    nfe = cur.fetchone()
    if not nfe:
        print("❌ NFe 257 não encontrada")
        return
    
    print(f"✅ NFe {nfe[1]} encontrada")
    print(f"Status: {nfe[6]}")
    print(f"Ambiente: {nfe[5]}")
    
    # Verifica json_nfe
    import json
    json_nfe = json.loads(nfe[7]) if nfe[7] else {}
    
    print("\n=== Dados do JSON_NFE ===")
    print(f"Emitente ID: {json_nfe.get('emitente_id')}")
    print(f"Destinatário ID: {json_nfe.get('destinatario_id')}")
    print(f"CFOP: {json_nfe.get('cfop_padrao')}")
    print(f"Número de itens: {len(json_nfe.get('itens', []))}")
    
    # Verifica CRT do emitente
    emitente_id = json_nfe.get('emitente_id')
    if emitente_id:
        cur.execute("""
            SELECT c.id, c.razao_social, c.regime_tributario_id, rt.codigo_crt
            FROM clientes c
            LEFT JOIN regimes_tributarios rt ON c.regime_tributario_id = rt.id
            WHERE c.id = %s
        """, (emitente_id,))
        emitente = cur.fetchone()
        if emitente:
            print(f"\n=== Emitente ===")
            print(f"ID: {emitente[0]}")
            print(f"Razão Social: {emitente[1]}")
            print(f"Regime Tributário ID: {emitente[2]}")
            print(f"CRT: {emitente[3]}")
    
    # Verifica destinatário
    dest_id = json_nfe.get('destinatario_id')
    if dest_id:
        cur.execute("""
            SELECT id, razao_social, uf
            FROM destinatarios
            WHERE id = %s
        """, (dest_id,))
        dest = cur.fetchone()
        if dest:
            print(f"\n=== Destinatário ===")
            print(f"ID: {dest[0]}")
            print(f"Razão Social: {dest[1]}")
            print(f"UF: {dest[2]}")
    
    # Verifica itens
    print(f"\n=== Itens ({len(json_nfe.get('itens', []))}) ===")
    for i, item in enumerate(json_nfe.get('itens', []), 1):
        print(f"\nItem {i}:")
        print(f"  Produto ID: {item.get('produto_id')}")
        print(f"  Descrição: {item.get('descricao_produto', 'N/A')[:50]}...")
        print(f"  CFOP: {item.get('cfop')}")
        print(f"  CST ICMS: {item.get('cst_icms')}")
        print(f"  CSOSN ICMS: {item.get('csosn_icms')}")
        print(f"  Origem: {item.get('origem')}")
        
        # Verifica se tem regra de tributação
        if item.get('regra_tributacao_id'):
            cur.execute("""
                SELECT id, cfop_id, cst_icms, csosn_icms
                FROM regras_tributacao
                WHERE id = %s
            """, (item['regra_tributacao_id'],))
            regra = cur.fetchone()
            if regra:
                print(f"  Regra Tributação: {regra[0]} - CST: {regra[2]}, CSOSN: {regra[3]}")
    
    cur.close()
    conn.close()
    
    print("\n" + "="*60)
    print("Diagnóstico:")
    print("- CRT 3 (Lucro Presumido) → DEVE usar CST, NÃO CSOSN")
    print("- CFOP 6108 (interestadual) → ICMS tributado normalmente")
    print("- CST 20 (Redução de Base de Cálculo) → Correto para regime normal")
    print("="*60)

if __name__ == '__main__':
    main()

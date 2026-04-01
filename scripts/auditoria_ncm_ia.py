#!/usr/bin/env python3
"""
Script de Auditoria - NCMs Auto-cadastrados pela IA
====================================================

Identifica produtos com NCMs cadastrados automaticamente pela IA
que precisam de validação manual na SEFAZ/Siscomex.

Autor: Sistema de Auditoria Automática
Data: 2026-03-23
"""

import sys
from pathlib import Path

# Adiciona root ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_db
from sqlalchemy import text
from datetime import datetime
from typing import List, Dict


def buscar_ncms_ia_automatico() -> List[Dict]:
    """Busca NCMs cadastrados automaticamente pela IA"""
    db = next(get_db())
    try:
        resultado = db.execute(text("""
            SELECT 
                n.ncm_id,
                n.codigo,
                n.descricao,
                n.data_atualizacao,
                n.fonte_atualizacao,
                COUNT(p.produto_id) as produtos_usando
            FROM ncms n
            LEFT JOIN produtos p ON n.ncm_id = p.ncm_id
            WHERE n.fonte_atualizacao = 'ia_automatico'
            GROUP BY n.ncm_id, n.codigo, n.descricao, n.data_atualizacao, n.fonte_atualizacao
            ORDER BY n.data_atualizacao DESC
        """)).fetchall()
        
        return [dict(row._mapping) for row in resultado]
    finally:
        db.close()


def buscar_produtos_por_ncm(ncm_id: int) -> List[Dict]:
    """Busca produtos que usam um NCM específico"""
    db = next(get_db())
    try:
        resultado = db.execute(text("""
            SELECT 
                p.produto_id,
                p.cliente_id,
                p.codigo_interno,
                p.descricao,
                p.data_cadastro,
                c.razao_social as cliente_nome
            FROM produtos p
            JOIN clientes c ON p.cliente_id = c.cliente_id
            WHERE p.ncm_id = :ncm_id
            ORDER BY p.data_cadastro DESC
        """), {'ncm_id': ncm_id}).fetchall()
        
        return [dict(row._mapping) for row in resultado]
    finally:
        db.close()


def gerar_relatorio_auditoria():
    """Gera relatório completo de auditoria"""
    print("=" * 80)
    print("RELATÓRIO DE AUDITORIA - NCMs Auto-cadastrados pela IA")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    ncms = buscar_ncms_ia_automatico()
    
    if not ncms:
        print("✅ Nenhum NCM auto-cadastrado pela IA encontrado.")
        print("   Sistema está seguro - todos os NCMs foram validados manualmente.")
        return
    
    print(f"⚠️  {len(ncms)} NCM(s) cadastrado(s) automaticamente pela IA")
    print(f"   Estes NCMs precisam de validação manual na SEFAZ/Siscomex")
    print()
    print("-" * 80)
    
    for idx, ncm in enumerate(ncms, 1):
        print(f"\n{idx}. NCM: {ncm['codigo']}")
        print(f"   ID: {ncm['ncm_id']}")
        print(f"   Descrição: {ncm['descricao']}")
        print(f"   Data Cadastro: {ncm['data_atualizacao'].strftime('%d/%m/%Y %H:%M')}" if ncm['data_atualizacao'] else "   Data Cadastro: N/A")
        print(f"   Produtos Usando: {ncm['produtos_usando']}")
        
        if ncm['produtos_usando'] > 0:
            print(f"\n   📦 Produtos afetados:")
            produtos = buscar_produtos_por_ncm(ncm['ncm_id'])
            for prod in produtos[:5]:  # Limita a 5 produtos
                print(f"      • [{prod['cliente_nome'][:30]}] {prod['descricao'][:50]}")
                print(f"        Código: {prod['codigo_interno']} | ID: {prod['produto_id']}")
            
            if len(produtos) > 5:
                print(f"      ... e mais {len(produtos) - 5} produto(s)")
        
        print(f"\n   🔗 Validar em: https://siscomex.gov.br/")
        print(f"   🔧 Corrigir via: http://100.26.12.107:8080/admin/produtos")
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print("RECOMENDAÇÕES:")
    print("=" * 80)
    print("1. Acesse https://siscomex.gov.br/ e valide cada NCM listado acima")
    print("2. Verifique se o código NCM está vigente e correto")
    print("3. Se NCM estiver INCORRETO:")
    print("   - Edite o produto em http://100.26.12.107:8080/admin/produtos")
    print("   - Altere para o NCM correto")
    print("   - Teste a emissão de NFe em homologação")
    print("4. Se NCM estiver CORRETO:")
    print("   - Atualize fonte_atualizacao para 'validado_manual' via SQL:")
    print("   - UPDATE ncms SET fonte_atualizacao = 'validado_manual' WHERE ncm_id = X;")
    print()
    print("⚠️  IMPORTANTE: Emissões de NFe com NCMs inválidos serão REJEITADAS pela SEFAZ")
    print("=" * 80)


def verificar_ncm_especifico(codigo_ncm: str):
    """Verifica um NCM específico"""
    db = next(get_db())
    try:
        ncm = db.execute(text("""
            SELECT ncm_id, codigo, descricao, fonte_atualizacao, data_atualizacao
            FROM ncms
            WHERE codigo = :codigo
        """), {'codigo': codigo_ncm}).fetchone()
        
        if not ncm:
            print(f"❌ NCM {codigo_ncm} não encontrado no banco de dados")
            return
        
        ncm_dict = dict(ncm._mapping)
        
        print("=" * 80)
        print(f"DETALHES DO NCM: {codigo_ncm}")
        print("=" * 80)
        print(f"ID: {ncm_dict['ncm_id']}")
        print(f"Código: {ncm_dict['codigo']}")
        print(f"Descrição: {ncm_dict['descricao']}")
        print(f"Fonte: {ncm_dict['fonte_atualizacao']}")
        print(f"Data: {ncm_dict['data_atualizacao'].strftime('%d/%m/%Y %H:%M')}" if ncm_dict['data_atualizacao'] else "Data: N/A")
        
        if ncm_dict['fonte_atualizacao'] == 'ia_automatico':
            print("\n⚠️  STATUS: Auto-cadastrado pela IA - REQUER VALIDAÇÃO MANUAL")
            produtos = buscar_produtos_por_ncm(ncm_dict['ncm_id'])
            if produtos:
                print(f"\n📦 {len(produtos)} produto(s) usando este NCM:")
                for prod in produtos:
                    print(f"   • {prod['descricao'][:60]}")
                    print(f"     Cliente: {prod['cliente_nome']}")
                    print(f"     ID: {prod['produto_id']}")
        else:
            print("\n✅ STATUS: Validado manualmente")
        
        print("=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Script de Auditoria - NCMs Auto-cadastrados pela IA"
    )
    parser.add_argument(
        '--ncm',
        type=str,
        help='Verificar um NCM específico (ex: 09011100)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.ncm:
            verificar_ncm_especifico(args.ncm)
        else:
            gerar_relatorio_auditoria()
    except KeyboardInterrupt:
        print("\n\n⚠️  Auditoria interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

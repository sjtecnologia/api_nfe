#!/usr/bin/env python3
"""
Script de Documentação - Regras Tributárias Atuais
===================================================
Exporta todas as regras de PIS/COFINS/ICMS/IPI antes da migração LC 214/2025
Data: 30/11/2025
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import csv
import json

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from database.models import (
    RegraTributacao, Cliente, RegimeTributario,
    Cfop, Ncm, CstIcms, CsosnIcms
)
from sqlalchemy.orm import joinedload

def exportar_regras_tributarias():
    """Exporta todas as regras tributárias para múltiplos formatos"""
    
    print("=" * 60)
    print("  DOCUMENTAÇÃO DE REGRAS TRIBUTÁRIAS - PRÉ LC 214/2025")
    print("=" * 60)
    print()
    
    # Criar diretório de documentação
    doc_dir = Path(__file__).parent.parent / "documentacao" / "pre_lc214"
    doc_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    db = next(get_db())
    
    print("📊 Consultando regras tributárias...")
    
    # Buscar todas as regras (ativas e inativas para histórico completo)
    regras = db.query(RegraTributacao).options(
        joinedload(RegraTributacao.cliente),
        joinedload(RegraTributacao.regime_tributario),
        joinedload(RegraTributacao.cfop),
        joinedload(RegraTributacao.ncm),
        joinedload(RegraTributacao.cst_icms_obj),
        joinedload(RegraTributacao.csosn_icms_obj)
    ).all()
    
    print(f"✓ Encontradas {len(regras)} regras tributárias")
    print()
    
    # 1. Exportar para CSV
    print("[1/4] Exportando para CSV...")
    csv_file = doc_dir / f"regras_tributarias_{timestamp}.csv"
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Cabeçalho
        writer.writerow([
            'ID', 'Descrição', 'Ativo', 'Prioridade',
            'Cliente', 'CNPJ Cliente', 'Regime Tributário',
            'CFOP', 'NCM', 'UF Origem', 'UF Destino', 'Tipo Item',
            'CSOSN ICMS', 'CST ICMS', 'Alíquota ICMS (%)', 
            'Redução Base ICMS (%)', 'Modalidade BC ICMS',
            'CST PIS', 'Alíquota PIS (%)', 
            'CST COFINS', 'Alíquota COFINS (%)',
            'CST IPI', 'Alíquota IPI (%)',
            'Vigência Início', 'Vigência Fim',
            'Observações', 'Criado Em', 'Atualizado Em'
        ])
        
        # Dados
        for regra in regras:
            writer.writerow([
                regra.regra_tributacao_id,
                regra.descricao_regra,
                'Sim' if regra.ativo else 'Não',
                regra.prioridade or 0,
                regra.cliente.razao_social if regra.cliente else 'TODAS',
                regra.cliente.cnpj if regra.cliente else '',
                regra.regime_tributario.nome if regra.regime_tributario else '',
                regra.cfop.cfop if regra.cfop else 'TODOS',
                regra.ncm.codigo if regra.ncm else 'TODOS',
                regra.uf_origem or 'TODAS',
                regra.uf_destino or 'TODAS',
                regra.tipo_item or 'TODOS',
                regra.csosn_icms or '',
                regra.cst_icms or '',
                float(regra.aliquota_icms or 0),
                float(regra.reducao_base_icms or 0),
                regra.modalidade_bc_icms or '',
                regra.cst_pis or '',
                float(regra.aliquota_pis or 0),
                regra.cst_cofins or '',
                float(regra.aliquota_cofins or 0),
                regra.cst_ipi or '',
                float(regra.aliquota_ipi or 0),
                regra.data_inicio_vigencia.strftime('%d/%m/%Y') if regra.data_inicio_vigencia else '',
                regra.data_fim_vigencia.strftime('%d/%m/%Y') if regra.data_fim_vigencia else '',
                regra.observacoes or '',
                regra.created_at.strftime('%d/%m/%Y %H:%M') if regra.created_at else '',
                regra.updated_at.strftime('%d/%m/%Y %H:%M') if regra.updated_at else ''
            ])
    
    print(f"   ✓ Arquivo CSV: {csv_file.name}")
    
    # 2. Exportar para JSON
    print("[2/4] Exportando para JSON...")
    json_file = doc_dir / f"regras_tributarias_{timestamp}.json"
    
    regras_json = []
    for regra in regras:
        regras_json.append({
            'id': regra.regra_tributacao_id,
            'descricao': regra.descricao_regra,
            'ativo': regra.ativo,
            'prioridade': regra.prioridade,
            'cliente': {
                'id': regra.cliente.cliente_id if regra.cliente else None,
                'razao_social': regra.cliente.razao_social if regra.cliente else None,
                'cnpj': regra.cliente.cnpj if regra.cliente else None
            },
            'regime_tributario': {
                'id': regra.regime_tributario.regime_tributario_id if regra.regime_tributario else None,
                'nome': regra.regime_tributario.nome if regra.regime_tributario else None
            },
            'cfop': {
                'id': regra.cfop.cfop_id if regra.cfop else None,
                'codigo': regra.cfop.cfop if regra.cfop else None,
                'descricao': regra.cfop.descricao if regra.cfop else None
            },
            'ncm': {
                'id': regra.ncm.ncm_id if regra.ncm else None,
                'codigo': regra.ncm.codigo if regra.ncm else None,
                'descricao': regra.ncm.descricao if regra.ncm else None
            },
            'filtros': {
                'uf_origem': regra.uf_origem,
                'uf_destino': regra.uf_destino,
                'tipo_item': regra.tipo_item
            },
            'icms': {
                'csosn': regra.csosn_icms,
                'cst': regra.cst_icms,
                'aliquota': float(regra.aliquota_icms or 0),
                'reducao_base': float(regra.reducao_base_icms or 0),
                'modalidade_bc': regra.modalidade_bc_icms
            },
            'pis': {
                'cst': regra.cst_pis,
                'aliquota': float(regra.aliquota_pis or 0)
            },
            'cofins': {
                'cst': regra.cst_cofins,
                'aliquota': float(regra.aliquota_cofins or 0)
            },
            'ipi': {
                'cst': regra.cst_ipi,
                'aliquota': float(regra.aliquota_ipi or 0)
            },
            'vigencia': {
                'inicio': regra.data_inicio_vigencia.isoformat() if regra.data_inicio_vigencia else None,
                'fim': regra.data_fim_vigencia.isoformat() if regra.data_fim_vigencia else None
            },
            'observacoes': regra.observacoes,
            'metadados': {
                'criado_em': regra.created_at.isoformat() if regra.created_at else None,
                'atualizado_em': regra.updated_at.isoformat() if regra.updated_at else None
            }
        })
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(regras_json, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ Arquivo JSON: {json_file.name}")
    
    # 3. Gerar relatório em Markdown
    print("[3/4] Gerando relatório Markdown...")
    md_file = doc_dir / f"RELATORIO_REGRAS_{timestamp}.md"
    
    # Estatísticas
    regras_ativas = [r for r in regras if r.ativo]
    regras_por_regime = {}
    for regra in regras_ativas:
        regime = regra.regime_tributario.nome if regra.regime_tributario else 'Sem regime'
        regras_por_regime[regime] = regras_por_regime.get(regime, 0) + 1
    
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# Relatório de Regras Tributárias\n\n")
        f.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
        f.write(f"**Status:** Pré-Migração LC 214/2025\n\n")
        f.write("---\n\n")
        
        f.write("## 📊 Estatísticas Gerais\n\n")
        f.write(f"- **Total de Regras:** {len(regras)}\n")
        f.write(f"- **Regras Ativas:** {len(regras_ativas)}\n")
        f.write(f"- **Regras Inativas:** {len(regras) - len(regras_ativas)}\n\n")
        
        f.write("### Distribuição por Regime Tributário\n\n")
        for regime, count in sorted(regras_por_regime.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- **{regime}:** {count} regras\n")
        f.write("\n---\n\n")
        
        f.write("## 📋 Regras Ativas Detalhadas\n\n")
        
        for regra in sorted(regras_ativas, key=lambda r: (
            r.regime_tributario.nome if r.regime_tributario else '',
            r.prioridade or 0
        ), reverse=True):
            f.write(f"### Regra #{regra.regra_tributacao_id}: {regra.descricao_regra}\n\n")
            f.write(f"**Prioridade:** {regra.prioridade or 'Não definida'}\n\n")
            
            if regra.cliente:
                f.write(f"**Cliente Específico:** {regra.cliente.razao_social} (CNPJ: {regra.cliente.cnpj})\n\n")
            else:
                f.write(f"**Aplicação:** Todos os clientes\n\n")
            
            f.write("**Critérios:**\n")
            f.write(f"- Regime: {regra.regime_tributario.nome if regra.regime_tributario else 'Não especificado'}\n")
            f.write(f"- CFOP: {regra.cfop.cfop if regra.cfop else 'Todos'}\n")
            f.write(f"- NCM: {regra.ncm.codigo if regra.ncm else 'Todos'}\n")
            f.write(f"- UF Origem: {regra.uf_origem or 'Todas'}\n")
            f.write(f"- UF Destino: {regra.uf_destino or 'Todas'}\n")
            f.write(f"- Tipo Item: {regra.tipo_item or 'Todos'}\n\n")
            
            f.write("**Tributação:**\n")
            if regra.csosn_icms or regra.cst_icms:
                f.write(f"- ICMS: {regra.csosn_icms or regra.cst_icms} - {regra.aliquota_icms or 0}%\n")
            if regra.cst_pis:
                f.write(f"- PIS: {regra.cst_pis} - {regra.aliquota_pis or 0}%\n")
            if regra.cst_cofins:
                f.write(f"- COFINS: {regra.cst_cofins} - {regra.aliquota_cofins or 0}%\n")
            if regra.cst_ipi:
                f.write(f"- IPI: {regra.cst_ipi} - {regra.aliquota_ipi or 0}%\n")
            
            f.write("\n---\n\n")
    
    print(f"   ✓ Relatório Markdown: {md_file.name}")
    
    # 4. Gerar SQL de recriação
    print("[4/4] Gerando script SQL de recriação...")
    sql_file = doc_dir / f"RECREATE_REGRAS_{timestamp}.sql"
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write("-- ============================================\n")
        f.write("-- Script de Recriação - Regras Tributárias\n")
        f.write(f"-- Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        f.write("-- Status: Pré-Migração LC 214/2025\n")
        f.write("-- ============================================\n\n")
        f.write("-- ATENÇÃO: Este script recria TODAS as regras tributárias\n")
        f.write("-- Use apenas para restauração ou auditoria\n\n")
        
        f.write("BEGIN;\n\n")
        
        for regra in regras:
            f.write(f"-- Regra #{regra.regra_tributacao_id}: {regra.descricao_regra}\n")
            f.write("INSERT INTO regras_tributacao (\n")
            f.write("    regra_tributacao_id, descricao_regra, ativo, prioridade,\n")
            f.write("    cliente_id, regime_tributario_id, cfop_id, ncm_id,\n")
            f.write("    uf_origem, uf_destino, tipo_item,\n")
            f.write("    csosn_icms, cst_icms, aliquota_icms, reducao_base_icms, modalidade_bc_icms,\n")
            f.write("    cst_pis, aliquota_pis,\n")
            f.write("    cst_cofins, aliquota_cofins,\n")
            f.write("    cst_ipi, aliquota_ipi,\n")
            f.write("    data_inicio_vigencia, data_fim_vigencia, observacoes\n")
            f.write(") VALUES (\n")
            f.write(f"    {regra.regra_tributacao_id}, '{regra.descricao_regra}', {regra.ativo}, {regra.prioridade or 'NULL'},\n")
            f.write(f"    {regra.cliente_id or 'NULL'}, {regra.regime_tributario_id or 'NULL'}, ")
            f.write(f"{regra.cfop_id or 'NULL'}, {regra.ncm_id or 'NULL'},\n")
            f.write(f"    {repr(regra.uf_origem) if regra.uf_origem else 'NULL'}, ")
            f.write(f"{repr(regra.uf_destino) if regra.uf_destino else 'NULL'}, ")
            f.write(f"{repr(regra.tipo_item) if regra.tipo_item else 'NULL'},\n")
            f.write(f"    {repr(regra.csosn_icms) if regra.csosn_icms else 'NULL'}, ")
            f.write(f"{repr(regra.cst_icms) if regra.cst_icms else 'NULL'}, ")
            f.write(f"{regra.aliquota_icms or 0}, {regra.reducao_base_icms or 0}, ")
            f.write(f"{regra.modalidade_bc_icms or 'NULL'},\n")
            f.write(f"    {repr(regra.cst_pis) if regra.cst_pis else 'NULL'}, {regra.aliquota_pis or 0},\n")
            f.write(f"    {repr(regra.cst_cofins) if regra.cst_cofins else 'NULL'}, {regra.aliquota_cofins or 0},\n")
            f.write(f"    {repr(regra.cst_ipi) if regra.cst_ipi else 'NULL'}, {regra.aliquota_ipi or 0},\n")
            f.write(f"    {repr(regra.data_inicio_vigencia.strftime('%Y-%m-%d')) if regra.data_inicio_vigencia else 'NULL'}, ")
            f.write(f"{repr(regra.data_fim_vigencia.strftime('%Y-%m-%d')) if regra.data_fim_vigencia else 'NULL'}, ")
            f.write(f"{repr(regra.observacoes) if regra.observacoes else 'NULL'}\n")
            f.write(");\n\n")
        
        f.write("COMMIT;\n")
    
    print(f"   ✓ Script SQL: {sql_file.name}")
    
    print()
    print("=" * 60)
    print("  ✅ DOCUMENTAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print()
    print(f"📁 Arquivos gerados em: {doc_dir}")
    print()
    print("Arquivos criados:")
    print(f"  1. {csv_file.name} (planilha)")
    print(f"  2. {json_file.name} (dados estruturados)")
    print(f"  3. {md_file.name} (relatório legível)")
    print(f"  4. {sql_file.name} (script de recriação)")
    print()
    print(f"Total de regras documentadas: {len(regras)}")
    print(f"Regras ativas: {len(regras_ativas)}")
    print()

if __name__ == '__main__':
    try:
        exportar_regras_tributarias()
    except Exception as e:
        print(f"\n❌ Erro ao exportar regras: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

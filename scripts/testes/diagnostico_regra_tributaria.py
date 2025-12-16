#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar regras tributárias
Ajuda a identificar porque uma regra não está sendo encontrada
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.connection import get_db
from database.models import RegraTributacao, Cliente, Cfop, Ncm, RegimeTributario
from sqlalchemy import text, or_

def diagnosticar_busca_regra():
    """Diagnostica por que uma regra tributária não está sendo encontrada"""
    
    print("=" * 80)
    print("DIAGNÓSTICO DE REGRAS TRIBUTÁRIAS")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        # Solicitar dados do usuário
        print("\n📋 Digite os dados para buscar a regra:")
        cliente_id = input("Cliente ID (ou Enter para pular): ").strip()
        if cliente_id:
            cliente_id = int(cliente_id)
            
        cfop_codigo = input("Código CFOP (ex: 5101): ").strip()
        ncm_codigo = input("Código NCM (ex: 85285900): ").strip()
        uf_origem = input("UF Origem (ex: SP): ").strip().upper()
        uf_destino = input("UF Destino (ex: SP): ").strip().upper()
        
        print("\n" + "=" * 80)
        print("ETAPA 1: Verificando dados do cliente")
        print("=" * 80)
        
        if cliente_id:
            cliente = db.query(Cliente).filter(Cliente.cliente_id == cliente_id).first()
            if cliente:
                print(f"✅ Cliente encontrado: {cliente.razao_social}")
                print(f"   CNPJ: {cliente.cnpj}")
                print(f"   UF: {cliente.uf}")
                print(f"   Regime Tributário ID: {cliente.regime_tributario_id}")
                
                regime = db.query(RegimeTributario).filter(
                    RegimeTributario.regime_tributario_id == cliente.regime_tributario_id
                ).first()
                if regime:
                    print(f"   Regime: {regime.nome}")
                    regime_tributario_id = cliente.regime_tributario_id
                else:
                    print("   ⚠️ Regime tributário não encontrado!")
                    regime_tributario_id = None
            else:
                print(f"❌ Cliente ID {cliente_id} não encontrado!")
                return
        else:
            print("⚠️ Sem cliente específico, buscando regras gerais")
            regime_tributario_id = None
        
        print("\n" + "=" * 80)
        print("ETAPA 2: Verificando CFOP")
        print("=" * 80)
        
        cfop_obj = None
        if cfop_codigo:
            cfop_obj = db.query(Cfop).filter(Cfop.cfop == cfop_codigo).first()
            if cfop_obj:
                print(f"✅ CFOP encontrado: {cfop_obj.cfop} - {cfop_obj.descricao}")
                print(f"   ID: {cfop_obj.cfop_id}")
            else:
                print(f"❌ CFOP {cfop_codigo} não encontrado no banco!")
        else:
            print("⚠️ CFOP não informado")
        
        print("\n" + "=" * 80)
        print("ETAPA 3: Verificando NCM")
        print("=" * 80)
        
        ncm_obj = None
        if ncm_codigo:
            ncm_obj = db.query(Ncm).filter(Ncm.codigo == ncm_codigo).first()
            if ncm_obj:
                print(f"✅ NCM encontrado: {ncm_obj.codigo} - {ncm_obj.descricao}")
                print(f"   ID: {ncm_obj.ncm_id}")
            else:
                print(f"❌ NCM {ncm_codigo} não encontrado no banco!")
        else:
            print("⚠️ NCM não informado")
        
        print("\n" + "=" * 80)
        print("ETAPA 4: Buscando regras compatíveis")
        print("=" * 80)
        
        # Construir query base
        query = db.query(RegraTributacao).filter(RegraTributacao.ativo == True)
        
        # Filtro de cliente
        if cliente_id:
            query_cliente = query.filter(
                or_(
                    RegraTributacao.cliente_id == cliente_id,
                    RegraTributacao.cliente_id.is_(None)
                )
            )
        else:
            query_cliente = query.filter(RegraTributacao.cliente_id.is_(None))
        
        regras_por_cliente = query_cliente.all()
        print(f"\n1️⃣ Regras após filtro de CLIENTE: {len(regras_por_cliente)} encontradas")
        if regras_por_cliente:
            for r in regras_por_cliente[:5]:  # Mostrar apenas 5
                print(f"   - ID {r.regra_tributacao_id}: {r.descricao_regra}")
        
        # Filtro de regime tributário
        if regime_tributario_id:
            query_regime = query_cliente.filter(
                RegraTributacao.regime_tributario_id == regime_tributario_id
            )
            regras_por_regime = query_regime.all()
            print(f"\n2️⃣ Regras após filtro de REGIME TRIBUTÁRIO ({regime_tributario_id}): {len(regras_por_regime)} encontradas")
            if regras_por_regime:
                for r in regras_por_regime[:5]:
                    print(f"   - ID {r.regra_tributacao_id}: {r.descricao_regra}")
        else:
            query_regime = query_cliente
            print(f"\n2️⃣ Sem filtro de regime tributário")
        
        # Filtro de CFOP
        if cfop_codigo and cfop_obj:
            query_cfop = query_regime.filter(
                or_(
                    RegraTributacao.cfop_id == cfop_obj.cfop_id,
                    RegraTributacao.cfop_id.is_(None)
                )
            )
            regras_por_cfop = query_cfop.all()
            print(f"\n3️⃣ Regras após filtro de CFOP ({cfop_codigo}): {len(regras_por_cfop)} encontradas")
            if regras_por_cfop:
                for r in regras_por_cfop[:5]:
                    cfop_nome = r.cfop.cfop if r.cfop else "Genérico"
                    print(f"   - ID {r.regra_tributacao_id}: {r.descricao_regra} (CFOP: {cfop_nome})")
        else:
            query_cfop = query_regime
            print(f"\n3️⃣ Sem filtro de CFOP")
        
        # Filtro de NCM
        if ncm_codigo and ncm_obj:
            query_ncm = query_cfop.filter(
                or_(
                    RegraTributacao.ncm_id == ncm_obj.ncm_id,
                    RegraTributacao.ncm_id.is_(None)
                )
            )
            regras_por_ncm = query_ncm.all()
            print(f"\n4️⃣ Regras após filtro de NCM ({ncm_codigo}): {len(regras_por_ncm)} encontradas")
            if regras_por_ncm:
                for r in regras_por_ncm[:5]:
                    ncm_nome = r.ncm.codigo if r.ncm else "Genérico"
                    print(f"   - ID {r.regra_tributacao_id}: {r.descricao_regra} (NCM: {ncm_nome})")
        else:
            query_ncm = query_cfop
            print(f"\n4️⃣ Sem filtro de NCM")
        
        # Filtro de UF
        if uf_origem:
            query_uf = query_ncm.filter(
                or_(
                    RegraTributacao.uf_origem == uf_origem,
                    RegraTributacao.uf_origem.is_(None)
                )
            )
            if uf_destino:
                query_uf = query_uf.filter(
                    or_(
                        RegraTributacao.uf_destino == uf_destino,
                        RegraTributacao.uf_destino.is_(None)
                    )
                )
            regras_por_uf = query_uf.all()
            print(f"\n5️⃣ Regras após filtro de UF ({uf_origem} → {uf_destino}): {len(regras_por_uf)} encontradas")
            if regras_por_uf:
                for r in regras_por_uf[:5]:
                    uf_info = f"{r.uf_origem or 'Todas'} → {r.uf_destino or 'Todas'}"
                    print(f"   - ID {r.regra_tributacao_id}: {r.descricao_regra} (UF: {uf_info})")
        else:
            query_uf = query_ncm
            print(f"\n5️⃣ Sem filtro de UF")
        
        # Ordenar por prioridade
        query_final = query_uf.order_by(
            RegraTributacao.cliente_id.desc(),
            RegraTributacao.prioridade.desc()
        )
        
        regra_final = query_final.first()
        
        print("\n" + "=" * 80)
        print("RESULTADO FINAL")
        print("=" * 80)
        
        if regra_final:
            print(f"\n✅ REGRA ENCONTRADA!")
            print(f"   ID: {regra_final.regra_tributacao_id}")
            print(f"   Descrição: {regra_final.descricao_regra}")
            print(f"   Prioridade: {regra_final.prioridade}")
            print(f"   Cliente ID: {regra_final.cliente_id or 'Genérico'}")
            print(f"   Regime: {regra_final.regime_tributario.nome if regra_final.regime_tributario else 'N/A'}")
            print(f"   CFOP: {regra_final.cfop.cfop if regra_final.cfop else 'Genérico'}")
            print(f"   NCM: {regra_final.ncm.codigo if regra_final.ncm else 'Genérico'}")
            print(f"   UF: {regra_final.uf_origem or 'Todas'} → {regra_final.uf_destino or 'Todas'}")
            print(f"\n   💰 TRIBUTOS:")
            print(f"   ICMS: {regra_final.aliquota_icms}% | CSOSN: {regra_final.csosn_icms} | CST: {regra_final.cst_icms}")
            print(f"   PIS: {regra_final.aliquota_pis}% | CST: {regra_final.cst_pis}")
            print(f"   COFINS: {regra_final.aliquota_cofins}% | CST: {regra_final.cst_cofins}")
            print(f"   IPI: {regra_final.aliquota_ipi}% | CST: {regra_final.cst_ipi}")
        else:
            print("\n❌ NENHUMA REGRA ENCONTRADA!")
            print("\n💡 POSSÍVEIS CAUSAS:")
            print("   1. Regime tributário do cliente não possui regras cadastradas")
            print("   2. CFOP ou NCM não estão cadastrados no banco")
            print("   3. Combinação específica de filtros não tem regra correspondente")
            print("   4. Regra existe mas está inativa")
            print("\n💡 SUGESTÕES:")
            print("   1. Cadastre uma regra GENÉRICA (sem CFOP/NCM específicos)")
            print("   2. Verifique se o regime tributário está correto")
            print("   3. Verifique se CFOP e NCM estão cadastrados")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnosticar_busca_regra()

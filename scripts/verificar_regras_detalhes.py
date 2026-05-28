#!/usr/bin/env python3
"""
Verificar Detalhes das Regras do Cliente 13
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import RegraTributacao, Ncm, Cfop
from sqlalchemy.orm import joinedload

def main():
    print("\n" + "="*80)
    print("🔍 DETALHES DAS REGRAS DO CLIENTE 13")
    print("="*80 + "\n")
    
    db = SessionLocal()
    
    try:
        regras = db.query(RegraTributacao).options(
            joinedload(RegraTributacao.ncm),
            joinedload(RegraTributacao.cfop)
        ).filter(
            RegraTributacao.cliente_id == 13
        ).order_by(RegraTributacao.prioridade.desc()).all()
        
        print(f"📊 Total de regras: {len(regras)}\n")
        
        for regra in regras:
            print(f"🔹 Regra ID {regra.regra_tributacao_id} | Prioridade: {regra.prioridade}")
            print(f"   Descrição: {regra.descricao_regra}")
            print(f"   CFOP: {regra.cfop.cfop if regra.cfop else 'TODOS'} (ID: {regra.cfop_id})")
            print(f"   NCM: {regra.ncm.codigo if regra.ncm else 'TODOS'} (ID: {regra.ncm_id})")
            print(f"   UF: {regra.uf_origem or 'TODAS'} → {regra.uf_destino or 'TODAS'}")
            print(f"   ICMS: {regra.csosn_icms or regra.cst_icms} | PIS: {regra.cst_pis} | COFINS: {regra.cst_cofins} | IPI: {regra.cst_ipi}")
            print()
        
        # Verificar se NCMs existem
        print("="*80)
        print("🔍 VERIFICANDO NCMs NO BANCO")
        print("="*80 + "\n")
        
        ncms_test = ['84713000', '84182100', '22011000']
        for codigo in ncms_test:
            ncm = db.query(Ncm).filter(Ncm.codigo == codigo).first()
            if ncm:
                print(f"✅ NCM {codigo}: ID {ncm.ncm_id} - {ncm.descricao}")
            else:
                print(f"❌ NCM {codigo}: NÃO ENCONTRADO NO BANCO")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    main()

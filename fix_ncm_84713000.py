#!/usr/bin/env python3
"""
Cadastrar NCM 84713000 e atualizar regra
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import Ncm, RegraTributacao

def main():
    print("\n" + "="*80)
    print("🔧 CORRIGINDO NCM 84713000")
    print("="*80 + "\n")
    
    db = SessionLocal()
    
    try:
        # 1. Verificar se NCM já existe
        ncm = db.query(Ncm).filter(Ncm.codigo == '84713000').first()
        
        if not ncm:
            print("📝 Criando NCM 84713000...")
            ncm = Ncm(
                codigo='84713000',
                descricao='Máquinas automáticas para processamento de dados, portáteis'
            )
            db.add(ncm)
            db.flush()
            print(f"✅ NCM criado com ID: {ncm.ncm_id}")
        else:
            print(f"✅ NCM já existe: ID {ncm.ncm_id}")
        
        # 2. Atualizar regra ID 19
        regra_19 = db.query(RegraTributacao).filter(
            RegraTributacao.regra_tributacao_id == 19
        ).first()
        
        if regra_19:
            print(f"\n📝 Atualizando regra ID 19...")
            print(f"   Antes: NCM ID: {regra_19.ncm_id}")
            regra_19.ncm_id = ncm.ncm_id
            print(f"   Depois: NCM ID: {regra_19.ncm_id}")
        
        db.commit()
        
        print("\n" + "="*80)
        print("✅ CORREÇÃO CONCLUÍDA!")
        print("="*80)
        
        # Verificar resultado
        regra_19 = db.query(RegraTributacao).filter(
            RegraTributacao.regra_tributacao_id == 19
        ).first()
        
        if regra_19 and regra_19.ncm_id:
            print(f"\n✅ Regra 19 agora está vinculada ao NCM {ncm.codigo}")
        else:
            print(f"\n⚠️ Algo deu errado!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    main()

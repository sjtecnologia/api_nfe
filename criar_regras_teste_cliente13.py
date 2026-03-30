#!/usr/bin/env python3
"""
Criar Regras de Teste para Cliente 13
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import RegraTributacao, Cfop, Ncm, Cliente
from sqlalchemy import text

def main():
    print("\n" + "="*80)
    print("📝 CRIANDO REGRAS DE TESTE PARA CLIENTE 13")
    print("="*80 + "\n")
    
    db = SessionLocal()
    
    try:
        # Verificar se cliente existe
        cliente = db.query(Cliente).filter(Cliente.cliente_id == 13).first()
        if not cliente:
            print("❌ Cliente 13 não encontrado!")
            return
        
        print(f"✅ Cliente: {cliente.razao_social}")
        print(f"   Regime: Simples Nacional (ID: 1)")
        print(f"   UF: {cliente.uf}")
        print()
        
        # Buscar CFOPs necessários
        cfop_5102 = db.query(Cfop).filter(Cfop.cfop == '5102').first()
        cfop_6102 = db.query(Cfop).filter(Cfop.cfop == '6102').first()
        cfop_5405 = db.query(Cfop).filter(Cfop.cfop == '5405').first()
        
        # NCMs para teste
        ncm_computador = db.query(Ncm).filter(Ncm.codigo == '84713000').first()
        ncm_geladeira = db.query(Ncm).filter(Ncm.codigo == '84182100').first()
        
        regras = [
            {
                "descricao": "Venda Estadual - Produtos Genéricos (CFOP 5102)",
                "cfop_id": cfop_5102.cfop_id if cfop_5102 else None,
                "ncm_id": None,  # Genérico - todos os NCMs
                "uf_origem": "SP",
                "uf_destino": "SP",
                "csosn_icms": "102",  # Tributada sem permissão de crédito
                "aliquota_icms": 0,
                "cst_pis": "99",
                "aliquota_pis": 0,
                "cst_cofins": "99",
                "aliquota_cofins": 0,
                "cst_ipi": "99",
                "aliquota_ipi": 0,
                "prioridade": 50
            },
            {
                "descricao": "Venda Interestadual - Produtos Genéricos (CFOP 6102)",
                "cfop_id": cfop_6102.cfop_id if cfop_6102 else None,
                "ncm_id": None,
                "uf_origem": "SP",
                "uf_destino": None,  # Qualquer UF destino
                "csosn_icms": "102",
                "aliquota_icms": 0,
                "cst_pis": "99",
                "aliquota_pis": 0,
                "cst_cofins": "99",
                "aliquota_cofins": 0,
                "cst_ipi": "99",
                "aliquota_ipi": 0,
                "prioridade": 40
            },
            {
                "descricao": "Venda Estadual - Computadores (NCM 84713000)",
                "cfop_id": cfop_5102.cfop_id if cfop_5102 else None,
                "ncm_id": ncm_computador.ncm_id if ncm_computador else None,
                "uf_origem": "SP",
                "uf_destino": "SP",
                "csosn_icms": "102",
                "aliquota_icms": 0,
                "cst_pis": "99",
                "aliquota_pis": 0,
                "cst_cofins": "99",
                "aliquota_cofins": 0,
                "cst_ipi": "99",
                "aliquota_ipi": 0,
                "prioridade": 80
            },
            {
                "descricao": "Venda Estadual - Geladeiras com IPI (NCM 84182100)",
                "cfop_id": cfop_5102.cfop_id if cfop_5102 else None,
                "ncm_id": ncm_geladeira.ncm_id if ncm_geladeira else None,
                "uf_origem": "SP",
                "uf_destino": "SP",
                "csosn_icms": "102",
                "aliquota_icms": 0,
                "cst_pis": "99",
                "aliquota_pis": 0,
                "cst_cofins": "99",
                "aliquota_cofins": 0,
                "cst_ipi": "50",  # IPI aplicado
                "aliquota_ipi": 5.0,  # 5% de IPI
                "prioridade": 90
            },
            {
                "descricao": "Venda de Bebidas - CFOP 5405 (Genérico)",
                "cfop_id": cfop_5405.cfop_id if cfop_5405 else None,
                "ncm_id": None,
                "uf_origem": "SP",
                "uf_destino": "SP",
                "csosn_icms": "102",
                "aliquota_icms": 0,
                "cst_pis": "99",
                "aliquota_pis": 0,
                "cst_cofins": "99",
                "aliquota_cofins": 0,
                "cst_ipi": "99",
                "aliquota_ipi": 0,
                "prioridade": 70
            }
        ]
        
        print("📋 Criando regras...")
        print("-" * 80)
        
        criadas = 0
        for dados in regras:
            # Verificar se regra similar já existe
            query = db.query(RegraTributacao).filter(
                RegraTributacao.cliente_id == 13,
                RegraTributacao.descricao_regra == dados["descricao"]
            )
            
            existe = query.first()
            if existe:
                print(f"⏭️  Regra já existe: {dados['descricao']}")
                continue
            
            nova_regra = RegraTributacao(
                cliente_id=13,
                regime_tributario_id=1,  # Simples Nacional
                cfop_id=dados["cfop_id"],
                ncm_id=dados["ncm_id"],
                uf_origem=dados["uf_origem"],
                uf_destino=dados["uf_destino"],
                tipo_item="Produto",
                prioridade=dados["prioridade"],
                csosn_icms=dados["csosn_icms"],
                aliquota_icms=dados["aliquota_icms"],
                cst_pis=dados["cst_pis"],
                aliquota_pis=dados["aliquota_pis"],
                cst_cofins=dados["cst_cofins"],
                aliquota_cofins=dados["aliquota_cofins"],
                cst_ipi=dados["cst_ipi"],
                aliquota_ipi=dados["aliquota_ipi"],
                descricao_regra=dados["descricao"],
                ativo=True
            )
            
            db.add(nova_regra)
            db.flush()
            
            print(f"✅ Criada: {dados['descricao']}")
            print(f"   ID: {nova_regra.regra_tributacao_id} | Prioridade: {dados['prioridade']}")
            criadas += 1
        
        db.commit()
        
        print()
        print("="*80)
        print(f"✅ {criadas} regra(s) criada(s) com sucesso!")
        print("="*80)
        
        # Listar todas as regras do cliente
        print("\n📋 TODAS AS REGRAS DO CLIENTE 13:")
        print("-" * 80)
        
        todas_regras = db.query(RegraTributacao).filter(
            RegraTributacao.cliente_id == 13,
            RegraTributacao.ativo == True
        ).order_by(RegraTributacao.prioridade.desc()).all()
        
        for regra in todas_regras:
            cfop_nome = regra.cfop.cfop if regra.cfop else "TODOS"
            ncm_nome = regra.ncm.codigo if regra.ncm else "TODOS"
            print(f"\n• ID {regra.regra_tributacao_id} [{regra.prioridade}]: {regra.descricao_regra}")
            print(f"  CFOP: {cfop_nome} | NCM: {ncm_nome}")
            print(f"  UF: {regra.uf_origem or 'TODAS'} → {regra.uf_destino or 'TODAS'}")
            print(f"  ICMS: {regra.csosn_icms or regra.cst_icms} ({regra.aliquota_icms or 0}%)")
            print(f"  PIS: {regra.cst_pis} ({regra.aliquota_pis or 0}%) | COFINS: {regra.cst_cofins} ({regra.aliquota_cofins or 0}%)")
            if regra.cst_ipi:
                print(f"  IPI: {regra.cst_ipi} ({regra.aliquota_ipi or 0}%)")
        
        print("\n" + "="*80)
        print("🎯 Agora você pode testar a API com payload simplificado!")
        print("="*80)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()

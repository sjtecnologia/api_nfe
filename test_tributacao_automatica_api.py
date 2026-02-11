#!/usr/bin/env python3
"""
Script de Teste - Tributação Automática via API v2
Cliente ID: 13
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import Cliente, RegraTributacao, Cfop, Ncm, RegimeTributario
from sqlalchemy import text
import json

def main():
    print("\n" + "="*80)
    print("🧪 TESTE - TRIBUTAÇÃO AUTOMÁTICA API v2")
    print("="*80 + "\n")
    
    db = SessionLocal()
    
    try:
        # =====================================================================
        # 1. VERIFICAR DADOS DO CLIENTE 13
        # =====================================================================
        print("📊 1. VERIFICANDO DADOS DO CLIENTE 13...")
        print("-" * 80)
        
        cliente = db.query(Cliente).filter(Cliente.cliente_id == 13).first()
        
        if not cliente:
            print("❌ Cliente 13 não encontrado!")
            return
        
        print(f"✅ Cliente encontrado:")
        print(f"   ID: {cliente.cliente_id}")
        print(f"   Razão Social: {cliente.razao_social}")
        print(f"   CNPJ: {cliente.cnpj}")
        print(f"   UF: {cliente.uf}")
        print(f"   Regime Tributário ID: {cliente.regime_tributario_id}")
        
        # Buscar regime tributário
        if cliente.regime_tributario_id:
            regime = db.query(RegimeTributario).filter(
                RegimeTributario.regime_tributario_id == cliente.regime_tributario_id
            ).first()
            if regime:
                print(f"   Regime: {regime.nome}")
        
        print()
        
        # =====================================================================
        # 2. VERIFICAR REGRAS TRIBUTÁRIAS DO CLIENTE
        # =====================================================================
        print("📋 2. VERIFICANDO REGRAS TRIBUTÁRIAS CADASTRADAS...")
        print("-" * 80)
        
        # Regras específicas do cliente
        regras_cliente = db.query(RegraTributacao).filter(
            RegraTributacao.cliente_id == 13,
            RegraTributacao.ativo == True
        ).all()
        
        print(f"\n🔹 Regras ESPECÍFICAS do cliente: {len(regras_cliente)}")
        for regra in regras_cliente[:5]:  # Mostrar até 5
            cfop_nome = regra.cfop.cfop if regra.cfop else "TODOS"
            ncm_nome = regra.ncm.codigo if regra.ncm else "TODOS"
            print(f"   • ID {regra.regra_tributacao_id}: {regra.descricao_regra}")
            print(f"     CFOP: {cfop_nome} | NCM: {ncm_nome} | UF: {regra.uf_origem or 'TODAS'} → {regra.uf_destino or 'TODAS'}")
            print(f"     {regra.csosn_icms or regra.cst_icms} | PIS: {regra.cst_pis} | COFINS: {regra.cst_cofins}")
        
        # Regras genéricas
        regras_genericas = db.query(RegraTributacao).filter(
            RegraTributacao.cliente_id.is_(None),
            RegraTributacao.ativo == True
        ).all()
        
        print(f"\n🔹 Regras GENÉRICAS (todos): {len(regras_genericas)}")
        for regra in regras_genericas[:5]:
            cfop_nome = regra.cfop.cfop if regra.cfop else "TODOS"
            ncm_nome = regra.ncm.codigo if regra.ncm else "TODOS"
            print(f"   • ID {regra.regra_tributacao_id}: {regra.descricao_regra}")
            print(f"     CFOP: {cfop_nome} | NCM: {ncm_nome}")
        
        total_regras = len(regras_cliente) + len(regras_genericas)
        
        if total_regras == 0:
            print("\n⚠️  ATENÇÃO: Nenhuma regra tributária cadastrada!")
            print("   Para testar, você precisa cadastrar pelo menos uma regra.")
            print("   Acesse: Admin > Regras de Tributação > Criar Nova")
            print()
            
            # Sugerir criação de regra de teste
            print("💡 SUGESTÃO: Criar regra de teste")
            criar = input("   Deseja criar uma regra de teste automaticamente? (s/n): ")
            
            if criar.lower() == 's':
                criar_regra_teste(db, cliente)
        
        print()
        
        # =====================================================================
        # 3. TESTAR BUSCA AUTOMÁTICA DE REGRAS
        # =====================================================================
        print("🔍 3. TESTANDO BUSCA AUTOMÁTICA DE REGRAS...")
        print("-" * 80)
        
        # Cenários de teste
        cenarios = [
            {
                "nome": "Venda Estadual - NCM Genérico",
                "ncm": "84713000",
                "cfop": "5102",
                "uf_destino": cliente.uf,
                "tipo_item": "Produto"
            },
            {
                "nome": "Venda Interestadual",
                "ncm": "84713000",
                "cfop": "6102",
                "uf_destino": "RJ" if cliente.uf != "RJ" else "SP",
                "tipo_item": "Produto"
            },
            {
                "nome": "Produto com IPI",
                "ncm": "84182100",  # Refrigerador
                "cfop": "5102",
                "uf_destino": cliente.uf,
                "tipo_item": "Produto"
            }
        ]
        
        for idx, cenario in enumerate(cenarios, 1):
            print(f"\n{idx}. {cenario['nome']}")
            print(f"   NCM: {cenario['ncm']} | CFOP: {cenario['cfop']} | UF Destino: {cenario['uf_destino']}")
            
            # Simular busca de regra (mesma lógica da API)
            from sqlalchemy import or_
            from sqlalchemy.orm import joinedload
            
            query = db.query(RegraTributacao).options(
                joinedload(RegraTributacao.regime_tributario),
                joinedload(RegraTributacao.cfop),
                joinedload(RegraTributacao.ncm)
            ).filter(RegraTributacao.ativo == True)
            
            # Filtrar por cliente
            query = query.filter(
                or_(
                    RegraTributacao.cliente_id == 13,
                    RegraTributacao.cliente_id.is_(None)
                )
            )
            
            # Filtrar por regime
            if cliente.regime_tributario_id:
                query = query.filter(RegraTributacao.regime_tributario_id == cliente.regime_tributario_id)
            
            # Filtrar por CFOP
            cfop_obj = db.query(Cfop).filter(Cfop.cfop == cenario['cfop']).first()
            if cfop_obj:
                query = query.filter(
                    or_(
                        RegraTributacao.cfop_id == cfop_obj.cfop_id,
                        RegraTributacao.cfop_id.is_(None)
                    )
                )
            
            # Filtrar por NCM
            ncm_obj = db.query(Ncm).filter(Ncm.codigo == cenario['ncm']).first()
            if ncm_obj:
                query = query.filter(
                    or_(
                        RegraTributacao.ncm_id == ncm_obj.ncm_id,
                        RegraTributacao.ncm_id.is_(None)
                    )
                )
            
            # Filtrar por UF
            query = query.filter(
                or_(
                    RegraTributacao.uf_origem == cliente.uf,
                    RegraTributacao.uf_origem.is_(None)
                )
            )
            query = query.filter(
                or_(
                    RegraTributacao.uf_destino == cenario['uf_destino'],
                    RegraTributacao.uf_destino.is_(None)
                )
            )
            
            # Filtrar por tipo
            query = query.filter(
                or_(
                    RegraTributacao.tipo_item == cenario['tipo_item'],
                    RegraTributacao.tipo_item.is_(None)
                )
            )
            
            # Ordenar por prioridade
            query = query.order_by(
                RegraTributacao.prioridade.desc(),
                RegraTributacao.cliente_id.desc().nullslast(),
                RegraTributacao.cfop_id.desc().nullslast(),
                RegraTributacao.ncm_id.desc().nullslast()
            )
            
            regra = query.first()
            
            if regra:
                print(f"   ✅ Regra encontrada: ID {regra.regra_tributacao_id}")
                print(f"      Descrição: {regra.descricao_regra}")
                print(f"      ICMS: {regra.csosn_icms or regra.cst_icms} ({regra.aliquota_icms or 0}%)")
                print(f"      PIS: {regra.cst_pis} ({regra.aliquota_pis or 0}%)")
                print(f"      COFINS: {regra.cst_cofins} ({regra.aliquota_cofins or 0}%)")
                if regra.cst_ipi:
                    print(f"      IPI: {regra.cst_ipi} ({regra.aliquota_ipi or 0}%)")
            else:
                print(f"   ⚠️  Nenhuma regra encontrada")
                print(f"      Sistema usará valores padrão")
        
        print()
        
        # =====================================================================
        # 4. SIMULAR PAYLOAD DA API
        # =====================================================================
        print("📤 4. SIMULANDO PAYLOAD DA API...")
        print("-" * 80)
        
        payload_exemplo = {
            "destinatario": {
                "cpf_cnpj": "12345678000195",
                "nome": "Cliente Teste Ltda",
                "endereco": "Rua Teste",
                "numero": "123",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "uf": "SP",
                "cep": "01234567",
                "email": "teste@cliente.com"
            },
            "itens": [
                {
                    "descricao": "Notebook Dell Inspiron 15",
                    "quantidade": 1,
                    "valor_unitario": 3500.00,
                    "ncm": "84713000",
                    "cfop": "5102",
                    "unidade": "UN"
                }
            ],
            "natureza_operacao": "Venda de Mercadoria"
        }
        
        print("\n✅ Payload Mínimo (o que o cliente precisa enviar):")
        print(json.dumps(payload_exemplo, indent=2, ensure_ascii=False))
        
        print("\n💡 Com esse payload, o sistema irá:")
        print("   1. Buscar regra tributária automaticamente")
        print("   2. Aplicar CST/CSOSN ICMS + alíquotas")
        print("   3. Aplicar PIS, COFINS, IPI automaticamente")
        print("   4. Gerar XML completo")
        print("   5. Enviar para SEFAZ")
        
        print()
        
        # =====================================================================
        # 5. RESUMO E RECOMENDAÇÕES
        # =====================================================================
        print("="*80)
        print("📊 RESUMO DO TESTE")
        print("="*80)
        
        print(f"\n✅ Cliente 13: {cliente.razao_social}")
        print(f"   • CNPJ: {cliente.cnpj}")
        print(f"   • UF: {cliente.uf}")
        print(f"   • Regime: {regime.nome if regime else 'N/A'}")
        
        print(f"\n📋 Regras Tributárias:")
        print(f"   • Específicas: {len(regras_cliente)}")
        print(f"   • Genéricas: {len(regras_genericas)}")
        print(f"   • Total: {total_regras}")
        
        if total_regras > 0:
            print("\n✅ Sistema pronto para tributação automática!")
            print("\n📝 Próximos passos:")
            print("   1. Gerar API Key para o cliente 13 (se ainda não tem)")
            print("   2. Fazer requisição POST para /api/v2/nfe/emitir")
            print("   3. Enviar payload mínimo (NCM + CFOP)")
            print("   4. Sistema aplicará regras automaticamente")
        else:
            print("\n⚠️  AÇÃO NECESSÁRIA:")
            print("   Cadastre pelo menos uma regra tributária antes de testar a API")
            print("   Acesse: Admin > Regras de Tributação > Criar Nova")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def criar_regra_teste(db, cliente):
    """Cria uma regra de teste básica para o cliente"""
    print("\n📝 Criando regra de teste...")
    
    try:
        # Buscar CFOP 5102
        cfop = db.query(Cfop).filter(Cfop.cfop == '5102').first()
        
        # Determinar CST/CSOSN baseado no regime
        if cliente.regime_tributario_id == 1:  # Simples Nacional
            nova_regra = RegraTributacao(
                cliente_id=13,
                regime_tributario_id=1,
                cfop_id=cfop.cfop_id if cfop else None,
                uf_origem=cliente.uf,
                uf_destino=cliente.uf,
                tipo_item='Produto',
                prioridade=100,
                csosn_icms='102',
                aliquota_icms=0,
                cst_pis='99',
                aliquota_pis=0,
                cst_cofins='99',
                aliquota_cofins=0,
                cst_ipi='99',
                aliquota_ipi=0,
                descricao_regra='Regra Teste - Venda Estadual Simples Nacional',
                ativo=True
            )
        else:  # Outros regimes
            nova_regra = RegraTributacao(
                cliente_id=13,
                regime_tributario_id=cliente.regime_tributario_id,
                cfop_id=cfop.cfop_id if cfop else None,
                uf_origem=cliente.uf,
                uf_destino=cliente.uf,
                tipo_item='Produto',
                prioridade=100,
                cst_icms='00',
                aliquota_icms=18.00,
                cst_pis='01',
                aliquota_pis=1.65,
                cst_cofins='01',
                aliquota_cofins=7.60,
                cst_ipi='99',
                aliquota_ipi=0,
                descricao_regra='Regra Teste - Venda Estadual',
                ativo=True
            )
        
        db.add(nova_regra)
        db.commit()
        
        print(f"✅ Regra de teste criada com sucesso (ID: {nova_regra.regra_tributacao_id})")
        print(f"   Descrição: {nova_regra.descricao_regra}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar regra de teste: {e}")


if __name__ == "__main__":
    main()

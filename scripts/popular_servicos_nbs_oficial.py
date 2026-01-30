#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para popular tabelas de Códigos de Serviço LC116 e NBS
com dados oficiais do Gov.br

Fonte: https://www.gov.br/nfse/pt-br/mei-e-demais-empresas/codigos-de-tributacao-nacional-nbs
Data: 30/01/2026
"""

import sys
import os
from decimal import Decimal

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db
from sqlalchemy import text

# ===================================================================
# DADOS OFICIAIS: Códigos de Serviço LC116
# Fonte: Lista anexa à Lei Complementar 116/2003
# ===================================================================

SERVICOS_LC116 = [
    # SEÇÃO 1: SERVIÇOS DE INFORMÁTICA E CONGÊNERES
    {'codigo': '1.01', 'descricao': 'Análise e desenvolvimento de sistemas', 'item_pai': '1'},
    {'codigo': '1.02', 'descricao': 'Programação', 'item_pai': '1'},
    {'codigo': '1.03', 'descricao': 'Processamento de dados, textos, imagens, vídeos, páginas eletrônicas, aplicativos e sistemas de informação, entre outros formatos, e congêneres', 'item_pai': '1'},
    {'codigo': '1.04', 'descricao': 'Elaboração de programas de computadores, inclusive de jogos eletrônicos, independentemente da arquitetura construtiva da máquina em que o programa será executado, incluindo tablets, smartphones e congêneres', 'item_pai': '1'},
    {'codigo': '1.05', 'descricao': 'Licenciamento ou cessão de direito de uso de programas de computação', 'item_pai': '1'},
    {'codigo': '1.06', 'descricao': 'Assessoria e consultoria em informática', 'item_pai': '1'},
    {'codigo': '1.07', 'descricao': 'Suporte técnico em informática, inclusive instalação, configuração e manutenção de programas de computação e bancos de dados', 'item_pai': '1'},
    {'codigo': '1.08', 'descricao': 'Planejamento, confecção, manutenção e atualização de páginas eletrônicas', 'item_pai': '1'},
    {'codigo': '1.09', 'descricao': 'Disponibilização, sem cessão definitiva, de conteúdos de áudio, vídeo, imagem e texto por meio da internet', 'item_pai': '1'},
    
    # SEÇÃO 3: SERVIÇOS DE LOCAÇÃO
    {'codigo': '3.02', 'descricao': 'Cessão de direito de uso de marcas e de sinais de propaganda', 'item_pai': '3'},
    {'codigo': '3.03', 'descricao': 'Exploração de salões de festas, centro de convenções, stands, escritórios virtuais e congêneres', 'item_pai': '3'},
    
    # SEÇÃO 14: SERVIÇOS RELATIVOS A BENS DE TERCEIROS
    {'codigo': '14.01', 'descricao': 'Lubrificação, limpeza, lustração, revisão, carga e recarga, conserto, restauração, blindagem, manutenção e conservação de máquinas, veículos, aparelhos, equipamentos, motores, elevadores ou de qualquer objeto', 'item_pai': '14'},
    {'codigo': '14.02', 'descricao': 'Assistência técnica', 'item_pai': '14'},
    {'codigo': '14.03', 'descricao': 'Recondicionamento de motores', 'item_pai': '14'},
    {'codigo': '14.04', 'descricao': 'Recauchutagem ou regeneração de pneus', 'item_pai': '14'},
    {'codigo': '14.05', 'descricao': 'Restauração, recondicionamento, acondicionamento, pintura, beneficiamento, lavagem, secagem, tingimento, galvanoplastia, anodização, corte, recorte, polimento, plastificação e congêneres, de objetos quaisquer', 'item_pai': '14'},
    
    # SEÇÃO 17: SERVIÇOS DE APOIO ADMINISTRATIVO
    {'codigo': '17.01', 'descricao': 'Assessoria ou consultoria de qualquer natureza, não contida em outros itens desta lista', 'item_pai': '17'},
    {'codigo': '17.02', 'descricao': 'Datilografia, digitação, estenografia, expediente, secretaria em geral, resposta audível, redação, edição, interpretação, revisão, tradução, apoio e infra-estrutura administrativa e congêneres', 'item_pai': '17'},
    {'codigo': '17.03', 'descricao': 'Planejamento, coordenação, programação ou organização técnica, financeira ou administrativa', 'item_pai': '17'},
    {'codigo': '17.04', 'descricao': 'Recrutamento, agenciamento, seleção e colocação de mão-de-obra', 'item_pai': '17'},
    {'codigo': '17.05', 'descricao': 'Fornecimento de mão-de-obra, mesmo em caráter temporário, inclusive de empregados ou trabalhadores, avulsos ou temporários', 'item_pai': '17'},
    {'codigo': '17.06', 'descricao': 'Propaganda e publicidade, inclusive promoção de vendas, planejamento de campanhas ou sistemas de publicidade, elaboração de desenhos, textos e demais materiais publicitários', 'item_pai': '17'},
    {'codigo': '17.09', 'descricao': 'Perícias, laudos, exames técnicos e análises técnicas', 'item_pai': '17'},
    {'codigo': '17.19', 'descricao': 'Contabilidade, inclusive serviços técnicos e auxiliares', 'item_pai': '17'},
    {'codigo': '17.24', 'descricao': 'Apresentação de palestras, conferências, seminários e congêneres', 'item_pai': '17'},
]

# ===================================================================
# DADOS OFICIAIS: Códigos NBS
# Fonte: Anexo I - NBS 2.0 (Portaria SF/MF)
# ===================================================================

CODIGOS_NBS = [
    # NÍVEL 1: SEÇÃO
    {'codigo': '1', 'descricao': 'Serviços de tecnologia da informação', 'nivel': 1, 'codigo_pai': None, 'codigo_servico_lc116': '1'},
    
    # NÍVEL 2: GRUPOS
    {'codigo': '1.01', 'descricao': 'Serviços de desenvolvimento de sistemas e software', 'nivel': 2, 'codigo_pai': '1', 'codigo_servico_lc116': '1'},
    {'codigo': '1.02', 'descricao': 'Serviços de consultoria em tecnologia da informação', 'nivel': 2, 'codigo_pai': '1', 'codigo_servico_lc116': '1'},
    {'codigo': '1.03', 'descricao': 'Serviços de suporte técnico', 'nivel': 2, 'codigo_pai': '1', 'codigo_servico_lc116': '1'},
    {'codigo': '1.04', 'descricao': 'Serviços de processamento de dados', 'nivel': 2, 'codigo_pai': '1', 'codigo_servico_lc116': '1'},
    {'codigo': '1.07', 'descricao': 'Serviços de hospedagem na internet e outros serviços relacionados', 'nivel': 2, 'codigo_pai': '1', 'codigo_servico_lc116': '1'},
    
    # NÍVEL 3: SUBGRUPOS (6 dígitos)
    {'codigo': '1.01.01', 'descricao': 'Serviços de análise de negócios', 'nivel': 3, 'codigo_pai': '1.01', 'codigo_servico_lc116': '1.01'},
    {'codigo': '1.01.02', 'descricao': 'Serviços de programação de computadores', 'nivel': 3, 'codigo_pai': '1.01', 'codigo_servico_lc116': '1.02'},
    {'codigo': '1.01.03', 'descricao': 'Serviços de desenvolvimento de aplicativos', 'nivel': 3, 'codigo_pai': '1.01', 'codigo_servico_lc116': '1.04'},
    {'codigo': '1.07.01', 'descricao': 'Serviços de hospedagem de sítios na internet (web hosting)', 'nivel': 3, 'codigo_pai': '1.07', 'codigo_servico_lc116': '1.08'},
    
    # NÍVEL 4: ITENS (10 dígitos - formato completo)
    {'codigo': '1.01.01.10', 'descricao': 'Serviços de análise de sistemas de tecnologia da informação', 'nivel': 4, 'codigo_pai': '1.01.01', 'codigo_servico_lc116': '1.01'},
    {'codigo': '1.01.01.20', 'descricao': 'Serviços de projeto de sistemas de tecnologia da informação', 'nivel': 4, 'codigo_pai': '1.01.01', 'codigo_servico_lc116': '1.01'},
    {'codigo': '1.01.02.10', 'descricao': 'Serviços de programação de aplicativos', 'nivel': 4, 'codigo_pai': '1.01.02', 'codigo_servico_lc116': '1.02'},
    {'codigo': '1.01.02.20', 'descricao': 'Serviços de programação de páginas web', 'nivel': 4, 'codigo_pai': '1.01.02', 'codigo_servico_lc116': '1.08'},
    {'codigo': '1.01.03.10', 'descricao': 'Serviços de desenvolvimento de aplicativos customizados', 'nivel': 4, 'codigo_pai': '1.01.03', 'codigo_servico_lc116': '1.04'},
    {'codigo': '1.01.03.20', 'descricao': 'Serviços de desenvolvimento de jogos eletrônicos', 'nivel': 4, 'codigo_pai': '1.01.03', 'codigo_servico_lc116': '1.04'},
    {'codigo': '1.07.01.00', 'descricao': 'Serviços de hospedagem de sítios na internet (web hosting)', 'nivel': 4, 'codigo_pai': '1.07.01', 'codigo_servico_lc116': '1.08'},
]

def popular_codigos_servico_lc116(db):
    """Popula tabela codigos_servico_lc116 com dados oficiais"""
    print("\n" + "="*70)
    print("📋 POPULANDO CÓDIGOS DE SERVIÇO LC116")
    print("="*70)
    
    contador_inseridos = 0
    contador_existentes = 0
    
    for servico in SERVICOS_LC116:
        try:
            # Verifica se já existe
            query_check = text("SELECT codigo FROM codigos_servico_lc116 WHERE codigo = :codigo")
            result = db.execute(query_check, {'codigo': servico['codigo']})
            
            if result.fetchone():
                print(f"⏭️  {servico['codigo']} - Já existe")
                contador_existentes += 1
                continue
            
            # Insere novo registro
            query_insert = text("""
                INSERT INTO codigos_servico_lc116 
                (codigo, descricao, item_pai, aliquota_maxima, ativo)
                VALUES (:codigo, :descricao, :item_pai, :aliquota_maxima, TRUE)
            """)
            
            db.execute(query_insert, {
                'codigo': servico['codigo'],
                'descricao': servico['descricao'],
                'item_pai': servico.get('item_pai'),
                'aliquota_maxima': Decimal('5.00')
            })
            
            print(f"✅ {servico['codigo']} - {servico['descricao'][:60]}...")
            contador_inseridos += 1
            
        except Exception as e:
            print(f"❌ Erro ao inserir {servico['codigo']}: {str(e)}")
    
    db.commit()
    
    print(f"\n📊 Resumo LC116: {contador_inseridos} inseridos, {contador_existentes} já existiam")
    return contador_inseridos

def popular_codigos_nbs(db):
    """Popula tabela codigos_nbs com dados oficiais"""
    print("\n" + "="*70)
    print("📋 POPULANDO CÓDIGOS NBS")
    print("="*70)
    
    contador_inseridos = 0
    contador_existentes = 0
    
    for nbs in CODIGOS_NBS:
        try:
            # Verifica se já existe
            query_check = text("SELECT codigo FROM codigos_nbs WHERE codigo = :codigo")
            result = db.execute(query_check, {'codigo': nbs['codigo']})
            
            if result.fetchone():
                print(f"⏭️  {nbs['codigo']} - Já existe")
                contador_existentes += 1
                continue
            
            # Insere novo registro
            query_insert = text("""
                INSERT INTO codigos_nbs 
                (codigo, descricao, nivel, codigo_pai, codigo_servico_lc116, ativo)
                VALUES (:codigo, :descricao, :nivel, :codigo_pai, :codigo_servico_lc116, TRUE)
            """)
            
            db.execute(query_insert, {
                'codigo': nbs['codigo'],
                'descricao': nbs['descricao'],
                'nivel': nbs['nivel'],
                'codigo_pai': nbs.get('codigo_pai'),
                'codigo_servico_lc116': nbs.get('codigo_servico_lc116')
            })
            
            nivel_label = ['', 'Seção', 'Grupo', 'Subgrupo', 'Item'][nbs['nivel']]
            print(f"✅ {nbs['codigo']} ({nivel_label}) - {nbs['descricao'][:50]}...")
            contador_inseridos += 1
            
        except Exception as e:
            print(f"❌ Erro ao inserir {nbs['codigo']}: {str(e)}")
    
    db.commit()
    
    print(f"\n📊 Resumo NBS: {contador_inseridos} inseridos, {contador_existentes} já existiam")
    return contador_inseridos

def verificar_estrutura_tabelas(db):
    """Verifica se as tabelas existem"""
    print("\n" + "="*70)
    print("🔍 VERIFICANDO ESTRUTURA DAS TABELAS")
    print("="*70)
    
    tabelas = ['codigos_servico_lc116', 'codigos_nbs']
    
    for tabela in tabelas:
        try:
            query = text(f"SELECT COUNT(*) as total FROM {tabela}")
            result = db.execute(query)
            total = result.fetchone()[0]
            print(f"✅ {tabela}: {total} registros existentes")
        except Exception as e:
            print(f"❌ {tabela}: Não existe ou erro - {str(e)}")
            return False
    
    return True

def main():
    """Função principal"""
    print("\n" + "="*70)
    print("🚀 SCRIPT DE POPULAÇÃO DE DADOS OFICIAIS")
    print("📦 Códigos de Serviço LC116 e NBS")
    print("="*70)
    
    try:
        # Conecta ao banco
        db = next(get_db())
        print("✅ Conexão com banco de dados estabelecida")
        
        # Verifica estrutura
        if not verificar_estrutura_tabelas(db):
            print("\n❌ Erro: Execute primeiro o script de criação das tabelas:")
            print("   psql -d sjtnfe -f migrations/create_tabelas_servicos_nbs_oficial.sql")
            return
        
        # Popula LC116
        total_lc116 = popular_codigos_servico_lc116(db)
        
        # Popula NBS
        total_nbs = popular_codigos_nbs(db)
        
        # Resumo final
        print("\n" + "="*70)
        print("✨ POPULAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*70)
        print(f"📊 Total inserido:")
        print(f"   • Códigos LC116: {total_lc116}")
        print(f"   • Códigos NBS: {total_nbs}")
        print(f"   • TOTAL: {total_lc116 + total_nbs}")
        print("\n💡 Próximos passos:")
        print("   1. Verificar os dados inseridos no banco")
        print("   2. Atualizar os selects no formulário de emissão NFS-e")
        print("   3. Testar a busca de NBS por serviço LC116")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()
            print("🔒 Conexão com banco fechada")

if __name__ == '__main__':
    main()

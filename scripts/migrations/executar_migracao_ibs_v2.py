#!/usr/bin/env python3
"""
Script de Migração para Preparação IBS/CBS - Versão 2
-------------------------------------------------------
Executa migração SQL e popula tabela de códigos de serviço LC 116/2003
Usa padrão de conexão nativo do projeto (database.connection)

Uso:
    python executar_migracao_ibs_v2.py

Autor: Sistema NFe
Data: 17/11/2025
"""

import sys
from pathlib import Path
from sqlalchemy import text

# Adicionar diretório raiz ao path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Importar conexão do banco de dados (padrão do projeto)
try:
    from database.connection import get_db
    print("[OK] Conexão de banco importada com sucesso")
except ImportError as e:
    print(f"[X] Erro ao importar database.connection: {e}")
    print("[TRACE] Diretório atual:", current_dir)
    print("\n[!]  Execute este script do diretório raiz do projeto:")
    print("    cd /Users/renato/Documents/Developement/api_nfe")
    print("    python3 executar_migracao_ibs_v2.py")
    sys.exit(1)


def executar_migracao_sql():
    """Executa arquivo SQL de migração"""
    print("\n" + "="*60)
    print("[?] EXECUTANDO MIGRAÇÃO SQL")
    print("="*60)
    
    arquivo_sql = Path(__file__).parent / 'migrations' / '001_preparacao_ibs_simples.sql'
    
    if not arquivo_sql.exists():
        print(f"[X] Arquivo não encontrado: {arquivo_sql}")
        return False
    
    print(f"[?] Lendo arquivo: {arquivo_sql.name}")
    
    db = next(get_db())
    try:
        with open(arquivo_sql, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("[?] Executando comandos SQL...")
        
        # Executar SQL como um bloco único (PostgreSQL suporta múltiplos comandos)
        try:
            db.execute(text(sql_content))
            print(f"  [OK] Comandos SQL executados")
        except Exception as e:
            # Ignorar erros de "já existe"
            if 'already exists' in str(e).lower():
                print(f"  ⏭️  Estruturas já existem, continuando...")
            else:
                raise
        
        db.commit()
        print("[OK] Migração SQL executada com sucesso!")
        return True
    
    except Exception as e:
        db.rollback()
        print(f"[X] Erro ao executar migração SQL: {e}")
        return False
    finally:
        db.close()


def popular_codigos_servico():
    """Popula tabela com códigos de serviço LC 116/2003"""
    print("\n" + "="*60)
    print("[DATA] POPULANDO CÓDIGOS DE SERVIÇO LC 116/2003")
    print("="*60)
    
    # Lista de códigos de serviço LC 116/2003 (40 principais)
    codigos = [
        # 01 - Serviços de informática
        ('01.01', 'Análise e desenvolvimento de sistemas'),
        ('01.02', 'Programação'),
        ('01.03', 'Processamento de dados e congêneres'),
        ('01.04', 'Elaboração de programas de computadores, inclusive de jogos eletrônicos'),
        ('01.05', 'Licenciamento ou cessão de direito de uso de programas de computação'),
        ('01.06', 'Assessoria e consultoria em informática'),
        ('01.07', 'Suporte técnico em informática'),
        ('01.08', 'Planejamento, confecção, manutenção e atualização de páginas eletrônicas'),
        
        # 02 - Serviços de pesquisas
        ('02.01', 'Serviços de pesquisas e desenvolvimento de qualquer natureza'),
        
        # 03 - Serviços de locação, cessão de direito
        ('03.02', 'Cessão de direito de uso de marcas e de sinais de propaganda'),
        ('03.03', 'Exploração de salões de festas, centro de convenções, stands, quadras esportivas'),
        ('03.04', 'Locação, sublocação, arrendamento de ferrovia, rodovia, postes, cabos, dutos'),
        ('03.05', 'Cessão de andaimes, palcos, coberturas e outras estruturas de uso temporário'),
        
        # 04 - Serviços de saúde
        ('04.01', 'Medicina e biomedicina'),
        ('04.02', 'Análises clínicas, patologia, radiologia, tomografia e congêneres'),
        ('04.03', 'Hospitais, clínicas, laboratórios, ambulatórios e congêneres'),
        ('04.08', 'Terapia ocupacional, fisioterapia e fonoaudiologia'),
        ('04.12', 'Odontologia'),
        ('04.16', 'Psicologia'),
        
        # 05 - Medicina veterinária
        ('05.01', 'Medicina veterinária e zootecnia'),
        
        # 06 - Cuidados pessoais
        ('06.01', 'Barbearia, cabeleireiros, manicuros, pedicuros e congêneres'),
        ('06.02', 'Esteticistas, tratamento de pele, depilação e congêneres'),
        
        # 07 - Serviços de engenharia e arquitetura
        ('07.01', 'Engenharia, agronomia, agrimensura, arquitetura, geologia, urbanismo e congêneres'),
        ('07.02', 'Execução, por administração, empreitada ou subempreitada, de obras de construção civil'),
        ('07.04', 'Demolição'),
        ('07.05', 'Reparação, conservação e reforma de edifícios, estradas, pontes, portos e congêneres'),
        
        # 08 - Serviços de educação
        ('08.01', 'Ensino regular pré-escolar, fundamental, médio e superior'),
        ('08.02', 'Instrução, treinamento, orientação pedagógica e educacional'),
        
        # 09 - Hospedagem e turismo
        ('09.01', 'Hospedagem em hotéis, apart-hotéis, motéis, pensões e congêneres'),
        ('09.02', 'Agenciamento, organização de programas de turismo, passeios, viagens'),
        ('09.03', 'Guias de turismo'),
        
        # 10 - Serviços de intermediação
        ('10.01', 'Agenciamento, corretagem de câmbio, seguros, cartões de crédito'),
        ('10.02', 'Agenciamento, corretagem de títulos, valores mobiliários'),
        ('10.05', 'Agenciamento, corretagem de bens móveis ou imóveis'),
        ('10.08', 'Agenciamento de publicidade e propaganda'),
        ('10.09', 'Representação de qualquer natureza, inclusive comercial'),
        ('10.10', 'Distribuição de bens de terceiros'),
    ]
    
    print(f"[DATA] Inserindo {len(codigos)} códigos de serviço...")
    
    db = next(get_db())
    try:
        inseridos = 0
        existentes = 0
        
        for codigo, descricao in codigos:
            # Verificar se já existe
            check_query = text("""
                SELECT id FROM codigos_servico WHERE codigo = :codigo
            """)
            existe = db.execute(check_query, {'codigo': codigo}).fetchone()
            
            if not existe:
                insert_query = text("""
                    INSERT INTO codigos_servico 
                    (codigo, descricao, aliquota_padrao, ativo)
                    VALUES 
                    (:codigo, :descricao, 0.00, TRUE)
                """)
                
                db.execute(insert_query, {
                    'codigo': codigo,
                    'descricao': descricao
                })
                inseridos += 1
                if inseridos % 5 == 0:
                    print(f"  [OK] {inseridos} códigos inseridos...")
            else:
                existentes += 1
        
        db.commit()
        print(f"\n[OK] Processamento concluído:")
        print(f"   • {inseridos} códigos inseridos")
        print(f"   • {existentes} códigos já existiam")
        return True
    
    except Exception as e:
        print(f"[X] Erro ao popular códigos de serviço: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verificar_estruturas():
    """Verifica se estruturas foram criadas corretamente"""
    print("\n" + "="*60)
    print("[SEARCH] VERIFICANDO ESTRUTURAS CRIADAS")
    print("="*60)
    
    tabelas_esperadas = [
        'codigos_servico',
        'aliquotas_ibs_municipio',
        'historico_calculo_ibs'
    ]
    
    db = next(get_db())
    try:
        for tabela in tabelas_esperadas:
            query = text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = :tabela
            """)
            
            result = db.execute(query, {'tabela': tabela}).fetchone()
            
            if result and result[0] > 0:
                # Contar registros
                count_query = text(f"SELECT COUNT(*) FROM {tabela}")
                count_result = db.execute(count_query).fetchone()
                count = count_result[0] if count_result else 0
                print(f"  [OK] {tabela:<35} ({count} registros)")
            else:
                print(f"  [X] {tabela:<35} (NÃO ENCONTRADA)")
        
        return True
    
    except Exception as e:
        print(f"[X] Erro ao verificar estruturas: {e}")
        return False
    finally:
        db.close()


def main():
    """Função principal"""
    print("\n" + "="*60)
    print("[START] MIGRAÇÃO IBS/CBS - FASE 1: PREPARAÇÃO")
    print("="*60)
    print("[LIST] Este script irá:")
    print("   1. Criar tabelas para estruturas IBS/CBS")
    print("   2. Popular códigos de serviço LC 116/2003")
    print("   3. Verificar estruturas criadas")
    print("="*60)
    
    # Passo 1: Executar migração SQL
    if not executar_migracao_sql():
        print("\n[X] Migração SQL falhou. Abortando...")
        return 1
    
    # Passo 2: Popular códigos de serviço
    if not popular_codigos_servico():
        print("\n[!]  Códigos de serviço não foram populados completamente")
    
    # Passo 3: Verificar estruturas
    verificar_estruturas()
    
    # Resumo final
    print("\n" + "="*60)
    print("[OK] MIGRAÇÃO FASE 1 CONCLUÍDA!")
    print("="*60)
    print("\n[LOG] Próximos passos:")
    print("   1. Testar serviço de cálculo IBS: services/calculo_ibs.py")
    print("   2. Aguardar publicação oficial das alíquotas IBS/CBS (2026)")
    print("   3. Popular tabela aliquotas_ibs_municipio quando disponível")
    print("\n[?] Consulte FASE1_PREPARACAO_IBS_README.md para mais detalhes")
    print("="*60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""
Script para atualizar a tabela classificacoes_ibs_cbs com os dados corretos
do arquivo cClassTrib 2025-12-12.xlsx
"""

import pandas as pd
from database.connection import SessionLocal
from database.models import ClassificacaoIBSCBS
from sqlalchemy import text

def atualizar_classificacoes_ibs_cbs():
    """Atualiza a tabela com os dados do arquivo Excel correto"""
    
    db = SessionLocal()
    
    try:
        # Ler o arquivo Excel
        file_path = 'Documentacao/cClassTrib 2025-12-12.xlsx'
        df = pd.read_excel(file_path)
        
        print(f"=== Lendo arquivo: {file_path} ===")
        print(f"Total de registros no Excel: {len(df)}\n")
        
        # Limpar tabela existente
        print("Limpando tabela existente...")
        db.execute(text("DELETE FROM classificacoes_ibs_cbs"))
        db.commit()
        print("Tabela limpa com sucesso!\n")
        
        # Inserir novos registros
        print("Inserindo novos registros...")
        registros_inseridos = 0
        erros = 0
        
        for index, row in df.iterrows():
            try:
                # Extrair dados do Excel
                cst_ibs_cbs = row['CST-IBS/CBS']
                cclass_trib = row['cClassTrib']
                nome_cclass_trib = row['Nome cClassTrib']
                descricao_cclass_trib = row['Descrição cClassTrib']
                tipo_aliquota = row['Tipo de Alíquota']
                p_red_ibs = row['pRedIBS'] if pd.notna(row['pRedIBS']) else 0
                p_red_cbs = row['pRedCBS'] if pd.notna(row['pRedCBS']) else 0
                
                # Criar código único combinando CST e cClassTrib
                codigo = f"{int(cst_ibs_cbs):02d}-{int(cclass_trib):05d}" if pd.notna(cclass_trib) else f"{int(cst_ibs_cbs):02d}"
                
                # Descrição completa
                descricao_completa = f"{nome_cclass_trib}\n{descricao_cclass_trib}"
                
                # Calcular alíquotas baseado no tipo e redução
                # Alíquotas de referência: IBS-UF = 0.10, IBS-MUN = 0.00, CBS = 0.90
                if tipo_aliquota == 'Uniforme nacional (referência)':
                    aliquota_ibs_uf = 0.10 * (1 - p_red_ibs/100)
                    aliquota_ibs_mun = 0.00
                    aliquota_cbs = 0.90 * (1 - p_red_cbs/100)
                elif tipo_aliquota == 'Uniforme setorial':
                    # Manter valores específicos ou usar padrão
                    aliquota_ibs_uf = 0.10
                    aliquota_ibs_mun = 0.00
                    aliquota_cbs = 0.90
                else:  # Padrão
                    aliquota_ibs_uf = 0.10
                    aliquota_ibs_mun = 0.00
                    aliquota_cbs = 0.90
                
                # Criar objeto ClassificacaoIBSCBS
                classificacao = ClassificacaoIBSCBS(
                    codigo=codigo,
                    descricao=descricao_completa,
                    aliquota_ibs_uf=round(aliquota_ibs_uf, 4),
                    aliquota_ibs_mun=round(aliquota_ibs_mun, 4),
                    aliquota_cbs=round(aliquota_cbs, 4),
                    ativo=True
                )
                
                db.add(classificacao)
                registros_inseridos += 1
                
                if registros_inseridos % 20 == 0:
                    print(f"Inseridos {registros_inseridos} registros...")
                    
            except Exception as e:
                erros += 1
                print(f"Erro na linha {index + 2}: {e}")
                continue
        
        # Commit final
        db.commit()
        
        print(f"\n=== RESUMO DA IMPORTAÇÃO ===")
        print(f"Total de registros processados: {len(df)}")
        print(f"Registros inseridos com sucesso: {registros_inseridos}")
        print(f"Erros encontrados: {erros}")
        
        # Verificar total na tabela
        total_db = db.query(ClassificacaoIBSCBS).count()
        print(f"\nTotal de registros na tabela: {total_db}")
        
        # Mostrar alguns exemplos
        print("\n=== EXEMPLOS DE REGISTROS INSERIDOS ===")
        exemplos = db.query(ClassificacaoIBSCBS).limit(5).all()
        for ex in exemplos:
            print(f"\nCódigo: {ex.codigo}")
            print(f"Descrição: {ex.descricao[:100]}...")
            print(f"Alíquotas - IBS-UF: {ex.aliquota_ibs_uf}, IBS-MUN: {ex.aliquota_ibs_mun}, CBS: {ex.aliquota_cbs}")
        
        return True
        
    except Exception as e:
        print(f"\nErro geral: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == '__main__':
    print("=== ATUALIZAÇÃO DE CLASSIFICAÇÕES IBS/CBS ===\n")
    print("Este script irá substituir TODOS os dados da tabela classificacoes_ibs_cbs")
    print("pelos dados corretos do arquivo cClassTrib 2025-12-12.xlsx\n")
    
    confirma = input("Deseja continuar? (S/N): ")
    
    if confirma.upper() == 'S':
        sucesso = atualizar_classificacoes_ibs_cbs()
        if sucesso:
            print("\n✅ Atualização concluída com sucesso!")
        else:
            print("\n❌ Atualização falhou!")
    else:
        print("\nOperação cancelada pelo usuário.")

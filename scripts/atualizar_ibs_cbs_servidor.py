#!/usr/bin/env python3
"""
Script para atualizar classificações IBS/CBS no servidor
Lê o arquivo cClassTrib 2025-12-12.xlsx e atualiza a tabela classificacoes_ibs_cbs
"""

import sys
import os
from pathlib import Path

# Detectar diretório raiz do projeto automaticamente
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

# Se o script foi extraído em uma pasta diferente, procurar pelo app.py
if not (BASE_DIR / 'app.py').exists():
    # Tentar encontrar app.py subindo na hierarquia
    current = BASE_DIR
    found = False
    for _ in range(5):  # Tentar até 5 níveis acima
        if (current / 'app.py').exists():
            BASE_DIR = current
            found = True
            break
        current = current.parent
    
    if not found:
        print("❌ ERRO: Não foi possível encontrar o diretório do projeto (app.py não encontrado)")
        print(f"   Diretório atual: {BASE_DIR}")
        print()
        print("Execute o script do diretório raiz do projeto:")
        print("   cd C:\\nfe_app")
        print("   python scripts\\atualizar_ibs_cbs_servidor.py")
        print()
        print("Ou mova os arquivos extraídos para dentro do projeto api_nfe")
        sys.exit(1)

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)  # Mudar diretório de trabalho para o raiz do projeto

print(f"🔧 Diretório do projeto: {BASE_DIR}")
print()

# Verificar e instalar dependências
def verificar_dependencias():
    """Verifica se as dependências necessárias estão instaladas"""
    modulos_necessarios = {
        'pandas': 'pandas',
        'openpyxl': 'openpyxl',
        'sqlalchemy': 'sqlalchemy',
        'psycopg2': 'psycopg2-binary',
        'flask': 'flask',
        'flask_login': 'flask-login'
    }
    
    modulos_faltando = []
    
    for modulo, pacote in modulos_necessarios.items():
        try:
            __import__(modulo)
        except ImportError:
            modulos_faltando.append(pacote)
    
    if modulos_faltando:
        print("⚠️  Dependências faltando:", ", ".join(modulos_faltando))
        print()
        resposta = input("Deseja instalar agora? (S/N): ")
        
        if resposta.upper() == 'S':
            print("\n📦 Instalando dependências...")
            import subprocess
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + modulos_faltando)
                print("✅ Dependências instaladas com sucesso!")
                print()
            except subprocess.CalledProcessError:
                print("\n❌ Erro ao instalar dependências.")
                print("Tente instalar manualmente:")
                print(f"   pip install {' '.join(modulos_faltando)}")
                print()
                sys.exit(1)
        else:
            print("\n❌ Dependências necessárias não instaladas.")
            print("Instale manualmente:")
            print(f"   pip install {' '.join(modulos_faltando)}")
            print()
            sys.exit(1)

# Verificar dependências antes de importar módulos do projeto
verificar_dependencias()

import pandas as pd
from sqlalchemy import text
from database.connection import SessionLocal
from database.models import ClassificacaoIBSCBS

def verificar_arquivo_excel():
    """Verifica se o arquivo Excel existe"""
    file_path = BASE_DIR / 'Documentacao' / 'cClassTrib 2025-12-12.xlsx'
    
    if not file_path.exists():
        print(f"❌ ERRO: Arquivo não encontrado: {file_path}")
        print("\nVerifique se o arquivo está no caminho correto:")
        print(f"  {file_path}")
        return None
    
    return file_path

def backup_tabela(db):
    """Faz backup dos dados atuais"""
    try:
        print("📦 Criando backup dos dados atuais...")
        
        # Contar registros atuais
        count = db.query(ClassificacaoIBSCBS).count()
        print(f"   Registros atuais na tabela: {count}")
        
        if count > 0:
            backup_file = BASE_DIR / 'backups' / f'classificacoes_ibs_cbs_backup_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.sql'
            backup_file.parent.mkdir(exist_ok=True)
            
            # Query para exportar
            registros = db.query(ClassificacaoIBSCBS).all()
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write("-- Backup de classificacoes_ibs_cbs\n")
                f.write(f"-- Data: {pd.Timestamp.now()}\n")
                f.write(f"-- Total de registros: {count}\n\n")
                
                for r in registros:
                    f.write(f"INSERT INTO classificacoes_ibs_cbs (codigo, descricao, aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs, ativo) VALUES ")
                    f.write(f"('{r.codigo}', '{r.descricao.replace(chr(39), chr(39)+chr(39))}', {r.aliquota_ibs_uf}, {r.aliquota_ibs_mun}, {r.aliquota_cbs}, {r.ativo});\n")
            
            print(f"   ✅ Backup salvo em: {backup_file}")
            return True
        else:
            print("   ℹ️  Tabela vazia, backup não necessário")
            return True
            
    except Exception as e:
        print(f"   ⚠️  Erro ao criar backup: {e}")
        return False

def atualizar_classificacoes():
    """Função principal de atualização"""
    
    print("=" * 70)
    print("  ATUALIZAÇÃO DE CLASSIFICAÇÕES IBS/CBS")
    print("=" * 70)
    print()
    
    # Verificar arquivo
    file_path = verificar_arquivo_excel()
    if not file_path:
        return False
    
    db = SessionLocal()
    
    try:
        # Fazer backup
        if not backup_tabela(db):
            resposta = input("\n⚠️  Backup falhou. Deseja continuar mesmo assim? (s/N): ")
            if resposta.lower() != 's':
                print("Operação cancelada pelo usuário.")
                return False
        
        print()
        print("📖 Lendo arquivo Excel...")
        df = pd.read_excel(file_path)
        print(f"   Total de registros no Excel: {len(df)}")
        
        # Validar estrutura do arquivo
        colunas_necessarias = [
            'CST-IBS/CBS', 'cClassTrib', 'Nome cClassTrib', 
            'Descrição cClassTrib', 'Tipo de Alíquota', 'pRedIBS', 'pRedCBS'
        ]
        
        colunas_faltando = [col for col in colunas_necessarias if col not in df.columns]
        if colunas_faltando:
            print(f"\n❌ ERRO: Colunas faltando no arquivo: {colunas_faltando}")
            return False
        
        print("   ✅ Estrutura do arquivo validada")
        
        print()
        print("🗑️  Limpando tabela existente...")
        db.execute(text("DELETE FROM classificacoes_ibs_cbs"))
        db.commit()
        print("   ✅ Tabela limpa")
        
        print()
        print("📝 Inserindo novos registros...")
        registros_inseridos = 0
        erros = []
        
        for index, row in df.iterrows():
            try:
                # Extrair dados
                cst_ibs_cbs = row['CST-IBS/CBS']
                cclass_trib = row['cClassTrib']
                nome_cclass_trib = row['Nome cClassTrib']
                descricao_cclass_trib = row['Descrição cClassTrib']
                tipo_aliquota = row['Tipo de Alíquota']
                p_red_ibs = row['pRedIBS'] if pd.notna(row['pRedIBS']) else 0
                p_red_cbs = row['pRedCBS'] if pd.notna(row['pRedCBS']) else 0
                
                # Criar código único
                if pd.notna(cclass_trib):
                    codigo = f"{int(cst_ibs_cbs):02d}-{int(cclass_trib):05d}"
                else:
                    codigo = f"{int(cst_ibs_cbs):02d}"
                
                # Descrição completa
                descricao_completa = f"{nome_cclass_trib}\n{descricao_cclass_trib}"
                
                # Calcular alíquotas
                if tipo_aliquota == 'Uniforme nacional (referência)':
                    aliquota_ibs_uf = 0.10 * (1 - p_red_ibs/100)
                    aliquota_ibs_mun = 0.00
                    aliquota_cbs = 0.90 * (1 - p_red_cbs/100)
                elif tipo_aliquota == 'Uniforme setorial':
                    aliquota_ibs_uf = 0.10
                    aliquota_ibs_mun = 0.00
                    aliquota_cbs = 0.90
                else:  # Padrão
                    aliquota_ibs_uf = 0.10
                    aliquota_ibs_mun = 0.00
                    aliquota_cbs = 0.90
                
                # Criar objeto
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
                
                # Progresso
                if registros_inseridos % 25 == 0:
                    print(f"   Processados: {registros_inseridos}/{len(df)} registros...")
                    
            except Exception as e:
                erros.append(f"Linha {index + 2}: {str(e)[:100]}")
                continue
        
        # Commit final
        print()
        print("💾 Salvando alterações no banco de dados...")
        db.commit()
        
        # Verificar resultado
        total_db = db.query(ClassificacaoIBSCBS).count()
        
        print()
        print("=" * 70)
        print("  RESUMO DA ATUALIZAÇÃO")
        print("=" * 70)
        print(f"✅ Registros processados:      {len(df)}")
        print(f"✅ Registros inseridos:        {registros_inseridos}")
        print(f"❌ Erros encontrados:          {len(erros)}")
        print(f"📊 Total na tabela:            {total_db}")
        print()
        
        if erros:
            print("⚠️  ERROS ENCONTRADOS:")
            for erro in erros[:10]:
                print(f"   - {erro}")
            if len(erros) > 10:
                print(f"   ... e mais {len(erros) - 10} erros")
            print()
        
        # Exemplos
        print("📋 EXEMPLOS DE REGISTROS:")
        exemplos = db.query(ClassificacaoIBSCBS).limit(5).all()
        for ex in exemplos:
            print(f"\n   Código: {ex.codigo}")
            print(f"   Descrição: {ex.descricao.split(chr(10))[0][:60]}...")
            print(f"   Alíquotas: IBS-UF={ex.aliquota_ibs_uf} | IBS-MUN={ex.aliquota_ibs_mun} | CBS={ex.aliquota_cbs}")
        
        print()
        print("=" * 70)
        print("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERRO DURANTE A ATUALIZAÇÃO")
        print("=" * 70)
        print(f"Erro: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("Revertendo alterações...")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == '__main__':
    print()
    
    # Verificar se está rodando como root/sudo (apenas em Unix/Linux)
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        print("⚠️  AVISO: Executando como root/sudo")
        print()
    
    # Confirmar execução
    if len(sys.argv) > 1 and sys.argv[1] == '--yes':
        confirmado = True
    else:
        print("Este script irá:")
        print("  1. Fazer backup dos dados atuais")
        print("  2. DELETAR todos os registros da tabela classificacoes_ibs_cbs")
        print("  3. Importar os novos dados do arquivo Excel")
        print()
        resposta = input("Deseja continuar? (s/N): ")
        confirmado = resposta.lower() == 's'
    
    if confirmado:
        sucesso = atualizar_classificacoes()
        sys.exit(0 if sucesso else 1)
    else:
        print("\n❌ Operação cancelada pelo usuário.")
        sys.exit(2)

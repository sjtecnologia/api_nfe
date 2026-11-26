"""
Script para executar migrations NT007 v1.03.00
Data: 09/02/2026
Autor: Sistema
Descrição: Cria tabelas de validação para Reforma Tributária (IBS/CBS)
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

# Importar configurações
try:
    from config.settings import DATABASE_URI
except ImportError:
    print("❌ Erro: Não foi possível importar DATABASE_URI de config.settings")
    print("💡 Certifique-se de que o arquivo config/settings.py existe")
    sys.exit(1)


def executar_migration_arquivo(engine, arquivo_sql: str, descricao: str):
    """
    Executa um arquivo SQL de migration
    
    Args:
        engine: Engine do SQLAlchemy
        arquivo_sql: Caminho do arquivo SQL
        descricao: Descrição da migration
    """
    print(f"\n{'='*70}")
    print(f"📄 {descricao}")
    print(f"📁 Arquivo: {arquivo_sql}")
    print(f"{'='*70}\n")
    
    # Verificar se arquivo existe
    if not os.path.exists(arquivo_sql):
        print(f"❌ Arquivo não encontrado: {arquivo_sql}")
        return False
    
    # Ler arquivo SQL
    try:
        with open(arquivo_sql, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return False
    
    # Executar SQL
    try:
        with engine.connect() as conn:
            # Executar em transação
            trans = conn.begin()
            try:
                # Dividir por statements (separados por ';')
                statements = [s.strip() for s in sql_content.split(';') if s.strip()]
                
                for i, statement in enumerate(statements, 1):
                    if statement:
                        print(f"⚙️  Executando statement {i}/{len(statements)}...")
                        conn.execute(text(statement))
                
                # Commit
                trans.commit()
                print(f"\n✅ Migration executada com sucesso!")
                print(f"📊 Total de statements: {len(statements)}")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Erro ao executar SQL: {e}")
                print(f"📍 Statement que falhou: {i}/{len(statements)}")
                return False
                
    except SQLAlchemyError as e:
        print(f"❌ Erro de conexão: {e}")
        return False


def verificar_tabelas_existentes(engine):
    """Verifica se as tabelas já existem"""
    print("\n🔍 Verificando tabelas existentes...")
    
    tabelas_verificar = [
        'indicador_operacao_ibs_cbs',
        'classificacao_tributaria_nfse',
        'cst_ibs_cbs',
        'nomenclatura_brasileira_servicos'
    ]
    
    try:
        with engine.connect() as conn:
            tabelas_existentes = []
            tabelas_faltando = []
            
            for tabela in tabelas_verificar:
                result = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    f"WHERE table_schema = 'public' AND table_name = '{tabela}')"
                ))
                existe = result.scalar()
                
                if existe:
                    tabelas_existentes.append(tabela)
                    print(f"  ✅ {tabela}")
                else:
                    tabelas_faltando.append(tabela)
                    print(f"  ❌ {tabela}")
            
            print(f"\n📊 Resultado:")
            print(f"  ✅ Existentes: {len(tabelas_existentes)}/{len(tabelas_verificar)}")
            print(f"  ❌ Faltando: {len(tabelas_faltando)}/{len(tabelas_verificar)}")
            
            return tabelas_faltando
            
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {e}")
        return tabelas_verificar


def main():
    """Função principal"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         🚀 MIGRATIONS NT007 v1.03.00 - REFORMA TRIBUTÁRIA       ║
║                                                                  ║
║  Criação de tabelas para validação IBS/CBS (LC 214/2025)       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Conectar ao banco
    print("🔌 Conectando ao banco de dados...")
    print(f"📍 DATABASE_URI: {DATABASE_URI[:30]}...")
    
    try:
        engine = create_engine(DATABASE_URI)
        # Testar conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            pg_version = result.scalar()
            print(f"✅ Conexão estabelecida!")
            print(f"🗄️  PostgreSQL: {pg_version.split(',')[0]}\n")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Verificar tabelas existentes
    tabelas_faltando = verificar_tabelas_existentes(engine)
    
    # Migrations a executar
    migrations = []
    
    # Migration 1: Tabelas de validação
    if any(t in ['indicador_operacao_ibs_cbs', 'classificacao_tributaria_nfse', 'cst_ibs_cbs'] 
           for t in tabelas_faltando):
        migrations.append({
            'arquivo': 'migrations/add_tabelas_validacao_nfse_nt007.sql',
            'descricao': 'MIGRATION 1: Tabelas de Validação AnexoVII',
            'tabelas': ['indicador_operacao_ibs_cbs', 'classificacao_tributaria_nfse', 'cst_ibs_cbs']
        })
    
    # Migration 2: Tabela NBS
    if 'nomenclatura_brasileira_servicos' in tabelas_faltando:
        migrations.append({
            'arquivo': 'migrations/add_tabela_nbs_servicos.sql',
            'descricao': 'MIGRATION 2: Tabela NBS (Nomenclatura Brasileira de Serviços)',
            'tabelas': ['nomenclatura_brasileira_servicos']
        })
    
    # Executar migrations
    if not migrations:
        print("\n" + "="*70)
        print("✅ TODAS AS TABELAS JÁ EXISTEM!")
        print("="*70)
        print("\n💡 Nenhuma migration necessária. Sistema já está atualizado.")
        return 0
    
    print(f"\n📋 Migrations a executar: {len(migrations)}")
    
    sucesso_total = True
    for i, migration in enumerate(migrations, 1):
        sucesso = executar_migration_arquivo(
            engine, 
            migration['arquivo'], 
            f"{migration['descricao']} ({i}/{len(migrations)})"
        )
        
        if not sucesso:
            sucesso_total = False
            print(f"\n⚠️  Migration {i} falhou. Parando execução.")
            break
    
    # Resumo final
    print("\n" + "="*70)
    if sucesso_total:
        print("✅ TODAS AS MIGRATIONS EXECUTADAS COM SUCESSO!")
        print("="*70)
        print("\n📊 Tabelas criadas:")
        for migration in migrations:
            for tabela in migration['tabelas']:
                print(f"  ✅ {tabela}")
        
        print("\n🚀 Próximos passos:")
        print("  1. Verificar dados inseridos nas tabelas")
        print("  2. Testar API: GET /api/nfse/nbs/search?q=consultoria")
        print("  3. Testar interface: /admin/nfse/emitir")
        print("  4. Popular tabela NBS com dados completos (se necessário)")
        
        return 0
    else:
        print("❌ ERRO NA EXECUÇÃO DAS MIGRATIONS")
        print("="*70)
        print("\n💡 Verifique os logs acima para identificar o problema.")
        print("💡 Execute o script novamente após corrigir os erros.")
        
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

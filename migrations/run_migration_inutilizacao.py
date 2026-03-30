#!/usr/bin/env python3
"""
Script para executar migration de criação da tabela nfe_inutilizacoes
Data: 12/02/2026
"""

import os
import psycopg2
from psycopg2 import sql

# Configuração do banco
DB_HOST = os.getenv("DB_HOST", "nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sjtnfe")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "gMGM!#)NW$nH1w(wrVIdcmn5")

def main():
    print("=" * 80)
    print("MIGRATION: Criação da tabela nfe_inutilizacoes")
    print("=" * 80)
    print()
    
    # Ler arquivo SQL
    migration_file = "migrations/005_create_nfe_inutilizacoes_table.sql"
    print(f"📄 Lendo arquivo: {migration_file}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print(f"✅ Arquivo lido com sucesso ({len(sql_content)} caracteres)")
    print()
    
    # Conectar ao banco
    print("🔌 Conectando ao banco de dados...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        print(f"✅ Conectado: {DB_NAME}@{DB_HOST}")
        print()
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return
    
    try:
        # Verificar se tabela já existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'nfe_inutilizacoes'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("⚠️  Tabela 'nfe_inutilizacoes' já existe!")
            print()
            response = input("Deseja recriar a tabela? (s/N): ").strip().lower()
            if response == 's':
                print("🗑️  Dropando tabela existente...")
                cursor.execute("DROP TABLE IF EXISTS nfe_inutilizacoes CASCADE;")
                conn.commit()
                print("✅ Tabela removida")
                print()
            else:
                print("❌ Operação cancelada pelo usuário")
                return
        
        # Executar migration
        print("🚀 Executando migration...")
        cursor.execute(sql_content)
        conn.commit()
        print("✅ Migration executada com sucesso!")
        print()
        
        # Verificar estrutura criada
        print("📊 Estrutura da tabela criada:")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'nfe_inutilizacoes'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        for col in columns:
            col_name, data_type, nullable, default = col
            null_str = "NULL" if nullable == 'YES' else "NOT NULL"
            default_str = f" DEFAULT {default}" if default else ""
            print(f"  • {col_name:<25} {data_type:<15} {null_str:<10}{default_str}")
        
        print()
        print("📈 Índices criados:")
        print("-" * 80)
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'nfe_inutilizacoes'
            ORDER BY indexname;
        """)
        
        indexes = cursor.fetchall()
        for idx_name, idx_def in indexes:
            print(f"  • {idx_name}")
        
        print()
        print("=" * 80)
        print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Erro ao executar migration: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Conexão fechada")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Script para aplicar migração de campos da Reforma Tributária na tabela NFS-e
Adiciona campos obrigatórios para IBS/CBS conforme LC 214/2025
Data: 30/01/2026
"""

import psycopg2
from psycopg2 import sql
import os
import sys
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SQLALCHEMY_DATABASE_URL

def get_connection():
    """Cria uma conexão direta com o banco de dados"""
    # Converter URL do SQLAlchemy para psycopg2
    # De: postgresql://user:pass@host:port/dbname
    # Para: psycopg2.connect(host=..., database=..., user=..., password=...)
    
    # URL simples
    if SQLALCHEMY_DATABASE_URL.startswith('postgresql://'):
        url = SQLALCHEMY_DATABASE_URL.replace('postgresql://', '')
        
        # Parse da URL
        if '@' in url:
            credentials, location = url.split('@')
            user, password = credentials.split(':')
            location_parts = location.split('/')
            host_port = location_parts[0]
            database = location_parts[1] if len(location_parts) > 1 else 'sjtnfe'
            
            if ':' in host_port:
                host, port = host_port.split(':')
            else:
                host = host_port
                port = '5432'
        else:
            # Sem credenciais na URL, usar localhost
            host = 'localhost'
            port = '5432'
            database = 'sjtnfe'
            user = 'postgres'
            password = ''
        
        return psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
    else:
        # Fallback para conexão local padrão
        return psycopg2.connect(
            host='localhost',
            port='5432',
            database='sjtnfe',
            user='postgres',
            password=''
        )

def executar_migration():
    """Executa a migration para adicionar campos da Reforma Tributária"""
    
    print("=" * 80)
    print("🚀 MIGRAÇÃO - Campos Reforma Tributária (LC 214/2025) - NFS-e")
    print("=" * 80)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Caminho do arquivo SQL
    migration_file = os.path.join(
        os.path.dirname(__file__),
        'add_nfse_reforma_tributaria_campos.sql'
    )
    
    if not os.path.exists(migration_file):
        print(f"❌ ERRO: Arquivo de migração não encontrado: {migration_file}")
        return False
    
    try:
        # Conectar ao banco de dados
        print("🔌 Conectando ao banco de dados...")
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ler o arquivo SQL
        print(f"📖 Lendo migração: {os.path.basename(migration_file)}")
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Executar a migração
        print("⚙️  Executando migração...")
        cursor.execute(sql_script)
        conn.commit()
        
        # Verificar campos adicionados
        print("\n✅ Migração executada com sucesso!")
        print("\n📋 Verificando campos adicionados:")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                column_default,
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'nfse' 
                AND column_name IN (
                    'codigo_nbs',
                    'finalidade_nfse',
                    'indicador_consumidor_final',
                    'codigo_indicador_operacao',
                    'indicador_destinatario',
                    'cst_ibs_cbs',
                    'codigo_classificacao_tributaria',
                    'codigo_localidade_incidencia',
                    'percentual_redutor',
                    'percentual_total_tributos_federais',
                    'percentual_total_tributos_estaduais',
                    'percentual_total_tributos_municipais',
                    'regime_especial_tributacao',
                    'optante_simples_nacional',
                    'incentivador_cultural'
                )
            ORDER BY ordinal_position;
        """)
        
        campos = cursor.fetchall()
        
        print(f"{'Campo':<40} {'Tipo':<20} {'Default':<20} {'Nullable'}")
        print("-" * 80)
        
        for campo in campos:
            nome, tipo, default, nullable = campo
            default_str = str(default)[:18] if default else '-'
            print(f"{nome:<40} {tipo:<20} {default_str:<20} {nullable}")
        
        print("-" * 80)
        print(f"✅ Total de {len(campos)} campos adicionados/verificados")
        
        # Contar registros na tabela
        cursor.execute("SELECT COUNT(*) FROM nfse")
        result = cursor.fetchone()
        total_nfse = result[0] if result else 0
        print(f"\n📊 Total de registros na tabela nfse: {total_nfse}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        print("\n📝 Próximos passos:")
        print("   1. ✅ Campos adicionados no banco de dados")
        print("   2. 🔄 Atualizar o modelo Python (nfse_model.py)")
        print("   3. 🔄 Atualizar o service de NFS-e para incluir os novos campos")
        print("   4. 🔄 Atualizar as rotas para processar os dados do formulário")
        print("   5. ✅ Testar emissão de NFS-e com os novos campos")
        print()
        
        return True
        
    except psycopg2.Error as e:
        print(f"\n❌ ERRO ao executar migração: {e}")
        print(f"Código do erro: {e.pgcode}")
        if conn:
            conn.rollback()
            conn.close()
        return False
        
    except Exception as e:
        print(f"\n❌ ERRO inesperado: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print()
    resposta = input("⚠️  Deseja executar a migração? (s/n): ")
    
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        sucesso = executar_migration()
        sys.exit(0 if sucesso else 1)
    else:
        print("❌ Migração cancelada pelo usuário.")
        sys.exit(1)

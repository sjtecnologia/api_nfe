#!/usr/bin/env python3
"""
Migration para corrigir nomes de colunas da tabela nfse
De Tomadores_* (maiúsculo) para tomador_* (minúsculo)
Data: 30/01/2026
"""

from config.settings import SQLALCHEMY_DATABASE_URL
import psycopg2
from urllib.parse import urlparse

def main():
    # Parse da URL
    result = urlparse(SQLALCHEMY_DATABASE_URL.replace('postgresql://', 'postgres://'))
    conn = psycopg2.connect(
        host=result.hostname,
        port=result.port or 5432,
        database=result.path[1:],
        user=result.username,
        password=result.password
    )
    
    cursor = conn.cursor()
    
    # Lista de colunas para renomear
    colunas = [
        ('Tomadores_id', 'tomador_id'),
        ('Tomadores_cpf_cnpj', 'tomador_cpf_cnpj'),
        ('Tomadores_razao_social', 'tomador_razao_social'),
        ('Tomadores_inscricao_municipal', 'tomador_inscricao_municipal'),
        ('Tomadores_endereco', 'tomador_endereco'),
        ('Tomadores_email', 'tomador_email'),
        ('Tomadores_telefone', 'tomador_telefone')
    ]
    
    print("🔄 Renomeando colunas da tabela nfse...")
    
    for old_name, new_name in colunas:
        try:
            sql = f"ALTER TABLE nfse RENAME COLUMN {old_name} TO {new_name}"
            cursor.execute(sql)
            print(f"✅ {old_name} → {new_name}")
        except Exception as e:
            if "does not exist" in str(e):
                print(f"⚠️ Coluna {old_name} já foi renomeada ou não existe")
            else:
                print(f"❌ Erro ao renomear {old_name}: {e}")
    
    conn.commit()
    
    # Verificar colunas finais
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'nfse' 
          AND column_name LIKE 'tomador%'
        ORDER BY column_name
    """)
    
    print("\n📋 Colunas do tomador na tabela nfse:")
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]}")
    
    cursor.close()
    conn.close()
    print("\n✅ Migration concluída com sucesso!")

if __name__ == "__main__":
    main()

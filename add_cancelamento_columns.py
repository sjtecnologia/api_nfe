#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para adicionar colunas de cancelamento na tabela nfe_emitidas
"""

import psycopg2
from psycopg2 import sql

# Configurações do banco
DB_CONFIG = {
    'host': 'nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'sjtnfe',
    'user': 'postgres',
    'password': 'gMGM!#)NW$nH1w(wrVIdcmn5'
}

def add_columns():
    """Adiciona colunas para armazenar dados de cancelamento"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Conectado ao banco de dados")
        
        # Verificar se as colunas já existem
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'nfe_emitidas'
            AND column_name IN (
                'protocolo_cancelamento',
                'data_cancelamento',
                'justificativa_cancelamento',
                'xml_cancelamento'
            )
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Colunas existentes: {existing_columns}")
        
        # Adicionar colunas que não existem
        alterations = []
        
        if 'protocolo_cancelamento' not in existing_columns:
            alterations.append("ADD COLUMN protocolo_cancelamento VARCHAR(20)")
            
        if 'data_cancelamento' not in existing_columns:
            alterations.append("ADD COLUMN data_cancelamento TIMESTAMP")
            
        if 'justificativa_cancelamento' not in existing_columns:
            alterations.append("ADD COLUMN justificativa_cancelamento TEXT")
            
        if 'xml_cancelamento' not in existing_columns:
            alterations.append("ADD COLUMN xml_cancelamento TEXT")
        
        if alterations:
            alter_sql = f"ALTER TABLE nfe_emitidas {', '.join(alterations)}"
            print(f"\nExecutando: {alter_sql}")
            
            cursor.execute(alter_sql)
            conn.commit()
            
            print(f"✓ {len(alterations)} coluna(s) adicionada(s) com sucesso!")
        else:
            print("✓ Todas as colunas já existem")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    add_columns()

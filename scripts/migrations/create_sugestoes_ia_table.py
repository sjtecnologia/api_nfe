#!/usr/bin/env python3
"""Script para criar tabela sugestoes_ia"""

from database.connection import get_db
from sqlalchemy import text

def create_sugestoes_ia_table():
    db = next(get_db())
    try:
        # Verifica se a tabela já existe
        check = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sugestoes_ia'
            )
        """)).fetchone()
        
        if check and check[0]:
            print("✓ Tabela 'sugestoes_ia' já existe")
            return
        
        # Cria a tabela (sem FK para evitar problemas)
        db.execute(text("""
            CREATE TABLE sugestoes_ia (
                sugestao_id SERIAL PRIMARY KEY,
                produto_id BIGINT,
                cliente_id BIGINT,
                
                descricao_produto TEXT NOT NULL,
                ncm_sugerido VARCHAR(10),
                ncm_confianca DECIMAL(5,2),
                cest_sugerido VARCHAR(10),
                cest_confianca DECIMAL(5,2),
                cst_sugerido VARCHAR(5),
                csosn_sugerido VARCHAR(5),
                cfop_sugerido VARCHAR(5),
                
                sugestao_aceita BOOLEAN DEFAULT NULL,
                
                data_sugestao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tempo_resposta_ms INTEGER
            )
        """))
        
        # Cria índices
        db.execute(text("CREATE INDEX idx_sugestoes_produto ON sugestoes_ia(produto_id)"))
        db.execute(text("CREATE INDEX idx_sugestoes_cliente ON sugestoes_ia(cliente_id)"))
        db.execute(text("CREATE INDEX idx_sugestoes_data ON sugestoes_ia(data_sugestao)"))
        
        db.commit()
        print("✓ Tabela 'sugestoes_ia' criada com sucesso!")
        print("✓ Índices criados")
        
    except Exception as e:
        db.rollback()
        print(f"[X] Erro ao criar tabela: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    create_sugestoes_ia_table()

#!/usr/bin/env python3
"""Script de teste rápido para verificar dados de origens de mercadoria"""

from database.connection import get_db
from sqlalchemy import text

def test_origens():
    db = next(get_db())
    try:
        rows = db.execute(text("""
            SELECT origem_id, codigo, descricao 
            FROM origens_mercadoria 
            ORDER BY codigo
        """)).fetchall()
        
        print(f"✓ Total de Origens de Mercadoria: {len(rows)}")
        print("\nPrimeiras 10 origens:")
        print("-" * 80)
        
        for row in rows[:10]:
            print(f"ID: {row[0]:2d} | Código: {row[1]:2s} | Descrição: {row[2]}")
        
        if len(rows) == 0:
            print("\n[!]  AVISO: Nenhuma origem encontrada no banco!")
            print("As origens padrão são:")
            print("0 - Nacional")
            print("1 - Estrangeira - Importação direta")
            print("2 - Estrangeira - Adquirida no mercado interno")
            
    except Exception as e:
        print(f"[X] Erro ao consultar origens: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    test_origens()

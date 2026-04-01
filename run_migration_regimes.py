#!/usr/bin/env python3
"""Executar migration para popular regimes_tributarios"""
import sys
sys.path.insert(0, '/home/ubuntu/api_nfe')

from app import app
from database.connection import SessionLocal
from sqlalchemy import text

print("="*70)
print("MIGRATION: Popular regimes_tributarios")
print("="*70)

with app.app_context():
    db = SessionLocal()
    try:
        # Ler o SQL da migration
        with open('/home/ubuntu/api_nfe/migrations/002_popular_regimes_tributarios.sql', 'r') as f:
            sql = f.read()
        
        print("\nExecutando migration...")
        db.execute(text(sql))
        db.commit()
        
        print("\n✅ Migration executada com sucesso!")
        
        # Verificar resultado
        result = db.execute(text("SELECT regime_tributario_id, nome FROM regimes_tributarios ORDER BY regime_tributario_id")).fetchall()
        print(f"\nRegimes cadastrados: {len(result)}")
        for row in result:
            print(f"  ID {row[0]}: {row[1]}")
            
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

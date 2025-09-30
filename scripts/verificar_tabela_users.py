import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verificar_tabela_users():
    """Verificar estrutura da tabela users"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Ver estrutura da tabela users
        colunas_result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """))
        
        print("📋 COLUNAS DA TABELA 'users':")
        print("="*50)
        for row in colunas_result:
            nullable = "NULL" if row.is_nullable == 'YES' else "NOT NULL"
            print(f"  {row.column_name:<25} {row.data_type:<15} {nullable}")
        
        # Ver alguns registros
        users_result = db.execute(text("""
            SELECT * FROM users LIMIT 3
        """))
        
        print(f"\n📋 REGISTROS DA TABELA 'users':")
        print("="*50)
        for row in users_result:
            for key, value in row._mapping.items():
                if key == 'password_hash':
                    print(f"  {key:<25}: [HASH OCULTO]")
                else:
                    print(f"  {key:<25}: {value}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    verificar_tabela_users()
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verificar_colunas_clientes():
    """Verificar colunas da tabela clientes"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Verificar estrutura da tabela
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'clientes'
            ORDER BY ordinal_position;
        """))
        
        print("📋 COLUNAS DA TABELA 'clientes':")
        print("="*50)
        for row in result:
            nullable = "NULL" if row.is_nullable == 'YES' else "NOT NULL"
            print(f"  {row.column_name:<20} {row.data_type:<15} {nullable}")
        
        print("\n📋 DADOS DO CLIENTE ID=5:")
        print("="*50)
        cliente_result = db.execute(text("""
            SELECT * FROM clientes WHERE cliente_id = 5
        """))
        
        cliente = cliente_result.first()
        if cliente:
            for key, value in cliente._mapping.items():
                print(f"  {key:<20}: {value}")
        else:
            print("❌ Cliente ID=5 não encontrado")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    verificar_colunas_clientes()
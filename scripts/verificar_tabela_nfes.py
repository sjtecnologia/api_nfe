import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verificar_tabela_nfes():
    """Verificar se tabela nfe_emitidas existe e suas colunas"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Verificar se tabela existe
        try:
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'nfe_emitidas' 
                AND table_schema = 'public'
            """))
            
            if result.first():
                print("✅ TABELA 'nfe_emitidas' EXISTE")
                
                # Ver estrutura da tabela
                colunas_result = db.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'nfe_emitidas'
                    ORDER BY ordinal_position;
                """))
                
                print("\n📋 COLUNAS DA TABELA 'nfe_emitidas':")
                print("="*50)
                for row in colunas_result:
                    nullable = "NULL" if row.is_nullable == 'YES' else "NOT NULL"
                    print(f"  {row.column_name:<25} {row.data_type:<15} {nullable}")
                
                # Ver quantos registros tem
                count_result = db.execute(text("SELECT COUNT(*) as total FROM nfe_emitidas"))
                total = count_result.first().total
                print(f"\n📊 TOTAL DE REGISTROS: {total}")
                
                if total > 0:
                    # Ver alguns registros do cliente 5
                    sample_result = db.execute(text("""
                        SELECT * FROM nfe_emitidas 
                        WHERE cliente_id = 5 
                        LIMIT 3
                    """))
                    
                    print(f"\n📋 PRIMEIROS REGISTROS DO CLIENTE 5:")
                    print("="*50)
                    for row in sample_result:
                        for key, value in row._mapping.items():
                            print(f"  {key:<25}: {value}")
                        print("-" * 50)
                        
            else:
                print("⚠️  TABELA 'nfe_emitidas' NÃO EXISTE")
                
                # Ver que tabelas existem com 'nfe' no nome
                tables_result = db.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name LIKE '%nfe%' 
                    AND table_schema = 'public'
                """))
                
                print("\n📋 TABELAS COM 'nfe' NO NOME:")
                for row in tables_result:
                    print(f"  - {row.table_name}")
                    
        except Exception as table_error:
            print(f"❌ Erro ao verificar tabela: {table_error}")
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    verificar_tabela_nfes()
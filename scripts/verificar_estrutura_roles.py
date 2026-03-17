import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verificar_estrutura_roles():
    """Verificar estrutura real das tabelas de roles e users"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🔍 VERIFICANDO ESTRUTURA DAS TABELAS DE AUTH")
        print("="*60)
        
        # Tabelas relacionadas à autenticação
        tabelas_auth = ['roles', 'users', 'user_roles', 'user_clients', 'permissions', 'role_permissions']
        
        for tabela in tabelas_auth:
            print(f"\n📋 ESTRUTURA DA TABELA '{tabela}':")
            print("-" * 50)
            
            try:
                # Ver colunas da tabela
                colunas_result = db.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = :tabela
                    ORDER BY ordinal_position;
                """), {"tabela": tabela})
                
                colunas = []
                for row in colunas_result:
                    nullable = "NULL" if row.is_nullable == 'YES' else "NOT NULL"
                    print(f"  {row.column_name:<25} {row.data_type:<15} {nullable}")
                    colunas.append(row.column_name)
                
                if not colunas:
                    print("  ❌ TABELA NÃO EXISTE")
                    continue
                
                # Ver registros se existirem
                count_result = db.execute(text(f"SELECT COUNT(*) as total FROM {tabela}"))
                total = count_result.first().total
                print(f"\n📊 REGISTROS: {total}")
                
                # Se tem registros, mostrar alguns
                if total > 0 and total <= 10:
                    print(f"📋 DADOS DE {tabela}:")
                    dados_result = db.execute(text(f"SELECT * FROM {tabela} LIMIT 5"))
                    for registro in dados_result:
                        print("  " + "-" * 40)
                        for key, value in registro._mapping.items():
                            print(f"  {key:<20}: {value}")
                
            except Exception as tabela_error:
                print(f"❌ Erro ao verificar tabela {tabela}: {tabela_error}")
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    verificar_estrutura_roles()
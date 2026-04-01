import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verificar_estrutura_tabelas():
    """Verificar estrutura das tabelas principais"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Tabelas para verificar
        tabelas_principais = [
            'produtos', 'destinatarios_nfe', 'regras_tributacao', 
            'certificados_digitais', 'nfe_emitidas', 'clientes'
        ]
        
        for tabela in tabelas_principais:
            print(f"\n📋 ESTRUTURA DA TABELA '{tabela}':")
            print("="*60)
            
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
                
                # Ver se tem registros
                count_result = db.execute(text(f"SELECT COUNT(*) as total FROM {tabela}"))
                total = count_result.first().total
                print(f"\n📊 TOTAL DE REGISTROS: {total}")
                
                # Verificar se tem coluna 'ativo'
                tem_ativo = 'ativo' in colunas
                tem_is_active = '_is_active' in colunas
                print(f"🔍 Tem coluna 'ativo': {'✅ SIM' if tem_ativo else '❌ NÃO'}")
                print(f"🔍 Tem coluna '_is_active': {'✅ SIM' if tem_is_active else '❌ NÃO'}")
                
                if total > 0 and tabela == 'destinatarios_nfe':
                    # Ver alguns registros da tabela destinatarios_nfe
                    print(f"\n📋 PRIMEIROS REGISTROS DE {tabela}:")
                    registros_result = db.execute(text(f"SELECT * FROM {tabela} LIMIT 3"))
                    for registro in registros_result:
                        for key, value in registro._mapping.items():
                            print(f"  {key:<25}: {value}")
                        print("-" * 50)
                
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
    verificar_estrutura_tabelas()
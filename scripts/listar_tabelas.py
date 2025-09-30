import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def listar_tabelas():
    """Listar todas as tabelas do banco"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Listar todas as tabelas
        tabelas_result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        
        print("📋 TODAS AS TABELAS NO BANCO:")
        print("="*50)
        
        tabelas = []
        for row in tabelas_result:
            tabela = row.table_name
            tabelas.append(tabela)
            print(f"  • {tabela}")
        
        print(f"\n📊 TOTAL: {len(tabelas)} tabelas")
        
        # Verificar especificamente as que esperamos
        tabelas_esperadas = [
            'produtos', 'destinatarios', 'regras_tributacao', 
            'certificados_digitais', 'nfe_emitidas', 'clientes'
        ]
        
        print("\n🔍 VERIFICAÇÃO DAS TABELAS ESPERADAS:")
        print("="*50)
        
        for tabela in tabelas_esperadas:
            status = "✅ EXISTE" if tabela in tabelas else "❌ NÃO EXISTE"
            print(f"  {tabela:<25} {status}")
            
            # Se existe, mostrar quantos registros tem
            if tabela in tabelas:
                try:
                    count_result = db.execute(text(f"SELECT COUNT(*) as total FROM {tabela}"))
                    total = count_result.first().total
                    print(f"    └─ {total} registros")
                except Exception as e:
                    print(f"    └─ Erro ao contar: {e}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    listar_tabelas()
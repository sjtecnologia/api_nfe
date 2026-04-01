import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db
from sqlalchemy import text

def verificar_tabelas():
    """Verificar tabelas existentes no banco"""
    
    try:
        db = next(get_db())
        
        # Listar todas as tabelas
        tabelas = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)).fetchall()
        
        print("📋 TABELAS EXISTENTES NO BANCO:")
        print("-" * 50)
        for tabela in tabelas:
            print(f"• {tabela.table_name}")
        print("-" * 50)
        
        # Verificar estrutura das tabelas relacionadas a usuários
        print("\n🔍 PROCURANDO TABELAS RELACIONADAS A USUÁRIOS:")
        for tabela in tabelas:
            nome_tabela = tabela.table_name
            if 'user' in nome_tabela.lower() or 'usuario' in nome_tabela.lower():
                print(f"\n📝 Estrutura da tabela '{nome_tabela}':")
                colunas = db.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{nome_tabela}'
                    ORDER BY ordinal_position
                """)).fetchall()
                
                for coluna in colunas:
                    nullable = "NULL" if coluna.is_nullable == "YES" else "NOT NULL"
                    print(f"  - {coluna.column_name}: {coluna.data_type} ({nullable})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {str(e)}")
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🔍 VERIFICANDO ESTRUTURA DO BANCO")
    print("="*40)
    verificar_tabelas()
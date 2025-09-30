import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import check_password_hash
from database.connection import get_db
from sqlalchemy import text

def testar_login():
    """Testar o processo de login"""
    
    try:
        db = next(get_db())
        
        username = "sjtec"
        password = "ma0610"
        
        # Buscar usuário
        user = db.execute(text("""
            SELECT u.id, u.username, u.password_hash, u._is_active, u.email,
                   uc.client_id, c.razao_social
            FROM users u
            LEFT JOIN user_clients uc ON u.id = uc.user_id
            LEFT JOIN clientes c ON uc.client_id = c.cliente_id
            WHERE u.username = :username
        """), {"username": username}).first()
        
        if not user:
            print("❌ Usuário não encontrado")
            return False
        
        print("✅ DADOS DO USUÁRIO:")
        print(f"ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Ativo: {user._is_active}")
        print(f"Cliente ID: {user.client_id}")
        print(f"Cliente: {user.razao_social}")
        
        # Testar senha
        password_ok = check_password_hash(user.password_hash, password)
        print(f"\n🔐 TESTE DE SENHA:")
        print(f"Senha correta: {password_ok}")
        
        if password_ok and user._is_active:
            print("\n✅ LOGIN DEVERIA FUNCIONAR!")
        else:
            print("\n❌ PROBLEMA NO LOGIN!")
            
        return password_ok and user._is_active
        
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🔍 TESTANDO LOGIN")
    print("="*30)
    testar_login()
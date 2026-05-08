
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db
from sqlalchemy import text

def verificar_usuario():
    try:
        db = next(get_db())
        
        # Verificar usuário criado
        user = db.execute(text("""
            SELECT u.id, u.username, u._is_active, u.email,
                   uc.client_id
            FROM users u
            LEFT JOIN user_clients uc ON u.id = uc.user_id
            WHERE u.username = 'sjtec'
        """)).first()
        
        if user:
            print("✅ USUÁRIO ENCONTRADO:")
            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Ativo: {user._is_active}")
            print(f"Email: {user.email}")
            print(f"Cliente ID: {user.client_id}")
        else:
            print("❌ Usuário não encontrado")
        
        # Verificar cliente
        cliente = db.execute(text("""
            SELECT cliente_id, razao_social, ativo
            FROM clientes 
            WHERE cliente_id = 5
        """)).first()
        
        if cliente:
            print(f"\n✅ CLIENTE ENCONTRADO:")
            print(f"ID: {cliente.cliente_id}")
            print(f"Razão Social: {cliente.razao_social}")
            print(f"Ativo: {cliente.ativo}")
        else:
            print("❌ Cliente não encontrado")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    verificar_usuario()
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def testar_importacoes():
    """Testar se todas as importações funcionam"""
    try:
        print("🔍 TESTANDO IMPORTAÇÕES...")
        
        # Testar modelo User
        from models.user import User
        print("✅ models.user importado com sucesso")
        
        # Testar autenticação
        user = User.authenticate('sjtec', 'ma0610')
        if user:
            print(f"✅ Autenticação funcionou: {user.username} (Cliente: {user.client_id})")
        else:
            print("❌ Falha na autenticação")
        
        # Testar user_loader
        if user:
            loaded_user = User.load_user(user.id)
            if loaded_user:
                print(f"✅ User loader funcionou: {loaded_user.username}")
            else:
                print("❌ Falha no user loader")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nas importações: {e}")
        return False

if __name__ == "__main__":
    print("🧪 TESTE COMPLETO DO SISTEMA DE LOGIN")
    print("="*50)
    testar_importacoes()
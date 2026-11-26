import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def testar_user_model():
    """Testar o modelo User"""
    try:
        from models.user import User
        print("✅ Modelo User importado com sucesso")
        
        # Testar autenticação
        print("\n🔐 TESTANDO AUTENTICAÇÃO:")
        user = User.authenticate('sjtec', 'ma0610')
        if user:
            print(f"✅ Autenticação OK: {user.username}")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Ativo: {user.is_active()}")
            print(f"   Admin: {user.is_admin()}")
            print(f"   Clientes: {len(user.clients)}")
            
            if user.clients:
                for client in user.clients:
                    print(f"   - Cliente: {client['razao_social']} (ID: {client['cliente_id']})")
            
            # Testar método get
            print(f"\n🔄 TESTANDO USER.GET({user.id}):")
            loaded_user = User.get(user.id)
            if loaded_user:
                print(f"✅ User.get() OK: {loaded_user.username}")
            else:
                print("❌ User.get() falhou")
                
        else:
            print("❌ Falha na autenticação")
        
        return user is not None
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 TESTANDO MODELO USER")
    print("="*40)
    testar_user_model()
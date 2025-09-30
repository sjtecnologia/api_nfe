import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verificar_roles_usuarios():
    """Verificar roles e usuários no sistema"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🔍 VERIFICANDO ROLES E USUÁRIOS")
        print("="*60)
        
        # 1. ROLES EXISTENTES
        print("\n📋 ROLES CADASTRADAS:")
        roles_result = db.execute(text("SELECT * FROM roles ORDER BY role_id"))
        roles = [dict(row._mapping) for row in roles_result]
        
        for role in roles:
            print(f"  • ID: {role['role_id']} | Nome: {role['role_name']} | Descrição: {role.get('description', 'N/A')}")
        
        # 2. USUÁRIOS EXISTENTES
        print(f"\n👥 USUÁRIOS CADASTRADOS:")
        users_result = db.execute(text("SELECT * FROM users ORDER BY user_id"))
        users = [dict(row._mapping) for row in users_result]
        
        for user in users:
            print(f"  • ID: {user['user_id']} | Username: {user['username']} | Email: {user.get('email', 'N/A')}")
        
        # 3. ASSOCIAÇÕES USER_ROLES
        print(f"\n🔗 ASSOCIAÇÕES USER_ROLES:")
        user_roles_result = db.execute(text("""
            SELECT ur.user_id, ur.role_id, u.username, r.role_name
            FROM user_roles ur
            LEFT JOIN users u ON ur.user_id = u.user_id
            LEFT JOIN roles r ON ur.role_id = r.role_id
            ORDER BY ur.user_id
        """))
        
        user_roles = [dict(row._mapping) for row in user_roles_result]
        
        if user_roles:
            for ur in user_roles:
                print(f"  • User: {ur['username']} (ID:{ur['user_id']}) → Role: {ur['role_name']} (ID:{ur['role_id']})")
        else:
            print("  ❌ NENHUMA ASSOCIAÇÃO ENCONTRADA!")
        
        # 4. ASSOCIAÇÕES USER_CLIENTS
        print(f"\n🏢 ASSOCIAÇÕES USER_CLIENTS:")
        user_clients_result = db.execute(text("""
            SELECT uc.user_id, uc.cliente_id, u.username, c.razao_social
            FROM user_clients uc
            LEFT JOIN users u ON uc.user_id = u.user_id
            LEFT JOIN clientes c ON uc.cliente_id = c.cliente_id
            ORDER BY uc.user_id
        """))
        
        user_clients = [dict(row._mapping) for row in user_clients_result]
        
        if user_clients:
            for uc in user_clients:
                print(f"  • User: {uc['username']} (ID:{uc['user_id']}) → Cliente: {uc['razao_social']} (ID:{uc['cliente_id']})")
        else:
            print("  ❌ NENHUMA ASSOCIAÇÃO ENCONTRADA!")
        
        print("\n" + "="*60)
        print("📊 RESUMO:")
        print(f"  • {len(roles)} roles cadastradas")
        print(f"  • {len(users)} usuários cadastrados")
        print(f"  • {len(user_roles)} associações user_roles")
        print(f"  • {len(user_clients)} associações user_clients")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    verificar_roles_usuarios()
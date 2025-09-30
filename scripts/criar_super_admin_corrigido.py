import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def criar_super_admin_corrigido():
    """Criar role SUPER_ADMIN com estrutura correta"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🚀 CRIANDO SUPER_ADMIN COM ESTRUTURA CORRETA")
        print("="*55)
        
        # 1. CRIAR ROLE SUPER_ADMIN (se não existir)
        super_admin_check = db.execute(text("""
            SELECT id FROM roles WHERE name = 'Super_Admin'
        """)).first()
        
        if not super_admin_check:
            db.execute(text("""
                INSERT INTO roles (name, description) 
                VALUES ('Super_Admin', 'Super Administrador - Acesso total ao sistema e gerenciamento da plataforma')
            """))
            print("✅ Role 'Super_Admin' criada!")
        else:
            print("ℹ️  Role 'Super_Admin' já existe!")
        
        # Buscar ID da role Super_Admin
        super_admin_role = db.execute(text("""
            SELECT id FROM roles WHERE name = 'Super_Admin'
        """)).first()
        super_admin_role_id = super_admin_role.id
        print(f"📋 Super_Admin role ID: {super_admin_role_id}")
        
        # 2. ASSOCIAR USUÁRIO sjtec (ID: 2) à role Super_Admin
        sjtec_user_id = 2
        
        # Remover qualquer role existente do sjtec
        db.execute(text("""
            DELETE FROM user_roles WHERE user_id = :user_id
        """), {"user_id": sjtec_user_id})
        print("🧹 Roles antigas do sjtec removidas")
        
        # Adicionar role Super_Admin
        db.execute(text("""
            INSERT INTO user_roles (user_id, role_id) 
            VALUES (:user_id, :role_id)
        """), {"user_id": sjtec_user_id, "role_id": super_admin_role_id})
        print(f"✅ sjtec (ID:{sjtec_user_id}) → Super_Admin (ID:{super_admin_role_id})")
        
        # 3. ASSOCIAR USUÁRIO admin (ID: 1) à role Super_Admin também
        admin_user_id = 1
        
        # Verificar se admin já tem a role
        existing_admin_role = db.execute(text("""
            SELECT * FROM user_roles WHERE user_id = :user_id AND role_id = :role_id
        """), {"user_id": admin_user_id, "role_id": super_admin_role_id}).first()
        
        if not existing_admin_role:
            db.execute(text("""
                INSERT INTO user_roles (user_id, role_id) 
                VALUES (:user_id, :role_id)
            """), {"user_id": admin_user_id, "role_id": super_admin_role_id})
            print(f"✅ admin (ID:{admin_user_id}) → Super_Admin (ID:{super_admin_role_id})")
        else:
            print("ℹ️  admin já tem role Super_Admin")
        
        # 4. VERIFICAR ASSOCIAÇÕES CLIENT (corrigir client_id vs cliente_id)
        print("\n🏢 VERIFICANDO ASSOCIAÇÕES DE CLIENTES:")
        
        # sjtec já está associado ao client_id 5
        sjtec_client_check = db.execute(text("""
            SELECT client_id FROM user_clients WHERE user_id = :user_id
        """), {"user_id": sjtec_user_id}).fetchall()
        
        print(f"📋 sjtec associado aos clientes: {[row.client_id for row in sjtec_client_check]}")
        
        # 5. COMMIT DAS ALTERAÇÕES
        db.commit()
        
        # 6. MOSTRAR RESULTADO FINAL
        print("\n" + "="*55)
        print("🎯 ESTRUTURA CRIADA COM SUCESSO!")
        
        # Mostrar todas as roles
        print("\n📋 ROLES FINAIS:")
        roles_result = db.execute(text("SELECT id, name, description FROM roles ORDER BY id"))
        for role in roles_result:
            print(f"  {role.id}. {role.name} - {role.description}")
        
        # Mostrar associações user_roles
        print("\n🔗 ASSOCIAÇÕES USER_ROLES:")
        user_roles_result = db.execute(text("""
            SELECT ur.user_id, ur.role_id, u.username, r.name as role_name
            FROM user_roles ur
            JOIN users u ON ur.user_id = u.id
            JOIN roles r ON ur.role_id = r.id
            ORDER BY ur.user_id
        """))
        
        for ur in user_roles_result:
            print(f"  • {ur.username} (ID:{ur.user_id}) → {ur.role_name} (ID:{ur.role_id})")
        
        print("\n✅ sjtec agora tem acesso total como Super_Admin!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    criar_super_admin_corrigido()
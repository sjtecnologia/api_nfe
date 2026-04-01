import os
import re

def get_permission_mapping():
    """Mapeia permissões antigas para as novas do banco"""
    return {
        'admin.clientes.create': 'clients.create',
        'admin.clientes.read': 'clients.read',
        'admin.clientes.update': 'clients.edit',
        'admin.clientes.delete': 'clients.delete',
        
        'admin.produtos.create': 'products.create',
        'admin.produtos.read': 'products.read',
        'admin.produtos.update': 'products.edit',
        'admin.produtos.delete': 'products.delete',
        
        'admin.certificados.create': 'certificates.create',
        'admin.certificados.read': 'certificates.read',
        'admin.certificados.update': 'certificates.edit',
        'admin.certificados.delete': 'certificates.delete',
        
        'admin.nfe.read': 'nfe.read',
        'admin.nfe.create': 'nfe.issue',
        'admin.nfe.update': 'nfe.edit',
        'admin.nfe.delete': 'nfe.delete',
        
        'admin.users.create': 'users.create',
        'admin.users.read': 'users.read',
        'admin.users.update': 'users.edit',
        'admin.users.delete': 'users.delete',
        
        'admin.roles.create': 'roles.create',
        'admin.roles.read': 'roles.read',
        'admin.roles.update': 'roles.edit',
        'admin.roles.delete': 'roles.delete',
        
        'admin.regras.create': 'rules.create',
        'admin.regras.read': 'rules.read',
        'admin.regras.update': 'rules.edit',
        'admin.regras.delete': 'rules.delete',
        
        'admin.tributacao.read': 'motivos_desoneracao.read',
        'admin.tributacao.create': 'motivos_desoneracao.create',
        'admin.tributacao.update': 'motivos_desoneracao.edit',
        'admin.tributacao.delete': 'motivos_desoneracao.delete',
    }

def update_permissions_in_file(file_path, permission_mapping):
    """Atualiza permissões em um arquivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Buscar padrões has_permission('...')
        for old_perm, new_perm in permission_mapping.items():
            patterns = [
                f"has_permission('{old_perm}')",
                f'has_permission("{old_perm}")',
                f"permission_required('{old_perm}')",
                f'permission_required("{old_perm}")',
            ]
            
            for pattern in patterns:
                if pattern in content:
                    replacement = pattern.replace(old_perm, new_perm)
                    content = content.replace(pattern, replacement)
                    changes_made.append(f"{old_perm} → {new_perm}")
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Atualizado: {file_path}")
            for change in changes_made:
                print(f"   🔄 {change}")
            return True
        else:
            print(f"⚪ Sem mudanças: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao atualizar {file_path}: {e}")
        return False

def update_all_permissions():
    """Atualiza todas as permissões"""
    permission_mapping = get_permission_mapping()
    updated_count = 0
    
    print("🔄 Atualizando permissões...\n")
    
    # Atualizar templates
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                if update_permissions_in_file(file_path, permission_mapping):
                    updated_count += 1
    
    # Atualizar routes
    for root, dirs, files in os.walk('routes'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if update_permissions_in_file(file_path, permission_mapping):
                    updated_count += 1
    
    print(f"\n🎉 Atualização concluída! {updated_count} arquivos foram modificados.")

if __name__ == "__main__":
    update_all_permissions()
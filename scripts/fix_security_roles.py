#!/usr/bin/env python3
"""
Script para aplicar correções de segurança baseadas em roles.
Corrige decorators em rotas para respeitar permissões de Viewer/Editor/Admin/Super_Admin.

Autor: GitHub Copilot
Data: 02/01/2026
"""

import re
import os
from pathlib import Path

# Mapeamento de rotas e seus decorators necessários
SECURITY_FIXES = {
    "admin_routes.py": {
        # Rotas que devem ser acessíveis apenas por Admin ou Super_Admin
        "admin_only": [
            "def admin_home",
            "def list_nfes",
            "def list_ncms",
            "def list_cst",
            "def list_cfops",
            "def list_csosn",
            "def list_regimes_tributarios",
            "def list_motivos_desoneracao",
            "def visualizar_cliente",
        ],
        # Rotas POST/DELETE que devem bloquear Viewer
        "block_viewer": [
            "def editar_produto",
            "def duplicar_produto",
            "def edit_ncm",
            "def delete_ncm",
            "def create_ncm",
            "def edit_cst",
            "def delete_cst",
            "def create_cst",
            "def save_cfop",
            "def delete_cfop",
            "def edit_csosn",
            "def delete_csosn",
            "def create_csosn",
            "def salvar_regime_tributario",
            "def delete_regime_tributario",
            "def edit_cliente",
            "def create_cliente",
            "def delete_cliente",
        ],
        # Rotas de gerenciamento que devem ser SOMENTE Super_Admin
        "super_admin_only": [
            "def list_usuarios",
            "def create_usuario",
            "def edit_usuario",
            "def delete_usuario",
            "def list_roles",
            "def create_role",
            "def edit_role",
            "def delete_role",
            "def list_permissions",
            "def create_permission",
            "def edit_permission",
            "def delete_permission",
        ],
    },
    "nfe_routes.py": {
        "block_viewer": [
            "def emitir_nfe",
            "def create",
            "def reenviar_nfe",
            "def emitir_rascunho",
            "def edit",
        ],
        "viewer_allowed": [
            "def list_nfes",
            "def view",
            "def download",
            "def generate_danfe",
        ],
    },
    "cliente_routes.py": {
        "block_viewer": [
            # POST/PUT/DELETE methods
        ],
    },
}

def read_file(filepath):
    """Lê conteúdo do arquivo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Erro ao ler {filepath}: {e}")
        return None

def write_file(filepath, content):
    """Escreve conteúdo no arquivo"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Erro ao escrever {filepath}: {e}")
        return False

def backup_file(filepath):
    """Cria backup do arquivo"""
    backup_path = f"{filepath}.backup"
    try:
        content = read_file(filepath)
        if content:
            write_file(backup_path, content)
            print(f"✅ Backup criado: {backup_path}")
            return True
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
    return False

def add_decorator_to_function(content, function_name, decorator, after_decorator='@login_required'):
    """
    Adiciona um decorator a uma função específica.
    
    Args:
        content: Conteúdo do arquivo
        function_name: Nome da função (ex: 'def editar_produto')
        decorator: Decorator a adicionar (ex: '@admin_required()')
        after_decorator: Adicionar depois deste decorator
    
    Returns:
        Conteúdo modificado
    """
    # Padrão para encontrar a função
    pattern = rf'({after_decorator}\n)(def {function_name.replace("def ", "")})'
    
    # Verificar se o decorator já existe
    decorator_pattern = rf'{decorator}\n.*?{function_name}'
    if re.search(decorator_pattern, content, re.DOTALL):
        print(f"  ⏭️  Decorator {decorator} já existe para {function_name}")
        return content
    
    # Adicionar decorator após @login_required
    replacement = rf'\1{decorator}\n\2'
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        print(f"  ✅ Adicionado {decorator} em {function_name}")
        return new_content
    else:
        print(f"  ⚠️  Não foi possível adicionar {decorator} em {function_name}")
        return content

def add_import_if_missing(content, import_statement):
    """Adiciona import se não existir"""
    if import_statement not in content:
        # Procurar a linha de imports do auth.decorators
        pattern = r'(from auth\.decorators import[^\n]+)'
        match = re.search(pattern, content)
        
        if match:
            # Adicionar à lista de imports existente
            existing_import = match.group(1)
            # Extrair imports atuais
            imports = re.findall(r'import (.+)', existing_import)[0]
            new_imports = imports.strip() + ', ' + import_statement.split('import ')[1]
            new_import_line = f"from auth.decorators import {new_imports}"
            content = content.replace(existing_import, new_import_line)
            print(f"  ✅ Adicionado import: {import_statement.split('import ')[1]}")
        else:
            # Adicionar nova linha de import
            # Procurar o primeiro import do auth
            auth_import_pattern = r'(from auth\.[^\n]+\n)'
            match = re.search(auth_import_pattern, content)
            if match:
                content = content.replace(match.group(1), match.group(1) + import_statement + '\n')
                print(f"  ✅ Adicionado novo import: {import_statement}")
    
    return content

def fix_admin_routes(filepath):
    """Aplica correções no arquivo admin_routes.py"""
    print(f"\n🔧 Corrigindo {filepath}...")
    
    content = read_file(filepath)
    if not content:
        return False
    
    # Criar backup
    backup_file(filepath)
    
    # Adicionar imports necessários
    content = add_import_if_missing(content, "from auth.decorators import admin_required, super_admin_required, block_viewer_access")
    
    fixes = SECURITY_FIXES.get("admin_routes.py", {})
    
    # Adicionar @admin_required() em rotas admin_only
    for func in fixes.get("admin_only", []):
        content = add_decorator_to_function(content, func, "@admin_required()")
    
    # Adicionar @block_viewer_access() em rotas POST/DELETE
    for func in fixes.get("block_viewer", []):
        content = add_decorator_to_function(content, func, "@block_viewer_access()")
    
    # Adicionar @super_admin_required() em rotas de gerenciamento
    for func in fixes.get("super_admin_only", []):
        content = add_decorator_to_function(content, func, "@super_admin_required()")
    
    # Escrever arquivo modificado
    if write_file(filepath, content):
        print(f"✅ Arquivo {filepath} corrigido com sucesso!")
        return True
    
    return False

def fix_nfe_routes(filepath):
    """Aplica correções no arquivo nfe_routes.py"""
    print(f"\n🔧 Corrigindo {filepath}...")
    
    content = read_file(filepath)
    if not content:
        return False
    
    # Criar backup
    backup_file(filepath)
    
    # Adicionar imports necessários
    content = add_import_if_missing(content, "from auth.decorators import block_viewer_access, viewer_or_higher_required")
    
    fixes = SECURITY_FIXES.get("nfe_routes.py", {})
    
    # Adicionar @block_viewer_access() em rotas de escrita
    for func in fixes.get("block_viewer", []):
        content = add_decorator_to_function(content, func, "@block_viewer_access()")
    
    # Escrever arquivo modificado
    if write_file(filepath, content):
        print(f"✅ Arquivo {filepath} corrigido com sucesso!")
        return True
    
    return False

def remove_permission_required_stubs(filepath):
    """Remove stubs do permission_required"""
    print(f"\n🧹 Removendo stubs de permission_required em {filepath}...")
    
    content = read_file(filepath)
    if not content:
        return False
    
    # Criar backup
    backup_file(filepath)
    
    # Padrão para encontrar stubs
    stub_pattern = r'''try:\s+from \.\.core\.permissions import permission_required.*?\nexcept.*?:\s+def permission_required\(permission\):\s+def decorator\(f\):\s+return f\s+return decorator'''
    
    # Remover stubs
    new_content = re.sub(stub_pattern, '', content, flags=re.DOTALL)
    
    if new_content != content:
        print(f"  ✅ Stubs removidos")
        
        # Escrever arquivo modificado
        if write_file(filepath, new_content):
            print(f"✅ Arquivo {filepath} atualizado!")
            return True
    else:
        print(f"  ℹ️  Nenhum stub encontrado")
    
    return False

def main():
    """Função principal"""
    print("="*80)
    print("🔒 APLICANDO CORREÇÕES DE SEGURANÇA")
    print("="*80)
    
    # Diretório base
    base_dir = Path(__file__).parent
    routes_dir = base_dir / "routes"
    
    # Verificar se diretório existe
    if not routes_dir.exists():
        print(f"❌ Diretório {routes_dir} não encontrado!")
        return
    
    # Arquivos a corrigir
    files_to_fix = {
        "admin_routes.py": fix_admin_routes,
        "nfe_routes.py": fix_nfe_routes,
    }
    
    success_count = 0
    total_count = len(files_to_fix)
    
    for filename, fix_function in files_to_fix.items():
        filepath = routes_dir / filename
        
        if not filepath.exists():
            print(f"⚠️  Arquivo {filepath} não encontrado, pulando...")
            continue
        
        # Aplicar correções
        if fix_function(str(filepath)):
            success_count += 1
        
        # Remover stubs de permission_required
        remove_permission_required_stubs(str(filepath))
    
    print("\n" + "="*80)
    print(f"📊 RESUMO: {success_count}/{total_count} arquivos corrigidos")
    print("="*80)
    
    if success_count == total_count:
        print("✅ Todas as correções foram aplicadas com sucesso!")
        print("\n⚠️  IMPORTANTE:")
        print("1. Revise os arquivos modificados")
        print("2. Execute testes para garantir que nada quebrou")
        print("3. Os arquivos de backup (.backup) foram criados")
        print("4. Commit as alterações após validação")
    else:
        print("⚠️  Algumas correções falharam. Verifique os logs acima.")
    
    print("\n📝 Próximos passos:")
    print("1. Revisar arquivos modificados")
    print("2. Testar cada role (Super_Admin, Admin, Editor, Viewer)")
    print("3. Verificar templates (ocultar botões para Viewers)")
    print("4. Atualizar documentação")

if __name__ == "__main__":
    main()

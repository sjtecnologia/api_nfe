import os
import re

def get_complete_route_mapping():
    """Mapeamento completo de todas as rotas antigas para novas"""
    return {
        # Auth routes
        'login': 'auth.login',
        'logout': 'auth.logout',
        
        # Home
        'home': 'home',
        'index': 'home',
        'main.home': 'home',
        
        # Admin - Dashboard
        'admin_home': 'admin.admin_home',
        'admin_dashboard': 'admin.admin_home',
        
        # Admin - Clientes (todas as variações possíveis)
        'admin_clientes_list': 'admin.list_clientes',
        'admin_clientes_add': 'admin.create_cliente',
        'admin_clientes_create': 'admin.create_cliente',
        'admin_clientes_new': 'admin.create_cliente',
        'admin_clientes_edit': 'admin.edit_cliente',
        'admin_clientes_update': 'admin.edit_cliente',
        'admin_clientes_view': 'admin.view_cliente',
        'admin_clientes_detail': 'admin.view_cliente',
        'admin_clientes_show': 'admin.view_cliente',
        'admin_clientes_delete': 'admin.delete_cliente',
        'admin_cliente_detail': 'admin.view_cliente',
        'admin_cliente_add': 'admin.create_cliente',
        'admin_cliente_edit': 'admin.edit_cliente',
        'admin_cliente_delete': 'admin.delete_cliente',
        
        # Admin - Produtos
        'admin_produtos_list': 'admin.list_produtos',
        'admin_produtos_add': 'admin.create_produto',
        'admin_produtos_create': 'admin.create_produto',
        'admin_produtos_new': 'admin.create_produto',
        'admin_produtos_edit': 'admin.edit_produto',
        'admin_produtos_update': 'admin.edit_produto',
        'admin_produtos_view': 'admin.view_produto',
        'admin_produtos_detail': 'admin.view_produto',
        'admin_produtos_show': 'admin.view_produto',
        'admin_produtos_delete': 'admin.delete_produto',
        'admin_produto_add': 'admin.create_produto',
        'admin_produto_edit': 'admin.edit_produto',
        'admin_produto_delete': 'admin.delete_produto',
        'admin_produto_detail': 'admin.view_produto',
        
        # Admin - Certificados
        'admin_certificados_list': 'admin.list_certificados',
        'admin_certificados_add': 'admin.create_certificado',
        'admin_certificados_create': 'admin.create_certificado',
        'admin_certificados_upload': 'admin.upload_certificado',
        'admin_upload_certificado': 'admin.upload_certificado',
        'admin_certificados_edit': 'admin.edit_certificado',
        'admin_certificados_update': 'admin.edit_certificado',
        'admin_certificados_view': 'admin.view_certificado',
        'admin_certificados_detail': 'admin.view_certificado',
        'admin_certificados_delete': 'admin.delete_certificado',
        'admin_certificado_upload': 'admin.upload_certificado',
        'admin_certificado_add': 'admin.create_certificado',
        'admin_certificado_edit': 'admin.edit_certificado',
        'admin_certificado_delete': 'admin.delete_certificado',
        
        # Admin - NFes
        'admin_nfes_list': 'admin.list_nfes',
        'admin_nfes_add': 'admin.create_nfe',
        'admin_nfes_create': 'admin.create_nfe',
        'admin_nfe_detail': 'admin.view_nfe',
        'admin_view_nfe': 'admin.view_nfe',
        'admin_nfes_view': 'admin.view_nfe',
        'admin_nfes_edit': 'admin.edit_nfe',
        'admin_nfes_delete': 'admin.delete_nfe',
        'admin_nfe_edit': 'admin.edit_nfe',
        'admin_nfe_delete': 'admin.delete_nfe',
        
        # Admin - Users
        'admin_users_list': 'admin.list_users',
        'admin_users_add': 'admin.create_user',
        'admin_users_create': 'admin.create_user',
        'admin_users_new': 'admin.create_user',
        'admin_users_edit': 'admin.edit_user',
        'admin_users_update': 'admin.edit_user',
        'admin_users_view': 'admin.view_user',
        'admin_users_detail': 'admin.view_user',
        'admin_users_delete': 'admin.delete_user',
        'admin_user_add': 'admin.create_user',
        'admin_user_edit': 'admin.edit_user',
        'admin_user_delete': 'admin.delete_user',
        'admin_user_detail': 'admin.view_user',
        
        # Admin - Roles
        'admin_roles_list': 'admin.list_roles',
        'admin_roles_add': 'admin.create_role',
        'admin_roles_create': 'admin.create_role',
        'admin_roles_new': 'admin.create_role',
        'admin_roles_edit': 'admin.edit_role',
        'admin_roles_update': 'admin.edit_role',
        'admin_roles_view': 'admin.view_role',
        'admin_roles_detail': 'admin.view_role',
        'admin_roles_delete': 'admin.delete_role',
        'admin_role_add': 'admin.create_role',
        'admin_role_edit': 'admin.edit_role',
        'admin_role_delete': 'admin.delete_role',
        
        # Admin - Regras Tributação
        'admin_regras_tributacao_list': 'admin.list_regras_tributacao',
        'admin_regras_tributacao_add': 'admin.create_regra_tributacao',
        'admin_regras_tributacao_create': 'admin.create_regra_tributacao',
        'admin_regras_tributacao_new': 'admin.create_regra_tributacao',
        'admin_regras_tributacao_edit': 'admin.edit_regra_tributacao',
        'admin_regras_tributacao_update': 'admin.edit_regra_tributacao',
        'admin_regras_tributacao_view': 'admin.view_regra_tributacao',
        'admin_regras_tributacao_detail': 'admin.view_regra_tributacao',
        'admin_regras_tributacao_delete': 'admin.delete_regra_tributacao',
        
        # Admin - CFOPs
        'admin_cfops_list': 'admin.list_cfops',
        'admin_cfops_add': 'admin.create_cfop',
        'admin_cfops_create': 'admin.create_cfop',
        'admin_cfops_edit': 'admin.edit_cfop',
        'admin_cfops_update': 'admin.edit_cfop',
        'admin_cfops_view': 'admin.view_cfop',
        'admin_cfops_detail': 'admin.view_cfop',
        'admin_cfops_delete': 'admin.delete_cfop',
        'admin_cfop_add': 'admin.create_cfop',
        'admin_cfop_edit': 'admin.edit_cfop',
        'admin_cfop_delete': 'admin.delete_cfop',
        
        # Admin - NCMs
        'admin_ncms_list': 'admin.list_ncms',
        'admin_ncms_add': 'admin.create_ncm',
        'admin_ncms_create': 'admin.create_ncm',
        'admin_ncms_edit': 'admin.edit_ncm',
        'admin_ncms_update': 'admin.edit_ncm',
        'admin_ncms_view': 'admin.view_ncm',
        'admin_ncms_detail': 'admin.view_ncm',
        'admin_ncms_delete': 'admin.delete_ncm',
        'admin_ncm_add': 'admin.create_ncm',
        'admin_ncm_edit': 'admin.edit_ncm',
        'admin_ncm_delete': 'admin.delete_ncm',
        
        # Admin - CST
        'admin_cst_list': 'admin.list_cst',
        'admin_cst_add': 'admin.create_cst',
        'admin_cst_create': 'admin.create_cst',
        'admin_cst_edit': 'admin.edit_cst',
        'admin_cst_update': 'admin.edit_cst',
        'admin_cst_view': 'admin.view_cst',
        'admin_cst_detail': 'admin.view_cst',
        'admin_cst_delete': 'admin.delete_cst',
        
        # Admin - CSOSN
        'admin_csosn_list': 'admin.list_csosn',
        'admin_csosn_add': 'admin.create_csosn',
        'admin_csosn_create': 'admin.create_csosn',
        'admin_csosn_edit': 'admin.edit_csosn',
        'admin_csosn_update': 'admin.edit_csosn',
        'admin_csosn_view': 'admin.view_csosn',
        'admin_csosn_detail': 'admin.view_csosn',
        'admin_csosn_delete': 'admin.delete_csosn',
        
        # Admin - Origens Mercadoria
        'admin_origens_mercadoria_list': 'admin.list_origens_mercadoria',
        'admin_origens_mercadoria_add': 'admin.create_origem_mercadoria',
        'admin_origens_mercadoria_create': 'admin.create_origem_mercadoria',
        'admin_origens_mercadoria_edit': 'admin.edit_origem_mercadoria',
        'admin_origens_mercadoria_update': 'admin.edit_origem_mercadoria',
        'admin_origens_mercadoria_view': 'admin.view_origem_mercadoria',
        'admin_origens_mercadoria_detail': 'admin.view_origem_mercadoria',
        'admin_origens_mercadoria_delete': 'admin.delete_origem_mercadoria',
        
        # Admin - Regimes Tributários
        'admin_regimes_tributarios_list': 'admin.list_regimes_tributarios',
        'admin_regimes_tributarios_add': 'admin.create_regime_tributario',
        'admin_regimes_tributarios_create': 'admin.create_regime_tributario',
        'admin_regimes_tributarios_edit': 'admin.edit_regime_tributario',
        'admin_regimes_tributarios_update': 'admin.edit_regime_tributario',
        'admin_regimes_tributarios_view': 'admin.view_regime_tributario',
        'admin_regimes_tributarios_detail': 'admin.view_regime_tributario',
        'admin_regimes_tributarios_delete': 'admin.delete_regime_tributario',
        
        # Admin - Destinatários
        'admin_destinatarios_list': 'admin.list_destinatarios',
        'admin_destinatarios_add': 'admin.create_destinatario',
        'admin_destinatarios_create': 'admin.create_destinatario',
        'admin_destinatarios_edit': 'admin.edit_destinatario',
        'admin_destinatarios_update': 'admin.edit_destinatario',
        'admin_destinatarios_view': 'admin.view_destinatario',
        'admin_destinatarios_detail': 'admin.view_destinatario',
        'admin_destinatarios_delete': 'admin.delete_destinatario',
        'admin_destinatario_list': 'admin.list_destinatarios',
        'admin_destinatario_add': 'admin.create_destinatario',
        'admin_destinatario_create': 'admin.create_destinatario',
        'admin_destinatario_edit': 'admin.edit_destinatario',
        'admin_destinatario_update': 'admin.edit_destinatario',
        'admin_destinatario_view': 'admin.view_destinatario',
        'admin_destinatario_detail': 'admin.view_destinatario',
        'admin_destinatario_delete': 'admin.delete_destinatario',
        
        # Admin - Motivos Desoneração
        'admin_motivos_desoneracao_list': 'admin.list_motivos_desoneracao',
        'admin_motivos_desoneracao_add': 'admin.create_motivo_desoneracao',
        'admin_motivos_desoneracao_create': 'admin.create_motivo_desoneracao',
        'admin_motivos_desoneracao_edit': 'admin.edit_motivo_desoneracao',
        'admin_motivos_desoneracao_update': 'admin.edit_motivo_desoneracao',
        'admin_motivos_desoneracao_view': 'admin.view_motivo_desoneracao',
        'admin_motivos_desoneracao_detail': 'admin.view_motivo_desoneracao',
        'admin_motivos_desoneracao_delete': 'admin.delete_motivo_desoneracao',
        'motivos_desoneracao_list': 'admin.list_motivos_desoneracao',
        'motivos_desoneracao_add': 'admin.create_motivo_desoneracao',
        'motivos_desoneracao_create': 'admin.create_motivo_desoneracao',
        'motivos_desoneracao_edit': 'admin.edit_motivo_desoneracao',
        'motivos_desoneracao_update': 'admin.edit_motivo_desoneracao',
        'motivos_desoneracao_view': 'admin.view_motivo_desoneracao',
        'motivos_desoneracao_detail': 'admin.view_motivo_desoneracao',
        'motivos_desoneracao_delete': 'admin.delete_motivo_desoneracao',
        
        # NFe routes
        'admin_emitir_nfe': 'nfe.emitir_nfe',
        'emitir_nfe': 'nfe.emitir_nfe',
        'nfe_emitir': 'nfe.emitir_nfe',
        'nfe_list': 'nfe.list_nfes',
        'list_nfes': 'nfe.list_nfes',
        'nfes_list': 'nfe.list_nfes',
        'xml_preview': 'nfe.xml_preview',
        'nfe_xml_preview': 'nfe.xml_preview',
        
        # API routes
        'api_cfops': 'api.get_cfops',
        'api_ncms': 'api.get_ncms',
        'api_produtos_cliente': 'api.get_produtos_cliente',
        'api_buscar_regra_tributacao': 'api.buscar_regra_tributacao',
        'api_clientes': 'api.get_clientes',
    }

def find_all_url_for_calls(file_path):
    """Encontra todas as chamadas url_for em um arquivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Padrão para encontrar url_for calls
        pattern = r"url_for\(['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)
        return matches
    except Exception as e:
        print(f"Erro ao ler {file_path}: {e}")
        return []

def analyze_and_fix_routes():
    """Analisa e corrige todas as rotas"""
    route_mapping = get_complete_route_mapping()
    
    print("🔍 Analisando todos os templates...\n")
    
    all_routes_found = set()
    files_with_issues = []
    
    # Analisar todos os templates
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                routes = find_all_url_for_calls(file_path)
                
                has_issues = False
                for route in routes:
                    all_routes_found.add(route)
                    if route not in route_mapping and not route.startswith(('admin.', 'nfe.', 'api.', 'auth.')):
                        print(f"⚠️  Rota não mapeada em {file_path}: {route}")
                        has_issues = True
                
                if has_issues:
                    files_with_issues.append(file_path)
    
    print(f"\n📊 Resumo da análise:")
    print(f"   Arquivos com problemas: {len(files_with_issues)}")
    print(f"   Total de rotas encontradas: {len(all_routes_found)}")
    
    # Corrigir arquivos
    print(f"\n🔧 Corrigindo arquivos...\n")
    
    fixed_count = 0
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                if fix_routes_in_file(file_path, route_mapping):
                    fixed_count += 1
    
    print(f"\n✅ {fixed_count} arquivos foram corrigidos!")

def fix_routes_in_file(file_path, route_mapping):
    """Corrige rotas em um arquivo específico"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Substituir cada rota antiga pela nova
        for old_route, new_route in route_mapping.items():
            if old_route != new_route:
                # Padrões possíveis de url_for
                patterns = [
                    f"url_for('{old_route}'",
                    f'url_for("{old_route}"',
                ]
                
                for pattern in patterns:
                    if pattern in content:
                        replacement = pattern.replace(old_route, new_route)
                        content = content.replace(pattern, replacement)
                        changes_made.append(f"{old_route} → {new_route}")
        
        # Salvar apenas se houve mudanças
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Corrigido: {file_path}")
            for change in changes_made:
                print(f"   🔄 {change}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Erro ao corrigir {file_path}: {e}")
        return False

if __name__ == "__main__":
    analyze_and_fix_routes()
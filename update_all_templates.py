import os
import re

def get_complete_route_mapping():
    """Mapeamento completo de rotas antigas para novas com blueprints"""
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
        
        # Admin - Clientes
        'admin_clientes_list': 'admin.list_clientes',
        'admin_clientes_create': 'admin.create_cliente',
        'admin_clientes_edit': 'admin.edit_cliente',
        'admin_clientes_view': 'admin.view_cliente',
        'admin_clientes_delete': 'admin.delete_cliente',
        'admin_cliente_detail': 'admin.view_cliente',
        
        # Admin - Produtos
        'admin_produtos_list': 'admin.list_produtos',
        'admin_produtos_create': 'admin.create_produto',
        'admin_produtos_edit': 'admin.edit_produto',
        'admin_produtos_view': 'admin.view_produto',
        'admin_produtos_delete': 'admin.delete_produto',
        
        # Admin - Certificados
        'admin_certificados_list': 'admin.list_certificados',
        'admin_certificados_upload': 'admin.upload_certificado',
        'admin_upload_certificado': 'admin.upload_certificado',
        'admin_certificados_view': 'admin.view_certificado',
        'admin_certificados_delete': 'admin.delete_certificado',
        
        # Admin - NFes
        'admin_nfes_list': 'admin.list_nfes',
        'admin_nfe_detail': 'admin.view_nfe',
        'admin_view_nfe': 'admin.view_nfe',
        
        # Admin - Users
        'admin_users_list': 'admin.list_users',
        'admin_users_create': 'admin.create_user',
        'admin_users_edit': 'admin.edit_user',
        'admin_users_view': 'admin.view_user',
        'admin_users_delete': 'admin.delete_user',
        
        # Admin - Roles
        'admin_roles_list': 'admin.list_roles',
        'admin_roles_create': 'admin.create_role',
        'admin_roles_edit': 'admin.edit_role',
        'admin_roles_view': 'admin.view_role',
        'admin_roles_delete': 'admin.delete_role',
        
        # Admin - Regras Tributação
        'admin_regras_tributacao_list': 'admin.list_regras_tributacao',
        'admin_regras_tributacao_create': 'admin.create_regra_tributacao',
        'admin_regras_tributacao_edit': 'admin.edit_regra_tributacao',
        'admin_regras_tributacao_view': 'admin.view_regra_tributacao',
        'admin_regras_tributacao_delete': 'admin.delete_regra_tributacao',
        
        # Admin - CFOPs
        'admin_cfops_list': 'admin.list_cfops',
        'admin_cfops_create': 'admin.create_cfop',
        'admin_cfops_edit': 'admin.edit_cfop',
        'admin_cfops_view': 'admin.view_cfop',
        'admin_cfops_delete': 'admin.delete_cfop',
        
        # Admin - NCMs
        'admin_ncms_list': 'admin.list_ncms',
        'admin_ncms_create': 'admin.create_ncm',
        'admin_ncms_edit': 'admin.edit_ncm',
        'admin_ncms_view': 'admin.view_ncm',
        'admin_ncms_delete': 'admin.delete_ncm',
        
        # Admin - CST
        'admin_cst_list': 'admin.list_cst',
        'admin_cst_create': 'admin.create_cst',
        'admin_cst_edit': 'admin.edit_cst',
        'admin_cst_view': 'admin.view_cst',
        'admin_cst_delete': 'admin.delete_cst',
        
        # Admin - CSOSN
        'admin_csosn_list': 'admin.list_csosn',
        'admin_csosn_create': 'admin.create_csosn',
        'admin_csosn_edit': 'admin.edit_csosn',
        'admin_csosn_view': 'admin.view_csosn',
        'admin_csosn_delete': 'admin.delete_csosn',
        
        # Admin - Origens Mercadoria
        'admin_origens_mercadoria_list': 'admin.list_origens_mercadoria',
        'admin_origens_mercadoria_create': 'admin.create_origem_mercadoria',
        'admin_origens_mercadoria_edit': 'admin.edit_origem_mercadoria',
        'admin_origens_mercadoria_view': 'admin.view_origem_mercadoria',
        'admin_origens_mercadoria_delete': 'admin.delete_origem_mercadoria',
        
        # Admin - Regimes Tributários
        'admin_regimes_tributarios_list': 'admin.list_regimes_tributarios',
        'admin_regimes_tributarios_create': 'admin.create_regime_tributario',
        'admin_regimes_tributarios_edit': 'admin.edit_regime_tributario',
        'admin_regimes_tributarios_view': 'admin.view_regime_tributario',
        'admin_regimes_tributarios_delete': 'admin.delete_regime_tributario',
        
        # Admin - Destinatários
        'admin_destinatarios_list': 'admin.list_destinatarios',
        'admin_destinatarios_create': 'admin.create_destinatario',
        'admin_destinatarios_edit': 'admin.edit_destinatario',
        'admin_destinatarios_view': 'admin.view_destinatario',
        'admin_destinatarios_delete': 'admin.delete_destinatario',
        'admin_destinatario_list': 'admin.list_destinatarios',
        'admin_destinatario_create': 'admin.create_destinatario',
        'admin_destinatario_edit': 'admin.edit_destinatario',
        'admin_destinatario_view': 'admin.view_destinatario',
        'admin_destinatario_delete': 'admin.delete_destinatario',
        
        # NFe routes
        'admin_emitir_nfe': 'nfe.emitir_nfe',
        'emitir_nfe': 'nfe.emitir_nfe',
        'nfe_list': 'nfe.list_nfes',
        'list_nfes': 'nfe.list_nfes',
        'xml_preview': 'nfe.xml_preview',
        
        # Tributação routes
        'motivos_desoneracao_list': 'tributacao.list_motivos_desoneracao',
        'motivos_desoneracao_create': 'tributacao.create_motivo_desoneracao',
        'motivos_desoneracao_edit': 'tributacao.edit_motivo_desoneracao',
        'motivos_desoneracao_view': 'tributacao.view_motivo_desoneracao',
        'motivos_desoneracao_delete': 'tributacao.delete_motivo_desoneracao',
        
        # API routes
        'api_cfops': 'api.get_cfops',
        'api_ncms': 'api.get_ncms',
        'api_produtos_cliente': 'api.get_produtos_cliente',
        'api_buscar_regra_tributacao': 'api.buscar_regra_tributacao',
        'api_clientes': 'api.get_clientes',
    }

def update_template_file(file_path, route_mapping):
    """Atualiza um arquivo de template"""
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

def update_all_templates():
    """Atualiza todos os templates"""
    route_mapping = get_complete_route_mapping()
    templates_dir = "templates"
    updated_count = 0
    
    print("🔄 Atualizando rotas nos templates...\n")
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                if update_template_file(file_path, route_mapping):
                    updated_count += 1
    
    print(f"\n🎉 Atualização concluída! {updated_count} arquivos foram modificados.")

if __name__ == "__main__":
    update_all_templates()
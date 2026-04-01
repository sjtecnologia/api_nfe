import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Cria a estrutura de diretórios para os templates"""
    directories = [
        'templates/admin/clientes',
        'templates/admin/produtos', 
        'templates/admin/certificados',
        'templates/admin/nfes',
        'templates/admin/users',
        'templates/admin/roles',
        'templates/admin/regras_tributacao',
        'templates/admin/cfops',
        'templates/admin/ncms',
        'templates/admin/cst',
        'templates/admin/csosn',
        'templates/admin/origens_mercadoria',
        'templates/admin/regimes_tributarios',
        'templates/admin/destinatarios',
        'templates/nfe',
        'templates/tributacao'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Criado diretório: {directory}")

def get_file_moves():
    """Define quais arquivos devem ser movidos para onde"""
    return {
        # Admin - Clientes
        'templates/admin_clientes_list.html': 'templates/admin/clientes/list.html',
        'templates/admin_clientes_form.html': 'templates/admin/clientes/form.html',
        
        # Admin - Produtos
        'templates/admin_produtos_list.html': 'templates/admin/produtos/list.html',
        'templates/admin_produtos_list_partial.html': 'templates/admin/produtos/list_partial.html',
        'templates/admin_produtos_form.html': 'templates/admin/produtos/form.html',
        'templates/admin_produtos_form_modal.html': 'templates/admin/produtos/form_modal.html',
        'templates/admin_produtos_form_fields.html': 'templates/admin/produtos/form_fields.html',
        
        # Admin - Certificados
        'templates/admin_certificados_list.html': 'templates/admin/certificados/list.html',
        'templates/admin_certificados_list_partial.html': 'templates/admin/certificados/list_partial.html',
        'templates/admin_certificados_form.html': 'templates/admin/certificados/form.html',
        'templates/admin_certificados_form_content.html': 'templates/admin/certificados/form_content.html',
        
        # Admin - NFes
        'templates/admin_nfes_list.html': 'templates/admin/nfes/list.html',
        
        # Admin - Users
        'templates/admin_users_list.html': 'templates/admin/users/list.html',
        'templates/admin_users_form.html': 'templates/admin/users/form.html',
        
        # Admin - Roles
        'templates/admin_roles_list.html': 'templates/admin/roles/list.html',
        
        # Admin - Regras Tributação
        'templates/admin_regras_tributacao_list.html': 'templates/admin/regras_tributacao/list.html',
        'templates/admin_regras_tributacao_list_partial.html': 'templates/admin/regras_tributacao/list_partial.html',
        'templates/admin_regras_tributacao_form.html': 'templates/admin/regras_tributacao/form.html',
        'templates/admin_regras_tributacao_form_modal.html': 'templates/admin/regras_tributacao/form_modal.html',
        'templates/admin_regras_tributacao_form_content.html': 'templates/admin/regras_tributacao/form_content.html',
        'templates/admin_regras_tributacao_form_fields.html': 'templates/admin/regras_tributacao/form_fields.html',
        
        # Admin - CFOPs
        'templates/admin_cfops_list.html': 'templates/admin/cfops/list.html',
        'templates/admin_cfops_form.html': 'templates/admin/cfops/form.html',
        
        # Admin - NCMs
        'templates/admin_ncms_list.html': 'templates/admin/ncms/list.html',
        'templates/admin_ncms_form.html': 'templates/admin/ncms/form.html',
        
        # Admin - CST
        'templates/admin_cst_list.html': 'templates/admin/cst/list.html',
        'templates/admin_cst_form.html': 'templates/admin/cst/form.html',
        
        # Admin - CSOSN
        'templates/admin_csosn_list.html': 'templates/admin/csosn/list.html',
        'templates/admin_csosn_form.html': 'templates/admin/csosn/form.html',
        
        # Admin - Origens Mercadoria
        'templates/admin_origens_mercadoria_list.html': 'templates/admin/origens_mercadoria/list.html',
        'templates/admin_origens_mercadoria_form.html': 'templates/admin/origens_mercadoria/form.html',
        
        # Admin - Regimes Tributários
        'templates/admin_regimes_tributarios_list.html': 'templates/admin/regimes_tributarios/list.html',
        'templates/admin_regimes_tributarios_form.html': 'templates/admin/regimes_tributarios/form.html',
        
        # Admin - Destinatários
        'templates/admin_destinatario_list.html': 'templates/admin/destinatarios/list.html',
        'templates/admin_destinatario_form.html': 'templates/admin/destinatarios/form.html',
        'templates/admin_destinatario_form_modal.html': 'templates/admin/destinatarios/form_modal.html',
        'templates/admin_destinatario_form_fields.html': 'templates/admin/destinatarios/form_fields.html',
        
        # NFe
        'templates/emitir_nfe.html': 'templates/nfe/emitir.html',
        'templates/xml_preview.html': 'templates/nfe/xml_preview.html',
        
        # Tributação (já está certo)
        # 'templates/tributacao/motivos_desoneracao_list.html': 'templates/tributacao/motivos_desoneracao_list.html',
        # 'templates/tributacao/motivos_desoneracao_form.html': 'templates/tributacao/motivos_desoneracao_form.html',
    }

def move_files():
    """Move os arquivos para a nova estrutura"""
    moves = get_file_moves()
    moved_count = 0
    
    for old_path, new_path in moves.items():
        if os.path.exists(old_path):
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            
            # Mover arquivo
            shutil.move(old_path, new_path)
            print(f"📁 Movido: {old_path} → {new_path}")
            moved_count += 1
        else:
            print(f"⚠️  Arquivo não encontrado: {old_path}")
    
    print(f"\n✅ {moved_count} arquivos reorganizados!")

if __name__ == "__main__":
    print("🗂️  Reorganizando estrutura de templates...\n")
    create_directory_structure()
    print("\n📂 Movendo arquivos...\n")
    move_files()
    print("\n🎉 Reorganização concluída!")
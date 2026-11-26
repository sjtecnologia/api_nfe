import os
import shutil
from pathlib import Path

def create_admin_tributacao_structure():
    """Cria a estrutura de diretórios para tributação dentro de admin"""
    directories = [
        'templates/admin/tributacao',
        'templates/admin/tributacao/motivos_desoneracao'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Criado diretório: {directory}")

def get_tributacao_file_moves():
    """Define quais arquivos de tributação devem ser movidos para admin"""
    return {
        # Motivos de Desoneração
        'templates/tributacao/motivos_desoneracao_list.html': 'templates/admin/tributacao/motivos_desoneracao_list.html',
        'templates/tributacao/motivos_desoneracao_form.html': 'templates/admin/tributacao/motivos_desoneracao_form.html',
        
        # Se existirem outros arquivos de tributação, adicione aqui
        # Exemplo:
        # 'templates/tributacao/outros_arquivos.html': 'templates/admin/tributacao/outros_arquivos.html',
    }

def move_tributacao_files():
    """Move os arquivos de tributação para dentro da estrutura admin"""
    moves = get_tributacao_file_moves()
    moved_count = 0
    
    print("📁 Movendo arquivos de tributação para admin...\n")
    
    for old_path, new_path in moves.items():
        if os.path.exists(old_path):
            # Criar diretório de destino se não existir
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            
            # Mover arquivo
            shutil.move(old_path, new_path)
            print(f"✅ Movido: {old_path} → {new_path}")
            moved_count += 1
        else:
            print(f"⚠️  Arquivo não encontrado: {old_path}")
    
    return moved_count

def remove_empty_tributacao_dir():
    """Remove o diretório tributação se estiver vazio"""
    tributacao_dir = 'templates/tributacao'
    
    if os.path.exists(tributacao_dir):
        try:
            # Verificar se o diretório está vazio
            if not os.listdir(tributacao_dir):
                os.rmdir(tributacao_dir)
                print(f"🗑️  Removido diretório vazio: {tributacao_dir}")
            else:
                remaining_files = os.listdir(tributacao_dir)
                print(f"⚠️  Diretório {tributacao_dir} não está vazio. Arquivos restantes:")
                for file in remaining_files:
                    print(f"   - {file}")
        except Exception as e:
            print(f"❌ Erro ao remover diretório {tributacao_dir}: {e}")

def update_tributacao_routes():
    """Atualiza as rotas nos templates movidos e nos blueprints"""
    
    # Mapeamento de rotas que precisam ser atualizadas
    route_updates = {
        # De tributacao.* para admin.*
        'tributacao.list_motivos_desoneracao': 'admin.list_motivos_desoneracao',
        'tributacao.create_motivo_desoneracao': 'admin.create_motivo_desoneracao',
        'tributacao.edit_motivo_desoneracao': 'admin.edit_motivo_desoneracao',
        'tributacao.view_motivo_desoneracao': 'admin.view_motivo_desoneracao',
        'tributacao.delete_motivo_desoneracao': 'admin.delete_motivo_desoneracao',
    }
    
    # Atualizar templates na nova localização
    admin_tributacao_dir = 'templates/admin/tributacao'
    updated_files = []
    
    if os.path.exists(admin_tributacao_dir):
        for root, dirs, files in os.walk(admin_tributacao_dir):
            for file in files:
                if file.endswith('.html'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        original_content = content
                        changes_made = []
                        
                        # Substituir rotas antigas pelas novas
                        for old_route, new_route in route_updates.items():
                            patterns = [
                                f"url_for('{old_route}'",
                                f'url_for("{old_route}"',
                            ]
                            
                            for pattern in patterns:
                                if pattern in content:
                                    replacement = pattern.replace(old_route, new_route)
                                    content = content.replace(pattern, replacement)
                                    changes_made.append(f"{old_route} → {new_route}")
                        
                        # Salvar se houve mudanças
                        if content != original_content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            print(f"🔄 Atualizado: {file_path}")
                            for change in changes_made:
                                print(f"   ✅ {change}")
                            updated_files.append(file_path)
                    
                    except Exception as e:
                        print(f"❌ Erro ao atualizar {file_path}: {e}")
    
    return updated_files

def create_admin_tributacao_routes_info():
    """Cria arquivo com informações sobre as rotas que precisam ser adicionadas ao admin_routes.py"""
    
    routes_info = '''
# =================================================================
# ROTAS DE TRIBUTAÇÃO PARA ADICIONAR AO admin_routes.py
# =================================================================

# Adicione estas rotas ao arquivo routes/admin_routes.py:

@admin_bp.route('/tributacao/motivos-desoneracao')
@login_required
@permission_required('admin.tributacao.read')
def list_motivos_desoneracao():
    """Lista motivos de desoneração"""
    try:
        db = next(get_db())
        # Implementar consulta aos motivos de desoneração
        motivos = []  # Temporário até implementar o modelo
        
        return render_template('admin/tributacao/motivos_desoneracao_list.html', motivos=motivos)
    except Exception as e:
        flash(f'Erro ao carregar motivos de desoneração: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/tributacao/motivos-desoneracao/novo', methods=['GET', 'POST'])
@login_required
@permission_required('admin.tributacao.create')
def create_motivo_desoneracao():
    """Cria novo motivo de desoneração"""
    if request.method == 'POST':
        try:
            # Implementar criação
            flash('Motivo de desoneração criado com sucesso!', 'success')
            return redirect(url_for('admin.list_motivos_desoneracao'))
        except Exception as e:
            flash(f'Erro ao criar motivo de desoneração: {str(e)}', 'danger')
    
    return render_template('admin/tributacao/motivos_desoneracao_form.html')

@admin_bp.route('/tributacao/motivos-desoneracao/<int:motivo_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('admin.tributacao.update')
def edit_motivo_desoneracao(motivo_id):
    """Edita motivo de desoneração"""
    try:
        db = next(get_db())
        # motivo = db.query(MotivoDesoneracao).filter(MotivoDesoneracao.id == motivo_id).first()
        motivo = None  # Temporário
        
        if not motivo:
            flash('Motivo de desoneração não encontrado!', 'danger')
            return redirect(url_for('admin.list_motivos_desoneracao'))
        
        if request.method == 'POST':
            # Implementar edição
            flash('Motivo de desoneração atualizado com sucesso!', 'success')
            return redirect(url_for('admin.list_motivos_desoneracao'))
        
        return render_template('admin/tributacao/motivos_desoneracao_form.html', motivo=motivo)
    except Exception as e:
        flash(f'Erro ao editar motivo de desoneração: {str(e)}', 'danger')
        return redirect(url_for('admin.list_motivos_desoneracao'))

@admin_bp.route('/tributacao/motivos-desoneracao/<int:motivo_id>')
@login_required
@permission_required('admin.tributacao.read')
def view_motivo_desoneracao(motivo_id):
    """Visualiza motivo de desoneração"""
    try:
        db = next(get_db())
        # motivo = db.query(MotivoDesoneracao).filter(MotivoDesoneracao.id == motivo_id).first()
        motivo = None  # Temporário
        
        if not motivo:
            flash('Motivo de desoneração não encontrado!', 'danger')
            return redirect(url_for('admin.list_motivos_desoneracao'))
        
        return render_template('admin/tributacao/motivos_desoneracao_detail.html', motivo=motivo)
    except Exception as e:
        flash(f'Erro ao visualizar motivo de desoneração: {str(e)}', 'danger')
        return redirect(url_for('admin.list_motivos_desoneracao'))

@admin_bp.route('/tributacao/motivos-desoneracao/<int:motivo_id>/deletar', methods=['POST'])
@login_required
@permission_required('admin.tributacao.delete')
def delete_motivo_desoneracao(motivo_id):
    """Deleta motivo de desoneração"""
    try:
        db = next(get_db())
        # motivo = db.query(MotivoDesoneracao).filter(MotivoDesoneracao.id == motivo_id).first()
        motivo = None  # Temporário
        
        if not motivo:
            flash('Motivo de desoneração não encontrado!', 'danger')
        else:
            # db.delete(motivo)
            # db.commit()
            flash('Motivo de desoneração deletado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao deletar motivo de desoneração: {str(e)}', 'danger')
    
    return redirect(url_for('admin.list_motivos_desoneracao'))

# =================================================================
# LEMBRE-SE DE:
# 1. Remover o blueprint tributacao_bp do app.py
# 2. Deletar o arquivo routes/tributacao_routes.py (se não for mais necessário)
# 3. Atualizar o menu no base.html para usar as novas rotas admin.*
# =================================================================
'''
    
    with open('admin_tributacao_routes.txt', 'w', encoding='utf-8') as f:
        f.write(routes_info)
    
    print("📝 Arquivo 'admin_tributacao_routes.txt' criado com as rotas a serem adicionadas!")

def main():
    """Função principal para executar toda a migração"""
    print("🔄 Iniciando migração de tributação para admin...\n")
    
    # 1. Criar estrutura de diretórios
    create_admin_tributacao_structure()
    print()
    
    # 2. Mover arquivos
    moved_count = move_tributacao_files()
    print(f"\n✅ {moved_count} arquivos movidos!")
    print()
    
    # 3. Atualizar rotas nos templates
    updated_files = update_tributacao_routes()
    print(f"\n🔄 {len(updated_files)} templates atualizados com novas rotas!")
    print()
    
    # 4. Remover diretório vazio
    remove_empty_tributacao_dir()
    print()
    
    # 5. Criar arquivo com informações das rotas
    create_admin_tributacao_routes_info()
    print()
    
    print("🎉 Migração concluída!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Adicione as rotas do arquivo 'admin_tributacao_routes.txt' ao 'routes/admin_routes.py'")
    print("2. Remova o blueprint tributacao_bp do app.py se não for mais necessário")
    print("3. Atualize o menu no base.html para usar as novas rotas admin.*")
    print("4. Teste as funcionalidades de tributação")

if __name__ == "__main__":
    main()
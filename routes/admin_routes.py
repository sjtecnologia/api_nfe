from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.connection import get_db
from auth.decorators import permission_required
from auth.permissions import has_permission
from sqlalchemy import text

admin_bp = Blueprint('admin', __name__)

# ========== DASHBOARD ==========
@admin_bp.route('/')
@login_required  
def admin_home():
    """Dashboard administrativo"""
    # REMOVER QUALQUER REDIRECIONAMENTO AQUI!
    # NÃO fazer redirect para 'home'
    
    try:
        db = next(get_db())
        
        # Estatísticas gerais da plataforma
        stats = {}
        
        # Total de clientes
        clientes_result = db.execute(text("SELECT COUNT(*) as total FROM clientes WHERE ativo = true"))
        stats['total_clientes'] = clientes_result.first().total
        
        # Total de NFes (todos os clientes)
        nfes_result = db.execute(text("SELECT COUNT(*) as total FROM nfe_emitidas"))
        stats['total_nfes'] = nfes_result.first().total
        
        # NFes no ano atual
        nfes_ano_result = db.execute(text("""
            SELECT COUNT(*) as total FROM nfe_emitidas 
            WHERE EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE)
        """))
        stats['nfes_ano'] = nfes_ano_result.first().total
        
        # NFes no mês atual
        nfes_mes_result = db.execute(text("""
            SELECT COUNT(*) as total FROM nfe_emitidas 
            WHERE EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND EXTRACT(MONTH FROM data_criacao) = EXTRACT(MONTH FROM CURRENT_DATE)
        """))
        stats['nfes_mes'] = nfes_mes_result.first().total
        
        # Últimos clientes cadastrados
        ultimos_clientes = db.execute(text("""
            SELECT cliente_id, razao_social, nome_fantasia, cnpj, data_cadastro
            FROM clientes 
            WHERE ativo = true
            ORDER BY data_cadastro DESC 
            LIMIT 5
        """))
        
        return render_template('admin/dashboard.html', 
                             stats=stats,
                             ultimos_clientes=[dict(row._mapping) for row in ultimos_clientes])
                             
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        # Em caso de erro, mostrar dashboard básico
        return render_template('admin/dashboard.html', 
                             stats={'total_clientes': 0, 'total_nfes': 0, 'nfes_ano': 0, 'nfes_mes': 0},
                             ultimos_clientes=[])

# ========== CLIENTES ==========
@admin_bp.route('/clientes')
@login_required
@permission_required('clients.read')
def list_clientes():
    """Lista clientes"""
    try:
        db = next(get_db())
        # clientes = db.query(Cliente).all()
        clientes = []  # Temporário
        return render_template('admin/clientes/list.html', clientes=clientes)
    except Exception as e:
        flash(f'Erro ao carregar clientes: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/clientes/novo', methods=['GET', 'POST'])
@login_required
@permission_required('clients.create')
def create_cliente():
    """Cria novo cliente"""
    if request.method == 'POST':
        try:
            # Implementar criação
            flash('Cliente criado com sucesso!', 'success')
            return redirect(url_for('admin.list_clientes'))
        except Exception as e:
            flash(f'Erro ao criar cliente: {str(e)}', 'danger')
    
    return render_template('admin/clientes/form.html')

@admin_bp.route('/clientes/<int:cliente_id>')
@login_required
@permission_required('clients.read')
def view_cliente(cliente_id):
    """Visualiza cliente"""
    try:
        db = next(get_db())
        # cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        cliente = None  # Temporário
        
        if not cliente:
            flash('Cliente não encontrado!', 'danger')
            return redirect(url_for('admin.list_clientes'))
        
        return render_template('admin/clientes/detail.html', cliente=cliente)
    except Exception as e:
        flash(f'Erro ao visualizar cliente: {str(e)}', 'danger')
        return redirect(url_for('admin.list_clientes'))

@admin_bp.route('/clientes/<int:cliente_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('clients.edit')
def edit_cliente(cliente_id):
    """Edita cliente"""
    try:
        db = next(get_db())
        # cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        cliente = None  # Temporário
        
        if not cliente:
            flash('Cliente não encontrado!', 'danger')
            return redirect(url_for('admin.list_clientes'))
        
        if request.method == 'POST':
            # Implementar edição
            flash('Cliente atualizado com sucesso!', 'success')
            return redirect(url_for('admin.view_cliente', cliente_id=cliente_id))
        
        return render_template('admin/clientes/form.html', cliente=cliente)
    except Exception as e:
        flash(f'Erro ao editar cliente: {str(e)}', 'danger')
        return redirect(url_for('admin.list_clientes'))

@admin_bp.route('/clientes/<int:cliente_id>/deletar', methods=['POST'])
@login_required
@permission_required('clients.delete')
def delete_cliente(cliente_id):
    """Deleta cliente"""
    try:
        db = next(get_db())
        # cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        # if cliente:
        #     db.delete(cliente)
        #     db.commit()
        flash('Cliente deletado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao deletar cliente: {str(e)}', 'danger')
    
    return redirect(url_for('admin.list_clientes'))

# ========== PRODUTOS ==========
@admin_bp.route('/produtos')
@login_required
@permission_required('products.read')
def list_produtos():
    """Lista produtos"""
    try:
        db = next(get_db())
        # produtos = db.query(Produto).all()
        produtos = []  # Temporário
        raw_produtos = produtos  # Para compatibilidade com templates existentes
        return render_template('admin/produtos/list.html', produtos=produtos, raw_produtos=raw_produtos)
    except Exception as e:
        flash(f'Erro ao carregar produtos: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/produtos/novo', methods=['GET', 'POST'])
@login_required
@permission_required('products.create')
def create_produto():
    """Cria novo produto"""
    if request.method == 'POST':
        try:
            # Implementar criação
            flash('Produto criado com sucesso!', 'success')
            return redirect(url_for('admin.list_produtos'))
        except Exception as e:
            flash(f'Erro ao criar produto: {str(e)}', 'danger')
    
    return render_template('admin/produtos/form.html')

@admin_bp.route('/produtos/<int:produto_id>')
@login_required
@permission_required('products.read')
def view_produto(produto_id):
    """Visualiza produto"""
    try:
        db = next(get_db())
        # produto = db.query(Produto).filter(Produto.id == produto_id).first()
        produto = None  # Temporário
        
        if not produto:
            flash('Produto não encontrado!', 'danger')
            return redirect(url_for('admin.list_produtos'))
        
        return render_template('admin/produtos/detail.html', produto=produto)
    except Exception as e:
        flash(f'Erro ao visualizar produto: {str(e)}', 'danger')
        return redirect(url_for('admin.list_produtos'))

# ========== CERTIFICADOS ==========
@admin_bp.route('/certificados')
@login_required
@permission_required('certificates.read')
def list_certificados():
    """Lista certificados"""
    try:
        db = next(get_db())
        # certificados = db.query(CertificadoDigital).all()
        certificados = []  # Temporário
        return render_template('admin/certificados/list.html', certificados=certificados)
    except Exception as e:
        flash(f'Erro ao carregar certificados: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/certificados/upload/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
@permission_required('certificates.create')
def upload_certificado(cliente_id):
    """Upload de certificado"""
    try:
        db = next(get_db())
        # cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        cliente = None  # Temporário
        
        if not cliente:
            flash('Cliente não encontrado!', 'danger')
            return redirect(url_for('admin.list_certificados'))
        
        if request.method == 'POST':
            # Implementar upload
            flash('Certificado enviado com sucesso!', 'success')
            return redirect(url_for('admin.list_certificados'))
        
        return render_template('admin/certificados/upload.html', cliente=cliente)
    except Exception as e:
        flash(f'Erro no upload do certificado: {str(e)}', 'danger')
        return redirect(url_for('admin.list_certificados'))

# ========== NFE ==========
@admin_bp.route('/nfes')
@login_required
@permission_required('nfe.read')
def list_nfes():
    """Lista NFes"""
    try:
        db = next(get_db())
        # nfes = db.query(Nfe).all()
        nfes = []  # Temporário
        return render_template('admin/nfes/list.html', nfes=nfes)
    except Exception as e:
        flash(f'Erro ao carregar NFes: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/nfes/<int:nfe_id>')
@login_required
@permission_required('nfe.read')
def view_nfe(nfe_id):
    """Visualiza NFe"""
    try:
        db = next(get_db())
        # nfe = db.query(Nfe).filter(Nfe.id == nfe_id).first()
        nfe = None  # Temporário
        
        if not nfe:
            flash('NFe não encontrada!', 'danger')
            return redirect(url_for('admin.list_nfes'))
        
        return render_template('admin/nfes/detail.html', nfe=nfe)
    except Exception as e:
        flash(f'Erro ao visualizar NFe: {str(e)}', 'danger')
        return redirect(url_for('admin.list_nfes'))

# ========== USUARIOS ==========
@admin_bp.route('/usuarios')
@login_required
@permission_required('users.read')
def list_users():
    """Lista usuários"""
    try:
        db = next(get_db())
        # users = db.query(User).all()
        users = []  # Temporário
        return render_template('admin/users/list.html', users=users)
    except Exception as e:
        flash(f'Erro ao carregar usuários: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
@permission_required('users.create')
def create_user():
    """Cria novo usuário"""
    if request.method == 'POST':
        try:
            # Implementar criação
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            flash(f'Erro ao criar usuário: {str(e)}', 'danger')
    
    return render_template('admin/users/form.html')

# ========== ROLES ==========
@admin_bp.route('/roles')
@login_required
@permission_required('roles.read')
def list_roles():
    """Lista papéis"""
    try:
        db = next(get_db())
        # roles = db.query(Role).all()
        roles = []  # Temporário
        return render_template('admin/roles/list.html', roles=roles)
    except Exception as e:
        flash(f'Erro ao carregar papéis: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

# ========== CADASTROS FISCAIS ==========
@admin_bp.route('/cfops')
@login_required
@permission_required('cfops.read')
def list_cfops():
    """Lista CFOPs"""
    try:
        db = next(get_db())
        # cfops = db.query(Cfop).all()
        cfops = []  # Temporário
        return render_template('admin/cfops/list.html', cfops=cfops)
    except Exception as e:
        flash(f'Erro ao carregar CFOPs: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/ncms')
@login_required
@permission_required('ncms.read')
def list_ncms():
    """Lista NCMs"""
    try:
        db = next(get_db())
        # ncms = db.query(Ncm).all()
        ncms = []  # Temporário
        return render_template('admin/ncms/list.html', ncms=ncms)
    except Exception as e:
        flash(f'Erro ao carregar NCMs: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/cst')
@login_required
@permission_required('cst.read')
def list_cst():
    """Lista CST"""
    try:
        db = next(get_db())
        # csts = db.query(Cst).all()
        csts = []  # Temporário
        return render_template('admin/cst/list.html', csts=csts)
    except Exception as e:
        flash(f'Erro ao carregar CSTs: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/csosn')
@login_required
@permission_required('csosn.read')
def list_csosn():
    """Lista CSOSN"""
    try:
        db = next(get_db())
        # csosns = db.query(Csosn).all()
        csosns = []  # Temporário
        return render_template('admin/csosn/list.html', csosns=csosns)
    except Exception as e:
        flash(f'Erro ao carregar CSOSN: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/origens-mercadoria')
@login_required
@permission_required('origens_mercadoria.read')
def list_origens_mercadoria():
    """Lista origens de mercadoria"""
    try:
        db = next(get_db())
        # origens = db.query(OrigemMercadoria).all()
        origens = []  # Temporário
        return render_template('admin/origens_mercadoria/list.html', origens=origens)
    except Exception as e:
        flash(f'Erro ao carregar origens de mercadoria: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/motivos-desoneracao')
@login_required
@permission_required('motivos_desoneracao.read')
def list_motivos_desoneracao():
    """Lista motivos de desoneração"""
    try:
        db = next(get_db())
        # motivos = db.query(MotivoDesoneracao).all()
        motivos = []  # Temporário
        return render_template('admin/tributacao/motivos_desoneracao_list.html', motivos=motivos)
    except Exception as e:
        flash(f'Erro ao carregar motivos de desoneração: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/regimes-tributarios')
@login_required
@permission_required('regimes_tributarios.read')
def list_regimes_tributarios():
    """Lista regimes tributários"""
    try:
        db = next(get_db())
        # regimes = db.query(RegimeTributario).all()
        regimes = []  # Temporário
        return render_template('admin/regimes_tributarios/list.html', regimes=regimes)
    except Exception as e:
        flash(f'Erro ao carregar regimes tributários: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/destinatarios')
@login_required
@permission_required('destinatarios_nfe.read')
def list_destinatarios():
    """Lista destinatários"""
    try:
        db = next(get_db())
        # destinatarios = db.query(DestinatarioNfe).all()
        destinatarios = []  # Temporário
        return render_template('admin/destinatarios/list.html', destinatarios=destinatarios)
    except Exception as e:
        flash(f'Erro ao carregar destinatários: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/regras-tributacao')
@login_required
@permission_required('rules.read')
def list_regras_tributacao():
    """Lista regras de tributação"""
    try:
        db = next(get_db())
        # regras = db.query(RegraTributacao).all()
        regras = []  # Temporário
        return render_template('admin/regras_tributacao/list.html', regras=regras)
    except Exception as e:
        flash(f'Erro ao carregar regras de tributação: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

# ========== PERMISSÕES ==========
@admin_bp.route('/permissoes')
@login_required
@permission_required('permissions.read')
def list_permissions():
    """Lista permissões"""
    try:
        db = next(get_db())
        # permissions = db.query(Permission).all()
        permissions = []  # Temporário
        return render_template('admin/permissions/list.html', permissions=permissions)
    except Exception as e:
        flash(f'Erro ao carregar permissões: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))
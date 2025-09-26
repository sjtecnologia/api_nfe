from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database.connection import get_db
from sqlalchemy import text

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def home():
    """Página inicial - redireciona conforme autenticação"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Se é admin, vai para dashboard admin
    if current_user.is_admin():
        return redirect(url_for('admin.admin_home'))
    
    # Se não é admin, verifica clientes acessíveis
    accessible_clients = current_user.get_accessible_clients()
    
    if len(accessible_clients) == 0:
        flash('Você não tem acesso a nenhum cliente. Contate o administrador.', 'warning')
        return render_template('no_clients.html')
    elif len(accessible_clients) == 1:
        # Usuário tem acesso a apenas 1 cliente - redirecionar direto
        client = accessible_clients[0]
        session['current_client_id'] = client['cliente_id']
        session['current_client_name'] = client['razao_social']
        return redirect(url_for('cliente.dashboard', cliente_id=client['cliente_id']))
    else:
        # Usuário tem acesso a múltiplos clientes - mostrar seleção
        return render_template('select_client.html', clients=accessible_clients)

@home_bp.route('/select-client/<int:cliente_id>')
@login_required
def select_client(cliente_id):
    """Seleciona cliente para trabalhar"""
    if not current_user.can_access_client(cliente_id):
        flash('Você não tem acesso a este cliente.', 'danger')
        return redirect(url_for('home.home'))
    
    # Buscar nome do cliente para salvar na sessão
    db = next(get_db())
    result = db.execute(text("""
        SELECT razao_social, nome_fantasia 
        FROM clientes 
        WHERE cliente_id = :cliente_id
    """), {"cliente_id": cliente_id})
    
    cliente = result.first()
    if cliente:
        session['current_client_id'] = cliente_id
        session['current_client_name'] = cliente.razao_social
        flash(f'Cliente selecionado: {cliente.razao_social}', 'success')
        return redirect(url_for('cliente.dashboard', cliente_id=cliente_id))
    else:
        flash('Cliente não encontrado.', 'danger')
        return redirect(url_for('home.home'))

@home_bp.route('/switch-client')
@login_required
def switch_client():
    """Permite trocar de cliente"""
    if current_user.is_admin():
        return redirect(url_for('admin.admin_home'))
    
    accessible_clients = current_user.get_accessible_clients()
    
    if len(accessible_clients) <= 1:
        flash('Você tem acesso a apenas um cliente.', 'info')
        return redirect(url_for('home.home'))
    
    return render_template('select_client.html', 
                         clients=accessible_clients, 
                         switching=True)
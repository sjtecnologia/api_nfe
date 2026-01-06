from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from flask_login import login_required, current_user
from database.connection import get_db
from sqlalchemy import text

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def home():
    """Página inicial que redireciona baseado no usuário"""
    
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Se o usuário está logado, verificar se tem clientes
    if hasattr(current_user, 'clients') and current_user.clients:
        # Se tem apenas 1 cliente, redirecionar diretamente
        if len(current_user.clients) == 1:
            from utils.id_encoder import encode_id
            cliente_id = current_user.clients[0]['cliente_id']
            print(f"[?] Redirecionando usuário {current_user.username} para cliente {cliente_id}")
            return redirect(url_for('cliente.dashboard', cliente_hash=encode_id(cliente_id)))
        
        # Se tem múltiplos clientes, mostrar seleção
        return render_template('select_client.html', clientes=current_user.clients)
    
    # Se é admin, redirecionar para admin
    if current_user.is_super_admin():
        return redirect(url_for('admin.admin_home'))
    
    # Se não tem clientes nem é admin, fazer logout
    flash('Sua conta não tem permissões configuradas. Contate o administrador.', 'error')
    return redirect(url_for('auth.logout'))

@home_bp.route('/select-client/<int:cliente_id>')
@login_required
def select_client(cliente_id):
    """Selecionar cliente e redirecionar para dashboard"""
    
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Verificar se usuário tem acesso ao cliente
    if hasattr(current_user, 'clients') and current_user.clients:
        user_client_ids = [client['cliente_id'] for client in current_user.clients]
        if cliente_id in user_client_ids:
            from utils.id_encoder import encode_id
            session['current_client_id'] = cliente_id
            # Atualiza o nome do cliente na sessão
            for client in current_user.clients:
                if client['cliente_id'] == cliente_id:
                    session['current_client_name'] = client.get('razao_social') or client.get('nome_fantasia') or ''
                    break
            return redirect(url_for('cliente.dashboard', cliente_hash=encode_id(cliente_id)))
    
    flash('Você não tem acesso a este cliente.', 'error')
    return redirect(url_for('home.home'))

@home_bp.route('/switch-client')
@login_required
def switch_client():
    """Alternar entre clientes"""
    
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Limpar cliente atual da sessão
    session.pop('current_client_id', None)
    
    # Redirecionar para seleção
    return redirect(url_for('home.home'))
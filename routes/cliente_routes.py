from flask import Blueprint, render_template, session, g, flash, redirect, url_for
from flask_login import login_required, current_user
from database.connection import get_db
from auth.decorators import client_access_required
from sqlalchemy import text
from datetime import datetime

cliente_bp = Blueprint('cliente', __name__)

@cliente_bp.route('/dashboard/<int:cliente_id>')
@login_required
@client_access_required()
def dashboard(cliente_id):
    """Dashboard específico do cliente"""
    try:
        db = next(get_db())
        
        # Buscar dados do cliente
        cliente_result = db.execute(text("""
            SELECT cliente_id, razao_social, nome_fantasia, cnpj
            FROM clientes 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        
        cliente_data = cliente_result.first()
        if not cliente_data:
            flash('Cliente não encontrado ou inativo.', 'danger')
            return redirect(url_for('home.home'))
            
        cliente = dict(cliente_data._mapping)
        
        # Estatísticas do cliente
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Total de NFes
        total_nfes_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM nfe_emitidas 
            WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        total_nfes = total_nfes_result.first().total
        
        # NFes no ano atual
        nfes_ano_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM nfe_emitidas 
            WHERE cliente_id = :cliente_id 
            AND EXTRACT(YEAR FROM data_criacao) = :year
        """), {"cliente_id": cliente_id, "year": current_year})
        nfes_ano = nfes_ano_result.first().total
        
        # NFes no mês atual
        nfes_mes_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM nfe_emitidas 
            WHERE cliente_id = :cliente_id 
            AND EXTRACT(YEAR FROM data_criacao) = :year
            AND EXTRACT(MONTH FROM data_criacao) = :month
        """), {"cliente_id": cliente_id, "year": current_year, "month": current_month})
        nfes_mes = nfes_mes_result.first().total
        
        # Total de produtos
        produtos_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM produtos 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        total_produtos = produtos_result.first().total
        
        stats = {
            'total_nfes': total_nfes,
            'nfes_ano': nfes_ano,
            'nfes_mes': nfes_mes,
            'total_produtos': total_produtos
        }
        
        return render_template('cliente/dashboard.html', 
                             cliente=cliente, 
                             stats=stats)
                             
    except Exception as e:
        flash(f'Erro ao carregar dashboard do cliente: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
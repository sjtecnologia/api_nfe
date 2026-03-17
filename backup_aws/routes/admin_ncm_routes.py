
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from database.connection import get_db
from routes.admin_routes import admin_bp

@admin_bp.route('/ncms/novo', methods=['GET', 'POST'])
@login_required
# Adicione permission_required se necessário
# @permission_required('ncms.create')
def create_ncm():
    db = next(get_db())
    try:
        if request.method == 'POST':
            codigo = request.form.get('codigo')
            descricao = request.form.get('descricao')
            # Adicione outros campos conforme necessário
            db.execute(text("""
                INSERT INTO ncms (codigo, descricao) VALUES (:codigo, :descricao)
            """), {'codigo': codigo, 'descricao': descricao})
            db.commit()
            flash('NCM cadastrado com sucesso!', 'success')
            return redirect(url_for('admin.list_ncms'))
        return render_template('admin/ncms/form.html', ncm=None)
    except Exception as e:
        db.rollback()
        flash(f'Erro ao cadastrar NCM: {e}', 'danger')
        return redirect(url_for('admin.list_ncms'))
    finally:
        db.close()

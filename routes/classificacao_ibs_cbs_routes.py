"""
Rotas para gerenciamento de Classificações IBS/CBS
Reforma Tributária LC 214/2025
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.connection import get_db
from database.models import ClassificacaoIBSCBS
from auth.decorators import login_required, permission_required
from sqlalchemy import func

classificacao_ibs_cbs_bp = Blueprint('classificacao_ibs_cbs', __name__, url_prefix='/admin/classificacoes-ibs-cbs')


@classificacao_ibs_cbs_bp.route('/', methods=['GET'])
@login_required
@permission_required(['admin', 'super_admin'])
def listar():
    """Listar todas as classificações IBS/CBS"""
    db = next(get_db())
    
    # Filtros opcionais
    busca = request.args.get('busca', '').strip()
    ativo = request.args.get('ativo', '')
    
    query = db.query(ClassificacaoIBSCBS)
    
    # Aplicar filtro de busca
    if busca:
        query = query.filter(
            (ClassificacaoIBSCBS.codigo.ilike(f'%{busca}%')) |
            (ClassificacaoIBSCBS.descricao.ilike(f'%{busca}%'))
        )
    
    # Aplicar filtro de status
    if ativo == '1':
        query = query.filter(ClassificacaoIBSCBS.ativo == True)
    elif ativo == '0':
        query = query.filter(ClassificacaoIBSCBS.ativo == False)
    
    # Ordenar por código
    classificacoes = query.order_by(ClassificacaoIBSCBS.codigo).all()
    
    return render_template(
        'admin/classificacoes_ibs_cbs/listar.html',
        classificacoes=classificacoes,
        busca=busca,
        ativo=ativo
    )


@classificacao_ibs_cbs_bp.route('/nova', methods=['GET', 'POST'])
@login_required
@permission_required(['admin', 'super_admin'])
def criar():
    """Criar nova classificação IBS/CBS"""
    if request.method == 'GET':
        return render_template('admin/classificacoes_ibs_cbs/form.html')
    
    db = next(get_db())
    
    try:
        # Validar se código já existe
        codigo = request.form.get('codigo', '').strip()
        existe = db.query(ClassificacaoIBSCBS).filter_by(codigo=codigo).first()
        
        if existe:
            flash('Código já existe! Use um código único.', 'danger')
            return redirect(url_for('classificacao_ibs_cbs.criar'))
        
        # Criar nova classificação
        nova = ClassificacaoIBSCBS(
            codigo=codigo,
            descricao=request.form.get('descricao', '').strip(),
            aliquota_ibs_uf=float(request.form.get('aliquota_ibs_uf', 0)),
            aliquota_ibs_mun=float(request.form.get('aliquota_ibs_mun', 0)),
            aliquota_cbs=float(request.form.get('aliquota_cbs', 0)),
            ativo=request.form.get('ativo') == 'on'
        )
        
        db.add(nova)
        db.commit()
        
        flash(f'Classificação {codigo} criada com sucesso!', 'success')
        return redirect(url_for('classificacao_ibs_cbs.listar'))
        
    except Exception as e:
        db.rollback()
        flash(f'Erro ao criar classificação: {str(e)}', 'danger')
        return redirect(url_for('classificacao_ibs_cbs.criar'))


@classificacao_ibs_cbs_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(['admin', 'super_admin'])
def editar(id):
    """Editar classificação IBS/CBS existente"""
    db = next(get_db())
    classificacao = db.query(ClassificacaoIBSCBS).filter_by(classificacao_id=id).first()
    
    if not classificacao:
        flash('Classificação não encontrada!', 'danger')
        return redirect(url_for('classificacao_ibs_cbs.listar'))
    
    if request.method == 'GET':
        return render_template('admin/classificacoes_ibs_cbs/form.html', classificacao=classificacao)
    
    try:
        # Validar se novo código já existe (se foi alterado)
        novo_codigo = request.form.get('codigo', '').strip()
        if novo_codigo != classificacao.codigo:
            existe = db.query(ClassificacaoIBSCBS).filter_by(codigo=novo_codigo).first()
            if existe:
                flash('Código já existe! Use um código único.', 'danger')
                return redirect(url_for('classificacao_ibs_cbs.editar', id=id))
        
        # Atualizar dados
        classificacao.codigo = novo_codigo
        classificacao.descricao = request.form.get('descricao', '').strip()
        classificacao.aliquota_ibs_uf = float(request.form.get('aliquota_ibs_uf', 0))
        classificacao.aliquota_ibs_mun = float(request.form.get('aliquota_ibs_mun', 0))
        classificacao.aliquota_cbs = float(request.form.get('aliquota_cbs', 0))
        classificacao.ativo = request.form.get('ativo') == 'on'
        
        db.commit()
        
        flash(f'Classificação {novo_codigo} atualizada com sucesso!', 'success')
        return redirect(url_for('classificacao_ibs_cbs.listar'))
        
    except Exception as e:
        db.rollback()
        flash(f'Erro ao atualizar classificação: {str(e)}', 'danger')
        return redirect(url_for('classificacao_ibs_cbs.editar', id=id))


@classificacao_ibs_cbs_bp.route('/deletar/<int:id>', methods=['POST'])
@login_required
@permission_required(['admin', 'super_admin'])
def deletar(id):
    """Deletar classificação IBS/CBS"""
    db = next(get_db())
    classificacao = db.query(ClassificacaoIBSCBS).filter_by(classificacao_id=id).first()
    
    if not classificacao:
        flash('Classificação não encontrada!', 'danger')
        return redirect(url_for('classificacao_ibs_cbs.listar'))
    
    try:
        codigo = classificacao.codigo
        db.delete(classificacao)
        db.commit()
        
        flash(f'Classificação {codigo} deletada com sucesso!', 'success')
        
    except Exception as e:
        db.rollback()
        flash(f'Erro ao deletar classificação: {str(e)}', 'danger')
    
    return redirect(url_for('classificacao_ibs_cbs.listar'))


@classificacao_ibs_cbs_bp.route('/toggle-status/<int:id>', methods=['POST'])
@login_required
@permission_required(['admin', 'super_admin'])
def toggle_status(id):
    """Ativar/desativar classificação"""
    db = next(get_db())
    classificacao = db.query(ClassificacaoIBSCBS).filter_by(classificacao_id=id).first()
    
    if not classificacao:
        return jsonify({'success': False, 'message': 'Classificação não encontrada'}), 404
    
    try:
        classificacao.ativo = not classificacao.ativo
        db.commit()
        
        status = 'ativada' if classificacao.ativo else 'desativada'
        return jsonify({
            'success': True,
            'message': f'Classificação {status} com sucesso',
            'ativo': classificacao.ativo
        })
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

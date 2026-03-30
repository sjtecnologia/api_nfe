"""
Rotas para gerenciamento de Planos e Assinaturas de NFe
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text, func
from datetime import date, datetime, timedelta
from decimal import Decimal

from database.connection import get_db
from database.models import PlanoNFe, AssinaturaCliente, Cliente
from auth.decorators import super_admin_required

planos_bp = Blueprint('planos', __name__, url_prefix='/planos')

# ============================================================================
# GERENCIAMENTO DE PLANOS
# ============================================================================

@planos_bp.route('/')
@login_required
@super_admin_required()
def list_planos():
    """Lista todos os planos cadastrados"""
    db = next(get_db())
    
    try:
        planos = db.query(PlanoNFe).order_by(
            PlanoNFe.tipo_plano,
            PlanoNFe.ordem_exibicao
        ).all()
        
        # Contar assinaturas ativas por plano
        stats = {}
        for plano in planos:
            count = db.query(func.count(AssinaturaCliente.assinatura_id)).filter(
                AssinaturaCliente.plano_id == plano.plano_id,
                AssinaturaCliente.status == 'ATIVA'
            ).scalar()
            stats[plano.plano_id] = count
        
        return render_template('admin/planos/list.html', 
                             planos=planos,
                             stats=stats)
    except Exception as e:
        flash(f'Erro ao listar planos: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@planos_bp.route('/criar', methods=['GET', 'POST'])
@login_required
@super_admin_required()
def criar_plano():
    """Criar novo plano"""
    db = next(get_db())
    
    if request.method == 'POST':
        try:
            # Capturar dados do formulário
            nome = request.form.get('nome')
            descricao = request.form.get('descricao', '')
            tipo_plano = request.form.get('tipo_plano')
            quantidade_nfes = request.form.get('quantidade_nfes')
            valor_mensal = request.form.get('valor_mensal')
            valor_por_nfe = request.form.get('valor_por_nfe', '0')
            ativo = request.form.get('ativo') == 'on'
            ordem_exibicao = request.form.get('ordem_exibicao', '0')
            
            # Validações
            if not nome or not tipo_plano or not valor_mensal:
                flash('Preencha todos os campos obrigatórios', 'warning')
                return redirect(url_for('planos.criar_plano'))
            
            # Converter valores
            quantidade_nfes_int = int(quantidade_nfes) if quantidade_nfes and quantidade_nfes.strip() else None
            valor_mensal_dec = Decimal(valor_mensal.replace(',', '.'))
            valor_por_nfe_dec = Decimal(valor_por_nfe.replace(',', '.')) if valor_por_nfe else Decimal('0')
            ordem_int = int(ordem_exibicao) if ordem_exibicao else 0
            
            # Criar plano
            novo_plano = PlanoNFe(
                nome=nome,
                descricao=descricao,
                tipo_plano=tipo_plano,
                quantidade_nfes=quantidade_nfes_int,
                valor_mensal=valor_mensal_dec,
                valor_por_nfe=valor_por_nfe_dec,
                ativo=ativo,
                ordem_exibicao=ordem_int
            )
            
            db.add(novo_plano)
            db.commit()
            
            flash(f'Plano "{nome}" criado com sucesso!', 'success')
            return redirect(url_for('planos.list_planos'))
            
        except Exception as e:
            db.rollback()
            flash(f'Erro ao criar plano: {str(e)}', 'danger')
    
    return render_template('admin/planos/form.html', plano=None)


@planos_bp.route('/<int:plano_id>/editar', methods=['GET', 'POST'])
@login_required
@super_admin_required()
def editar_plano(plano_id):
    """Editar plano existente"""
    db = next(get_db())
    
    plano = db.query(PlanoNFe).filter_by(plano_id=plano_id).first()
    if not plano:
        flash('Plano não encontrado', 'danger')
        return redirect(url_for('planos.list_planos'))
    
    if request.method == 'POST':
        try:
            plano.nome = request.form.get('nome')
            plano.descricao = request.form.get('descricao', '')
            plano.tipo_plano = request.form.get('tipo_plano')
            
            quantidade = request.form.get('quantidade_nfes')
            plano.quantidade_nfes = int(quantidade) if quantidade and quantidade.strip() else None
            
            plano.valor_mensal = Decimal(request.form.get('valor_mensal').replace(',', '.'))
            
            valor_nfe = request.form.get('valor_por_nfe', '0')
            plano.valor_por_nfe = Decimal(valor_nfe.replace(',', '.')) if valor_nfe else Decimal('0')
            
            plano.ativo = request.form.get('ativo') == 'on'
            
            ordem = request.form.get('ordem_exibicao', '0')
            plano.ordem_exibicao = int(ordem) if ordem else 0
            
            db.commit()
            
            flash(f'Plano "{plano.nome}" atualizado com sucesso!', 'success')
            return redirect(url_for('planos.list_planos'))
            
        except Exception as e:
            db.rollback()
            flash(f'Erro ao atualizar plano: {str(e)}', 'danger')
    
    return render_template('admin/planos/form.html', plano=plano)


@planos_bp.route('/<int:plano_id>/toggle', methods=['POST'])
@login_required
@super_admin_required()
def toggle_plano(plano_id):
    """Ativar/desativar plano"""
    db = next(get_db())
    
    try:
        plano = db.query(PlanoNFe).filter_by(plano_id=plano_id).first()
        if not plano:
            return jsonify({'success': False, 'message': 'Plano não encontrado'}), 404
        
        plano.ativo = not plano.ativo
        db.commit()
        
        status = 'ativado' if plano.ativo else 'desativado'
        return jsonify({'success': True, 'message': f'Plano {status} com sucesso', 'ativo': plano.ativo})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# GERENCIAMENTO DE ASSINATURAS
# ============================================================================

@planos_bp.route('/assinaturas')
@login_required
@super_admin_required()
def list_assinaturas():
    """Lista todas as assinaturas"""
    db = next(get_db())
    
    try:
        # Filtros
        status_filter = request.args.get('status', '')
        cliente_filter = request.args.get('cliente', '')
        
        query = db.query(AssinaturaCliente).join(Cliente).join(PlanoNFe)
        
        if status_filter:
            query = query.filter(AssinaturaCliente.status == status_filter)
        
        if cliente_filter:
            query = query.filter(Cliente.razao_social.ilike(f'%{cliente_filter}%'))
        
        assinaturas = query.order_by(AssinaturaCliente.data_inicio.desc()).all()
        
        return render_template('admin/planos/assinaturas_list.html', 
                             assinaturas=assinaturas,
                             status_filter=status_filter,
                             cliente_filter=cliente_filter)
    except Exception as e:
        flash(f'Erro ao listar assinaturas: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@planos_bp.route('/assinaturas/criar', methods=['GET', 'POST'])
@login_required
@super_admin_required()
def criar_assinatura():
    """Criar nova assinatura para cliente"""
    db = next(get_db())
    
    if request.method == 'POST':
        try:
            cliente_id = request.form.get('cliente_id')
            plano_id = request.form.get('plano_id')
            data_inicio = request.form.get('data_inicio')
            dia_vencimento = request.form.get('dia_vencimento', '10')
            observacoes = request.form.get('observacoes', '')
            
            if not cliente_id or not plano_id or not data_inicio:
                flash('Preencha todos os campos obrigatórios', 'warning')
                return redirect(url_for('planos.criar_assinatura'))
            
            # Verificar se cliente já tem assinatura ativa
            assinatura_existente = db.query(AssinaturaCliente).filter(
                AssinaturaCliente.cliente_id == cliente_id,
                AssinaturaCliente.status == 'ATIVA'
            ).first()
            
            if assinatura_existente:
                flash('Cliente já possui uma assinatura ativa. Cancele a anterior primeiro.', 'warning')
                return redirect(url_for('planos.criar_assinatura'))
            
            # Converter data
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            periodo_fim = data_inicio_obj + timedelta(days=30)
            
            # Criar assinatura
            nova_assinatura = AssinaturaCliente(
                cliente_id=int(cliente_id),
                plano_id=int(plano_id),
                data_inicio=data_inicio_obj,
                status='ATIVA',
                dia_vencimento=int(dia_vencimento),
                nfes_consumidas=0,
                periodo_ref_inicio=data_inicio_obj,
                periodo_ref_fim=periodo_fim,
                observacoes=observacoes
            )
            
            db.add(nova_assinatura)
            db.commit()
            
            flash('Assinatura criada com sucesso!', 'success')
            return redirect(url_for('planos.list_assinaturas'))
            
        except Exception as e:
            db.rollback()
            flash(f'Erro ao criar assinatura: {str(e)}', 'danger')
    
    # GET - Carregar clientes e planos
    clientes = db.query(Cliente).filter_by(ativo=True).order_by(Cliente.razao_social).all()
    planos = db.query(PlanoNFe).filter_by(ativo=True).order_by(PlanoNFe.ordem_exibicao).all()
    
    return render_template('admin/planos/assinatura_form.html', 
                         assinatura=None,
                         clientes=clientes,
                         planos=planos,
                         date=date)


@planos_bp.route('/assinaturas/<int:assinatura_id>/editar', methods=['GET', 'POST'])
@login_required
@super_admin_required()
def editar_assinatura(assinatura_id):
    """Editar assinatura existente"""
    db = next(get_db())
    
    assinatura = db.query(AssinaturaCliente).filter_by(assinatura_id=assinatura_id).first()
    if not assinatura:
        flash('Assinatura não encontrada', 'danger')
        return redirect(url_for('planos.list_assinaturas'))
    
    if request.method == 'POST':
        try:
            assinatura.plano_id = int(request.form.get('plano_id'))
            assinatura.status = request.form.get('status')
            assinatura.dia_vencimento = int(request.form.get('dia_vencimento', '10'))
            
            data_fim = request.form.get('data_fim')
            assinatura.data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date() if data_fim else None
            
            assinatura.observacoes = request.form.get('observacoes', '')
            
            db.commit()
            
            flash('Assinatura atualizada com sucesso!', 'success')
            return redirect(url_for('planos.list_assinaturas'))
            
        except Exception as e:
            db.rollback()
            flash(f'Erro ao atualizar assinatura: {str(e)}', 'danger')
    
    planos = db.query(PlanoNFe).filter_by(ativo=True).order_by(PlanoNFe.ordem_exibicao).all()
    
    return render_template('admin/planos/assinatura_form.html', 
                         assinatura=assinatura,
                         clientes=None,  # Não permite mudar cliente
                         planos=planos,
                         date=date)


@planos_bp.route('/assinaturas/<int:assinatura_id>/renovar', methods=['POST'])
@login_required
@super_admin_required()
def renovar_assinatura(assinatura_id):
    """Renovar período da assinatura (zera contador)"""
    db = next(get_db())
    
    try:
        result = db.execute(
            text("SELECT renovar_periodo_assinatura(:assinatura_id)"),
            {"assinatura_id": assinatura_id}
        ).scalar()
        
        if result:
            db.commit()
            flash('Período renovado com sucesso! Contador zerado.', 'success')
        else:
            flash('Assinatura não encontrada', 'danger')
            
    except Exception as e:
        db.rollback()
        flash(f'Erro ao renovar assinatura: {str(e)}', 'danger')
    
    return redirect(url_for('planos.list_assinaturas'))


@planos_bp.route('/assinaturas/<int:assinatura_id>/cancelar', methods=['POST'])
@login_required
@super_admin_required()
def cancelar_assinatura(assinatura_id):
    """Cancelar assinatura"""
    db = next(get_db())
    
    try:
        assinatura = db.query(AssinaturaCliente).filter_by(assinatura_id=assinatura_id).first()
        if not assinatura:
            return jsonify({'success': False, 'message': 'Assinatura não encontrada'}), 404
        
        assinatura.status = 'CANCELADA'
        assinatura.data_fim = date.today()
        db.commit()
        
        return jsonify({'success': True, 'message': 'Assinatura cancelada com sucesso'})
        
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# CONSULTAS E RELATÓRIOS
# ============================================================================

@planos_bp.route('/relatorio/consumo')
@login_required
@super_admin_required()
def relatorio_consumo():
    """Relatório de consumo por cliente"""
    db = next(get_db())
    
    try:
        # Buscar assinaturas ativas com consumo
        assinaturas = db.query(AssinaturaCliente).filter(
            AssinaturaCliente.status == 'ATIVA'
        ).join(Cliente).join(PlanoNFe).all()
        
        # Calcular estatísticas
        dados = []
        for assinatura in assinaturas:
            if assinatura.plano.quantidade_nfes:
                percentual = (assinatura.nfes_consumidas / assinatura.plano.quantidade_nfes) * 100
                restantes = assinatura.plano.quantidade_nfes - assinatura.nfes_consumidas
            else:
                percentual = 0
                restantes = 999999
            
            dados.append({
                'assinatura': assinatura,
                'percentual': round(percentual, 1),
                'restantes': restantes
            })
        
        # Ordenar por percentual (maior primeiro)
        dados.sort(key=lambda x: x['percentual'], reverse=True)
        
        return render_template('admin/planos/relatorio_consumo.html', dados=dados)
        
    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'danger')
        return redirect(url_for('planos.list_assinaturas'))


@planos_bp.route('/api/verificar-limite/<int:cliente_id>')
@login_required
def verificar_limite_api(cliente_id):
    """API para verificar se cliente pode emitir NFe"""
    db = next(get_db())
    
    try:
        result = db.execute(
            text("SELECT * FROM pode_emitir_nfe(:cliente_id)"),
            {"cliente_id": cliente_id}
        ).fetchone()
        
        return jsonify({
            'pode_emitir': result[0],
            'mensagem': result[1],
            'nfes_disponiveis': result[2],
            'plano_nome': result[3]
        })
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

"""
Rotas para o Catálogo de Serviços do cliente (análogo ao catálogo de Produtos).

Usado para cadastrar os serviços faturáveis via NFS-e, com valor padrão e
vínculo opcional a uma regra tributária (`regras_tributacao_servicos`).
"""

import logging
from typing import Any, Dict, List, Optional

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy import text

from database.connection import get_db
from auth.decorators import admin_required, block_viewer_access, viewer_or_higher_required

logger = logging.getLogger(__name__)

servicos_bp = Blueprint('servicos', __name__, url_prefix='/admin/servicos')


def _get_db():
    return next(get_db())


def _safe_row_to_dict(row, columns: Optional[List[str]] = None) -> Dict[str, Any]:
    if not row:
        return {}
    if hasattr(row, '_mapping'):
        return dict(row._mapping)
    if columns:
        return {col: (row[i] if i < len(row) else None) for i, col in enumerate(columns)}
    try:
        return dict(row)
    except Exception:
        return {}


def _get_or_none(field: str, convert_to=None):
    val = request.form.get(field)
    if val is None or val == '':
        return None
    try:
        if convert_to == int:
            return int(val)
        elif convert_to == float:
            return float(val)
        return val
    except (ValueError, TypeError):
        return None


@servicos_bp.route('')
@login_required
@admin_required()
def list_servicos():
    """Lista o catálogo de serviços do cliente atual, com filtros e paginação."""
    db = _get_db()
    try:
        cliente_id = request.args.get('cliente_id') or session.get('current_client_id')
        if not cliente_id:
            flash('Nenhum cliente selecionado.', 'error')
            return render_template('admin/servicos/list.html', servicos=[], cliente_id=None, cliente_nome='')
        cliente_id = int(cliente_id)

        filtro_codigo = request.args.get('codigo', '').strip()
        filtro_descricao = request.args.get('descricao', '').strip()
        filtro_ativo = request.args.get('ativo', '').strip()

        where_clauses = []
        params: Dict[str, Any] = {'cliente_id': cliente_id}

        if filtro_codigo:
            where_clauses.append("s.codigo_interno ILIKE :codigo")
            params['codigo'] = f'%{filtro_codigo}%'
        if filtro_descricao:
            where_clauses.append("s.descricao ILIKE :descricao")
            params['descricao'] = f'%{filtro_descricao}%'
        if filtro_ativo and filtro_ativo != 'todos':
            where_clauses.append("s.ativo = :ativo")
            params['ativo'] = filtro_ativo == '1'

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        PER_PAGE = 20
        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1

        total = db.execute(text(f"""
            SELECT COUNT(*) FROM servicos s WHERE s.cliente_id = :cliente_id{where_sql}
        """), params).scalar() or 0

        params['limit'] = PER_PAGE
        params['offset'] = (page - 1) * PER_PAGE

        rows = db.execute(text(f"""
            SELECT s.servico_id, s.codigo_interno, s.descricao, s.unidade, s.valor_padrao,
                   s.regra_id, s.ativo, r.codigo_servico_lc116, r.codigo_nbs, r.aliquota_iss
            FROM servicos s
            LEFT JOIN regras_tributacao_servicos r ON r.regra_id = s.regra_id
            WHERE s.cliente_id = :cliente_id{where_sql}
            ORDER BY s.descricao
            LIMIT :limit OFFSET :offset
        """), params).fetchall()
        servicos = [_safe_row_to_dict(r) for r in rows]

        cliente_row = db.execute(text("SELECT razao_social FROM clientes WHERE cliente_id = :cid"), {'cid': cliente_id}).fetchone()
        cliente_nome = cliente_row[0] if cliente_row else f"ID {cliente_id}"

        total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        pagination = {
            'page': page,
            'per_page': PER_PAGE,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
        }

        return render_template(
            'admin/servicos/list.html',
            servicos=servicos,
            cliente_id=cliente_id,
            cliente_nome=cliente_nome,
            pagination=pagination,
        )
    except Exception as e:
        logger.error(f"[X] Erro list_servicos: {e}")
        flash('Erro ao carregar catálogo de serviços', 'error')
        return render_template('admin/servicos/list.html', servicos=[], cliente_id=None, cliente_nome='')
    finally:
        db.close()


@servicos_bp.route('/add', methods=['GET'])
@login_required
@admin_required()
def create_servico():
    cliente_id = request.args.get('cliente_id') or session.get('current_client_id')
    if not cliente_id or str(cliente_id).lower() == 'none':
        flash('Selecione um cliente antes de cadastrar serviços.', 'error')
        return redirect(url_for('admin.list_clientes'))
    cliente_id = str(cliente_id)
    db = _get_db()
    try:
        regras = db.execute(text("""
            SELECT regra_id, codigo_servico_lc116, codigo_nbs, descricao_servico, aliquota_iss
            FROM regras_tributacao_servicos
            WHERE cliente_id = :cid AND ativo = true
            ORDER BY codigo_servico_lc116
        """), {'cid': cliente_id}).fetchall()
        return render_template(
            'admin/servicos/form.html',
            servico=None,
            regras=[dict(r._mapping) for r in regras],
            cliente_id=cliente_id,
        )
    except Exception as e:
        logger.error(f"[X] Erro create_servico: {e}")
        flash('Erro ao carregar formulário de serviço', 'error')
        return redirect(url_for('servicos.list_servicos', cliente_id=cliente_id))
    finally:
        db.close()


@servicos_bp.route('/add', methods=['POST'])
@login_required
@admin_required()
@block_viewer_access()
def store_servico():
    db = _get_db()
    try:
        cliente_id = request.form.get('cliente_id') or session.get('current_client_id')
        if not cliente_id or cliente_id == 'None':
            flash('Cliente não selecionado.', 'error')
            return redirect(url_for('servicos.list_servicos'))

        data = {
            'cliente_id': int(cliente_id),
            'codigo_interno': request.form.get('codigo_interno'),
            'descricao': request.form.get('descricao'),
            'unidade': request.form.get('unidade', 'UN'),
            'valor_padrao': _get_or_none('valor_padrao', float) or 0,
            'regra_id': _get_or_none('regra_id', int),
            'created_by_user_id': current_user.id,
            'ativo': True,
        }
        db.execute(text("""
            INSERT INTO servicos (cliente_id, codigo_interno, descricao, unidade, valor_padrao, regra_id, created_by_user_id, ativo)
            VALUES (:cliente_id, :codigo_interno, :descricao, :unidade, :valor_padrao, :regra_id, :created_by_user_id, :ativo)
        """), data)
        db.commit()
        flash('Serviço cadastrado com sucesso', 'success')
        return redirect(url_for('servicos.list_servicos', cliente_id=cliente_id))
    except Exception as e:
        db.rollback()
        logger.error(f"[X] Erro store_servico: {e}")
        flash('Erro ao cadastrar serviço', 'error')
        return redirect(url_for('servicos.create_servico'))
    finally:
        db.close()


@servicos_bp.route('/<int:servico_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required()
@block_viewer_access()
def editar_servico(servico_id: int):
    db = _get_db()
    try:
        if request.method == 'POST':
            data = {
                'servico_id': servico_id,
                'codigo_interno': request.form.get('codigo_interno'),
                'descricao': request.form.get('descricao'),
                'unidade': request.form.get('unidade', 'UN'),
                'valor_padrao': _get_or_none('valor_padrao', float) or 0,
                'regra_id': _get_or_none('regra_id', int),
            }
            db.execute(text("""
                UPDATE servicos
                SET codigo_interno=:codigo_interno,
                    descricao=:descricao,
                    unidade=:unidade,
                    valor_padrao=:valor_padrao,
                    regra_id=:regra_id,
                    data_atualizacao=CURRENT_TIMESTAMP
                WHERE servico_id=:servico_id
            """), data)
            db.commit()
            flash('Serviço atualizado', 'success')
            row = db.execute(text("SELECT cliente_id FROM servicos WHERE servico_id = :sid"), {'sid': servico_id}).fetchone()
            cliente_id = row[0] if row else None
            return redirect(url_for('servicos.list_servicos', cliente_id=cliente_id))

        row = db.execute(text("SELECT * FROM servicos WHERE servico_id = :sid"), {'sid': servico_id}).fetchone()
        servico = dict(row._mapping) if row else None
        if not servico:
            flash('Serviço não encontrado', 'danger')
            return redirect(url_for('servicos.list_servicos'))

        regras = db.execute(text("""
            SELECT regra_id, codigo_servico_lc116, codigo_nbs, descricao_servico, aliquota_iss
            FROM regras_tributacao_servicos
            WHERE cliente_id = :cid AND ativo = true
            ORDER BY codigo_servico_lc116
        """), {'cid': servico['cliente_id']}).fetchall()

        return render_template(
            'admin/servicos/form.html',
            servico=servico,
            regras=[dict(r._mapping) for r in regras],
            cliente_id=servico['cliente_id'],
        )
    except Exception as e:
        db.rollback()
        logger.error(f"[X] Erro editar_servico: {e}")
        flash('Erro ao editar serviço', 'error')
        return redirect(url_for('servicos.list_servicos'))
    finally:
        db.close()


@servicos_bp.route('/<int:servico_id>/duplicar', methods=['POST'])
@login_required
@admin_required()
@block_viewer_access()
def duplicar_servico(servico_id: int):
    db = _get_db()
    cliente_id = None
    try:
        row = db.execute(text("SELECT * FROM servicos WHERE servico_id = :sid"), {'sid': servico_id}).fetchone()
        servico = dict(row._mapping) if row else None
        if not servico:
            flash('Serviço não encontrado', 'danger')
            return redirect(url_for('servicos.list_servicos'))

        cliente_id = servico['cliente_id']
        novo_codigo = f"{servico['codigo_interno']}-COPIA"
        db.execute(text("""
            INSERT INTO servicos (cliente_id, codigo_interno, descricao, unidade, valor_padrao, regra_id, created_by_user_id, ativo)
            VALUES (:cliente_id, :codigo_interno, :descricao, :unidade, :valor_padrao, :regra_id, :created_by_user_id, true)
        """), {
            'cliente_id': servico['cliente_id'],
            'codigo_interno': novo_codigo,
            'descricao': f"{servico['descricao']} (cópia)",
            'unidade': servico['unidade'],
            'valor_padrao': servico['valor_padrao'],
            'regra_id': servico['regra_id'],
            'created_by_user_id': current_user.id,
        })
        db.commit()
        flash('Serviço duplicado com sucesso', 'success')
    except Exception as e:
        db.rollback()
        logger.error(f"[X] Erro duplicar_servico: {e}")
        flash('Erro ao duplicar serviço', 'error')
    finally:
        db.close()
    return redirect(url_for('servicos.list_servicos', cliente_id=cliente_id))


@servicos_bp.route('/alterar-status', methods=['POST'])
@login_required
@admin_required()
@block_viewer_access()
def alterar_status_servico():
    db = _get_db()
    try:
        servico_id = request.form.get('servico_id')
        ativo = request.form.get('ativo') == 'true'
        db.execute(text("UPDATE servicos SET ativo = :ativo WHERE servico_id = :sid"), {'ativo': ativo, 'sid': servico_id})
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        logger.error(f"[X] Erro alterar_status_servico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@servicos_bp.route('/<int:servico_id>/delete', methods=['POST'])
@login_required
@admin_required()
@block_viewer_access()
def delete_servico(servico_id: int):
    db = _get_db()
    try:
        row = db.execute(text("SELECT cliente_id FROM servicos WHERE servico_id = :sid"), {'sid': servico_id}).fetchone()
        cliente_id = row[0] if row else None
        db.execute(text("DELETE FROM servicos WHERE servico_id = :sid"), {'sid': servico_id})
        db.commit()
        flash('Serviço excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        logger.error(f"[X] Erro delete_servico: {e}")
        flash('Erro ao excluir serviço', 'error')
        cliente_id = None
    finally:
        db.close()
    return redirect(url_for('servicos.list_servicos', cliente_id=cliente_id))


@servicos_bp.route('/api/list')
@login_required
@viewer_or_higher_required()
def api_list_servicos():
    """Lista JSON dos serviços ativos do cliente atual — usada para autocompletar a emissão de NFS-e."""
    db = _get_db()
    try:
        cliente_id = request.args.get('cliente_id') or session.get('current_client_id')
        if not cliente_id:
            return jsonify([])
        rows = db.execute(text("""
            SELECT s.servico_id, s.codigo_interno, s.descricao, s.unidade, s.valor_padrao,
                   r.codigo_servico_lc116, r.codigo_nbs, r.aliquota_iss
            FROM servicos s
            LEFT JOIN regras_tributacao_servicos r ON r.regra_id = s.regra_id
            WHERE s.cliente_id = :cid AND s.ativo = true
            ORDER BY s.descricao
        """), {'cid': cliente_id}).fetchall()
        data = []
        for r in rows:
            m = dict(r._mapping)
            data.append({
                'servico_id': m['servico_id'],
                'codigo_interno': m['codigo_interno'],
                'descricao': m['descricao'],
                'unidade': m['unidade'],
                'valor_padrao': float(m['valor_padrao']) if m['valor_padrao'] is not None else 0,
                'codigo_servico_lc116': m['codigo_servico_lc116'],
                'codigo_nbs': m['codigo_nbs'],
                'aliquota_iss': float(m['aliquota_iss']) if m['aliquota_iss'] is not None else None,
            })
        return jsonify(data)
    except Exception as e:
        logger.error(f"[X] Erro api_list_servicos: {e}")
        return jsonify([]), 500
    finally:
        db.close()

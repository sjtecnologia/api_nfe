"""
routes/admin_api_routes.py

Blueprint com as rotas de API JSON do módulo admin.
Extrai as rotas puramente JSON (sem render_template) de admin_routes.py,
mantendo as URLs inalteradas (/admin/api/...).

Registrado em app.py com url_prefix='/admin'.
"""
import logging
from flask import Blueprint, jsonify, request
from flask_login import login_required
from database.connection import get_db

logger = logging.getLogger(__name__)

admin_api_bp = Blueprint('admin_api', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Classificações IBS/CBS
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/classificacoes-ibs-cbs', methods=['GET'])
@login_required
def api_classificacoes_ibs_cbs():
    """Lista classificações IBS/CBS ativas — usado em formulários de emissão (CRT=3)."""
    from database.models import ClassificacaoIBSCBS

    db = next(get_db())
    try:
        rows = db.query(ClassificacaoIBSCBS).filter_by(ativo=True).all()
        resultado = [
            {
                'id':               c.classificacao_id,
                'codigo':           c.codigo,
                'descricao':        c.descricao,
                'aliquota_ibs_uf':  float(c.aliquota_ibs_uf),
                'aliquota_ibs_mun': float(c.aliquota_ibs_mun),
                'aliquota_cbs':     float(c.aliquota_cbs),
            }
            for c in rows
        ]
        return jsonify({'success': True, 'data': resultado})

    except Exception as e:
        logger.error('Erro ao buscar classificações IBS/CBS: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Regime tributário do cliente
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/regime-tributario/<int:cliente_id>', methods=['GET'])
@login_required
def api_regime_tributario_cliente(cliente_id):
    """
    Retorna CRT do regime tributário do cliente.
    Usado nos formulários de emissão para controlar exibição de campos IBS/CBS.
    """
    from database.models import Cliente

    db = next(get_db())
    try:
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente não encontrado'}), 404

        crt         = cliente.regime_tributario.crt  if cliente.regime_tributario else 1
        regime_nome = cliente.regime_tributario.nome if cliente.regime_tributario else 'Simples Nacional'

        return jsonify({
            'success':       True,
            'crt':           crt,
            'regime_nome':   regime_nome,
            'requer_ibs_cbs': crt == 3,
        })

    except Exception as e:
        logger.error('Erro ao buscar regime tributário cliente %s: %s', cliente_id, e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Informações do cliente
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/cliente/<int:cliente_id>/info', methods=['GET'])
@login_required
def api_cliente_info(cliente_id):
    """
    Retorna informações do cliente para ajustar interface dinamicamente
    (regime tributário, UF, Simples Nacional vs Regime Normal).
    """
    from sqlalchemy import text

    db = next(get_db())
    try:
        row = db.execute(text("""
            SELECT c.cliente_id, c.razao_social, c.uf,
                   c.regime_tributario_id,
                   rt.nome AS regime_nome
            FROM clientes c
            LEFT JOIN regimes_tributarios rt
                   ON c.regime_tributario_id = rt.regime_tributario_id
            WHERE c.cliente_id = :cid
        """), {'cid': cliente_id}).fetchone()

        if not row:
            return jsonify({'erro': 'Cliente não encontrado'}), 404

        d = dict(row._mapping)
        regime_nome       = (d.get('regime_nome') or '').lower()
        is_simples        = 'simples' in regime_nome

        return jsonify({
            'cliente_id':           d['cliente_id'],
            'razao_social':         d['razao_social'],
            'uf':                   d['uf'],
            'regime_tributario_id': d['regime_tributario_id'],
            'regime_nome':          d.get('regime_nome'),
            'is_simples_nacional':  is_simples,
            'mostrar_cst':          not is_simples,
            'mostrar_csosn':        is_simples,
        })

    except Exception as e:
        logger.error('Erro ao buscar dados do cliente %s: %s', cliente_id, e, exc_info=True)
        return jsonify({'erro': 'Erro interno do servidor'}), 500
    finally:
        db.close()

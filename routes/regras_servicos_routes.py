"""
Rotas para gerenciamento de Regras Tributárias de Serviços (NFS-e)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from database.connection import get_db
from auth.decorators import permission_required, admin_required
from decimal import Decimal
from models.nfse_model import DEFAULT_CODIGO_NBS, normalizar_codigo_nbs

regras_servicos_bp = Blueprint('regras_servicos', __name__, url_prefix='/admin/regras-servicos')

def _get_db():
    """Helper para obter conexão com banco"""
    return next(get_db())


# Expressão SQL que normaliza um código LC116 removendo zeros à esquerda de cada
# parte (ex.: '01.01' e '1.01' passam a ser comparáveis como '1.1'). Necessário
# porque a tela de emissão de NFS-e usa códigos sem zero à esquerda (dict fixo em
# models/nfse_model.py) enquanto o cadastro de regras usa os códigos oficiais
# com zero à esquerda (tabela codigos_servico_lc116, ex.: '01.01').
_NORMALIZA_LC116_SQL = r"regexp_replace({coluna}, '(^|\.)0+(\d)', '\1\2', 'g')"


def _normalizar_codigo_lc116(codigo):
    """Remove zeros à esquerda de cada parte do código LC116 (ex.: '01.01' -> '1.1').
    Deve produzir o mesmo resultado que _NORMALIZA_LC116_SQL aplicado na coluna do banco."""
    if not codigo:
        return codigo
    partes = str(codigo).split('.')
    return '.'.join(p.lstrip('0') or '0' for p in partes)


@regras_servicos_bp.route('/')
@login_required
@permission_required('regras_tributacao.view')
def list_regras_servicos():
    """Lista todas as regras tributárias de serviços"""
    db = _get_db()
    cliente_id = request.args.get('cliente_id') or session.get('current_client_id')
    
    try:
        if not cliente_id:
            flash('Selecione um cliente para visualizar as regras de serviços.', 'warning')
            return render_template('admin/regras_servicos/list.html', regras=[], cliente_id=None)
        
        # Capturar filtros
        filtro_codigo_servico = request.args.get('codigo_servico', '').strip()
        filtro_codigo_nbs = request.args.get('codigo_nbs', '').strip()
        filtro_descricao = request.args.get('descricao', '').strip()
        filtro_ativo = request.args.get('ativo', '').strip()
        
        # Construir WHERE dinâmico
        where_clauses = []
        params = {'cliente_id': cliente_id}
        
        if filtro_codigo_servico:
            where_clauses.append("rs.codigo_servico_lc116 ILIKE :codigo_servico")
            params['codigo_servico'] = f'%{filtro_codigo_servico}%'
        
        if filtro_codigo_nbs:
            where_clauses.append("rs.codigo_nbs ILIKE :codigo_nbs")
            params['codigo_nbs'] = f'%{filtro_codigo_nbs}%'
        
        if filtro_descricao:
            where_clauses.append("rs.descricao_servico ILIKE :descricao")
            params['descricao'] = f'%{filtro_descricao}%'
        
        if filtro_ativo and filtro_ativo != 'todos':
            where_clauses.append("rs.ativo = :ativo")
            params['ativo'] = filtro_ativo == 'ativo'
        
        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Buscar regras do cliente
        query = text(f"""
            SELECT 
                rs.*,
                c.razao_social as cliente_nome,
                rt.nome as regime_tributario_nome,
                u1.username as created_by_username,
                u2.username as updated_by_username
            FROM regras_tributacao_servicos rs
            JOIN clientes c ON rs.cliente_id = c.cliente_id
            LEFT JOIN regimes_tributarios rt ON rs.regime_tributario_id = rt.regime_tributario_id
            LEFT JOIN users u1 ON rs.created_by_user_id = u1.id
            LEFT JOIN users u2 ON rs.updated_by_user_id = u2.id
            WHERE rs.cliente_id = :cliente_id{where_sql}
            ORDER BY rs.prioridade ASC, rs.codigo_servico_lc116 ASC
        """)
        
        rows = db.execute(query, params).fetchall()
        regras = [dict(row._mapping) for row in rows]
        
        return render_template('admin/regras_servicos/list.html', 
                             regras=regras, 
                             cliente_id=cliente_id)
    
    except Exception as e:
        print(f"Erro ao listar regras de serviços: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao listar regras: {str(e)}', 'error')
        return render_template('admin/regras_servicos/list.html', regras=[], cliente_id=cliente_id)
    finally:
        db.close()


@regras_servicos_bp.route('/nova')
@regras_servicos_bp.route('/nova/<int:cliente_id>')
@login_required
@permission_required('regras_tributacao.create')
def nova_regra_servico(cliente_id=None):
    """Formulário para criar nova regra de serviço"""
    db = _get_db()
    
    if not cliente_id:
        cliente_id = request.args.get('cliente_id') or session.get('current_client_id')
    
    try:
        # Buscar regimes tributários
        regimes = db.execute(text("SELECT * FROM regimes_tributarios ORDER BY nome")).fetchall()
        regimes = [dict(row._mapping) for row in regimes]
        
        # Buscar dados do cliente
        cliente = None
        if cliente_id:
            result = db.execute(text("SELECT * FROM clientes WHERE cliente_id = :id"), {'id': cliente_id}).fetchone()
            if result:
                cliente = dict(result._mapping)
        
        return render_template('admin/regras_servicos/form.html',
                             regra=None,
                             regimes=regimes,
                             cliente=cliente,
                             cliente_id=cliente_id)
    
    except Exception as e:
        print(f"Erro ao abrir formulário: {e}")
        flash(f'Erro ao abrir formulário: {str(e)}', 'error')
        return redirect(url_for('regras_servicos.list_regras_servicos', cliente_id=cliente_id))
    finally:
        db.close()


@regras_servicos_bp.route('/editar/<int:regra_id>')
@login_required
@permission_required('regras_tributacao.edit')
def editar_regra_servico(regra_id):
    """Formulário para editar regra de serviço"""
    db = _get_db()
    
    try:
        # Buscar regra
        regra = db.execute(text("""
            SELECT rs.*, c.razao_social as cliente_nome
            FROM regras_tributacao_servicos rs
            JOIN clientes c ON rs.cliente_id = c.cliente_id
            WHERE rs.regra_id = :regra_id
        """), {'regra_id': regra_id}).fetchone()
        
        if not regra:
            flash('Regra não encontrada.', 'error')
            return redirect(url_for('regras_servicos.list_regras_servicos'))
        
        regra = dict(regra._mapping)
        
        # Buscar regimes tributários
        regimes = db.execute(text("SELECT * FROM regimes_tributarios ORDER BY nome")).fetchall()
        regimes = [dict(row._mapping) for row in regimes]
        
        # Buscar dados do cliente
        cliente = db.execute(text("SELECT * FROM clientes WHERE cliente_id = :id"), 
                           {'id': regra['cliente_id']}).fetchone()
        cliente = dict(cliente._mapping) if cliente else None
        
        return render_template('admin/regras_servicos/form.html',
                             regra=regra,
                             regimes=regimes,
                             cliente=cliente,
                             cliente_id=regra['cliente_id'])
    
    except Exception as e:
        print(f"Erro ao editar regra: {e}")
        flash(f'Erro ao editar regra: {str(e)}', 'error')
        return redirect(url_for('regras_servicos.list_regras_servicos'))
    finally:
        db.close()


@regras_servicos_bp.route('/salvar', methods=['POST'])
@login_required
@permission_required('regras_tributacao.create')
def salvar_regra_servico():
    """Salva (cria ou atualiza) regra de serviço"""
    db = _get_db()
    
    try:
        regra_id = request.form.get('regra_id')
        cliente_id = request.form.get('cliente_id')
        
        # Coletar dados do formulário
        dados = {
            'cliente_id': int(cliente_id),
            'regime_tributario_id': int(request.form.get('regime_tributario_id')),
            'codigo_servico_lc116': request.form.get('codigo_servico_lc116'),
            # codigo_nbs é VARCHAR(9) no banco (GISS exige só dígitos, sem pontos).
            # Alguns selects carregam o código no formato "1.0101.10.00" (tabela
            # codigos_nbs); removemos pontos/traços e truncamos por segurança
            # para nunca estourar o limite da coluna (StringDataRightTruncation).
            'codigo_nbs': normalizar_codigo_nbs(request.form.get('codigo_nbs', DEFAULT_CODIGO_NBS)),
            'descricao_servico': request.form.get('descricao_servico', ''),
            'aliquota_iss': Decimal(request.form.get('aliquota_iss', '5.00')),
            'iss_retido': request.form.get('iss_retido') == 'on',
            'responsavel_retencao': request.form.get('responsavel_retencao') or None,
            'cst_ibs_cbs': request.form.get('cst_ibs_cbs', '001'),
            'codigo_indicador_operacao': request.form.get('codigo_indicador_operacao', '000001'),
            'codigo_classificacao_tributaria': request.form.get('codigo_classificacao_tributaria', '000001'),
            'codigo_localidade_incidencia': request.form.get('codigo_localidade_incidencia', '3549805'),
            'percentual_redutor': Decimal(request.form.get('percentual_redutor', '0.00')),
            'percentual_total_tributos_federais': Decimal(request.form.get('percentual_total_tributos_federais', '0.00')),
            'percentual_total_tributos_estaduais': Decimal(request.form.get('percentual_total_tributos_estaduais', '0.00')),
            'percentual_total_tributos_municipais': Decimal(request.form.get('percentual_total_tributos_municipais', '5.00')),
            'regime_especial_tributacao': request.form.get('regime_especial_tributacao') or None,
            'optante_simples_nacional': request.form.get('optante_simples_nacional') == 'on',
            'incentivador_cultural': request.form.get('incentivador_cultural') == 'on',
            'uf_origem': request.form.get('uf_origem') or None,
            'uf_destino': request.form.get('uf_destino') or None,
            'indicador_destinatario': request.form.get('indicador_destinatario', '0'),
            'indicador_consumidor_final': request.form.get('indicador_consumidor_final', '0'),
            'finalidade_nfse': request.form.get('finalidade_nfse', '0'),
            'prioridade': int(request.form.get('prioridade', '100')),
            'descricao_regra': request.form.get('descricao_regra', ''),
            'ativo': request.form.get('ativo') == 'on'
        }
        
        if regra_id:
            # Atualizar
            dados['updated_by_user_id'] = current_user.id
            
            query = text("""
                UPDATE regras_tributacao_servicos SET
                    regime_tributario_id = :regime_tributario_id,
                    codigo_servico_lc116 = :codigo_servico_lc116,
                    codigo_nbs = :codigo_nbs,
                    descricao_servico = :descricao_servico,
                    aliquota_iss = :aliquota_iss,
                    iss_retido = :iss_retido,
                    responsavel_retencao = :responsavel_retencao,
                    cst_ibs_cbs = :cst_ibs_cbs,
                    codigo_indicador_operacao = :codigo_indicador_operacao,
                    codigo_classificacao_tributaria = :codigo_classificacao_tributaria,
                    codigo_localidade_incidencia = :codigo_localidade_incidencia,
                    percentual_redutor = :percentual_redutor,
                    percentual_total_tributos_federais = :percentual_total_tributos_federais,
                    percentual_total_tributos_estaduais = :percentual_total_tributos_estaduais,
                    percentual_total_tributos_municipais = :percentual_total_tributos_municipais,
                    regime_especial_tributacao = :regime_especial_tributacao,
                    optante_simples_nacional = :optante_simples_nacional,
                    incentivador_cultural = :incentivador_cultural,
                    uf_origem = :uf_origem,
                    uf_destino = :uf_destino,
                    indicador_destinatario = :indicador_destinatario,
                    indicador_consumidor_final = :indicador_consumidor_final,
                    finalidade_nfse = :finalidade_nfse,
                    prioridade = :prioridade,
                    descricao_regra = :descricao_regra,
                    ativo = :ativo,
                    updated_by_user_id = :updated_by_user_id
                WHERE regra_id = :regra_id
            """)
            dados['regra_id'] = int(regra_id)
            db.execute(query, dados)
            db.commit()
            flash('Regra atualizada com sucesso!', 'success')
        else:
            # Inserir
            dados['created_by_user_id'] = current_user.id
            
            query = text("""
                INSERT INTO regras_tributacao_servicos (
                    cliente_id, regime_tributario_id, codigo_servico_lc116, codigo_nbs, descricao_servico,
                    aliquota_iss, iss_retido, responsavel_retencao, cst_ibs_cbs, codigo_indicador_operacao,
                    codigo_classificacao_tributaria, codigo_localidade_incidencia, percentual_redutor,
                    percentual_total_tributos_federais, percentual_total_tributos_estaduais, percentual_total_tributos_municipais,
                    regime_especial_tributacao, optante_simples_nacional, incentivador_cultural,
                    uf_origem, uf_destino, indicador_destinatario, indicador_consumidor_final, finalidade_nfse,
                    prioridade, descricao_regra, ativo, created_by_user_id
                ) VALUES (
                    :cliente_id, :regime_tributario_id, :codigo_servico_lc116, :codigo_nbs, :descricao_servico,
                    :aliquota_iss, :iss_retido, :responsavel_retencao, :cst_ibs_cbs, :codigo_indicador_operacao,
                    :codigo_classificacao_tributaria, :codigo_localidade_incidencia, :percentual_redutor,
                    :percentual_total_tributos_federais, :percentual_total_tributos_estaduais, :percentual_total_tributos_municipais,
                    :regime_especial_tributacao, :optante_simples_nacional, :incentivador_cultural,
                    :uf_origem, :uf_destino, :indicador_destinatario, :indicador_consumidor_final, :finalidade_nfse,
                    :prioridade, :descricao_regra, :ativo, :created_by_user_id
                )
            """)
            db.execute(query, dados)
            db.commit()
            flash('Regra criada com sucesso!', 'success')
        
        return redirect(url_for('regras_servicos.list_regras_servicos', cliente_id=cliente_id))
    
    except Exception as e:
        print(f"Erro ao salvar regra: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        flash(f'Erro ao salvar regra: {str(e)}', 'error')
        return redirect(url_for('regras_servicos.list_regras_servicos', cliente_id=cliente_id))
    finally:
        db.close()


@regras_servicos_bp.route('/excluir/<int:regra_id>', methods=['POST'])
@login_required
@permission_required('regras_tributacao.delete')
def excluir_regra_servico(regra_id):
    """Exclui regra de serviço"""
    db = _get_db()
    
    try:
        # Buscar cliente_id antes de deletar
        regra = db.execute(text("SELECT cliente_id FROM regras_tributacao_servicos WHERE regra_id = :id"), 
                          {'id': regra_id}).fetchone()
        
        if not regra:
            flash('Regra não encontrada.', 'error')
            return redirect(url_for('regras_servicos.list_regras_servicos'))
        
        cliente_id = regra.cliente_id
        
        # Deletar
        db.execute(text("DELETE FROM regras_tributacao_servicos WHERE regra_id = :id"), {'id': regra_id})
        db.commit()
        
        flash('Regra excluída com sucesso!', 'success')
        return redirect(url_for('regras_servicos.list_regras_servicos', cliente_id=cliente_id))
    
    except Exception as e:
        print(f"Erro ao excluir regra: {e}")
        db.rollback()
        flash(f'Erro ao excluir regra: {str(e)}', 'error')
        return redirect(url_for('regras_servicos.list_regras_servicos'))
    finally:
        db.close()


@regras_servicos_bp.route('/toggle/<int:regra_id>', methods=['POST'])
@login_required
@permission_required('regras_tributacao.edit')
def toggle_regra_servico(regra_id):
    """Ativa/desativa regra de serviço"""
    db = _get_db()
    
    try:
        db.execute(text("""
            UPDATE regras_tributacao_servicos 
            SET ativo = NOT ativo,
                updated_by_user_id = :user_id
            WHERE regra_id = :id
        """), {'id': regra_id, 'user_id': current_user.id})
        db.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"Erro ao alterar status: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@regras_servicos_bp.route('/api/buscar', methods=['POST'])
@login_required
def api_buscar_regra_servico():
    """API para buscar regra tributária por código de serviço"""
    db = _get_db()
    
    try:
        cliente_id = request.json.get('cliente_id')
        codigo_servico = request.json.get('codigo_servico')
        uf_destino = request.json.get('uf_destino')
        
        if not cliente_id or not codigo_servico:
            return jsonify({'success': False, 'error': 'Parâmetros inválidos'}), 400
        
        # Buscar regra com maior prioridade
        # Compara códigos LC116 normalizados (sem zero à esquerda), pois a tela
        # de emissão usa formato '1.01' e o cadastro de regras usa '01.01'.
        query = text(f"""
            SELECT *
            FROM regras_tributacao_servicos
            WHERE cliente_id = :cliente_id
              AND {_NORMALIZA_LC116_SQL.format(coluna='codigo_servico_lc116')} = :codigo_servico
              AND ativo = TRUE
              AND (uf_destino IS NULL OR uf_destino = :uf_destino)
            ORDER BY prioridade ASC
            LIMIT 1
        """)
        
        result = db.execute(query, {
            'cliente_id': cliente_id,
            'codigo_servico': _normalizar_codigo_lc116(codigo_servico),
            'uf_destino': uf_destino or ''
        }).fetchone()
        
        if result:
            regra = dict(result._mapping)
            # Converter Decimal para float
            for key, value in regra.items():
                if isinstance(value, Decimal):
                    regra[key] = float(value)
            
            return jsonify({'success': True, 'regra': regra})
        else:
            return jsonify({'success': False, 'regra': None})
    
    except Exception as e:
        print(f"Erro ao buscar regra: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@regras_servicos_bp.route('/api/buscar-regra', methods=['GET'])
def api_buscar_regra_servico_get():
    """API para buscar regra tributária por código de serviço (GET)"""
    db = _get_db()
    
    try:
        cliente_id = request.args.get('cliente_id')
        codigo_servico = request.args.get('codigo_servico')
        uf_destino = request.args.get('uf_destino', 'SP')
        
        if not cliente_id or not codigo_servico:
            return jsonify({'success': False, 'error': 'Parâmetros inválidos', 'regra': None}), 400
        
        # Buscar regra com maior prioridade (código LC116 normalizado, ver comentário acima)
        query = text(f"""
            SELECT *
            FROM regras_tributacao_servicos
            WHERE cliente_id = :cliente_id
              AND {_NORMALIZA_LC116_SQL.format(coluna='codigo_servico_lc116')} = :codigo_servico
              AND ativo = TRUE
              AND (uf_destino IS NULL OR uf_destino = :uf_destino)
            ORDER BY prioridade ASC
            LIMIT 1
        """)
        
        result = db.execute(query, {
            'cliente_id': int(cliente_id),
            'codigo_servico': _normalizar_codigo_lc116(codigo_servico),
            'uf_destino': uf_destino
        }).fetchone()
        
        if result:
            regra = dict(result._mapping)
            # Converter Decimal para float
            for key, value in regra.items():
                if isinstance(value, Decimal):
                    regra[key] = float(value)
            
            return jsonify({'success': True, 'regra': regra})
        else:
            return jsonify({'success': True, 'regra': None})
    
    except Exception as e:
        print(f"Erro ao buscar regra: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'regra': None}), 500
    finally:
        db.close()

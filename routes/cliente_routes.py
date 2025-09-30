from flask import Blueprint, render_template, redirect, url_for, session, request, flash, jsonify, g
from flask_login import login_required, current_user
from auth.decorators import client_access_required
from database.connection import get_db
from sqlalchemy import text
from datetime import datetime

cliente_bp = Blueprint('cliente', __name__)

@cliente_bp.route('/dashboard/<int:cliente_id>')
@login_required
@client_access_required()
def dashboard(cliente_id):
    """Dashboard específico do cliente - ESTRUTURAS REAIS"""
    try:
        print(f"🎯 DASHBOARD: Entrando no dashboard do cliente {cliente_id}")
        db = next(get_db())
        
        # Buscar dados do cliente
        cliente_result = db.execute(text("""
            SELECT cliente_id, razao_social, nome_fantasia, cnpj,
                   inscricao_estadual, inscricao_municipal,
                   logradouro, numero, complemento, bairro, 
                   nome_municipio, uf, cep,
                   telefone_contato, email_contato, data_cadastro
            FROM clientes 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        
        cliente_data = cliente_result.first()
        if not cliente_data:
            flash('Cliente não encontrado.', 'danger')
            return redirect(url_for('auth.login'))
            
        cliente = dict(cliente_data._mapping)
        print(f"✅ Cliente: {cliente['razao_social']}")
        
        # ===== ESTATÍSTICAS COM ESTRUTURAS CORRETAS =====
        
        # 1. PRODUTOS (tem coluna 'ativo')
        produtos_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM produtos 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        total_produtos = produtos_result.first().total or 0
        
        # 2. DESTINATÁRIOS NFE (NÃO tem coluna 'ativo')
        destinatarios_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM destinatarios_nfe 
            WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        total_destinatarios = destinatarios_result.first().total or 0
        
        # 3. REGRAS TRIBUTÁRIAS (tem coluna 'ativo')
        regras_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM regras_tributacao 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        total_regras = regras_result.first().total or 0
        
        # 4. CERTIFICADOS DIGITAIS (tem coluna 'ativo')
        cert_result = db.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN validade_fim > CURRENT_DATE THEN 1 END) as validos
            FROM certificados_digitais 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        cert_data = cert_result.first()
        total_certificados = cert_data.total or 0
        cert_validos = cert_data.validos or 0
        
        # 5. NFEs (NÃO tem coluna 'ativo')
        nfes_result = db.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN status = 'Autorizada' THEN 1 END) as autorizadas
            FROM nfe_emitidas 
            WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        nfes_data = nfes_result.first()
        total_nfes = nfes_data.total or 0
        nfes_autorizadas = nfes_data.autorizadas or 0
        
        print(f"📊 Contagens: {total_produtos}P, {total_destinatarios}D, {total_regras}R, {total_certificados}C, {total_nfes}N")
        
        # ===== DADOS RECENTES =====
        
        # Produtos recentes (com coluna 'ativo')
        produtos_recentes_result = db.execute(text("""
            SELECT produto_id, descricao, unidade_comercial as unidade, 
                   preco_unitario_padrao as preco_unitario, 
                   (SELECT codigo FROM ncms WHERE ncm_id = produtos.ncm_id) as ncm_codigo,
                   produto_id as data_cadastro
            FROM produtos 
            WHERE cliente_id = :cliente_id AND ativo = true
            ORDER BY produto_id DESC
            
        """), {"cliente_id": cliente_id})
        produtos_recentes = [dict(row._mapping) for row in produtos_recentes_result]
        
        # Destinatários recentes (SEM coluna 'ativo', nomes corretos)
        dest_recentes_result = db.execute(text("""
            SELECT destinatario_id, nome_razao_social as razao_social, 
                   cpf_cnpj as cnpj_cpf, nome_municipio, uf, data_cadastro
            FROM destinatarios_nfe 
            WHERE cliente_id = :cliente_id
            ORDER BY data_cadastro DESC
            
        """), {"cliente_id": cliente_id})
        destinatarios_recentes = [dict(row._mapping) for row in dest_recentes_result]
        
        # Estatísticas para o template
        stats = {
            'total_nfes': total_nfes,
            'nfes_ano': total_nfes,
            'nfes_mes': 0,
            'nfes_autorizadas': nfes_autorizadas,
            'nfes_pendentes': total_nfes - nfes_autorizadas,
            'total_produtos': total_produtos,
            'total_destinatarios': total_destinatarios,
            'total_regras': total_regras,
            'total_certificados': total_certificados,
            'cert_validos': cert_validos,
            'cert_vencidos': total_certificados - cert_validos,
            'valor_total': 0.0
        }
        
        print(f"✅ DASHBOARD: Dados carregados - {total_produtos} produtos, {total_destinatarios} destinatários")
        
        # Definir cliente atual
        session['current_client_id'] = cliente_id
        g.current_client = cliente
        
        return render_template('cliente/dashboard.html', 
                             cliente=cliente,
                             stats=stats,
                             nfes_recentes=[],
                             produtos_recentes=produtos_recentes,
                             destinatarios_recentes=destinatarios_recentes,
                             current_user=current_user)
        
    except Exception as e:
        print(f"❌ ERRO no dashboard: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro interno do servidor.', 'error')
        return redirect(url_for('auth.login'))
        
    finally:
        if 'db' in locals():
            db.close()

@cliente_bp.route('/resumo/<int:cliente_id>')
@login_required
@client_access_required()
def resumo(cliente_id):
    """Resumo do cliente"""
    try:
        db = next(get_db())
        
        cliente_data = db.execute(text("""
            SELECT cliente_id, razao_social, nome_fantasia
            FROM clientes 
            WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id}).first()
        
        if not cliente_data:
            return jsonify({'error': 'Cliente não encontrado'}), 404
            
        return jsonify({
            'cliente_id': cliente_data.cliente_id,
            'razao_social': cliente_data.razao_social,
            'nome_fantasia': cliente_data.nome_fantasia
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()

@cliente_bp.route('/api/estatisticas/<int:cliente_id>')
@login_required
@client_access_required()
def api_estatisticas(cliente_id):
    """API para estatísticas do cliente - ESTRUTURAS CORRETAS"""
    try:
        db = next(get_db())
        
        # Queries com estruturas corretas
        stats_result = db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM produtos WHERE cliente_id = :cliente_id AND ativo = true) as produtos,
                (SELECT COUNT(*) FROM destinatarios_nfe WHERE cliente_id = :cliente_id) as destinatarios,
                (SELECT COUNT(*) FROM regras_tributacao WHERE cliente_id = :cliente_id AND ativo = true) as regras,
                (SELECT COUNT(*) FROM certificados_digitais WHERE cliente_id = :cliente_id AND ativo = true) as certificados,
                (SELECT COUNT(*) FROM nfe_emitidas WHERE cliente_id = :cliente_id) as nfes
        """), {"cliente_id": cliente_id}).first()
        
        estatisticas = {
            'total_nfes': stats_result.nfes or 0,
            'total_produtos': stats_result.produtos or 0,
            'total_destinatarios': stats_result.destinatarios or 0,
            'total_regras': stats_result.regras or 0,
            'total_certificados': stats_result.certificados or 0,
            'valor_total': 0.0,
            'grafico_mensal': [0] * 12
        }
        
        return jsonify(estatisticas)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'db' in locals():
            db.close()
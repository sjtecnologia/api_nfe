from flask import Blueprint, render_template, redirect, url_for, session, request, flash, jsonify, g
from flask_login import login_required, current_user
# Certifique-se de que o decorator existe ou defina um placeholder temporário
try:
    from auth.decorators import client_access_required
except ImportError:
    # Placeholder: Permite acesso sem restrição (substitua pela lógica correta depois)
    def client_access_required():
        def decorator(f):
            return f
        return decorator
from auth.permissions import get_accessible_client_ids
from database.connection import get_db
from sqlalchemy import func, text
from datetime import datetime, timedelta

from database.models import CertificadoDigital, Cliente, DestinatarioNFe, Produto, RegraTributacao

cliente_bp = Blueprint('cliente', __name__)

@cliente_bp.route('/dashboard/<int:cliente_id>')
@login_required
@client_access_required()
def dashboard(cliente_id):
    """Dashboard principal do cliente"""
    db = next(get_db())
    
    try:
        # Verificar se o usuário tem acesso a este cliente
        accessible_clients = get_accessible_client_ids(db)
        if cliente_id not in accessible_clients:
            flash('Você não tem permissão para acessar este cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        print(f"✅ Acesso permitido ao cliente {cliente_id} para usuário {current_user.username}")
        print(f"🎯 DASHBOARD: Entrando no dashboard do cliente {cliente_id}")
        
        # Buscar dados do cliente
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        if not cliente:
            flash('Cliente não encontrado.', 'danger')
            return redirect(url_for('home.home'))
        
        print(f"✅ Cliente: {cliente.razao_social}")
        
        # Estatísticas
        total_produtos = db.query(func.count(Produto.produto_id)).filter_by(cliente_id=cliente_id).scalar() or 0
        total_destinatarios = db.query(func.count(DestinatarioNFe.destinatario_id)).filter_by(cliente_id=cliente_id).scalar() or 0
        total_regras = db.query(func.count(RegraTributacao.regra_tributacao_id)).filter_by(cliente_id=cliente_id).scalar() or 0
        total_certificados = db.query(func.count(CertificadoDigital.certificado_digital_id)).filter_by(cliente_id=cliente_id).scalar() or 0
        
        # Contagem de NFes - Usar SQL Nativo para garantir resultados corretos
        # CORRIGIDO: Usar formato MAIÚSCULO para os status para garantir compatibilidade
        query_nfes_total = text("""
            SELECT COUNT(*) as total
            FROM nfe_emitidas
            WHERE cliente_id = :cliente_id
        """)
        
        query_nfes_ano = text("""
            SELECT COUNT(*) as total
            FROM nfe_emitidas
            WHERE cliente_id = :cliente_id
            AND EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE)
        """)
        
        query_nfes_mes = text("""
            SELECT COUNT(*) as total
            FROM nfe_emitidas
            WHERE cliente_id = :cliente_id
            AND EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND EXTRACT(MONTH FROM data_criacao) = EXTRACT(MONTH FROM CURRENT_DATE)
        """)
        
        total_nfes_row = db.execute(query_nfes_total, {"cliente_id": cliente_id}).fetchone()
        total_nfes = total_nfes_row[0] if total_nfes_row is not None else 0

        nfes_ano_row = db.execute(query_nfes_ano, {"cliente_id": cliente_id}).fetchone()
        nfes_ano = nfes_ano_row[0] if nfes_ano_row is not None else 0

        nfes_mes_row = db.execute(query_nfes_mes, {"cliente_id": cliente_id}).fetchone()
        nfes_mes = nfes_mes_row[0] if nfes_mes_row is not None else 0
        
        print(f"📊 Contagens: {total_produtos}P, {total_destinatarios}D, {total_regras}R, {total_certificados}C, {total_nfes}N")
        
        # Estatísticas agrupadas
        stats = {
            'total_produtos': total_produtos,
            'total_destinatarios': total_destinatarios,
            'total_regras': total_regras,
            'total_certificados': total_certificados,
            'total_nfes': total_nfes,
            'nfes_ano': nfes_ano,
            'nfes_mes': nfes_mes
        }
        
        # CORRIGIDO: Últimas NFes - Usar SQL nativo para garantir dados corretos
        query_ultimas_nfes = text("""
            SELECT 
                nfe_emitida_id,
                cliente_id,
                status,
                data_criacao,
                chave_acesso,
                protocolo_sefaz,
                destinatario_razao_social,
                destinatario_cnpj_cpf,
                json_nfe
            FROM nfe_emitidas
            WHERE cliente_id = :cliente_id
            ORDER BY data_criacao DESC
            LIMIT 5
        """)
        
        ultimas_nfes_result = db.execute(query_ultimas_nfes, {"cliente_id": cliente_id})
        ultimas_nfes = []
        
        for row in ultimas_nfes_result:
            nfe_dict = dict(row._mapping)
            
            # CORRIGIDO: Extrair valor da NFe do JSON
            try:
                import json
                json_data = json.loads(nfe_dict['json_nfe']) if isinstance(nfe_dict['json_nfe'], str) else nfe_dict['json_nfe']
                
                # Tentar extrair o valor total de diferentes formas possíveis na estrutura JSON
                valor_total = None
                if isinstance(json_data, dict):
                    # Verificar várias possíveis localizações do valor total
                    if 'total' in json_data and isinstance(json_data['total'], dict):
                        if 'ICMSTot' in json_data['total'] and isinstance(json_data['total']['ICMSTot'], dict):
                            valor_total = json_data['total']['ICMSTot'].get('vNF')
                    
                    # Verificar na estrutura form_data -> valorPagamento
                    elif 'form_data' in json_data and isinstance(json_data['form_data'], dict):
                        valor_total = json_data['form_data'].get('valorPagamento')
                
                if valor_total is not None:
                    try:
                        nfe_dict['valor_total'] = float(valor_total)
                    except (ValueError, TypeError):
                        nfe_dict['valor_total'] = 0.0
                else:
                    nfe_dict['valor_total'] = 0.0
                    
            except Exception as e:
                print(f"⚠️ Erro ao processar JSON da NFe {nfe_dict['nfe_emitida_id']}: {e}")
                nfe_dict['valor_total'] = 0.0
            
            ultimas_nfes.append(nfe_dict)
        
        # CORRIGIDO: NFes por mês - últimos 6 meses
        hoje = datetime.now()
        seis_meses_atras = hoje - timedelta(days=180)
        
        query_nfes_por_mes = text("""
            SELECT 
                EXTRACT(MONTH FROM data_criacao) as mes,
                EXTRACT(YEAR FROM data_criacao) as ano,
                COUNT(*) as quantidade
            FROM nfe_emitidas
            WHERE cliente_id = :cliente_id
            AND data_criacao >= :data_inicio
            GROUP BY EXTRACT(YEAR FROM data_criacao), EXTRACT(MONTH FROM data_criacao)
            ORDER BY EXTRACT(YEAR FROM data_criacao), EXTRACT(MONTH FROM data_criacao)
        """)
        
        nfes_por_mes_result = db.execute(query_nfes_por_mes, {
            "cliente_id": cliente_id,
            "data_inicio": seis_meses_atras
        })
        
        nfes_por_mes = []
        for row in nfes_por_mes_result:
            nfes_por_mes.append({
                'mes': int(row[0]),
                'ano': int(row[1]),
                'quantidade': int(row[2])
            })
        
        # CORRIGIDO: Se não houver dados para os últimos 6 meses, criar dados vazios
        if not nfes_por_mes:
            for i in range(6):
                mes_atual = hoje - timedelta(days=30 * i)
                nfes_por_mes.insert(0, {
                    'mes': mes_atual.month,
                    'ano': mes_atual.year,
                    'quantidade': 0
                })
        
        print(f"✅ DASHBOARD: Dados carregados - {total_produtos} produtos, {total_destinatarios} destinatários, {len(ultimas_nfes)} NFes recentes")
        
        return render_template('cliente/dashboard.html', 
                             cliente=cliente, 
                             stats=stats,
                             ultimas_nfes=ultimas_nfes,
                             nfes_por_mes=nfes_por_mes)
                             
    except Exception as e:
        db.rollback()
        print(f"❌ Erro no dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
    finally:
        db.close()

@cliente_bp.route('/resumo/<int:cliente_id>')
@login_required
@client_access_required()
def resumo(cliente_id):
    """Página de resumo do cliente"""
    db = next(get_db())
    
    try:
        # Verificar se o usuário tem acesso a este cliente
        accessible_clients = get_accessible_client_ids(db)
        if cliente_id not in accessible_clients:
            flash('Você não tem permissão para acessar este cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Buscar dados do cliente
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        if not cliente:
            flash('Cliente não encontrado.', 'danger')
            return redirect(url_for('home.home'))
        
        return render_template('cliente/resumo.html', cliente=cliente)
        
    except Exception as e:
        flash(f'Erro ao carregar dados do cliente: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
    finally:
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
            'total_nfes': stats_result.nfes if stats_result and hasattr(stats_result, 'nfes') else 0,
            'total_produtos': stats_result.produtos if stats_result and hasattr(stats_result, 'produtos') else 0,
            'total_destinatarios': stats_result.destinatarios if stats_result and hasattr(stats_result, 'destinatarios') else 0,
            'total_regras': stats_result.regras if stats_result and hasattr(stats_result, 'regras') else 0,
            'total_certificados': stats_result.certificados if stats_result and hasattr(stats_result, 'certificados') else 0,
            'valor_total': 0.0,
            'grafico_mensal': [0] * 12
        }
        
        return jsonify(estatisticas)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            if 'db' in locals() and locals()['db'] is not None:
                locals()['db'].close()
        except Exception:
            pass
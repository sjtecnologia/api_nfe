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
        print(f"\n{'='*80}")
        print(f"[?] DASHBOARD: Acessando dashboard do cliente {cliente_id}")
        print(f"[USER] Usuário: {current_user.username}")
        print(f"{'='*80}")
        
        # Verificar se o usuário tem acesso a este cliente
        accessible_clients = get_accessible_client_ids(db)
        print(f"[LIST] Clientes acessíveis: {accessible_clients}")
        
        if cliente_id not in accessible_clients:
            print(f"[X] Acesso negado ao cliente {cliente_id}")
            flash('Você não tem permissão para acessar este cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        print(f"[OK] Acesso permitido ao cliente {cliente_id} para usuário {current_user.username}")
        print(f"[?] DASHBOARD: Entrando no dashboard do cliente {cliente_id}")
        
        # Buscar dados do cliente
        print("[LOG] Buscando dados do cliente...")
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        if not cliente:
            print(f"[X] Cliente {cliente_id} não encontrado no banco")
            flash('Cliente não encontrado.', 'danger')
            return redirect(url_for('home.home'))
        
        print(f"[OK] Cliente: {cliente.razao_social}")
        
        # Estatísticas
        print("[DATA] Calculando estatísticas...")
        total_produtos = db.query(func.count(Produto.produto_id)).filter_by(cliente_id=cliente_id).scalar() or 0
        print(f"  Produtos: {total_produtos}")
        
        total_destinatarios = db.query(func.count(DestinatarioNFe.destinatario_id)).filter_by(cliente_id=cliente_id).scalar() or 0
        print(f"  Destinatários: {total_destinatarios}")
        
        total_regras = db.query(func.count(RegraTributacao.regra_tributacao_id)).filter_by(cliente_id=cliente_id).scalar() or 0
        print(f"  Regras: {total_regras}")
        
        total_certificados = db.query(func.count(CertificadoDigital.certificado_digital_id)).filter_by(cliente_id=cliente_id).scalar() or 0
        print(f"  Certificados: {total_certificados}")
        
        # Contagem de NFes - Usar SQL Nativo para garantir resultados corretos
        print("[DATA] Contando NFes...")
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
        print(f"  Total NFes: {total_nfes}")

        nfes_ano_row = db.execute(query_nfes_ano, {"cliente_id": cliente_id}).fetchone()
        nfes_ano = nfes_ano_row[0] if nfes_ano_row is not None else 0
        print(f"  NFes no ano: {nfes_ano}")

        nfes_mes_row = db.execute(query_nfes_mes, {"cliente_id": cliente_id}).fetchone()
        nfes_mes = nfes_mes_row[0] if nfes_mes_row is not None else 0
        print(f"  NFes no mês: {nfes_mes}")
        
        print(f"[DATA] Contagens: {total_produtos}P, {total_destinatarios}D, {total_regras}R, {total_certificados}C, {total_nfes}N")
        
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
                mensagem_sefaz,
                destinatario_razao_social,
                destinatario_cnpj_cpf,
                tipo_nfe,
                valor_total,
                json_nfe
            FROM nfe_emitidas
            WHERE cliente_id = :cliente_id
            ORDER BY data_criacao DESC
            LIMIT 3
        """)
        
        ultimas_nfes_result = db.execute(query_ultimas_nfes, {"cliente_id": cliente_id})
        ultimas_nfes = []
        
        print(f"[DATA] Processando últimas NFes...")
        for row in ultimas_nfes_result:
            try:
                nfe_dict = dict(row._mapping)
                print(f"  NFe ID {nfe_dict.get('nfe_emitida_id')}: Status={nfe_dict.get('status')}, Data={nfe_dict.get('data_criacao')}")
                
                # CORRIGIDO: Usar valor_total do banco ou extrair do JSON como fallback
                try:
                    # Primeiro tentar usar o valor_total do banco de dados
                    if nfe_dict.get('valor_total') is not None:
                        try:
                            nfe_dict['valor_total'] = float(nfe_dict['valor_total'])
                            print(f"    [OK] Valor total do banco: R$ {nfe_dict['valor_total']:.2f}")
                        except (ValueError, TypeError):
                            print(f"    [!] Erro ao converter valor do banco: {nfe_dict['valor_total']}")
                            nfe_dict['valor_total'] = 0.0
                    # Se não tiver no banco, tentar extrair do JSON
                    elif nfe_dict.get('json_nfe') is not None:
                        import json
                        json_data = json.loads(nfe_dict['json_nfe']) if isinstance(nfe_dict['json_nfe'], str) else nfe_dict['json_nfe']
                        
                        # Tentar extrair o valor total de diferentes formas possíveis na estrutura JSON
                        valor_total = None
                        if isinstance(json_data, dict):
                            # 1. NFCe: Verificar em totais -> valor_total
                            if 'totais' in json_data and isinstance(json_data['totais'], dict):
                                valor_total = json_data['totais'].get('valor_total')
                            # 2. NFe: Verificar várias possíveis localizações do valor total
                            elif 'total' in json_data and isinstance(json_data['total'], dict):
                                if 'ICMSTot' in json_data['total'] and isinstance(json_data['total']['ICMSTot'], dict):
                                    valor_total = json_data['total']['ICMSTot'].get('vNF')
                            # 3. Verificar na estrutura form_data -> valorPagamento
                            elif 'form_data' in json_data and isinstance(json_data['form_data'], dict):
                                valor_total = json_data['form_data'].get('valorPagamento')
                        
                        if valor_total is not None:
                            try:
                                nfe_dict['valor_total'] = float(valor_total)
                                print(f"    [OK] Valor total do JSON: R$ {nfe_dict['valor_total']:.2f}")
                            except (ValueError, TypeError):
                                print(f"    [!] Erro ao converter valor do JSON: {valor_total}")
                                nfe_dict['valor_total'] = 0.0
                        else:
                            print(f"    [!] Valor total não encontrado no JSON")
                            nfe_dict['valor_total'] = 0.0
                    else:
                        print(f"    [!] Nem valor_total nem json_nfe disponíveis")
                        nfe_dict['valor_total'] = 0.0
                        
                except Exception as e:
                    print(f"    [X] Erro ao processar valor da NFe {nfe_dict.get('nfe_emitida_id')}: {e}")
                    import traceback
                    traceback.print_exc()
                    nfe_dict['valor_total'] = 0.0
                
                ultimas_nfes.append(nfe_dict)
                
            except Exception as e:
                print(f"  [X] Erro ao processar linha da NFe: {e}")
                import traceback
                traceback.print_exc()
                # Continuar com a próxima NFe
                continue
        
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
        
        print(f"[OK] DASHBOARD: Dados carregados - {total_produtos} produtos, {total_destinatarios} destinatários, {len(ultimas_nfes)} NFes recentes")
        
        return render_template('cliente/dashboard.html', 
                             cliente=cliente, 
                             stats=stats,
                             ultimas_nfes=ultimas_nfes,
                             nfes_por_mes=nfes_por_mes)
                             
    except Exception as e:
        db.rollback()
        print(f"[X] Erro no dashboard: {str(e)}")
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

@cliente_bp.route('/selecionar-cliente')
@login_required
def selecionar_cliente():
    db = next(get_db())
    try:
        clientes_result = db.execute(text("""
            SELECT c.cliente_id, c.razao_social
            FROM user_clients uc
            JOIN clientes c ON c.cliente_id = uc.client_id
            WHERE uc.user_id = :user_id AND c.ativo = true
        """), {"user_id": current_user.id})
        clientes_do_usuario = [dict(row._mapping) for row in clientes_result]
        return render_template('cliente/selecionar_cliente.html', clientes_do_usuario=clientes_do_usuario)
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

@cliente_bp.route('/api/nfes_por_mes/<int:cliente_id>')
@login_required
@client_access_required()
def api_nfes_por_mes(cliente_id):
    """API para dados do gráfico de NFes por mês"""
    try:
        db = next(get_db())
        
        # Pegar período do query string (padrão: 6 meses)
        periodo = request.args.get('periodo', '6')
        
        # Calcular data de início baseado no período
        hoje = datetime.now()
        
        if periodo == 'ano_atual':
            data_inicio = datetime(hoje.year, 1, 1)
        elif periodo == 'ano_anterior':
            data_inicio = datetime(hoje.year - 1, 1, 1)
            hoje = datetime(hoje.year - 1, 12, 31)
        elif periodo == '24':
            data_inicio = hoje - timedelta(days=730)
        elif periodo == '12':
            data_inicio = hoje - timedelta(days=365)
        else:  # padrão 6 meses
            data_inicio = hoje - timedelta(days=180)
        
        # Buscar dados agrupados por mês
        query_nfes_por_mes = text("""
            SELECT 
                EXTRACT(MONTH FROM data_criacao)::INTEGER as mes,
                EXTRACT(YEAR FROM data_criacao)::INTEGER as ano,
                COUNT(*)::INTEGER as quantidade
            FROM nfe_emitidas
            WHERE cliente_id = :cliente_id
            AND data_criacao >= :data_inicio
            AND data_criacao <= :data_fim
            GROUP BY EXTRACT(YEAR FROM data_criacao), EXTRACT(MONTH FROM data_criacao)
            ORDER BY ano, mes
        """)
        
        result = db.execute(query_nfes_por_mes, {
            "cliente_id": cliente_id,
            "data_inicio": data_inicio,
            "data_fim": hoje
        })
        
        nfes_por_mes = []
        for row in result:
            nfes_por_mes.append({
                'mes': row[0],
                'ano': row[1],
                'quantidade': row[2]
            })
        
        # Se não houver dados, retornar array vazio
        if not nfes_por_mes:
            # Criar meses vazios para o período
            meses_periodo = []
            meses = int(periodo) if periodo.isdigit() else 6
            
            if periodo == 'ano_atual':
                for m in range(1, hoje.month + 1):
                    meses_periodo.append({'mes': m, 'ano': hoje.year, 'quantidade': 0})
            elif periodo == 'ano_anterior':
                for m in range(1, 13):
                    meses_periodo.append({'mes': m, 'ano': hoje.year - 1, 'quantidade': 0})
            else:
                for i in range(meses):
                    mes_atual = hoje - timedelta(days=30 * i)
                    meses_periodo.insert(0, {
                        'mes': mes_atual.month,
                        'ano': mes_atual.year,
                        'quantidade': 0
                    })
            
            nfes_por_mes = meses_periodo
        
        return jsonify(nfes_por_mes)
        
    except Exception as e:
        print(f"[X] Erro api_nfes_por_mes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            if 'db' in locals() and locals()['db'] is not None:
                locals()['db'].close()
        except Exception:
            pass
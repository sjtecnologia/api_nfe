"""
Rotas para NFS-e Nacional - Nota Fiscal de Serviço Eletrônica
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response, session
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import text
import traceback

# Importar dependências do projeto
from database.connection import get_db
from database.models import Cliente
from services.nfse_service import NFSeService, criar_nfse_de_formulario
from models.nfse_model import (
    NFSeNacional, CODIGOS_SERVICO_LC116, CODIGOS_MUNICIPIO_SP, ALIQUOTAS_ISS_SJRP
)
from auth.decorators import editor_or_admin_required, viewer_or_higher_required
from auth.permissions import get_accessible_client_ids

# Blueprint
nfse_bp = Blueprint('nfse', __name__, url_prefix='/admin/nfse')


def br_to_float(valor_str):
    """Converte valor monetário brasileiro (5.000,00) para float (5000.00)"""
    if not valor_str:
        return 0.0
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    # Remove pontos de milhar e substitui vírgula por ponto
    valor_limpo = str(valor_str).replace('.', '').replace(',', '.')
    try:
        return float(valor_limpo)
    except ValueError:
        return 0.0


@nfse_bp.route('/')
@login_required
@viewer_or_higher_required()
def index():
    """Redireciona para a lista de NFS-e"""
    return redirect(url_for('nfse.list_nfse'))


@nfse_bp.route('/list')
@login_required
@viewer_or_higher_required()
def list_nfse():
    """Lista NFS-e emitidas"""
    db = next(get_db())
    try:
        # Obter clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Determinar cliente_id (mesmo padrão da NFe)
        cliente_id = None
        if request.args.get('cliente_id'):
            try:
                cliente_id_str = request.args.get('cliente_id')
                cliente_id = int(cliente_id_str) if cliente_id_str else None
                if cliente_id and cliente_id not in accessible_clients:
                    flash('Você não tem acesso a este cliente.', 'danger')
                    return redirect(url_for('home.home'))
            except ValueError:
                flash('ID do cliente inválido', 'danger')
                return redirect(url_for('home.home'))
        elif session.get('current_client_id'):
            cliente_id = session.get('current_client_id')
            if cliente_id not in accessible_clients:
                cliente_id = accessible_clients[0]
        else:
            cliente_id = accessible_clients[0]
        
        # Buscar NFS-e do cliente usando SQLAlchemy
        query = text("""
            SELECT n.*, d.nome_razao_social as tomador_nome
            FROM nfse n
            LEFT JOIN destinatarios_nfe d ON n.tomador_id = d.destinatario_id
            WHERE n.cliente_id = :cliente_id
            ORDER BY n.created_at DESC
            LIMIT 100
        """)
        result = db.execute(query, {"cliente_id": cliente_id})
        nfses = result.mappings().all()
        
        return render_template('admin/nfse/list.html', nfses=nfses)
        
    except Exception as e:
        print(f"[NFSE] Erro ao listar: {e}")
        traceback.print_exc()
        flash(f"Erro ao carregar NFS-e: {str(e)}", "danger")
        return render_template('admin/nfse/list.html', nfses=[])
    finally:
        db.close()


@nfse_bp.route('/emitir', methods=['GET'])
@login_required
@editor_or_admin_required()
def emitir_form():
    """Formulário de emissão de NFS-e"""
    db = next(get_db())
    try:
        # Obter clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Determinar cliente_id (mesmo padrão da NFe)
        cliente_id = None
        if request.args.get('cliente_id'):
            try:
                cliente_id_str = request.args.get('cliente_id')
                cliente_id = int(cliente_id_str) if cliente_id_str else None
                if cliente_id and cliente_id not in accessible_clients:
                    flash('Você não tem acesso a este cliente.', 'danger')
                    return redirect(url_for('home.home'))
            except ValueError:
                flash('ID do cliente inválido', 'danger')
                return redirect(url_for('home.home'))
        elif session.get('current_client_id'):
            cliente_id = session.get('current_client_id')
            if cliente_id not in accessible_clients:
                cliente_id = accessible_clients[0]
        else:
            cliente_id = accessible_clients[0]
        
        # Buscar dados do emitente/prestador
        emitente = db.query(Cliente).filter(Cliente.cliente_id == cliente_id).first()
        
        if not emitente:
            flash("Dados do prestador não encontrados", "danger")
            return redirect(url_for('nfse.index'))
        
        # Buscar tomadores (Destinatários/Tomadores do serviço)
        query_tomadores = text("""
            SELECT * FROM destinatarios_nfe 
            WHERE cliente_id = :cliente_id 
            ORDER BY nome_razao_social
        """)
        result = db.execute(query_tomadores, {"cliente_id": cliente_id})
        tomadores = result.mappings().all()
        
        # Buscar próximo número RPS
        query_rps = text("""
            SELECT COALESCE(MAX(numero_rps), 0) + 1 as proximo_rps
            FROM nfse WHERE cliente_id = :cliente_id
        """)
        result_rps = db.execute(query_rps, {"cliente_id": cliente_id})
        row = result_rps.mappings().first()
        proximo_rps = row['proximo_rps'] if row else 1
        
        return render_template(
            'admin/nfse/emitir.html',
            emitente=emitente,
            emitente_data=emitente,
            tomadores=tomadores,
            proximo_rps=proximo_rps,
            codigos_servico=CODIGOS_SERVICO_LC116,
            aliquotas_iss=ALIQUOTAS_ISS_SJRP,
            municipios=CODIGOS_MUNICIPIO_SP
        )
        
    except Exception as e:
        print(f"[NFSE] Erro no formulário: {e}")
        traceback.print_exc()
        flash(f"Erro ao carregar formulário: {str(e)}", "danger")
        return redirect(url_for('nfse.list_nfse'))
    finally:
        db.close()


@nfse_bp.route('/emitir', methods=['POST'])
@login_required
@editor_or_admin_required()
def emitir():
    """Processa emissão de NFS-e"""
    db = next(get_db())
    try:
        # Obter clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Determinar cliente_id (mesmo padrão da NFe)
        cliente_id = None
        if request.form.get('cliente_id'):
            try:
                cliente_id_str = request.form.get('cliente_id')
                cliente_id = int(cliente_id_str) if cliente_id_str else None
                if cliente_id and cliente_id not in accessible_clients:
                    flash('Você não tem acesso a este cliente.', 'danger')
                    return redirect(url_for('home.home'))
            except ValueError:
                flash('ID do cliente inválido', 'danger')
                return redirect(url_for('home.home'))
        elif session.get('current_client_id'):
            cliente_id = session.get('current_client_id')
            if cliente_id not in accessible_clients:
                cliente_id = accessible_clients[0]
        else:
            cliente_id = accessible_clients[0]
        
        # Buscar dados do prestador com regime tributário
        from sqlalchemy.orm import joinedload
        prestador_data = db.query(Cliente).options(
            joinedload(Cliente.regime_tributario)
        ).filter(Cliente.cliente_id == cliente_id).first()
        
        if not prestador_data:
            flash("Dados do prestador não encontrados", "danger")
            return redirect(url_for('nfse.emitir_form'))
        
        # Coletar dados do formulário
        dados = {
            'cliente_id': cliente_id,
            'numero_rps': request.form.get('numero_rps'),
            'serie_rps': request.form.get('serie_rps', '1'),
            'tipo_rps': request.form.get('tipo_rps', '1'),
            'data_competencia': request.form.get('data_competencia'),
            'natureza_operacao': request.form.get('natureza_operacao', '1'),
            'ambiente': request.form.get('ambiente', 'homologacao'),
            
            # Tomadores
            'tomador_cpf_cnpj': request.form.get('tomador_cpf_cnpj', ''),
            'tomador_razao_social': request.form.get('tomador_razao_social', ''),
            'tomador_inscricao_municipal': request.form.get('tomador_inscricao_municipal'),
            'tomador_logradouro': request.form.get('tomador_logradouro', ''),
            'tomador_numero': request.form.get('tomador_numero', ''),
            'tomador_complemento': request.form.get('tomador_complemento', ''),
            'tomador_bairro': request.form.get('tomador_bairro', ''),
            'tomador_codigo_municipio': request.form.get('tomador_codigo_municipio', ''),
            'tomador_uf': request.form.get('tomador_uf', 'SP'),
            'tomador_cep': request.form.get('tomador_cep', ''),
            'tomador_telefone': request.form.get('tomador_telefone', ''),
            'tomador_email': request.form.get('tomador_email', ''),
            
            # Serviço
            'codigo_servico': request.form.get('codigo_servico', '17.01'),
            'codigo_cnae': request.form.get('codigo_cnae'),
            'discriminacao': request.form.get('discriminacao', ''),
            'valor_servico': br_to_float(request.form.get('valor_servico', 0)),
            'valor_deducoes': br_to_float(request.form.get('valor_deducoes', 0)),
            'valor_pis': br_to_float(request.form.get('valor_pis', 0)),
            'valor_cofins': br_to_float(request.form.get('valor_cofins', 0)),
            'valor_inss': br_to_float(request.form.get('valor_inss', 0)),
            'valor_ir': br_to_float(request.form.get('valor_ir', 0)),
            'valor_csll': br_to_float(request.form.get('valor_csll', 0)),
            'outras_retencoes': br_to_float(request.form.get('outras_retencoes', 0)),
            'desconto_incondicionado': br_to_float(request.form.get('desconto_incondicionado', 0)),
            'desconto_condicionado': br_to_float(request.form.get('desconto_condicionado', 0)),
            'aliquota_iss': br_to_float(request.form.get('aliquota_iss', 0)),
            'iss_retido': request.form.get('iss_retido') == 'on',
            'codigo_municipio_prestacao': request.form.get('codigo_municipio_prestacao', '3549805'),
            
            # Campos obrigatórios Reforma Tributária (LC 214/2025)
            'codigo_nbs': request.form.get('codigo_nbs', '101010000'),
            'percentual_total_tributos_federais': br_to_float(request.form.get('percentual_total_tributos_federais', 0)),
            'percentual_total_tributos_estaduais': br_to_float(request.form.get('percentual_total_tributos_estaduais', 0)),
            'percentual_total_tributos_municipais': br_to_float(request.form.get('percentual_total_tributos_municipais', 5)),
            'finalidade_nfse': request.form.get('finalidade_nfse', '0'),
            'indicador_consumidor_final': request.form.get('indicador_consumidor_final', '0'),
            'codigo_indicador_operacao': request.form.get('codigo_indicador_operacao', '000001'),
            'indicador_destinatario': request.form.get('indicador_destinatario', '0'),
            'cst_ibs_cbs': request.form.get('cst_ibs_cbs', '001'),
            'codigo_classificacao_tributaria': request.form.get('codigo_classificacao_tributaria', '000001'),
            'codigo_localidade_incidencia': request.form.get('codigo_localidade_incidencia', '3549805'),
            'percentual_redutor': br_to_float(request.form.get('percentual_redutor', 0)),
            'regime_especial_tributacao': request.form.get('regime_especial_tributacao'),
            # CORREÇÃO: Buscar do regime tributário do cliente (CRT=1 = Simples Nacional)
            # Carrega o relacionamento regime_tributario se ainda não estiver carregado
            'optante_simples_nacional': prestador_data.regime_tributario.crt == 1 if prestador_data.regime_tributario else False,
            'incentivador_cultural': request.form.get('incentivador_cultural') == 'on',
            
            # Informações adicionais
            'informacoes_complementares': request.form.get('informacoes_complementares', '')
        }
        
        # Converter prestador_data para dict
        prestador_dict = {
            'cnpj': prestador_data.cnpj if hasattr(prestador_data, 'cnpj') else '',
            'inscricao_municipal': prestador_data.inscricao_municipal if hasattr(prestador_data, 'inscricao_municipal') else '',
            'razao_social': prestador_data.razao_social if hasattr(prestador_data, 'razao_social') else '',
            'nome_fantasia': prestador_data.nome_fantasia if hasattr(prestador_data, 'nome_fantasia') else '',
            'logradouro': prestador_data.logradouro if hasattr(prestador_data, 'logradouro') else '',
            'numero': prestador_data.numero if hasattr(prestador_data, 'numero') else '',
            'bairro': prestador_data.bairro if hasattr(prestador_data, 'bairro') else '',
            'codigo_municipio': '3549805',  # SJRP
            'uf': prestador_data.uf if hasattr(prestador_data, 'uf') else 'SP',
            'cep': prestador_data.cep if hasattr(prestador_data, 'cep') else '',
            'optante_simples': getattr(prestador_data, 'optante_simples', True)
        }
        
        # Criar objeto NFS-e
        nfse = criar_nfse_de_formulario(dados, prestador_dict)
        
        # Inicializar serviço
        ambiente = dados.get('ambiente', 'homologacao')
        service = NFSeService(ambiente=ambiente)
        
        # Gerar XML do RPS
        xml_rps = service.gerar_xml_rps(nfse)
        
        # Status inicial
        status = '0'  # Pendente
        protocolo = None
        numero_nfse = None
        mensagem_erro = None
        
        # Tentar enviar para o webservice GISS Online
        try:
            print("[NFSE] Tentando enviar para GISS Online (Homologação RTC)...")
            sucesso, resposta = service.enviar_lote_rps(nfse, db_session=db)
            
            if sucesso:
                protocolo = resposta.get('protocolo')
                status = '2'  # Aguardando Processamento
                print(f"[NFSE] ✅ Enviado com sucesso! Protocolo: {protocolo}")
                flash(f"RPS enviado para processamento! Protocolo: {protocolo}", "success")
            else:
                mensagem_erro = resposta.get('mensagem', 'Erro desconhecido')
                print(f"[NFSE] ⚠️ Erro no envio: {mensagem_erro}")
                flash(f"RPS salvo, mas houve erro no envio: {mensagem_erro}", "warning")
                
        except Exception as e:
            print(f"[NFSE] ⚠️ Exceção ao enviar: {e}")
            flash(f"RPS salvo localmente. Erro ao enviar: {str(e)}", "warning")
        
        # Salvar no banco de dados com todos os campos da Reforma Tributária
        insert_query = text("""
            INSERT INTO nfse (
                cliente_id, numero_rps, serie_rps, tipo_rps,
                data_emissao, data_competencia, natureza_operacao,
                tomador_cpf_cnpj, tomador_razao_social, tomador_endereco,
                codigo_servico, discriminacao, valor_servicos,
                aliquota_iss, valor_iss, valor_liquido,
                codigo_nbs, finalidade_nfse, indicador_consumidor_final,
                codigo_indicador_operacao, indicador_destinatario,
                cst_ibs_cbs, codigo_classificacao_tributaria,
                codigo_localidade_incidencia, percentual_redutor,
                percentual_total_tributos_federais,
                percentual_total_tributos_estaduais,
                percentual_total_tributos_municipais,
                regime_especial_tributacao, optante_simples_nacional,
                incentivador_cultural,
                xml_rps, status, ambiente, protocolo, mensagem_retorno, created_at
            ) VALUES (
                :cliente_id, :numero_rps, :serie_rps, :tipo_rps,
                :data_emissao, :data_competencia, :natureza_operacao,
                :tomador_cpf_cnpj, :tomador_razao_social, :tomador_endereco,
                :codigo_servico, :discriminacao, :valor_servicos,
                :aliquota_iss, :valor_iss, :valor_liquido,
                :codigo_nbs, :finalidade_nfse, :indicador_consumidor_final,
                :codigo_indicador_operacao, :indicador_destinatario,
                :cst_ibs_cbs, :codigo_classificacao_tributaria,
                :codigo_localidade_incidencia, :percentual_redutor,
                :percentual_total_tributos_federais,
                :percentual_total_tributos_estaduais,
                :percentual_total_tributos_municipais,
                :regime_especial_tributacao, :optante_simples_nacional,
                :incentivador_cultural,
                :xml_rps, :status, :ambiente, :protocolo, :mensagem_retorno, :created_at
            ) RETURNING id
        """)
        
        # Calcular valores (já convertidos para float)
        valor_servicos = dados.get('valor_servico', 0.0)
        aliquota = dados.get('aliquota_iss', 0.0)
        valor_iss = valor_servicos * (aliquota / 100)
        valor_liquido = valor_servicos - valor_iss if dados.get('iss_retido') else valor_servicos
        
        result = db.execute(insert_query, {
            'cliente_id': cliente_id,
            'numero_rps': int(dados['numero_rps']),
            'serie_rps': dados['serie_rps'],
            'tipo_rps': dados['tipo_rps'],
            'data_emissao': datetime.now(),
            'data_competencia': dados['data_competencia'],
            'natureza_operacao': dados['natureza_operacao'],
            'tomador_cpf_cnpj': dados['tomador_cpf_cnpj'].replace('.', '').replace('-', '').replace('/', ''),
            'tomador_razao_social': dados['tomador_razao_social'],
            'tomador_endereco': f"{dados['tomador_logradouro']}, {dados['tomador_numero']}",
            'codigo_servico': dados['codigo_servico'],
            'discriminacao': dados['discriminacao'],
            'valor_servicos': valor_servicos,
            'aliquota_iss': aliquota,
            'valor_iss': valor_iss,
            'valor_liquido': valor_liquido,
            # Campos Reforma Tributária (LC 214/2025)
            'codigo_nbs': dados.get('codigo_nbs', '101010000'),
            'finalidade_nfse': dados.get('finalidade_nfse', '0'),
            'indicador_consumidor_final': dados.get('indicador_consumidor_final', '0'),
            'codigo_indicador_operacao': dados.get('codigo_indicador_operacao', '000001'),
            'indicador_destinatario': dados.get('indicador_destinatario', '0'),
            'cst_ibs_cbs': dados.get('cst_ibs_cbs', '001'),
            'codigo_classificacao_tributaria': dados.get('codigo_classificacao_tributaria', '000001'),
            'codigo_localidade_incidencia': dados.get('codigo_localidade_incidencia', '3549805'),
            'percentual_redutor': dados.get('percentual_redutor', 0.0),
            'percentual_total_tributos_federais': dados.get('percentual_total_tributos_federais', 0.0),
            'percentual_total_tributos_estaduais': dados.get('percentual_total_tributos_estaduais', 0.0),
            'percentual_total_tributos_municipais': dados.get('percentual_total_tributos_municipais', 5.0),
            'regime_especial_tributacao': dados.get('regime_especial_tributacao'),
            'optante_simples_nacional': dados.get('optante_simples_nacional', True),
            'incentivador_cultural': dados.get('incentivador_cultural', False),
            # Campos de controle
            'xml_rps': xml_rps,
            'status': status,
            'ambiente': ambiente,
            'protocolo': protocolo,
            'mensagem_retorno': mensagem_erro,
            'created_at': datetime.now()
        })
        
        db.commit()
        row = result.fetchone()
        nfse_id = row[0] if row else None
        
        if not nfse_id:
            raise Exception("Erro ao obter ID da NFS-e inserida")
        
        return redirect(url_for('nfse.visualizar', nfse_id=nfse_id))
        
    except Exception as e:
        print(f"[NFSE] Erro na emissão: {e}")
        traceback.print_exc()
        db.rollback()
        flash(f"Erro ao emitir NFS-e: {str(e)}", "danger")
        return redirect(url_for('nfse.emitir_form'))
    finally:
        db.close()


@nfse_bp.route('/consultar/<protocolo>')
@login_required
@viewer_or_higher_required()
def consultar_status(protocolo):
    """Consulta status do lote pelo protocolo"""
    db = next(get_db())
    try:
        # Obter clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Determinar cliente_id
        cliente_id = session.get('current_client_id', accessible_clients[0])
        if cliente_id not in accessible_clients:
            cliente_id = accessible_clients[0]
        
        # Buscar dados do prestador
        prestador = db.query(Cliente).filter(Cliente.cliente_id == cliente_id).first()
        
        if not prestador:
            flash("Dados do prestador não encontrados", "danger")
            return redirect(url_for('nfse.list_nfse'))
        
        # TODO: Implementar consulta real ao webservice GISS
        resultado = {
            'situacao': 'aguardando',
            'mensagem': 'Consulta ao webservice será implementada em breve'
        }
        
        return render_template(
            'admin/nfse/consulta_status.html',
            protocolo=protocolo,
            resultado=resultado,
            sucesso=False
        )
        
    except Exception as e:
        print(f"[NFSE] Erro na consulta: {e}")
        flash(f"Erro ao consultar: {str(e)}", "danger")
        return redirect(url_for('nfse.list_nfse'))
    finally:
        db.close()


@nfse_bp.route('/cancelar/<int:nfse_id>', methods=['GET', 'POST'])
@login_required
@editor_or_admin_required()
def cancelar(nfse_id):
    """Cancela uma NFS-e"""
    db = next(get_db())
    try:
        # Obter clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Determinar cliente_id
        cliente_id = session.get('current_client_id', accessible_clients[0])
        if cliente_id not in accessible_clients:
            cliente_id = accessible_clients[0]
        
        # Buscar NFS-e
        query = text("""
            SELECT * FROM nfse WHERE id = :nfse_id AND cliente_id = :cliente_id
        """)
        result = db.execute(query, {"nfse_id": nfse_id, "cliente_id": cliente_id})
        nfse_data = result.mappings().first()
        
        if not nfse_data:
            flash("NFS-e não encontrada", "danger")
            return redirect(url_for('nfse.list_nfse'))
        
        if request.method == 'POST':
            motivo = request.form.get('motivo_cancelamento', '1')
            
            # TODO: Implementar cancelamento real no webservice GISS
            
            # Atualizar status no banco
            update_query = text("""
                UPDATE nfse SET status = '3', updated_at = :updated_at
                WHERE id = :nfse_id
            """)
            db.execute(update_query, {"updated_at": datetime.now(), "nfse_id": nfse_id})
            db.commit()
            
            flash("NFS-e marcada como cancelada!", "success")
            flash("Nota: Cancelamento no webservice será implementado em breve.", "info")
            return redirect(url_for('nfse.list_nfse'))
        
        return render_template('admin/nfse/cancelar.html', nfse=nfse_data)
        
    except Exception as e:
        print(f"[NFSE] Erro no cancelamento: {e}")
        db.rollback()
        flash(f"Erro ao cancelar: {str(e)}", "danger")
        return redirect(url_for('nfse.list_nfse'))
    finally:
        db.close()


@nfse_bp.route('/visualizar/<int:nfse_id>')
@login_required
@viewer_or_higher_required()
def visualizar(nfse_id):
    """Visualiza detalhes de uma NFS-e"""
    db = next(get_db())
    try:
        # Obter clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Determinar cliente_id
        cliente_id = session.get('current_client_id', accessible_clients[0])
        if cliente_id not in accessible_clients:
            cliente_id = accessible_clients[0]
        
        query = text("""
            SELECT * FROM nfse WHERE id = :nfse_id AND cliente_id = :cliente_id
        """)
        result = db.execute(query, {"nfse_id": nfse_id, "cliente_id": cliente_id})
        nfse_data = result.mappings().first()
        
        if not nfse_data:
            flash("NFS-e não encontrada", "danger")
            return redirect(url_for('nfse.list_nfse'))
        
        return render_template('admin/nfse/visualizar.html', nfse=nfse_data)
        
    except Exception as e:
        flash(f"Erro ao visualizar: {str(e)}", "danger")
        return redirect(url_for('nfse.list_nfse'))
    finally:
        db.close()


@nfse_bp.route('/xml/<int:nfse_id>')
@login_required
@viewer_or_higher_required()
def download_xml(nfse_id):
    """Download do XML da NFS-e"""
    db = next(get_db())
    try:
        # Obter clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))
        
        # Determinar cliente_id
        cliente_id = session.get('current_client_id', accessible_clients[0])
        if cliente_id not in accessible_clients:
            cliente_id = accessible_clients[0]
        
        query = text("""
            SELECT xml_nfse, xml_rps, numero_nfse, numero_rps
            FROM nfse WHERE id = :nfse_id AND cliente_id = :cliente_id
        """)
        result = db.execute(query, {"nfse_id": nfse_id, "cliente_id": cliente_id})
        nfse_data = result.mappings().first()
        
        if not nfse_data:
            flash("NFS-e não encontrada", "danger")
            return redirect(url_for('nfse.list_nfse'))
        
        # Priorizar XML da NFS-e, senão usar RPS
        xml_content = nfse_data['xml_nfse'] or nfse_data['xml_rps']
        numero = nfse_data['numero_nfse'] or nfse_data['numero_rps']
        
        if not xml_content:
            flash("XML não disponível", "warning")
            return redirect(url_for('nfse.visualizar', nfse_id=nfse_id))
        
        return Response(
            xml_content,
            mimetype='application/xml',
            headers={
                'Content-Disposition': f'attachment; filename=nfse_{numero}.xml'
            }
        )
        
    except Exception as e:
        flash(f"Erro ao baixar XML: {str(e)}", "danger")
        return redirect(url_for('nfse.list_nfse'))
    finally:
        db.close()


# ============================================================================
# API endpoints para AJAX
# ============================================================================

@nfse_bp.route('/api/aliquota/<codigo_servico>')
@login_required
def get_aliquota(codigo_servico):
    """Retorna alíquota ISS para o código de serviço"""
    aliquota = ALIQUOTAS_ISS_SJRP.get(codigo_servico, ALIQUOTAS_ISS_SJRP.get("default", 5.0))
    return jsonify({"aliquota": aliquota})


@nfse_bp.route('/api/tomador/<int:tomador_id>')
@login_required
def get_tomador(tomador_id):
    """Retorna dados do Tomadores"""
    db = next(get_db())
    try:
        # Obter clientes acessíveis
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            return jsonify({"error": "Acesso negado"}), 403
        
        # Determinar cliente_id
        cliente_id = session.get('current_client_id', accessible_clients[0])
        if cliente_id not in accessible_clients:
            cliente_id = accessible_clients[0]
        
        query = text("""
            SELECT * FROM destinatarios_nfe 
            WHERE destinatario_id = :tomador_id AND cliente_id = :cliente_id
        """)
        result = db.execute(query, {"tomador_id": tomador_id, "cliente_id": cliente_id})
        Tomadores = result.mappings().first()
        
        if Tomadores:
            return jsonify(dict(Tomadores))
        
        return jsonify({"error": "Tomadores não encontrado"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@nfse_bp.route('/api/servicos-lc116')
@login_required
def get_servicos_lc116():
    """Retorna lista de códigos de serviço LC116 ativos"""
    db = next(get_db())
    try:
        query = text("""
            SELECT codigo, descricao 
            FROM codigos_servico_lc116 
            WHERE ativo = TRUE 
            ORDER BY codigo
        """)
        result = db.execute(query)
        servicos = [{"codigo": row[0], "descricao": row[1]} for row in result]
        
        return jsonify({"success": True, "servicos": servicos})
        
    except Exception as e:
        print(f"Erro ao buscar serviços LC116: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@nfse_bp.route('/api/codigos-nbs/<codigo_servico>')
@login_required
def get_codigos_nbs(codigo_servico):
    """Retorna códigos NBS disponíveis para um serviço LC116"""
    db = next(get_db())
    try:
        query = text("""
            SELECT codigo, descricao, nivel
            FROM codigos_nbs 
            WHERE codigo_servico_lc116 = :codigo_servico 
            AND ativo = TRUE
            ORDER BY codigo
        """)
        result = db.execute(query, {"codigo_servico": codigo_servico})
        codigos_nbs = [
            {"codigo": row[0], "descricao": row[1], "nivel": row[2]} 
            for row in result
        ]
        
        return jsonify({"success": True, "codigos_nbs": codigos_nbs})
        
    except Exception as e:
        print(f"Erro ao buscar códigos NBS: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

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


def _coletar_dados_prestador_nfse(form, prestador_data):
    """Monta os dicts `dados` (campos do formulário de emissão) e `prestador_dict`
    a partir do form da tela de emissão de NFS-e e do Cliente (prestador).

    Compartilhado entre a emissão real (`emitir`) e as prévias
    (`preview_xml`/`preview_danfe`) para não duplicar o mapeamento de campos.
    """
    dados = {
        'cliente_id': prestador_data.cliente_id,
        'numero_rps': form.get('numero_rps'),
        'serie_rps': form.get('serie_rps', '1'),
        'tipo_rps': form.get('tipo_rps', '1'),
        'data_competencia': form.get('data_competencia'),
        'natureza_operacao': form.get('natureza_operacao', '1'),
        'ambiente': form.get('ambiente', 'homologacao'),

        # Tomadores
        'tomador_cpf_cnpj': form.get('tomador_cpf_cnpj', ''),
        'tomador_razao_social': form.get('tomador_razao_social', ''),
        'tomador_inscricao_municipal': form.get('tomador_inscricao_municipal'),
        'tomador_logradouro': form.get('tomador_logradouro', ''),
        'tomador_numero': form.get('tomador_numero', ''),
        'tomador_complemento': form.get('tomador_complemento', ''),
        'tomador_bairro': form.get('tomador_bairro', ''),
        'tomador_codigo_municipio': form.get('tomador_codigo_municipio', ''),
        'tomador_uf': form.get('tomador_uf', 'SP'),
        'tomador_cep': form.get('tomador_cep', ''),
        'tomador_telefone': form.get('tomador_telefone', ''),
        'tomador_email': form.get('tomador_email', ''),

        # Serviço
        'codigo_servico': form.get('codigo_servico', '17.01'),
        'codigo_cnae': form.get('codigo_cnae'),
        'discriminacao': form.get('discriminacao', ''),
        'valor_servico': br_to_float(form.get('valor_servico', 0)),
        'valor_deducoes': br_to_float(form.get('valor_deducoes', 0)),
        'valor_pis': br_to_float(form.get('valor_pis', 0)),
        'valor_cofins': br_to_float(form.get('valor_cofins', 0)),
        'valor_inss': br_to_float(form.get('valor_inss', 0)),
        'valor_ir': br_to_float(form.get('valor_ir', 0)),
        'valor_csll': br_to_float(form.get('valor_csll', 0)),
        'outras_retencoes': br_to_float(form.get('outras_retencoes', 0)),
        'desconto_incondicionado': br_to_float(form.get('desconto_incondicionado', 0)),
        'desconto_condicionado': br_to_float(form.get('desconto_condicionado', 0)),
        'aliquota_iss': br_to_float(form.get('aliquota_iss', 0)),
        'iss_retido': form.get('iss_retido') == 'on',
        'codigo_municipio_prestacao': form.get('codigo_municipio_prestacao', '3549805'),

        # Campos obrigatórios Reforma Tributária (LC 214/2025)
        'codigo_nbs': form.get('codigo_nbs', '101010000'),
        'percentual_total_tributos_federais': br_to_float(form.get('percentual_total_tributos_federais', 0)),
        'percentual_total_tributos_estaduais': br_to_float(form.get('percentual_total_tributos_estaduais', 0)),
        'percentual_total_tributos_municipais': br_to_float(form.get('percentual_total_tributos_municipais', 5)),
        'finalidade_nfse': form.get('finalidade_nfse', '0'),
        'indicador_consumidor_final': form.get('indicador_consumidor_final', '0'),
        'codigo_indicador_operacao': form.get('codigo_indicador_operacao', '000001'),
        'indicador_destinatario': form.get('indicador_destinatario', '0'),
        'cst_ibs_cbs': form.get('cst_ibs_cbs', '001'),
        'codigo_classificacao_tributaria': form.get('codigo_classificacao_tributaria', '000001'),
        'codigo_localidade_incidencia': form.get('codigo_localidade_incidencia', '3549805'),
        'percentual_redutor': br_to_float(form.get('percentual_redutor', 0)),
        'regime_especial_tributacao': form.get('regime_especial_tributacao'),
        # Buscar do regime tributário do cliente (CRT=1 = Simples Nacional)
        'optante_simples_nacional': prestador_data.regime_tributario.crt == 1 if prestador_data.regime_tributario else False,
        'incentivador_cultural': form.get('incentivador_cultural') == 'on',

        # Informações adicionais
        'informacoes_complementares': form.get('informacoes_complementares', '')
    }

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

    return dados, prestador_dict


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
        dados, prestador_dict = _coletar_dados_prestador_nfse(request.form, prestador_data)
        
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


def _carregar_prestador_para_preview(db, request_form):
    """Resolve cliente_id (mesmo padrão de emitir/emitir_form) e carrega o
    prestador com regime tributário. Retorna (prestador_data, cliente_id) ou
    (None, None) se não houver acesso/prestador."""
    from sqlalchemy.orm import joinedload

    accessible_clients = get_accessible_client_ids(db)
    if not accessible_clients:
        return None, None

    cliente_id = None
    if request_form.get('cliente_id'):
        try:
            cliente_id = int(request_form.get('cliente_id'))
            if cliente_id not in accessible_clients:
                return None, None
        except ValueError:
            return None, None
    elif session.get('current_client_id'):
        cliente_id = session.get('current_client_id')
        if cliente_id not in accessible_clients:
            cliente_id = accessible_clients[0]
    else:
        cliente_id = accessible_clients[0]

    prestador_data = db.query(Cliente).options(
        joinedload(Cliente.regime_tributario)
    ).filter(Cliente.cliente_id == cliente_id).first()

    return prestador_data, cliente_id


@nfse_bp.route('/preview-xml', methods=['POST'])
@login_required
@editor_or_admin_required()
def preview_xml():
    """Gera o XML do RPS a partir dos dados do formulário, SEM enviar ao GISS
    nem salvar no banco — usado pelo botão 'Visualizar XML' na tela de emissão."""
    db = next(get_db())
    try:
        prestador_data, cliente_id = _carregar_prestador_para_preview(db, request.form)
        if not prestador_data:
            return jsonify({'success': False, 'message': 'Prestador não encontrado ou sem acesso.'}), 404

        dados, prestador_dict = _coletar_dados_prestador_nfse(request.form, prestador_data)
        nfse = criar_nfse_de_formulario(dados, prestador_dict)

        ambiente = dados.get('ambiente', 'homologacao')
        service = NFSeService(ambiente=ambiente)
        xml_rps = service.gerar_xml_rps(nfse)

        return jsonify({'success': True, 'xml_preview': xml_rps, 'message': 'XML gerado com sucesso (preview)'})
    except Exception as e:
        print(f"[NFSE] Erro ao gerar preview do XML: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro ao gerar preview: {str(e)}'}), 500
    finally:
        db.close()


@nfse_bp.route('/preview-danfe', methods=['POST'])
@login_required
@editor_or_admin_required()
def preview_danfe():
    """Gera um DANFSe de RASCUNHO (sem chave nacional/protocolo, pois esses
    dados só existem após o RPS ser processado pelo GISS/ADN) a partir dos
    dados do formulário — usado pelo botão 'Preview DANFE' na tela de emissão."""
    import tempfile
    import os as _os
    from models.nfse_model import CODIGOS_MUNICIPIO_SP
    from services.danfse_service import renderizar_danfse_pdf

    db = next(get_db())
    pdf_path = None
    try:
        prestador_data, cliente_id = _carregar_prestador_para_preview(db, request.form)
        if not prestador_data:
            return jsonify({'success': False, 'message': 'Prestador não encontrado ou sem acesso.'}), 404

        dados, prestador_dict = _coletar_dados_prestador_nfse(request.form, prestador_data)
        ambiente = dados.get('ambiente', 'homologacao')

        valor_servico = dados.get('valor_servico', 0.0)
        aliquota = dados.get('aliquota_iss', 0.0)
        valor_iss = valor_servico * (aliquota / 100)
        valor_liquido = valor_servico - valor_iss if dados.get('iss_retido') else valor_servico

        municipio_prestacao = CODIGOS_MUNICIPIO_SP.get(
            dados.get('codigo_municipio_prestacao'), dados.get('codigo_municipio_prestacao')
        )

        dados_rascunho = {
            'chave_acesso': None,
            'numero_nfse': None,
            'competencia': dados.get('data_competencia'),
            'dh_proc': None,
            'numero_dps': dados.get('numero_rps'),
            'serie_dps': dados.get('serie_rps'),
            'dh_emi_dps': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'tp_emit': 'Prestador',
            'c_stat': '0',
            'fin_nfse': dados.get('finalidade_nfse'),
            'tp_amb': '2' if ambiente == 'homologacao' else '1',
            'amb_ger': 'Rascunho local (pré-envio ao GISS/ADN)',
            'x_loc_emi': municipio_prestacao,
            'prest_cnpj': prestador_dict.get('cnpj'),
            'prest_im': prestador_dict.get('inscricao_municipal'),
            'prest_fone': getattr(prestador_data, 'telefone_contato', None),
            'prest_nome': prestador_dict.get('razao_social'),
            'prest_email': getattr(prestador_data, 'email_contato', None),
            'toma_cnpj': dados.get('tomador_cpf_cnpj'),
            'toma_nome': dados.get('tomador_razao_social'),
            'toma_fone': dados.get('tomador_telefone'),
            'toma_email': dados.get('tomador_email'),
            'dest_cnpj': None,
            'dest_nome': None,
            'c_trib_nac': dados.get('codigo_servico'),
            'c_nbs': dados.get('codigo_nbs'),
            'x_trib_nac': None,
            'x_desc_serv': dados.get('discriminacao'),
            'trib_issqn': '1' if aliquota else None,
            'v_bc_issqn': str(valor_servico - dados.get('valor_deducoes', 0.0) - dados.get('desconto_incondicionado', 0.0)),
            'aliq_issqn': str(aliquota) if aliquota else None,
            'v_issqn': str(valor_iss),
            'cst_ibscbs': dados.get('cst_ibs_cbs'),
            'c_class_trib': dados.get('codigo_classificacao_tributaria'),
            'v_ibs_tot': None,
            'v_cbs_tot': None,
            'v_serv': str(valor_servico),
            'v_liq': str(valor_liquido),
            'v_tot_nf': str(valor_liquido),
            'x_inf_comp': dados.get('informacoes_complementares'),
            'watermark_texto': 'PRÉVIA - SEM VALOR FISCAL',
        }

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            pdf_path = tmp.name

        renderizar_danfse_pdf(dados_rascunho, pdf_path)

        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        return Response(pdf_bytes, mimetype='application/pdf')
    except Exception as e:
        print(f"[NFSE] Erro ao gerar preview do DANFE: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro ao gerar preview do DANFE: {str(e)}'}), 500
    finally:
        if pdf_path:
            try:
                _os.remove(pdf_path)
            except OSError:
                pass
        db.close()


@nfse_bp.route('/consultar/<protocolo>')
@login_required
@viewer_or_higher_required()
def consultar_status(protocolo):
    """
    Consulta o status do lote no GISS Online (Ambiente de Dados Nacional) e,
    quando processado com sucesso, persiste `numero_nfse`, `codigo_verificacao`,
    `chave_nota_nacional` e o `xml_nfse` (CompNfse completo) — dados
    necessários para o DANFSe (NT008).
    """
    db = next(get_db())
    try:
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))

        cliente_id = session.get('current_client_id', accessible_clients[0])
        if cliente_id not in accessible_clients:
            cliente_id = accessible_clients[0]

        prestador = db.query(Cliente).filter(Cliente.cliente_id == cliente_id).first()
        if not prestador:
            flash("Dados do prestador não encontrados", "danger")
            return redirect(url_for('nfse.list_nfse'))

        nfse_row = db.execute(
            text("SELECT id, ambiente FROM nfse WHERE protocolo = :protocolo AND cliente_id = :cliente_id"),
            {"protocolo": protocolo, "cliente_id": cliente_id}
        ).mappings().first()

        if not nfse_row:
            flash("NFS-e com este protocolo não encontrada.", "danger")
            return redirect(url_for('nfse.list_nfse'))

        service = NFSeService(ambiente=nfse_row['ambiente'] or 'homologacao')
        sucesso, resultado = service.consultar_lote(
            protocolo=protocolo,
            prestador_cnpj=(prestador.cnpj or '').replace('.', '').replace('-', '').replace('/', ''),
            inscricao_municipal=prestador.inscricao_municipal or '',
            db_session=db,
            cliente_id=cliente_id,
        )

        if not sucesso:
            flash("Erro ao consultar status: {}".format(resultado.get('erro', 'Erro desconhecido')), "danger")
            return render_template(
                'admin/nfse/consulta_status.html',
                protocolo=protocolo, resultado=resultado, sucesso=False, nfse_id=nfse_row['id']
            )

        situacao_codigo = resultado.get('situacao_codigo')

        if situacao_codigo == '4' and resultado.get('chave_nota_nacional'):
            # Processado com sucesso e com chave do ADN — persistir NFS-e definitiva
            db.execute(text("""
                UPDATE nfse SET
                    status = '1',
                    numero_nfse = :numero_nfse,
                    codigo_verificacao = :codigo_verificacao,
                    chave_nota_nacional = :chave_nota_nacional,
                    xml_nfse = :xml_nfse,
                    updated_at = :updated_at
                WHERE id = :nfse_id
            """), {
                "numero_nfse": resultado.get('numero_nfse'),
                "codigo_verificacao": resultado.get('codigo_verificacao'),
                "chave_nota_nacional": resultado.get('chave_nota_nacional'),
                "xml_nfse": resultado.get('xml_nfse'),
                "updated_at": datetime.now(),
                "nfse_id": nfse_row['id'],
            })
            db.commit()
            flash("NFS-e autorizada e sincronizada com o Ambiente de Dados Nacional!", "success")
        elif situacao_codigo == '3':
            db.execute(text("""
                UPDATE nfse SET status = '4', mensagem_retorno = :mensagem, updated_at = :updated_at
                WHERE id = :nfse_id
            """), {
                "mensagem": resultado.get('situacao', 'Processado com erro'),
                "updated_at": datetime.now(),
                "nfse_id": nfse_row['id'],
            })
            db.commit()
            flash("Lote processado com erro pelo GISS. Verifique os detalhes.", "danger")
        else:
            flash(f"Status atual: {resultado.get('situacao', 'Desconhecido')}. Ainda aguardando processamento.", "info")

        return render_template(
            'admin/nfse/consulta_status.html',
            protocolo=protocolo, resultado=resultado, sucesso=(situacao_codigo == '4'), nfse_id=nfse_row['id']
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


@nfse_bp.route('/pdf/<int:nfse_id>')
@login_required
@viewer_or_higher_required()
def download_danfse(nfse_id):
    """
    Gera e faz download do DANFSe (Documento Auxiliar da NFS-e Nacional),
    conforme NT008. Exige que a NFS-e tenha sido processada com sucesso pelo
    GISS/Ambiente de Dados Nacional (campo `xml_nfse` com `ChaveNotaNacional`
    preenchida). NFS-e ainda pendente de consulta/confirmação não é elegível.
    """
    import tempfile
    from services.danfse_service import gerar_danfse_pdf, XmlNaoENacionalError

    db = next(get_db())
    try:
        accessible_clients = get_accessible_client_ids(db)
        if not accessible_clients:
            flash('Você não tem acesso a nenhum cliente.', 'danger')
            return redirect(url_for('home.home'))

        cliente_id = session.get('current_client_id', accessible_clients[0])
        if cliente_id not in accessible_clients:
            cliente_id = accessible_clients[0]

        query = text("""
            SELECT xml_nfse, numero_nfse, numero_rps, ambiente
            FROM nfse WHERE id = :nfse_id AND cliente_id = :cliente_id
        """)
        result = db.execute(query, {"nfse_id": nfse_id, "cliente_id": cliente_id})
        nfse_data = result.mappings().first()

        if not nfse_data or not nfse_data['xml_nfse']:
            flash("XML da NFS-e não disponível para gerar o DANFSe.", "warning")
            return redirect(url_for('nfse.visualizar', nfse_id=nfse_id))

        numero = nfse_data['numero_nfse'] or nfse_data['numero_rps']

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            gerar_danfse_pdf(
                nfse_data['xml_nfse'],
                tmp_path,
                ambiente=nfse_data['ambiente'] or 'producao',
            )
        except XmlNaoENacionalError as e:
            flash(
                "Esta NFS-e ainda não possui a chave de acesso do Ambiente de "
                "Dados Nacional (ChaveNotaNacional). Consulte o status do lote "
                f"no GISS antes de gerar o DANFSe. Detalhe técnico: {e}",
                "warning"
            )
            return redirect(url_for('nfse.visualizar', nfse_id=nfse_id))

        with open(tmp_path, 'rb') as f:
            pdf_bytes = f.read()

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=danfse_{numero}.pdf'
            }
        )

    except Exception as e:
        flash(f"Erro ao gerar DANFSe: {str(e)}", "danger")
        return redirect(url_for('nfse.visualizar', nfse_id=nfse_id))
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
        # item_pai preenchido = item "folha" (ex.: '1.01'); item_pai vazio/nulo =
        # cabeçalho de seção (ex.: '1' - "Serviços de informática e congêneres").
        # Cabeçalhos de seção não são códigos de serviço válidos para uma NFS-e
        # e não devem aparecer como opção selecionável (bug: usuário podia
        # escolher "1" em vez de "1.01" ao cadastrar uma regra tributária,
        # fazendo a busca de regra na emissão nunca encontrar nada).
        query = text("""
            SELECT codigo, descricao 
            FROM codigos_servico_lc116 
            WHERE ativo = TRUE 
              AND item_pai IS NOT NULL
              AND item_pai != ''
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

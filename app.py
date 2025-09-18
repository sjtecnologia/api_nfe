from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, abort, current_app, get_flashed_messages
import json
import os
import uuid
from datetime import datetime, date
from decimal import Decimal
from functools import wraps
# Importe os modelos do seu arquivo models.py
from database.models import (
    Base, Cfop, Ncm, Produto, Cliente, RegimeTributario, CertificadoDigital,
    NFeEmitidas, RegraTributacao, Csosnicms, Csticms, OrigemMercadoria,
    DestinatarioNFe, MotivoDesoneracao, User, Role, Permission, UserRole,
    RolePermission, UserClient
)
# Imports para processar certificado
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12 # Adicione esta importação
from cryptography.hazmat.primitives import hashes
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker, joinedload # ADICIONADO joinedload aqui
from sqlalchemy.exc import IntegrityError, OperationalError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Chave secreta para mensagens flash (SUBSTITUA POR UMA CHAVE SEGURA EM PRODUÇÃO)
# Mantenha essa chave segura! Use algo como os.urandom(24) ou uma string complexa.
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'sua_chave_secreta_padrao_muito_complexa_e_longa_aqui')
# --- Configuração do Banco de Dados ---
# ATENÇÃO: Verifique se o host e o nome do banco de dados estão corretos para o seu ambiente.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Mo2505@localhost:5432/sjtnfe")

if "postgresql" in SQLALCHEMY_DATABASE_URL:
    os.environ['DB_TYPE'] = 'postgresql'
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    os.environ['DB_TYPE'] = 'postgresql'

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.context_processor
def inject_template_globals():
    return {
        'has_permission': has_permission,
        'current_user': current_user, # Já deve estar disponível pelo Flask-Login, mas garante
        'now': datetime.now() # Para o footer, se ainda não tiver
    }

# Dependência para obter a sessão do DB em cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# --- Configuração do Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Rota para onde o usuário é redirecionado se não estiver logado
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"
@login_manager.user_loader
def load_user(user_id):
    # Esta função é chamada pelo Flask-Login para carregar um usuário a partir do ID
    db = SessionLocal() # Abre uma nova sessão para esta função
    try:
        user = db.get(User, int(user_id)) # Se 'db' for sua instância de Session
        return user
    finally:
        db.close() # Fecha a sessão

# --- Funções Auxiliares ---
# Função para obter os IDs dos clientes que o usuário logado tem acesso
def get_accessible_client_ids(db_session):
    if not current_user.is_authenticated:
        return []
    # Se o usuário é um administrador, ele tem acesso a todos os clientes
    if has_permission('admin.full_access'): # Exemplo de permissão de super-admin
        # Retorna todos os clientes existentes para um admin
        return [c.cliente_id for c in db_session.query(Cliente.cliente_id).all()]
    
    # Caso contrário, filtra pelos clientes explicitamente vinculados
    accessible_client_ids = db_session.query(UserClient.client_id).filter_by(user_id=current_user.id).all()
    return [c[0] for c in accessible_client_ids]
# Função para verificar se o usuário atual tem uma permissão específica
def has_permission(permission_name):
    if not current_user.is_authenticated:
        return False
    
    # Super-admin (com permissão 'admin.full_access') sempre tem todas as permissões
# Super-admin (com permissão 'admin.full_access') sempre tem todas as permissões
    # Verifique se o usuário tem a permissão 'admin.full_access'
    db = SessionLocal() # Nova sessão para esta verificação
    user_permissions_query = db.query(Permission.name).join(RolePermission).join(Role).join(UserRole).filter(UserRole.user_id == current_user.id).distinct()
    user_permissions_names = [p[0] for p in user_permissions_query.all()]
    db.close()
    if 'admin.full_access' in user_permissions_names:
        return True
    
    return permission_name in user_permissions_names
# Decorator Personalizado para Checagem de Permissão
def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Por favor, faça login para acessar esta página.", "info")
                return redirect(url_for('login', next=request.url))
            if not has_permission(permission_name):
                flash(f"Você não tem permissão para acessar esta funcionalidade ({permission_name}).", 'danger')
                return redirect(url_for('home')) # Ou para uma página de "Acesso Negado"
            return f(*args, **kwargs)
        return decorated_function
    return decorator
# Função auxiliar para processar upload de certificado
def process_certificate_upload(db_session, cliente_id, request_form, request_files):
    cert_file = request_files.get('conteudo_certificado_file')
    
    if cert_file and cert_file.filename != '':
        try:
            file_content = cert_file.read() # Conteúdo em bytes
            cert_password = request_form.get('cert_senha_certificado')
            if not cert_password:
                flash('Senha do certificado é obrigatória ao fazer upload de um arquivo.', 'danger')
                return False, None
            
            private_key = None
            cert_x509_obj = None 
            try:
                # CORREÇÃO AQUI: pkcs12 é um módulo, e load_key_and_certificates é um método que retorna uma tupla
                p12_tuple = pkcs12.load_key_and_certificates( 
                    file_content,
                    cert_password.encode('utf-8'), 
                    default_backend()
                )
                private_key = p12_tuple[0] # A chave privada é o primeiro elemento da tupla
                cert_x509_obj = p12_tuple[1] # O certificado X.509 é o segundo elemento da tupla
            except ValueError:
                try:
                    # Fallback para certificado PEM (se for o caso)
                    cert_x509_obj = x509.load_pem_x509_certificate(file_content, default_backend())
                except ValueError:
                    flash(f'Erro ao carregar o certificado: Formato de arquivo ou senha inválidos para {cert_file.filename}.', 'danger')
                    return False, None
            
            if not cert_x509_obj:
                flash(f'Não foi possível carregar o certificado do arquivo {cert_file.filename}.', 'danger')
                return False, None
            
            fingerprint = cert_x509_obj.fingerprint(hashes.SHA256()).hex()
            validade_inicio_final = cert_x509_obj.not_valid_before_utc.replace(tzinfo=None)
            validade_fim_final = cert_x509_obj.not_valid_after_utc.replace(tzinfo=None)
# Aqui você pode verificar se já existe um certificado com o mesmo fingerprint para o cliente
            # existente_cert = db_session.query(CertificadoDigital).filter_by(cliente_id=cliente_id, fingerprint=fingerprint).first()
            # if existente_cert:
            #    flash('Já existe um certificado com este fingerprint para este cliente.', 'warning')
            #    return False, None
            encrypted_cert_password = cert_password.encode('utf-8')
            
            cert_obj = CertificadoDigital(
                cliente_id=cliente_id,
                fingerprint=fingerprint,
                conteudo_certificado=file_content,
                senha_certificado=encrypted_cert_password,
                validade_inicio=validade_inicio_final,
                validade_fim=validade_fim_final,
                ativo=request_form.get('cert_ativo') == 'on',
                data_upload=datetime.now(),
                nome_arquivo_original=request_form.get('cert_nome_arquivo_original') or cert_file.filename,
                created_by_user_id=current_user.id if current_user.is_authenticated else None # Auditoria
            )
            db_session.add(cert_obj)
            return True, cert_obj
        except Exception as e:
            flash(f'Erro inesperado ao processar o certificado: {e}', 'danger')
            current_app.logger.error(f"Certificate processing error: {e}", exc_info=True) # Log para depuração
            return False, None
    return True, None # Nenhum arquivo de certificado enviado, sem erro
# --- Rotas de Autenticação ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = next(get_db())
        user = db.query(User).filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=request.form.get('remember_me')) # Adiciona "lembrar-me"
            flash('Login realizado com sucesso!', 'success')
            return redirect(request.args.get('next') or url_for('home'))
        else:
            flash('Nome de usuário ou senha inválidos.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))
# --- Rotas Principais ---
@app.route('/')
@login_required
def home():
    """Rota inicial para o sistema após o login."""
    return render_template('home.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar a saúde da API."""
    return jsonify({"status": "UP", "timestamp": datetime.now().isoformat()}), 200

# --- Rotas de API para listagem geral (retornam JSON - sem proteção por login) ---
# Essas rotas geralmente não são expostas diretamente para usuários finais,
# mas podem ser consumidas pela interface web do seu próprio aplicativo já logado.
# Para API externa, considere autenticação por API Key/Token.
@app.route('/api/cfops', methods=['GET'])
def get_api_cfops():
    db = next(get_db())
    cfops = db.query(Cfop).all()
    cfop_list = [{"cfop_id": c.cfop_id, "cfop": c.cfop, "descricao": c.descricao} for c in cfops]
    return jsonify(cfop_list), 200

@app.route('/api/ncms', methods=['GET'])
def get_api_ncms():
    db = next(get_db())
    ncms = db.query(Ncm).all()
    ncm_list = [{"ncm_id": n.ncm_id, "codigo": n.codigo, "descricao": n.descricao} for n in ncms]
    return jsonify(ncm_list), 200
@app.route('/api/produtos', methods=['GET'])
def get_api_produtos():
    db = next(get_db())
    produtos = db.query(Produto).all() # ATENÇÃO: Retorna TODOS os produtos. Para API específica por cliente, adicione filtros.
    produto_list = [{"produto_id": p.produto_id, "codigo_interno": p.codigo_interno, "descricao": p.descricao} for p in produtos]
    return jsonify(produto_list), 200
@app.route('/api/clientes', methods=['GET'])
def get_api_clientes():
    db = next(get_db())
    clientes = db.query(Cliente).all() # ATENÇÃO: Retorna TODOS os clientes. Para API específica por usuário/cliente, adicione filtros.
    cliente_list = [{"cliente_id": c.cliente_id, "cnpj": c.cnpj, "razao_social": c.razao_social} for c in clientes]
    return jsonify(cliente_list), 200
@app.route('/api/certificados', methods=['GET'])
def get_api_certificados():
    db = next(get_db())
    certificados = db.query(CertificadoDigital).all() # ATENÇÃO: Retorna TODOS.
    certificado_list = [{"certificado_digital_id": c.certificado_digital_id, "fingerprint": c.fingerprint, "validade_fim": c.validade_fim.isoformat()} for c in certificados]
    return jsonify(certificado_list), 200
@app.route('/api/nfes', methods=['GET'])
def get_api_nfes():
    db = next(get_db())
    nfes = db.query(NFeEmitidas).all()
    nfe_list = [{"nfe_emitida_id": n.nfe_emitida_id, "tipo_nfe": n.tipo_nfe, "data_criacao": n.data_criacao.isoformat()} for n in nfes]
    return jsonify(nfe_list), 200
@app.route('/api/regimes_tributarios', methods=['GET'])
def get_api_regimes_tributarios():
    db = next(get_db())
    regimes_tributarios = db.query(RegimeTributario).all()
    regimes_tributario_list = [{"regime_tributario_id": r.regime_tributario_id, "nome": r.nome, "descricao": r.descricao} for r in regimes_tributarios]
    return jsonify(regimes_tributario_list), 200
@app.route('/api/regras_tributacao', methods=['GET'])
def get_api_regras_tributacao():
    db = next(get_db())
    regras_tributacao = db.query(RegraTributacao).all() # ATENÇÃO: Retorna TODAS.
    regra_tributacao_list = [{"regra_tributacao_id": r.regra_tributacao_id, "descricao_regra": r.descricao_regra} for r in regras_tributacao]
    return jsonify(regra_tributacao_list), 200
@app.route('/api/regras_tributacao/buscar', methods=['POST'])
@login_required # Proteger este endpoint também, para que apenas usuários logados possam buscar regras
def buscar_regra_tributacao():
    db = next(get_db())
    data = request.get_json()

    cliente_id = data.get('cliente_id')
    regime_tributario_id = data.get('regime_tributario_id')
    cfop_codigo = data.get('cfop_codigo')
    ncm_codigo = data.get('ncm_codigo')
    uf_origem = data.get('uf_origem')
    uf_destino = data.get('uf_destino')
    tipo_item = data.get('tipo_item')
    
    # Validar acesso ao cliente
    accessible_client_ids = get_accessible_client_ids(db)
    if cliente_id and int(cliente_id) not in accessible_client_ids:
        return jsonify({"error": "Acesso negado para este cliente."}), 403
    query = db.query(RegraTributacao).options(
        joinedload(RegraTributacao.regime_tributario),
        joinedload(RegraTributacao.cfop),
        joinedload(RegraTributacao.ncm),
        joinedload(RegraTributacao.cst_icms_obj),
        joinedload(RegraTributacao.csosn_icms_obj),
        joinedload(RegraTributacao.motivo_desoneracao)
    ).filter(RegraTributacao.ativo == True) # Apenas regras ativas
# Filtros obrigatórios
    if cliente_id: # A regra pode ser específica de um cliente ou global (cliente_id IS NULL)
        query = query.filter(or_(RegraTributacao.cliente_id == cliente_id, RegraTributacao.cliente_id.is_(None)))
    else: # Se o cliente_id não for fornecido, buscar apenas regras globais
        query = query.filter(RegraTributacao.cliente_id.is_(None))
    
    if regime_tributario_id:
        query = query.filter(RegraTributacao.regime_tributario_id == regime_tributario_id)
    
    # Filtros condicionais (se o valor for fornecido, aplica o filtro)
    if cfop_codigo:
        query = query.join(Cfop).filter(Cfop.cfop == cfop_codigo)
    if ncm_codigo:
        query = query.join(Ncm).filter(Ncm.codigo == ncm_codigo)
    if uf_origem:
        query = query.filter(RegraTributacao.uf_origem == uf_origem)
    if uf_destino:
        query = query.filter(RegraTributacao.uf_destino == uf_destino)
    if tipo_item:
        query = query.filter(RegraTributacao.tipo_item == tipo_item)
# Ordenar por prioridade (maior prioridade primeiro)
    # Se houver regras globais e específicas para o cliente,
    # e se cliente_id for not null na regra, dar prioridade a ela
    # e depois pela prioridade da regra.
    query = query.order_by(
        RegraTributacao.cliente_id.desc(), # Regras com cliente_id vêm antes de regras globais (None)
        RegraTributacao.prioridade.desc() # Maior prioridade primeiro
    )

    regra_encontrada = query.first()

    if regra_encontrada:
        return jsonify(regra_encontrada.to_dict()), 200
    else:
        return jsonify({"message": "Nenhuma regra de tributação encontrada para os critérios fornecidos."}), 404

@app.route('/api/csosn', methods=['GET'])
def get_api_csosns():
    db = next(get_db())
    csosns = db.query(Csosnicms).all()
    csosn_list = [{"csosn_id": c.csosn_id, "codigo": c.codigo, "descricao": c.descricao} for c in csosns]
    return jsonify(csosn_list), 200
@app.route('/api/cst', methods=['GET'])
def get_api_csts():
    db = next(get_db())
    csts = db.query(Csticms).all()
    cst_list = [{"cst_id": c.cst_id, "codigo": c.codigo, "descricao": c.descricao} for c in csts]
    return jsonify(cst_list), 200
@app.route('/api/origens_mercadoria', methods=['GET'])
def get_api_origens_mercadoria():
    db = next(get_db())
    origens = db.query(OrigemMercadoria).all()
    origens_list = [{"origem_id": o.origem_id, "codigo": o.codigo, "descricao": o.descricao} for o in origens]
    return jsonify(origens_list), 200


# --- Rotas de Administração (Front-end Rendering - Protegidas com Login e Permissões) ---
# --- Rotas de Administração (Front-end Rendering - Protegidas com Login e Permissões) ---

# Rotas para Certificados (A listagem geral continua aqui, mas não no menu)
@app.route('/admin/certificados')
@login_required
@permission_required('certificates.read')
def admin_certificados_list():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    certificados = db.query(CertificadoDigital).filter(CertificadoDigital.cliente_id.in_(accessible_client_ids)).all()
    # Adicionando clientes para exibir no template
    clientes = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    cliente_map = {c.cliente_id: c.razao_social for c in clientes}
    return render_template('admin_certificados_list.html', certificados=certificados, cliente_map=cliente_map)
# Rota de Adição de Certificado - Suporta requisição normal e AJAX para modal
@app.route('/admin/certificados/add', methods=['GET', 'POST'])
@login_required
@permission_required('certificates.create')
def admin_certificados_add():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    clientes_disponiveis = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    
    # Verifica se a requisição veio de um modal (AJAX)
    is_modal_request = request.args.get('modal', 'false').lower() == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    return_client_id = request.args.get('cliente_id', type=int) # Cliente ID de onde veio a requisição
    
    if request.method == 'POST':
        cliente_id_form = request.form.get('cliente_id')
        
        # Valida se o cliente_id_form está entre os clientes acessíveis
        cliente_id = int(cliente_id_form) if cliente_id_form else None
        if cliente_id is None or cliente_id not in accessible_client_ids:
            msg = 'Você não tem permissão para adicionar certificados a este cliente.'
            if is_modal_request:
                return jsonify({'success': False, 'message': msg}), 403
            flash(msg, 'danger')
            return render_template('admin_certificados_form.html', clientes=clientes_disponiveis, form_data=request.form, return_client_id=return_client_id)
        
        success, cert_obj = process_certificate_upload(db, cliente_id, request.form, request.files)
        
        if success and cert_obj:
            try:
                db.commit()
                msg = 'Certificado cadastrado com sucesso!'
                if is_modal_request:
                    return jsonify({'success': True, 'message': msg, 'redirect_url': url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='certificados') if return_client_id else url_for('admin_certificados_list')}), 201
                flash(msg, 'success')
                if return_client_id: # Se veio de uma aba de cliente, retorna para lá
                    return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='certificados'))
                return redirect(url_for('admin_certificados_list'))
            except IntegrityError as e:
                db.rollback()
                error_msg = f"Erro de integridade ao adicionar certificado: {e.orig}"
                if is_modal_request:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'danger')
            except Exception as e:
                db.rollback()
                error_msg = f"Erro ao adicionar certificado: {e}"
                if is_modal_request:
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'danger')
        else:
            db.rollback() # Garante rollback se process_certificate_upload falhar
            # A mensagem de erro já foi setada por process_certificate_upload
            error_msg = "Erro ao processar certificado." # Ou pega a mensagem do flash
            if is_modal_request:
                # Tenta pegar a mensagem do flash ou uma genérica
                flashed_messages = get_flashed_messages(with_categories=True)
                specific_error_msg = next((msg for cat, msg in flashed_messages if cat == 'danger'), error_msg)
                return jsonify({'success': False, 'message': specific_error_msg}), 400
    
    initial_form_data = request.form # Usa request.form para manter dados em caso de erro
    if return_client_id and not initial_form_data.get('cliente_id'):
        initial_form_data = initial_form_data.copy()
        initial_form_data['cliente_id'] = return_client_id
    if is_modal_request:
        # Renderiza apenas o conteúdo do formulário para o modal
        return render_template('admin_certificados_form_content.html', clientes=clientes_disponiveis, form_data=initial_form_data, return_client_id=return_client_id)
    else:
        # Renderiza a página completa se não for requisição de modal
        return render_template('admin_certificados_form.html', clientes=clientes_disponiveis, form_data=initial_form_data, return_client_id=return_client_id)
@app.route('/admin/certificados/edit/<int:certificado_digital_id>', methods=['GET', 'POST'])
@login_required
@permission_required('certificates.edit')
def admin_certificados_edit(certificado_digital_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    # Filtra o certificado pelo ID e pelos clientes acessíveis
    certificado = db.query(CertificadoDigital).filter(
        CertificadoDigital.certificado_digital_id == certificado_digital_id,
        CertificadoDigital.cliente_id.in_(accessible_client_ids)
    ).first()
    if not certificado:
        flash('Certificado não encontrado ou você não tem permissão para acessá-lo.', 'danger')
        return redirect(url_for('admin_clientes_list')) # Redireciona para lista de clientes ou certificates
    
    return_client_id = request.args.get('cliente_id', type=int) 
    if not return_client_id and certificado:
        return_client_id = certificado.cliente_id # Se não veio do form de cliente, pega o cliente do certificado
    clientes_disponiveis = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()

    if request.method == 'POST':
        # Permite alterar o cliente associado ao certificado, mas valida a permissão
        novo_cliente_id_form = request.form.get('cliente_id')
        novo_cliente_id = int(novo_cliente_id_form) if novo_cliente_id_form else None
        if novo_cliente_id is None or novo_cliente_id not in accessible_client_ids:
            flash('Você não tem permissão para associar o certificado a este cliente.', 'danger')
            # Retorna para o form, pré-preenchendo com os dados atuais e mensagens de erro
            return render_template('admin_certificados_form.html', certificado=certificado, clientes=clientes_disponiveis, form_data=request.form, return_client_id=return_client_id)
        
        certificado.cliente_id = novo_cliente_id
        certificado.nome_arquivo_original = request.form.get('cert_nome_arquivo_original')
        
        validade_inicio_str = request.form.get('cert_validade_inicio')
        validade_fim_str = request.form.get('cert_validade_fim')
        try:
            certificado.validade_inicio = datetime.strptime(validade_inicio_str, '%Y-%m-%d') if validade_inicio_str else None
            certificado.validade_fim = datetime.strptime(validade_fim_str, '%Y-%m-%d') if validade_fim_str else None
        except ValueError:
            flash('Formato de data inválido para o certificado. Use AAAA-MM-DD.', 'danger')
            return render_template('admin_certificados_form.html', certificado=certificado, clientes=clientes_disponiveis, form_data=request.form, return_client_id=return_client_id)
        
        certificado.ativo = request.form.get('cert_ativo') == 'on'
        
        new_password = request.form.get('cert_senha_certificado')
        if new_password:
            certificado.senha_certificado = new_password.encode('utf-8')
        
        try:
            db.commit()
            flash('Certificado atualizado com sucesso!', 'success')
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='certificados'))
            return redirect(url_for('admin_certificados_list'))
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar certificado: {e}", 'danger')
    
    cert_data = {
        'nome_arquivo_original': certificado.nome_arquivo_original,
        'validade_inicio': certificado.validade_inicio.strftime('%Y-%m-%d') if certificado.validade_inicio else '',
        'validade_fim': certificado.validade_fim.strftime('%Y-%m-%d') if certificado.validade_fim else '',
        'ativo': certificado.ativo,
        'cliente_id': certificado.cliente_id # Necessário para o dropdown
    }
    return render_template('admin_certificados_form.html', certificado=certificado, clientes=clientes_disponiveis, form_data=cert_data, return_client_id=return_client_id)
@app.route('/admin/certificados/delete/<int:certificado_digital_id>', methods=['POST'])
@login_required
@permission_required('certificates.delete')
def admin_certificados_delete(certificado_digital_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)

    certificado = db.query(CertificadoDigital).filter(
        CertificadoDigital.certificado_digital_id == certificado_digital_id,
        CertificadoDigital.cliente_id.in_(accessible_client_ids)
    ).first()
    if not certificado:
        flash('Certificado não encontrado ou você não tem permissão para excluí-lo.', 'danger')
        return redirect(url_for('admin_clientes_list'))
    
    cliente_id_redirect = certificado.cliente_id # Guarda para redirecionamento
    try:
        db.delete(certificado)
        db.commit()
        flash('Certificado excluído com sucesso!', 'success')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir certificado: {e}", 'danger')
    
    if cliente_id_redirect: # Se o certificado estava associado a um cliente, volta para a aba do cliente
        return redirect(url_for('admin_clientes_edit', cliente_id=cliente_id_redirect, _anchor='certificados'))
    return redirect(url_for('admin_certificados_list'))
# Rotas para Regimes Tributários (dados globais, não dependem de cliente_id)
@app.route('/admin/regimes_tributarios/list')
@login_required
@permission_required('regimes_tributarios.read')
def admin_regimes_tributarios_list():
    db = next(get_db())
    regimes = db.query(RegimeTributario).all()
    return render_template('admin_regimes_tributarios_list.html', regimes=regimes)
@app.route('/admin/regimes_tributarios/add', methods=['GET', 'POST'])
@login_required
@permission_required('regimes_tributarios.create')
def admin_regimes_tributarios_add():
    db = next(get_db())
    form_data = request.form
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        
        if not nome:
            flash('O nome do regime tributário é obrigatório.', 'danger')
            return render_template('admin_regimes_tributarios_form.html', form_data=form_data)
        try:
            novo_regime = RegimeTributario(nome=nome, descricao=descricao)
            db.add(novo_regime)
            db.commit()
            flash('Regime Tributário adicionado com sucesso!', 'success')
            return redirect(url_for('admin_regimes_tributarios_list'))
        except IntegrityError:
            db.rollback()
            flash('Nome do regime tributário já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar regime tributário: {e}", 'danger')
    
    return render_template('admin_regimes_tributarios_form.html', form_data=form_data)
@app.route('/admin/regimes_tributarios/edit/<int:regime_tributario_id>', methods=['GET', 'POST'])
@login_required
@permission_required('regimes_tributarios.edit')
def admin_regimes_tributarios_edit(regime_tributario_id):
    db = next(get_db())
    regime = db.query(RegimeTributario).get(regime_tributario_id)
    if not regime:
        abort(404)
    form_data = request.form
    if request.method == 'POST':
        regime.nome = request.form.get('nome')
        regime.descricao = request.form.get('descricao')
        
        if not regime.nome:
            flash('O nome do regime tributário é obrigatório.', 'danger')
            return render_template('admin_regimes_tributarios_form.html', regime=regime, form_data=form_data)
        try:
            db.commit()
            flash('Regime Tributário atualizado com sucesso!', 'success')
            return redirect(url_for('admin_regimes_tributarios_list'))
        except IntegrityError:
            db.rollback()
            flash('Nome do regime tributário já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar regime tributário: {e}", 'danger')
            
    return render_template('admin_regimes_tributarios_form.html', regime=regime, form_data=form_data)
@app.route('/admin/regimes_tributarios/delete/<int:regime_tributario_id>', methods=['POST'])
@login_required
@permission_required('regimes_tributarios.delete')
def admin_regimes_tributarios_delete(regime_tributario_id):
    db = next(get_db())
    regime = db.query(RegimeTributario).get(regime_tributario_id)
    if not regime:
        abort(404)
    try:
        db.delete(regime)
        db.commit()
        flash('Regime Tributário excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este regime tributário pois ele está vinculado a clientes.', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir regime tributário: {e}", 'danger')
    return redirect(url_for('admin_regimes_tributarios_list'))

# Rotas para Clientes
@app.route('/admin/clientes/list')
@login_required
@permission_required('clients.read')
def admin_clientes_list():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    clientes = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    return render_template('admin_clientes_list.html', clientes=clientes)
@app.route('/admin/clientes/add', methods=['GET', 'POST'])
@login_required
@permission_required('clients.create')
def admin_clientes_add():
    db = next(get_db())
    regimes_tributarios = db.query(RegimeTributario).all()
    # Dados para dropdowns em produtos e regras (mesmo que o cliente ainda não exista, para o POST)
    ncms = db.query(Ncm).all()
    origens_mercadoria = db.query(OrigemMercadoria).all()
    cfops = db.query(Cfop).all()
    csts = db.query(Csticms).all()
    csosns = db.query(Csosnicms).all()
    form_data = request.form # Para manter dados do formulário em caso de erro
    if request.method == 'POST':
        cnpj = request.form.get('cnpj')
        razao_social = request.form.get('razao_social')
        nome_fantasia = request.form.get('nome_fantasia')
        inscricao_estadual = request.form.get('inscricao_estadual')
        inscricao_municipal = request.form.get('inscricao_municipal')
        regime_tributario_id = request.form.get('regime_tributario_id')
        cnae = request.form.get('cnae')
        logradouro = request.form.get('logradouro')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento')
        bairro = request.form.get('bairro')
        codigo_municipio = request.form.get('codigo_municipio')
        nome_municipio = request.form.get('nome_municipio')
        uf = request.form.get('uf')
        cep = request.form.get('cep')
        email_contato = request.form.get('email_contato')
        telefone_contato = request.form.get('telefone_contato')
        ativo = request.form.get('ativo') == 'on'
        
        # Validação simples para os dados do cliente
        if not all([cnpj, razao_social, regime_tributario_id, logradouro, numero, bairro, codigo_municipio, nome_municipio, uf, cep]):
            flash('Por favor, preencha todos os campos obrigatórios do cliente.', 'danger')
            return render_template('admin_clientes_form.html', 
                                   regimes_tributarios=regimes_tributarios, 
                                   ncms=ncms, 
                                   origens_mercadoria=origens_mercadoria, 
                                   cfops=cfops, csts=csts, csosns=csosns, 
                                   form_data=form_data, # Passa os dados do form para re-preencher
                                   cliente={}, # Cliente vazio para novo cadastro
                                   # Não passa os *_existentes para novo cliente
                                   )
        
        try:
            regime_tributario_id = int(regime_tributario_id)
            novo_cliente = Cliente(
                cnpj=cnpj,
                razao_social=razao_social,
                nome_fantasia=nome_fantasia,
                inscricao_estadual=inscricao_estadual,
                inscricao_municipal=inscricao_municipal,
                regime_tributario_id=regime_tributario_id,
                cnae=cnae,
                logradouro=logradouro,
                numero=numero,
                complemento=complemento,
                bairro=bairro,
                codigo_municipio=codigo_municipio,
                nome_municipio=nome_municipio,
                uf=uf,
                cep=cep,
                email_contato=email_contato,
                telefone_contato=telefone_contato,
                ativo=ativo,
                data_cadastro=datetime.now(),
                data_atualizacao=datetime.now(),
                created_by_user_id=current_user.id # Auditoria
            )
            db.add(novo_cliente)
            db.flush() # flush para obter o cliente_id
            # Vincula o usuário atual ao cliente recém-criado
            user_client = UserClient(user_id=current_user.id, client_id=novo_cliente.cliente_id)
            db.add(user_client)
# Processa o upload do certificado, se houver (apenas para o primeiro certificado na criação)
            success_cert, cert_obj = process_certificate_upload(db, novo_cliente.cliente_id, request.form, request.files)
            if not success_cert:
                db.rollback() 
                return render_template('admin_clientes_form.html', regimes_tributarios=regimes_tributarios, ncms=ncms, origens_mercadoria=origens_mercadoria, cfops=cfops, csts=csts, csosns=csosns, form_data=form_data, cliente={}) # Volta com os dados preenchidos
            
            db.commit()
            flash('Cliente e configurações iniciais cadastrados com sucesso!', 'success')
            return redirect(url_for('admin_clientes_edit', cliente_id=novo_cliente.cliente_id)) 
        except IntegrityError as e:
            db.rollback()
            error_message = f"Erro de integridade: {e.orig}"
            if "duplicate key value violates unique constraint" in str(e.orig) and "cnpj" in str(e.orig):
                error_message = "Erro: CNPJ já cadastrado."
            flash(error_message, 'danger')
        except ValueError as e:
            db.rollback()
            flash(f"Erro de formato: {e}. Verifique os campos numéricos e de IDs.", 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro interno ao cadastrar cliente: {e}", 'danger')
        
    return render_template('admin_clientes_form.html', 
                           regimes_tributarios=regimes_tributarios, 
                           ncms=ncms,
                           origens_mercadoria=origens_mercadoria,
                           cfops=cfops, csts=csts, csosns=csosns,
                           form_data=form_data, # Passa os dados do form para re-preencher
                           cliente={}, # Cliente vazio para novo cadastro
                           )
@app.route('/admin/clientes/edit/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
@permission_required('clients.edit')
def admin_clientes_edit(cliente_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    cliente = db.query(Cliente).filter(
        Cliente.cliente_id == cliente_id,
        Cliente.cliente_id.in_(accessible_client_ids)
    ).first()
    if not cliente:
        flash('Cliente não encontrado ou você não tem permissão para acessá-lo.', 'danger')
        return redirect(url_for('admin_clientes_list'))
    
    # Dados para as abas
    regimes_tributarios = db.query(RegimeTributario).all()
    certificados_existentes = db.query(CertificadoDigital).filter_by(cliente_id=cliente_id).all()
    # ATUALIZADO: Carregar novos relacionamentos para Produtos para o template
    produtos_existentes = db.query(Produto).filter_by(cliente_id=cliente_id).options(
        joinedload(Produto.ncm), 
        joinedload(Produto.cfop),
        joinedload(Produto.origem),
        joinedload(Produto.csts_icms),
        joinedload(Produto.csosns_icms)
    ).all()
    regras_existentes = db.query(RegraTributacao).filter_by(cliente_id=cliente_id).all()
    destinatarios_existentes = db.query(DestinatarioNFe).filter_by(cliente_id=cliente_id).all()
# Dados para os dropdowns dentro das abas de Produtos e Regras Tributárias
    ncms = db.query(Ncm).all()
    origens_mercadoria = db.query(OrigemMercadoria).all()
    cfops = db.query(Cfop).all()
    csts = db.query(Csticms).all()
    csosns = db.query(Csosnicms).all()
    motivos_desoneracao = db.query(MotivoDesoneracao).order_by(MotivoDesoneracao.codigo).all()
    form_data = request.form # Para manter dados do formulário em caso de erro
    if request.method == 'POST':
        # Atualiza os dados do cliente
        cliente.cnpj = request.form.get('cnpj')
        cliente.razao_social = request.form.get('razao_social')
        cliente.nome_fantasia = request.form.get('nome_fantasia')
        cliente.inscricao_estadual = request.form.get('inscricao_estadual')
        cliente.inscricao_municipal = request.form.get('inscricao_municipal')
        cliente.regime_tributario_id = int(request.form.get('regime_tributario_id'))
        cliente.cnae = request.form.get('cnae')
        cliente.logradouro = request.form.get('logradouro')
        cliente.numero = request.form.get('numero')
        cliente.complemento = request.form.get('complemento')
        cliente.bairro = request.form.get('bairro')
        cliente.codigo_municipio = request.form.get('codigo_municipio')
        cliente.nome_municipio = request.form.get('nome_municipio')
        cliente.uf = request.form.get('uf')
        cliente.cep = request.form.get('cep')
        cliente.email_contato = request.form.get('email_contato')
        cliente.telefone_contato = request.form.get('telefone_contato')
        cliente.ativo = request.form.get('ativo') == 'on'
        cliente.data_atualizacao = datetime.now()
        # Validação simples para os dados do cliente
        if not all([cliente.cnpj, cliente.razao_social, cliente.regime_tributario_id, cliente.logradouro, cliente.numero, cliente.bairro, cliente.codigo_municipio, cliente.nome_municipio, cliente.uf, cliente.cep]):
            flash('Por favor, preencha todos os campos obrigatórios do cliente.', 'danger')
            return render_template('admin_clientes_form.html', 
                                   cliente=cliente, 
                                   regimes_tributarios=regimes_tributarios, 
                                   certificados_existentes=certificados_existentes, # Passa para re-renderizar abas
                                   produtos_existentes=produtos_existentes, 
                                   regras_existentes=regras_existentes, 
                                   destinatarios_existentes=destinatarios_existentes,
                                   ncms=ncms, origens_mercadoria=origens_mercadoria,
                                   cfops=cfops, csts=csts, csosns=csosns, 
                                   motivos_desoneracao=motivos_desoneracao,
                                   form_data=request.form # Usa request.form para manter o que o usuário digitou
                                   )
        try:
            # Processa o upload do certificado, se houver (lógica existente)
            # Este é para o caso de um NOVO certificado ser adicionado via o campo de upload na aba de cliente.
            # Se for para editar um certificado existente, a rota admin_certificados_edit cuidará disso.
            success_cert, cert_obj = process_certificate_upload(db, cliente_id, request.form, request.files)
            if not success_cert:
                db.rollback() 
                # Re-carrega dados para o template, pois db.rollback() desfaz o estado do cliente
                certificados_existentes = db.query(CertificadoDigital).filter_by(cliente_id=cliente_id).all() 
                produtos_existentes = db.query(Produto).filter_by(cliente_id=cliente_id).all() 
                regras_existentes = db.query(RegraTributacao).filter_by(cliente_id=cliente_id).all() 
                destinatarios_existentes = db.query(DestinatarioNFe).filter_by(cliente_id=cliente_id).all()
                return render_template('admin_clientes_form.html', 
                                       cliente=cliente, 
                                       regimes_tributarios=regimes_tributarios, 
                                       certificados_existentes=certificados_existentes, 
                                       produtos_existentes=produtos_existentes, 
                                       regras_existentes=regras_existentes, 
                                       destinatarios_existentes=destinatarios_existentes,
                                       ncms=ncms, origens_mercadoria=origens_mercadoria, 
                                       cfops=cfops, csts=csts, csosns=csosns, 
                                       motivos_desoneracao=motivos_desoneracao,
                                       form_data=request.form)
            
            db.commit()
            flash('Cliente e configurações atualizados com sucesso!', 'success')
            return redirect(url_for('admin_clientes_edit', cliente_id=cliente_id)) 
        except IntegrityError as e:
            db.rollback()
            error_message = f"Erro de integridade: {e.orig}"
            if "duplicate key value violates unique constraint" in str(e.orig) and "cnpj" in str(e.orig):
                error_message = "Erro: CNPJ já cadastrado para outro cliente."
            flash(error_message, 'danger')
        except ValueError as e:
            db.rollback()
            flash(f"Erro de formato: {e}. Verifique os campos numéricos e de IDs.", 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro interno ao atualizar cliente: {e}", 'danger')
    
    # Para GET, use o objeto cliente para pré-preencher o formulário
    # form_data inicializa com os dados do cliente para preencher os campos do formulário
    return render_template('admin_clientes_form.html',
                           cliente=cliente,
                           regimes_tributarios=regimes_tributarios,
                           certificados_existentes=certificados_existentes,
                           produtos_existentes=produtos_existentes, 
                           regras_existentes=regras_existentes, 
                           destinatarios_existentes=destinatarios_existentes,
                           ncms=ncms, origens_mercadoria=origens_mercadoria, 
                           cfops=cfops, csts=csts, csosns=csosns, 
                           motivos_desoneracao=motivos_desoneracao,
                           form_data=cliente) # Usa o objeto cliente para preencher o formulário na carga inicial
@app.route('/admin/clientes/delete/<int:cliente_id>', methods=['POST'])
@login_required
@permission_required('clients.delete')
def admin_clientes_delete(cliente_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)

    cliente = db.query(Cliente).filter(
        Cliente.cliente_id == cliente_id,
        Cliente.cliente_id.in_(accessible_client_ids)
    ).first()

    if not cliente:
        flash('Cliente não encontrado ou você não tem permissão para excluí-lo.', 'danger')
        return redirect(url_for('admin_clientes_list'))
    try:
        # Primeiro, excluímos registros dependentes (se não houver cascade delete configurado no DB)
        # SQLAlchemy pode fazer isso automaticamente com cascade, mas explicitamente é mais seguro
        db.query(CertificadoDigital).filter_by(cliente_id=cliente_id).delete()
        db.query(Produto).filter_by(cliente_id=cliente_id).delete()
        db.query(RegraTributacao).filter_by(cliente_id=cliente_id).delete()
        db.query(DestinatarioNFe).filter_by(cliente_id=cliente_id).delete()
        db.query(UserClient).filter_by(client_id=cliente_id).delete() # Remove a associação do cliente com usuários
        # Cuidado: NFeEmitidas também depende de cliente_id. Se quiser excluir tudo, deve ser feito aqui ou via cascade.
        # db.query(NFeEmitidas).filter_by(cliente_id=cliente_id).delete()
        db.delete(cliente)
        db.commit()
        flash('Cliente e dados associados excluídos com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este cliente pois ele ainda está vinculado a outros registros (ex: NF-e).', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir cliente: {e}", 'danger')
    return redirect(url_for('admin_clientes_list'))

# --- Rotas para NCM (dados globais) ---
@app.route('/admin/ncms/list')
@login_required
@permission_required('ncms.read')
def admin_ncms_list():
    db = next(get_db())
    ncms = db.query(Ncm).all()
    return render_template('admin_ncms_list.html', ncms=ncms)
@app.route('/admin/ncms/add', methods=['GET', 'POST'])
@login_required
@permission_required('ncms.create')
def admin_ncms_add():
    db = next(get_db())
    form_data = request.form
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        data_inicio_str = request.form.get('data_Inicio')
        data_fim_str = request.form.get('data_Fim')
        tipo_ato = request.form.get('tipo_ato')
        numero_ato = request.form.get('numero_ato')
        ano_ato = request.form.get('ano_ato')
        if not all([codigo, descricao]):
            flash('Código e Descrição são campos obrigatórios para NCM.', 'danger')
            return render_template('admin_ncms_form.html', form_data=form_data)
        
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date() if data_inicio_str else None
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else None
            
            novo_ncm = Ncm(
                codigo=codigo,
                descricao=descricao,
                data_Inicio=data_inicio,
                data_Fim=data_fim,
                tipo_ato=tipo_ato,
                numero_ato=numero_ato,
                ano_ato=ano_ato,
                created_by_user_id=current_user.id # Auditoria
            )
            db.add(novo_ncm)
            db.commit()
            flash('NCM adicionado com sucesso!', 'success')
            return redirect(url_for('admin_ncms_list'))
        except IntegrityError:
            db.rollback()
            flash('Código NCM já existe.', 'danger')
        except ValueError:
            db.rollback()
            flash('Formato de data inválido. Use AAAA-MM-DD.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar NCM: {e}", 'danger')
    return render_template('admin_ncms_form.html', form_data=form_data)
@app.route('/admin/ncms/edit/<int:ncm_id>', methods=['GET', 'POST'])
@login_required
@permission_required('ncms.edit')
def admin_ncms_edit(ncm_id):
    db = next(get_db())
    ncm = db.query(Ncm).get(ncm_id)
    if not ncm:
        abort(404)
    form_data = request.form
    if request.method == 'POST':
        ncm.codigo = request.form.get('codigo')
        ncm.descricao = request.form.get('descricao')
        data_inicio_str = request.form.get('data_Inicio')
        data_fim_str = request.form.get('data_Fim')
        ncm.tipo_ato = request.form.get('tipo_ato')
        ncm.numero_ato = request.form.get('numero_ato')
        ncm.ano_ato = request.form.get('ano_ato')
        if not all([ncm.codigo, ncm.descricao]):
            flash('Código e Descrição são campos obrigatórios para NCM.', 'danger')
            return render_template('admin_ncms_form.html', ncm=ncm, form_data=form_data)
        
        try:
            ncm.data_Inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date() if data_inicio_str else None
            ncm.data_Fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else None
            db.commit()
            flash('NCM atualizado com sucesso!', 'success')
            return redirect(url_for('admin_ncms_list'))
        except IntegrityError:
            db.rollback()
            flash('Código NCM já existe.', 'danger')
        except ValueError:
            db.rollback()
            flash('Formato de data inválido. Use AAAA-MM-DD.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar NCM: {e}", 'danger')
    return render_template('admin_ncms_form.html', ncm=ncm, form_data=ncm)
@app.route('/admin/ncms/delete/<int:ncm_id>', methods=['POST'])
@login_required
@permission_required('ncms.delete')
def admin_ncms_delete(ncm_id):
    db = next(get_db())
    ncm = db.query(Ncm).get(ncm_id)
    if not ncm:
        abort(404)
    try:
        db.delete(ncm)
        db.commit()
        flash('NCM excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este NCM pois ele está vinculado a outros registros (ex: Produtos).', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir NCM: {e}", 'danger')
    return redirect(url_for('admin_ncms_list'))
# --- Rotas para CST ICMS (dados globais) ---
@app.route('/admin/cst/list')
@login_required
@permission_required('cst.read')
def admin_cst_list():
    db = next(get_db())
    csts = db.query(Csticms).all()
    return render_template('admin_cst_list.html', csts=csts)
@app.route('/admin/cst/add', methods=['GET', 'POST'])
@login_required
@permission_required('cst.create')
def admin_cst_add():
    db = next(get_db())
    form_data = request.form
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        if not all([codigo, descricao]):
            flash('Código e Descrição são campos obrigatórios para CST ICMS.', 'danger')
            return render_template('admin_cst_form.html', form_data=form_data)
        
        try:
            novo_cst = Csticms(codigo=codigo, descricao=descricao)
            db.add(novo_cst)
            db.commit()
            flash('CST ICMS adicionado com sucesso!', 'success')
            return redirect(url_for('admin_cst_list'))
        except IntegrityError:
            db.rollback()
            flash('Código CST ICMS já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar CST ICMS: {e}", 'danger')
    return render_template('admin_cst_form.html', form_data=form_data)
@app.route('/admin/cst/edit/<int:cst_id>', methods=['GET', 'POST'])
@login_required
@permission_required('cst.edit')
def admin_cst_edit(cst_id):
    db = next(get_db())
    cst = db.query(Csticms).get(cst_id)
    if not cst:
        abort(404)
    form_data = request.form
    if request.method == 'POST':
        cst.codigo = request.form.get('codigo')
        cst.descricao = request.form.get('descricao')
        if not all([cst.codigo, cst.descricao]):
            flash('Código e Descrição são campos obrigatórios para CST ICMS.', 'danger')
            return render_template('admin_cst_form.html', cst=cst, form_data=form_data)
        
        try:
            db.commit()
            flash('CST ICMS atualizado com sucesso!', 'success')
            return redirect(url_for('admin_cst_list'))
        except IntegrityError:
            db.rollback()
            flash('Código CST ICMS já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar CST ICMS: {e}", 'danger')
    return render_template('admin_cst_form.html', cst=cst, form_data=cst)
@app.route('/admin/cst/delete/<int:cst_id>', methods=['POST'])
@login_required
@permission_required('cst.delete')
def admin_cst_delete(cst_id):
    db = next(get_db())
    cst = db.query(Csticms).get(cst_id)
    if not cst:
        abort(404)
    try:
        db.delete(cst)
        db.commit()
        flash('CST ICMS excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este CST ICMS pois ele está vinculado a outros registros.', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir CST ICMS: {e}", 'danger')
    return redirect(url_for('admin_cst_list'))
# --- Rotas para CFOP (dados globais) ---
@app.route('/admin/cfops/list')
@login_required
@permission_required('cfops.read')
def admin_cfops_list():
    db = next(get_db())
    cfops = db.query(Cfop).all()
    return render_template('admin_cfops_list.html', cfops=cfops)
@app.route('/admin/cfops/add', methods=['GET', 'POST'])
@login_required
@permission_required('cfops.create')
def admin_cfops_add():
    db = next(get_db())
    form_data = request.form
    if request.method == 'POST':
        cfop_code = request.form.get('cfop')
        descricao = request.form.get('descricao')
        observacao = request.form.get('observacao')
        tipooperacao = request.form.get('tipooperacao')
        identificadordestinooperacao = request.form.get('identificadordestinooperacao')
        if not all([cfop_code, descricao, observacao]):
            flash('CFOP, Descrição e Observação são campos obrigatórios.', 'danger')
            return render_template('admin_cfops_form.html', form_data=form_data)
        
        try:
            novo_cfop = Cfop(
                cfop=cfop_code,
                descricao=descricao,
                observacao=observacao,
                tipooperacao=tipooperacao,
                identificadordestinooperacao=identificadordestinooperacao
            )
            db.add(novo_cfop)
            db.commit()
            flash('CFOP adicionado com sucesso!', 'success')
            return redirect(url_for('admin_cfops_list'))
        except IntegrityError:
            db.rollback()
            flash('Código CFOP já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar CFOP: {e}", 'danger')
    return render_template('admin_cfops_form.html', form_data=form_data)
@app.route('/admin/cfops/edit/<int:cfop_id>', methods=['GET', 'POST'])
@login_required
@permission_required('cfops.edit')
def admin_cfops_edit(cfop_id):
    db = next(get_db())
    cfop_obj = db.query(Cfop).get(cfop_id)
    if not cfop_obj:
        abort(404)
    form_data = request.form
    if request.method == 'POST':
        cfop_obj.cfop = request.form.get('cfop')
        cfop_obj.descricao = request.form.get('descricao')
        cfop_obj.observacao = request.form.get('observacao')
        cfop_obj.tipooperacao = request.form.get('tipooperacao')
        cfop_obj.identificadordestinooperacao = request.form.get('identificadordestinooperacao')
        if not all([cfop_obj.cfop, cfop_obj.descricao, cfop_obj.observacao]):
            flash('CFOP, Descrição e Observação são campos obrigatórios.', 'danger')
            return render_template('admin_cfops_form.html', cfop=cfop_obj, form_data=form_data)
        
        try:
            db.commit()
            flash('CFOP atualizado com sucesso!', 'success')
            return redirect(url_for('admin_cfops_list'))
        except IntegrityError:
            db.rollback()
            flash('Código CFOP já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar CFOP: {e}", 'danger')
    return render_template('admin_cfops_form.html', cfop=cfop_obj, form_data=cfop_obj)
@app.route('/admin/cfops/delete/<int:cfop_id>', methods=['POST'])
@login_required
@permission_required('cfops.delete')
def admin_cfops_delete(cfop_id):
    db = next(get_db())
    cfop_obj = db.query(Cfop).get(cfop_id)
    if not cfop_obj:
        abort(404)
    try:
        db.delete(cfop_obj)
        db.commit()
        flash('CFOP excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este CFOP pois ele está vinculado a outros registros (ex: Regras de Tributação).', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir CFOP: {e}", 'danger')
    return redirect(url_for('admin_cfops_list'))
# --- Rotas para CSOSN ICMS (dados globais) ---
@app.route('/admin/csosn/list')
@login_required
@permission_required('csosn.read')
def admin_csosn_list():
    db = next(get_db())
    csosns = db.query(Csosnicms).all()
    return render_template('admin_csosn_list.html', csosns=csosns)
@app.route('/admin/csosn/add', methods=['GET', 'POST'])
@login_required
@permission_required('csosn.create')
def admin_csosn_add():
    db = next(get_db())
    form_data = request.form
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        if not all([codigo, descricao]):
            flash('Código e Descrição são campos obrigatórios para CSOSN ICMS.', 'danger')
            return render_template('admin_csosn_form.html', form_data=form_data)
        
        try:
            novo_csosn = Csosnicms(codigo=codigo, descricao=descricao)
            db.add(novo_csosn)
            db.commit()
            flash('CSOSN ICMS adicionado com sucesso!', 'success')
            return redirect(url_for('admin_csosn_list'))
        except IntegrityError:
            db.rollback()
            flash('Código CSOSN ICMS já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar CSOSN ICMS: {e}", 'danger')
    return render_template('admin_csosn_form.html', form_data=form_data)
@app.route('/admin/csosn/edit/<int:csosn_id>', methods=['GET', 'POST'])
@login_required
@permission_required('csosn.edit')
def admin_csosn_edit(csosn_id):
    db = next(get_db())
    csosn = db.query(Csosnicms).get(csosn_id)
    if not csosn:
        abort(404)
    form_data = request.form
    if request.method == 'POST':
        csosn.codigo = request.form.get('codigo')
        csosn.descricao = request.form.get('descricao')
        if not all([csosn.codigo, csosn.descricao]):
            flash('Código e Descrição são campos obrigatórios para CSOSN ICMS.', 'danger')
            return render_template('admin_csosn_form.html', csosn=csosn, form_data=form_data)
        
        try:
            db.commit()
            flash('CSOSN ICMS atualizado com sucesso!', 'success')
            return redirect(url_for('admin_csosn_list'))
        except IntegrityError:
            db.rollback()
            flash('Código CSOSN ICMS já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar CSOSN ICMS: {e}", 'danger')
    return render_template('admin_csosn_form.html', csosn=csosn, form_data=csosn)
@app.route('/admin/csosn/delete/<int:csosn_id>', methods=['POST'])
@login_required
@permission_required('csosn.delete')
def admin_csosn_delete(csosn_id):
    db = next(get_db())
    csosn = db.query(Csosnicms).get(csosn_id)
    if not csosn:
        abort(404)
    try:
        db.delete(csosn)
        db.commit()
        flash('CSOSN ICMS excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este CSOSN ICMS pois ele está vinculado a outros registros.', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir CSOSN ICMS: {e}", 'danger')
    return redirect(url_for('admin_csosn_list'))
# --- Rotas para Produtos ---
# A listagem geral continua aqui, mas não no menu
@app.route('/admin/produtos/list')
@login_required
@permission_required('products.read')
def admin_produtos_list():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    produtos = db.query(Produto).filter(Produto.cliente_id.in_(accessible_client_ids)).all()
    # Adicionando clientes para exibir no template
    clientes = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    cliente_map = {c.cliente_id: c.razao_social for c in clientes}
    return render_template('admin_produtos_list.html', produtos=produtos, cliente_map=cliente_map)

# Rota de Adição de Produto - Suporta requisição normal e AJAX para modal
@app.route('/admin/produtos/add', methods=['GET', 'POST'])
@login_required
@permission_required('products.create')
def admin_produtos_add():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    clientes_disponiveis = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    
    ncms = db.query(Ncm).all()
    origens = db.query(OrigemMercadoria).all()
    cfops = db.query(Cfop).all() # CARREGAR PARA DROPDOWNS
    csts_icms = db.query(Csticms).all() # CARREGAR PARA DROPDOWNS
    csosns_icms = db.query(Csosnicms).all() # CARREGAR PARA DROPDOWNS

    is_modal_request = request.args.get('modal', 'false').lower() == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    return_client_id = request.args.get('cliente_id', type=int)
    
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        codigo_interno = request.form.get('codigo_interno')
        descricao = request.form.get('descricao')
        ncm_id = request.form.get('ncm_id')
        cest = request.form.get('cest')
        unidade_comercial = request.form.get('unidade_comercial')
        preco_unitario_padrao_str = request.form.get('preco_unitario_padrao')
        origem_mercadoria = request.form.get('origem_mercadoria')
        tipo_item = request.form.get('tipo_item')
        ativo = request.form.get('ativo') == 'on'
        # --- NOVOS CAMPOS ---
        cfop_id = request.form.get('cfop_id')
        cst_id = request.form.get('cst_id')
        csosn_id = request.form.get('csosn_id')
        # --------------------
        
        if not all([cliente_id, codigo_interno, descricao, unidade_comercial, preco_unitario_padrao_str, origem_mercadoria, tipo_item]):
            msg = 'Por favor, preencha todos os campos obrigatórios do produto.'
            if is_modal_request:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'danger')
            print("CSTs disponíveis1:", [(c.cst_id, c.codigo, c.descricao) for c in csts_icms])
            return render_template('admin_produtos_form.html', clientes=clientes_disponiveis, ncms=ncms, origens=origens, cfops=cfops, csts_icms=csts_icms, csosns_icms=csosns_icms, form_data=request.form, return_client_id=return_client_id)
        
        try:
            cliente_id = int(cliente_id)
            if cliente_id not in accessible_client_ids:
                msg = 'Você não tem permissão para adicionar produtos a este cliente.'
                if is_modal_request:
                    return jsonify({'success': False, 'message': msg}), 403
                flash(msg, 'danger')
                print("CSTs disponíveis2:", [(c.cst_id, c.codigo, c.descricao) for c in csts_icms])
                return render_template('admin_produtos_form.html', clientes=clientes_disponiveis, ncms=ncms, origens=origens, cfops=cfops, csts_icms=csts_icms, csosns_icms=csosns_icms, form_data=request.form, return_client_id=return_client_id)
            
            ncm_id = int(ncm_id) if ncm_id else None
            preco_unitario_padrao = Decimal(preco_unitario_padrao_str)
            origem_mercadoria = int(origem_mercadoria)

            # --- PROCESSAR NOVOS CAMPOS ---
            cfop_id = int(cfop_id) if cfop_id else None
            cst_id = int(cst_id) if cst_id else None
            csosn_id = int(csosn_id) if csosn_id else None
            # ------------------------------

            novo_produto = Produto(
                cliente_id=cliente_id,
                codigo_interno=codigo_interno,
                descricao=descricao,
                ncm_id=ncm_id,
                cest=cest,
                unidade_comercial=unidade_comercial,
                preco_unitario_padrao=preco_unitario_padrao,
                origem_mercadoria=origem_mercadoria,
                tipo_item=tipo_item,
                ativo=ativo,
                cfop_id=cfop_id, # NOVO
                cst_id=cst_id, # NOVO
                csosn_id=csosn_id, # NOVO
                created_by_user_id=current_user.id
            )
            db.add(novo_produto)
            db.commit()
            msg = 'Produto adicionado com sucesso!'
            if is_modal_request:
                return jsonify({'success': True, 'message': msg, 'redirect_url': url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='produtos') if return_client_id else url_for('admin_produtos_list')}), 201
            flash(msg, 'success')
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='produtos'))
            return redirect(url_for('admin_produtos_list'))
        except IntegrityError:
            db.rollback()
            error_msg = 'Código Interno do produto já existe para este cliente.'
            if is_modal_request:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
        except ValueError as e:
            db.rollback()
            error_msg = f'Erro de formato: {e}. Verifique os campos numéricos e de IDs.'
            if is_modal_request:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
        except Exception as e:
            db.rollback()
            error_msg = f"Erro ao adicionar produto: {e}"
            if is_modal_request:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
    
    initial_form_data = request.form
    if return_client_id and not initial_form_data.get('cliente_id'):
        initial_form_data = initial_form_data.copy()
        initial_form_data['cliente_id'] = return_client_id
    print("CSTs disponíveis3:", [(c.cst_id, c.codigo, c.descricao) for c in csts_icms])
    if is_modal_request:
        return render_template('admin_produtos_form_modal.html', 
                            clientes=clientes_disponiveis, 
                            ncms=ncms, 
                            origens=origens, 
                            cfops=cfops, 
                            csts_icms=csts_icms,  # Alterado aqui
                            csosns_icms=csosns_icms,  # Alterado aqui
                            form_data=initial_form_data, 
                            return_client_id=return_client_id)
    else:
        return render_template('admin_produtos_form.html', 
                            clientes=clientes_disponiveis, 
                            ncms=ncms, 
                            origens=origens, 
                            cfops=cfops, 
                            csts_icms=csts_icms,  # Alterado aqui
                            csosns_icms=csosns_icms,  # Alterado aqui
                            form_data=initial_form_data, 
                            return_client_id=return_client_id)

@app.route('/admin/produtos/edit/<int:produto_id>', methods=['GET', 'POST'])
@login_required
@permission_required('products.edit')
def admin_produtos_edit(produto_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)

    produto = db.query(Produto).filter(
        Produto.produto_id == produto_id,
        Produto.cliente_id.in_(accessible_client_ids)
    ).first()
    if not produto:
        flash('Produto não encontrado ou você não tem permissão para acessá-lo.', 'danger')
        return redirect(url_for('admin_produtos_list'))
    
    return_client_id = request.args.get('cliente_id', type=int) 
    if not return_client_id and produto:
        return_client_id = produto.cliente_id

    clientes_disponiveis = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    ncms = db.query(Ncm).all()
    origens = db.query(OrigemMercadoria).all()
    cfops = db.query(Cfop).all() # CARREGAR PARA DROPDOWNS
    csts_icms = db.query(Csticms).all() # CARREGAR PARA DROPDOWNS
    csosns_icms = db.query(Csosnicms).all() # CARREGAR PARA DROPDOWNS
    form_data = request.form
    if request.method == 'POST':
        novo_cliente_id = int(request.form.get('cliente_id'))
        
        if novo_cliente_id not in accessible_client_ids:
            flash('Você não tem permissão para mover o produto para este cliente.', 'danger')
            return render_template('admin_produtos_form.html', produto=produto, clientes=clientes_disponiveis, ncms=ncms, origens=origens, cfops=cfops, csts_icms=csts_icms,  # Alterado aqui
                            csosns_icms=csosns_icms, form_data=form_data, return_client_id=return_client_id)
        
        produto.cliente_id = novo_cliente_id
        produto.codigo_interno = request.form.get('codigo_interno')
        produto.descricao = request.form.get('descricao')
        produto.ncm_id = int(request.form.get('ncm_id')) if request.form.get('ncm_id') else None
        produto.cest = request.form.get('cest')
        produto.unidade_comercial = request.form.get('unidade_comercial')
        preco_unitario_padrao = request.form.get('preco_unitario_padrao')
        produto.origem_mercadoria = int(request.form.get('origem_mercadoria'))
        produto.tipo_item = request.form.get('tipo_item')
        produto.ativo = request.form.get('ativo') == 'on'
        # --- ATUALIZAR NOVOS CAMPOS ---
        produto.cfop_id = int(request.form.get('cfop_id')) if request.form.get('cfop_id') else None
        produto.cst_id = int(request.form.get('cst_id')) if request.form.get('cst_id') else None
        produto.csosn_id = int(request.form.get('csosn_id')) if request.form.get('csosn_id') else None
        # ------------------------------
        if not all([produto.cliente_id, produto.codigo_interno, produto.descricao, produto.unidade_comercial, preco_unitario_padrao, produto.origem_mercadoria, produto.tipo_item]):
            flash('Por favor, preencha todos os campos obrigatórios do produto.', 'danger')
            return render_template('admin_produtos_form.html', produto=produto, clientes=clientes_disponiveis, ncms=ncms, origens=origens, cfops=cfops, csts_icms=csts_icms,  # Alterado aqui
                            csosns_icms=csosns_icms, form_data=form_data, return_client_id=return_client_id)
        
        try:
            produto.preco_unitario_padrao = Decimal(preco_unitario_padrao)
            db.commit()
            flash('Produto atualizado com sucesso!', 'success')
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='produtos'))
            return redirect(url_for('admin_produtos_list'))
        except IntegrityError:
            db.rollback()
            flash('Código Interno do produto já existe para este cliente.', 'danger')
        except ValueError as e:
            db.rollback()
            flash(f"Erro de formato: {e}. Verifique os campos numéricos e de IDs.", 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar produto: {e}", 'danger')
    return render_template('admin_produtos_form.html', produto=produto, clientes=clientes_disponiveis, ncms=ncms, origens=origens, cfops=cfops, csts_icms=csts_icms,  # Alterado aqui
                            csosns_icms=csosns_icms, form_data=produto, return_client_id=return_client_id)
@app.route('/admin/produtos/delete/<int:produto_id>', methods=['POST'])
@login_required
@permission_required('products.delete')
def admin_produtos_delete(produto_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    produto = db.query(Produto).filter(
        Produto.produto_id == produto_id,
        Produto.cliente_id.in_(accessible_client_ids)
    ).first()
    if not produto:
        flash('Produto não encontrado ou você não tem permissão para excluí-lo.', 'danger')
        return redirect(url_for('admin_produtos_list'))
    
    return_client_id = produto.cliente_id
    try:
        db.delete(produto)
        db.commit()
        flash('Produto excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este produto pois ele está vinculado a outros registros.', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir produto: {e}", 'danger')
    
    if return_client_id: # Se o produto estava associado a um cliente, volta para a aba do cliente
        return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='produtos'))
    return redirect(url_for('admin_produtos_list'))
# --- Rotas para Regras de Tributação ---
# A listagem geral continua aqui, mas não no menu
@app.route('/admin/regras_tributacao/list')
@login_required
@permission_required('rules.read')
def admin_regras_tributacao_list():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    # Regras podem ser globais (cliente_id is NULL) ou específicas de cliente.
    # Um admin pode ver todas, um usuário comum, apenas as globais e as dos clientes que ele acessa.
    regras = db.query(RegraTributacao).filter(
        (RegraTributacao.cliente_id.is_(None)) | (RegraTributacao.cliente_id.in_(accessible_client_ids))
    ).all()
    # Adicionando clientes para exibir no template
    clientes = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    cliente_map = {c.cliente_id: c.razao_social for c in clientes}
    return render_template('admin_regras_tributacao_list.html', regras=regras, cliente_map=cliente_map)
# Rota de Adição de Regra Tributária - Suporta requisição normal e AJAX para modal
@app.route('/admin/regras_tributacao/add', methods=['GET', 'POST'])
@login_required
@permission_required('rules.create')
def admin_regras_tributacao_add():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    clientes_disponiveis = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    
    regimes_tributarios = db.query(RegimeTributario).all()
    cfops = db.query(Cfop).all()
    ncms = db.query(Ncm).all()
    csts = db.query(Csticms).all()
    csosns = db.query(Csosnicms).all()
    motivos_desoneracao = db.query(MotivoDesoneracao).order_by(MotivoDesoneracao.codigo).all()
    
    # Verifica se a requisição veio de um modal (AJAX)
    is_modal_request = request.args.get('modal', 'false').lower() == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    return_client_id = request.args.get('cliente_id', type=int) 
    
    if request.method == 'POST':
        cliente_id_form = request.form.get('cliente_id')
        regime_tributario_id = request.form.get('regime_tributario_id')
        cfop_id = request.form.get('cfop_id')
        ncm_id = request.form.get('ncm_id')
        uf_origem = request.form.get('uf_origem')
        uf_destino = request.form.get('uf_destino')
        tipo_item = request.form.get('tipo_item')
        prioridade_str = request.form.get('prioridade')
        # csts_icms = request.form.get('csts_icms')
        # csosns_icms = request.form.get('csosns_icms')
        aliquota_icms_str = request.form.get('aliquota_icms')
        reducao_base_icms_str = request.form.get('reducao_base_icms')
        modalidade_bc_icms_str = request.form.get('modalidade_bc_icms')
        motivo_desoneracao_icms_str = request.form.get('motivo_desoneracao_icms')
        cst_pis = request.form.get('cst_pis')
        aliquota_pis_str = request.form.get('aliquota_pis')
        cst_cofins = request.form.get('cst_cofins')
        aliquota_cofins_str = request.form.get('aliquota_cofins')
        cst_ipi = request.form.get('cst_ipi')
        aliquota_ipi_str = request.form.get('aliquota_ipi')
        descricao_regra = request.form.get('descricao_regra')
        ativo = request.form.get('ativo') == 'on'
        
        if not all([regime_tributario_id, cfop_id]): # Campos minimos obrigatorios
            msg = 'Regime Tributário e CFOP são campos obrigatórios para Regra de Tributação.'
            if is_modal_request:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'danger')
            return render_template('admin_regras_tributacao_form.html', clientes=clientes_disponiveis, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, motivos_desoneracao=motivos_desoneracao, form_data=request.form, return_client_id=return_client_id)
        
        try:
            cliente_id = int(cliente_id_form) if cliente_id_form else None
            # Valida se o usuário tem permissão para adicionar a este cliente
            if cliente_id is not None and cliente_id not in accessible_client_ids:
                msg = 'Você não tem permissão para adicionar regras a este cliente.'
                if is_modal_request:
                    return jsonify({'success': False, 'message': msg}), 403
                flash(msg, 'danger')
                return render_template('admin_regras_tributacao_form.html', clientes=clientes_disponiveis, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, motivos_desoneracao=motivos_desoneracao, form_data=request.form, return_client_id=return_client_id)
            
            regime_tributario_id = int(regime_tributario_id)
            cfop_id = int(cfop_id)
            ncm_id = int(ncm_id) if ncm_id else None
            prioridade = int(prioridade_str) if prioridade_str else 100
            aliquota_icms = Decimal(aliquota_icms_str) if aliquota_icms_str else None
            reducao_base_icms = Decimal(reducao_base_icms_str) if reducao_base_icms_str else None
            modalidade_bc_icms = int(modalidade_bc_icms_str) if modalidade_bc_icms_str else None
            motivo_desoneracao_icms = int(motivo_desoneracao_icms_str) if motivo_desoneracao_icms_str else None
            aliquota_pis = Decimal(aliquota_pis_str) if aliquota_pis_str else None
            aliquota_cofins = Decimal(aliquota_cofins_str) if aliquota_cofins_str else None
            aliquota_ipi = Decimal(aliquota_ipi_str) if aliquota_ipi_str else None
            nova_regra = RegraTributacao(
                cliente_id=cliente_id,
                regime_tributario_id=regime_tributario_id,
                cfop_id=cfop_id,
                ncm_id=ncm_id,
                uf_origem=uf_origem,
                uf_destino=uf_destino,
                tipo_item=tipo_item,
                prioridade=prioridade,
                # cst_icms=csts_icms,
                # csosn_icms=csosn_icms,
                aliquota_icms=aliquota_icms,
                reducao_base_icms=reducao_base_icms,
                modalidade_bc_icms=modalidade_bc_icms,
                motivo_desoneracao_icms=motivo_desoneracao_icms,
                cst_pis=cst_pis,
                aliquota_pis=aliquota_pis,
                cst_cofins=cst_cofins,
                aliquota_cofins=aliquota_cofins,
                cst_ipi=cst_ipi,
                aliquota_ipi=aliquota_ipi,
                descricao_regra=descricao_regra,
                data_criacao=datetime.now(),
                ativo=ativo,
                created_by_user_id=current_user.id # Auditoria
            )
            db.add(nova_regra)
            db.commit()
            msg = 'Regra de Tributação adicionada com sucesso!'
            if is_modal_request:
                return jsonify({'success': True, 'message': msg, 'redirect_url': url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='regras') if return_client_id else url_for('admin_regras_tributacao_list')}), 201
            flash(msg, 'success')
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='regras'))
            return redirect(url_for('admin_regras_tributacao_list'))
        except IntegrityError as e:
            db.rollback()
            # Captura a mensagem de erro original do banco de dados para melhor depuração
            # e.orig contém o objeto de exceção do banco de dados subjacente (ex: psycopg2.IntegrityError)
            db_error_message = str(e.orig)
            # Tenta extrair uma mensagem mais amigável se for um erro comum de duplicidade
            if "duplicate key value violates unique constraint" in db_error_message:
                error_msg = f"Erro: Uma regra idêntica já existe. Detalhes: {db_error_message}"
            elif "violates foreign key constraint" in db_error_message:
                error_msg = f"Erro: Um dos IDs selecionados (Cliente, Regime, CFOP, NCM, etc.) não existe. Detalhes: {db_error_message}"
            else:
                error_msg = f"Erro de integridade ao adicionar regra: {db_error_message}. Verifique os dados fornecidos."
            
            current_app.logger.error(f"Integrity error when adding rule: {db_error_message}", exc_info=True)
            
            if is_modal_request:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
        except ValueError as e:
            db.rollback()
            error_msg = f'Erro de formato: {e}. Verifique os campos numéricos e de IDs.'
            if is_modal_request:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
        except Exception as e:
            db.rollback()
            error_msg = f"Erro ao adicionar Regra de Tributação: {e}"
            if is_modal_request:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
    
    # Renderiza o formulário (seja para o modal ou para a página completa)
    initial_form_data = request.form # Para manter dados em caso de erro
    if return_client_id and not initial_form_data.get('cliente_id'):
        initial_form_data = initial_form_data.copy()
        initial_form_data['cliente_id'] = return_client_id
# ONDE A MUDANÇA OCORRE: Renderiza o template correto dependendo se é modal ou não
    if is_modal_request:
        # Renderiza o NOVO template específico para o modal
        return render_template('admin_regras_tributacao_form_modal.html', clientes=clientes_disponiveis, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, motivos_desoneracao=motivos_desoneracao, form_data=initial_form_data, return_client_id=return_client_id)
    else:
        # Renderiza a página completa
        return render_template('admin_regras_tributacao_form.html', clientes=clientes_disponiveis, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, motivos_desoneracao=motivos_desoneracao, form_data=initial_form_data, return_client_id=return_client_id)
    
@app.route('/admin/regras_tributacao/edit/<int:regra_tributacao_id>', methods=['GET', 'POST'])
@login_required
@permission_required('rules.edit')
def admin_regras_tributacao_edit(regra_tributacao_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    regra = db.query(RegraTributacao).filter(
        RegraTributacao.regra_tributacao_id == regra_tributacao_id,
        (RegraTributacao.cliente_id.is_(None)) | (RegraTributacao.cliente_id.in_(accessible_client_ids))
    ).first()

    if not regra:
        flash('Regra de Tributação não encontrada ou você não tem permissão para acessá-la.', 'danger')
        return redirect(url_for('admin_regras_tributacao_list'))
    
    return_client_id = request.args.get('cliente_id', type=int) 
    if not return_client_id and regra:
        return_client_id = regra.cliente_id # Se não veio do form de cliente, pega o cliente da regra
    clientes_disponiveis = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    regimes_tributarios = db.query(RegimeTributario).all()
    cfops = db.query(Cfop).all()
    ncms = db.query(Ncm).all()
    csts = db.query(Csticms).all()
    csosns = db.query(Csosnicms).all()
    motivos_desoneracao = db.query(MotivoDesoneracao).order_by(MotivoDesoneracao.codigo).all()
    form_data = request.form
    if request.method == 'POST':
        novo_cliente_id_form = request.form.get('cliente_id')
        novo_cliente_id = int(novo_cliente_id_form) if novo_cliente_id_form else None
        # Valida se o usuário tem permissão para associar a este novo cliente
        if novo_cliente_id is not None and novo_cliente_id not in accessible_client_ids:
            flash('Você não tem permissão para associar a regra a este cliente.', 'danger')
            return render_template('admin_regras_tributacao_form.html', regra=regra, clientes=clientes_disponiveis, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, motivos_desoneracao=motivos_desoneracao, form_data=form_data, return_client_id=return_client_id)
        
        regra.cliente_id = novo_cliente_id
        regra.regime_tributario_id = int(request.form.get('regime_tributario_id'))
        regra.cfop_id = int(request.form.get('cfop_id'))
        regra.ncm_id = int(request.form.get('ncm_id')) if request.form.get('ncm_id') else None
        regra.uf_origem = request.form.get('uf_origem')
        regra.uf_destino = request.form.get('uf_destino')
        regra.tipo_item = request.form.get('tipo_item')
        prioridade_str = request.form.get('prioridade')
        regra.cst_icms = request.form.get('cst_icms')
        regra.csosn_icms = request.form.get('csosn_icms')
        aliquota_icms_str = request.form.get('aliquota_icms')
        reducao_base_icms_str = request.form.get('reducao_base_icms')
        modalidade_bc_icms_str = request.form.get('modalidade_bc_icms')
        motivo_desoneracao_icms_str = request.form.get('motivo_desoneracao_icms')
        regra.cst_pis = request.form.get('cst_pis')
        aliquota_pis_str = request.form.get('aliquota_pis')
        regra.cst_cofins = request.form.get('cst_cofins')
        aliquota_cofins_str = request.form.get('aliquota_cofins')
        regra.cst_ipi = request.form.get('cst_ipi')
        aliquota_ipi_str = request.form.get('aliquota_ipi')
        regra.descricao_regra = request.form.get('descricao_regra')
        regra.ativo = request.form.get('ativo') == 'on'
        if not all([regra.regime_tributario_id, regra.cfop_id]):
            flash('Regime Tributário e CFOP são campos obrigatórios para Regra de Tributação.', 'danger')
            return render_template('admin_regras_tributacao_form.html', regra=regra, clientes=clientes_disponiveis, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, motivos_desoneracao=motivos_desoneracao, form_data=form_data, return_client_id=return_client_id)
        
        try:
            regra.prioridade = int(prioridade_str) if prioridade_str else 100
            regra.aliquota_icms = Decimal(aliquota_icms_str) if aliquota_icms_str else None
            regra.reducao_base_icms = Decimal(reducao_base_icms_str) if reducao_base_icms_str else None
            regra.modalidade_bc_icms = int(modalidade_bc_icms_str) if modalidade_bc_icms_str else None
            regra.motivo_desoneracao_icms = int(motivo_desoneracao_icms_str) if motivo_desoneracao_icms_str else None
            regra.aliquota_pis = Decimal(aliquota_pis_str) if aliquota_pis_str else None
            regra.aliquota_cofins = Decimal(aliquota_cofins_str) if aliquota_cofins_str else None
            regra.aliquota_ipi = Decimal(aliquota_ipi_str) if aliquota_ipi_str else None
            
            db.commit()
            flash('Regra de Tributação atualizada com sucesso!', 'success')
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='regras'))
            return redirect(url_for('admin_regras_tributacao_list'))
        except ValueError as e:
            db.rollback()
            flash(f"Erro de formato: {e}. Verifique os campos numéricos e de IDs.", 'danger')
        except IntegrityError:
            db.rollback()
            flash('Erro de integridade ao atualizar regra. Verifique se os IDs existem ou se há duplicatas.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar Regra de Tributação: {e}", 'danger')
    return render_template('admin_regras_tributacao_form.html', regra=regra, clientes=clientes_disponiveis, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, motivos_desoneracao=motivos_desoneracao, form_data=regra, return_client_id=return_client_id)
@app.route('/admin/regras_tributacao/delete/<int:regra_tributacao_id>', methods=['POST'])
@login_required
@permission_required('rules.delete')
def admin_regras_tributacao_delete(regra_tributacao_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    regra = db.query(RegraTributacao).filter(
        RegraTributacao.regra_tributacao_id == regra_tributacao_id,
        (RegraTributacao.cliente_id.is_(None)) | (RegraTributacao.cliente_id.in_(accessible_client_ids))
    ).first()
    if not regra:
        flash('Regra de Tributação não encontrada ou você não tem permissão para excluí-la.', 'danger')
        return redirect(url_for('admin_regras_tributacao_list'))
    
    return_client_id = regra.cliente_id
    try:
        db.delete(regra)
        db.commit()
        flash('Regra de Tributação excluída com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir esta regra de tributação pois ela está vinculada a outros registros.', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir Regra de Tributação: {e}", 'danger')
    
    if return_client_id: # Se a regra estava associada a um cliente, volta para a aba do cliente
        return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='regras'))
    return redirect(url_for('admin_regras_tributacao_list'))
# --- Rotas para OrigemMercadoria (dados globais) ---
@app.route('/admin/origens_mercadoria/list')
@login_required
@permission_required('origens_mercadoria.read')
def admin_origens_mercadoria_list():
    db = next(get_db())
    origens = db.query(OrigemMercadoria).all()
    return render_template('admin_origens_mercadoria_list.html', origens=origens)
@app.route('/admin/origens_mercadoria/add', methods=['GET', 'POST'])
@login_required
@permission_required('origens_mercadoria.create')
def admin_origens_mercadoria_add():
    db = next(get_db())
    form_data = request.form
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        if not all([codigo, descricao]):
            flash('Código e Descrição são campos obrigatórios para Origem de Mercadoria.', 'danger')
            return render_template('admin_origens_mercadoria_form.html', form_data=form_data)
        
        try:
            nova_origem = OrigemMercadoria(codigo=codigo, descricao=descricao)
            db.add(nova_origem)
            db.commit()
            flash('Origem de Mercadoria adicionada com sucesso!', 'success')
            return redirect(url_for('admin_origens_mercadoria_list'))
        except IntegrityError:
            db.rollback()
            flash('Código de Origem de Mercadoria já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar Origem de Mercadoria: {e}", 'danger')
    return render_template('admin_origens_mercadoria_form.html', form_data=form_data)
@app.route('/admin/origens_mercadoria/edit/<int:origem_id>', methods=['GET', 'POST'])
@login_required
@permission_required('origens_mercadoria.edit')
def admin_origens_mercadoria_edit(origem_id):
    db = next(get_db())
    origem = db.query(OrigemMercadoria).get(origem_id)
    if not origem:
        abort(404)
    form_data = request.form
    if request.method == 'POST':
        origem.codigo = request.form.get('codigo')
        origem.descricao = request.form.get('descricao')
        if not all([origem.codigo, origem.descricao]):
            flash('Código e Descrição são campos obrigatórios para Origem de Mercadoria.', 'danger')
            return render_template('admin_origens_mercadoria_form.html', origem=origem, form_data=form_data)
        
        try:
            db.commit()
            flash('Origem de Mercadoria atualizada com sucesso!', 'success')
            return redirect(url_for('admin_origens_mercadoria_list'))
        except IntegrityError:
            db.rollback()
            flash('Código de Origem de Mercadoria já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar Origem de Mercadoria: {e}", 'danger')
    return render_template('admin_origens_mercadoria_form.html', origem=origem, form_data=origem)
@app.route('/admin/origens_mercadoria/delete/<int:origem_id>', methods=['POST'])
@login_required
@permission_required('origens_mercadoria.delete')
def admin_origens_mercadoria_delete(origem_id):
    db = next(get_db())
    origem = db.query(OrigemMercadoria).get(origem_id)
    if not origem:
        abort(404)
    try:
        db.delete(origem)
        db.commit()
        flash('Origem de Mercadoria excluída com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir esta Origem de Mercadoria pois ela está vinculada a outros registros (ex: Produtos).', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir Origem de Mercadoria: {e}", 'danger')
    return redirect(url_for('admin_origens_mercadoria_list'))
# --- Rotas para DestinatarioNFe ---
@app.route('/admin/destinatarios_nfe/list')
@login_required
@permission_required('destinatarios_nfe.read')
def admin_destinatarios_nfe_list():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    destinatarios = db.query(DestinatarioNFe).filter(DestinatarioNFe.cliente_id.in_(accessible_client_ids)).all()
    # Adicionando clientes para exibir no template
    clientes = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    cliente_map = {c.cliente_id: c.razao_social for c in clientes}
    return render_template('destinatario/lista.html', destinatarios=destinatarios, cliente_map=cliente_map)
@app.route('/admin/destinatarios_nfe/add', methods=['GET', 'POST'])
@login_required
@permission_required('destinatarios_nfe.create')
def admin_destinatarios_nfe_add():
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    clientes_disponiveis = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    
    # Verifica se a requisição veio de um modal (AJAX)
    is_modal_request = request.args.get('modal', 'false').lower() == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Objeto dummy para 'Novo' destinatário e para o título do template
    destinatario_obj = {} 
    form_data = {} # Para preencher em caso de POST com erro
    return_client_id = request.args.get('cliente_id', type=int)
    
    if request.method == 'POST':
        form_data = request.form.to_dict() # Coleta todos os dados do formulário para repopular
        
        cliente_id_form = form_data.get('cliente_id')
        cliente_id = int(cliente_id_form) if cliente_id_form else None
        
        if cliente_id is not None and cliente_id not in accessible_client_ids:
            msg = 'Você não tem permissão para adicionar destinatários a este cliente.'
            if is_modal_request:
                return jsonify({'success': False, 'message': msg}), 403
            flash(msg, 'danger')
            return render_template(
                'admin_destinatario_form.html',
                destinatario=destinatario_obj, # Objeto vazio, para o título 'Novo Destinatário'
                form_data=form_data,           # Dados para repopular os campos
                clientes=clientes_disponiveis,
                return_client_id=return_client_id
            )
        
        # Mapeia os dados do formulário para o formato do modelo
        data = {
            'cliente_id': cliente_id,
            'tipo_pessoa': form_data.get('tipo_pessoa'),
            'nome_razao_social': form_data.get('nome_razao_social'),
            'cpf_cnpj': form_data.get('cpf_cnpj').replace('.', '').replace('/', '').replace('-', ''), 
            'ie': form_data.get('ie'),
            'ie_indicador_nfe': form_data.get('ie_indicador_nfe'),
            'email': form_data.get('email'),
            'telefone': form_data.get('telefone').replace('(', '').replace(')', '').replace(' ', '').replace('-', ''), 
            'logradouro': form_data.get('logradouro'),
            'numero': form_data.get('numero'),
            'complemento': form_data.get('complemento'),
            'bairro': form_data.get('bairro'),
            'cep': form_data.get('cep').replace('-', ''), 
            'codigo_municipio': form_data.get('codigo_municipio'),
            'nome_municipio': form_data.get('nome_municipio'),
            'uf': form_data.get('uf'),
            'codigo_uf': form_data.get('codigo_uf'), 
            'codigo_pais': form_data.get('codigo_pais') or '1058',
            'nome_pais': form_data.get('nome_pais') or 'Brasil',
            'created_by_user_id': current_user.id if current_user.is_authenticated else None
        }
        # Validação de campos obrigatórios (repetida do frontend, para segurança)
        required_fields = ['tipo_pessoa', 'nome_razao_social', 'cpf_cnpj', 'ie_indicador_nfe',
                           'logradouro', 'numero', 'bairro', 'cep', 'codigo_municipio',
                           'nome_municipio', 'uf', 'codigo_uf', 'cliente_id'] 
        
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            msg = f"Preencha todos os campos obrigatórios. Faltando: {', '.join(missing_fields)}"
            if is_modal_request:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'danger')
            return render_template(
                'admin_destinatario_form.html',
                destinatario=destinatario_obj, # Objeto vazio
                form_data=form_data,           # Dados para repopular os campos
                clientes=clientes_disponiveis,
                return_client_id=return_client_id
            )
        try:
            novo_destinatario = DestinatarioNFe(**data)
            db.add(novo_destinatario)
            db.commit()
            msg = 'Destinatário cadastrado com sucesso!'
            if is_modal_request:
                return jsonify({'success': True, 'message': msg, 'redirect_url': url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='destinatarios') if return_client_id else url_for('admin_destinatarios_nfe_list')}), 201
            flash(msg, 'success')
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='destinatarios'))
            return redirect(url_for('admin_destinatarios_nfe_list'))
        except IntegrityError as e:
            db.rollback()
            db_error_message = str(e.orig)
            if "duplicate key value violates unique constraint" in db_error_message:
                error_msg = f"CPF/CNPJ já cadastrado para outro destinatário. Detalhes: {db_error_message}"
            elif "violates foreign key constraint" in db_error_message:
                error_msg = f"Erro de chave estrangeira. Um dos IDs de referência não existe. Detalhes: {db_error_message}"
            else:
                error_msg = f"Erro de integridade ao cadastrar destinatário: {db_error_message}"
            
            current_app.logger.error(f"Erro ao cadastrar destinatário: {db_error_message}", exc_info=True)
            
            if is_modal_request:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
        except Exception as e:
            db.rollback()
            error_msg = f"Erro ao cadastrar destinatário: {e}"
            current_app.logger.error(f"Erro ao cadastrar destinatário: {e}", exc_info=True)
            if is_modal_request:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
    
    initial_form_data = form_data # Para manter dados em caso de erro
    if return_client_id and not initial_form_data.get('cliente_id'):
        initial_form_data['cliente_id'] = return_client_id
    if is_modal_request:
        # Renderiza o NOVO template específico para o modal
        return render_template(
            'admin_destinatario_form_modal.html',
            clientes=clientes_disponiveis,
            form_data=initial_form_data,
            return_client_id=return_client_id
        )
    else:
        # Renderiza a página completa
        return render_template(
            'admin_destinatario_form.html',
            destinatario=destinatario_obj, # Objeto vazio para 'Novo'
            form_data=initial_form_data,   # Dados vazios para o primeiro carregamento, ou com return_client_id
            clientes=clientes_disponiveis,
            return_client_id=return_client_id
        )
@app.route('/admin/destinatarios_nfe/edit/<int:destinatario_id>', methods=['GET', 'POST'])
@login_required
@permission_required('destinatarios_nfe.edit')
def admin_destinatarios_nfe_edit(destinatario_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    destinatario_obj = db.query(DestinatarioNFe).filter(
        DestinatarioNFe.destinatario_id == destinatario_id,
        DestinatarioNFe.cliente_id.in_(accessible_client_ids)
    ).first()
    if not destinatario_obj:
        flash('Destinatário não encontrado ou você não tem permissão para acessá-lo.', 'danger')
        return redirect(url_for('admin_destinatarios_nfe_list'))
    
    clientes_disponiveis = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    
    # O return_client_id pode vir da URL ou ser o cliente_id do próprio destinatário
    return_client_id = request.args.get('cliente_id', type=int) 
    if not return_client_id:
        return_client_id = destinatario_obj.cliente_id # Sempre pega do objeto se não vier da URL
    form_data = {} # Usado para repopular em caso de POST com erro
    
    if request.method == 'POST':
        form_data = request.form.to_dict() # Coleta todos os dados do formulário para repopular
        novo_cliente_id_form = form_data.get('cliente_id')        
        novo_cliente_id = int(novo_cliente_id_form) if novo_cliente_id_form else None
        
        if novo_cliente_id is not None and novo_cliente_id not in accessible_client_ids:
            flash('Você não tem permissão para associar o destinatário a este cliente.', 'danger')
            return render_template(
                'admin_destinatario_form.html',
                destinatario=destinatario_obj, # Objeto original, para o título 'Editar...'
                form_data=form_data,       # Dados submetidos (com erro) para repopular
                clientes=clientes_disponiveis,
                return_client_id=return_client_id
            )
        
        # Atualiza os dados do objeto destinatario
        destinatario_obj.cliente_id = novo_cliente_id
        destinatario_obj.tipo_pessoa = form_data.get('tipo_pessoa')
        destinatario_obj.nome_razao_social = form_data.get('nome_razao_social')
        destinatario_obj.cpf_cnpj = form_data.get('cpf_cnpj').replace('.', '').replace('/', '').replace('-', '')
        destinatario_obj.ie = form_data.get('ie')
        destinatario_obj.ie_indicador_nfe = form_data.get('ie_indicador_nfe')
        destinatario_obj.email = form_data.get('email')
        destinatario_obj.telefone = form_data.get('telefone').replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
        destinatario_obj.logradouro = form_data.get('logradouro')
        destinatario_obj.numero = form_data.get('numero')
        destinatario_obj.complemento = form_data.get('complemento')
        destinatario_obj.bairro = form_data.get('bairro')
        destinatario_obj.cep = form_data.get('cep').replace('-', '')
        destinatario_obj.codigo_municipio = form_data.get('codigo_municipio')
        destinatario_obj.nome_municipio = form_data.get('nome_municipio')
        destinatario_obj.uf = form_data.get('uf')
        destinatario_obj.codigo_uf = form_data.get('codigo_uf')
        destinatario_obj.codigo_pais = form_data.get('codigo_pais') or '1058'
        destinatario_obj.nome_pais = form_data.get('nome_pais') or 'Brasil'
        destinatario_obj.data_atualizacao = datetime.now()
        # Validação de campos obrigatórios
        required_fields = ['tipo_pessoa', 'nome_razao_social', 'cpf_cnpj', 'ie_indicador_nfe',
                           'logradouro', 'numero', 'bairro', 'cep', 'codigo_municipio',
                           'nome_municipio', 'uf', 'codigo_uf', 'cliente_id']
        
        missing_fields = [f for f in required_fields if not getattr(destinatario_obj, f)] # Usar getattr para objeto
        if missing_fields:
            msg = f"Preencha todos os campos obrigatórios. Faltando: {', '.join(missing_fields)}"
            flash(msg, 'danger')
            return render_template(
                'admin_destinatario_form.html',
                destinatario=destinatario_obj, # Objeto atualizado com alguns dados, para o título
                form_data=form_data,       # Dados submetidos para repopular
                clientes=clientes_disponiveis,
                return_client_id=return_client_id
            )
        try:
            db.commit()
            flash('Destinatário atualizado com sucesso!', 'success')
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='destinatarios'))
            return redirect(url_for('admin_destinatarios_nfe_list'))
        except IntegrityError as e:
            db.rollback()
            db_error_message = str(e.orig)
            if "duplicate key value violates unique constraint" in db_error_message:
                error_msg = f"CPF/CNPJ já cadastrado para outro destinatário. Detalhes: {db_error_message}"
            elif "violates foreign key constraint" in db_error_message:
                error_msg = f"Erro de chave estrangeira. Um dos IDs de referência não existe. Detalhes: {db_error_message}"
            else:
                error_msg = f"Erro de integridade ao atualizar destinatário: {db_error_message}"
            current_app.logger.error(f"Erro ao atualizar destinatário: {db_error_message}", exc_info=True)
            flash(error_msg, 'danger')
        except Exception as e:
            db.rollback()
            error_msg = f"Erro ao atualizar destinatário: {e}"
            current_app.logger.error(f"Erro ao atualizar destinatário: {e}", exc_info=True)
            flash(error_msg, 'danger')
            
    # GET request para exibir o formulário de edição
    # Usa o objeto 'destinatario_obj' diretamente para preencher os campos
    return render_template(
        'admin_destinatario_form.html',
        destinatario=destinatario_obj, # Objeto do DB para o título e valores padrão
        form_data=destinatario_obj,    # Objeto do DB para preencher os campos no GET
        clientes=clientes_disponiveis,
        return_client_id=return_client_id
    )
@app.route('/admin/destinatarios_nfe/delete/<int:destinatario_id>', methods=['POST'])
@login_required
@permission_required('destinatarios_nfe.delete')
def admin_destinatarios_nfe_delete(destinatario_id):
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)

    destinatario = db.query(DestinatarioNFe).filter(
        DestinatarioNFe.destinatario_id == destinatario_id,
        DestinatarioNFe.cliente_id.in_(accessible_client_ids)
    ).first()
    if not destinatario:
        flash('Destinatário não encontrado ou você não tem permissão para excluí-lo.', 'danger')
        return redirect(url_for('admin_destinatarios_nfe_list'))
    
    client_id_for_redirect = destinatario.cliente_id
    try:
        db.delete(destinatario)
        db.commit()
        flash('Destinatário excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este destinatário pois ele está vinculado a outros registros (ex: NF-e).', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir destinatário: {e}", 'danger')
    
    if client_id_for_redirect:
        return redirect(url_for('admin_clientes_edit', cliente_id=client_id_for_redirect, _anchor='destinatarios'))
    return redirect(url_for('admin_destinatarios_nfe_list'))
# --- Rotas para Motivos de Desoneração ICMS (dados globais) ---
# **CORREÇÃO DE DUPLICAÇÃO:** Esta é a ÚNICA definição para esta rota.
@app.route('/admin/motivos_desoneracao/list')
@login_required
@permission_required('motivos_desoneracao.read')
def admin_motivos_desoneracao_list():
    db = next(get_db())
    motivos = db.query(MotivoDesoneracao).order_by(MotivoDesoneracao.codigo).all()
    return render_template('tributacao/motivos_desoneracao_list.html', motivos=motivos)
@app.route('/admin/motivos_desoneracao/add', methods=['GET', 'POST'])
@login_required
@permission_required('motivos_desoneracao.create')
def admin_motivos_desoneracao_add():
    db = next(get_db())
    form_data = request.form
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        if not all([codigo, descricao]):
            flash('Código e Descrição são campos obrigatórios para Motivo de Desoneração.', 'danger')
            return render_template('tributacao/motivos_desoneracao_form.html', form_data=form_data)
        try:
            novo_motivo = MotivoDesoneracao(codigo=codigo, descricao=descricao)
            db.add(novo_motivo)
            db.commit()
            flash('Motivo de Desoneração adicionado com sucesso!', 'success')
            return redirect(url_for('admin_motivos_desoneracao_list'))
        except IntegrityError:
            db.rollback()
            flash('Código de Motivo de Desoneração já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar Motivo de Desoneração: {e}", 'danger')
    return render_template('tributacao/motivos_desoneracao_form.html', form_data=form_data)
@app.route('/admin/motivos_desoneracao/edit/<int:motivo_id>', methods=['GET', 'POST'])
@login_required
@permission_required('motivos_desoneracao.edit')
def admin_motivos_desoneracao_edit(motivo_id):
    db = next(get_db())
    motivo = db.query(MotivoDesoneracao).get(motivo_id)
    if not motivo:
        abort(404)
    form_data = request.form
    if request.method == 'POST':
        motivo.codigo = request.form.get('codigo')
        motivo.descricao = request.form.get('descricao')
        if not all([motivo.codigo, motivo.descricao]):
            flash('Código e Descrição são campos obrigatórios para Motivo de Desoneração.', 'danger')
            return render_template('tributacao/motivos_desoneracao_form.html', motivo=motivo, form_data=form_data)
        try:
            db.commit()
            flash('Motivo de Desoneração atualizado com sucesso!', 'success')
            return redirect(url_for('admin_motivos_desoneracao_list'))
        except IntegrityError:
            db.rollback()
            flash('Código de Motivo de Desoneração já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar Motivo de Desoneração: {e}", 'danger')
    return render_template('tributacao/motivos_desoneracao_form.html', motivo=motivo, form_data=motivo)
@app.route('/admin/motivos_desoneracao/delete/<int:motivo_id>', methods=['POST'])
@login_required
@permission_required('motivos_desoneracao.delete')
def admin_motivos_desoneracao_delete(motivo_id):
    db = next(get_db())
    motivo = db.query(MotivoDesoneracao).get(motivo_id)
    if not motivo:
        abort(404)
    try:
        db.delete(motivo)
        db.commit()
        flash('Motivo de Desoneração excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este Motivo de Desoneração pois ele está vinculado a outros registros.', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir Motivo de Desoneração: {e}", 'danger')
    return redirect(url_for('admin_motivos_desoneracao_list'))
# --- Rotas para Gerenciamento de Usuários ---

@app.route('/admin/users/list')
@login_required
@permission_required('users.read')
def admin_users_list():
    db = next(get_db())
    users = db.query(User).all()
    return render_template('admin_users_list.html', users=users)
@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@permission_required('users.create')
def admin_users_add():
    db = next(get_db())
    roles = db.query(Role).all()
    accessible_client_ids = get_accessible_client_ids(db)
    clients = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        selected_roles_ids = request.form.getlist('roles')
        selected_clients_ids = request.form.getlist('clients')
        is_active = request.form.get('is_active') == 'on'
        if not (username and password and password_confirm):
            flash('Nome de usuário, senha e confirmação de senha são obrigatórios.', 'danger')
            return render_template('admin_users_form.html', roles=roles, clients=clients, form_data=request.form)
        if password != password_confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('admin_users_form.html', roles=roles, clients=clients, form_data=request.form)
        try:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password_hash=hashed_password, is_active=is_active)
            db.add(new_user)
            db.flush()
            for role_id_str in selected_roles_ids:
                user_role = UserRole(user_id=new_user.id, role_id=int(role_id_str))
                db.add(user_role)
            
            for client_id_str in selected_clients_ids:
                client_id = int(client_id_str)
                # Dupla checagem: o admin só pode vincular usuários a clientes que ele mesmo acessa
                if client_id not in accessible_client_ids:
                    flash(f'Você não tem permissão para vincular o usuário ao cliente com ID {client_id}.', 'danger')
                    raise Exception('Permissão negada para vincular cliente.')
                user_client = UserClient(user_id=new_user.id, client_id=client_id)
                db.add(user_client)
            db.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin_users_list'))
        except IntegrityError:
            db.rollback()
            flash('Nome de usuário ou e-mail já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao criar usuário: {e}", 'danger')
    return render_template('admin_users_form.html', roles=roles, clients=clients, form_data={})

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@permission_required('users.edit')
def admin_users_edit(user_id):
    db = next(get_db())
    user = db.query(User).get(user_id)
    if not user:
        abort(404)
    
    roles = db.query(Role).all()
    
    # Clientes que o *admin atual* pode acessar para vincular ao *usuário que está sendo editado*
    accessible_client_ids_by_admin = get_accessible_client_ids(db)
    clients_for_dropdown = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids_by_admin)).all()
    user_roles_ids = {ur.role_id for ur in user.roles}
    user_clients_ids = {uc.client_id for uc in user.clients}
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        new_password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        selected_roles_ids = {int(id) for id in request.form.getlist('roles')}
        selected_clients_ids = {int(id) for id in request.form.getlist('clients')}
        user.is_active = request.form.get('is_active') == 'on'
        if new_password:
            if new_password != password_confirm:
                flash('As senhas não coincidem.', 'danger')
                return render_template('admin_users_form.html', user=user, roles=roles, clients=clients_for_dropdown, user_roles_ids=user_roles_ids, user_clients_ids=user_clients_ids)
            user.password_hash = generate_password_hash(new_password)
        try:
            # Atualiza roles do usuário
            for ur in list(user.roles): # Usar list() para evitar "collection was modified"
                if ur.role_id not in selected_roles_ids:
                    db.delete(ur)
            for role_id in selected_roles_ids:
                if role_id not in user_roles_ids:
                    user_role = UserRole(user_id=user.id, role_id=role_id)
                    db.add(user_role)
            
            # Atualiza clientes do usuário
            for uc in list(user.clients): # Usar list()
                if uc.client_id not in selected_clients_ids:
                    db.delete(uc)
            for client_id in selected_clients_ids:
                # Dupla checagem: o admin só pode vincular usuários a clientes que ele mesmo acessa
                if client_id not in accessible_client_ids_by_admin:
                    flash(f'Você não tem permissão para vincular o usuário ao cliente com ID {client_id}.', 'danger')
                    raise Exception('Permissão negada para vincular cliente.')
                if client_id not in user_clients_ids:
                    user_client = UserClient(user_id=user.id, client_id=client_id)
                    db.add(user_client)
            db.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin_users_list'))
        except IntegrityError:
            db.rollback()
            flash('Nome de usuário ou e-mail já existe.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar usuário: {e}", 'danger')
    return render_template('admin_users_form.html', user=user, roles=roles, clients=clients_for_dropdown, user_roles_ids=user_roles_ids, user_clients_ids=user_clients_ids)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@permission_required('users.delete')
def admin_users_delete(user_id):
    db = next(get_db())
    user = db.query(User).get(user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash('Você não pode excluir a si mesmo.', 'danger')
        return redirect(url_for('admin_users_list'))
    try:
        db.delete(user)
        db.commit()
        flash('Usuário excluído com sucesso!', 'success')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir usuário: {e}", 'danger')
    
    return redirect(url_for('admin_users_list'))
# --- Rotas para Gerenciamento de Papéis (Roles) ---
@app.route('/admin/roles/list')
@login_required
@permission_required('roles.read')
def admin_roles_list():
    db = next(get_db())
    roles = db.query(Role).all()
    return render_template('admin_roles_list.html', roles=roles)


def get_active_certificate_for_client(db_session, cliente_id):
    # Lógica para buscar o certificado ativo do cliente_id
    # Exemplo:
    cert = db_session.query(CertificadoDigital).filter_by(cliente_id=cliente_id, ativo=True).first()
    return cert # Retorna o objeto CertificadoDigital (com conteudo_certificado, senha_certificado, etc.)

# Nova rota para a tela de emissão de NF-e
# ... (código anterior) ...

@app.route('/admin/emitir_nfe', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue') # Nova permissão, ajuste conforme seu sistema de permissões
def admin_emitir_nfe():
    db = next(get_db())
    # O emitente é o cliente associado ao usuário logado, ou o cliente selecionado se for multi-empresa
    # Para simplificar, assumimos um único cliente por usuário ou que o cliente já está selecionado em sessão
    accessible_client_ids = get_accessible_client_ids(db)
    
    if not accessible_client_ids:
        flash('Você não está associado a nenhum cliente ou não tem permissão para emitir NF-e.', 'danger')
        return redirect(url_for('home'))
    emitente_cliente_id = accessible_client_ids[0]
    emitente_data = db.query(Cliente).options(joinedload(Cliente.regime_tributario)).filter_by(cliente_id=emitente_cliente_id).first()
    if not emitente_data:
        flash('Dados do emitente não encontrados.', 'danger')
        return redirect(url_for('home'))
    emitente_data_for_template = {
        "cliente_id": emitente_data.cliente_id,
        "razao_social": emitente_data.razao_social,
        "cnpj": emitente_data.cnpj,
        "inscricao_estadual": emitente_data.inscricao_estadual,
        "logradouro": emitente_data.logradouro,
        "numero": emitente_data.numero,
        "bairro": emitente_data.bairro,
        "cep": emitente_data.cep,
        "nome_municipio": emitente_data.nome_municipio,
        "uf": emitente_data.uf,
        "cnae": emitente_data.cnae,
        "regime_tributario_nome": emitente_data.regime_tributario.nome if emitente_data.regime_tributario else 'N/A',
        "regime_tributario_id": emitente_data.regime_tributario_id # ADICIONADO AQUI
    }
    
    destinatarios_obj = db.query(DestinatarioNFe).filter_by(cliente_id=emitente_cliente_id).all()
    destinatarios_for_template = [d.to_dict() for d in destinatarios_obj] # Já convertido para dicionário
    # --- ATUALIZADO: Usar joinedload para os novos relacionamentos do Produto ---
    produtos_obj = db.query(Produto).filter_by(cliente_id=emitente_cliente_id).options(
        joinedload(Produto.ncm), 
        joinedload(Produto.cfop), # CARREGA O CFOP PADRÃO DO PRODUTO
        joinedload(Produto.origem),
        joinedload(Produto.csts_icms), # CARREGA O CST ICMS PADRÃO DO PRODUTO
        joinedload(Produto.csosns_icms) # CARREGA O CSOSN ICMS PADRÃO DO PRODUTO
    ).all()
    produtos_for_template = [p.to_dict() for p in produtos_obj] # Já convertido para dicionário

    # --- CORREÇÃO AQUI: Converter objetos SQLAlchemy para listas de dicionários ---
    # --- NOVO: Buscar listas completas para CFOPs, CSTs e CSOSNs ---
    # all_cfops = db.query(Cfop).all() # LINHA ORIGINAL
    all_cfops_raw = db.query(Cfop).all()
    all_cfops_for_template = [{"cfop_id": c.cfop_id, "cfop": c.cfop, "descricao": c.descricao} for c in all_cfops_raw]

    # all_csts_icms = db.query(Csticms).all() # LINHA ORIGINAL
    all_csts_icms_raw = db.query(Csticms).all()
    all_csts_icms_for_template = [{"cst_id": c.cst_id, "codigo": c.codigo, "descricao": c.descricao} for c in all_csts_icms_raw]

    # all_csosns_icms = db.query(Csosnicms).all() # LINHA ORIGINAL
    all_csosns_icms_raw = db.query(Csosnicms).all()
    all_csosns_icms_for_template = [{"csosn_id": c.csosn_id, "codigo": c.codigo, "descricao": c.descricao} for c in all_csosns_icms_raw]
    # ----------------------------------------------------------------

    form_data = {} 
    initial_nfe_items = [] 

    if request.method == 'POST':
        form_data = request.form.to_dict()
        action = request.form.get('action')
        nfe_items_raw = []
        for key in request.form:
            if key.startswith('items[') and key.endswith('][json]'):
                try:
                    nfe_items_raw.append(json.loads(request.form[key]))
                except json.JSONDecodeError:
                    flash(f"Erro ao decodificar item JSON: {request.form[key]}", 'danger')
                    initial_nfe_items = nfe_items_raw 
                    return render_template('emitir_nfe.html',
                                           emitente_data=emitente_data_for_template,
                                           destinatarios=destinatarios_for_template,
                                           produtos=produtos_for_template,
                                           all_cfops=all_cfops_for_template, # CORRIGIDO AQUI
                                           all_csts=all_csts_icms_for_template, # CORRIGIDO AQUI
                                           all_csosns=all_csosns_icms_for_template, # CORRIGIDO AQUI
                                           form_data=form_data,
                                           initial_nfe_items=initial_nfe_items)
        
        initial_nfe_items = nfe_items_raw
        # --- VALIDAÇÕES E CONSTRUÇÃO DO XML (incluindo natOp agora como dropdown) ---
        if not form_data.get('natOp') or not form_data.get('finNFe'): # 'natOp' é o CFOP
            flash('Campos de identificação da NF-e são obrigatórios.', 'danger')
            return render_template('emitir_nfe.html',
                                   emitente_data=emitente_data_for_template,
                                   destinatarios=destinatarios_for_template,
                                   produtos=produtos_for_template,
                                   all_cfops=all_cfops_for_template, # CORRIGIDO AQUI
                                   all_csts=all_csts_icms_for_template, # CORRIGIDO AQUI
                                   all_csosns=all_csosns_icms_for_template, # CORRIGIDO AQUI
                                   form_data=form_data,
                                   initial_nfe_items=initial_nfe_items)
        
        # ... (restante da lógica de POST) ...
        flash('Lógica de emissão/pré-visualização/rascunho ainda não implementada para este formulário.', 'info')
        # AQUI VOCÊ ADICIONARIA A LÓGICA DE GERAÇÃO DO XML
        # EXEMPLO: return render_template('xml_preview.html', xml_content=generated_xml)
        
    return render_template('emitir_nfe.html',
                           emitente_data=emitente_data_for_template,
                           destinatarios=destinatarios_for_template,
                           produtos=produtos_for_template,
                           all_cfops=all_cfops_for_template, # CORRIGIDO AQUI
                           all_csts=all_csts_icms_for_template, # CORRIGIDO AQUI
                           all_csosns=all_csosns_icms_for_template, # CORRIGIDO AQUI
                           form_data=form_data,
                           initial_nfe_items=initial_nfe_items)




if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
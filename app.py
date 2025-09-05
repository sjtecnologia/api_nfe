from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, abort
import json
import os
import uuid
from datetime import datetime, date
from decimal import Decimal # Para lidar com tipos Numeric do SQLAlchemy

# Importe os modelos do seu arquivo models.py
# Certifique-se de que todos os modelos necessários estejam aqui.
# Ex: from database.models import Cliente, Produto, RegraTributacao, etc.
from database.models import Base, Cfop, Ncm, Produto, Cliente, RegimeTributario, CertificadoDigital, NFeEmitidas, RegraTributacao, Csosnicms, Csticms, OrigemMercadoria, DestinatarioNFe, MotivoDesoneracao

# Imports para processar certificado
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes # Para gerar fingerprint

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError

app = Flask(__name__)
# Chave secreta para mensagens flash (SUBSTITUA POR UMA CHAVE SEGURA EM PRODUÇÃO)
app.secret_key = 'keysegura123' 

# --- Configuração do Banco de Dados ---
# ATENÇÃO: Verifique se o host e o nome do banco de dados estão corretos para o seu ambiente.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Mo2505@localhost:5432/sjtnfe")

if "postgresql" in SQLALCHEMY_DATABASE_URL:
    os.environ['DB_TYPE'] = 'postgresql'

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependência para obter a sessão do DB em cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Funções Auxiliares ---
# ATENÇÃO: Em um ambiente de produção, o conteúdo e senha do certificado DEVERIAM
# ser criptografados ANTES de serem armazenados no banco de dados.
# Para este exemplo, estamos armazenando os bytes brutos do arquivo.
def process_certificate_upload(db, cliente_id, request_form, request_files):
    cert_file = request_files.get('conteudo_certificado_file')
    
    # Só processa se um arquivo foi enviado E não está vazio
    if cert_file and cert_file.filename != '':
        try:
            file_content = cert_file.read() # Conteúdo em bytes
            cert_password = request_form.get('cert_senha_certificado')
            if not cert_password:
                flash('Senha do certificado é obrigatória ao fazer upload de um arquivo.', 'danger')
                return False, None

            # Tenta extrair o fingerprint e datas do próprio certificado (melhor prática)
            try:
                # Tenta carregar como PFX (PKCS12)
                private_key = None
                cert_x509_obj = None # Renomeado para evitar conflito com 'cert' no return
                # O cryptography.x509.load_key_and_certificates espera bytes e senha em bytes
                try:
                    p12 = x509.load_key_and_certificates(
                        file_content,
                        cert_password.encode('utf-8'), # Senha precisa ser em bytes
                        default_backend()
                    )
                    private_key = p12.key
                    cert_x509_obj = p12.cert # Assume que o primeiro é o certificado principal
                except ValueError:
                    # Se falhar como PFX, tenta como PEM (pode ser apenas o certificado)
                    try:
                        cert_x509_obj = x509.load_pem_x509_certificate(file_content, default_backend())
                    except ValueError:
                        flash(f'Erro ao carregar o certificado: Formato de arquivo ou senha inválidos para {cert_file.filename}.', 'danger')
                        return False, None
                
                if not cert_x509_obj:
                    flash(f'Não foi possível carregar o certificado do arquivo {cert_file.filename}.', 'danger')
                    return False, None

                # Extrai fingerprint e datas do próprio certificado
                fingerprint = cert_x509_obj.fingerprint(hashes.SHA256()).hex()
                # Use as datas do certificado se estiverem disponíveis
                validade_inicio_final = cert_x509_obj.not_valid_before_utc.replace(tzinfo=None)
                validade_fim_final = cert_x509_obj.not_valid_after_utc.replace(tzinfo=None)

            except Exception as e:
                flash(f'Erro ao ler dados do certificado (fingerprint/validade): {e}. Verifique o arquivo e a senha.', 'danger')
                return False, None

            # Criptografar senha do certificado antes de armazenar
            # Para este exemplo, estamos apenas convertendo para bytes
            encrypted_cert_password = cert_password.encode('utf-8')
            
            cert_obj = CertificadoDigital(
                cliente_id=cliente_id,
                fingerprint=fingerprint,
                conteudo_certificado=file_content, # Armazena os bytes brutos
                senha_certificado=encrypted_cert_password, # Senha convertida para bytes
                validade_inicio=validade_inicio_final, # Usar data do certificado
                validade_fim=validade_fim_final, # Usar data do certificado
                ativo=request_form.get('cert_ativo') == 'on',
                data_upload=datetime.now(),
                nome_arquivo_original=request_form.get('cert_nome_arquivo_original') or cert_file.filename
            )
            db.add(cert_obj)
            return True, cert_obj
        except Exception as e:
            flash(f'Erro inesperado ao processar o certificado: {e}', 'danger')
            print(f"Certificate processing error: {e}") # Para depuração no console
            return False, None
    return True, None # Nenhum arquivo de certificado enviado, sem erro

# --- Rotas da API Gerais (retornam JSON) ---

@app.route('/')
def home():
    """Rota inicial para verificar se a API está online."""
    return jsonify({
        "message": "API de Emissão de NF está online!",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Verifica a saúde da API.",
            "/cfops": "Lista todos os códigos CFOPs e suas descrições (API).",
            "/admin/clientes/list": "Acessa a interface de administração de clientes."
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar a saúde da API."""
    return jsonify({"status": "UP", "timestamp": datetime.now().isoformat()}), 200

# Rotas de API para listagem geral (podem ser usadas em dropdowns de outros formulários)
@app.route('/api/cfops', methods=['GET'])
def get_api_cfops():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    cfops = db.query(Cfop).all()
    cfop_list = [{"cfop_id": c.cfop_id, "cfop": c.cfop, "descricao": c.descricao} for c in cfops]
    return jsonify(cfop_list), 200

@app.route('/api/ncms', methods=['GET'])
def get_api_ncms():
    """Retorna a lista completa de NCMs."""
    db = next(get_db())
    ncms = db.query(Ncm).all()
    ncm_list = [{"ncm_id": n.ncm_id, "codigo": n.codigo, "descricao": n.descricao} for n in ncms]
    return jsonify(ncm_list), 200

@app.route('/api/produtos', methods=['GET'])
def get_api_produtos():
    """Retorna a lista completa de Produtos."""
    db = next(get_db())
    produtos = db.query(Produto).all()
    produto_list = [{"produto_id": p.produto_id, "codigo_interno": p.codigo_interno, "descricao": p.descricao} for p in produtos]
    return jsonify(produto_list), 200

@app.route('/api/clientes', methods=['GET'])
def get_api_clientes():
    """Retorna a lista completa de Clientes (API)."""
    db = next(get_db())
    clientes = db.query(Cliente).all()
    cliente_list = [{"cliente_id": c.cliente_id, "cnpj": c.cnpj, "razao_social": c.razao_social} for c in clientes]
    return jsonify(cliente_list), 200

@app.route('/api/certificados', methods=['GET'])
def get_api_certificados():
    """Retorna a lista completa de Certificados Digitais (API)."""
    db = next(get_db())
    certificados = db.query(CertificadoDigital).all()
    certificado_list = [{"certificado_digital_id": c.certificado_digital_id, "fingerprint": c.fingerprint, "validade_fim": c.validade_fim.isoformat()} for c in certificados]
    return jsonify(certificado_list), 200

@app.route('/api/nfes', methods=['GET'])
def get_api_nfes():
    """Retorna a lista completa de NF-e emitidas."""
    db = next(get_db())
    nfes = db.query(NFeEmitidas).all()
    nfe_list = [{"nfe_emitida_id": n.nfe_emitida_id, "tipo_nfe": n.tipo_nfe, "data_criacao": n.data_criacao.isoformat()} for n in nfes]
    return jsonify(nfe_list), 200

@app.route('/api/regimes_tributarios', methods=['GET'])
def get_api_regimes_tributarios():
    """Retorna a lista completa de Regimes Tributários (API)."""
    db = next(get_db())
    regimes_tributarios = db.query(RegimeTributario).all()
    regimes_tributario_list = [{"regime_tributario_id": r.regime_tributario_id, "nome": r.nome, "descricao": r.descricao} for r in regimes_tributarios]
    return jsonify(regimes_tributario_list), 200

@app.route('/api/regras_tributacao', methods=['GET'])
def get_api_regras_tributacao():
    """Retorna a lista completa de Regras de Tributação (API)."""
    db = next(get_db())
    regras_tributacao = db.query(RegraTributacao).all()
    regra_tributacao_list = [{"regra_tributacao_id": r.regra_tributacao_id, "descricao_regra": r.descricao_regra} for r in regras_tributacao]
    return jsonify(regra_tributacao_list), 200

@app.route('/api/csosn', methods=['GET'])
def get_api_csosns():
    """Retorna a lista completa de CSOSN ICMS."""
    db = next(get_db())
    csosns = db.query(Csosnicms).all()
    csosn_list = [{"csosn_id": c.csosn_id, "codigo": c.codigo, "descricao": c.descricao} for c in csosns]
    return jsonify(csosn_list), 200

@app.route('/api/cst', methods=['GET'])
def get_api_csts():
    """Retorna a lista completa de CST ICMS."""
    db = next(get_db())
    csts = db.query(Csticms).all()
    cst_list = [{"cst_id": c.cst_id, "codigo": c.codigo, "descricao": c.descricao} for c in csts]
    return jsonify(cst_list), 200

@app.route('/api/origens_mercadoria', methods=['GET'])
def get_api_origens_mercadoria():
    """Retorna a lista completa de Origens de Mercadoria."""
    db = next(get_db())
    origens = db.query(OrigemMercadoria).all()
    origens_list = [{"origem_id": o.origem_id, "codigo": o.codigo, "descricao": o.descricao} for o in origens]
    return jsonify(origens_list), 200


# --- Rotas de Administração (Front-end Rendering) ---

# Rotas para Certificados (ainda existem, mas não no menu principal)
@app.route('/admin/certificados')
def admin_certificados_list():
    db = next(get_db())
    certificados = db.query(CertificadoDigital).all()
    return render_template('admin_certificados_list.html', certificados=certificados)

@app.route('/admin/certificados/edit/<int:certificado_digital_id>', methods=['GET', 'POST'])
def admin_certificados_edit(certificado_digital_id):
    db = next(get_db())
    certificado = db.query(CertificadoDigital).get(certificado_digital_id)
    if not certificado:
        abort(404)
    
    if request.method == 'POST':
        certificado.nome_arquivo_original = request.form.get('cert_nome_arquivo_original')
        
        validade_inicio_str = request.form.get('cert_validade_inicio')
        validade_fim_str = request.form.get('cert_validade_fim')

        try:
            certificado.validade_inicio = datetime.strptime(validade_inicio_str, '%Y-%m-%d')
            certificado.validade_fim = datetime.strptime(validade_fim_str, '%Y-%m-%d')
        except ValueError:
            flash('Formato de data inválido para o certificado. Use AAAA-MM-DD.', 'danger')
            return render_template('admin_certificados_form.html', certificado=certificado, cert_data=request.form)
        certificado.ativo = request.form.get('cert_ativo') == 'on'
        
        new_password = request.form.get('cert_senha_certificado')
        if new_password: # Assume que a nova senha é fornecida em texto simples para ser criptografada
            certificado.senha_certificado = new_password.encode('utf-8') # Convertendo para bytes

        try:
            db.commit()
            flash('Certificado atualizado com sucesso!', 'success')
            return redirect(url_for('admin_clientes_edit', cliente_id=certificado.cliente_id))
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar certificado: {e}", 'danger')
    
    cert_data = {
        'nome_arquivo_original': certificado.nome_arquivo_original,
        'validade_inicio': certificado.validade_inicio.strftime('%Y-%m-%d') if certificado.validade_inicio else '',
        'validade_fim': certificado.validade_fim.strftime('%Y-%m-%d') if certificado.validade_fim else '',
        'ativo': certificado.ativo
    }
    return render_template('admin_certificados_form.html', certificado=certificado, cert_data=cert_data)

@app.route('/admin/certificados/delete/<int:certificado_digital_id>', methods=['POST'])
def admin_certificados_delete(certificado_digital_id):
    db = next(get_db())
    certificado = db.query(CertificadoDigital).get(certificado_digital_id)
    if not certificado:
        abort(404)
    cliente_id = certificado.cliente_id
    try:
        db.delete(certificado)
        db.commit()
        flash('Certificado excluído com sucesso!', 'success')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir certificado: {e}", 'danger')

    return redirect(url_for('admin_clientes_edit', cliente_id=cliente_id))

# Rotas para Regimes Tributários
@app.route('/admin/regimes_tributarios/list')
def admin_regimes_tributarios_list():
    db = next(get_db())
    regimes = db.query(RegimeTributario).all()
    return render_template('admin_regimes_tributarios_list.html', regimes=regimes)

@app.route('/admin/regimes_tributarios/add', methods=['GET', 'POST'])
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
def admin_clientes_list():
    db = next(get_db())
    clientes = db.query(Cliente).all()
    return render_template('admin_clientes_list.html', clientes=clientes)

@app.route('/admin/clientes/add', methods=['GET', 'POST'])
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
                                   ncms=ncms, # Passa para manter os dropdowns
                                   origens_mercadoria=origens_mercadoria, # Passa para manter os dropdowns
                                   cfops=cfops, csts=csts, csosns=csosns, # Passa para manter os dropdowns
                                   form_data=form_data)
        
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
                data_atualizacao=datetime.now()
            )
            db.add(novo_cliente)
            db.flush() # flush para obter o cliente_id

            # Processa o upload do certificado, se houver
            success, cert_obj = process_certificate_upload(db, novo_cliente.cliente_id, request.form, request.files)
            if not success:
                db.rollback() 
                return render_template('admin_clientes_form.html', regimes_tributarios=regimes_tributarios, ncms=ncms, origens_mercadoria=origens_mercadoria, cfops=cfops, csts=csts, csosns=csosns, form_data=form_data)

            db.commit()
            flash('Cliente e configurações iniciais cadastrados com sucesso!', 'success')
            # Redireciona para edição para que abas de produtos/regras apareçam
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
                           form_data=form_data)

@app.route('/admin/clientes/edit/<int:cliente_id>', methods=['GET', 'POST'])
def admin_clientes_edit(cliente_id):
    db = next(get_db())
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        abort(404)
    
    # Dados para as abas
    regimes_tributarios = db.query(RegimeTributario).all()
    certificados_existentes = db.query(CertificadoDigital).filter_by(cliente_id=cliente_id).all()
    produtos_existentes = db.query(Produto).filter_by(cliente_id=cliente_id).all()
    regras_existentes = db.query(RegraTributacao).filter_by(cliente_id=cliente_id).all()

    # Dados para os dropdowns dentro das abas de Produtos e Regras Tributárias
    ncms = db.query(Ncm).all()
    origens_mercadoria = db.query(OrigemMercadoria).all()
    cfops = db.query(Cfop).all()
    csts = db.query(Csticms).all()
    csosns = db.query(Csosnicms).all()

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
                                   certificados_existentes=certificados_existentes,
                                   produtos_existentes=produtos_existentes, 
                                   regras_existentes=regras_existentes, 
                                   ncms=ncms, origens_mercadoria=origens_mercadoria, 
                                   cfops=cfops, csts=csts, csosns=csosns, 
                                   form_data=form_data)
        try:
            # Processa o upload do certificado, se houver (lógica existente)
            success_cert, cert_obj = process_certificate_upload(db, cliente_id, request.form, request.files)
            if not success_cert:
                db.rollback() 
                certificados_existentes = db.query(CertificadoDigital).filter_by(cliente_id=cliente_id).all() # Recarrega
                return render_template('admin_clientes_form.html', cliente=cliente, regimes_tributarios=regimes_tributarios, certificados_existentes=certificados_existentes, produtos_existentes=produtos_existentes, regras_existentes=regras_existentes, ncms=ncms, origens_mercadoria=origens_mercadoria, cfops=cfops, csts=csts, csosns=csosns, form_data=form_data)
            
            db.commit()
            flash('Cliente e configurações atualizados com sucesso!', 'success')
            return redirect(url_for('admin_clientes_edit', cliente_id=cliente_id)) # Redireciona para recarregar com dados atualizados
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
    return render_template('admin_clientes_form.html',
                           cliente=cliente,
                           regimes_tributarios=regimes_tributarios,
                           certificados_existentes=certificados_existentes,
                           produtos_existentes=produtos_existentes, 
                           regras_existentes=regras_existentes, 
                           ncms=ncms, origens_mercadoria=origens_mercadoria, 
                           cfops=cfops, csts=csts, csosns=csosns, 
                           form_data=cliente)

@app.route('/admin/clientes/delete/<int:cliente_id>', methods=['POST'])
def admin_clientes_delete(cliente_id):
    db = next(get_db())
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        abort(404)

    try:
        db.delete(cliente)
        db.commit()
        flash('Cliente excluído com sucesso!', 'success')
    except IntegrityError:
        db.rollback()
        flash('Não é possível excluir este cliente pois ele está vinculado a outros registros (ex: NF-e).', 'danger')
    except Exception as e:
        db.rollback()
        flash(f"Erro ao excluir cliente: {e}", 'danger')

    return redirect(url_for('admin_clientes_list'))

# --- Rotas para NCM ---
@app.route('/admin/ncms/list')
def admin_ncms_list():
    db = next(get_db())
    ncms = db.query(Ncm).all()
    return render_template('admin_ncms_list.html', ncms=ncms)

@app.route('/admin/ncms/add', methods=['GET', 'POST'])
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
                ano_ato=ano_ato
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

# --- Rotas para CST ICMS ---
@app.route('/admin/cst/list')
def admin_cst_list():
    db = next(get_db())
    csts = db.query(Csticms).all()
    return render_template('admin_cst_list.html', csts=csts)

@app.route('/admin/cst/add', methods=['GET', 'POST'])
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

# --- Rotas para CFOP ---
@app.route('/admin/cfops/list')
def admin_cfops_list():
    db = next(get_db())
    cfops = db.query(Cfop).all()
    return render_template('admin_cfops_list.html', cfops=cfops)

@app.route('/admin/cfops/add', methods=['GET', 'POST'])
def admin_cfops_add():
    db = next(get_db())
    form_data = request.form
    if request.method == 'POST':
        cfop_code = request.form.get('cfop') # 'cfop' é o nome da coluna no modelo Cfop
        descricao = request.form.get('descricao')
        observacao = request.form.get('observacao')
        tipooperacao = request.form.get('tipooperacao')
        identificadordestinooperacao = request.form.get('identificadordestinooperacao')

        if not all([cfop_code, descricao, observacao]):
            flash('CFOP, Descrição e Observação são campos obrigatórios.', 'danger')
            return render_template('admin_cfops_form.html', form_data=form_data)
        
        try:
            novo_cfop = Cfop(
                cfop=cfop_code, # Use o nome da variável local
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
def admin_cfops_edit(cfop_id):
    db = next(get_db())
    cfop_obj = db.query(Cfop).get(cfop_id) # Renomeado para não conflitar com a classe Cfop
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

# --- Rotas para CSOSN ICMS ---
@app.route('/admin/csosn/list')
def admin_csosn_list():
    db = next(get_db())
    csosns = db.query(Csosnicms).all()
    return render_template('admin_csosn_list.html', csosns=csosns)

@app.route('/admin/csosn/add', methods=['GET', 'POST'])
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
# Removido do menu principal, agora o fluxo principal é através do cliente
@app.route('/admin/produtos/list') # Mantida rota de listagem, pode ser útil para debug
def admin_produtos_list():
    db = next(get_db())
    produtos = db.query(Produto).all()
    return render_template('admin_produtos_list.html', produtos=produtos)

@app.route('/admin/produtos/add', methods=['GET', 'POST'])
def admin_produtos_add():
    db = next(get_db())
    clientes = db.query(Cliente).all()
    ncms = db.query(Ncm).all()
    origens = db.query(OrigemMercadoria).all()
    form_data = request.form
    
    # Captura o cliente_id da URL se vier da tela do cliente
    # Usamos request.args.get para obter parâmetros de URL
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

        if not all([cliente_id, codigo_interno, descricao, unidade_comercial, preco_unitario_padrao_str, origem_mercadoria, tipo_item]):
            flash('Por favor, preencha todos os campos obrigatórios do produto.', 'danger')
            return render_template('admin_produtos_form.html', clientes=clientes, ncms=ncms, origens=origens, form_data=form_data, return_client_id=return_client_id)
        
        try:
            cliente_id = int(cliente_id)
            ncm_id = int(ncm_id) if ncm_id else None # NCM pode ser nulo
            preco_unitario_padrao = Decimal(preco_unitario_padrao_str)
            origem_mercadoria = int(origem_mercadoria) # Código da origem

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
                ativo=ativo
            )
            db.add(novo_produto)
            db.commit()
            flash('Produto adicionado com sucesso!', 'success')
            # Redireciona de volta para a tela de edição do cliente e para a aba de produtos
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='tab-client-products'))
            return redirect(url_for('admin_produtos_list')) # Fallback se não veio da tela do cliente
        except IntegrityError:
            db.rollback()
            flash('Código Interno do produto já existe para este cliente.', 'danger')
        except ValueError as e:
            db.rollback()
            flash(f'Erro de formato: {e}. Verifique os campos numéricos e de IDs.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar produto: {e}", 'danger')
    return render_template('admin_produtos_form.html', clientes=clientes, ncms=ncms, origens=origens, form_data=form_data, return_client_id=return_client_id)

@app.route('/admin/produtos/edit/<int:produto_id>', methods=['GET', 'POST'])
def admin_produtos_edit(produto_id):
    db = next(get_db())
    produto = db.query(Produto).get(produto_id)
    if not produto:
        abort(404)
    
    # Captura o cliente_id da URL se vier da tela do cliente
    return_client_id = request.args.get('cliente_id', type=int) 
    # Ou se não vier na URL, tenta pegar do produto que está sendo editado
    if not return_client_id and produto:
        return_client_id = produto.cliente_id

    clientes = db.query(Cliente).all()
    ncms = db.query(Ncm).all()
    origens = db.query(OrigemMercadoria).all()
    form_data = request.form

    if request.method == 'POST':
        produto.cliente_id = int(request.form.get('cliente_id'))
        produto.codigo_interno = request.form.get('codigo_interno')
        produto.descricao = request.form.get('descricao')
        produto.ncm_id = int(request.form.get('ncm_id')) if request.form.get('ncm_id') else None
        produto.cest = request.form.get('cest')
        produto.unidade_comercial = request.form.get('unidade_comercial')
        preco_unitario_padrao = request.form.get('preco_unitario_padrao') # Captura como str para Decimal
        produto.origem_mercadoria = int(request.form.get('origem_mercadoria'))
        produto.tipo_item = request.form.get('tipo_item')
        produto.ativo = request.form.get('ativo') == 'on'

        if not all([produto.cliente_id, produto.codigo_interno, produto.descricao, produto.unidade_comercial, preco_unitario_padrao, produto.origem_mercadoria, produto.tipo_item]):
            flash('Por favor, preencha todos os campos obrigatórios do produto.', 'danger')
            return render_template('admin_produtos_form.html', produto=produto, clientes=clientes, ncms=ncms, origens=origens, form_data=form_data, return_client_id=return_client_id)
        
        try:
            produto.preco_unitario_padrao = Decimal(preco_unitario_padrao) # Converte para Decimal aqui
            db.commit()
            flash('Produto atualizado com sucesso!', 'success')
            # Redireciona de volta para a tela de edição do cliente e para a aba de produtos
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='tab-client-products'))
            return redirect(url_for('admin_produtos_list')) # Fallback se não veio da tela do cliente
        except IntegrityError:
            db.rollback()
            flash('Código Interno do produto já existe para este cliente.', 'danger')
        except ValueError as e:
            db.rollback()
            flash(f'Erro de formato: {e}. Verifique os campos numéricos e de IDs.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar produto: {e}", 'danger')
    return render_template('admin_produtos_form.html', produto=produto, clientes=clientes, ncms=ncms, origens=origens, form_data=produto, return_client_id=return_client_id)

@app.route('/admin/produtos/delete/<int:produto_id>', methods=['POST'])
def admin_produtos_delete(produto_id):
    db = next(get_db())
    produto = db.query(Produto).get(produto_id)
    if not produto:
        abort(404)
    
    # Captura o cliente_id para redirecionar de volta corretamente
    return_client_id = produto.cliente_id if produto else None

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
    
    # Redireciona de volta para a tela de edição do cliente e para a aba de produtos
    if return_client_id:
        return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='tab-client-products'))
    return redirect(url_for('admin_produtos_list')) # Fallback

# --- Rotas para Regras de Tributação ---
# Removido do menu principal, agora o fluxo principal é através do cliente
@app.route('/admin/regras_tributacao/list') # Mantida rota de listagem, pode ser útil para debug
def admin_regras_tributacao_list():
    db = next(get_db())
    regras = db.query(RegraTributacao).all()
    return render_template('admin_regras_tributacao_list.html', regras=regras)

@app.route('/admin/regras_tributacao/add', methods=['GET', 'POST'])
def admin_regras_tributacao_add():
    db = next(get_db())
    clientes = db.query(Cliente).all()
    regimes_tributarios = db.query(RegimeTributario).all()
    cfops = db.query(Cfop).all()
    ncms = db.query(Ncm).all()
    csts = db.query(Csticms).all()
    csosns = db.query(Csosnicms).all()
    form_data = request.form

    # Captura o cliente_id da URL se vier da tela do cliente
    return_client_id = request.args.get('cliente_id', type=int) 

    

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        regime_tributario_id = request.form.get('regime_tributario_id')
        cfop_id = request.form.get('cfop_id')
        ncm_id = request.form.get('ncm_id')
        uf_origem = request.form.get('uf_origem')
        uf_destino = request.form.get('uf_destino')
        tipo_item = request.form.get('tipo_item')
        prioridade_str = request.form.get('prioridade')
        cst_icms = request.form.get('cst_icms')
        csosn_icms = request.form.get('csosn_icms')
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
            flash('Regime Tributário e CFOP são campos obrigatórios para Regra de Tributação.', 'danger')
            return render_template('admin_regras_tributacao_form.html', clientes=clientes, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, form_data=form_data, return_client_id=return_client_id)
        
        try:
            # Conversão de tipos
            cliente_id = int(cliente_id) if cliente_id else None
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
                cst_icms=cst_icms,
                csosn_icms=csosn_icms,
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
                ativo=ativo
            )
            db.add(nova_regra)
            db.commit()
            flash('Regra de Tributação adicionada com sucesso!', 'success')
            # Redireciona de volta para a tela de edição do cliente E ABRE A ABA DE REGRAS
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='tab-client-rules'))
            return redirect(url_for('admin_regras_tributacao_list')) # Fallback
        except ValueError as e:
            db.rollback()
            flash(f'Erro de formato: {e}. Verifique os campos numéricos e de IDs.', 'danger')
        except IntegrityError:
            db.rollback()
            flash('Erro de integridade ao adicionar regra. Verifique se os IDs existem ou se há duplicatas.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao adicionar Regra de Tributação: {e}", 'danger')
    return render_template('admin_regras_tributacao_form.html', clientes=clientes, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, form_data=form_data, return_client_id=return_client_id)

@app.route('/admin/regras_tributacao/edit/<int:regra_tributacao_id>', methods=['GET', 'POST'])
def admin_regras_tributacao_edit(regra_tributacao_id):
    db = next(get_db())
    regra = db.query(RegraTributacao).get(regra_tributacao_id)
    if not regra:
        abort(404)
    
    # Captura o cliente_id da URL se vier da tela do cliente
    return_client_id = request.args.get('cliente_id', type=int) 
    # Ou se não vier na URL, tenta pegar da regra que está sendo editada
    if not return_client_id and regra:
        return_client_id = regra.cliente_id

    clientes = db.query(Cliente).all()
    regimes_tributarios = db.query(RegimeTributario).all()
    cfops = db.query(Cfop).all()
    ncms = db.query(Ncm).all()
    csts = db.query(Csticms).all()
    csosns = db.query(Csosnicms).all()
    form_data = request.form

    if request.method == 'POST':
        regra.cliente_id = int(request.form.get('cliente_id')) if request.form.get('cliente_id') else None
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
            return render_template('admin_regras_tributacao_form.html', regra=regra, clientes=clientes, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, form_data=form_data, return_client_id=return_client_id)
        
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
            # Redireciona de volta para a tela de edição do cliente E ABRE A ABA DE REGRAS
            if return_client_id:
                return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='tab-client-rules'))
            return redirect(url_for('admin_regras_tributacao_list')) # Fallback
        except ValueError as e:
            db.rollback()
            flash(f'Erro de formato: {e}. Verifique os campos numéricos e de IDs.', 'danger')
        except IntegrityError:
            db.rollback()
            flash('Erro de integridade ao atualizar regra. Verifique se os IDs existem ou se há duplicatas.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar Regra de Tributação: {e}", 'danger')
    return render_template('admin_regras_tributacao_form.html', regra=regra, clientes=clientes, regimes_tributarios=regimes_tributarios, cfops=cfops, ncms=ncms, csts=csts, csosns=csosns, form_data=regra, return_client_id=return_client_id)

@app.route('/admin/regras_tributacao/delete/<int:regra_tributacao_id>', methods=['POST'])
def admin_regras_tributacao_delete(regra_tributacao_id):
    db = next(get_db())
    regra = db.query(RegraTributacao).get(regra_tributacao_id)
    if not regra:
        abort(404)
    
    # Captura o cliente_id para redirecionar de volta corretamente
    return_client_id = regra.cliente_id if regra else None

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
    
    # Redireciona de volta para a tela de edição do cliente E ABRE A ABA DE REGRAS
    if return_client_id:
        return redirect(url_for('admin_clientes_edit', cliente_id=return_client_id, _anchor='tab-client-rules'))
    return redirect(url_for('admin_regras_tributacao_list')) # Fallback

# --- Rotas para OrigemMercadoria ---
@app.route('/admin/origens_mercadoria/list')
def admin_origens_mercadoria_list():
    db = next(get_db())
    origens = db.query(OrigemMercadoria).all()
    return render_template('admin_origens_mercadoria_list.html', origens=origens)

@app.route('/admin/origens_mercadoria/add', methods=['GET', 'POST'])
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
def admin_destinatarios_nfe_list():
    db = next(get_db())
    destinatarios = db.query(DestinatarioNFe).all()
    return render_template('destinatario/lista.html', destinatarios=destinatarios)

@app.route('/admin/destinatarios_nfe/add', methods=['GET', 'POST'])
def admin_destinatarios_nfe_add():
    db = next(get_db())
    form_data = request.form # Para manter dados do formulário em caso de erro

    if request.method == 'POST':
        # Mapeamento e validação dos campos
        # Note que codigo_uf e nome_municipio são preenchidos pela busca CEP
        data = {
            'tipo_pessoa': request.form.get('tipo_pessoa'),
            'nome_razao_social': request.form.get('nome_razao_social'),
            'cpf_cnpj': request.form.get('cpf_cnpj').replace('.', '').replace('/', '').replace('-', ''), # Limpa máscara
            'ie': request.form.get('ie'),
            'ie_indicador_nfe': request.form.get('ie_indicador_nfe'),
            'email': request.form.get('email'),
            'telefone': request.form.get('telefone').replace('(', '').replace(')', '').replace(' ', '').replace('-', ''), # Limpa máscara
            'logradouro': request.form.get('logradouro'),
            'numero': request.form.get('numero'),
            'complemento': request.form.get('complemento'),
            'bairro': request.form.get('bairro'),
            'cep': request.form.get('cep').replace('-', ''), # Limpa máscara
            'codigo_municipio': request.form.get('codigo_municipio'),
            'nome_municipio': request.form.get('nome_municipio'),
            'uf': request.form.get('uf'),
            'codigo_uf': request.form.get('codigo_uf'), # Campo para código IBGE da UF
            'codigo_pais': request.form.get('codigo_pais') or '1058',
            'nome_pais': request.form.get('nome_pais') or 'Brasil',
        }

        # Validação de campos obrigatórios (adapte conforme sua necessidade)
        required_fields = ['tipo_pessoa', 'nome_razao_social', 'cpf_cnpj', 'ie_indicador_nfe',
                           'logradouro', 'numero', 'bairro', 'cep', 'codigo_municipio',
                           'nome_municipio', 'uf', 'codigo_uf']
        
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            flash(f"Preencha todos os campos obrigatórios. Faltando: {', '.join(missing_fields)}", 'danger')
            return render_template('destinatario/cadastro.html', form_data=data)

        try:
            novo_destinatario = DestinatarioNFe(**data)
            db.add(novo_destinatario)
            db.commit()
            flash('Destinatário cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_destinatarios_nfe_list'))
        except IntegrityError:
            db.rollback()
            flash('CPF/CNPJ já cadastrado para outro destinatário.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao cadastrar destinatário: {e}", 'danger')

    return render_template('destinatario/cadastro.html', form_data=form_data)

@app.route('/admin/destinatarios_nfe/edit/<int:destinatario_id>', methods=['GET', 'POST'])
def admin_destinatarios_nfe_edit(destinatario_id):
    db = next(get_db())
    destinatario = db.query(DestinatarioNFe).get(destinatario_id)
    if not destinatario:
        abort(404)
    form_data = request.form # Para manter dados do formulário em caso de erro no POST

    if request.method == 'POST':
        destinatario.tipo_pessoa = request.form.get('tipo_pessoa')
        destinatario.nome_razao_social = request.form.get('nome_razao_social')
        destinatario.cpf_cnpj = request.form.get('cpf_cnpj').replace('.', '').replace('/', '').replace('-', '')
        destinatario.ie = request.form.get('ie')
        destinatario.ie_indicador_nfe = request.form.get('ie_indicador_nfe')
        destinatario.email = request.form.get('email')
        destinatario.telefone = request.form.get('telefone').replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
        destinatario.logradouro = request.form.get('logradouro')
        destinatario.numero = request.form.get('numero')
        destinatario.complemento = request.form.get('complemento')
        destinatario.bairro = request.form.get('bairro')
        destinatario.cep = request.form.get('cep').replace('-', '')
        destinatario.codigo_municipio = request.form.get('codigo_municipio')
        destinatario.nome_municipio = request.form.get('nome_municipio')
        destinatario.uf = request.form.get('uf')
        destinatario.codigo_uf = request.form.get('codigo_uf')
        destinatario.codigo_pais = request.form.get('codigo_pais') or '1058'
        destinatario.nome_pais = request.form.get('nome_pais') or 'Brasil'
        destinatario.data_atualizacao = datetime.now()

        required_fields = ['tipo_pessoa', 'nome_razao_social', 'cpf_cnpj', 'ie_indicador_nfe',
                           'logradouro', 'numero', 'bairro', 'cep', 'codigo_municipio',
                           'nome_municipio', 'uf', 'codigo_uf']
        
        missing_fields = [f for f in required_fields if not getattr(destinatario, f)]
        if missing_fields:
            flash(f"Preencha todos os campos obrigatórios. Faltando: {', '.join(missing_fields)}", 'danger')
            return render_template('destinatario/editar.html', destinatario=destinatario, form_data=request.form)

        try:
            db.commit()
            flash('Destinatário atualizado com sucesso!', 'success')
            return redirect(url_for('admin_destinatarios_nfe_list'))
        except IntegrityError:
            db.rollback()
            flash('CPF/CNPJ já cadastrado para outro destinatário.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro ao atualizar destinatário: {e}", 'danger')

    return render_template('destinatario/editar.html', destinatario=destinatario, form_data=destinatario)

@app.route('/admin/destinatarios_nfe/delete/<int:destinatario_id>', methods=['POST'])
def admin_destinatarios_nfe_delete(destinatario_id):
    db = next(get_db())
    destinatario = db.query(DestinatarioNFe).get(destinatario_id)
    if not destinatario:
        abort(404)
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
    return redirect(url_for('admin_destinatarios_nfe_list'))

# --- Rotas para Motivos de Desoneração ICMS ---
@app.route('/admin/motivos_desoneracao/list')
def admin_motivos_desoneracao_list():
    db = next(get_db())
    motivos = db.query(MotivoDesoneracao).order_by(MotivoDesoneracao.codigo).all()
    return render_template('tributacao/motivos_desoneracao.html', motivos=motivos)

# --- Atualização de rota de Clientes para incluir o link para motivos de desoneração ---
# (Certifique-se de que esta rota já está no seu app.py e a aba 'tab-client-rules' existe no admin_clientes_form.html)
@app.route('/admin/clientes/edit/<int:cliente_id>', methods=['GET', 'POST'])
def admin_clientes_edit(cliente_id):
    db = next(get_db())
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        abort(404)
    
    # Dados para as abas
    regimes_tributarios = db.query(RegimeTributario).all()
    certificados_existentes = db.query(CertificadoDigital).filter_by(cliente_id=cliente_id).all()
    produtos_existentes = db.query(Produto).filter_by(cliente_id=cliente_id).all()
    regras_existentes = db.query(RegraTributacao).filter_by(cliente_id=cliente_id).all()

    # Dados para os dropdowns dentro das abas de Produtos e Regras Tributárias
    ncms = db.query(Ncm).all()
    origens_mercadoria = db.query(OrigemMercadoria).all()
    cfops = db.query(Cfop).all()
    csts = db.query(Csticms).all()
    csosns = db.query(Csosnicms).all()
    
    # Adicione a busca dos motivos de desoneração para o template
    motivos_desoneracao = db.query(MotivoDesoneracao).order_by(MotivoDesoneracao.codigo).all()

    form_data = request.form # Para manter dados do formulário em caso de erro

    if request.method == 'POST':
        # ... (sua lógica de atualização de cliente existente, como já está) ...
        # Se for um POST, você pode querer recarregar motivos_desoneracao também em caso de erro.
        flash("Funcionalidade de atualização de cliente acionada.", "info") # Apenas para debug, remova

    # Para GET, use o objeto cliente para pré-preencher o formulário
    return render_template('admin_clientes_form.html',
                           cliente=cliente,
                           regimes_tributarios=regimes_tributarios,
                           certificados_existentes=certificados_existentes,
                           produtos_existentes=produtos_existentes, 
                           regras_existentes=regras_existentes, 
                           ncms=ncms, origens_mercadoria=origens_mercadoria, 
                           cfops=cfops, csts=csts, csosns=csosns, 
                           motivos_desoneracao=motivos_desoneracao, # PASSE PARA O TEMPLATE
                           form_data=cliente)


# --- Configuração de Execução Local ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    # host='0.0.0.0' permite que o servidor seja acessível de outras máquinas na rede local
    # Para depuração local apenas, 'localhost' ou '127.0.0.1' pode ser suficiente.
    app.run(debug=True, host='0.0.0.0', port=port)
# app.py
from flask import Flask, jsonify, request, abort, render_template, redirect, url_for, flash
import json
import os
import uuid
from datetime import datetime, date
import base64
from decimal import Decimal

# Importe os modelos necessários
from database.models import Base, Cfop, Ncm, Produto, Cliente, RegimeTributario, CertificadoDigital, NFeEmitidas, RegraTributacao, Csosnicms, Csticms, serialize_sqla_object

from sqlalchemy import create_engine, DateTime, Date, Numeric, LargeBinary
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

app.secret_key = 'keysegura123' # NECESSÁRIO PARA USAR flash (SUBSTITUA POR UMA CHAVE SEGURA EM PRODUÇÃO)

# --- Configuração do Banco de Dados ---
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Mo2505@host:5432/sjtnfe")
# Configura o tipo de DB para o JSONB condicional (se for usar PgSQL)
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    os.environ['DB_TYPE'] = 'postgresql'

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Adicione uma dependência para obter a sessão do DB em cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Rotas para Certificados Digitais (Web Admin) ---

@app.route('/admin/certificados')
def admin_certificados_list():
    """Exibe a lista de Certificados Digitais na interface web."""
    db = next(get_db())
    certificados = db.query(CertificadoDigital).all()
    # Para exibição, o conteudo_certificado e senha_certificado não devem ser mostrados,
    # mas o to_dict() os serializa. Você pode querer removê-los do dicionário aqui ou no template.
    return render_template('admin_certificados_list.html', certificados=certificados)


@app.route('/admin/certificados/add', methods=['GET', 'POST'])
def admin_certificados_add():
    """Adiciona um novo Certificado Digital via interface web."""
    db = next(get_db())
    clientes = db.query(Cliente).all() # Para preencher o dropdown de cliente_id

    if request.method == 'POST':
        errors = []
        
        # Obtenha os dados do formulário
        cliente_id = request.form.get('cliente_id')
        senha_certificado_str = request.form.get('senha_certificado')
        validade_inicio_str = request.form.get('validade_inicio')
        validade_fim_str = request.form.get('validade_fim')
        ativo = 'ativo' in request.form
        nome_arquivo_original = request.form.get('nome_arquivo_original')
        
        # Lidar com o upload do arquivo
        uploaded_file = request.files.get('conteudo_certificado_file')
        conteudo_certificado_bytes = None
        if uploaded_file and uploaded_file.filename != '':
            conteudo_certificado_bytes = uploaded_file.read()
            # O nome do arquivo original pode ser o nome do arquivo enviado, se não for fornecido um nome_arquivo_original no form
            if not nome_arquivo_original:
                nome_arquivo_original = uploaded_file.filename
        else:
            errors.append("O arquivo do certificado é obrigatório.")
        
        # Validação básica
        if not cliente_id:
            errors.append("O Cliente é obrigatório.")
        if not senha_certificado_str:
            errors.append("A Senha do Certificado é obrigatória.")
        if not validade_inicio_str:
            errors.append("A Data de Validade Inicial é obrigatória.")
        if not validade_fim_str:
            errors.append("A Data de Validade Final é obrigatória.")

        # Conversão de tipos e tratamento de erros
        try:
            cliente_id = int(cliente_id) if cliente_id else None
            # Simplesmente convertendo a senha para bytes para demonstração.
            # Lembre-se: EM PRODUÇÃO, A SENHA DEVE SER CRIPTOGRAFADA.
            senha_certificado_bytes = senha_certificado_str.encode('utf-8') if senha_certificado_str else None
            validade_inicio = datetime.fromisoformat(validade_inicio_str) if validade_inicio_str else None
            validade_fim = datetime.fromisoformat(validade_fim_str) if validade_fim_str else None
        except ValueError:
            errors.append("Formato de ID de cliente ou data inválido.")

        if errors:
            flash(f"Erro no preenchimento do formulário: {'. '.join(errors)}", 'danger')
            return render_template(
                'admin_certificados_form.html',
                clientes=clientes,
                certificado=request.form # Passa os dados para preencher o form novamente
            )

        try:
            new_certificado = CertificadoDigital(
                cliente_id=cliente_id,
                conteudo_certificado=conteudo_certificado_bytes, # Lembre-se da criptografia!
                senha_certificado=senha_certificado_bytes,     # Lembre-se da criptografia!
                validade_inicio=validade_inicio,
                validade_fim=validade_fim,
                ativo=ativo,
                nome_arquivo_original=nome_arquivo_original,
                data_upload=datetime.now() # A data de upload é definida automaticamente
            )
            db.add(new_certificado)
            db.commit()
            flash('Certificado Digital cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_certificados_list'))
        except IntegrityError as e:
            db.rollback()
            flash(f"Erro de integridade ao cadastrar certificado: {e.orig.pgerror}", 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro interno ao cadastrar certificado: {e}", 'danger')
            
    return render_template(
        'admin_certificados_form.html',
        clientes=clientes,
        certificado=None # Nenhum certificado existente para preencher o form
    )

@app.route('/admin/certificados/edit/<int:certificado_digital_id>', methods=['GET', 'POST'])
def admin_certificados_edit(certificado_digital_id):
    """Edita um Certificado Digital existente via interface web."""
    db = next(get_db())
    certificado = db.query(CertificadoDigital).get(certificado_digital_id)
    if not certificado:
        abort(404, description="Certificado Digital não encontrado.")

    clientes = db.query(Cliente).all()

    if request.method == 'POST':
        errors = []
        
        # Obtenha os dados do formulário
        cliente_id = request.form.get('cliente_id')
        senha_certificado_str = request.form.get('senha_certificado')
        validade_inicio_str = request.form.get('validade_inicio')
        validade_fim_str = request.form.get('validade_fim')
        ativo = 'ativo' in request.form
        nome_arquivo_original = request.form.get('nome_arquivo_original')

        # Lidar com o upload do novo arquivo (opcional na edição)
        uploaded_file = request.files.get('conteudo_certificado_file')
        if uploaded_file and uploaded_file.filename != '':
            certificado.conteudo_certificado = uploaded_file.read() # Atualiza o conteúdo
            if not nome_arquivo_original:
                certificado.nome_arquivo_original = uploaded_file.filename
            else:
                certificado.nome_arquivo_original = nome_arquivo_original
        else:
            # Se não houver novo upload, mantém o nome original existente ou o que foi digitado
            if nome_arquivo_original:
                certificado.nome_arquivo_original = nome_arquivo_original

        # Validação básica
        if not cliente_id:
            errors.append("O Cliente é obrigatório.")
        if not senha_certificado_str:
            errors.append("A Senha do Certificado é obrigatória.")
        if not validade_inicio_str:
            errors.append("A Data de Validade Inicial é obrigatória.")
        if not validade_fim_str:
            errors.append("A Data de Validade Final é obrigatória.")

        # Conversão de tipos e tratamento de erros
        try:
            certificado.cliente_id = int(cliente_id) if cliente_id else None
            # Senha só é atualizada se for fornecida no formulário de edição
            if senha_certificado_str:
                 # Lembre-se: EM PRODUÇÃO, A SENHA DEVE SER CRIPTOGRAFADA.
                certificado.senha_certificado = senha_certificado_str.encode('utf-8')
            certificado.validade_inicio = datetime.fromisoformat(validade_inicio_str) if validade_inicio_str else None
            certificado.validade_fim = datetime.fromisoformat(validade_fim_str) if validade_fim_str else None
            certificado.ativo = ativo
        except ValueError:
            errors.append("Formato de ID de cliente ou data inválido.")

        if errors:
            flash(f"Erro no preenchimento do formulário: {'. '.join(errors)}", 'danger')
            return render_template(
                'admin_certificados_form.html',
                clientes=clientes,
                certificado=certificado # Passa o objeto certificado existente para preencher o formulário
            )

        try:
            db.commit()
            flash('Certificado Digital atualizado com sucesso!', 'success')
            return redirect(url_for('admin_certificados_list'))
        except IntegrityError as e:
            db.rollback()
            flash(f"Erro de integridade ao atualizar certificado: {e.orig.pgerror}", 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro interno ao atualizar certificado: {e}", 'danger')

    # Para requisições GET, renderiza o formulário com os dados atuais do certificado
    return render_template(
        'admin_certificados_form.html',
        clientes=clientes,
        certificado=certificado # Passa o objeto certificado para o formulário GET
    )

@app.route('/admin/certificados/delete/<int:certificado_digital_id>', methods=['POST'])
def admin_certificados_delete(certificado_digital_id):
    """Deleta um Certificado Digital via interface web."""
    db = next(get_db())
    certificado = db.query(CertificadoDigital).get(certificado_digital_id)
    if not certificado:
        abort(404, description="Certificado Digital não encontrado para exclusão.")
    
    try:
        db.delete(certificado)
        db.commit()
        flash('Certificado Digital excluído com sucesso!', 'success')
        return redirect(url_for('admin_certificados_list'))
    except IntegrityError:
        db.rollback()
        flash('Não foi possível excluir o Certificado Digital devido a dependências em outras tabelas.', 'danger')
        return redirect(url_for('admin_certificados_list'))
    except Exception as e:
        db.rollback()
        flash(f"Erro ao deletar certificado: {e}", 'danger')
        return redirect(url_for('admin_certificados_list'))


# --- Funções Auxiliares para Manipulação de Dados ---
def parse_request_data(model, data):
    """Converte dados da requisição para o formato do modelo, lidando com tipos especiais."""
    parsed_data = {}
    for column in model.__table__.columns:
        col_name = column.name
        if col_name in data:
            value = data[col_name]
            if isinstance(column.type, (type(DateTime()), type(Date()))): # Checa se é DateTime ou Date
                if value:
                    try:
                        # Tenta parsear do formato ISO 8601 (padrão JSON)
                        parsed_data[col_name] = datetime.fromisoformat(value)
                    except ValueError:
                        # Se falhar, tenta outros formatos comuns, ou você pode exigir ISO
                        try:
                            parsed_data[col_name] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            if isinstance(column.type, type(Date())):
                                try:
                                    parsed_data[col_name] = datetime.strptime(value, '%Y-%m-%d').date()
                                except ValueError:
                                    abort(400, description=f"Formato de data/hora inválido para '{col_name}'. Use YYYY-MM-DDTHH:MM:SS ou YYYY-MM-DD.")
                            else:
                                abort(400, description=f"Formato de data/hora inválido para '{col_name}'. Use YYYY-MM-DDTHH:MM:SS.")
                else:
                    parsed_data[col_name] = None # Permite nulo se o campo permitir
            elif isinstance(column.type, type(Numeric())):
                try:
                    parsed_data[col_name] = Decimal(str(value))
                except (TypeError, ValueError):
                    abort(400, description=f"Valor numérico inválido para '{col_name}'.")
            elif isinstance(column.type, type(LargeBinary())):
                if value:
                    try:
                        parsed_data[col_name] = base64.b64decode(value)
                    except (TypeError, ValueError):
                        abort(400, description=f"Conteúdo binário inválido para '{col_name}'. Deve ser base64.")
                else:
                    parsed_data[col_name] = None
            else:
                parsed_data[col_name] = value
    return parsed_data

# --- Rotas da API ---

@app.route('/')
def home():
    """Rota inicial para verificar se a API está online."""
    return jsonify({
        "message": "API de Emissão de NF está online!",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Verifica a saúde da API.",
            "/cfops": "Gerencia CFOPs.",
            "/ncms": "Gerencia NCMs.",
            "/produtos": "Gerencia Produtos.",
            "/clientes": "Gerencia Clientes.",
            "/certificados": "Gerencia Certificados Digitais.",
            "/nfes": "Gerencia NF-e Emitidas.",
            "/regimes_tributarios": "Gerencia Regimes Tributários.",
            "/regras_tributacao": "Gerencia Regras de Tributação.",
            "/csosn": "Gerencia CSOSN ICMS.",
            "/cst": "Gerencia CST ICMS."
        }
    })



@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar a saúde da API."""
    return jsonify({"status": "UP", "timestamp": datetime.now().isoformat()}), 200

# --- Rotas para RegimeTributario ---
@app.route('/regimes_tributarios', methods=['GET'])
def get_regimes_tributarios():
    """Retorna a lista completa de Regimes Tributários."""
    db = next(get_db())
    regimes = db.query(RegimeTributario).all()
    return jsonify([regime.to_dict() for regime in regimes]), 200

@app.route('/regimes_tributarios/<int:regime_id>', methods=['GET'])
def get_regime_tributario(regime_id):
    """Retorna um Regime Tributário específico pelo ID."""
    db = next(get_db())
    regime = db.query(RegimeTributario).get(regime_id)
    if not regime:
        abort(404, description="Regime Tributário não encontrado.")
    return jsonify(regime.to_dict()), 200

@app.route('/regimes_tributarios', methods=['POST'])
def create_regime_tributario():
    """Cria um novo Regime Tributário."""
    db = next(get_db())
    data = request.json
    if not data or 'nome' not in data:
        abort(400, description="Dados insuficientes. 'nome' é obrigatório.")
    
    try:
        new_regime = RegimeTributario(
            nome=data['nome'],
            descricao=data.get('descricao')
        )
        db.add(new_regime)
        db.commit()
        return jsonify(new_regime.to_dict()), 201 # 201 Created
    except IntegrityError as e:
        db.rollback()
        abort(409, description=f"Erro de integridade: {e.orig.pgerror}") # Conflict if 'nome' is duplicated
    except Exception as e:
        db.rollback()
        abort(500, description=f"Erro interno ao criar Regime Tributário: {e}")

@app.route('/regimes_tributarios/<int:regime_id>', methods=['PUT'])
def update_regime_tributario(regime_id):
    """Atualiza um Regime Tributário existente."""
    db = next(get_db())
    regime = db.query(RegimeTributario).get(regime_id)
    if not regime:
        abort(404, description="Regime Tributário não encontrado.")
    
    data = request.json
    if not data:
        abort(400, description="Nenhum dado fornecido para atualização.")

    try:
        # Atualiza apenas os campos fornecidos no request.json
        for key, value in data.items():
            if hasattr(regime, key):
                setattr(regime, key, value)
        
        db.commit()
        return jsonify(regime.to_dict()), 200
    except IntegrityError as e:
        db.rollback()
        abort(409, description=f"Erro de integridade: {e.orig.pgerror}")
    except Exception as e:
        db.rollback()
        abort(500, description=f"Erro interno ao atualizar Regime Tributário: {e}")

@app.route('/regimes_tributarios/<int:regime_id>', methods=['DELETE'])
def delete_regime_tributario(regime_id):
    """Deleta um Regime Tributário."""
    db = next(get_db())
    regime = db.query(RegimeTributario).get(regime_id)
    if not regime:
        abort(404, description="Regime Tributário não encontrado.")
    
    try:
        db.delete(regime)
        db.commit()
        return jsonify({"message": "Regime Tributário excluído com sucesso"}), 204 # 204 No Content
    except IntegrityError as e:
        db.rollback()
        abort(409, description=f"Não foi possível excluir o Regime Tributário devido a dependências em outras tabelas. Erro: {e.orig.pgerror}")
    except Exception as e:
        db.rollback()
        abort(500, description=f"Erro interno ao deletar Regime Tributário: {e}")

@app.route('/cfops', methods=['GET'])
def get_cfops():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    cfops = db.query(Cfop).all()
    cfop_list = [{"cfop": cfop.cfop, "descricao": cfop.descricao} for cfop in cfops]
    return jsonify(cfop_list), 200
# --- Rotas para Cfop ---
# As rotas de GET ALL já existem, as de GET BY ID, POST, PUT, DELETE seguem o mesmo padrão
@app.route('/cfops/<int:cfop_id>', methods=['GET'])
def get_cfop(cfop_id):
    db = next(get_db())
    cfop_obj = db.query(Cfop).get(cfop_id) # Renomeado para evitar conflito com a classe Cfop
    if not cfop_obj:
        abort(404, description="CFOP não encontrado.")
    return jsonify(cfop_obj.to_dict()), 200

@app.route('/cfops', methods=['POST'])
def create_cfop():
    db = next(get_db())
    data = request.json
    # cfop, descricao, observacao são NOT NULL no seu modelo
    if not data or not all(k in data for k in ['cfop', 'descricao', 'observacao']):
        abort(400, description="Dados insuficientes. 'cfop', 'descricao', 'observacao' são obrigatórios.")
    
    try:
        new_cfop = Cfop(
            cfop=data['cfop'],
            descricao=data['descricao'],
            observacao=data['observacao'],
            tipooperacao=data.get('tipooperacao'),
            identificadordestinooperacao=data.get('identificadordestinooperacao')
        )
        db.add(new_cfop)
        db.commit()
        return jsonify(new_cfop.to_dict()), 201
    except IntegrityError as e:
        db.rollback()
        abort(409, description=f"Erro de integridade (CFOP duplicado, etc.): {e.orig.pgerror}")
    except Exception as e:
        db.rollback()
        abort(500, description=f"Erro interno ao criar CFOP: {e}")

@app.route('/cfops/<int:cfop_id>', methods=['PUT'])
def update_cfop(cfop_id):
    db = next(get_db())
    cfop_obj = db.query(Cfop).get(cfop_id)
    if not cfop_obj:
        abort(404, description="CFOP não encontrado.")
    
    data = request.json
    if not data:
        abort(400, description="Nenhum dado fornecido para atualização.")

    try:
        # Atualiza os campos que não são a PK
        if 'cfop' in data: cfop_obj.cfop = data['cfop']
        if 'descricao' in data: cfop_obj.descricao = data['descricao']
        if 'observacao' in data: cfop_obj.observacao = data['observacao']
        if 'tipooperacao' in data: cfop_obj.tipooperacao = data['tipooperacao']
        if 'identificadordestinooperacao' in data: cfop_obj.identificadordestinooperacao = data['identificadordestinooperacao']
        
        db.commit()
        return jsonify(cfop_obj.to_dict()), 200
    except IntegrityError as e:
        db.rollback()
        abort(409, description=f"Erro de integridade: {e.orig.pgerror}")
    except Exception as e:
        db.rollback()
        abort(500, description=f"Erro interno ao atualizar CFOP: {e}")

@app.route('/cfops/<int:cfop_id>', methods=['DELETE'])
def delete_cfop(cfop_id):
    db = next(get_db())
    cfop_obj = db.query(Cfop).get(cfop_id)
    if not cfop_obj:
        abort(404, description="CFOP não encontrado.")
    
    try:
        db.delete(cfop_obj)
        db.commit()
        return jsonify({"message": "CFOP excluído com sucesso"}), 204
    except IntegrityError as e:
        db.rollback()
        abort(409, description=f"Não foi possível excluir o CFOP devido a dependências em outras tabelas. Erro: {e.orig.pgerror}")
    except Exception as e:
        db.rollback()
        abort(500, description=f"Erro interno ao deletar CFOP: {e}")

@app.route('/ncms', methods=['GET'])
def get_ncms():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    ncms = db.query(Ncm).all()
    ncm_list = [{"codigo": ncm.codigo, "descricao": ncm.descricao} for ncm in ncms]
    return jsonify(ncm_list), 200

# --- Rotas para Ncm ---
# Primary Key: ncm_id, Campo Único: codigo
@app.route('/ncms/<int:ncm_id>', methods=['GET'])
def get_ncm(ncm_id):
    db = next(get_db())
    obj = db.query(Ncm).get(ncm_id)
    if not obj: abort(404, description="NCM não encontrado.")
    return jsonify(obj.to_dict()), 200

@app.route('/ncms', methods=['POST'])
def create_ncm():
    db = next(get_db())
    data = parse_request_data(Ncm, request.json)
    required_fields = ['codigo', 'descricao']
    if not all(field in data and data[field] is not None for field in required_fields):
        abort(400, description=f"Campos obrigatórios ausentes ou nulos: {', '.join(required_fields)}.")
    try:
        new_obj = Ncm(**data)
        db.add(new_obj); db.commit(); return jsonify(new_obj.to_dict()), 201
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/ncms/<int:ncm_id>', methods=['PUT'])
def update_ncm(ncm_id):
    db = next(get_db()); obj = db.query(Ncm).get(ncm_id)
    if not obj: abort(404, description="NCM não encontrado.")
    data = parse_request_data(Ncm, request.json)
    try:
        for key, value in data.items(): setattr(obj, key, value)
        db.commit(); return jsonify(obj.to_dict()), 200
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/ncms/<int:ncm_id>', methods=['DELETE'])
def delete_ncm(ncm_id):
    db = next(get_db()); obj = db.query(Ncm).get(ncm_id)
    if not obj: abort(404, description="NCM não encontrado.")
    try: db.delete(obj); db.commit(); return jsonify({"message": "NCM excluído."}), 204
    except IntegrityError as e: db.rollback(); abort(409, description=f"Não foi possível excluir: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/produtos', methods=['GET'])
def get_produtos():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    produtos = db.query(Produto).all()
    produto_list = [{"codigo": produtos.codigo_interno, "descricao": produtos.descricao} for produto in produtos]
    return jsonify(produto_list), 200

# --- Rotas para Produto ---
# Primary Key: produto_id, UniqueConstraint: (cliente_id, codigo_interno)
@app.route('/produtos/<int:produto_id>', methods=['GET'])
def get_produto(produto_id):
    db = next(get_db())
    obj = db.query(Produto).get(produto_id)
    if not obj: abort(404, description="Produto não encontrado.")
    return jsonify(obj.to_dict()), 200

@app.route('/produtos', methods=['POST'])
def create_produto():
    db = next(get_db())
    data = parse_request_data(Produto, request.json)
    required_fields = ['codigo_interno', 'descricao', 'unidade_comercial', 'preco_unitario_padrao', 'origem_mercadoria', 'tipo_item']
    if not all(field in data and data[field] is not None for field in required_fields):
        abort(400, description=f"Campos obrigatórios ausentes ou nulos: {', '.join(required_fields)}.")
    try:
        new_obj = Produto(**data)
        db.add(new_obj); db.commit(); return jsonify(new_obj.to_dict()), 201
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/produtos/<int:produto_id>', methods=['PUT'])
def update_produto(produto_id):
    db = next(get_db()); obj = db.query(Produto).get(produto_id)
    if not obj: abort(404, description="Produto não encontrado.")
    data = parse_request_data(Produto, request.json)
    try:
        for key, value in data.items(): setattr(obj, key, value)
        db.commit(); return jsonify(obj.to_dict()), 200
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/produtos/<int:produto_id>', methods=['DELETE'])
def delete_produto(produto_id):
    db = next(get_db()); obj = db.query(Produto).get(produto_id)
    if not obj: abort(404, description="Produto não encontrado.")
    try: db.delete(obj); db.commit(); return jsonify({"message": "Produto excluído."}), 204
    except IntegrityError as e: db.rollback(); abort(409, description=f"Não foi possível excluir: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")


@app.route('/clientes', methods=['GET'])
def get_clientes():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    clientes = db.query(Cliente).all()
    cliente_list = [{"cnpj": clientes.cnpj, "razao_social": clientes.razao_social} for cliente in clientes]
    return jsonify(cliente_list), 200

# --- Rotas para Clientes ---
# Primary Key: cliente_id, Campo Único: cnpj
@app.route('/clientes/<int:cliente_id>', methods=['GET'])
def get_cliente(cliente_id):
    db = next(get_db())
    obj = db.query(Cliente).get(cliente_id)
    if not obj: abort(404, description="Cliente não encontrado.")
    return jsonify(obj.to_dict()), 200

@app.route('/clientes', methods=['POST'])
def create_cliente():
    db = next(get_db())
    data = parse_request_data(Cliente, request.json) # Use a função auxiliar
    # Validação dos campos obrigatórios conforme seu modelo
    required_fields = ['cnpj', 'razao_social', 'regime_tributario_id', 'logradouro', 'numero', 'bairro', 'codigo_municipio', 'nome_municipio', 'uf', 'cep']
    if not all(field in data and data[field] is not None for field in required_fields):
        abort(400, description=f"Campos obrigatórios ausentes ou nulos: {', '.join(required_fields)}.")
    try:
        new_obj = Cliente(**data)
        db.add(new_obj); db.commit(); return jsonify(new_obj.to_dict()), 201
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/clientes/<int:cliente_id>', methods=['PUT'])
def update_cliente(cliente_id):
    db = next(get_db()); obj = db.query(Cliente).get(cliente_id)
    if not obj: abort(404, description="Cliente não encontrado.")
    data = parse_request_data(Cliente, request.json) # Use a função auxiliar
    try:
        for key, value in data.items(): setattr(obj, key, value)
        obj.data_atualizacao = datetime.now() # Atualiza data de atualização
        db.commit(); return jsonify(obj.to_dict()), 200
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/clientes/<int:cliente_id>', methods=['DELETE'])
def delete_cliente(cliente_id):
    db = next(get_db()); obj = db.query(Cliente).get(cliente_id)
    if not obj: abort(404, description="Cliente não encontrado.")
    try: db.delete(obj); db.commit(); return jsonify({"message": "Cliente excluído."}), 204
    except IntegrityError as e: db.rollback(); abort(409, description=f"Não foi possível excluir: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/certificados', methods=['GET'])
def get_certificados(): 
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    certificados = db.query(CertificadoDigital).all()
    certificado_list = [{"fingerprint": certificados.fingerprint, "conteudo_certificado": certificados.conteudo_certificado} for certificado in certificados]
    return jsonify(certificado_list), 200

# --- Rotas para CertificadoDigital ---
# Primary Key: certificado_digital_id (cliente_id é parte da PK composta no DDL, mas o Flask usa PK simples para rotas)
# NOTE: Conteúdo do certificado e senha são LargeBinary, requer base64 encode/decode.
# SEGURANÇA: NUNCA exponha senhas de certificados digitais diretamente em uma API. Certifique-se de que o uso de `senha_certificado` e `conteudo_certificado` via API esteja criptografado e/ou muito bem protegido.
@app.route('/certificados/<int:certificado_digital_id>', methods=['GET'])
def get_certificado(certificado_digital_id):
    db = next(get_db())
    obj = db.query(CertificadoDigital).get(certificado_digital_id)
    if not obj: abort(404, description="Certificado Digital não encontrado.")
    return jsonify(obj.to_dict()), 200

@app.route('/certificados', methods=['POST'])
def create_certificado():
    db = next(get_db())
    data = parse_request_data(CertificadoDigital, request.json) # Use a função auxiliar
    required_fields = ['cliente_id', 'conteudo_certificado', 'senha_certificado', 'validade_inicio', 'validade_fim']
    if not all(field in data and data[field] is not None for field in required_fields):
        abort(400, description=f"Campos obrigatórios ausentes ou nulos: {', '.join(required_fields)}.")
    try:
        new_obj = CertificadoDigital(**data)
        db.add(new_obj); db.commit(); return jsonify(new_obj.to_dict()), 201
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/certificados/<int:certificado_digital_id>', methods=['PUT'])
def update_certificado(certificado_digital_id):
    db = next(get_db()); obj = db.query(CertificadoDigital).get(certificado_digital_id)
    if not obj: abort(404, description="Certificado Digital não encontrado.")
    data = parse_request_data(CertificadoDigital, request.json) # Use a função auxiliar
    try:
        for key, value in data.items(): setattr(obj, key, value)
        db.commit(); return jsonify(obj.to_dict()), 200
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/certificados/<int:certificado_digital_id>', methods=['DELETE'])
def delete_certificado(certificado_digital_id):
    db = next(get_db()); obj = db.query(CertificadoDigital).get(certificado_digital_id)
    if not obj: abort(404, description="Certificado Digital não encontrado.")
    try: db.delete(obj); db.commit(); return jsonify({"message": "Certificado Digital excluído."}), 204
    except IntegrityError as e: db.rollback(); abort(409, description=f"Não foi possível excluir: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/nfes', methods=['GET'])
def get_nfes():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    nfes = db.query(NFeEmitidas).all()
    nfe_list = [{"nfe_emitida_id": nfes.nfe_emitida_id, "tipo_nfe": nfes.tipo_nfe} for nfe in nfes]
    return jsonify(nfe_list), 200

# --- Rotas para NFeEmitidas ---
# Primary Key: nfe_emitida_id
# O campo json_nfe é JSONB, então o JSON enviado no request deve ser um objeto JSON válido.
@app.route('/nfes/<int:nfe_emitida_id>', methods=['GET'])
def get_nfe(nfe_emitida_id):
    db = next(get_db())
    obj = db.query(NFeEmitidas).get(nfe_emitida_id)
    if not obj: abort(404, description="NF-e Emitida não encontrada.")
    return jsonify(obj.to_dict()), 200

@app.route('/nfes', methods=['POST'])
def create_nfe():
    db = next(get_db())
    data = parse_request_data(NFeEmitidas, request.json) # Use a função auxiliar
    required_fields = ['cliente_id', 'tipo_nfe', 'finalidade_emissao', 'natureza_operacao', 'json_nfe']
    if not all(field in data and data[field] is not None for field in required_fields):
        abort(400, description=f"Campos obrigatórios ausentes ou nulos: {', '.join(required_fields)}.")
    try:
        new_obj = NFeEmitidas(**data)
        db.add(new_obj); db.commit(); return jsonify(new_obj.to_dict()), 201
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/nfes/<int:nfe_emitida_id>', methods=['PUT'])
def update_nfe(nfe_emitida_id):
    db = next(get_db()); obj = db.query(NFeEmitidas).get(nfe_emitida_id)
    if not obj: abort(404, description="NF-e Emitida não encontrada.")
    data = parse_request_data(NFeEmitidas, request.json) # Use a função auxiliar
    try:
        for key, value in data.items(): setattr(obj, key, value)
        db.commit(); return jsonify(obj.to_dict()), 200
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/nfes/<int:nfe_emitida_id>', methods=['DELETE'])
def delete_nfe(nfe_emitida_id):
    db = next(get_db()); obj = db.query(NFeEmitidas).get(nfe_emitida_id)
    if not obj: abort(404, description="NF-e Emitida não encontrada.")
    try: db.delete(obj); db.commit(); return jsonify({"message": "NF-e Emitida excluída."}), 204
    except IntegrityError as e: db.rollback(); abort(409, description=f"Não foi possível excluir: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

# @app.route('/regimes_tributarios', methods=['GET'])
# def get_regimes_tributarios():
#     """Retorna a lista completa de CFOPs."""
#     db = next(get_db())
#     regimes_tributarios = db.query(RegimeTributario).all()
#     regimes_tributario_list = [{"nome": regimes_tributarios.nome, "descricao": regimes_tributarios.descricao} for regimes_tributario in regimes_tributarios]
#     return jsonify(regimes_tributario_list), 200

@app.route('/regras_tributacao', methods=['GET'])
def get_regras_tributacao():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    regras_tributacao = db.query(RegraTributacao).all()
    regra_tributacao_list = [{"regra_tributacao_id": regras_tributacao.regra_tributacao_id} for regra_tributacao in regras_tributacao]
    return jsonify(regra_tributacao_list), 200

# --- Rotas para RegraTributacao ---
# Primary Key: regra_tributacao_id
@app.route('/regras_tributacao/<int:regra_tributacao_id>', methods=['GET'])
def get_regra_tributacao(regra_tributacao_id):
    db = next(get_db())
    obj = db.query(RegraTributacao).get(regra_tributacao_id)
    if not obj: abort(404, description="Regra de Tributação não encontrada.")
    return jsonify(obj.to_dict()), 200

@app.route('/regras_tributacao', methods=['POST'])
def create_regra_tributacao():
    db = next(get_db())
    data = parse_request_data(RegraTributacao, request.json)
    required_fields = ['regime_tributario_id', 'cfop_id'] # ncm_id pode ser nullable
    if not all(field in data and data[field] is not None for field in required_fields):
        abort(400, description=f"Campos obrigatórios ausentes ou nulos: {', '.join(required_fields)}.")
    try:
        new_obj = RegraTributacao(**data)
        db.add(new_obj); db.commit(); return jsonify(new_obj.to_dict()), 201
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/regras_tributacao/<int:regra_tributacao_id>', methods=['PUT'])
def update_regra_tributacao(regra_tributacao_id):
    db = next(get_db()); obj = db.query(RegraTributacao).get(regra_tributacao_id)
    if not obj: abort(404, description="Regra de Tributação não encontrada.")
    data = parse_request_data(RegraTributacao, request.json)
    try:
        for key, value in data.items(): setattr(obj, key, value)
        db.commit(); return jsonify(obj.to_dict()), 200
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/regras_tributacao/<int:regra_tributacao_id>', methods=['DELETE'])
def delete_regra_tributacao(regra_tributacao_id):
    db = next(get_db()); obj = db.query(RegraTributacao).get(regra_tributacao_id)
    if not obj: abort(404, description="Regra de Tributação não encontrada.")
    try: db.delete(obj); db.commit(); return jsonify({"message": "Regra de Tributação excluída."}), 204
    except IntegrityError as e: db.rollback(); abort(409, description=f"Não foi possível excluir: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/csosn', methods=['GET'])
def get_csosns():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    csosns = db.query(Csosnicms).all()
    csosn_list = [{"codigo": csosn.codigo, "descricao": csosn.descricao} for csosn in csosns]
    return jsonify(csosn_list), 200

# --- Rotas para Csosnicms ---
# Primay Key: csosn_id, Campo Único: codigo
@app.route('/csosn/<int:csosn_id>', methods=['GET'])
def get_csosn(csosn_id):
    db = next(get_db())
    obj = db.query(Csosnicms).get(csosn_id)
    if not obj: abort(404, description="CSOSN não encontrado.")
    return jsonify(obj.to_dict()), 200

@app.route('/csosn', methods=['POST'])
def create_csosn():
    db = next(get_db())
    data = request.json
    if not data or not all(k in data for k in ['codigo', 'descricao']): abort(400, description="'codigo' e 'descricao' são obrigatórios.")
    try:
        new_obj = Csosnicms(codigo=data['codigo'], descricao=data['descricao'])
        db.add(new_obj); db.commit(); return jsonify(new_obj.to_dict()), 201
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/csosn/<int:csosn_id>', methods=['PUT'])
def update_csosn(csosn_id):
    db = next(get_db()); obj = db.query(Csosnicms).get(csosn_id)
    if not obj: abort(404, description="CSOSN não encontrado.")
    data = request.json
    try:
        if 'codigo' in data: obj.codigo = data['codigo']
        if 'descricao' in data: obj.descricao = data['descricao']
        db.commit(); return jsonify(obj.to_dict()), 200
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/csosn/<int:csosn_id>', methods=['DELETE'])
def delete_csosn(csosn_id):
    db = next(get_db()); obj = db.query(Csosnicms).get(csosn_id)
    if not obj: abort(404, description="CSOSN não encontrado.")
    try: db.delete(obj); db.commit(); return jsonify({"message": "CSOSN excluído."}), 204
    except IntegrityError as e: db.rollback(); abort(409, description=f"Não foi possível excluir: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/cst', methods=['GET'])
def get_csts():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    csts = db.query(Csticms).all()
    cst_list = [{"codigo": cst.codigo, "descricao": cst.descricao} for cst in csts]
    return jsonify(cst_list), 200

# --- Rotas para Csticms ---
# Primary Key: cst_id, Campo Único: codigo
@app.route('/cst/<int:cst_id>', methods=['GET'])
def get_cst(cst_id):
    db = next(get_db())
    obj = db.query(Csticms).get(cst_id)
    if not obj: abort(404, description="CST não encontrado.")
    return jsonify(obj.to_dict()), 200

@app.route('/cst', methods=['POST'])
def create_cst():
    db = next(get_db())
    data = request.json
    if not data or not all(k in data for k in ['codigo', 'descricao']): abort(400, description="'codigo' e 'descricao' são obrigatórios.")
    try:
        new_obj = Csticms(codigo=data['codigo'], descricao=data['descricao'])
        db.add(new_obj); db.commit(); return jsonify(new_obj.to_dict()), 201
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/cst/<int:cst_id>', methods=['PUT'])
def update_cst(cst_id):
    db = next(get_db()); obj = db.query(Csticms).get(cst_id)
    if not obj: abort(404, description="CST não encontrado.")
    data = request.json
    try:
        if 'codigo' in data: obj.codigo = data['codigo']
        if 'descricao' in data: obj.descricao = data['descricao']
        db.commit(); return jsonify(obj.to_dict()), 200
    except IntegrityError as e: db.rollback(); abort(409, description=f"Erro: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")

@app.route('/cst/<int:cst_id>', methods=['DELETE'])
def delete_cst(cst_id):
    db = next(get_db()); obj = db.query(Csticms).get(cst_id)
    if not obj: abort(404, description="CST não encontrado.")
    try: db.delete(obj); db.commit(); return jsonify({"message": "CST excluído."}), 204
    except IntegrityError as e: db.rollback(); abort(409, description=f"Não foi possível excluir: {e.orig.pgerror}")
    except Exception as e: db.rollback(); abort(500, description=f"Erro: {e}")


# --- Rotas para Clientes (Web Admin) ---

@app.route('/admin/clientes')
def admin_clientes_list():
    """Exibe a lista de Clientes na interface web."""
    db = next(get_db())
    clientes = db.query(Cliente).all()
    return render_template('admin_clientes_list.html', clientes=clientes)


@app.route('/admin/clientes/add', methods=['GET', 'POST'])
def admin_clientes_add():
    """Adiciona um novo Cliente via interface web, com opção de certificado."""
    db = next(get_db())
    regimes_tributarios = db.query(RegimeTributario).all()

    if request.method == 'POST':
        form_data = {
            'cnpj': request.form.get('cpf_cnpj'),
            'razao_social': request.form.get('nome_completo'),
            'nome_fantasia': request.form.get('nome_fantasia'),
            'inscricao_estadual': request.form.get('rg_ie'),
            'inscricao_municipal': request.form.get('inscricao_municipal'),
            'regime_tributario_id': request.form.get('regime_tributario_id'),
            'cnae': request.form.get('cnae'),
            'logradouro': request.form.get('logradouro'),
            'numero': request.form.get('numero'),
            'complemento': request.form.get('complemento'),
            'bairro': request.form.get('bairro'),
            'codigo_municipio': request.form.get('codigo_municipio'),
            'nome_municipio': request.form.get('cidade'),
            'uf': request.form.get('estado'),
            'cep': request.form.get('cep'),
            'email_contato': request.form.get('email'),
            'telefone_contato': request.form.get('telefone_celular'),
            'ativo': 'ativo' in request.form # Checkbox
        }
        
        required_model_fields = [
            'cnpj', 'razao_social', 'regime_tributario_id', 'logradouro', 'numero',
            'bairro', 'codigo_municipio', 'nome_municipio', 'uf', 'cep'
        ]
        
        errors = []
        for field in required_model_fields:
            if not form_data.get(field):
                errors.append(f"O campo '{field.replace('_', ' ').capitalize()}' é obrigatório.")
        
        try:
            if form_data.get('regime_tributario_id'):
                form_data['regime_tributario_id'] = int(form_data['regime_tributario_id'])
            else:
                errors.append("O campo 'Regime Tributário' é obrigatório.")
        except ValueError:
            errors.append("Regime Tributário inválido.")

        # --- Lógica de Certificado (NOVO) ---
        cert_uploaded_file = request.files.get('conteudo_certificado_file')
        cert_senha = request.form.get('cert_senha_certificado') # Renomeado para evitar conflito
        cert_validade_inicio_str = request.form.get('cert_validade_inicio')
        cert_validade_fim_str = request.form.get('cert_validade_fim')
        cert_nome_arquivo = request.form.get('cert_nome_arquivo_original')
        cert_ativo = 'cert_ativo' in request.form

        # Só tenta processar certificado se um arquivo foi enviado
        if cert_uploaded_file and cert_uploaded_file.filename != '':
            if not cert_senha:
                errors.append("A Senha do Certificado é obrigatória.")
            if not cert_validade_inicio_str:
                errors.append("A Data de Validade Início do Certificado é obrigatória.")
            if not cert_validade_fim_str:
                errors.append("A Data de Validade Fim do Certificado é obrigatória.")
            
            try:
                cert_validade_inicio = datetime.fromisoformat(cert_validade_inicio_str) if cert_validade_inicio_str else None
                cert_validade_fim = datetime.fromisoformat(cert_validade_fim_str) if cert_validade_fim_str else None
            except ValueError:
                errors.append("Formato de data de certificado inválido (use AAAA-MM-DD).")
        elif any([cert_senha, cert_validade_inicio_str, cert_validade_fim_str, cert_nome_arquivo]):
            # Se algum campo de certificado foi preenchido mas o arquivo não, é um erro
            errors.append("Por favor, selecione um arquivo de certificado ou deixe os campos de certificado em branco.")


        if errors:
            flash(f"Erro no preenchimento do formulário: {'. '.join(errors)}", 'danger')
            return render_template(
                'admin_clientes_form.html',
                regimes_tributarios=regimes_tributarios,
                cliente=form_data, # Passa os dados preenchidos para manter no formulário
                # Passa também os dados do certificado para re-preencher
                cert_data={
                    'conteudo_certificado_file': None, # Arquivo não pode ser repassado
                    'senha_certificado': cert_senha,
                    'validade_inicio': cert_validade_inicio_str,
                    'validade_fim': cert_validade_fim_str,
                    'nome_arquivo_original': cert_nome_arquivo,
                    'ativo': cert_ativo
                }
            )

        try:
            new_cliente = Cliente(**form_data)
            db.add(new_cliente)
            db.flush() # flush para que new_cliente.cliente_id esteja disponível
            
            # --- Salvar Certificado (se houver) ---
            if cert_uploaded_file and cert_uploaded_file.filename != '':
                new_certificado = CertificadoDigital(
                    cliente_id=new_cliente.cliente_id,
                    conteudo_certificado=cert_uploaded_file.read(), # Lembre-se da criptografia!
                    senha_certificado=cert_senha.encode('utf-8'),     # Lembre-se da criptografia!
                    validade_inicio=cert_validade_inicio,
                    validade_fim=cert_validade_fim,
                    ativo=cert_ativo,
                    nome_arquivo_original=cert_nome_arquivo if cert_nome_arquivo else cert_uploaded_file.filename,
                    data_upload=datetime.now()
                )
                db.add(new_certificado)

            db.commit()
            flash('Cliente e certificado (se houver) cadastrados com sucesso!', 'success')
            return redirect(url_for('admin_clientes_list'))
        except IntegrityError as e:
            db.rollback()
            flash(f"Erro de integridade ao cadastrar cliente: {e.orig.pgerror}", 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro interno ao cadastrar cliente: {e}", 'danger')
            
    return render_template(
        'admin_clientes_form.html',
        regimes_tributarios=regimes_tributarios,
        cliente=None, # Nenhum cliente pre-existente
        cert_data=None # Nenhum dado de certificado pré-existente
    )


# --- Rotas para Cliente (EDIT e DELETE - Exemplo, a serem implementadas de forma similar) ---

@app.route('/admin/clientes/edit/<int:cliente_id>', methods=['GET', 'POST'])
def admin_clientes_edit(cliente_id):
    """Edita um Cliente existente via interface web, com opção de adicionar certificado."""
    db = next(get_db())
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        abort(404, description="Cliente não encontrado.")

    regimes_tributarios = db.query(RegimeTributario).all()
    # Busca os certificados existentes do cliente
    certificados_existentes = db.query(CertificadoDigital).filter_by(cliente_id=cliente_id).all()

    if request.method == 'POST':
        form_data = {
            'cnpj': request.form.get('cpf_cnpj'),
            'razao_social': request.form.get('nome_completo'),
            'nome_fantasia': request.form.get('nome_fantasia'),
            'inscricao_estadual': request.form.get('rg_ie'),
            'inscricao_municipal': request.form.get('inscricao_municipal'),
            'regime_tributario_id': request.form.get('regime_tributario_id'),
            'cnae': request.form.get('cnae'),
            'logradouro': request.form.get('logradouro'),
            'numero': request.form.get('numero'),
            'complemento': request.form.get('complemento'),
            'bairro': request.form.get('bairro'),
            'codigo_municipio': request.form.get('codigo_municipio'),
            'nome_municipio': request.form.get('cidade'),
            'uf': request.form.get('estado'),
            'cep': request.form.get('cep'),
            'email_contato': request.form.get('email'),
            'telefone_contato': request.form.get('telefone_celular'),
            'ativo': 'ativo' in request.form
        }

        required_model_fields = [
            'cnpj', 'razao_social', 'regime_tributario_id', 'logradouro', 'numero',
            'bairro', 'codigo_municipio', 'nome_municipio', 'uf', 'cep'
        ]
        
        errors = []
        for field in required_model_fields:
            if not form_data.get(field):
                errors.append(f"O campo '{field.replace('_', ' ').capitalize()}' é obrigatório.")
        
        try:
            if form_data.get('regime_tributario_id'):
                form_data['regime_tributario_id'] = int(form_data['regime_tributario_id'])
            else:
                errors.append("O campo 'Regime Tributário' é obrigatório.")
        except ValueError:
            errors.append("Regime Tributário inválido.")

        # --- Lógica de Certificado (NOVO) ---
        cert_uploaded_file = request.files.get('conteudo_certificado_file')
        cert_senha = request.form.get('cert_senha_certificado')
        cert_validade_inicio_str = request.form.get('cert_validade_inicio')
        cert_validade_fim_str = request.form.get('cert_validade_fim')
        cert_nome_arquivo = request.form.get('cert_nome_arquivo_original')
        cert_ativo = 'cert_ativo' in request.form

        cert_data_for_template = {
            'senha_certificado': cert_senha,
            'validade_inicio': cert_validade_inicio_str,
            'validade_fim': cert_validade_fim_str,
            'nome_arquivo_original': cert_nome_arquivo,
            'ativo': cert_ativo
        }

        # Só tenta processar um NOVO certificado se um arquivo foi enviado na seção de "adicionar"
        if cert_uploaded_file and cert_uploaded_file.filename != '':
            if not cert_senha:
                errors.append("A Senha do Certificado é obrigatória para o novo certificado.")
            if not cert_validade_inicio_str:
                errors.append("A Data de Validade Início para o novo certificado é obrigatória.")
            if not cert_validade_fim_str:
                errors.append("A Data de Validade Fim para o novo certificado é obrigatória.")
            
            try:
                cert_validade_inicio = datetime.fromisoformat(cert_validade_inicio_str) if cert_validade_inicio_str else None
                cert_validade_fim = datetime.fromisoformat(cert_validade_fim_str) if cert_validade_fim_str else None
            except ValueError:
                errors.append("Formato de data de novo certificado inválido (use AAAA-MM-DD).")
        elif any([cert_senha, cert_validade_inicio_str, cert_validade_fim_str, cert_nome_arquivo]):
            # Se algum campo de certificado foi preenchido mas o arquivo não, é um erro para adição
            errors.append("Por favor, selecione um arquivo de certificado para o novo certificado ou deixe os campos em branco.")


        if errors:
            flash(f"Erro no preenchimento do formulário: {'. '.join(errors)}", 'danger')
            return render_template(
                'admin_clientes_form.html',
                regimes_tributarios=regimes_tributarios,
                cliente=cliente, # Passa o objeto cliente existente para preencher o formulário
                form_data=form_data, # Dados do POST para preservar as alterações do cliente
                certificados_existentes=certificados_existentes, # Para re-exibir a lista
                cert_data=cert_data_for_template # Dados do novo certificado preenchidos
            )

        try:
            for key, value in form_data.items():
                if key == 'regime_tributario_id' and value is not None:
                    setattr(cliente, key, int(value))
                elif key in ['ativo'] and value is not None:
                    setattr(cliente, key, value)
                else:
                    setattr(cliente, key, value)
            
            cliente.data_atualizacao = datetime.now()
            db.commit() # Commit do cliente primeiro

            # --- Salvar NOVO Certificado (se houver) ---
            if cert_uploaded_file and cert_uploaded_file.filename != '':
                new_certificado = CertificadoDigital(
                    cliente_id=cliente.cliente_id,
                    conteudo_certificado=cert_uploaded_file.read(), # Lembre-se da criptografia!
                    senha_certificado=cert_senha.encode('utf-8'),     # Lembre-se da criptografia!
                    validade_inicio=cert_validade_inicio,
                    validade_fim=cert_validade_fim,
                    ativo=cert_ativo,
                    nome_arquivo_original=cert_nome_arquivo if cert_nome_arquivo else cert_uploaded_file.filename,
                    data_upload=datetime.now()
                )
                db.add(new_certificado)
                db.commit() # Commit do novo certificado

            flash('Cliente e certificado (se houver) atualizados com sucesso!', 'success')
            return redirect(url_for('admin_clientes_list'))
        except IntegrityError as e:
            db.rollback()
            flash(f"Erro de integridade ao atualizar cliente: {e.orig.pgerror}", 'danger')
        except Exception as e:
            db.rollback()
            flash(f"Erro interno ao atualizar cliente: {e}", 'danger')

    # Para requisições GET
    return render_template(
        'admin_clientes_form.html',
        regimes_tributarios=regimes_tributarios,
        cliente=cliente, # Passa o objeto cliente para o formulário GET
        certificados_existentes=certificados_existentes, # Para exibir a lista de certificados
        cert_data=None # Nenhum dado de novo certificado no GET
    )

@app.route('/admin/clientes/delete/<int:cliente_id>', methods=['POST'])
def admin_clientes_delete(cliente_id):
    db = next(get_db())
    cliente = db.query(Cliente).get(cliente_id)
    if not cliente:
        abort(404, description="Cliente não encontrado para exclusão.")
    
    try:
        db.delete(cliente)
        db.commit()
        flash('Cliente excluído com sucesso!', 'success')
        return redirect(url_for('admin_clientes_list'))
    except IntegrityError:
        db.rollback()
        flash('Não foi possível excluir o Cliente devido a dependências em outras tabelas.', 'danger')
        return redirect(url_for('admin_clientes_list'))
    except Exception as e:
        db.rollback()
        flash(f"Erro ao deletar cliente: {e}", 'danger')
        return redirect(url_for('admin_clientes_list'))

# --- Rotas da Aplicação Web de Administração (Exemplo: Regimes Tributários) ---

@app.route('/admin/regimes_tributarios')
def admin_regimes_tributarios_list():
    """Exibe a lista de Regimes Tributários na interface web."""
    db = next(get_db())
    regimes = db.query(RegimeTributario).all()
    return render_template('admin_regimes_tributarios_list.html', regimes=regimes)

@app.route('/admin/regimes_tributarios/add', methods=['GET', 'POST'])
def admin_regimes_tributarios_add():
    """Adiciona um novo Regime Tributário via interface web."""
    db = next(get_db())
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao')
        
        try:
            new_regime = RegimeTributario(nome=nome, descricao=descricao)
            db.add(new_regime)
            db.commit()
            return redirect(url_for('admin_regimes_tributarios_list'))
        except IntegrityError:
            db.rollback()
            # Poderíamos adicionar uma mensagem flash para o usuário aqui
            return render_template('admin_regimes_tributarios_form.html', regime=None, error="Já existe um Regime Tributário com este nome.")
        except Exception as e:
            db.rollback()
            return render_template('admin_regimes_tributarios_form.html', regime=None, error=f"Erro ao adicionar: {e}")
            
    return render_template('admin_regimes_tributarios_form.html', regime=None, error=None)

@app.route('/admin/regimes_tributarios/edit/<int:regime_id>', methods=['GET', 'POST'])
def admin_regimes_tributarios_edit(regime_id):
    """Edita um Regime Tributário existente via interface web."""
    db = next(get_db())
    regime = db.query(RegimeTributario).get(regime_id)
    if not regime:
        abort(404, description="Regime Tributário não encontrado para edição.")

    if request.method == 'POST':
        regime.nome = request.form['nome']
        regime.descricao = request.form.get('descricao')
        
        try:
            db.commit()
            return redirect(url_for('admin_regimes_tributarios_list'))
        except IntegrityError:
            db.rollback()
            return render_template('admin_regimes_tributarios_form.html', regime=regime, error="Já existe um Regime Tributário com este nome.")
        except Exception as e:
            db.rollback()
            return render_template('admin_regimes_tributarios_form.html', regime=regime, error=f"Erro ao editar: {e}")

    return render_template('admin_regimes_tributarios_form.html', regime=regime, error=None)

@app.route('/admin/regimes_tributarios/delete/<int:regime_id>', methods=['POST'])
def admin_regimes_tributarios_delete(regime_id):
    """Deleta um Regime Tributário via interface web."""
    db = next(get_db())
    regime = db.query(RegimeTributario).get(regime_id)
    if not regime:
        abort(404, description="Regime Tributário não encontrado para exclusão.")
    
    try:
        db.delete(regime)
        db.commit()
        return redirect(url_for('admin_regimes_tributarios_list'))
    except IntegrityError:
        db.rollback()
        # Poderíamos adicionar uma mensagem flash para o usuário aqui
        return redirect(url_for('admin_regimes_tributarios_list', error="Não foi possível excluir o Regime Tributário devido a dependências em outras tabelas."))
    except Exception as e:
        db.rollback()
        return redirect(url_for('admin_regimes_tributarios_list', error=f"Erro ao deletar: {e}"))

# --- Configuração de Execução Local ---
if __name__ == '__main__':
    # Obtém a porta das variáveis de ambiente (necessário para Heroku e outros PaaS)
    # ou usa 8080 como padrão para desenvolvimento local.
    port = int(os.environ.get('PORT', 8080))
    # 'debug=True' permite o recarregamento automático e exibe erros detalhados.
    # NUNCA use debug=True em produção.
    # 'host='0.0.0.0'' torna a API acessível de qualquer IP na rede (útil em containers).
    app.run(debug=True, host='localhost', port=port)

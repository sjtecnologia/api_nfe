# app.py
from flask import Flask, jsonify, request, abort, render_template, redirect, url_for
import json
import os
import uuid
from datetime import datetime, date
import base64
from decimal import Decimal

# Importe os modelos e o Base, create_engine, sessionmaker do seu arquivo models.py
from database.models import Base, Cfop, Ncm, Produto, Cliente, RegimeTributario, CertificadoDigital, NFeEmitidas, RegraTributacao, Csosnicms, Csticms  # Importe outros modelos conforme necessário
from sqlalchemy import create_engine, DateTime, Date, Numeric, LargeBinary
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

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

# app.py
from flask import Flask, jsonify, request
import json
import os
import uuid # Para gerar IDs únicos
from datetime import datetime

# Importe os modelos e o Base, create_engine, sessionmaker do seu arquivo models.py
from database.models import Base, Cfop, Ncm, Produto, Cliente, RegimeTributario, CertificadoDigital, NFeEmitidas, RegraTributacao, Csosnicms, Csticms  # Importe outros modelos conforme necessário
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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


# --- Rotas da API ---

@app.route('/')
def home():
    """Rota inicial para verificar se a API está online."""
    return jsonify({
        "message": "API de Emissão de NF está online!",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Verifica a saúde da API.",
            "/cfops": "Lista todos os códigos CFOPs e suas descrições.",
            "/certificados": "Gerencia o armazenamento de certificados digitais."
            # "/nfe": "Endpoint para emissão de NF-e (a ser implementado)."
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar a saúde da API."""
    return jsonify({"status": "UP", "timestamp": datetime.now().isoformat()}), 200

@app.route('/cfops', methods=['GET'])
def get_cfops():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    cfops = db.query(Cfop).all()
    cfop_list = [{"cfop": cfop.cfop, "descricao": cfop.descricao} for cfop in cfops]
    return jsonify(cfop_list), 200

@app.route('/ncms', methods=['GET'])
def get_ncms():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    ncms = db.query(Ncm).all()
    ncm_list = [{"codigo": ncm.codigo, "descricao": ncm.descricao} for ncm in ncms]
    return jsonify(ncm_list), 200

@app.route('/produtos', methods=['GET'])
def get_produtos():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    produtos = db.query(Produto).all()
    produto_list = [{"codigo": produtos.codigo_interno, "descricao": produtos.descricao} for produto in produtos]
    return jsonify(produto_list), 200

@app.route('/clientes', methods=['GET'])
def get_clientes():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    clientes = db.query(Cliente).all()
    cliente_list = [{"cnpj": clientes.cnpj, "razao_social": clientes.razao_social} for cliente in clientes]
    return jsonify(cliente_list), 200

@app.route('/certificados', methods=['GET'])
def get_certificados(): 
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    certificados = db.query(CertificadoDigital).all()
    certificado_list = [{"fingerprint": certificados.fingerprint, "conteudo_certificado": certificados.conteudo_certificado} for certificado in certificados]
    return jsonify(certificado_list), 200

@app.route('/nfes', methods=['GET'])
def get_nfes():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    nfes = db.query(NFeEmitidas).all()
    nfe_list = [{"nfe_emitida_id": nfes.nfe_emitida_id, "tipo_nfe": nfes.tipo_nfe} for nfe in nfes]
    return jsonify(nfe_list), 200

@app.route('/regimes_tributarios', methods=['GET'])
def get_regimes_tributarios():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    regimes_tributarios = db.query(RegimeTributario).all()
    regimes_tributario_list = [{"nome": regimes_tributarios.nome, "descricao": regimes_tributarios.descricao} for regimes_tributario in regimes_tributarios]
    return jsonify(regimes_tributario_list), 200

@app.route('/regras_tributacao', methods=['GET'])
def get_regras_tributacao():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    regras_tributacao = db.query(RegraTributacao).all()
    regra_tributacao_list = [{"regra_tributacao_id": regras_tributacao.regra_tributacao_id} for regra_tributacao in regras_tributacao]
    return jsonify(regra_tributacao_list), 200

@app.route('/csosn', methods=['GET'])
def get_csosns():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    csosns = db.query(Csosnicms).all()
    csosn_list = [{"codigo": csosn.codigo, "descricao": csosn.descricao} for csosn in csosns]
    return jsonify(csosn_list), 200

@app.route('/cst', methods=['GET'])
def get_csts():
    """Retorna a lista completa de CFOPs."""
    db = next(get_db())
    csts = db.query(Csticms).all()
    cst_list = [{"codigo": cst.codigo, "descricao": cst.descricao} for cst in csts]
    return jsonify(cst_list), 200

# --- Configuração de Execução Local ---
if __name__ == '__main__':
    # Obtém a porta das variáveis de ambiente (necessário para Heroku e outros PaaS)
    # ou usa 8080 como padrão para desenvolvimento local.
    port = int(os.environ.get('PORT', 8080))
    # 'debug=True' permite o recarregamento automático e exibe erros detalhados.
    # NUNCA use debug=True em produção.
    # 'host='0.0.0.0'' torna a API acessível de qualquer IP na rede (útil em containers).
    app.run(debug=True, host='localhost', port=port)

# app.py
from flask import Flask, jsonify, request
import json
import os
import uuid # Para gerar IDs únicos
from datetime import datetime

# Importe os modelos e o Base, create_engine, sessionmaker do seu arquivo models.py
from database.models import Base, RegimeTributario, Cliente, CertificadoDigital, NFeEmitidas, Cfop, Ncm, Produto, RegraTributacao
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

# --- Configuração do Banco de Dados ---
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root:Mo@2508@host:5432/sjtnfe")
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

# # --- Configurações da Aplicação ---
# # Caminho para o arquivo de dados CFOP
# # Em produção, você pode carregar isso de um banco de dados ou serviço externo
# CFOP_DATA_FILE = 'cfop_data.json'

# # Simulando um "cofre" de certificados em memória (NÃO PARA PRODUÇÃO)
# # Em produção, isso seria um banco de dados seguro, KMS, HashiCorp Vault, etc.
# CERTIFICATE_STORE = {}

# # --- Funções Auxiliares para Carregar Dados ---
# def load_cfop_data():
#     """Carrega os dados de CFOP do arquivo JSON."""
#     try:
#         with open(CFOP_DATA_FILE, 'r', encoding='utf-8') as f:
#             data = json.load(f)
#         app.logger.info(f"Dados de CFOP carregados com sucesso de {CFOP_DATA_FILE}. Total: {len(data)} entradas.")
#         return data
#     except FileNotFoundError:
#         app.logger.error(f"Erro: O arquivo '{CFOP_DATA_FILE}' não foi encontrado. Certifique-se de que ele existe.")
#         return []
#     except json.JSONDecodeError:
#         app.logger.error(f"Erro ao decodificar JSON de '{CFOP_DATA_FILE}'. Verifique o formato do arquivo.")
#         return []

# # Carrega os dados de CFOP ao iniciar a aplicação
# cfop_list = load_cfop_data()

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
    cfop_list = [{"codigo": cfop.codigo, "descricao": cfop.descricao} for cfop in cfops]
    return jsonify(cfop_list), 200



# --- Configuração de Execução Local ---
if __name__ == '__main__':
    # Obtém a porta das variáveis de ambiente (necessário para Heroku e outros PaaS)
    # ou usa 8080 como padrão para desenvolvimento local.
    port = int(os.environ.get('PORT', 8080))
    # 'debug=True' permite o recarregamento automático e exibe erros detalhados.
    # NUNCA use debug=True em produção.
    # 'host='0.0.0.0'' torna a API acessível de qualquer IP na rede (útil em containers).
    app.run(debug=True, host='localhost', port=port)

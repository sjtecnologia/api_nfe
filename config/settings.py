import os
from dotenv import load_dotenv

# Carregar .env antes de qualquer leitura de variável de ambiente
load_dotenv()

# Configurações do Flask
_secret_key = os.getenv('FLASK_SECRET_KEY')
if not _secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY não configurada. "
        "Defina essa variável de ambiente antes de iniciar o servidor."
    )
SECRET_KEY = _secret_key

# Configurações do Banco de Dados
_database_url = os.getenv("DATABASE_URL")
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL não configurada. "
        "Defina essa variável de ambiente antes de iniciar o servidor. "
        "Exemplo: postgresql://usuario:senha@host:5432/banco"
    )
SQLALCHEMY_DATABASE_URL = _database_url

# Configurações da Sefaz
SEFAZ_AMBIENTE_HOMOLOGACAO = True  # True = Homologação, False = Produção
USAR_CERTIFICADO_REAL = True  # True = Usar certificado real, False = Simulado

# Configurações de Debug — padrão False para segurança em produção
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
HOST = os.getenv('FLASK_HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 8080))

# Configurações de Upload
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')

# Configurações de Log
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# IBS/CBS - Reforma Tributária (LC 214/2024)
# False = desabilitado (padrão até implementação completa)
HABILITAR_IBS_CBS = os.getenv('HABILITAR_IBS_CBS', 'True').lower() == 'true'
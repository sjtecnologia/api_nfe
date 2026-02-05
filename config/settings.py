import os

# Configurações do Flask
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'sua_chave_secreta_padrao_muito_complexa_e_longa_aqui')

# Configurações do Banco de Dados
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Mo2505@localhost:5432/sjtnfe")

# Configurações da Sefaz
SEFAZ_AMBIENTE_HOMOLOGACAO = True  # True = Homologação, False = Produção
USAR_CERTIFICADO_REAL = True  # True = Usar certificado real, False = Simulado

# ⚠️ REFORMA TRIBUTÁRIA - IBS/CBS (LC 214/2025)
# Habilitar/desabilitar tags IBS/CBS no XML da NFe
# ATENÇÃO: A SEFAZ-SP (homologação) ainda pode estar rejeitando essas tags
# mesmo que a Reforma já esteja em vigor. Desabilitar temporariamente
# se houver erro "Falha no Schema XML" relacionado ao IBS/CBS
HABILITAR_IBS_CBS = False  # True = Incluir tags IBS/CBS, False = Não incluir

# Configurações de Debug
DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
HOST = os.getenv('FLASK_HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 8080))

# Configurações de Upload
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')

# Configurações de Log
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Configurações de Backup
BACKUP_DIR = os.getenv('BACKUP_DIR', 'backups')
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
BACKUP_LOG_DIR = os.getenv('BACKUP_LOG_DIR', 'logs')

# Configurações do Banco de Dados para Backup
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'sjtnfe')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Mo2505')
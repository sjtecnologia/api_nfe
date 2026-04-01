#!/bin/bash

# ============================================================
# Script de Atualizacao do Banco de Dados - Certificado A3
# Data: 18/12/2024
# Descricao: Adiciona suporte para certificados A3 (tokens)
# ============================================================

echo ""
echo "============================================================"
echo "ATUALIZACAO DO BANCO DE DADOS - SUPORTE CERTIFICADO A3"
echo "============================================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Definir variaveis do banco de dados
# IMPORTANTE: Ajuste estas variaveis conforme sua configuracao
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-nfesjt}"
DB_USER="${DB_USER:-postgres}"

echo "Configuracao do Banco de Dados:"
echo "  Host: $DB_HOST"
echo "  Porta: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  Usuario: $DB_USER"
echo ""

# Verificar se o psql existe
if ! command -v psql &> /dev/null; then
    echo -e "${RED}[ERRO]${NC} PostgreSQL cliente (psql) nao encontrado!"
    echo "Por favor, instale o PostgreSQL:"
    echo "  Ubuntu/Debian: sudo apt-get install postgresql-client"
    echo "  CentOS/RHEL: sudo yum install postgresql"
    echo "  macOS: brew install postgresql"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} PostgreSQL cliente encontrado."
echo ""

# Obter diretorio do script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Criar backup antes da migracao
echo "============================================================"
echo "CRIANDO BACKUP DO BANCO DE DADOS"
echo "============================================================"
echo ""

BACKUP_DIR="$SCRIPT_DIR/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_pre_a3_$TIMESTAMP.sql"

echo "Criando backup em: $BACKUP_FILE"
echo ""

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F p -f "$BACKUP_FILE"

if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO]${NC} Falha ao criar backup!"
    echo "Abortando atualizacao por seguranca."
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Backup criado com sucesso!"
echo ""

# Executar migracao
echo "============================================================"
echo "EXECUTANDO MIGRACAO DO BANCO DE DADOS"
echo "============================================================"
echo ""

MIGRATION_FILE="$PROJECT_DIR/database/migrations/add_tipo_certificado.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}[ERRO]${NC} Arquivo de migracao nao encontrado!"
    echo "Procurado em: $MIGRATION_FILE"
    echo ""
    echo "Certifique-se de que o arquivo existe no caminho correto."
    exit 1
fi

echo "Aplicando migracao: $MIGRATION_FILE"
echo ""

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[ERRO]${NC} Falha ao executar migracao!"
    echo ""
    echo "O backup foi salvo em: $BACKUP_FILE"
    echo "Voce pode restaura-lo com:"
    echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $BACKUP_FILE"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}[OK]${NC} Migracao aplicada com sucesso!"
echo ""

# Verificar se as colunas foram criadas
echo "============================================================"
echo "VERIFICANDO ESTRUTURA DO BANCO"
echo "============================================================"
echo ""

echo "Verificando colunas adicionadas..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'certificados_digitais' AND column_name IN ('tipo_certificado', 'token_slot_id', 'token_label', 'pkcs11_library') ORDER BY column_name;"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}[OK]${NC} Colunas verificadas!"
else
    echo -e "${YELLOW}[AVISO]${NC} Nao foi possivel verificar as colunas"
fi

echo ""
echo "============================================================"
echo "ATUALIZACAO CONCLUIDA COM SUCESSO!"
echo "============================================================"
echo ""
echo "Proximos passos:"
echo "  1. Instalar PyKCS11: pip install PyKCS11"
echo "  2. Instalar drivers dos tokens:"
echo "     - Ubuntu/Debian: sudo apt-get install libpcsclite-dev pcscd"
echo "     - CentOS/RHEL: sudo yum install pcsc-lite pcsc-lite-libs"
echo "     - macOS: brew install pcsc-lite"
echo "  3. Reiniciar o servico da API:"
echo "     - Systemd: sudo systemctl restart api_nfe_principal"
echo "     - Manual: pkill -f 'python.*app.py' && python app.py &"
echo ""
echo "Backup salvo em: $BACKUP_FILE"
echo ""
echo "Documentacao: docs/SUPORTE_CERTIFICADOS_A3.md"
echo ""

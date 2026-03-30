#!/bin/bash

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📦 SCRIPT DE MIGRAÇÃO DO BANCO LOCAL PARA RDS AWS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
LOCAL_DB="sjtnfe"
LOCAL_HOST="localhost"
LOCAL_USER="postgres"
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/sjtnfe_backup_${TIMESTAMP}.sql"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURAÇÕES DO RDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RDS_ENDPOINT="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
RDS_USER="postgres"
RDS_DB="sjtnfe"
RDS_PORT="5432"
RDS_PASSWORD="gMGM!#)NW\$nH1w(wrVIdcmn5"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📦 MIGRAÇÃO DO BANCO DE DADOS LOCAL → RDS AWS${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Banco local:  ${LOCAL_DB} @ ${LOCAL_HOST}"
echo "Banco RDS:    ${RDS_DB} @ ${RDS_ENDPOINT}"
echo "Backup file:  ${BACKUP_FILE}"
echo ""

# Criar diretório de backups se não existir
mkdir -p ${BACKUP_DIR}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ETAPA 1: Backup do banco local
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}ETAPA 1/4: Fazendo backup do banco local...${NC}"
echo ""
echo "Por favor, digite a senha do PostgreSQL LOCAL quando solicitado:"

pg_dump -h ${LOCAL_HOST} \
        -U ${LOCAL_USER} \
        -d ${LOCAL_DB} \
        --no-owner \
        --no-acl \
        -f ${BACKUP_FILE}

if [ ! -f "${BACKUP_FILE}" ] || [ ! -s "${BACKUP_FILE}" ]; then
    echo -e "${RED}❌ ERRO: Backup não foi criado ou está vazio!${NC}"
    exit 1
fi

BACKUP_SIZE=$(du -h ${BACKUP_FILE} | cut -f1)
echo -e "${GREEN}✅ Backup criado com sucesso! Tamanho: ${BACKUP_SIZE}${NC}"
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ETAPA 2: Transferir backup para AWS EC2
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}ETAPA 2/4: Transferindo backup para AWS EC2...${NC}"
echo ""

SSH_KEY="$HOME/Downloads/nfe-new-api-key.pem"
EC2_HOST="ubuntu@3.87.73.106"

if [ ! -f "${SSH_KEY}" ]; then
    echo -e "${RED}❌ ERRO: Chave SSH não encontrada em ${SSH_KEY}${NC}"
    echo "   Verifique o caminho da chave SSH"
    exit 1
fi

scp -i ${SSH_KEY} ${BACKUP_FILE} ${EC2_HOST}:/home/ubuntu/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backup transferido para EC2 com sucesso!${NC}"
else
    echo -e "${RED}❌ ERRO: Falha ao transferir backup para EC2${NC}"
    exit 1
fi
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ETAPA 3: Restaurar no RDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}ETAPA 3/4: Restaurando backup no RDS...${NC}"
echo ""

BACKUP_FILENAME=$(basename ${BACKUP_FILE})

ssh -i ${SSH_KEY} ${EC2_HOST} << EOF
echo "Conectando ao RDS e restaurando banco de dados..."

# Dropar e recriar o banco (CUIDADO: apaga dados existentes!)
echo "⚠️  Recriando banco de dados (dados existentes serão apagados)..."
PGPASSWORD="${RDS_PASSWORD}" psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d postgres -c "DROP DATABASE IF EXISTS ${RDS_DB};" 2>&1
PGPASSWORD="${RDS_PASSWORD}" psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d postgres -c "CREATE DATABASE ${RDS_DB};" 2>&1

# Restaurar backup
echo "Restaurando backup..."
PGPASSWORD="${RDS_PASSWORD}" psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d ${RDS_DB} -f /home/ubuntu/${BACKUP_FILENAME} 2>&1 | tail -20

# Limpar arquivo de backup
rm /home/ubuntu/${BACKUP_FILENAME}
echo "Backup restaurado e arquivo temporário removido."
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Banco de dados restaurado no RDS com sucesso!${NC}"
else
    echo -e "${RED}❌ ERRO: Falha ao restaurar banco no RDS${NC}"
    exit 1
fi
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ETAPA 4: Verificar integridade
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo -e "${YELLOW}ETAPA 4/4: Verificando integridade dos dados...${NC}"
echo ""

# Contar tabelas localmente
echo "Tabelas no banco LOCAL:"
LOCAL_TABLES=$(psql -h ${LOCAL_HOST} -U ${LOCAL_USER} -d ${LOCAL_DB} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
echo "   Total: ${LOCAL_TABLES} tabelas"
echo ""

# Contar tabelas no RDS
echo "Tabelas no banco RDS:"
ssh -i ${SSH_KEY} ${EC2_HOST} << EOF
RDS_TABLES=\$(PGPASSWORD="${RDS_PASSWORD}" psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d ${RDS_DB} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
echo "   Total: \${RDS_TABLES} tabelas"
EOF

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📋 Backup salvo em: ${BACKUP_FILE}"
echo "🔗 RDS Endpoint: ${RDS_ENDPOINT}"
echo "🗄️  Database: ${RDS_DB}"
echo ""
echo "⚠️  PRÓXIMOS PASSOS:"
echo "   1. Atualizar .env na EC2 com credenciais do RDS"
echo "   2. Reiniciar serviços: sudo systemctl restart api-nfe-principal"
echo "   3. Testar aplicação: https://api.emitemax.com.br/health"
echo ""

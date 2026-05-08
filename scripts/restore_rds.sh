#!/bin/bash

# Script simplificado para restaurar no RDS

set -e

# Configurações
RDS_ENDPOINT="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
RDS_USER="postgres"
RDS_DB="sjtnfe"
BACKUP_FILE="backups/sjtnfe_backup_20251230_124256.sql"
SSH_KEY="$HOME/Downloads/nfe-new-api-key.pem"
EC2_HOST="ubuntu@3.87.73.106"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 RESTAURAÇÃO DO BANCO NO RDS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "RDS: ${RDS_ENDPOINT}"
echo "Database: ${RDS_DB}"
echo ""

# Verificar se backup já foi transferido
echo "Verificando backup na EC2..."
ssh -i ${SSH_KEY} ${EC2_HOST} "ls -lh /home/ubuntu/$(basename ${BACKUP_FILE})" 2>/dev/null || {
    echo "Transferindo backup..."
    scp -i ${SSH_KEY} ${BACKUP_FILE} ${EC2_HOST}:/home/ubuntu/
}

echo ""
echo "✅ Backup disponível na EC2"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  PRÓXIMOS PASSOS MANUAIS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Atualizar Security Group do RDS no Console AWS:"
echo "   - EC2 > Security Groups > nfe-database-sg"
echo "   - Inbound Rules > Edit"
echo "   - Adicionar regra PostgreSQL (5432) com Source: 172.30.1.214/32"
echo ""
echo "2. Após atualizar Security Group, conecte na EC2:"
echo "   ssh -i ${SSH_KEY} ${EC2_HOST}"
echo ""
echo "3. Teste a conexão com RDS:"
echo "   PGPASSWORD='gMGM!#)NW\$nH1w(wrVIdcmn5' psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d postgres -c '\l'"
echo ""
echo "4. Se a conexão funcionar, restaure o banco:"
echo ""
echo "   # Dropar e recriar banco"
echo "   PGPASSWORD='gMGM!#)NW\$nH1w(wrVIdcmn5' psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d postgres -c 'DROP DATABASE IF EXISTS sjtnfe;'"
echo "   PGPASSWORD='gMGM!#)NW\$nH1w(wrVIdcmn5' psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d postgres -c 'CREATE DATABASE sjtnfe;'"
echo ""
echo "   # Restaurar backup"
echo "   PGPASSWORD='gMGM!#)NW\$nH1w(wrVIdcmn5' psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d ${RDS_DB} -f /home/ubuntu/$(basename ${BACKUP_FILE})"
echo ""
echo "   # Verificar tabelas"
echo "   PGPASSWORD='gMGM!#)NW\$nH1w(wrVIdcmn5' psql -h ${RDS_ENDPOINT} -U ${RDS_USER} -d ${RDS_DB} -c '\dt'"
echo ""

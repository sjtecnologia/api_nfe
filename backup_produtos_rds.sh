#!/bin/bash
# Backup da tabela produtos no RDS antes da atualização

set -e

DB_HOST="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
DB_PORT="5432"
DB_USER="postgres"
DB_NAME="sjtnfe"
BACKUP_DIR="$(dirname "$0")/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/produtos_backup_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Iniciando backup da tabela 'produtos' em: $BACKUP_FILE"

PGPASSWORD='gMGM!#)NW$nH1w(wrVIdcmn5' pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -t produtos \
  --no-password \
  -f "$BACKUP_FILE"

echo "Backup concluído com sucesso!"
ls -lh "$BACKUP_FILE"

#!/bin/bash

################################################################################
# Script de Backup Automático do Banco de Dados PostgreSQL
# Sistema: API NFe
# Descrição: Realiza backup completo com compressão, rotação e logs
################################################################################

# Configurações (podem ser sobrescritas por variáveis de ambiente)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-sjtnfe}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-***SENHA_LOCAL_DEV***}"

# Diretórios
BACKUP_DIR="${BACKUP_DIR:-./backups}"
LOG_DIR="${LOG_DIR:-./logs}"

# Retenção (em dias)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Criar diretórios se não existirem
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"

# Nome do arquivo de backup com timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"
LOG_FILE="${LOG_DIR}/backup_${TIMESTAMP}.log"

# Função de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Função de erro
error_exit() {
    log "ERRO: $1"
    exit 1
}

# Início do backup
log "=========================================="
log "Iniciando backup do banco de dados"
log "=========================================="
log "Database: $DB_NAME"
log "Host: $DB_HOST:$DB_PORT"
log "Backup File: $BACKUP_FILE_GZ"

# Verificar se pg_dump está disponível
if ! command -v pg_dump &> /dev/null; then
    error_exit "pg_dump não encontrado. Instale o PostgreSQL client."
fi

# Exportar senha para o pg_dump
export PGPASSWORD="$DB_PASSWORD"

# Executar backup
log "Executando pg_dump..."
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    -f "$BACKUP_FILE" 2>> "$LOG_FILE"; then
    log "✓ Dump do banco criado com sucesso"
else
    error_exit "Falha ao criar dump do banco de dados"
fi

# Comprimir backup
log "Comprimindo backup..."
if gzip "$BACKUP_FILE" 2>> "$LOG_FILE"; then
    log "✓ Backup comprimido com sucesso"
else
    error_exit "Falha ao comprimir backup"
fi

# Verificar tamanho do backup
BACKUP_SIZE=$(du -h "$BACKUP_FILE_GZ" | cut -f1)
log "Tamanho do backup: $BACKUP_SIZE"

# Limpar senha da memória
unset PGPASSWORD

# Rotação de backups antigos
log "=========================================="
log "Executando rotação de backups..."
log "Mantendo backups dos últimos $RETENTION_DAYS dias"

DELETED_COUNT=0
while IFS= read -r old_backup; do
    rm -f "$old_backup"
    log "✓ Backup antigo removido: $(basename "$old_backup")"
    ((DELETED_COUNT++))
done < <(find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" -type f -mtime +$RETENTION_DAYS)

if [ $DELETED_COUNT -eq 0 ]; then
    log "Nenhum backup antigo para remover"
else
    log "Total de backups antigos removidos: $DELETED_COUNT"
fi

# Contar backups restantes
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" -type f | wc -l)
log "Total de backups disponíveis: $BACKUP_COUNT"

# Finalização
log "=========================================="
log "✓ Backup concluído com sucesso!"
log "=========================================="

# Retornar sucesso
exit 0

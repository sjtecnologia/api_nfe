#!/bin/bash

################################################################################
# Script de Restauração de Backup do Banco de Dados PostgreSQL
# Sistema: API NFe
# Descrição: Restaura backup com validação e confirmação
################################################################################

# Configurações (podem ser sobrescritas por variáveis de ambiente)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-sjtnfe}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-Mo2505}"

# Diretórios
BACKUP_DIR="${BACKUP_DIR:-./backups}"
LOG_DIR="${LOG_DIR:-./logs}"

# Criar diretórios se não existirem
mkdir -p "$LOG_DIR"

# Timestamp para log
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/restore_${TIMESTAMP}.log"

# Função de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Função de erro
error_exit() {
    log "ERRO: $1"
    exit 1
}

# Verificar argumentos
if [ $# -eq 0 ]; then
    echo "=========================================="
    echo "Script de Restauração de Backup"
    echo "=========================================="
    echo ""
    echo "Uso: $0 <arquivo_backup.sql.gz>"
    echo ""
    echo "Backups disponíveis:"
    echo ""
    
    if [ -d "$BACKUP_DIR" ]; then
        ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
        
        if [ $? -ne 0 ]; then
            echo "  Nenhum backup encontrado em $BACKUP_DIR"
        fi
    else
        echo "  Diretório de backups não encontrado: $BACKUP_DIR"
    fi
    
    echo ""
    exit 1
fi

BACKUP_FILE="$1"

# Início da restauração
log "=========================================="
log "Iniciando restauração do banco de dados"
log "=========================================="
log "Database: $DB_NAME"
log "Host: $DB_HOST:$DB_PORT"
log "Backup File: $BACKUP_FILE"

# Verificar se o arquivo de backup existe
if [ ! -f "$BACKUP_FILE" ]; then
    error_exit "Arquivo de backup não encontrado: $BACKUP_FILE"
fi

# Verificar se o arquivo está comprimido
if [[ "$BACKUP_FILE" == *.gz ]]; then
    IS_COMPRESSED=true
    SQL_FILE="${BACKUP_FILE%.gz}"
else
    IS_COMPRESSED=false
    SQL_FILE="$BACKUP_FILE"
fi

# Confirmar restauração
echo ""
echo "=========================================="
echo "⚠️  ATENÇÃO: OPERAÇÃO DESTRUTIVA ⚠️"
echo "=========================================="
echo ""
echo "Você está prestes a RESTAURAR o banco de dados:"
echo "  Database: $DB_NAME"
echo "  Host: $DB_HOST:$DB_PORT"
echo "  Backup: $(basename "$BACKUP_FILE")"
echo ""
echo "TODOS OS DADOS ATUAIS SERÃO SUBSTITUÍDOS!"
echo ""
read -p "Tem certeza que deseja continuar? (digite 'SIM' para confirmar): " CONFIRM

if [ "$CONFIRM" != "SIM" ]; then
    log "Restauração cancelada pelo usuário"
    echo "Operação cancelada."
    exit 0
fi

# Verificar se psql está disponível
if ! command -v psql &> /dev/null; then
    error_exit "psql não encontrado. Instale o PostgreSQL client."
fi

# Exportar senha
export PGPASSWORD="$DB_PASSWORD"

# Descomprimir se necessário
if [ "$IS_COMPRESSED" = true ]; then
    log "Descomprimindo backup..."
    if gunzip -c "$BACKUP_FILE" > "$SQL_FILE" 2>> "$LOG_FILE"; then
        log "✓ Backup descomprimido com sucesso"
        TEMP_SQL_FILE="$SQL_FILE"
    else
        error_exit "Falha ao descomprimir backup"
    fi
fi

# Verificar tamanho do arquivo SQL
SQL_SIZE=$(du -h "$SQL_FILE" | cut -f1)
log "Tamanho do arquivo SQL: $SQL_SIZE"

# Executar restauração
log "Executando restauração..."
log "Isso pode levar alguns minutos dependendo do tamanho do backup..."

if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_FILE" 2>> "$LOG_FILE"; then
    log "✓ Banco de dados restaurado com sucesso"
else
    error_exit "Falha ao restaurar banco de dados. Verifique o log: $LOG_FILE"
fi

# Limpar arquivo temporário se foi descomprimido
if [ "$IS_COMPRESSED" = true ] && [ -f "$TEMP_SQL_FILE" ]; then
    rm -f "$TEMP_SQL_FILE"
    log "✓ Arquivo temporário removido"
fi

# Limpar senha da memória
unset PGPASSWORD

# Verificar integridade básica
log "Verificando integridade básica..."
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>> "$LOG_FILE" | xargs)

if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt 0 ]; then
    log "✓ Verificação básica OK - $TABLE_COUNT tabelas encontradas"
else
    log "⚠️  AVISO: Não foi possível verificar a integridade do banco"
fi

# Finalização
log "=========================================="
log "✓ Restauração concluída com sucesso!"
log "=========================================="
echo ""
echo "Restauração concluída! Verifique o log para detalhes: $LOG_FILE"
echo ""

# Retornar sucesso
exit 0

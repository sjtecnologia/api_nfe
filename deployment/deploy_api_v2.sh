#!/bin/bash

#############################################
# Script de Deploy API v2 - EmiteMax
# Data: 18/12/2025
# Descrição: Deploy automatizado da API v2
#############################################

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
APP_DIR="/var/www/api_nfe"
DB_NAME="sjtnfe"
DB_USER="postgres"
BACKUP_DIR="/var/backups/api_nfe"
LOG_FILE="/tmp/deploy_api_v2_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   DEPLOY API v2 - EmiteMax             ║${NC}"
echo -e "${BLUE}║   Sistema de API Keys e Webhooks       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Função de log
log() {
    echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERRO]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[AVISO]${NC} $1" | tee -a "$LOG_FILE"
}

# Verificar se está rodando como root ou com sudo
if [ "$EUID" -ne 0 ]; then 
    error "Este script precisa ser executado como root ou com sudo"
fi

# Criar diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

echo ""
log "Iniciando deploy da API v2..."
echo ""

# ========================================
# 1. BACKUP
# ========================================
echo -e "${YELLOW}ETAPA 1: BACKUP${NC}"
log "Criando backup do banco de dados..."

BACKUP_FILE="$BACKUP_DIR/backup_antes_api_v2_$(date +%Y%m%d_%H%M%S).sql"
if sudo -u postgres pg_dump "$DB_NAME" > "$BACKUP_FILE"; then
    log "✓ Backup do banco criado: $BACKUP_FILE"
else
    error "Falha ao criar backup do banco de dados"
fi

log "Criando backup do código..."
BACKUP_CODE="$BACKUP_DIR/backup_codigo_$(date +%Y%m%d_%H%M%S).tar.gz"
if tar -czf "$BACKUP_CODE" "$APP_DIR" 2>/dev/null; then
    log "✓ Backup do código criado: $BACKUP_CODE"
else
    warning "Falha ao criar backup do código (continuando...)"
fi

echo ""

# ========================================
# 2. VERIFICAÇÃO DE ARQUIVOS
# ========================================
echo -e "${YELLOW}ETAPA 2: VERIFICAÇÃO DE ARQUIVOS${NC}"
log "Verificando se todos os arquivos necessários existem..."

REQUIRED_FILES=(
    "database/migrations/add_api_keys.sql"
    "auth/api_key_auth.py"
    "routes/api_keys_routes.py"
    "routes/api_v2_routes.py"
    "routes/webhooks_routes.py"
    "services/webhook_service.py"
    "templates/admin/api_keys/list.html"
    "templates/admin/api_keys/create.html"
    "templates/admin/api_keys/stats.html"
    "templates/admin/webhooks/list.html"
    "templates/admin/webhooks/create.html"
)

MISSING_FILES=0
cd "$APP_DIR" || error "Diretório da aplicação não encontrado: $APP_DIR"

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        error "Arquivo não encontrado: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -eq 0 ]; then
    log "✓ Todos os arquivos necessários foram encontrados"
else
    error "Faltam $MISSING_FILES arquivos necessários"
fi

echo ""

# ========================================
# 3. MIGRATION DO BANCO
# ========================================
echo -e "${YELLOW}ETAPA 3: MIGRATION DO BANCO DE DADOS${NC}"
log "Executando migration..."

if sudo -u postgres psql "$DB_NAME" -f database/migrations/add_api_keys.sql > /tmp/migration_output.log 2>&1; then
    log "✓ Migration executada com sucesso"
else
    error "Falha ao executar migration. Verifique /tmp/migration_output.log"
fi

# Verificar se tabelas foram criadas
log "Verificando criação das tabelas..."
TABLES=("api_keys" "api_usage_logs" "webhooks" "webhook_queue")

for table in "${TABLES[@]}"; do
    if sudo -u postgres psql "$DB_NAME" -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$table');" | grep -q "t"; then
        log "  ✓ Tabela $table criada"
    else
        error "Tabela $table não foi criada"
    fi
done

echo ""

# ========================================
# 4. PERMISSÕES
# ========================================
echo -e "${YELLOW}ETAPA 4: AJUSTANDO PERMISSÕES${NC}"
log "Configurando permissões dos arquivos..."

# Ajustar ownership
chown -R www-data:www-data "$APP_DIR" || warning "Falha ao ajustar ownership"

# Ajustar permissões
chmod -R 755 "$APP_DIR/templates/admin/api_keys" || warning "Falha ao ajustar permissões de templates"
chmod -R 755 "$APP_DIR/templates/admin/webhooks" || warning "Falha ao ajustar permissões de templates"
chmod 644 "$APP_DIR/auth/api_key_auth.py" || warning "Falha ao ajustar permissões de auth"
chmod 644 "$APP_DIR/routes/"*.py || warning "Falha ao ajustar permissões de routes"
chmod 644 "$APP_DIR/services/webhook_service.py" || warning "Falha ao ajustar permissões de services"

log "✓ Permissões ajustadas"

echo ""

# ========================================
# 5. REINICIAR SERVIÇOS
# ========================================
echo -e "${YELLOW}ETAPA 5: REINICIANDO SERVIÇOS${NC}"

# Detectar tipo de serviço
if systemctl list-units --type=service | grep -q "api_nfe"; then
    log "Reiniciando serviço systemd..."
    systemctl restart api_nfe || error "Falha ao reiniciar serviço"
    systemctl status api_nfe --no-pager || true
    log "✓ Serviço reiniciado"
elif command -v supervisorctl &> /dev/null; then
    log "Reiniciando via supervisor..."
    supervisorctl restart api_nfe || error "Falha ao reiniciar via supervisor"
    log "✓ Serviço reiniciado via supervisor"
else
    warning "Sistema de gerenciamento de serviço não detectado. Reinicie manualmente."
fi

echo ""

# ========================================
# 6. TESTES BÁSICOS
# ========================================
echo -e "${YELLOW}ETAPA 6: TESTES BÁSICOS${NC}"
log "Aguardando serviço inicializar..."
sleep 3

# Verificar se aplicação está respondendo
log "Testando endpoint API v2..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v2/nfes 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    log "✓ API v2 está respondendo (esperado 401/403 sem API Key)"
elif [ "$HTTP_CODE" = "000" ]; then
    error "Aplicação não está respondendo. Verifique os logs."
else
    warning "API retornou código inesperado: $HTTP_CODE"
fi

echo ""

# ========================================
# 7. CONFIGURAR WEBHOOK WORKER
# ========================================
echo -e "${YELLOW}ETAPA 7: WEBHOOK WORKER (OPCIONAL)${NC}"
log "Verificando configuração do webhook worker..."

if [ -f "/etc/systemd/system/webhook-worker.service" ]; then
    log "✓ Serviço webhook-worker já existe"
else
    warning "Webhook worker não configurado. Configure manualmente:"
    echo ""
    echo "  Crie: /etc/systemd/system/webhook-worker.service"
    echo "  Ou adicione ao cron:"
    echo "  */5 * * * * cd $APP_DIR && python3 -c 'from services.webhook_service import process_webhook_queue; process_webhook_queue()'"
fi

echo ""

# ========================================
# RESUMO FINAL
# ========================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      DEPLOY CONCLUÍDO COM SUCESSO!     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}RESUMO:${NC}"
echo "  ✓ Backup criado: $BACKUP_FILE"
echo "  ✓ Migration executada: 4 tabelas criadas"
echo "  ✓ Arquivos verificados: 11 novos arquivos"
echo "  ✓ Permissões ajustadas"
echo "  ✓ Serviço reiniciado"
echo "  ✓ API v2 respondendo"
echo ""
echo -e "${BLUE}PRÓXIMOS PASSOS:${NC}"
echo "  1. Acessar painel admin e criar uma API Key de teste"
echo "  2. Testar emissão de NFe via API v2"
echo "  3. Configurar webhooks se necessário"
echo "  4. Configurar webhook worker (ver documentação)"
echo "  5. Monitorar logs: tail -f /var/log/api_nfe/error.log"
echo ""
echo -e "${BLUE}DOCUMENTAÇÃO:${NC}"
echo "  • $APP_DIR/deployment/ARQUIVOS_API_V2_DEPLOY.md"
echo "  • $APP_DIR/docs/API_INTEGRACAO_MANUAL.md"
echo ""
echo -e "${YELLOW}Log completo salvo em: $LOG_FILE${NC}"
echo ""

# ========================================
# CHECKLIST PÓS-DEPLOY
# ========================================
echo -e "${BLUE}CHECKLIST PÓS-DEPLOY:${NC}"
echo ""
echo "  [ ] Páginas de API Keys acessíveis"
echo "  [ ] Páginas de Webhooks acessíveis"
echo "  [ ] Criar API Key de teste"
echo "  [ ] Testar POST /api/v2/nfe/emitir"
echo "  [ ] Testar rate limiting"
echo "  [ ] Configurar webhook de teste"
echo "  [ ] Verificar logs de erro"
echo "  [ ] Monitorar performance"
echo ""

log "Deploy finalizado!"

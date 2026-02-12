#!/bin/bash

# ============================================================================
# Script de Deploy - Funcionalidade de Inutilização de Numeração NFe/NFCe
# Data: 12/02/2026
# Servidor: AWS EC2 (100.26.12.107)
# ============================================================================

set -e  # Exit on error

echo "============================================================================"
echo "🚀 DEPLOY: Inutilização de Numeração NFe/NFCe"
echo "============================================================================"
echo ""

# Configurações
SSH_KEY="$HOME/Downloads/nfe-new-api-key.pem"
SERVER="ubuntu@100.26.12.107"
REMOTE_DIR="/home/ubuntu/api_nfe"
SERVICE_NAME="api-nfe-principal"

# Verificar se a chave SSH existe
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Erro: Chave SSH não encontrada em $SSH_KEY"
    exit 1
fi

echo "📋 Checklist de Deploy:"
echo "  ✓ Backend: database/models.py"
echo "  ✓ Backend: services/sefaz_service.py"
echo "  ✓ Backend: routes/nfe_routes.py"
echo "  ✓ Frontend: templates/admin/nfes/inutilizar.html"
echo "  ✓ Frontend: templates/admin/nfes/listar_inutilizacoes.html"
echo "  ✓ Frontend: templates/admin/nfes/list.html"
echo "  ✓ Migration: migrations/005_create_nfe_inutilizacoes_table.sql"
echo "  ✓ Migration: migrations/run_migration_inutilizacao.py"
echo ""

# Confirmação
read -p "🤔 Continuar com o deploy? (s/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo "❌ Deploy cancelado pelo usuário"
    exit 0
fi

echo ""
echo "============================================================================"
echo "📦 ETAPA 1: Backup dos arquivos atuais no servidor"
echo "============================================================================"

ssh -i "$SSH_KEY" "$SERVER" << 'ENDSSH'
cd /home/ubuntu/api_nfe
BACKUP_DIR="backups/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📁 Criando backup em: $BACKUP_DIR"

# Backup dos arquivos que serão modificados
[ -f database/models.py ] && cp database/models.py "$BACKUP_DIR/"
[ -f services/sefaz_service.py ] && cp services/sefaz_service.py "$BACKUP_DIR/"
[ -f routes/nfe_routes.py ] && cp routes/nfe_routes.py "$BACKUP_DIR/"
[ -f templates/admin/nfes/list.html ] && cp templates/admin/nfes/list.html "$BACKUP_DIR/"

echo "✅ Backup concluído"
ENDSSH

echo ""
echo "============================================================================"
echo "📤 ETAPA 2: Upload dos arquivos para o servidor"
echo "============================================================================"

# Backend
echo "📄 Uploading: database/models.py"
scp -i "$SSH_KEY" database/models.py "$SERVER:/tmp/"

echo "📄 Uploading: services/sefaz_service.py"
scp -i "$SSH_KEY" services/sefaz_service.py "$SERVER:/tmp/"

echo "📄 Uploading: routes/nfe_routes.py"
scp -i "$SSH_KEY" routes/nfe_routes.py "$SERVER:/tmp/"

# Frontend
echo "📄 Uploading: templates/admin/nfes/inutilizar.html"
scp -i "$SSH_KEY" templates/admin/nfes/inutilizar.html "$SERVER:/tmp/"

echo "📄 Uploading: templates/admin/nfes/listar_inutilizacoes.html"
scp -i "$SSH_KEY" templates/admin/nfes/listar_inutilizacoes.html "$SERVER:/tmp/"

echo "📄 Uploading: templates/admin/nfes/list.html"
scp -i "$SSH_KEY" templates/admin/nfes/list.html "$SERVER:/tmp/"

# Migrations
echo "📄 Uploading: migrations/005_create_nfe_inutilizacoes_table.sql"
scp -i "$SSH_KEY" migrations/005_create_nfe_inutilizacoes_table.sql "$SERVER:/tmp/"

echo "📄 Uploading: migrations/run_migration_inutilizacao.py"
scp -i "$SSH_KEY" migrations/run_migration_inutilizacao.py "$SERVER:/tmp/"

echo "✅ Upload concluído"

echo ""
echo "============================================================================"
echo "📂 ETAPA 3: Movendo arquivos para posições finais"
echo "============================================================================"

ssh -i "$SSH_KEY" "$SERVER" << 'ENDSSH'
cd /home/ubuntu/api_nfe

echo "📦 Movendo arquivos backend..."
sudo mv /tmp/models.py database/
sudo mv /tmp/sefaz_service.py services/
sudo mv /tmp/nfe_routes.py routes/

echo "🎨 Movendo templates..."
sudo mv /tmp/inutilizar.html templates/admin/nfes/
sudo mv /tmp/listar_inutilizacoes.html templates/admin/nfes/
sudo mv /tmp/list.html templates/admin/nfes/

echo "🗄️ Movendo migrations..."
sudo mv /tmp/005_create_nfe_inutilizacoes_table.sql migrations/
sudo mv /tmp/run_migration_inutilizacao.py migrations/

echo "🔑 Ajustando permissões..."
sudo chown -R ubuntu:ubuntu database/ services/ routes/ templates/ migrations/
sudo chmod 644 database/models.py services/sefaz_service.py routes/nfe_routes.py
sudo chmod 644 templates/admin/nfes/*.html
sudo chmod 755 migrations/run_migration_inutilizacao.py

echo "✅ Arquivos movidos e permissões ajustadas"
ENDSSH

echo ""
echo "============================================================================"
echo "🗄️ ETAPA 4: Executando Migration no RDS"
echo "============================================================================"

ssh -i "$SSH_KEY" "$SERVER" << 'ENDSSH'
cd /home/ubuntu/api_nfe

echo "📊 Executando migration..."
python3 migrations/run_migration_inutilizacao.py

if [ $? -eq 0 ]; then
    echo "✅ Migration executada com sucesso!"
else
    echo "❌ Erro ao executar migration"
    exit 1
fi
ENDSSH

echo ""
echo "============================================================================"
echo "🔄 ETAPA 5: Reiniciando Serviço Flask"
echo "============================================================================"

ssh -i "$SSH_KEY" "$SERVER" << 'ENDSSH'
echo "🛑 Parando serviço..."
sudo systemctl stop api-nfe-principal

echo "⏳ Aguardando 3 segundos..."
sleep 3

echo "🚀 Iniciando serviço..."
sudo systemctl start api-nfe-principal

echo "⏳ Aguardando 5 segundos para inicialização..."
sleep 5

echo "📊 Status do serviço:"
sudo systemctl status api-nfe-principal --no-pager -l

if sudo systemctl is-active --quiet api-nfe-principal; then
    echo "✅ Serviço iniciado com sucesso!"
else
    echo "❌ Erro ao iniciar serviço!"
    exit 1
fi
ENDSSH

echo ""
echo "============================================================================"
echo "🔍 ETAPA 6: Verificando Logs"
echo "============================================================================"

echo "📋 Últimas 30 linhas do log:"
ssh -i "$SSH_KEY" "$SERVER" "sudo journalctl -u api-nfe-principal -n 30 --no-pager"

echo ""
echo "============================================================================"
echo "✅ DEPLOY CONCLUÍDO COM SUCESSO!"
echo "============================================================================"
echo ""
echo "📊 Resumo:"
echo "  • Backend: 3 arquivos atualizados"
echo "  • Frontend: 3 templates criados/atualizados"
echo "  • Migration: Tabela nfe_inutilizacoes criada"
echo "  • Serviço: Reiniciado com sucesso"
echo ""
echo "🌐 URLs de Teste:"
echo "  • Formulário: http://100.26.12.107:8080/nfe/inutilizar/form?cliente_id=29"
echo "  • Listagem: http://100.26.12.107:8080/nfe/inutilizacoes?cliente_id=29"
echo ""
echo "📝 Próximos passos:"
echo "  1. Testar formulário de inutilização"
echo "  2. Testar processamento com SEFAZ (homologação)"
echo "  3. Verificar listagem e filtros"
echo "  4. Testar download de XMLs"
echo ""
echo "🔍 Monitorar logs em tempo real:"
echo "  ssh -i $SSH_KEY $SERVER 'sudo journalctl -u api-nfe-principal -f'"
echo ""
echo "============================================================================"

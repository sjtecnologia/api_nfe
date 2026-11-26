#!/bin/bash

# Script para atualizar .env na EC2 e reiniciar serviços

set -e

SSH_KEY="$HOME/Downloads/nfe-new-api-key.pem"
EC2_HOST="ubuntu@3.87.73.106"
RDS_ENDPOINT="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
RDS_PASSWORD="***SENHA_RDS_ROTACIONADA***"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 ATUALIZANDO CONFIGURAÇÕES NA EC2"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Conectar na EC2 e executar comandos
ssh -i ${SSH_KEY} ${EC2_HOST} << 'ENDSSH'

echo "1️⃣ Fazendo backup do .env atual..."
if [ -f /home/ubuntu/api_nfe/.env ]; then
    cp /home/ubuntu/api_nfe/.env /home/ubuntu/api_nfe/.env.backup.$(date +%Y%m%d_%H%M%S)
    echo "   ✅ Backup criado"
else
    echo "   ℹ️  Arquivo .env não existe, criando novo"
fi

echo ""
echo "2️⃣ Atualizando arquivo .env com credenciais do RDS..."

cat > /home/ubuntu/api_nfe/.env << 'EOF'
# Flask Configuration
FLASK_SECRET_KEY=***FLASK_SECRET_KEY_ROTACIONADA***
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
PORT=8080

# Database Configuration (RDS)
DATABASE_URL=postgresql://postgres:***SENHA_RDS_ROTACIONADA***@nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com:5432/sjtnfe
DB_HOST=nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=sjtnfe
DB_USER=postgres
DB_PASSWORD=***SENHA_RDS_ROTACIONADA***

# Upload and Storage
UPLOAD_FOLDER=/home/ubuntu/api_nfe/uploads
BACKUP_DIR=/home/ubuntu/api_nfe/backups
BACKUP_LOG_DIR=/home/ubuntu/api_nfe/logs

# Log Configuration
LOG_LEVEL=INFO

# SEFAZ Configuration
SEFAZ_AMBIENTE_HOMOLOGACAO=True
USAR_CERTIFICADO_REAL=True
EOF

echo "   ✅ Arquivo .env atualizado"

echo ""
echo "3️⃣ Testando conexão com RDS..."
if PGPASSWORD='***SENHA_RDS_ROTACIONADA***' psql -h nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com -U postgres -d sjtnfe -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" > /dev/null 2>&1; then
    echo "   ✅ Conexão com RDS funcionando"
else
    echo "   ❌ ERRO: Não foi possível conectar ao RDS"
    exit 1
fi

echo ""
echo "4️⃣ Verificando se serviços existem..."
if systemctl list-unit-files | grep -q "api-nfe-principal.service"; then
    echo "   ✅ Serviço api-nfe-principal encontrado"
    HAS_PRINCIPAL=true
else
    echo "   ⚠️  Serviço api-nfe-principal não encontrado"
    HAS_PRINCIPAL=false
fi

if systemctl list-unit-files | grep -q "api-nfe-ia.service"; then
    echo "   ✅ Serviço api-nfe-ia encontrado"
    HAS_IA=true
else
    echo "   ⚠️  Serviço api-nfe-ia não encontrado"
    HAS_IA=false
fi

echo ""
echo "5️⃣ Reiniciando serviços..."
if [ "$HAS_PRINCIPAL" = true ]; then
    sudo systemctl restart api-nfe-principal
    echo "   ✅ api-nfe-principal reiniciado"
else
    echo "   ℹ️  api-nfe-principal não instalado (pule para ETAPA 7 do guia)"
fi

if [ "$HAS_IA" = true ]; then
    sudo systemctl restart api-nfe-ia
    echo "   ✅ api-nfe-ia reiniciado"
else
    echo "   ℹ️  api-nfe-ia não instalado (pule para ETAPA 7 do guia)"
fi

echo ""
echo "6️⃣ Verificando status dos serviços..."
sleep 3

if [ "$HAS_PRINCIPAL" = true ]; then
    echo ""
    echo "   📊 Status api-nfe-principal:"
    sudo systemctl status api-nfe-principal --no-pager -l | head -15
fi

if [ "$HAS_IA" = true ]; then
    echo ""
    echo "   📊 Status api-nfe-ia:"
    sudo systemctl status api-nfe-ia --no-pager -l | head -15
fi

echo ""
echo "7️⃣ Testando endpoint da aplicação..."
sleep 2
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health | grep -q "200"; then
    echo "   ✅ Aplicação respondendo em http://localhost:8080/health"
else
    echo "   ⚠️  Aplicação não está respondendo ainda (pode levar alguns segundos)"
fi

ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ATUALIZAÇÃO CONCLUÍDA!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Próximos passos:"
echo "   1. Testar aplicação: https://api.emitemax.com.br/health"
echo "   2. Verificar logs: ssh -i ${SSH_KEY} ${EC2_HOST}"
echo "      sudo journalctl -u api-nfe-principal -f"
echo ""

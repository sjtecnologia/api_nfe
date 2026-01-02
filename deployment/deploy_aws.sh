#!/bin/bash

# Script de Deploy Automatizado - AWS EC2
# Uso: ./deploy_aws.sh

set -e

echo "================================================"
echo "🚀 Deploy Automatizado - API NFe na AWS"
echo "================================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se está rodando na EC2
if [ ! -f /etc/cloud/cloud.cfg ]; then
    echo -e "${RED}❌ Este script deve ser executado na instância EC2${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Verificando configuração...${NC}"

# Verificar se .env existe
if [ ! -f /home/ubuntu/api_nfe/.env ]; then
    echo -e "${RED}❌ Arquivo .env não encontrado!${NC}"
    echo "Crie o arquivo /home/ubuntu/api_nfe/.env com as configurações necessárias"
    exit 1
fi

# Verificar se venv existe
if [ ! -d /home/ubuntu/api_nfe/venv ]; then
    echo -e "${YELLOW}📦 Criando virtual environment...${NC}"
    cd /home/ubuntu/api_nfe
    python3 -m venv venv
fi

echo -e "${GREEN}✅ Configuração verificada${NC}"
echo ""

# Ativar virtual environment
echo -e "${YELLOW}🔧 Ativando virtual environment...${NC}"
cd /home/ubuntu/api_nfe
source venv/bin/activate

# Atualizar pip
echo -e "${YELLOW}📦 Atualizando pip...${NC}"
pip install --upgrade pip

# Instalar dependências
echo -e "${YELLOW}📦 Instalando dependências...${NC}"
pip install -r requirements.txt
pip install gunicorn uvicorn python-dotenv

echo -e "${GREEN}✅ Dependências instaladas${NC}"
echo ""

# Criar diretórios necessários
echo -e "${YELLOW}📁 Criando diretórios...${NC}"
mkdir -p /home/ubuntu/api_nfe/uploads
mkdir -p /home/ubuntu/api_nfe/backups
mkdir -p /home/ubuntu/api_nfe/logs
chmod 755 /home/ubuntu/api_nfe/uploads
chmod 755 /home/ubuntu/api_nfe/backups
chmod 755 /home/ubuntu/api_nfe/logs

echo -e "${GREEN}✅ Diretórios criados${NC}"
echo ""

# Verificar conexão com banco
echo -e "${YELLOW}🗄️  Verificando conexão com banco de dados...${NC}"
source /home/ubuntu/api_nfe/.env

if psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Conexão com banco OK${NC}"
else
    echo -e "${RED}❌ Erro ao conectar no banco de dados${NC}"
    echo "Verifique as configurações no arquivo .env"
    exit 1
fi
echo ""

# Copiar arquivos de serviço systemd
echo -e "${YELLOW}⚙️  Configurando serviços systemd...${NC}"

# Flask App
sudo tee /etc/systemd/system/api-nfe-principal.service > /dev/null <<EOF
[Unit]
Description=API NFe Principal - Flask Application
After=network.target postgresql.service

[Service]
Type=notify
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/api_nfe
Environment="PATH=/home/ubuntu/api_nfe/venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/home/ubuntu/api_nfe/.env
ExecStart=/home/ubuntu/api_nfe/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8080 \
    --timeout 300 \
    --access-logfile /home/ubuntu/api_nfe/logs/access.log \
    --error-logfile /home/ubuntu/api_nfe/logs/error.log \
    --log-level info \
    app:app

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# IA Service
sudo tee /etc/systemd/system/api-nfe-ia.service > /dev/null <<EOF
[Unit]
Description=API NFe IA Service - FastAPI
After=network.target ollama.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/api_nfe/ia_service
Environment="PATH=/home/ubuntu/api_nfe/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/ubuntu/api_nfe/venv/bin/uvicorn \
    main:app \
    --host 0.0.0.0 \
    --port 8081 \
    --workers 2 \
    --log-level info

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Serviços configurados${NC}"
echo ""

# Recarregar systemd
echo -e "${YELLOW}🔄 Recarregando systemd...${NC}"
sudo systemctl daemon-reload

# Habilitar serviços
echo -e "${YELLOW}✅ Habilitando serviços...${NC}"
sudo systemctl enable api-nfe-principal
sudo systemctl enable api-nfe-ia

# Reiniciar serviços
echo -e "${YELLOW}🔄 Reiniciando serviços...${NC}"
sudo systemctl restart api-nfe-principal
sudo systemctl restart api-nfe-ia

# Aguardar inicialização
echo -e "${YELLOW}⏳ Aguardando serviços iniciarem...${NC}"
sleep 5

# Verificar status
echo ""
echo -e "${YELLOW}📊 Status dos serviços:${NC}"
echo ""

if systemctl is-active --quiet api-nfe-principal; then
    echo -e "${GREEN}✅ Flask App: RODANDO${NC}"
else
    echo -e "${RED}❌ Flask App: PARADO${NC}"
    sudo journalctl -u api-nfe-principal -n 20
fi

if systemctl is-active --quiet api-nfe-ia; then
    echo -e "${GREEN}✅ IA Service: RODANDO${NC}"
else
    echo -e "${RED}❌ IA Service: PARADO${NC}"
    sudo journalctl -u api-nfe-ia -n 20
fi

if systemctl is-active --quiet ollama; then
    echo -e "${GREEN}✅ Ollama: RODANDO${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama: NÃO DETECTADO${NC}"
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx: RODANDO${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx: NÃO RODANDO${NC}"
fi

echo ""
echo "================================================"
echo -e "${GREEN}🎉 Deploy concluído!${NC}"
echo "================================================"
echo ""
echo "📝 Próximos passos:"
echo "1. Configurar Nginx (ver guia AWS_DEPLOY_COMPLETO.md)"
echo "2. Configurar domínio e SSL"
echo "3. Testar aplicação em: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
echo ""
echo "📊 Ver logs:"
echo "  - Flask: sudo journalctl -u api-nfe-principal -f"
echo "  - IA: sudo journalctl -u api-nfe-ia -f"
echo ""

#!/bin/bash

# Script de Atualização Rápida - AWS
# Para atualizar código sem reinstalar tudo
# Uso: ./atualizar_codigo_aws.sh

set -e

echo "================================================"
echo "🔄 Atualização Rápida - API NFe"
echo "================================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /home/ubuntu/api_nfe

# Fazer backup do .env
echo -e "${YELLOW}💾 Fazendo backup do .env...${NC}"
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Atualizar código (escolha o método)
echo -e "${YELLOW}📥 Escolha o método de atualização:${NC}"
echo "1) Git pull"
echo "2) Copiar via SCP (do Mac)"
echo "3) Já atualizei manualmente"
read -p "Opção (1-3): " opcao

case $opcao in
    1)
        echo -e "${YELLOW}🔄 Atualizando via Git...${NC}"
        git pull
        ;;
    2)
        echo -e "${YELLOW}📋 Execute no seu Mac:${NC}"
        IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
        echo ""
        echo "cd ~/Documents/Developement"
        echo "tar -czf api_nfe.tar.gz api_nfe"
        echo "scp -i ~/Downloads/nfe-api-key.pem api_nfe.tar.gz ubuntu@$IP:/home/ubuntu/"
        echo ""
        read -p "Pressione ENTER após copiar os arquivos..."
        
        # Descompactar
        cd /home/ubuntu
        tar -xzf api_nfe.tar.gz
        cd api_nfe
        ;;
    3)
        echo -e "${GREEN}✅ Ok, continuando...${NC}"
        ;;
    *)
        echo "Opção inválida"
        exit 1
        ;;
esac

# Restaurar .env
echo -e "${YELLOW}🔧 Restaurando configuração...${NC}"
if [ -f .env.backup.* ]; then
    latest_backup=$(ls -t .env.backup.* | head -1)
    cp $latest_backup .env
fi

# Atualizar dependências
echo -e "${YELLOW}📦 Atualizando dependências...${NC}"
source venv/bin/activate
pip install -r requirements.txt

# Migrar banco (se houver novas migrations)
echo -e "${YELLOW}🗄️  Verificando migrations...${NC}"
if [ -d "database/migrations" ]; then
    source .env
    for migration in database/migrations/*.sql; do
        if [ -f "$migration" ]; then
            echo "Executando: $migration"
            psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f "$migration" || true
        fi
    done
fi

# Reiniciar serviços
echo -e "${YELLOW}🔄 Reiniciando serviços...${NC}"
sudo systemctl restart api-nfe-principal
sudo systemctl restart api-nfe-ia

# Aguardar
sleep 5

# Verificar status
echo ""
echo -e "${YELLOW}📊 Status:${NC}"

if systemctl is-active --quiet api-nfe-principal; then
    echo -e "${GREEN}✅ Flask App: OK${NC}"
else
    echo -e "${RED}❌ Flask App: ERRO${NC}"
    sudo journalctl -u api-nfe-principal -n 20
fi

if systemctl is-active --quiet api-nfe-ia; then
    echo -e "${GREEN}✅ IA Service: OK${NC}"
else
    echo -e "${RED}❌ IA Service: ERRO${NC}"
    sudo journalctl -u api-nfe-ia -n 20
fi

echo ""
echo "================================================"
echo -e "${GREEN}🎉 Atualização concluída!${NC}"
echo "================================================"
echo ""
echo "📝 Testar aplicação:"
IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "http://$IP"
echo ""

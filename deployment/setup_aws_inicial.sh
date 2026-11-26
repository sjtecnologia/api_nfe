#!/bin/bash

# Script de Setup Inicial - AWS EC2
# Executa na primeira vez após criar a instância EC2
# Uso: ./setup_aws_inicial.sh

set -e

echo "================================================"
echo "🔧 Setup Inicial - Servidor AWS EC2"
echo "================================================"
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}📦 Atualizando sistema...${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "${YELLOW}📦 Instalando dependências base...${NC}"

# Python e ferramentas
sudo apt install -y python3.10 python3-pip python3-venv python3-dev

# PostgreSQL client
sudo apt install -y postgresql-client

# Build essentials
sudo apt install -y build-essential libssl-dev libffi-dev

# Git
sudo apt install -y git

# XML libraries
sudo apt install -y libxml2-dev libxslt1-dev

# PKCS11 (certificados A3)
sudo apt install -y libpcsclite-dev pcscd

# Nginx
sudo apt install -y nginx

# Supervisor
sudo apt install -y supervisor

# Utilidades
sudo apt install -y htop curl wget unzip

echo -e "${GREEN}✅ Dependências instaladas${NC}"
echo ""

# Instalar Ollama
echo -e "${YELLOW}🤖 Instalando Ollama...${NC}"
curl -fsSL https://ollama.com/install.sh | sh

echo -e "${YELLOW}🤖 Baixando modelo CodeLlama...${NC}"
ollama pull codellama:7b-instruct

echo -e "${GREEN}✅ Ollama instalado${NC}"
echo ""

# Configurar serviço Ollama
echo -e "${YELLOW}⚙️  Configurando serviço Ollama...${NC}"
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama LLM Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="OLLAMA_HOST=0.0.0.0:1234"
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

echo -e "${GREEN}✅ Ollama configurado${NC}"
echo ""

# Configurar firewall UFW
echo -e "${YELLOW}🔒 Configurando firewall...${NC}"
sudo ufw --force enable
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status

echo -e "${GREEN}✅ Firewall configurado${NC}"
echo ""

# Instalar e configurar Fail2Ban
echo -e "${YELLOW}🔒 Instalando Fail2Ban...${NC}"
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

echo -e "${GREEN}✅ Fail2Ban instalado${NC}"
echo ""

# Criar script de backup
echo -e "${YELLOW}💾 Criando script de backup...${NC}"
cat > /home/ubuntu/backup-database.sh <<'EOF'
#!/bin/bash

BACKUP_DIR="/home/ubuntu/api_nfe/backups"
DATE=$(date +%Y%m%d_%H%M%S)
source /home/ubuntu/api_nfe/.env

# Criar diretório
mkdir -p $BACKUP_DIR

# Fazer backup
export PGPASSWORD=$DB_PASSWORD
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f "$BACKUP_DIR/backup_$DATE.dump"

# Remover backups antigos (>7 dias)
find $BACKUP_DIR -name "backup_*.dump" -mtime +7 -delete

echo "Backup concluído: backup_$DATE.dump"
EOF

chmod +x /home/ubuntu/backup-database.sh

echo -e "${GREEN}✅ Script de backup criado${NC}"
echo ""

# Configurar cron para backup
echo -e "${YELLOW}⏰ Configurando backup automático...${NC}"
(crontab -l 2>/dev/null; echo "0 3 * * * /home/ubuntu/backup-database.sh >> /home/ubuntu/api_nfe/logs/backup.log 2>&1") | crontab -

echo -e "${GREEN}✅ Backup automático configurado (diariamente às 3h)${NC}"
echo ""

# Configurar cron para auditoria diária do assistente fiscal
echo -e "${YELLOW}🛡️ Configurando auditoria diária do assistente fiscal...${NC}"
(crontab -l 2>/dev/null; echo "30 6 * * * cd /home/ubuntu/api_nfe && /usr/bin/python3 /home/ubuntu/api_nfe/scripts/auditoria_assistente_diaria.py >> /home/ubuntu/api_nfe/logs/assistente_auditoria.log 2>&1") | crontab -

echo -e "${GREEN}✅ Auditoria diária do assistente configurada (06:30)${NC}"
echo ""

# Configurar cron para resumo diário do consultor de vendas
echo -e "${YELLOW}📈 Configurando resumo diário do consultor de vendas...${NC}"
(crontab -l 2>/dev/null; echo "45 6 * * * cd /home/ubuntu/api_nfe && /usr/bin/python3 /home/ubuntu/api_nfe/scripts/consultor_vendas_diario.py >> /home/ubuntu/api_nfe/logs/consultor_vendas_diario.log 2>&1") | crontab -

echo -e "${GREEN}✅ Resumo diário do consultor configurado (06:45)${NC}"
echo ""

# Criar alias úteis
echo -e "${YELLOW}🔧 Configurando aliases...${NC}"
cat >> /home/ubuntu/.bashrc <<'EOF'

# Aliases API NFe
alias nfe-logs='sudo journalctl -u api-nfe-principal -f'
alias ia-logs='sudo journalctl -u api-nfe-ia -f'
alias nfe-restart='sudo systemctl restart api-nfe-principal api-nfe-ia nginx'
alias nfe-status='sudo systemctl status api-nfe-principal api-nfe-ia ollama nginx'
alias nfe-backup='bash /home/ubuntu/backup-database.sh'
alias nfe-auditoria-assistente='cd /home/ubuntu/api_nfe && /usr/bin/python3 /home/ubuntu/api_nfe/scripts/auditoria_assistente_diaria.py'
alias nfe-consultor-diario='cd /home/ubuntu/api_nfe && /usr/bin/python3 /home/ubuntu/api_nfe/scripts/consultor_vendas_diario.py'

EOF

echo -e "${GREEN}✅ Aliases configurados${NC}"
echo ""

echo "================================================"
echo -e "${GREEN}🎉 Setup inicial concluído!${NC}"
echo "================================================"
echo ""
echo "📝 Próximos passos:"
echo ""
echo "1. Criar arquivo .env com as configurações:"
echo "   nano /home/ubuntu/api_nfe/.env"
echo ""
echo "2. Copiar código da aplicação:"
echo "   - Via git: git clone https://github.com/sjtecnologia/api_nfe.git"
echo "   - Via SCP do seu Mac"
echo ""
echo "3. Executar script de deploy:"
echo "   cd /home/ubuntu/api_nfe/deployment"
echo "   bash deploy_aws.sh"
echo ""
echo "4. Configurar Nginx (ver AWS_DEPLOY_COMPLETO.md)"
echo ""
echo "🔍 Serviços instalados:"
echo "  ✅ Python 3.10"
echo "  ✅ PostgreSQL client"
echo "  ✅ Nginx"
echo "  ✅ Ollama (CodeLlama)"
echo "  ✅ Fail2Ban"
echo "  ✅ UFW Firewall"
echo ""
echo "📚 Aliases disponíveis (após logout/login):"
echo "  - nfe-logs: Ver logs da aplicação principal"
echo "  - ia-logs: Ver logs do serviço de IA"
echo "  - nfe-restart: Reiniciar todos os serviços"
echo "  - nfe-status: Ver status de todos os serviços"
echo "  - nfe-backup: Fazer backup manual do banco"
echo ""

#!/bin/bash

# Script para deploy das correções do campo ambiente no AWS
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================================"
echo "🚀 Deploy de Correções - Campo Ambiente"
echo "================================================"
echo ""

# Solicitar IP do servidor AWS
echo -e "${YELLOW}Digite o IP público do servidor AWS EC2:${NC}"
read -p "IP: " AWS_IP

if [ -z "$AWS_IP" ]; then
    echo -e "${RED}❌ IP não pode ser vazio!${NC}"
    exit 1
fi

# Verificar chave SSH
SSH_KEY="$HOME/Downloads/nfe-new-api-key.pem"
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ Chave SSH não encontrada: $SSH_KEY${NC}"
    exit 1
fi

# Verificar permissões da chave
chmod 400 "$SSH_KEY"

echo ""
echo -e "${GREEN}✅ Configuração validada${NC}"
echo "   IP: $AWS_IP"
echo "   Chave: $SSH_KEY"
echo ""

# Criar tarball com apenas os arquivos modificados
echo -e "${YELLOW}📦 Criando pacote de atualização...${NC}"
tar -czf /tmp/api_nfe_fixes.tar.gz \
    routes/nfe_routes.py \
    templates/admin/danfe/danfce.html

echo -e "${GREEN}✅ Pacote criado${NC}"
echo ""

# Fazer backup no servidor
echo -e "${YELLOW}💾 Criando backup no servidor...${NC}"
ssh -i "$SSH_KEY" ubuntu@$AWS_IP << 'EOF'
cd /home/ubuntu/api_nfe
mkdir -p backups/ambiente_fix_$(date +%Y%m%d_%H%M%S)
cp routes/nfe_routes.py backups/ambiente_fix_$(date +%Y%m%d_%H%M%S)/
cp templates/admin/danfe/danfce.html backups/ambiente_fix_$(date +%Y%m%d_%H%M%S)/
echo "Backup criado em: backups/ambiente_fix_$(date +%Y%m%d_%H%M%S)"
EOF

echo -e "${GREEN}✅ Backup criado${NC}"
echo ""

# Copiar arquivos para o servidor
echo -e "${YELLOW}📤 Enviando arquivos para AWS...${NC}"
scp -i "$SSH_KEY" /tmp/api_nfe_fixes.tar.gz ubuntu@$AWS_IP:/tmp/

echo -e "${GREEN}✅ Arquivos enviados${NC}"
echo ""

# Extrair e aplicar no servidor
echo -e "${YELLOW}🔧 Aplicando correções...${NC}"
ssh -i "$SSH_KEY" ubuntu@$AWS_IP << 'EOF'
cd /home/ubuntu/api_nfe
tar -xzf /tmp/api_nfe_fixes.tar.gz
echo "Arquivos extraídos com sucesso"
EOF

echo -e "${GREEN}✅ Correções aplicadas${NC}"
echo ""

# Reiniciar serviços
echo -e "${YELLOW}🔄 Reiniciando serviços...${NC}"
ssh -i "$SSH_KEY" ubuntu@$AWS_IP << 'EOF'
sudo systemctl restart api-nfe-principal
sudo systemctl restart api-nfe-ia
echo "Serviços reiniciados"
EOF

echo -e "${GREEN}✅ Serviços reiniciados${NC}"
echo ""

# Aguardar inicialização
echo -e "${YELLOW}⏳ Aguardando inicialização dos serviços...${NC}"
sleep 10

# Verificar status
echo -e "${YELLOW}📊 Verificando status dos serviços...${NC}"
ssh -i "$SSH_KEY" ubuntu@$AWS_IP << 'EOF'
echo ""
echo "=== Status API Principal ==="
sudo systemctl status api-nfe-principal --no-pager | head -10
echo ""
echo "=== Status IA Service ==="
sudo systemctl status api-nfe-ia --no-pager | head -10
echo ""

# Verificar se está rodando
if systemctl is-active --quiet api-nfe-principal; then
    echo "✅ Flask App: RODANDO"
else
    echo "❌ Flask App: ERRO"
    echo "Logs:"
    sudo journalctl -u api-nfe-principal -n 20 --no-pager
fi

if systemctl is-active --quiet api-nfe-ia; then
    echo "✅ IA Service: RODANDO"
else
    echo "❌ IA Service: ERRO"
    echo "Logs:"
    sudo journalctl -u api-nfe-ia -n 20 --no-pager
fi
EOF

echo ""
echo "================================================"
echo -e "${GREEN}🎉 Deploy concluído!${NC}"
echo "================================================"
echo ""
echo "📝 Arquivos atualizados:"
echo "   - routes/nfe_routes.py (linha 147)"
echo "   - templates/admin/danfe/danfce.html (linha 261)"
echo ""
echo "🔧 Correção aplicada:"
echo "   ambiente=2 agora corretamente identifica PRODUÇÃO"
echo "   ambiente=1 agora corretamente identifica HOMOLOGAÇÃO"
echo ""
echo "🌐 Acesse a aplicação em:"
echo "   http://$AWS_IP"
echo ""
echo "📋 Para verificar logs:"
echo "   ssh -i $SSH_KEY ubuntu@$AWS_IP"
echo "   sudo journalctl -u api-nfe-principal -f"
echo ""

# Limpar arquivo temporário
rm -f /tmp/api_nfe_fixes.tar.gz

echo -e "${GREEN}✨ Tudo pronto!${NC}"

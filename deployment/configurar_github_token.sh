#!/bin/bash

# Script para configurar GitHub Token para usar GitHub Models API

echo "=== Configuração GitHub Models API ==="
echo ""
echo "Este script configura o token do GitHub para usar modelos de IA gratuitos."
echo ""

# Verificar se já existe token
if [ -f /home/ubuntu/api_nfe/.env ]; then
    if grep -q "GITHUB_TOKEN" /home/ubuntu/api_nfe/.env; then
        echo "✅ Token do GitHub já está configurado em .env"
        echo ""
        echo "Para atualizar o token:"
        echo "1. Edite: /home/ubuntu/api_nfe/.env"
        echo "2. Atualize a linha: GITHUB_TOKEN=seu_novo_token"
        echo "3. Reinicie: sudo systemctl restart api-nfe-ia"
        exit 0
    fi
fi

echo "Para obter o token do GitHub:"
echo ""
echo "1. Acesse: https://github.com/settings/tokens"
echo "2. Clique em 'Generate new token' → 'Generate new token (classic)'"
echo "3. Dê um nome: 'NFe IA Validation'"
echo "4. Marque o scope: [x] read:packages"
echo "5. Clique em 'Generate token'"
echo "6. COPIE o token (só aparece uma vez!)"
echo ""
echo "OU use token existente do GitHub CLI:"
echo "   gh auth token"
echo ""

read -p "Cole o token do GitHub aqui: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Token não fornecido. Saindo..."
    exit 1
fi

# Adicionar ao .env
if [ ! -f /home/ubuntu/api_nfe/.env ]; then
    touch /home/ubuntu/api_nfe/.env
fi

# Adicionar ou atualizar GITHUB_TOKEN
if grep -q "GITHUB_TOKEN" /home/ubuntu/api_nfe/.env; then
    sed -i "s/GITHUB_TOKEN=.*/GITHUB_TOKEN=$GITHUB_TOKEN/" /home/ubuntu/api_nfe/.env
else
    echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> /home/ubuntu/api_nfe/.env
fi

echo ""
echo "✅ Token configurado em /home/ubuntu/api_nfe/.env"
echo ""
echo "Reiniciando serviço de IA..."
sudo systemctl restart api-nfe-ia

sleep 2

echo ""
echo "=== Status do Serviço ==="
sudo systemctl status api-nfe-ia --no-pager | head -10

echo ""
echo "✅ Pronto! Agora o sistema usa GitHub Models API (muito mais rápido!)"
echo ""
echo "Modelos disponíveis:"
echo "  - gpt-4o-mini (padrão - rápido e preciso)"
echo "  - gpt-4o (mais poderoso)"
echo "  - Claude 3.5 Sonnet"
echo ""
echo "Para testar:"
echo "  curl -X POST http://localhost:8081/valida/tributacao \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"crt\": \"1\", \"itens\": [{\"cfop\": \"5405\", \"csosn_icms\": \"102\"}]}'"

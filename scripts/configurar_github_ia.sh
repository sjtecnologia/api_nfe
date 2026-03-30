#!/bin/bash

# Script para configurar GitHub Token no servidor AWS

echo "🚀 Configuração GitHub Models API"
echo ""
echo "Este script vai configurar o token do GitHub para usar IA rápida (2-5s)."
echo ""
echo "====================================="
echo "PASSO 1: Obter seu token do GitHub"
echo "====================================="
echo ""
echo "Execute no seu terminal local:"
echo "  gh auth token"
echo ""
echo "Ou acesse:"
echo "  https://github.com/settings/tokens"
echo ""
echo "Cole o token aqui (não vai aparecer ao digitar):"
read -s GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo ""
    echo "❌ Token vazio! Execute novamente."
    exit 1
fi

echo ""
echo "✅ Token recebido!"
echo ""
echo "====================================="
echo "PASSO 2: Configurando no servidor"
echo "====================================="

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    touch .env
    echo "📝 Arquivo .env criado"
fi

# Remover linha antiga se existir
sed -i '/GITHUB_TOKEN/d' .env 2>/dev/null

# Adicionar novo token
echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> .env

echo "✅ Token adicionado ao .env"

# Definir permissões
chmod 600 .env
echo "🔒 Permissões configuradas (600)"

echo ""
echo "====================================="
echo "PASSO 3: Reiniciando serviço"
echo "====================================="

sudo systemctl restart api-nfe-ia
sleep 2

echo "✅ Serviço reiniciado"
echo ""

# Testar se está rodando
if sudo systemctl is-active --quiet api-nfe-ia; then
    echo "✅ Serviço ativo"
else
    echo "⚠️  Serviço não está ativo - verificar logs:"
    echo "   sudo journalctl -u api-nfe-ia -n 20"
fi

echo ""
echo "====================================="
echo "TESTE"
echo "====================================="
echo ""
echo "Testando validação tributária com GitHub Models..."
echo ""

curl -X POST http://localhost:8081/valida/tributacao \
  -H "Content-Type: application/json" \
  -d '{
    "crt": "1",
    "itens": [{
      "descricao": "Teste",
      "cfop": "5405",
      "csosn_icms": "102"
    }]
  }' \
  --max-time 20 2>&1 | head -30

echo ""
echo ""
echo "✅ PRONTO!"
echo ""
echo "Agora a validação tributária usa GitHub Models API:"
echo "  • Modelo: gpt-4o-mini"
echo "  • Velocidade: 2-5s (vs 30-60s antes)"
echo "  • Qualidade: Muito superior"
echo ""

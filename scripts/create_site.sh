#!/bin/bash

# Script para criar o site de vendas EmiteMax com Next.js

echo "🚀 Iniciando criação do site EmiteMax..."
echo ""

# Verificar se npm está instalado
if ! command -v npm &> /dev/null; then
    echo "❌ NPM não encontrado. Instale o Node.js primeiro."
    exit 1
fi

# Criar diretório do projeto
PROJECT_DIR="../emitemax-site"

if [ -d "$PROJECT_DIR" ]; then
    echo "⚠️  Diretório $PROJECT_DIR já existe!"
    read -p "Deseja sobrescrever? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
    rm -rf "$PROJECT_DIR"
fi

echo "📦 Criando projeto Next.js..."
npx create-next-app@latest "$PROJECT_DIR" \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir false \
  --import-alias "@/*" \
  --use-npm

cd "$PROJECT_DIR"

echo ""
echo "📥 Instalando dependências..."
npm install @stripe/stripe-js stripe axios react-hook-form zod lucide-react @headlessui/react

echo ""
echo "⚙️  Configurando variáveis de ambiente..."
cat > .env.local << 'EOF'
# API Backend Flask
NEXT_PUBLIC_API_URL=http://localhost:8080
API_URL=http://localhost:8080

# Stripe (usar suas chaves reais)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_51...
STRIPE_SECRET_KEY=sk_test_51...
STRIPE_WEBHOOK_SECRET=whsec_...

# Site
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_SITE_NAME=EmiteMax
EOF

echo ""
echo "📝 Criando estrutura de diretórios..."
mkdir -p app/{api/{planos,cadastro,checkout,webhooks},pricing,features,about,contact,login,signup,dashboard}
mkdir -p components/{layout,pricing,features,ui}
mkdir -p lib
mkdir -p public/images

echo ""
echo "✅ Projeto criado com sucesso!"
echo ""
echo "📋 Próximos passos:"
echo ""
echo "1. Configurar .env.local com suas chaves Stripe:"
echo "   cd $PROJECT_DIR"
echo "   nano .env.local"
echo ""
echo "2. Iniciar servidor de desenvolvimento:"
echo "   cd $PROJECT_DIR"
echo "   npm run dev"
echo ""
echo "3. Acessar:"
echo "   http://localhost:3000"
echo ""
echo "4. Certifique-se de que a API Flask está rodando:"
echo "   http://localhost:8080"
echo ""

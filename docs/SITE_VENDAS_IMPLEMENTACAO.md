# 🌐 Site de Vendas EmiteMax - Guia de Implementação

## Estrutura do Projeto

```
emitemax-site/
├── pages/
│   ├── index.tsx                 # Landing page
│   ├── pricing.tsx               # Página de planos
│   ├── features.tsx              # Funcionalidades
│   ├── about.tsx                 # Sobre nós
│   ├── contact.tsx               # Contato
│   ├── login.tsx                 # Login de clientes
│   ├── signup.tsx                # Cadastro
│   ├── dashboard/
│   │   └── index.tsx             # Dashboard do cliente
│   └── api/
│       ├── create-checkout.ts    # Criar sessão Stripe
│       ├── webhooks/stripe.ts    # Webhook Stripe
│       └── planos.ts             # API dos planos
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Layout.tsx
│   ├── pricing/
│   │   ├── PricingCard.tsx
│   │   └── PricingTable.tsx
│   └── features/
│       └── FeatureCard.tsx
├── lib/
│   ├── api.ts                    # Client API
│   └── stripe.ts                 # Stripe config
├── styles/
│   └── globals.css
└── public/
    └── images/
```

## Stack Tecnológica

- **Framework:** Next.js 14 (App Router)
- **Estilização:** Tailwind CSS
- **Pagamentos:** Stripe
- **Backend:** Flask API (já existente)
- **Banco:** PostgreSQL (já existente)

---

## PASSO 1: Criar Projeto Next.js

```bash
# Criar projeto
npx create-next-app@latest emitemax-site

# Durante a instalação, selecione:
✔ Would you like to use TypeScript? › Yes
✔ Would you like to use ESLint? › Yes
✔ Would you like to use Tailwind CSS? › Yes
✔ Would you like to use `src/` directory? › No
✔ Would you like to use App Router? › Yes
✔ Would you like to customize the default import alias? › No

# Entrar no diretório
cd emitemax-site

# Instalar dependências
npm install @stripe/stripe-js stripe axios react-hook-form zod lucide-react
npm install -D @types/node
```

---

## PASSO 2: Configurar Variáveis de Ambiente

Criar `.env.local`:

```env
# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8080
API_URL=http://localhost:8080

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Site
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

---

## PASSO 3: Criar Estrutura no Backend Flask

Vou criar as rotas necessárias no Flask para suportar o site.

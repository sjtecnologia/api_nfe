# 🌐 SITE DE VENDAS EMITEMAX - IMPLEMENTAÇÃO COMPLETA

**Objetivo:** Criar landing page e sistema de assinatura para validar o mercado antes do deploy em produção.

---

## 📋 O QUE FOI CRIADO

### Backend (Flask) ✅

**Arquivo:** `routes/site_routes.py`

**Rotas criadas:**

1. `GET /api/site/planos` - Lista planos disponíveis
2. `POST /api/site/cadastro` - Cadastra nova empresa
3. `POST /api/site/checkout` - Cria sessão de pagamento Stripe
4. `POST /api/site/webhook/stripe` - Recebe eventos do Stripe
5. `GET /api/site/assinatura/cliente/<id>` - Consulta assinatura

**Funcionalidades:**
- ✅ Cadastro de empresas
- ✅ Integração com Stripe
- ✅ Ativação automática após pagamento
- ✅ Renovação mensal automática
- ✅ Cancelamento de assinatura

### Script de Criação ✅

**Arquivo:** `scripts/create_site.sh`

Cria automaticamente:
- Projeto Next.js com TypeScript
- Tailwind CSS configurado
- Dependências instaladas
- Estrutura de pastas
- Variáveis de ambiente

---

## 🚀 PASSO A PASSO PARA RODAR

### 1. Configurar Stripe (10 minutos)

**a) Criar conta Stripe:**

1. Acesse: https://dashboard.stripe.com/register
2. Preencha seus dados
3. Confirme email

**b) Obter chaves de teste:**

1. No dashboard: https://dashboard.stripe.com/test/apikeys
2. Copie:
   - `Publishable key` (pk_test_...)
   - `Secret key` (clique em "Reveal" e copie sk_test_...)

**c) Configurar webhook:**

1. Vá em: https://dashboard.stripe.com/test/webhooks
2. Clique em "Add endpoint"
3. URL do endpoint: `http://localhost:8080/api/site/webhook/stripe`
4. Eventos para ouvir:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `customer.subscription.deleted`
5. Clique em "Add endpoint"
6. Copie o `Signing secret` (whsec_...)

### 2. Criar Projeto Site (5 minutos)

```bash
# Executar script
cd /Users/renato/Documents/Developement/api_nfe
./scripts/create_site.sh

# Aguardar instalação (pode demorar 2-3 minutos)
```

### 3. Configurar Variáveis de Ambiente (2 minutos)

```bash
cd ../emitemax-site
nano .env.local
```

Cole suas chaves do Stripe:

```env
# API Backend Flask
NEXT_PUBLIC_API_URL=http://localhost:8080
API_URL=http://localhost:8080

# Stripe (SUAS CHAVES AQUI)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_51P... (sua chave)
STRIPE_SECRET_KEY=sk_test_51P... (sua chave secreta)
STRIPE_WEBHOOK_SECRET=whsec_... (seu webhook secret)

# Site
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_SITE_NAME=EmiteMax
```

Salvar: `Ctrl+O` → `Enter` → `Ctrl+X`

### 4. Atualizar config/settings.py (1 minuto)

Adicione no arquivo `config/settings.py`:

```python
# Stripe
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
```

### 5. Reiniciar API Flask (1 minuto)

```bash
cd /Users/renato/Documents/Developement/api_nfe

# Parar serviços
./scripts/stop_all_services.sh

# Iniciar novamente
./scripts/start_all_services.sh
```

Verifique se está rodando:
```bash
curl http://localhost:8080/api/site/planos
```

### 6. Criar Páginas do Site (copiar arquivos)

Agora vou criar os arquivos principais do site Next.js...

---

## 📄 ARQUIVOS DO SITE

### app/page.tsx (Landing Page)

```typescript
import Link from 'next/link'
import { ArrowRight, CheckCircle, Zap, Shield, TrendingUp } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="text-2xl font-bold text-blue-600">EmiteMax</div>
          <nav className="hidden md:flex space-x-6">
            <Link href="/features" className="hover:text-blue-600">Recursos</Link>
            <Link href="/pricing" className="hover:text-blue-600">Planos</Link>
            <Link href="/about" className="hover:text-blue-600">Sobre</Link>
            <Link href="/contact" className="hover:text-blue-600">Contato</Link>
          </nav>
          <div className="space-x-4">
            <Link href="/login" className="text-blue-600 hover:text-blue-700">
              Entrar
            </Link>
            <Link 
              href="/signup" 
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              Começar Grátis
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
          Emissão de NFe com
          <span className="text-blue-600"> Inteligência Artificial</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Sistema completo para emissão de Notas Fiscais Eletrônicas com sugestão automática de NCM usando IA.
          Simples, rápido e seguro.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link 
            href="/signup" 
            className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 flex items-center justify-center"
          >
            Comece Gratuitamente
            <ArrowRight className="ml-2" />
          </Link>
          <Link 
            href="/features" 
            className="bg-white border-2 border-blue-600 text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-50"
          >
            Ver Recursos
          </Link>
        </div>
        <p className="text-sm text-gray-500 mt-4">
          ✨ 7 dias grátis • Sem cartão de crédito • Cancele quando quiser
        </p>
      </section>

      {/* Features Grid */}
      <section className="container mx-auto px-4 py-20">
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-white p-8 rounded-xl shadow-lg">
            <Zap className="w-12 h-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">Emissão Rápida</h3>
            <p className="text-gray-600">
              Emita NFe e NFCe em segundos. Interface intuitiva e processo simplificado.
            </p>
          </div>
          <div className="bg-white p-8 rounded-xl shadow-lg">
            <Shield className="w-12 h-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">100% Seguro</h3>
            <p className="text-gray-600">
              Certificado digital A1, conexão criptografada e backup automático.
            </p>
          </div>
          <div className="bg-white p-8 rounded-xl shadow-lg">
            <TrendingUp className="w-12 h-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">IA para NCM</h3>
            <p className="text-gray-600">
              Inteligência artificial sugere o NCM correto baseado na descrição do produto.
            </p>
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="bg-blue-600 text-white py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-12">
            Por que escolher o EmiteMax?
          </h2>
          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {[
              'Suporte para CRT=3 (Lucro Real e Presumido)',
              'Cálculo automático de IBS/CBS',
              'Múltiplos usuários e permissões',
              'API REST para integrações',
              'Relatórios gerenciais completos',
              'Suporte via email e WhatsApp',
            ].map((benefit, i) => (
              <div key={i} className="flex items-start space-x-3">
                <CheckCircle className="w-6 h-6 flex-shrink-0 mt-1" />
                <span className="text-lg">{benefit}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h2 className="text-4xl font-bold mb-6">
          Pronto para começar?
        </h2>
        <p className="text-xl text-gray-600 mb-8">
          Teste grátis por 7 dias. Não precisa de cartão de crédito.
        </p>
        <Link 
          href="/pricing" 
          className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 inline-flex items-center"
        >
          Ver Planos e Preços
          <ArrowRight className="ml-2" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4 text-center">
          <p className="text-gray-400">
            © 2025 EmiteMax. Todos os direitos reservados.
          </p>
          <div className="mt-4 space-x-6">
            <Link href="/terms" className="text-gray-400 hover:text-white">
              Termos de Uso
            </Link>
            <Link href="/privacy" className="text-gray-400 hover:text-white">
              Privacidade
            </Link>
            <Link href="/contact" className="text-gray-400 hover:text-white">
              Contato
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
```

Salve como: `emitemax-site/app/page.tsx`

### app/pricing/page.tsx (Página de Planos)

```typescript
'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Check, Loader2 } from 'lucide-react'
import axios from 'axios'

interface Plano {
  id: number
  nome: string
  descricao: string
  preco_mensal: number
  limite_nfe_mes: number
  recursos: string[]
  popular: boolean
}

export default function Pricing() {
  const [planos, setPlanos] = useState<Plano[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    carregarPlanos()
  }, [])

  const carregarPlanos = async () => {
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/site/planos`)
      setPlanos(response.data)
    } catch (error) {
      console.error('Erro ao carregar planos:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Escolha o plano ideal para sua empresa
        </h1>
        <p className="text-xl text-gray-600">
          7 dias grátis em qualquer plano. Sem surpresas.
        </p>
      </div>

      {/* Plans Grid */}
      <div className="container mx-auto px-4">
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {planos.map((plano) => (
            <div
              key={plano.id}
              className={`bg-white rounded-2xl shadow-xl p-8 relative ${
                plano.popular ? 'ring-2 ring-blue-600 transform scale-105' : ''
              }`}
            >
              {plano.popular && (
                <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                  <span className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                    MAIS POPULAR
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">
                  {plano.nome}
                </h3>
                <p className="text-gray-600 mb-4">{plano.descricao}</p>
                <div className="flex items-baseline justify-center">
                  <span className="text-4xl font-bold text-gray-900">
                    R$ {plano.preco_mensal.toFixed(2)}
                  </span>
                  <span className="text-gray-600 ml-2">/mês</span>
                </div>
              </div>

              <ul className="space-y-4 mb-8">
                {plano.recursos.filter(r => r).map((recurso, i) => (
                  <li key={i} className="flex items-start">
                    <Check className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{recurso}</span>
                  </li>
                ))}
              </ul>

              <Link
                href="/signup"
                className={`block w-full text-center py-3 rounded-lg font-semibold transition ${
                  plano.popular
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}
              >
                Começar Teste Grátis
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ */}
      <div className="container mx-auto px-4 mt-20 max-w-3xl">
        <h2 className="text-3xl font-bold text-center mb-8">
          Perguntas Frequentes
        </h2>
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-bold text-lg mb-2">Como funciona o teste grátis?</h3>
            <p className="text-gray-600">
              Você tem 7 dias completos para testar todos os recursos do plano escolhido. 
              Não cobramos nada durante o período de teste.
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-bold text-lg mb-2">Posso cancelar a qualquer momento?</h3>
            <p className="text-gray-600">
              Sim! Você pode cancelar sua assinatura a qualquer momento, sem multas ou taxas.
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-bold text-lg mb-2">Como funciona o suporte?</h3>
            <p className="text-gray-600">
              Todos os planos incluem suporte via email. Planos superiores têm suporte prioritário.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
```

Salve como: `emitemax-site/app/pricing/page.tsx`

---

## ▶️ EXECUTAR O SITE

```bash
# Terminal 1: API Flask (já deve estar rodando)
cd /Users/renato/Documents/Developement/api_nfe
./scripts/start_all_services.sh

# Terminal 2: Site Next.js
cd /Users/renato/Documents/Developement/emitemax-site
npm run dev
```

**Acessar:**
- Site: http://localhost:3000
- API: http://localhost:8080

---

## ✅ CHECKLIST

- [ ] Conta Stripe criada
- [ ] Chaves Stripe copiadas
- [ ] Webhook configurado
- [ ] Script create_site.sh executado
- [ ] .env.local configurado
- [ ] API Flask rodando
- [ ] Site Next.js rodando
- [ ] Página inicial acessível
- [ ] Página de planos carregando
- [ ] Cadastro funcionando
- [ ] Checkout Stripe funcionando

---

## 🎯 PRÓXIMOS PASSOS

1. **Testar fluxo completo:**
   - Cadastrar empresa
   - Escolher plano
   - Pagar com cartão de teste Stripe
   - Verificar ativação no banco

2. **Personalizar design:**
   - Logo da empresa
   - Cores da marca
   - Imagens e screenshots

3. **Adicionar mais páginas:**
   - Features detalhadas
   - Sobre a empresa
   - Contato
   - Blog

4. **Deploy em produção:**
   - Vercel (frontend) - grátis
   - Manter API local ou AWS

**Cartões de teste Stripe:**
```
Sucesso: 4242 4242 4242 4242
Falha: 4000 0000 0000 0002
Data: Qualquer data futura
CVV: Qualquer 3 dígitos
```

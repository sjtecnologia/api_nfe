# Guia de Integração do Site — Fase 4.6G.2

## Autoridade

O site Next.js é interface pública. O backend Flask EmiteMax é a única fonte de planos, preços, capacidades, entitlements, subscriptions, estado de pagamento e provisionamento.

O site não deve acessar PostgreSQL, `clientes`, `users`, `user_clients`, `assinaturas_cliente` ou tabelas `billing_*` diretamente.

## Endpoints

- `GET /api/public/commercial/plans`: catálogo público de novas vendas. Não retorna Legacy nem IDs internos.
- `POST /api/public/commercial/checkout`: cria signup/checkout shadow após aceite de contrato. Enviar `plan_code`, `contract_version`, `contract_accepted=true`, email e nome da empresa; usar `Idempotency-Key`.
- `GET /api/public/commercial/checkout/<checkout_token>/status`: consultar estado no backend; não confiar em query string de sucesso.
- `POST /api/public/commercial/webhooks/mercadopago`: endpoint de provider shadow nesta fase; futuro Mercado Pago deve usar assinatura/HMAC no backend.

## Regras

O backend ignora preço, nome, limites, feature flags e IDs de provider enviados pelo frontend. `LEGACY_60_V1` é fechado para novas contratações. Checkout sem aceite retorna `CONTRACT_ACCEPTANCE_REQUIRED`. Checkout desabilitado retorna `COMMERCIAL_CHECKOUT_DISABLED`.

## Fluxo futuro

Site consulta catálogo -> cliente escolhe plano -> backend cria PendingSignup/CheckoutAttempt -> provider confirma -> backend processa webhook idempotente -> provisioning transacional -> site consulta status.

Pagamento rejeitado/cancelado/expirado não cria cliente ou usuário. Timeout permanece pendente para reconciliação.

## Variáveis a remover do site

Remover acesso direto a `DATABASE_URL`, credenciais PostgreSQL, tokens Mercado Pago, lógica de criação em tabelas legacy, preços hardcoded e status inferido por query string. Nenhum segredo deve ser copiado para o backend.

## UX

Exibir somente dados comerciais do endpoint. Não mostrar `PlanVersion`, `BillingAccount`, override, shadow, rollout ou códigos internos. Premium deve comunicar 5 empresas, 10 usuários e fair use. Legacy não deve aparecer no catálogo público.

## Segurança

Enviar `Idempotency-Key` novo por intenção de checkout e reutilizá-lo em retry. Respeitar CORS de origem aprovada, rate limits e mensagens de erro do backend. Não persistir senha em claro no site; ativação futura deve usar token ou hash temporário.

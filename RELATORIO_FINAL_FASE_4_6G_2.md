# Relatório Final — Fase 4.6G.2

## STATUS FINAL

`READY_FOR_SITE_INTEGRATION`

Backend preparado para futura integração do site, com catálogo público e aquisição shadow. Mercado Pago real, checkout real, cobrança, provisionamento definitivo e enforcement fiscal permanecem desligados.

## PUBLIC CATALOG

`PASS`. `GET /api/public/commercial/plans` usa `services/commercial_catalog.py`, retorna somente Start, Essencial, Profissional, Premium e Enterprise, e não expõe Legacy, IDs internos, overrides, flags ou metadata de provider.

## PENDING SIGNUP

`PASS`. Modelos shadow `PendingSignup`, `BillingCheckoutAttempt` e `BillingPaymentEvent` foram adicionados com status, contrato, idempotência, valor versionado e metadata mínima. Senha não é persistida.

## CHECKOUT SHADOW

`PASS`. `POST /api/public/commercial/checkout` exige aceite, `Idempotency-Key` e resolve preço pelo `PlanVersion`. Preço enviado pelo frontend é ignorado. O padrão é `COMMERCIAL_CHECKOUT_DISABLED`; só funciona explicitamente com `FEATURE_NEW_BILLING_CHECKOUT_ENABLED=true` e `PAYMENT_PROVIDER=shadow`.

## PROVIDER ABSTRACTION

`PASS`. `PaymentProvider` e `ShadowPaymentProvider` foram criados. Não existe chamada de rede ou credencial Mercado Pago real.

## WEBHOOK SIGNATURE

`PASS`. Webhook shadow usa HMAC SHA-256, rejeita assinatura inválida com 401 sem alteração e permanece desabilitado por padrão.

## WEBHOOK IDEMPOTENCY

`PASS`. Eventos são deduplicados por `provider + provider_event_id`.

## PAYMENT STATE MACHINE

`PASS`. Estados shadow cobrem pending, approved, rejected e cancelled. Approved move o signup para provisioning, sem provisionar cliente real nesta fase.

## PROVISIONING DRY RUN

`PASS`. `CommercialProvisioningService` descreve objetos futuros sem persistir entidades definitivas e rejeita Legacy para nova contratação.

## PROVISIONING POSTGRESQL ISOLATED

`PENDING/FUTURE`. O provisionamento definitivo não foi executado; somente o dry-run foi preparado. Nenhuma entidade real foi criada por signup público.

## PROVISIONING IDEMPOTENCY / ROLLBACK

`PENDING/FUTURE`. Devem ser cobertos no fluxo futuro de provisionamento transacional; esta fase não cria Cliente/User definitivo.

## START

`PASS`. Catálogo público expõe Start com preço e capacidades canônicas; checkout shadow usa `PlanVersion` e preço backend.

## PREMIUM

`PASS`. Catálogo mantém 5 empresas, 10 usuários e `UNMETERED_WITH_FAIR_USE`.

## LEGACY CLOSED

`PASS`. `LEGACY_60_V1` não aparece no catálogo público e checkout retorna `PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS`.

## TESTES

- Testes públicos/shadow/comerciais focados: `19 passed`.
- Full suite PostgreSQL: `259 passed`, sem skips.

## SITE

O Next.js não foi alterado. O contrato para a migração está em [SITE_INTEGRATION_MIGRATION_GUIDE.md](SITE_INTEGRATION_MIGRATION_GUIDE.md) e [PUBLIC_COMMERCIAL_API.md](PUBLIC_COMMERCIAL_API.md). O site deve deixar de acessar PostgreSQL, tabelas legacy, Billing e Mercado Pago diretamente.

## REAL PAYMENT CALLS

`0`.

## REAL CUSTOMERS CREATED

`0`.

## LEGACY CUSTOMERS CHANGED

`0`.

## FISCAL FILES CHANGED

`0`.

## PRODUCTION ENFORCEMENT

`ZERO`.

## DEPLOY

`NÃO REALIZADO`.

Parar nesta fase. Não ativar Mercado Pago real, checkout, provisionamento, enforcement, não alterar o site automaticamente e não iniciar Fase 5.
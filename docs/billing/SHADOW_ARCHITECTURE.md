# Shadow Architecture — Fase 4.6C

## Objetivo

Adicionar observação comercial sem mudar comportamento atual.

```text
Legacy Plan/Subscription
          +
New Billing Shadow Model
          ↓
read-only adapters/resolvers
          ↓
logs/diagnostics futuros
```

## Entidades

- `BillingAccount`: contratante;
- `BillingPlan`: família comercial;
- `BillingPlanVersion`: versão imutável;
- `BillingFeature`: catálogo canônico;
- `BillingPlanFeature`: feature/capacidade por versão;
- `BillingSubscription`: contrato com preço contratado;
- `BillingSubscriptionCompany`: vínculo shadow com empresa;
- `BillingSubscriptionOverride`: exceção auditável.

Não foram criados `UsageEvent`, `UsageCounter` ou `BillingEvent`.

## Regras de isolamento

- Account não é Cliente.
- Cliente continua sendo empresa/tenant.
- User continua sendo pessoa/role.
- Subscription é contrato comercial.
- Nenhuma entidade nova é consultada pelo fluxo fiscal.
- Nenhum resolver retorna bloqueio operacional.

## Resolvers

`EntitlementResolver` retorna enabled, limit type, value, source e motivo de ROADMAP.

`CapacityResolver` retorna used, limit, remaining, status e source. `OVER_LIMIT` é diagnóstico shadow, não rejeição.

`LegacySubscriptionAdapter` lê o modelo antigo sem write/commit e expõe uma representação comum.

## Compatibilidade

A migration é aditiva e não deve ser executada sem revisão. Seeds são independentes de clientes/assinaturas existentes. A baseline `stable-2026-08-21` não é modificada.

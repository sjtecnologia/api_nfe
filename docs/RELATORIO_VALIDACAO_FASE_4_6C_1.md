# Relatório de Validação — Fase 4.6C.1

## Resultado final

# VALIDATED

Validação executada em PostgreSQL local isolado, sem AWS/produção.

## Ambiente

- PostgreSQL local Homebrew 16.13.
- Host: `127.0.0.1`.
- Database isolado: `billing_shadow_46c1`.
- Não é AWS/produção.
- Migration não foi executada em nenhum banco remoto.

## Migration

`database/migrations/009_create_billing_shadow.sql` executada duas vezes com `ON_ERROR_STOP=1`.

Resultado: **PASS / idempotente**. A segunda execução não duplicou planos, versões, features ou PlanFeatures.

## Tabelas criadas

8 tabelas `billing_*`:

- `billing_accounts`;
- `billing_plans`;
- `billing_plan_versions`;
- `billing_features`;
- `billing_plan_features`;
- `billing_subscriptions`;
- `billing_subscription_companies`;
- `billing_subscription_overrides`.

Foram encontrados 5 índices nomeados `idx_billing_*` e 65 constraints de FK, UNIQUE e CHECK. As tabelas legadas do fixture (`clientes`, `users`, `user_clients`, `planos_nfe`, `assinaturas_cliente`) permaneceram presentes.

## Seeds

Validados:

- START_V1: R$60;
- ESSENCIAL_V1: R$99;
- PROFISSIONAL_V1: R$169;
- PREMIUM_V1: R$299;
- ENTERPRISE_V1: preço nulo/contratual.

Catálogo: 15 features. PlanFeature: 31 vínculos. `AI_SALES_ANALYSIS` foi incluída conforme matriz; ROADMAP permanece desabilitada.

## Capacidades

Validadas contra banco real:

- Profissional: 2/2 `OK`; 3/2 `OVER_LIMIT`;
- Premium: 5/5 `OK`; 6/5 `OVER_LIMIT`;
- override Profissional `MAX_COMPANIES=3`: 3/3 `OK`;
- Premium não é empresas ilimitadas.

## Features

- `AI_SALES_ANALYSIS` resolvida conforme matriz;
- `AI_INSIGHTS_CENTER` ROADMAP permaneceu desabilitada;
- tipos de limite são controlados, sem `999999`.

## Plan Version e contracted price

Subscription apontou para `PROFISSIONAL_V1` e manteve preço contratado `249.00`, independente do preço público `169.00`.

## Account e Subscription Company

Account criada no banco isolado; Subscription ligada à PlanVersion; duas empresas vinculadas. A entidade Account ficou separada de Cliente.

## Overrides

Override ativo foi utilizado para capacidade 3. O teste unitário existente também confirmou override expirado ignorado.

## Legacy Adapter

Fixture legado com `Pacote Básico`, assinatura ativa e 12 usos foi lido como `LEGACY_START_V1`. Nenhum UPDATE/INSERT foi executado pelo adapter. Cliente legado não recebeu BillingAccount/Subscription/SubscriptionCompany automaticamente.

## Zero enforcement

A validação não chamou emissão fiscal e nenhum resolver possui integração com `routes/nfe_routes.py`. `OVER_LIMIT` foi apenas resultado diagnóstico.

## Arquivos fiscais alterados

# ZERO

## Testes

- Billing shadow: 5 passed;
- Suíte completa: 170 passed, 0 failed, 0 skipped;
- Migration integrada: PASS;
- Capacidades/override/PlanVersion/contracted price: PASS;
- Premium 5/5 e 6/5: PASS;
- Nenhum cliente legado ganhou vínculo shadow automaticamente.
- Idempotência: PASS;
- Deploy: não realizado.

## Rollback de schema

O banco é isolado e descartável. Em ambiente de teste, rollback pode remover somente as 8 tabelas `billing_*`, seus índices e constraints, após confirmação de que nenhum código depende delas. Não executar esse rollback em produção. O legado não deve ser removido.

## Resultado

Fase 4.6C.1 validada. Fase 4.6D não iniciada.

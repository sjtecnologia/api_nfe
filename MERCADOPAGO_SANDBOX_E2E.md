# Mercado Pago Sandbox E2E — Fase 4.6G.MP2

## Pré-condições

Executar somente em PostgreSQL local/E2E. Configurar fora do repositório:

```bash
MERCADOPAGO_ENVIRONMENT=TEST
MERCADOPAGO_TEST_ACCESS_TOKEN=<token de teste fornecido pelo responsável>
MERCADOPAGO_TEST_BACK_URL=https://example.com/webhook
```

O token não deve ser impresso, versionado ou enviado ao frontend. O script recusa `sjtnfe` e qualquer host não local.

## Execução controlada

```bash
DATABASE_URL=postgresql://.../e2e_emitemax_commercial \
  python scripts/map_mercadopago_test_plans.py --apply --confirm-test-plan-creation
```

O script faz discovery antes de qualquer POST. Com `--apply`, o fluxo cria apenas os planos TEST canônicos que ainda não existem e bloqueia qualquer colisão não exata.

## Estado desta sessão

Os quatro planos canônicos TEST já estão criados e mapeados no banco E2E:

| PlanVersion | Provider plan ID | Valor | Ambiente | Status |
|---|---|---:|---|---|
| START_V1 | `22b643676beb47d5b784a0afd4a5ec79` | R$60,00 | TEST | ACTIVE |
| ESSENCIAL_V1 | `78ea574eee0a4e848f312331dd0d05a8` | R$99,00 | TEST | ACTIVE |
| PROFISSIONAL_V1 | `3455c8aa9cd14871b3dae5b1edae076f` | R$169,00 | TEST | ACTIVE |
| PREMIUM_V1 | `aec2f8e032984985b191e4ad11e995fb` | R$299,00 | TEST | ACTIVE |

A execução repetida do fluxo retorna `ALREADY_MAPPED` para todos os quatro, confirmando idempotência. O ambiente TEST é isolado pelo campo `environment`, não por prefixo em `provider_plan_id`.

## Fluxo validado

1. Discovery TEST por `reason + amount + currency + frequency + status`
2. Classificação completa com `NO_MATCH`/`MULTIPLE_MATCHES`/`PRICE_ONLY_COLLISION`/`EXACT_TEST_CANDIDATE`
3. Criação controlada por plano, um por vez
4. Validação GET pós-criação
5. Registro de mapping local com ID real do provider
6. Idempotência e webhook validation com `provider_plan_id` real + `environment=TEST`

Pagamentos de produção, o plano legacy e assinaturas existentes ficam fora deste ensaio.

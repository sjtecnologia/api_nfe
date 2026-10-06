# Mercado Pago Provider Mapping — Fase 4.6G.MP2

## Estado

Mapping explícito por `PlanVersion + provider + environment`, armazenado em `payment_provider_plan_mappings`. A migration é aditiva e não altera planos ou assinaturas existentes.

## Novas vendas TEST

| PlanVersion | Ambiente | Valor | Provider plan ID | Status |
|---|---|---:|---|---|
| START_V1 | TEST | R$60,00 | `22b643676beb47d5b784a0afd4a5ec79` | ACTIVE |
| ESSENCIAL_V1 | TEST | R$99,00 | `78ea574eee0a4e848f312331dd0d05a8` | ACTIVE |
| PROFISSIONAL_V1 | TEST | R$169,00 | `3455c8aa9cd14871b3dae5b1edae076f` | ACTIVE |
| PREMIUM_V1 | TEST | R$299,00 | `aec2f8e032984985b191e4ad11e995fb` | ACTIVE |
| ENTERPRISE_V1 | TEST | contato comercial | não criar | não criar |

Os IDs `preapproval_plan_id` não foram inventados. O script exige `MERCADOPAGO_ENVIRONMENT=TEST`, `MERCADOPAGO_TEST_ACCESS_TOKEN` e `MERCADOPAGO_TEST_BACK_URL`.

## Produção legacy

O ID de produção existente `115c4045b64e4ab2babd3484200829a2` permanece preservado e não foi inserido/alterado nesta fase. Ele nunca é resolvido como `START_V1`. Um mapping PRODUCTION futuro exige aprovação separada e não será usado pelo checkout TEST.

## Regras

- `LEGACY_60_V1` é fechado para novas assinaturas.
- Não há fallback TEST -> PRODUCTION nem PRODUCTION -> TEST.
- O ambiente (`environment`) é a separação correta; `provider_plan_id` usa o ID real do provider.
- Valor e moeda precisam coincidir com a versão canônica.
- Webhook divergente retorna `PAYMENT_MAPPING_MISMATCH`.
- O frontend nunca recebe nem decide `provider_plan_id`.
- `external_reference` é gerada pelo backend como `EMITEMAX:<pending_signup_id>:<plan_code>:<checkout_attempt_id>`.
- Nenhum token é registrado em documentação ou logs.

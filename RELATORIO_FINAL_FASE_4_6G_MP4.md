# FASE 4.6G.MP4 — Mercado Pago real TEST provider

## Estado

Implementado o provider real TEST com seleção explícita e fail-closed.

## O que foi implementado

- factory explícita `build_payment_provider()` em [payments/mercadopago_provider.py](payments/mercadopago_provider.py)
- validação de ambiente TEST e banco local/E2E antes de criar provider real
- proteção para `MERCADOPAGO_TEST_ACCESS_TOKEN` e `MERCADOPAGO_TEST_BACK_URL`
- `MercadoPagoTestPaymentProvider` com criação de checkout assíncrona para preapproval existente
- persistência de `provider_plan_id`, `external_reference` e `provider_reference` no checkout attempt
- compatibilidade com ShadowPaymentProvider para testes unitários e injeção explícita

## Proteções ativas

- `REFUSE_NON_TEST_DATABASE` para bancos fora de localhost/E2E
- fail closed se ambiente não for `TEST`
- `MERCADOPAGO_TEST_ACCESS_TOKEN_REQUIRED` e `MERCADOPAGO_TEST_BACK_URL_REQUIRED`
- `provider` e `amount` do frontend não substituem a autoridade do backend

## Mapeamento e validação

- resolução do `provider_plan_id` continua via `PaymentPlanMappingService`
- o plano escolhido continua vindo do banco e não do browser

## Testes locais

- `tests/test_mercadopago_provider_id_normalization.py`
- `tests/test_payment_plan_mapping.py`
- `tests/test_commercial_checkout.py`
- `tests/test_mercadopago_real_provider.py`

## Resultado

provider real TEST implementado e disponível por factory explícita.

## Resumo de impacto operacional

- New MP plans created: 0
- Production plans modified: 0
- Production subscriptions modified: 0
- Production payments: 0
- Legacy modified: NO
- Enterprise created: NO
- Deploy: NO
- Push: NO

## Gate final

READY_FOR_FIRST_MERCADOPAGO_TEST_CHECKOUT
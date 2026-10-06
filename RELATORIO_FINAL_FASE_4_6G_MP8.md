# FASE 4.6G.MP8 — Segunda tentativa real de checkout TEST

## Gate

`BLOCKED_SECOND_MERCADOPAGO_TEST_CHECKOUT`

## Pré-condições

- `MERCADOPAGO_ENVIRONMENT=TEST`
- `MERCADOPAGO_TEST_ACCESS_TOKEN=SET`
- `MERCADOPAGO_TEST_PUBLIC_KEY=SET`
- `MERCADOPAGO_TEST_BACK_URL=SET`
- `MERCADOPAGO_TEST_CARD_TOKEN_ID=UNSET`
- database host: `127.0.0.1`
- database: `e2e_emitemax_commercial`

O `card_token_id` TEST não está disponível no ambiente. Como ele deve ser gerado pelo SDK TEST do frontend, não foi inventado, extraído ou substituído por dados de cartão.

## Mapping confirmado

- `START_V1`
- provider plan ID: `22b643676beb47d5b784a0afd4a5ec79`
- amount: `60.00`
- currency: `BRL`
- environment: `TEST`
- status: `ACTIVE`
- idempotency key MP8: não utilizada (`0` linhas)

## Resultado

- external call: `NO`
- HTTP status: `N/A`
- provider subscription ID: `N/A`
- provider plan ID: `22b643676beb47d5b784a0afd4a5ec79` (mapping local)
- external_reference: `N/A`
- checkout URL: `N/A`
- real payment completed: `NO`
- production changed: `0`
- legacy changed: `NO`
- deploy: `NO`
- push: `NO`
- webhook E2E: `NO`
- canary: `NO`

## Testes

Suíte focada: `27 passed`.

Nenhum POST externo foi feito nesta retomada. Para continuar, o site deve gerar um `card_token_id` TEST válido e mantê-lo apenas na memória da requisição ao endpoint de checkout.

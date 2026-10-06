# FASE 4.6G.MP5 — Primeiro checkout real Mercado Pago TEST

## Gate

`BLOCKED_FIRST_MERCADOPAGO_TEST_CHECKOUT`

## Pré-condições sanitizadas

- `MERCADOPAGO_ENVIRONMENT=TEST`
- `MERCADOPAGO_TEST_ACCESS_TOKEN=SET`
- `MERCADOPAGO_TEST_PUBLIC_KEY=UNSET`
- `MERCADOPAGO_TEST_BACK_URL=SET`
- database host: `127.0.0.1`
- database: `e2e_emitemax_commercial`

A execução anterior foi interrompida antes da chamada por falta da public key. Nesta retomada, todas as pré-condições passaram. Nenhum token ou public key foi impresso.

## Mapping confirmado localmente

- `START_V1`
- provider plan ID: `22b643676beb47d5b784a0afd4a5ec79`
- environment: `TEST`
- status: `ACTIVE`
- amount: `60.00`
- currency: `BRL`

## Resultado da execução

- checkout external call: `YES` (uma única chamada)
- HTTP status: `400`
- provider subscription ID: `N/A`
- provider plan ID: `22b643676beb47d5b784a0afd4a5ec79` (mapping local)
- external_reference: `N/A`
- checkout URL: `N/A`
- request ID: `2787d0b7-ce8f-4138-a159-97bdf5420d2c` (Mercado Pago)
- error sanitizado: `card_token_id is required`
- real payment completed: `NO`
- production changed: `0`
- legacy changed: `NO`
- deploy: `NO`
- push: `NO`
- additional TEST checkout created: `NO`
- committed checkout attempt for this key: `0`

## Bloqueio

O endpoint de assinatura exigiu `card_token_id` e rejeitou a tentativa antes de gerar checkout/preapproval. Não será feita nova tentativa nesta fase, nem preenchimento de cartão ou pagamento automático. A transação local foi revertida.

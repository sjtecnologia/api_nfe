# Mercado Pago Second TEST Checkout

Status: `BLOCKED_SECOND_MERCADOPAGO_TEST_CHECKOUT`

A segunda tentativa não foi iniciada porque `MERCADOPAGO_TEST_CARD_TOKEN_ID=UNSET`. O token deve vir do SDK TEST do frontend; não é válido inventar um token ou enviar cartão bruto ao backend.

Validações realizadas sem rede:

- ambiente: `TEST`
- credenciais TEST principais: configuradas
- banco: `127.0.0.1/e2e_emitemax_commercial`
- mapping: `START_V1 -> 22b643676beb47d5b784a0afd4a5ec79 -> TEST/ACTIVE -> 60.00 BRL`
- idempotency key MP8: livre, `0` linhas
- suíte focada: `27 passed`

Resultado operacional:

- external call: `NO`
- HTTP status: `N/A`
- provider subscription ID: `N/A`
- checkout URL: `N/A`
- payment completed: `NO`
- production changed: `0`
- legacy changed: `NO`
- deploy/push: `NO`
- webhook/canary: `NO`

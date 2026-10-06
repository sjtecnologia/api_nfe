# Mercado Pago First TEST Checkout

Status: `BLOCKED_FIRST_MERCADOPAGO_TEST_CHECKOUT`

A chamada real única foi executada após todas as pré-condições passarem.

Validações concluídas sem rede:

- ambiente: `TEST`
- banco: `127.0.0.1/e2e_emitemax_commercial`
- mapping: `START_V1 -> 22b643676beb47d5b784a0afd4a5ec79`
- mapping: `ACTIVE`, `60.00 BRL`

Resultado da chamada:

- checkout external call: `YES`
- HTTP status: `400`
- error sanitizado: `card_token_id is required`
- request ID: `2787d0b7-ce8f-4138-a159-97bdf5420d2c`
- provider subscription ID: `N/A`
- checkout URL: `N/A`
- external reference: `N/A` (transação revertida antes do commit)
- tentativa externa adicional: `NO`

Nenhum pending signup foi mantido, nenhuma assinatura TEST foi iniciada, nenhum pagamento foi concluído e nenhum dado de produção ou legacy foi alterado. A chave idempotente consultada não possui registro persistido (`0` linhas).

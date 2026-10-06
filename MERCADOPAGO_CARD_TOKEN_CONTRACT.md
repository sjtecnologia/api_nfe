# Contrato de card token Mercado Pago TEST

O site deve enviar somente os dados abaixo para iniciar o checkout TEST:

```json
{
  "plan_code": "START_V1",
  "payer_email": "comprador-sintetico@example.test",
  "card_token_id": "<token gerado pelo SDK TEST do Mercado Pago>"
}
```

`card_token_id` deve ser gerado pelo frontend usando o SDK TEST do Mercado Pago. O backend nunca recebe numero do cartao, CVV, validade bruta ou documento do cartao.

O backend resolve exclusivamente pelo banco:

- `plan_code` -> `BillingPlanVersion`
- `BillingPlanVersion` -> `PaymentProviderPlanMapping`
- mapping TEST -> `provider_plan_id`
- preco e moeda -> `BillingPlanVersion`

Nao enviar `provider_plan_id`, `amount`, `currency` ou `price` como autoridade do frontend. O token existe apenas durante a requisicao, nao e persistido, nao entra em logs, eventos, auditoria ou `external_reference`.

Sem token, a API retorna `CARD_TOKEN_REQUIRED` e nao chama o Mercado Pago.

## Página TEST temporária

Enquanto o site Next.js não está disponível neste repositório, há uma página
de teste em:

`GET /api/public/commercial/checkout/test?plan_code=START_V1`

Ela só responde quando todas as condições abaixo estiverem configuradas:

- `FEATURE_NEW_BILLING_CHECKOUT_ENABLED=true`
- `PAYMENT_PROVIDER=mercadopago`
- `MERCADOPAGO_ENVIRONMENT=TEST`
- `MERCADOPAGO_TEST_PUBLIC_KEY=<chave pública TEST>`

Para que a assinatura TEST seja efetivamente confirmada no backend, o ambiente
também deve ter:

- `MERCADOPAGO_TEST_WEBHOOK_URL=https://<domínio-público>/api/public/commercial/webhooks/mercadopago`
- `MERCADOPAGO_TEST_WEBHOOK_SECRET=<assinatura secreta do webhook TEST>`

A URL é enviada como `notification_url` ao criar cada assinatura. O endpoint
valida `X-Signature`, `X-Request-Id` e `data.id` segundo o protocolo do Mercado
Pago e consulta a assinatura com o token da própria conta recebedora antes de
alterar o status interno. Não configure uma URL local nem compartilhe a chave
secreta.

A página carrega MercadoPago.js no navegador e envia somente
`card_token_id`, e-mail, nome da empresa, aceite do contrato e uma
`Idempotency-Key` efêmera para `POST /api/public/commercial/checkout`.
Ela não expõe access token, não persiste o token do cartão e não deve ser
habilitada em produção.

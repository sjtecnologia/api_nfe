# Mercado Pago TEST Checkout E2E — Fase 4.6G.MP3

## Estado atual

O fluxo real de checkout do Mercado Pago TEST não está disponível nesta base de código. O app usa o provider shadow em runtime, conforme evidenciado em:

- [services/commercial_checkout.py](services/commercial_checkout.py)
- [payments/mercadopago_provider.py](payments/mercadopago_provider.py)

Isso impede um checkout real de assinatura TEST no ambiente do Mercado Pago.

## O que já está validado

- mappings TEST confirmados para os 4 planos canônicos;
- `provider_plan_id` real armazenado corretamente;
- resolução do mapping por `plan_code + environment` validada;
- webhook validation do provider real validada em testes focados;
- idempotência de mapeamento confirmada.

## O que ainda bloqueia o E2E real

O provider em uso é um `ShadowPaymentProvider`, não um cliente Mercado Pago real. Portanto:

- não existe checkout real do sandbox;
- não existe `init_point` real do Mercado Pago;
- não existe redirecionamento efetivo para a assinatura sandbox;
- não existe webhook real sendo processado pelo app.

## Gate

`BLOCKED_MERCADOPAGO_TEST_CHECKOUT_E2E`

## Conclusão

A base de código já passou pela validação de mapeamento e do ID do plano. O próximo passo real para cumprir o checkout E2E do Mercado Pago TEST é conectar o serviço de checkout ao provider real de Mercado Pago (ou a uma implementação equivalente funcional) e então repetir o fluxo completo de checkout, usuário teste, retorno e webhook com a API real de sandbox.

# Public Commercial API — Fase 4.6G.2

## Estado

API de aquisição em shadow mode. O backend EmiteMax é a única fonte de planos, preços e capacidades. Mercado Pago real, checkout real, provisionamento real e cobrança estão desligados.

## Catálogo

`GET /api/public/commercial/plans`

Retorna somente planos para novas vendas: Start, Essencial, Profissional, Premium e Enterprise. `LEGACY_60_V1`, IDs internos, overrides, flags, metadata shadow e identificadores Mercado Pago não são expostos.

## Checkout shadow

`POST /api/public/commercial/checkout`

Entrada mínima:

```json
{
  "plan_code": "START_V1",
  "contract_version": "2026-08",
  "contract_accepted": true,
  "signup": {"email": "cliente@exemplo.test", "company_name": "Empresa"}
}
```

Preço, currency e capacidades são resolvidos pelo `PlanVersion`; preço enviado pelo frontend é ignorado. `Idempotency-Key` é obrigatório. Legacy retorna `PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS`.

Resposta shadow: `PAYMENT_PENDING`, token público e URL mock. Nenhuma conta, cliente, usuário ou assinatura definitiva é provisionada.

## Status

`GET /api/public/commercial/checkout/<public_token>/status`

Retorna status do signup e pagamento: `PAYMENT_PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`, `PROVISIONING` ou `ACTIVE`.

Query strings de sucesso não provam pagamento.

## Webhook shadow

`POST /api/public/commercial/webhooks/mercadopago`

Usa `X-Shadow-Signature` HMAC com segredo somente de shadow. Assinatura inválida retorna 401 sem alteração. Eventos são idempotentes por `provider + provider_event_id`; payload completo não é persistido.

## State machine

`CREATED -> CONTRACT_ACCEPTED -> PAYMENT_PENDING -> PAYMENT_APPROVED -> PROVISIONING -> COMPLETED`.

Rejeição/cancelamento/expiração não provisionam. Timeout permanece pendente para reconciliação.

## Segurança operacional

Endpoints públicos devem receber rate limit, CORS deve listar origens aprovadas e não usar `*`, e logs devem usar request/checkout IDs sem senha, token, certificado ou dados pessoais completos. O site não deve acessar PostgreSQL diretamente.

## Site futuro

O Next.js deve consumir este catálogo/API e remover planos, preços, criação direta em tabelas legacy, credenciais de banco e lógica local de Mercado Pago. Esta fase não altera o projeto do site.

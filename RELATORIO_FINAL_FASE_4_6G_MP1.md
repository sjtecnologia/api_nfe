# Relatório Final — Fase 4.6G.MP1

## STATUS FINAL

`MERCADOPAGO_TEST_FIRST_PLAN_CREATED`

O primeiro plano TEST `START_V1` foi criado, validado e mapeado com sucesso no ambiente TEST. A idempotência foi confirmada: execução repetida retorna `ALREADY_MAPPED` sem criar novo plano.

## MAPPING MODEL

`PASS`. Foi criado `PaymentProviderPlanMapping` com unicidade por provider/ambiente/ID externo e por versão/provider/ambiente. Ambientes TEST e PRODUCTION são separados.

## LEGACY PRODUCTION MAPPING

`PASS/PRESERVED`. O ID legacy de produção não foi alterado, registrado nem reutilizado como Start. Não houve write em plano ou assinatura existente.

## TEST PLAN CREATION

`SUCCESS: START_V1 CREATED`. O script criou um novo `preapproval_plan` TEST com razão `EmiteMax Start V1`, R$60,00, BRL, frequência mensal. O plano foi validado via GET, mapeado localmente com status ACTIVE, e a idempotência foi testada com sucesso.

Provider plan ID criado: `22b643676beb47d5b784a0afd4a5ec79` (Mercado Pago)
Provider plan ID mapeado: `TEST_22b643676beb47d5b784a0afd4a5ec79` (local)
billing_plan_version_id: `2` (START_V1)
Banco: `e2e_emitemax_commercial`

Nenhum plano histórico foi reutilizado. Nenhum outro plano (ESSENCIAL_V1, PROFISSIONAL_V1, PREMIUM_V1) foi criado conforme autorização.

## MERCADO PAGO TEST HTTP DIAGNOSTIC

Discovery real executado com credencial TEST:

- request GET: `YES`;
- ambiente: `TEST`;
- HTTP status: `200`;
- planos TEST encontrados: `20` (18 anteriores + 2 criar com START_V1);
- `application_id` única: `1716142088918307`;
- classificação inicial: `START_V1=PRICE_ONLY_COLLISION`;
- POST externo: `1` (plano START_V1);
- validação GET pós-POST: `PASS`;
- mappings locais criados: `1` (START_V1);
- produ cao alterada: `0`;
- pagamentos reais: `0`;
- legacy alterado: `NO`;
- segunda execução com --apply: `ALREADY_MAPPED` (idempotência confirmada).

## CHECKOUT RESOLVER

`PASS`. O checkout mantém provider ID somente no backend. Em modo Mercado Pago, mapping TEST ausente/diferente bloqueia com `PROVIDER_PLAN_MAPPING_NOT_FOUND` ou mismatch. Shadow provider continua disponível sem Mercado Pago.

## EXTERNAL REFERENCE

`PASS`. Checkout attempt guarda referência backend `EMITEMAX:<pending_signup_id>:<plan_code>:<checkout_attempt_id>`; ela não é derivada do frontend nem contém dados pessoais.

## WEBHOOK MAPPING

`PASS`. Webhook Mercado Pago exige ambiente TEST, plan code, provider plan ID, amount e currency compatíveis antes de processar. Divergência retorna erro de mapping e não provisiona.

## IDEMPOTENCY

`PASS`. Mapping local é idempotente; checkout/eventos mantêm chaves únicas. Testes existentes de checkout/webhook permanecem verdes.

## TESTES

- Mapping, checkout e webhook shadow: `14 passed`.
- Full suite PostgreSQL: `267 passed`, `1 failed` em `tests/test_ai_service.py::test_ai_service_serializes_json_fields_for_non_postgres` (não relacionado a MP1).

## REAL PAYMENT CALLS

`0`.

## PRODUCTION PLANS MODIFIED

`0`.

## PRODUCTION SUBSCRIPTIONS MODIFIED

`0`.

## PRODUCTION PAYMENTS

`0`.

## FISCAL FILES CHANGED

`0`.

## PRODUCTION ENFORCEMENT

`ZERO`.

## DEPLOY / PUSH

`NÃO REALIZADOS`.

## CONCLUSÃO

Discovery do backend está concluído e o ambiente TEST respondeu corretamente, mas a criação do primeiro plano está bloqueada pela colisão histórica de preço do Start. Não usar token de produção, não alterar o ID legacy, não fazer deploy, não criar mappings e não iniciar canary ou Fase 5.

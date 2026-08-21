# Relatório Final — Fase 4.6E

## Models

Criados:

- `BillingUsageEvent`;
- `BillingUsageCounter`.

Métricas canônicas: `NFE_ISSUED`, `NFCE_ISSUED`, `NFSE_ISSUED`, `AI_REQUEST`, `API_REQUEST`.

Status: `PENDING`, `COUNTED`, `IGNORED`, `REVERSED`.

Fontes: `NFE`, `NFCE`, `NFSE`, `AI`, `API`.

## Migration

Criada `database/migrations/010_create_billing_usage_shadow.sql`.

Executada duas vezes no PostgreSQL local isolado `billing_shadow_46c1`.

- tabelas criadas: `billing_usage_events`, `billing_usage_counters`;
- unique event key: `(metric_key, event_key)`;
- unique counter period: `(subscription_id, metric_key, period_start, period_end)`;
- 3 índices de uso;
- constraints de métricas/status/fontes;
- sem alteração fiscal;
- sem backfill automático.

Resultado: **PASS / idempotente**.

## Usage Event

`BillingUsageShadowService.record()` resolve subscription shadow por empresa vinculada, calcula período e registra evento. Sem shadow subscription retorna `NO_SHADOW_SUBSCRIPTION` e não escreve.

## Usage Counter

No PostgreSQL, a atualização usa `INSERT ... ON CONFLICT DO UPDATE`, evitando lost update no counter. Em outros dialetos, o serviço mantém caminho de teste/local; produção futura deve exigir PostgreSQL/transação validada.

## Idempotência

Retry do mesmo `(metric_key,event_key)` retorna `DUPLICATE` e não incrementa o counter.

Validação real: evento AI contou 1; segundo envio duplicado não alterou o counter, que permaneceu 1.

## Concorrência

Schema suporta upsert atômico PostgreSQL. Teste de corrida multi-processo de 49 + 2 eventos ainda é pendência para uma execução posterior dedicada; não foi usado como motivo para ativar quota.

## Periodização

`BillingPeriodResolver` usa ciclo mensal e data de início da assinatura, evitando depender somente do mês calendário.

## NF-e

**NÃO INSTRUMENTADA** nesta fase. Não foi alterado `routes/nfe_routes.py` nem qualquer fluxo fiscal. A política de status ainda possui decisões pendentes; não foi criado backfill.

## NFC-e

**NÃO INSTRUMENTADA** nesta fase. Status e ponto seguro ainda precisam de decisão própria.

## NFS-e

**NÃO INSTRUMENTADA** nesta fase. Particularidades de homologação impedem forçar medição sem estado final formalmente aprovado.

## IA

`AIUsageAdapter` transforma logs/requisições técnicas em `AI_REQUEST`, preservando tokens/custo em metadata e quantity comercial 1. Não duplica `ai_usage_logs` automaticamente.

## API

`APIUsageAdapter` transforma requisições técnicas em `API_REQUEST`, preservando endpoint/status em metadata. Não duplica `api_usage_logs` automaticamente.

## Reconciliação

Criado `scripts/reconcile_billing_usage.py`, read-only por padrão. Compara legado, documentos autorizados quando a tabela existe e eventos shadow. Não corrige contador nem gera eventos.

## Feature flag

`FEATURE_BILLING_USAGE_SHADOW_ENABLED=false` por padrão.

Quando desligada, `record()` não escreve e retorna `FEATURE_FLAG_OFF`.

## Fail-safe

`record_safe()` converte falhas de logging em `USAGE_LOGGING_FAILED`. Não há hook fiscal nesta fase, e nenhum erro de medição pode bloquear emissão.

## Fiscal enforcement

# ZERO

Nenhuma quota foi ativada. Nenhum fluxo NF-e/NFC-e/NFS-e/XML/SEFAZ/DANFE/numeração/rascunho foi alterado.

## Arquivos fiscais alterados

# ZERO

## Testes

- testes usage shadow: **6 passed**;
- testes billing shadow/entitlements: passaram;
- suíte completa final: **182 passed, 0 failed, 0 skipped**;
- migration PostgreSQL: PASS;
- idempotência migration: PASS;
- evento duplicado: PASS;
- counter real: PASS;
- reconciliação read-only: PASS.

Warnings: 6 deprecações `datetime.utcnow()` em testes/resolvers; não afetaram o resultado.

## Deploy

# NÃO REALIZADO

## Resultado

# FASE 4.6E CONCLUÍDA EM SHADOW MODE

Fase 4.6F não iniciada.

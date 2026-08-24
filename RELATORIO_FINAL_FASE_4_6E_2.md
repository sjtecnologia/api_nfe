# Relatório final da Fase 4.6E.2

## Status atual

O resultado da prova desta fase é:

READY_FOR_4_6F

A implementação shadow de reserva foi corrigida e validada em PostgreSQL real isolado. A suíte dedicada passou com 10 cenários, incluindo a corrida crítica 49 + 2.

Comando executado:

```bash
cd /Volumes/Projects/api_nfe && BILLING_SHADOW_DATABASE_URL='postgresql://postgres@localhost:5432/postgres' pytest -q tests/test_billing_reservation_shadow.py
```

Resultado direto observado: `10 passed`.

## Causas das falhas

1. Reuso de chave de plano em banco compartilhado
   - Os testes criavam `START_V1` repetidamente em um banco persistente e isso gerava `UniqueViolation` em `billing_plans.code`.

2. `begin()` em Session já transacionada
   - O serviço usava `with self.db.begin()` mesmo quando a sessão já estava dentro de uma transação ativa, o que gerava comportamento inconsistente em Postgres.

3. Teardown do banco isolado sem autocommit
   - `DROP DATABASE` em PostgreSQL precisa ocorrer fora de transação; o passo de cleanup foi ajustado para `AUTOCOMMIT`.

## Correções aplicadas

- Isolamento do banco de prova em banco dedicado `billing_reservation_46e2`.
- Cleanup com `TRUNCATE ... RESTART IDENTITY CASCADE` antes/depois dos cenários.
- Lock advisory transacional determinístico para cada assinatura, métrica e período.
- Estratégia de transação própria em `reserve()` e `confirm()`, com rollback de autobegin anterior.
- Ajuste da expectativa de legado para refletir `LEGACY_BYPASS` quando o plano é não migrado e sem bloqueio.
- Mantém a arquitetura shadow-only: nenhuma alteração fiscal, sem SEFAZ/XML/DANFE, sem quota ativa.

## Database isolado

A estratégia aplicada é criar e destruir um banco dedicado por execução. O fluxo foi validado no teste de reserva, incluindo a prova final de concorrência real.

## Transaction strategy

A estratégia aplicada é:

- usar uma sessão por worker/thread,
- abrir transação somente se a sessão não estiver já em transação,
- executar `pg_advisory_xact_lock(hashtextextended(lock_key, 0))`,
- validar `counted + active_reserved + requested <= effective_limit` dentro da mesma transação.

A decisão é reconsultada dentro do lock e o lock é liberado no commit, antes de qualquer integração externa.

## Lock strategy

O lock é `billing-quota:{subscription_id}:{metric_key}:{period_start}:{period_end}`. Python `hash()` não é usado; `hashtextextended` gera a chave estável no PostgreSQL.

## 49 + 2

Status: PASS

Objetivo esperado:

- counted = 49
- active_reserved = 0
- duas sessões concorrentes com quantity = 1
- resultado esperado: 1 reservado e 1 `QUOTA_EXCEEDED`
- total final: 50

Resultado real observado: uma reserva `RESERVED`, uma `QUOTA_EXCEEDED`, com `counted = 49`, `active_reserved = 1` e efetivo 50.

## 48 + 2

Status: PASS, duas reservas ativas e efetivo 50.

## Same key

Status: PASS, uma reserva lógica e uma resposta `DUPLICATE`.

## Confirm / confirm concurrent / release / expiry

Status: PASS nos cenários preservados de confirmação, confirmação duplicada, release e expiry.

## Premium / legacy / override / multi-subscription

Status: PASS nos cenários shadow de premium, legado, override, subscriptions distintas e métricas/períodos distintos.

## Testes PostgreSQL

Atual: 10 testes PostgreSQL passaram, com banco dedicado criado e destruído por execução.

## Suíte completa

Comando executado com PostgreSQL habilitado:

```bash
BILLING_SHADOW_DATABASE_URL='postgresql://postgres@localhost:5432/postgres' pytest -q
```

Resultado: `193 passed, 0 failed`.

## Fiscal enforcement

ZERO

Nenhuma alteração em fluxos fiscais, SEFAZ, XML, DANFE, roteamento NF-e ou emissão.

## Arquivos fiscais alterados

ZERO

## Conclusão

A Fase 4.6E.2 provou em PostgreSQL real que duas requisições simultâneas não conseguem reservar a mesma última vaga.

Resultado desta fase: READY_FOR_4_6F.

Esta conclusão não inicia a 4.6F; apenas registra que o gate técnico da reserva foi satisfeito.

# Relatório Final — Fase 4.6F.11

## STATUS FINAL

`READY_FOR_REAL_LEGACY_MIGRATION_APPROVAL`

O rehearsal final foi concluído com cópia mínima e sanitizada da estrutura real dos clientes legacy 11/13 em PostgreSQL descartável. Nenhuma migração real foi executada.

## SOURCE SJT NFE

`READ ONLY PASS`. O banco `sjtnfe` foi consultado em `SET TRANSACTION READ ONLY`. Foram extraídos somente IDs estruturais, status, assinatura, plano, datas e contagens de usuários. Nenhum nome, documento, endereço, email, certificado, XML, secret, API key ou senha foi copiado.

Snapshot de origem agregado:

- clientes 11 e 13: ativos;
- assinatura legacy ativa: uma por cliente;
- plano de origem: Pacote Básico;
- usuários: 2 no cliente 11 e 3 no cliente 13;
- empresas estruturais: 1 por cliente.

## REHEARSAL DB

`PASS`. Cada teste criou um database descartável `billing_legacy_rehearsal_<pid>_<run>`, com PostgreSQL real, e o removeu no teardown. Destino nunca foi `sjtnfe`.

IDs de destino sintéticos: `101` representa a forma estrutural do cliente 11 e `102` representa a forma estrutural do cliente 13.

## SANITIZATION

`PASS`. Clientes receberam dados textuais sintéticos; documentos pessoais foram nulos/removidos; usuários receberam nomes/emails sintéticos; somente contagens e relacionamentos estruturais foram preservados.

## DRY-RUN

`PASS`. Nenhum BillingAccount, Subscription, vínculo ou override foi criado. Contagens permaneceram `0,0,0,0`.

## APPLY

`PASS`. No rehearsal foram criadas somente as representações esperadas: BillingAccount, BillingSubscription, BillingSubscriptionCompany e overrides explícitos de `MAX_USERS`/`MAX_COMPANIES`.

## CUSTOMER 11

`PASS` no fixture sanitizado 101:

- contracted_price: `60.00` BRL;
- plano: `LEGACY_60_V1`;
- usuários preservados: `2`;
- empresas preservadas: `1`;
- quota: `CONTRACTUAL`/`LEGACY_PRESERVED`, não 50;
- grandfathered: representado pela política do executor;
- novas subscriptions: fechadas.

## CUSTOMER 13

`PASS` no fixture sanitizado 102:

- contracted_price: `60.00` BRL;
- plano: `LEGACY_60_V1`;
- usuários preservados: `3`;
- empresas preservadas: `1`;
- quota: `CONTRACTUAL`/`LEGACY_PRESERVED`, não 50;
- grandfathered: representado pela política do executor;
- novas subscriptions: fechadas.

## IDEMPOTENCY

`PASS`. Segunda execução retornou `ALREADY_MIGRATED` para ambos; contagens finais foram `2 accounts`, `2 subscriptions`, `2 links`, `4 overrides`, sem duplicações ou alteração de preço/capacidade.

## CONCURRENCY

`PASS`. Duas tentativas simultâneas para o mesmo cliente rehearsal produziram uma única representação, usando lock advisory transacional por cliente.

## ROLLBACK

`PASS`. Falha injetada após criação do account removeu toda a representação parcial no rehearsal: account, subscription, company link e overrides ficaram zero para a operação. Dados legacy sanitizados permaneceram intactos.

## LEGACY QUOTA

`PASS`. `LEGACY_60_V1` não herda `START_V1=50`; a feature `NFE_MONTHLY` é `CONTRACTUAL` com metadata `LEGACY_PRESERVED`.

## USER CAPACITY

`PASS`. Capacidades atuais foram preservadas: 2 e 3 usuários, sem limite inferior ou conversão para ilimitado.

## COMPANY CAPACITY

`PASS`. Uma empresa por fixture, explicitamente preservada; nenhum `UNLIMITED_COMPANIES` foi criado.

## FUTURE FEATURE ISOLATION

`PASS`. `AI_INSIGHTS_CENTER` permaneceu desabilitada/roadmap e não foi concedida automaticamente.

## CLIENTES 5 / 12 / 14

Não foram copiados nem migrados. O executor rejeita IDs fora da allowlist sintética com `NOT_APPROVED_FOR_MIGRATION`.

## TESTS

 Full suite PostgreSQL: `239 passed`, sem skips.

## REAL DATABASE WRITES

`0`. Snapshot agregado de `sjtnfe` antes/depois permaneceu inalterado.

## REAL CUSTOMERS MIGRATED

`0`.

## FISCAL FILES CHANGED

`0`.

## PRODUCTION ENFORCEMENT

`ZERO`. Nenhum cliente real foi adicionado ao rollout. Quota permanece desligada em produção.

## DEPLOY

`NÃO REALIZADO`.

A ferramenta está pronta para aprovação humana da futura execução, mas esta fase termina sem `--apply` contra `sjtnfe`. Não iniciar 4.6G nem Fase 5.

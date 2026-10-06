# Relatório Final — Fase 4.6F.12

## STATUS FINAL

`READY_FOR_EXPLICIT_REAL_MIGRATION_AUTHORIZATION`

O dry-run final foi executado contra `sjtnfe` real, sem `--apply`, em conexão local PostgreSQL read-only. Nenhuma migração real foi executada.

## REAL DRY RUN

`PASS`. O executor foi chamado explicitamente com `--dry-run --client-id 11 --client-id 13`. A ausência de Billing shadow em `sjtnfe` foi tratada como `WOULD_CREATE`, sem DDL/DML.

A saída foi repetida duas vezes e comparada byte-a-byte: `identical=YES`.

## CUSTOMER 11

`PASS`:

- decision: `GRANDFATHER_READY`;
- status: `WOULD_MIGRATE`;
- plano proposto: `LEGACY_60_V1`;
- preço: `60.00 BRL`, fonte `MANUAL_BUSINESS_DECISION`;
- `MAX_USERS=2`;
- `MAX_COMPANIES=1`;
- quota: `LEGACY_PRESERVED`;
- acesso existente preservado;
- sem atualização de dados legacy.

## CUSTOMER 13

`PASS`:

- decision: `GRANDFATHER_READY`;
- status: `WOULD_MIGRATE`;
- plano proposto: `LEGACY_60_V1`;
- preço: `60.00 BRL`, fonte `MANUAL_BUSINESS_DECISION`;
- `MAX_USERS=3`;
- `MAX_COMPANIES=1`;
- quota: `LEGACY_PRESERVED`;
- acesso existente preservado;
- sem atualização de dados legacy.

## REAL STATE MATCHES REHEARSAL

`YES`. `sjtnfe` confirmou clientes 11/13 ativos, Pacote Básico, uma assinatura ativa por cliente, usuários 2/3 e uma empresa por cliente.

## OBJECTS WOULD CREATE

Por cliente, exatamente 5 objetos:

- `WOULD_CREATE BillingAccount`;
- `WOULD_CREATE BillingSubscription`;
- `WOULD_CREATE BillingSubscriptionCompany`;
- `WOULD_CREATE BillingSubscriptionOverride(MAX_USERS)`;
- `WOULD_CREATE BillingSubscriptionOverride(MAX_COMPANIES)`.

`ALREADY_EXISTS=0`, `WOULD_UPDATE=0`, `CONFLICT=0`. A PlanVersion legacy e seus features são necessários apenas na futura aplicação isolada; o dry-run real não os cria.

## LEGACY DATA WOULD UPDATE

`ZERO`: clientes, PlanoNFe, AssinaturaCliente, users, user_clients, NF-e, NFC-e e NFS-e não seriam alterados.

## IDEMPOTENCY KEY

A chave estável é `LEGACY_GRANDFATHER_CLIENT_<cliente_id>` combinada com `LEGACY_60_V1` e o vínculo do cliente. Não depende de timestamp, request ID ou UUID aleatório.

## NFE QUOTA

`LEGACY_PRESERVED`. `START_V1=50` não é herdado, direta ou indiretamente.

## SNAPSHOTS

Antes, entre execuções e depois: `clientes=5`, `assinaturas_cliente=2`, `planos_nfe=6`. `DATABASE_WRITES=ZERO`.

## CLIENTES 5 / 12 / 14

Não foram incluídos no dry-run aprovado. O executor possui allowlist explícita e retorna `NOT_APPROVED_FOR_MIGRATION` para IDs não aprovados.

## PRODUCTION PROTECTION

`PASS`: `--apply` contra `sjtnfe` é recusado com `REFUSE_PRODUCTION_WRITE`; dry-run não permite escrita e exige target local permitido.

## FULL SUITE

A regressão PostgreSQL final após a alteração somente do modo dry-run/output foi `240 passed`, sem skips.

## REAL DB WRITES

`ZERO`.

## REAL CUSTOMERS MIGRATED

`ZERO`.

## FISCAL FILES CHANGED

`ZERO`.

## PRODUCTION ENFORCEMENT

`ZERO`.

## DEPLOY

`NÃO REALIZADO`.

## CONCLUSÃO

O que o executor faria em `sjtnfe` está documentado em [LEGACY_REAL_MIGRATION_APPROVAL.md](LEGACY_REAL_MIGRATION_APPROVAL.md). A fase termina aguardando autorização explícita separada; não executar `--apply`, não migrar 11/13, não ativar quota, não iniciar 4.6G nem Fase 5.

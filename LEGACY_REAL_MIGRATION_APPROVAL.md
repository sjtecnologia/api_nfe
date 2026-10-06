# Pacote de Aprovação — Migração Legacy Real

**Status:** dry-run concluído; autorização de escrita ainda não concedida  
**Fonte da decisão:** `MANUAL_BUSINESS_DECISION`  
**Banco de origem:** `sjtnfe`  
**Database writes reais:** `0`

## Cliente 11

**ANTES**

- cliente ativo;
- assinatura legacy ativa;
- plano de origem: Pacote Básico;
- condição comercial aprovada: R$60,00/mês;
- 2 usuários atuais;
- 1 empresa atual;
- evidência histórica individual: não encontrada.

**DEPOIS PROPOSTO**

- `BillingAccount` novo;
- `BillingSubscription` em `LEGACY_60_V1`;
- `contracted_price=60.00`, `currency=BRL`;
- `MAX_USERS=2`;
- `MAX_COMPANIES=1`;
- `NFE_MONTHLY=LEGACY_PRESERVED`/`CONTRACTUAL`;
- `PRESERVE_EXISTING_ACCESS`;
- `CLOSED_TO_NEW_SUBSCRIPTIONS`;
- enforcement: `OFF`.

## Cliente 13

**ANTES**

- cliente ativo;
- assinatura legacy ativa;
- plano de origem: Pacote Básico;
- condição comercial aprovada: R$60,00/mês;
- 3 usuários atuais;
- 1 empresa atual;
- evidência histórica individual: não encontrada.

**DEPOIS PROPOSTO**

- `BillingAccount` novo;
- `BillingSubscription` em `LEGACY_60_V1`;
- `contracted_price=60.00`, `currency=BRL`;
- `MAX_USERS=3`;
- `MAX_COMPANIES=1`;
- `NFE_MONTHLY=LEGACY_PRESERVED`/`CONTRACTUAL`;
- `PRESERVE_EXISTING_ACCESS`;
- `CLOSED_TO_NEW_SUBSCRIPTIONS`;
- enforcement: `OFF`.

## Diferença exata do dry-run

Para cada cliente:

- `WOULD_CREATE`: `BillingAccount`, `BillingSubscription`, `BillingSubscriptionCompany`, `BillingSubscriptionOverride(MAX_USERS)`, `BillingSubscriptionOverride(MAX_COMPANIES)`;
- `ALREADY_EXISTS`: nenhum;
- `WOULD_UPDATE`: nenhum;
- `CONFLICT`: nenhum;
- dados legacy que seriam atualizados: nenhum.

Clientes `5`, `12` e `14` não fazem parte da execução aprovada e devem retornar `NOT_APPROVED_FOR_MIGRATION` sem objetos a criar.

## Aprovação pendente

Este documento é pacote de revisão, não autorização de execução. `--apply` contra `sjtnfe` permanece proibido pelo executor. Uma execução real futura exige nova aprovação humana explícita, validação final do estado e procedimento controlado separado.

# Relatório Final — Fase 4.6F.6

## STATUS FINAL

`REAL_CENSUS_COMPLETE`

O censo comercial real foi executado somente em PostgreSQL local, em transação `READ ONLY`, com rollback garantido. Nenhuma migração comercial foi executada.

## DATABASE AUDITED

`REAL`: database local `sjtnfe`. A conexão foi validada com `current_database()` e `transaction_read_only=on`. O banco E2E não foi usado como substituto.

## TOTAL CLIENTS

5

## ACTIVE

5

## LEGACY CANDIDATES

2

## R60 CANDIDATES

2, identificados por valor público legado exatamente R$60,00. O valor não foi tratado como `contracted_price`.

## HIGH / MEDIUM / LOW

- HIGH: 0
- MEDIUM: 0
- LOW: 2

Os dois casos exigem revisão porque não possuem preço contratado persistido e apresentam conflito de usuários para a capacidade futura do Start.

## MANUAL REVIEW

5 registros: 2 candidatos legacy e 3 clientes sem assinatura ativa. Todos permanecem sem migração.

## PRICE

- preço contratado conhecido: 0;
- preço contratado desconhecido entre legacy: 2.

`PlanoNFe.valor_mensal` foi tratado apenas como evidência de catálogo, nunca como preço contratado.

## IMPACT SIMULATION

- acima de 50 NF-e nos últimos 30 dias: 0;
- conflito de empresas: 0;
- conflito de usuários: 2;
- conflito de features: 0;
- pacote ilimitado legacy: 0;
- clientes sem assinatura: 3.

Os 2 candidatos legacy ficam no grupo C do plano controlado por conflito de usuários. Os 3 sem assinatura ficam no grupo E.

## GROUPS

- Grupo A, grandfathering simples: 0 confirmados.
- Grupo B, R$60 compatível com Start: 0 aprovados.
- Grupo C, R$60 com impacto de capacidade: 2.
- Grupo D, ilimitado ou especial: 0 identificados.
- Grupo E, dados incompletos: 3 sem assinatura, além dos casos legacy sem preço contratado.

## REASON CODES

Foram usados códigos estruturados: `LEGACY_PLAN_MATCH`, `R60_PRICE_MATCH`, `MISSING_PRICE`, `USER_CAPACITY_CONFLICT`, `SHADOW_MISSING`, `NO_SUBSCRIPTION` e `MANUAL_REVIEW_REQUIRED`.

## ALREADY SHADOW

0. As tabelas Billing shadow não existem no banco auditado. Isso não autoriza sua criação nesta fase.

## READ-ONLY PROOF

`SET TRANSACTION READ ONLY` foi aplicado. Snapshot antes/depois: `clientes=5`, `assinaturas_cliente=2`, `planos_nfe=6` em ambos os lados. Resultado: `database_writes=0` e `read_only_snapshot=UNCHANGED`.

## MIGRATED CUSTOMERS

ZERO

## DATABASE WRITES

ZERO

## FISCAL FILES CHANGED

ZERO nesta fase. Nenhum arquivo fiscal foi editado para executar o censo.

## PRODUCTION ENFORCEMENT

ZERO

## TESTS

- Censo real read-only: PASS.
- Preview e testes comerciais: `14 passed` na validação anterior.
- Full suite PostgreSQL após o censo: `219 passed`, sem skips.

## RISK / GAPS

- O legado não persiste `contracted_price` por assinatura.
- Há 2 subscriptions ativas para 5 clientes, portanto 3 clientes estão sem assinatura ativa.
- O banco real não possui representação Billing shadow.
- O censo não autoriza inferência de direitos, quota ou migração.
- O detalhe local `legacy_migration_preview.json` é ignorado pelo Git e não deve ser distribuído.

## DEPLOY

NÃO REALIZADO.

Parar após o censo. Não executar migração comercial, não ativar quota real, não iniciar 4.6G nem Fase 5.
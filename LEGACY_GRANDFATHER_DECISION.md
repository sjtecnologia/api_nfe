# Decisão de Grandfathering Legacy — Fase 4.6F.9

**Data:** 2026-08-25  
**Fonte:** `MANUAL_BUSINESS_DECISION`  
**Status:** aprovada para preview; não persistida e não executada

## Clientes abrangidos

A decisão abrange exclusivamente os clientes internos `11` e `13`. Ambos permanecem `LEGACY_GRANDFATHERED` e `GRANDFATHER_READY` para futura representação controlada.

- mensalidade preservada: R$60,00;
- preço fonte: decisão comercial manual, não evidência histórica reconstruída;
- usuários atuais preservados;
- empresas atuais preservadas;
- nenhuma redução automática de capacidade;
- quota NF-e: `LEGACY_PRESERVED`/`NOT_ENFORCED_LEGACY`;
- features existentes: `PRESERVE_EXISTING_ACCESS`;
- novas features: não concedidas automaticamente;
- `START_V1` não é aplicado retroativamente;
- plano legacy conceitual: `LEGACY_60_V1`;
- novas subscriptions: fechadas (`CLOSED_TO_NEW_SUBSCRIPTIONS`).

A existência de contrato histórico individual continua `NOT_FOUND`; a condição atual foi explicitamente preservada por decisão administrativa.

## Clientes não abrangidos

Os clientes `5`, `12` e `14` permanecem `UNCHANGED_NO_COMMERCIAL_MIGRATION`. Não recebem preço, plano, assinatura, quota, BillingAccount ou recomendação automática.

## Limites da decisão

Grandfathering preserva a condição atual observada e aprovada; não significa empresas ilimitadas, usuários ilimitados, consumo infinito ou acesso automático a produtos futuros. Add-ons, upgrades e novas features exigirão decisão própria.

## Segurança

Nenhum `BillingAccount`, `BillingSubscription`, override, `contracted_price` ou decisão foi criado no banco. O documento é política versionada, não comando de migração.

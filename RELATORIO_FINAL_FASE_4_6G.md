# Relatório Final — Fase 4.6G

## STATUS FINAL

`READY_FOR_CONTROLLED_NEW_SUBSCRIPTION_ROLLOUT`

Catálogo comercial e UX informativa foram consolidados. Checkout, cobrança e enforcement fiscal permanecem desligados.

## CATÁLOGO

Fonte canônica: `services/commercial_catalog.py`.

- `START_V1`: R$60,00, 1 empresa, 1 usuário, 50 NF-e/mês.
- `ESSENCIAL_V1`: R$99,00, 1 empresa, 2 usuários, 200 NF-e/mês.
- `PROFISSIONAL_V1`: R$169,00, 2 empresas, 5 usuários, 500 NF-e/mês.
- `PREMIUM_V1`: R$299,00, 5 empresas, 10 usuários, `UNMETERED_WITH_FAIR_USE`.
- `ENTERPRISE_V1`: sob consulta, capacidades contratuais.
- `LEGACY_60_V1`: somente clientes existentes, fechado para novas subscriptions.

Premium não oferece empresas ilimitadas. NF-e, NFC-e e NFS-e têm políticas independentes.

## LEGACY BASELINE

Clientes 11 e 13 permanecem em `LEGACY_60_V1`, R$60, capacidades preservadas e quota `LEGACY_PRESERVED`. A UX não exibe `START`, `50 NF-e/mês`, IDs internos ou metadata técnica para esses clientes.

## UX

`/admin/meu-plano` agora mostra plano atual, preço contratado, empresas, usuários, política de NF-e, recursos incluídos, planos disponíveis e CTA informativo. Legacy aparece como “Legacy — Condição preservada” e “Sem novo limite aplicado”. Nenhum clique altera assinatura, preço, quota ou entitlement.

## NOVAS ASSINATURAS

`CommercialSubscriptionService` está preparado para fluxo futuro. Usa `PlanVersion` e `contracted_price`, rejeita `LEGACY_60_V1` com `PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS` e não é chamado por checkout nesta fase.

## DECISÕES E GAPS

Os valores de catálogo estão formalizados nos documentos comerciais existentes. Permanecem fora desta fase: cobrança, checkout, Stripe, add-ons, upgrade request persistente, fair use operacional, e entitlements completos para todas as features parciais. Capacidades físicas ausentes no banco não foram inventadas no runtime fiscal.

## TESTES

- Catálogo, subscriptions e legacy: `20 passed` na validação focada.
- Full suite PostgreSQL: `247 passed`, sem skips.

## PRODUÇÃO

- `FEATURE_BILLING_ENTITLEMENTS_ENABLED`: não ativada.
- quota rollout real: sem clientes adicionados.
- enforcement fiscal: `ZERO`.
- checkout/Stripe: `OFF`.
- arquivos fiscais alterados: `ZERO` nesta fase.
- deploy/push: não realizados.

## CONCLUSÃO

A fase está pronta para rollout controlado de novas contratações apenas após aprovação explícita. Parar nesta fase; não ativar cobrança, enforcement, 4.6H ou Fase 5.

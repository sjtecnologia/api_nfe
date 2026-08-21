# Relatório Final — Fase 4.6B

## Status

# FASE 4.6B CONCLUÍDA — CONTRATO DOCUMENTADO

Nenhuma migration, alteração de banco, alteração fiscal, mudança de checkout ou implementação de entitlement foi realizada.

## Matriz aprovada preliminarmente

| Plano | Preço | Empresas | Usuários | NF-e | NFC-e | NFS-e |
|---|---:|---:|---:|---:|---:|---:|
| START | R$60 | 1 | 1 | 50/mês | 50/mês | 30/mês |
| ESSENCIAL | R$99 | 1 | 2 | 200/mês | 200/mês | 100/mês |
| PROFISSIONAL | R$169 | 2 | 5 | 500/mês | 500/mês | 300/mês |
| PREMIUM | R$299 | 5 | 10 | fair use | fair use | fair use |
| ENTERPRISE | Consulta | contratual | contratual | contratual | contratual | contratual |

As quotas NFC-e/NFS-e são contratuais preliminares, não aplicadas.

## Catálogo de features

Criado em [docs/billing/FEATURE_CATALOG.md](billing/FEATURE_CATALOG.md), com keys canônicas e estados `AVAILABLE`, `PARTIAL`, `ROADMAP`. Features ROADMAP não são comercialmente disponíveis.

## Contrato comercial

Criado em [docs/billing/COMMERCIAL_PLAN_CONTRACT.md](billing/COMMERCIAL_PLAN_CONTRACT.md), incluindo:

- limites de empresas/usuários;
- proibição de empresas ilimitadas;
- `UNMETERED_WITH_FAIR_USE`;
- PlanVersion;
- contracted_price;
- add-ons futuros;
- upgrade/downgrade;
- separação role/entitlement/quota.

## Legacy mapping

Criado em [docs/billing/LEGACY_PLAN_MAPPING.md](billing/LEGACY_PLAN_MAPPING.md).

Mapeamentos definidos:

- `PlanoNFe` → `PlanVersion`;
- `AssinaturaCliente` → `Subscription` + `SubscriptionCompany`;
- `quantidade_nfes` → `NFE_MONTHLY`;
- `nfes_consumidas` → não migrar cegamente para `UsageCounter`;
- Pacote Ilimitado → DEPRECATED para novas contratações;
- clientes R$60 → `LEGACY_START_V1` conceitual.

## Política de NF-e

Criado [docs/billing/NFE_QUOTA_POLICY.md](billing/NFE_QUOTA_POLICY.md). A política permanece pendente de aprovação e não foi conectada à emissão.

## Auditoria do estado atual

- planos/assinaturas: legado administrativo/manual;
- assinatura ligada diretamente à empresa;
- checkout Stripe não comprovado como ativo no `app.py`;
- API v2 consulta assinatura;
- emissão web principal não possui enforcement comprovado;
- quotas IA existem como limite técnico por funcionalidade/usuário/cliente;
- não há entitlement central;
- não há PlanVersion, Account, add-ons, overrides ou billing events ativos;
- API keys/webhooks oferecem infraestrutura técnica reutilizável, não cobrança.

## Decisões pendentes

- fonte oficial de billing;
- Account/contratante;
- política de estados que consomem NF-e;
- concorrência/reserva/idempotência;
- fail-open/fail-closed;
- grandfathering detalhado;
- gateway e reconciliação;
- catálogo comercial final;
- quotas NFC-e/NFS-e;
- add-ons;
- Enterprise contratual.

## Testes

A fase é documental. Nenhum teste funcional novo foi implementado. A suíte existente deve ser executada para garantir que a baseline não regrediu.

Resultado da auditoria: nenhum arquivo funcional foi alterado.

## Release Gate e baseline

A baseline `stable-2026-08-21` permanece intacta. Esta fase não altera a tag nem a emissão fiscal.

## Artefatos criados

- `docs/billing/COMMERCIAL_PLAN_CONTRACT.md`
- `docs/billing/FEATURE_CATALOG.md`
- `docs/billing/LEGACY_PLAN_MAPPING.md`
- `docs/billing/NFE_QUOTA_POLICY.md`
- `docs/RELATORIO_FINAL_FASE_4_6B.md`

## Resultado final

# NENHUMA ALTERAÇÃO FUNCIONAL REALIZADA

# NÃO INICIAR FASE 4.6C AUTOMATICAMENTE

# NÃO INICIAR FASE 5

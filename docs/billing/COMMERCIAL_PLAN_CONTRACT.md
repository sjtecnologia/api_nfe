# Contrato Comercial Preliminar — EmiteMax

**Fase**: 4.6G
**Status**: catálogo comercial canônico; não ativa cobrança, checkout ou enforcement
**Baseline fiscal protegida**: `stable-2026-08-21`

## Princípios

- Plano comercial não é role de usuário.
- Assinatura não é empresa.
- Entitlement não é permissão.
- Quota não é limite técnico de IA.
- Preço público não é necessariamente preço contratado.
- Nenhuma mudança comercial pode bloquear emissão fiscal sem implementação aprovada, testes dedicados e rollout controlado.

## Planos

| Plano | Preço mensal | Empresas | Usuários | NF-e/mês | NFC-e/mês | NFS-e/mês |
|---|---:|---:|---:|---:|---:|---:|
| START_V1 | R$ 60 | 1 | 1 | 50 | 50 | 30 |
| ESSENCIAL_V1 | R$ 99 | 1 | 2 | 200 | 200 | 100 |
| PROFISSIONAL_V1 | R$ 169 | 2 | 5 | 500 | 500 | 300 |
| PREMIUM_V1 | R$ 299 | 5 | 10 | `UNMETERED_WITH_FAIR_USE` | `UNMETERED_WITH_FAIR_USE` | `UNMETERED_WITH_FAIR_USE` |
| ENTERPRISE_V1 | Sob consulta | Contratual | Contratual | Contratual | Contratual | Contratual |

As franquias NFC-e/NFS-e são preliminares e não estão conectadas ao runtime.

**Proibição**: Premium nunca oferece empresas ilimitadas. A 6ª empresa exige `COMPANY_ADDON` ou Enterprise.

`LEGACY_START_V1` é fechado para novas vendas. Clientes existentes próximos de R$60 não recebem `START_V1` nem 50 NF-e automaticamente. `contracted_price`, quando conhecido, e direitos observados permanecem protegidos até aceite explícito.

## Capacidades conceituais

- `MAX_COMPANIES`: número máximo de empresas vinculadas;
- `MAX_USERS`: número máximo de usuários;
- `NFE_MONTHLY`, `NFCE_MONTHLY`, `NFSE_MONTHLY`: capacidade mensal futura;
- `COMPANY_ADDON`: empresa adicional contratada;
- `USER_ADDON`: usuário adicional contratado;
- `API_ACCESS`: acesso à API conforme política futura.

Semântica de capacidade:

- `LIMITED`: possui número definido;
- `UNMETERED_WITH_FAIR_USE`: sem franquia comercial predeterminada, mas com proteção contra abuso;
- `CONTRACTUAL`: definido por contrato Enterprise.

Nunca representar ilimitado com `999999`.

`LEGACY_POLICY_REVIEW_REQUIRED` deve ser usado quando os dados não permitirem determinar quota, empresas ou usuários legados.

As capacidades acima são catálogo comercial informativo. O preço efetivamente contratado permanece na assinatura e não muda por alteração posterior do catálogo.

## Versionamento e preço

Identidade comercial deve usar `PlanVersion`, não preço:

- `START_V1`, `ESSENCIAL_V1`, `PROFISSIONAL_V1`, `PREMIUM_V1`.
- Nova oferta pode ser `START_V2` sem alterar clientes `START_V1`.
- A futura assinatura deve armazenar `contracted_price`, além da referência à versão.

Isso suporta desconto, negociação, grandfathering, campanhas e parceiros.

## Legacy

Clientes atuais próximos de R$60 devem ser mapeados para `LEGACY_START_V1`, preservando preço e direitos até decisão explícita. Não migrar automaticamente, não reduzir quota silenciosamente e não interromper emissão.

## Upgrade/downgrade

Futuros upgrades devem criar evento e vigência claros. Downgrade não pode remover capacidade no meio de ciclo sem política aprovada. Alterações devem ser auditáveis e não podem alterar histórico contratual.

## Fair use

`UNMETERED_WITH_FAIR_USE` mantém rate limit, logs, auditoria, proteção contra automação abusiva, sublicenciamento e uso incompatível. Não equivale a ausência de controle técnico.

## Política de migração

Upgrade ou downgrade exige comparação de limites, empresas, usuários, features, add-ons e overrides, confirmação explícita e auditoria. Downgrade incompatível retorna `DOWNGRADE_REQUIRES_ACTION`; não remove empresas ou usuários automaticamente.

## Não implementado nesta fase

Checkout, gateway, webhooks, cobrança de add-ons, solicitação persistente de upgrade e enforcement de inadimplência. Nesta fase, os CTAs apenas orientam o contato comercial.

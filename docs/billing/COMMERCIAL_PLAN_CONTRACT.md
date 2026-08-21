# Contrato Comercial Preliminar — EmiteMax

**Fase**: 4.6B  
**Status**: proposta contratual/documental, não implementada  
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
| START | R$ 60 | 1 | 1 | 50 | 50 | 30 |
| ESSENCIAL | R$ 99 | 1 | 2 | 200 | 200 | 100 |
| PROFISSIONAL | R$ 169 | 2 | 5 | 500 | 500 | 300 |
| PREMIUM | R$ 299 | 5 | 10 | `UNMETERED_WITH_FAIR_USE` | `UNMETERED_WITH_FAIR_USE` | `UNMETERED_WITH_FAIR_USE` |
| ENTERPRISE/PARCEIROS | Sob consulta | Contratual | Contratual | Contratual | Contratual | Contratual |

As franquias NFC-e/NFS-e são preliminares e não estão conectadas ao runtime.

**Proibição**: Premium nunca oferece empresas ilimitadas. A 6ª empresa exige `COMPANY_ADDON` ou Enterprise.

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

## Não implementado nesta fase

Account, Subscription, PlanVersion, entitlements, quotas, add-ons, checkout, gateway, webhooks de billing e enforcement fiscal.

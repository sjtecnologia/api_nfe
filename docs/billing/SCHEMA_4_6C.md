# Schema 4.6C — Shadow

## Tabelas novas

| Tabela | Finalidade |
|---|---|
| `billing_accounts` | contratante comercial |
| `billing_plans` | família de plano |
| `billing_plan_versions` | versão/preço imutável |
| `billing_features` | catálogo de features |
| `billing_plan_features` | matriz feature × versão |
| `billing_subscriptions` | contrato e preço contratado |
| `billing_subscription_companies` | assinatura ↔ empresa |
| `billing_subscription_overrides` | exceções auditáveis |

## Constraints e índices

- keys e version codes únicos;
- feature por plan version única;
- empresa por assinatura única;
- override por assinatura/key único;
- FKs para clientes e usuários;
- índices em versões, assinatura, empresa e overrides;
- tipos de limite controlados: `DISABLED`, `ENABLED`, `LIMITED`, `UNMETERED_WITH_FAIR_USE`, `CONTRACTUAL`.

## Seeds

- `START_V1` — R$60;
- `ESSENCIAL_V1` — R$99;
- `PROFISSIONAL_V1` — R$169;
- `PREMIUM_V1` — R$299;
- `ENTERPRISE_V1` — preço contratual/null.

A migration `database/migrations/009_create_billing_shadow.sql` contém o DDL/seeds, mas não foi executada.

## Segurança da migração

- sem DROP;
- sem ALTER destrutivo;
- sem trigger fiscal;
- sem hook em emissão;
- sem vincular clientes existentes;
- reversão futura deve remover somente objetos novos após backup e aprovação.

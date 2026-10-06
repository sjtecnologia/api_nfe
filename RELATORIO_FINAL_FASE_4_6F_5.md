# Relatório Final — Fase 4.6F.5

## STATUS FINAL

`READY_FOR_LEGACY_MIGRATION_REVIEW`

A política comercial, grandfathering de clientes atuais, proteção de contratos próximos de R$60 e preview read-only foram formalizados. Nenhuma migração comercial foi executada.

## AUDITORIA DE CANDIDATOS

A auditoria foi executada somente no banco E2E local `e2e_46f_local`, que é sintético e não representa a população comercial real:

- candidatos: `1`;
- `HIGH`: `0`;
- `MEDIUM`: `1`;
- `LOW`: `0`;
- preço contratado conhecido: `1`;
- preço contratado aproximadamente R$60: `1`;
- revisão manual: `1`;
- clientes migrados: `0`.

O banco comercial configurado no `.env` não foi consultado: a configuração disponível não forneceu um database local parseável para auditoria segura. Não foram exibidos CPF/CNPJ.

## LEGACY R$60 POLICY

Clientes atuais próximos de R$60 não recebem `START_V1` nem limite de 50 NF-e automaticamente. `contracted_price` é preservado quando existente; `PlanoNFe.valor_mensal` é apenas evidência de catálogo. Sem preço contratado ou contrato suficiente, o resultado é `LEGACY_POLICY_REVIEW_REQUIRED`.

## GRANDFATHERING

`LEGACY_START_V1` é classificação para revisão e `CLOSED_FOR_NEW_SALES`. Login, deploy, migration técnica, alteração de catálogo e feature flags não migram clientes. Encerramento depende de upgrade, aceite explícito, novo contrato, cancelamento/retorno ou negociação formal.

## MATRIZ COMERCIAL

- `START_V1`: novas contratações, 50 NF-e/mês, 1 empresa, 1 usuário.
- `PROFISSIONAL_V1`: 500 NF-e/mês, até 2 empresas, 5 usuários.
- `PREMIUM_V1`: NF-e `UNMETERED_WITH_FAIR_USE`, até 5 empresas, 10 usuários; nunca ilimitado.
- `ENTERPRISE_V1`: capacidades contratuais explícitas.
- `LEGACY_START_V1`: somente grandfathering/revisão, sem novas vendas.

NF-e, NFC-e e NFS-e são capacidades independentes. Recursos `ROADMAP` não são vendidos como disponíveis.

## MIGRATION PREVIEW

`services/billing_migration_preview.py` e `scripts/audit_legacy_customers.py` são read-only, não fazem DDL/DML, não chamam commit e não bloqueiam emissão. O resultado sempre exige `MANUAL_REVIEW`; dados desconhecidos ficam fail-open como `REVIEW_REQUIRED`.

## OVERRIDES E ADD-ONS

O schema atual suporta override com motivo, responsável, data de criação e validade opcional. Add-ons conceituais são `ADDITIONAL_COMPANY`, `ADDITIONAL_USER` e `ADDITIONAL_NFE_PACK`; não há cobrança ou ativação nesta fase. Downgrade incompatível deve retornar `DOWNGRADE_REQUIRES_ACTION` sem remover empresas/usuários automaticamente.

## TESTES

- Preview + commercial shadow: `14 passed`.
- Full suite PostgreSQL: `219 passed`, sem skips; nenhuma lógica fiscal foi reaberta.
- Nenhum cliente foi migrado.

## RISCOS E GAPS

- O legado não armazena `contracted_price` por assinatura.
- `valor_mensal` público não prova preço negociado.
- `quantidade_nfes=NULL` não distingue sozinho avulso, ilimitado ou contrato.
- Não há histórico persistido de aceite/migração.
- O banco E2E não serve como censo de clientes reais.
- Inadimplência, checkout, gateway e cobrança de add-ons permanecem fora desta fase.

## PRODUÇÃO

- enforcement de quota global: `OFF`;
- clientes reais na allowlist: `ZERO`;
- migrações comerciais: `ZERO`;
- checkout/Stripe: `OFF`;
- arquivos fiscais alterados nesta fase: `ZERO`;
- deploy/push: não realizados.

## ARQUIVOS PRODUZIDOS/ATUALIZADOS

- `LEGACY_CUSTOMER_MIGRATION_POLICY.md`
- `LEGACY_R60_POLICY.md`
- `BILLING_MIGRATION_PREVIEW.md`
- `services/billing_migration_preview.py`
- `scripts/audit_legacy_customers.py`
- `tests/test_billing_migration_preview.py`
- `docs/billing/COMMERCIAL_PLAN_CONTRACT.md`
- `docs/billing/FEATURE_CATALOG.md`
- `docs/billing/LEGACY_PLAN_MAPPING.md`
- `docs/billing/NFE_QUOTA_POLICY.md`

Parar nesta fase. Não iniciar 4.6G nem Fase 5.

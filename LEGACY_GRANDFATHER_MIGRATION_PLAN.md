# Plano Futuro de Migração Legacy Grandfathered

**Status:** dry-run/planejamento; nenhuma escrita permitida nesta fase

## Pré-condições

Somente os clientes `11` e `13`, após revisão humana, podem ser considerados para uma futura representação Billing. O aceite deve registrar a decisão manual, data, preço R$60,00, capacidades atuais e política de preservação.

## Representação futura

A execução aprovada poderá criar, em transação idempotente:

1. `BillingAccount` para o contratante identificado;
2. `BillingSubscription` referenciando `LEGACY_60_V1`, `contracted_price=60.00` e `currency=BRL`;
3. `BillingSubscriptionCompany` para as empresas atuais aprovadas;
4. overrides explícitos de `MAX_USERS` e `MAX_COMPANIES` com valores atuais, motivo, operador e validade quando aplicável;
5. entitlements de acesso existente sem conceder features criadas posteriormente.

A quota `NFE_MONTHLY` deve permanecer `LEGACY_PRESERVED`, sem copiar o limite Start de 50.

## Idempotência

A futura operação deverá localizar por uma chave estável de contratante/cliente e verificar, antes de criar, account, subscription, vínculos e overrides. Segunda execução não pode duplicar entidades, alterar preço ou aumentar capacidade. Qualquer conflito deve abortar a transação inteira.

## Rollback

Antes de ativar enforcement, reverter removendo somente a representação Billing criada pela operação, em ordem de dependência, ou marcando-a inativa conforme a política aprovada. Restaurar o estado legacy anterior e não tocar em emissão fiscal, documentos, numeração, XML, SEFAZ ou quota legada.

## Confirmação obrigatória

A execução futura exigirá confirmação explícita, revisão do preview e registro de operador, data, motivo, preço/plano anterior e novo, entitlements anteriores/novos e aceite. `--dry-run` deve ser o padrão; uma opção de escrita, se criada, exigirá confirmação separada e bloqueio contra produção.

## Fora desta fase

Não criar BillingAccount, Subscription, Company ou Override. Não preencher `contracted_price`. Não ativar quota, não comunicar clientes e não executar deploy.

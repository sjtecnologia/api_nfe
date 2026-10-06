# Política de Migração Comercial, Grandfathering e Legados

**Fase:** 4.6F.5  
**Status:** política e auditoria read-only; nenhuma migração executada

## Regra fundamental

Clientes existentes não são convertidos silenciosamente para `START_V1`. Login, deploy, migration técnica, alteração de catálogo ou ativação futura de feature flag não são eventos de migração.

## Grandfathering

`LEGACY_START_V1` é um rótulo de revisão para contratos legados elegíveis. Até uma decisão comercial explícita, preserva-se o `contracted_price` conhecido e os direitos observados. A ausência de evidência não autoriza inferir quota, empresas ou usuários.

Condições de encerramento possíveis, sempre com aceite registrado: upgrade solicitado, migração aceita, cancelamento seguido de nova contratação, alteração contratual formal ou negociação individual. Cancelamento e retorno usam o catálogo vigente, salvo decisão contratual expressa.

## Classificação

- `HIGH`: existe assinatura legacy ativa e preço contratado shadow conhecido, com evidência coerente.
- `MEDIUM`: assinatura ativa e indícios de plano legado ou preço público próximo de R$60, mas falta preço contratado ou evidência completa.
- `LOW`: plano/contrato ausente, ambíguo, sem vigência confiável ou com dados conflitantes.

Mesmo `HIGH` significa `MANUAL_REVIEW`, nunca migração automática.

## Fail-safe

Se não for possível determinar a condição comercial, o resultado é `LEGACY_UNKNOWN`/`REVIEW_REQUIRED` e a emissão não é bloqueada. Quota fiscal não é inferida a partir de preço público ou contador legado isolado.

## Auditoria

A auditoria consulta somente `clientes`, `assinaturas_cliente`, `planos_nfe`, `billing_accounts`, `billing_subscriptions` e vínculos. Não exibe CPF/CNPJ. O preview read-only está em `services/billing_migration_preview.py` e sempre termina com rollback, sem DDL/DML.

## Estados conceituais

`NOT_EVALUATED`, `REVIEW_REQUIRED`, `APPROVED`, `MIGRATION_SCHEDULED`, `MIGRATED`, `REJECTED`, `GRANDFATHERED`.

## Controles obrigatórios de uma migração futura

Registrar operador, data, plano/preço anterior e novo, entitlements antes/depois, motivo, aceite, vigência e evidência. Criar nova subscription/versão quando aplicável; preservar histórico.

**Nesta fase:** `CUSTOMER COMMERCIAL MIGRATIONS = ZERO`.

# Censo Comercial Real — Fase 4.6F.6

**Banco auditado:** `sjtnfe` local  
**Modo:** PostgreSQL `READ ONLY`, rollback garantido  
**Data da execução:** 2026-08-25  
**Migração executada:** não

## Resumo agregado

| Métrica | Resultado |
|---|---:|
| Total de clientes | 5 |
| Ativos | 5 |
| Inativos | 0 |
| Candidatos legacy | 2 |
| Candidatos LEGACY_R60 | 2 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 2 |
| Revisão manual | 5 |
| Preço contratado conhecido | 0 |
| Preço contratado desconhecido | 2 legacy |
| Pacote ilimitado legacy | 0 |
| Acima de 50 NF-e nos últimos 30 dias | 0 |
| Conflito de empresas | 0 |
| Conflito de usuários | 2 |
| Conflito de features | 0 |
| Já representados em shadow | 0 |
| Sem assinatura | 3 |
| Inconsistências detectadas | 0 |
| Clientes migrados | 0 |
| Escritas no banco | 0 |

## Interpretação

Os dois candidatos legacy têm plano identificável e preço público de R$60, mas não possuem `contracted_price` persistido. Por isso ambos são `LOW`, `MANUAL_REVIEW_REQUIRED` e não podem ser convertidos automaticamente. O conflito de usuários impede tratar esses casos como migração simples para `START_V1`.

Os três clientes sem assinatura ativa não foram classificados como legacy. Permanecem `NO_SUBSCRIPTION`, `REVIEW_REQUIRED` e fail-open.

O banco real não possui as tabelas Billing shadow nesta execução; portanto `ALREADY_SHADOW=0` significa “nenhuma representação encontrada”, não autorização para criar uma.

## Segurança e escopo

O censo não seleciona CPF/CNPJ, telefone, endereço, certificados, API keys ou senhas. O detalhamento administrativo local está em `legacy_migration_preview.json`, ignorado pelo Git. Nenhuma comunicação, alteração de preço, alteração de plano, vínculo, quota ou emissão fiscal foi realizada.

## Arquivo detalhado

`legacy_migration_preview.json` é artefato local ignorado e contém somente `cliente_id`, nome de plano e métricas comerciais mínimas para revisão autorizada. Não deve ser versionado nem enviado para fora do ambiente administrativo.

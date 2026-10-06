# Mapeamento de Planos Legados

**Fase**: 4.6F.5
**Status**: somente mapeamento e revisão; nenhuma migração executada

## Mapeamento conceitual

| Legado | Futuro | Compatibilidade |
|---|---|---|
| `PlanoNFe` | `PlanVersion` | `nome`, preço e quantidade não bastam para identidade/versionamento |
| `AssinaturaCliente` | `Subscription` + `SubscriptionCompany` | legado liga diretamente a empresa |
| `cliente_id` na assinatura | vínculo da assinatura à empresa | futuro deve passar por conta contratante |
| `quantidade_nfes` | capacidade `NFE_MONTHLY` | não cobre NFC-e/NFS-e nem semântica de estados |
| `nfes_consumidas` | `UsageCounter` derivado de `UsageEvent` | não migrar cegamente; origem/status/idempotência não estão registrados |
| `valor_mensal` no plano | `contracted_price` na assinatura | preço atual não preserva desconto/negociação |
| `data_inicio/data_fim` | vigência da Subscription | precisa de histórico de eventos |
| `status` textual | estado/versionamento de assinatura | precisa de eventos, motivo e fonte |
| plano com quantidade `NULL` | `UNMETERED_WITH_FAIR_USE` ou `CONTRACTUAL` | não deve virar empresas ilimitadas |

## Pacote Ilimitado legado

O plano `Pacote Ilimitado` da migration 006 é `DEPRECATED` para novas contratações futuras. Não apagar, não alterar e não bloquear clientes existentes nesta fase.

## Legacy Start

Clientes atuais próximos de R$60 devem ser identificados e mapeados para `LEGACY_START_V1` em uma futura migração assistida. Preservar:

- preço contratado;
- direitos atuais;
- quantidade de empresas/usuários existente;
- data e evidência de contratação;
- descontos e observações.

Não preencher informações ausentes por inferência.

## Incompatibilidades

1. Não há entidade Account/contratante.
2. Não há preço contratado por assinatura.
3. Não há PlanVersion.
4. Não há histórico de mudança.
5. Não há SubscriptionCompany.
6. Não há add-ons.
7. `nfes_consumidas` é contador mutável, sem UsageEvent idempotente.
8. Não há política formal para autorizada/rejeitada/cancelada/retry.
9. Quota de IA e quota fiscal são conceitos misturados por fallback de `quantidade_nfes` no serviço de IA.
10. API v2 e emissão web têm enforcement diferente.

## Política 4.6F.5

- `LEGACY_START_V1` é `CLOSED_FOR_NEW_SALES`.
- `START_V1` com 50 NF-e/mês vale para novas contratações, não retroativamente.
- `contracted_price` é a fonte do preço contratado; `valor_mensal` não o substitui.
- `quantidade_nfes=NULL` não será convertido em ilimitado sem contrato.
- Premium possui no máximo 5 empresas e 10 usuários; nunca “ilimitado”.
- Falta de evidência resulta em `LEGACY_UNKNOWN`/`REVIEW_REQUIRED` e fail-open.

## Estratégia futura

1. Extrair snapshot somente leitura.
2. Classificar cada plano/assinatura.
3. Criar PlanVersion legado imutável.
4. Criar adapter de leitura em shadow mode.
5. Comparar resultados com o legado.
6. Migrar eventos/uso somente após política aprovada.
7. Manter rollback e baseline fiscal intactos.

# Política de Quota NF-e — 4.6E.1

**Fase**: 4.6E.1
**Status**: proposta técnica formalizada; não aplicada ao runtime fiscal

## Objetivo

Definir a política comercial e técnica de faturamento para NF-e sem ativar enforcement em produção. Esta fase apenas valida a camada shadow de uso e documenta o ponto futuro de hook fiscal.

## Regra final de não mistura

Quota fiscal não pode ser baseada em “parece que funciona”. Antes de bloquear a 51ª NF-e de um cliente real, é necessário definir:

- o que conta;
- quando conta;
- como concorre;
- como faz retry;
- como reconcilia;
- o que acontece quando billing falha.

## Concurrency e idempotência

A correção implementada na camada shadow garante que:

- `BillingUsageEvent` usa `UniqueConstraint("metric_key", "event_key")`;
- `BillingUsageShadowService.record()` verifica duplicidade antes do insert;
- se o banco rejeita a inserção por violação de unique constraint, o serviço faz rollback e retorna `DUPLICATE`;
- no PostgreSQL, o `billing_usage_counters` usa `INSERT ... ON CONFLICT DO UPDATE`;
- o caminho de código evita lost update e mantém idempotência em retries simultâneos.

Exigência formal para o futuro:

- `event_key` fiscal deve ser determinístico;
- não usar UUID aleatório para NF-e lógica;
- a mesma chave precisa cobrir retry, callback duplicado, reload, reenvio e webhook repetido.

## Event key NF-e

Recomendação padrão:

```text
NFE:<nfe_emitida_id>:AUTHORIZED
```

ou outra chave determinística equivalente, derivada do documento fiscal real e do status final. O key deve ser mapeado em função do `source_id` da NF-e autorizada para evitar contagem duplicada.

## Status policy

| Status | Conta? | Reversão? | Motivo |
|---|---|---|---|
| RASCUNHO | Não | Não | Estado local, não transmitido |
| TENTATIVA LOCAL | Não | Não | Falha de validação local |
| REJEITADA | Não | Não | Documento não autorizado |
| AUTORIZADA | Sim, 1 | Não | Consumo comercial real |
| CANCELADA (após autorização) | Não devolve automaticamente | Não | No futuro, quota já foi consumida |
| DENEGADA | Não | Não | Documento não aceite pelo emissor/estado |
| CONTINGÊNCIA | Não até reconciliação | Não | Estado intermediário e potencialmente transiente |
| REENVIO / DUPLICIDADE | Não | Não | Mesma operação lógica deve ser deduplicada |
| INUTILIZAÇÃO | Não | Não | Não é NF-e emitida na prática |
| FALHA DE REDE | Não decide automaticamente | Não | Requer reconciliação do estado real |
| TIMEOUT COM RESULTADO DESCONHECIDO | Não decide automaticamente | Não | Aguardando reconciliação |

## Cancelamento

A recomendação comercial padrão é manter quota consumida após autorização. O cancelamento posterior não reverte automaticamente a utilização. Isso preserva a regra de que o uso de emissão foi realizado e o documento fiscal já foi aceito.

## Retry, reenvio e duplicidade

- retry da mesma NF-e não deve gerar nova contagem;
- reenvio do mesmo documento deve ser tratada como operação idempotente;
- duplicidade deve causar `DUPLICATE` ou equivalente;
- o contador deve ser incrementado apenas uma vez por `event_key` único.

## Timeout e status ambíguo

Se a transmissão tiver timeout ou o retorno não for conclusivo, a política recomendada é não decidir pela quota até reconciliação do estado real.

## Ponto futuro de hook

O ponto mais seguro, em arquitetura, é:

```text
rota de emissão
↓
workflow / service de NFe
↓
transmissão à SEFAZ
↓
persistência do documento
↓
status autorizado
```

O registro do evento fiscal deve ocorrer somente após confirmação confiável de autorização, nunca ao clicar em “Emitir” e nunca antes da chamada externa ser concluída.

Não foi inserido hook fiscal nesta fase. A identificação do ponto exato deve ser feita no fluxo real de NFe antes de 4.6F.

## Reserva de quota

Para o eventual enforcement da 4.6F, a arquitetura mais segura em PostgreSQL é uma reserva curta e transacional antes da transmissão:

- `CHECK` para verificar limite atual;
- `RESERVE`/`PENDING` para bloquear a operação em curso;
- `CONFIRM` ao autorizar;
- `RELEASE` em caso de rejeição, timeout ou falha.

Trade-off:

- opção simples: lock curto imediatamente antes da transmissão;
- opção mais robusta: reserva atômica com TTL/expiração e reconciliação.

Padrão recomendado para a futura 4.6F: reserva curta, não lock longo da transação durante a chamada externa à SEFAZ.

## Fail-safe

Se a NF-e foi autorizada e o `UsageEvent` falhar, a emissão fiscal não pode ser revertida nem exibida como erro fiscal. A estratégia mínima é:

- manter o documento fiscal válido;
- registrar uso em `PENDING_RECONCILIATION` ou mecanismo equivalente;
- permitir reconciliação posterior;
- impedir que falha de billing transforme documento autorizado em erro fiscal.

## Fail-closed

Diferenciar claramente:

- antes da transmissão: quota check pode impedir nova emissão quando enforcement estiver ativo;
- depois da autorização: falha de billing não pode transformar documento autorizado em erro fiscal.

## API v2 + Web

A quota futura deve compartilhar a mesma fonte comercial para Web NF-e e API v2 NF-e. Não devem existir contadores paralelos ou duplicados por canal de entrada.

## Legacy, Premium e Enterprise

- `LEGACY_START_V1`: não receber limite de 50 automaticamente sem migração comercial aprovada;
- `PREMIUM`: `NFE_MONTHLY = UNMETERED_WITH_FAIR_USE`; não inventar limite de 999999;
- `ENTERPRISE`: usar limite contratual somente se configurado; caso contrário, marcar `CONTRACTUAL_REVIEW` e não inventar valor.
- `SUPER_ADMIN`: bypass operacional deve ser explícito, auditado e motivado; nunca silencioso.

## Alertas de consumo

A política proposta para alertas é:

- 70%;
- 80%;
- 90%;
- 100%.

Esses alertas não devem ser ativados na UI desta fase; apenas eventos/estados devem ser definidos.

## 50/50, 51ª NF-e e contrato de erro

- `START` com `used=49` e `limit=50`: próxima reserva deve ser permitida;
- `used/reserved=50`: próxima tentativa deve ser bloqueada;
- a mensagem de quota excedida deve ser: “Você atingiu o limite de 50 NF-e do seu plano Start neste período.”;
- o erro comercial deve ser expresso com `code = PLAN_NFE_QUOTA_EXCEEDED` e não como rejeição SEFAZ.

## Reconciliação e backfill

A futura reconciliação deve detectar:

- NF-e autorizada sem `UsageEvent`;
- `UsageEvent` sem NF-e autorizada;
- counter divergente;
- event duplicado.

Backfill deve ser idempotente e persistir `event_key` determinístico por documento. Não foi executado nesta fase.

## Arquivos e testes deste estágio

Arquivos fiscais alterados: `ZERO`.

Validação realizada:

- 7 testes do shadow billing passaram;
- 0 falhas;
- 0 skips;
- comando executado: `pytest -q tests/test_billing_usage_shadow.py`.

## Status final do rollout

O estágio 4.6E.1 está pronto para auditoria de concorrência e documentação de quota, mas ainda não atende ao critério final para 4.6F:

- concorrência real PostgreSQL exaustiva ainda não foi executada para 49/50 + 2 processos;
- a política fiscal completa para cada status ainda precisa fechar acordo final com o fluxo real;
- o ponto exato de hook na emissão NF-e não foi validado no código da aplicação;
- a reserva de quota e fail-safe finais ainda são projeto e não implementação.

## Resultado

`BLOCKED` para 4.6F.

Não iniciar 4.6F até que a concorrência real, a idempotência fiscal final, a política de status e a estratégia de reserva sejam validadas no fluxo real da aplicação.

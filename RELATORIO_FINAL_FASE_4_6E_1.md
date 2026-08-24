# Relatório Final — Fase 4.6E.1

## Status

**Resultado**: READY_FOR_4_6F? **NO**

**Resultado correto**: **BLOCKED**

A fase 4.6E.1 concluiu os requisitos mínimos do shadow billing em termos de concorrência e idempotência de uso, mas ainda não atende ao critério final da fase 4.6F porque a quota fiscal real não foi validada no fluxo de emissão com o contrato de status definido e a reserva de quota ainda está em desenho.

## 1. Concorrência

Foi validado o padrão de concorrência no serviço shadow:

- `BillingUsageEvent` exige chave única em `(metric_key, event_key)`;
- o serviço checa duplicidade antes do insert;
- em caso de erro de integridade do banco, o serviço faz `rollback` e devolve `DUPLICATE`;
- o counter usa `INSERT ... ON CONFLICT DO UPDATE` em PostgreSQL;
- o uso em testes unitários confirma ausência de perda do counter em cenário de chave duplicada.

### Evidência executada

Comando executado:

```bash
pytest -q tests/test_billing_usage_shadow.py
```

Resultado:

- `7 passed`;
- `0 failed`;
- `3 warnings`.

## 2. Idempotência

A camada shadow implementa idempotência por `(metric_key, event_key)`.

O cenário coberto:

- mesmo `event_key` repetido;
- retorno `DUPLICATE`;
- sem contagem adicional;
- sem criação de evento duplicado.

A gravação do counter também é protegida por unique constraint por período.

## 3. Status policy

Foi documentada a política recomendada para NF-e:

- `RASCUNHO`: não conta;
- `REJEITADA`: não conta;
- `AUTORIZADA`: conta 1;
- `CANCELADA` após autorização: não reverte automaticamente;
- `TIMEOUT/RESULTADO DESCONHECIDO`: não decide até reconciliação;
- `REENVIO/DUPLICIDADE`: não conta novamente;
- `CONTINGÊNCIA`: pendente de decisão.

## 4. Ponto seguro de instrumentação

O ponto recomendado é somente após confirmação confiável de autorização do documento fiscal, nunca antes da transmissão e nunca apenas ao clicar em “Emitir”.

A arquitetura ainda não foi conectada ao fluxo real da aplicação; a análise ficou documental e em projeto.

## 5. Fail-safe

A estratégia definida é:

- documento fiscal autorizado permanece válido;
- falha de billing não reverte emissão fiscal;
- uso é recolocado em `PENDING_RECONCILIATION` ou mecanismo equivalente;
- reconciliação posterior corrige divergência.

## 6. Reserva de quota

A arquitetura recomendada para futura 4.6F é:

- `CHECK + RESERVE` antes da transmissão;
- `CONFIRM` quando autorizado;
- `RELEASE` em rejeição/timeout/falha;
- TTL/expiração para evitar reserva infinita;
- lock curto, sem manter transação aberta durante a chamada externa à SEFAZ.

## 7. Arquivos fiscais alterados

**ZERO**

Nenhum XML, regra fiscal, flow, ou documento de transmissão foi alterado nesta fase.

## 8. Testes

### Testes executados

- `pytest -q tests/test_billing_usage_shadow.py`

### Resultado

- total: `7`
- passed: `7`
- failed: `0`
- skipped: `0`

## 9. Deploy

**NÃO REALIZADO**.

## 10. Decisão final

O estágio alcançou a prova de:

- concorrência da camada shadow;
- idempotência por `event_key`;
- tratamento de duplicidade por restrição de banco;
- ponto futuro de hook identificado;
- fail-safe e reserva definidas em desenho.

Mas ainda faltam os critérios finais exigidos para o gate da 4.6F:

- concorrência real com 49/50 + 2 solicitações em PostgreSQL isolado;
- decisão final de status fiscal para cada fluxo de NFe real;
- validação do hook no fluxo de emissão ativo;
- contrato de erro comercial e UX final da 51ª NF-e;
- confirmação de tabela de reconciliação e TTL de reserva.

## Resultado final

**BLOCKED**

Não avançar para 4.6F sem fechar esses pontos em validação real do fluxo fiscal.

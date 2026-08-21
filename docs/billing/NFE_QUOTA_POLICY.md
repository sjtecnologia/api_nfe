# Política de Quota NF-e — Decisão Pendente

**Fase**: 4.6B  
**Status**: proposta técnica; NÃO aplicada ao runtime

## Objetivo

Definir questões que precisam de aprovação comercial, jurídica e técnica antes de limitar emissão. Nenhuma quota é ativada por este documento.

## Questões pendentes

| Evento | Decisão necessária | Recomendação técnica preliminar |
|---|---|---|
| NF-e autorizada | Conta quota? | Sim: documento efetivamente autorizado |
| NF-e rejeitada | Conta quota? | Não por padrão; registrar tentativa separadamente |
| NF-e cancelada | Devolve quota? | Não automaticamente: autorização já consumiu documento fiscal |
| Inutilização | Conta quota? | Não como NF-e emitida; registrar evento próprio |
| Contingência | Conta quota? | Reservar/contar conforme política de transmissão posterior |
| Retry/reenvio | Conta novamente? | Não: idempotência por operação/documento |
| Duplicidade | Conta novamente? | Não: deduplicar por chave/operação |
| Rascunho | Conta quota? | Não: estado local não transmitido |
| Falha antes da transmissão | Conta quota? | Não; registrar falha técnica |
| Falha após transmissão incerta | Conta quota? | Estado pendente para reconciliação, nunca incremento cego |
| NFS-e/NFC-e | Compartilham quota? | Não assumir; quotas separadas |

## Ponto de enforcement futuro

O check deve ocorrer após autenticação, autorização de role e resolução do tenant, e antes do primeiro efeito externo/transmissão. A reserva precisa ser atômica e idempotente. O enforcement não deve ser inserido na geração XML, assinatura ou retry sem testes específicos.

## Modelo recomendado

```text
UsageEvent(document_type, tenant, operation_id, status, occurred_at)
        ↓ idempotência
QuotaReservation(cycle, operation_id, state)
        ↓ transação/lock
UsageCounter(cycle, document_type, committed_usage)
```

O contador legado `nfes_consumidas` não deve ser copiado cegamente para `UsageCounter` sem auditoria e reconciliação.

## Concorrência

O cenário 49/50 com duas requisições exige reserva condicional/transação serializável ou mecanismo equivalente. Um `SELECT` seguido de `UPDATE` sem lock não é suficiente.

## Falha do serviço de entitlement

Decisão pendente. Recomendação preliminar:

- features não fiscais: fail-closed;
- emissão fiscal: usar estado local auditável/cacheável e política aprovada; nenhum bypass silencioso;
- emissão já autorizada não deve ser desfeita por falha posterior de registro;
- falha ambígua deve ir para reconciliação.

## Avisos

Propor alertas em 70%, 80%, 90% e 100% no dashboard/emissão, mas não implementar nesta fase.

## Testes obrigatórios antes de ativação

- 50ª e 51ª emissão;
- autorizada/rejeitada/cancelada/inutilizada;
- retry/idempotência;
- concorrência;
- contingência;
- multiempresa;
- ausência/falha de entitlement;
- rollback/desativação da política.

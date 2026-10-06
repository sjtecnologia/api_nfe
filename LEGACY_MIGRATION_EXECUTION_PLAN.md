# Plano de Migração Controlada — Fase 4.6F.6

**Status:** proposta; não executar nesta fase

## Regras de entrada

Nenhum cliente é migrado sem revisão administrativa, contrato/evidência suficiente, confirmação explícita quando aplicável, comparação de entitlements e registro de auditoria. O plano vigente não altera emissão fiscal, quota, preço ou vínculos.

## Grupos

### Grupo A — Grandfathering simples

Candidatos com dados coerentes, sem conflito de capacidade e com direitos documentados. Marcar `GRANDFATHER_READY`; preservar condição legada até aceite. Não migrar automaticamente.

### Grupo B — R$60 compatível

Clientes com evidência contratual de aproximadamente R$60, uso dentro dos limites novos e sem perda funcional. Podem receber oferta futura de `START_V1`, sempre com diferenças, preço, limites e confirmação explícita.

### Grupo C — R$60 com impacto

Clientes acima de 50 NF-e/mês ou com conflito de empresas/usuários/features. Não oferecer START automaticamente; avaliar `ESSENCIAL_V1`, `PROFISSIONAL_V1` ou condição especial.

### Grupo D — Pacote ilimitado ou contrato especial

Revisão individual obrigatória. Nunca converter automaticamente para `PREMIUM_V1`; Premium possui capacidade explícita de cinco empresas e fair use para emissão.

### Grupo E — Dados incompletos/inconsistentes

Corrigir cadastro ou localizar evidência contratual antes de qualquer oferta. Usar `REVIEW_REQUIRED`/`LEGACY_UNKNOWN` e fail-open.

## Resultado do censo atual

- Grupo A: 0 confirmados; os 2 legacy exigem revisão por preço contratado ausente e conflito de usuários.
- Grupo B: 0 aprovados.
- Grupo C: 2 candidatos para atenção especial por conflito de usuários.
- Grupo D: 0 identificados.
- Grupo E: 3 clientes sem assinatura ativa, além dos 2 casos legacy sem preço contratado.

## Execução futura

1. Aprovar a política e revisar cada caso.
2. Confirmar contratante, empresas, usuários, preço e entitlements.
3. Mostrar impacto e aviso de irreversibilidade antes do aceite.
4. Criar nova versão/subscription sem sobrescrever histórico.
5. Registrar operador, data, motivo, preço/planos e entitlements antes/depois.
6. Validar em shadow e manter rollback.

**Nesta fase:** migrações comerciais `ZERO`, checkout `OFF`, gateway `OFF`, enforcement de inadimplência `OFF`, quota de clientes reais `OFF`.

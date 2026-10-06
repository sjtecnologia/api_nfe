# Plano de implementação — CT-e e MDF-e

## Escopo

Esta frente cobre CT-e, CT-e OS, CT-e Simplificado e MDF-e. A referência
externa confirma que CT-e/CT-e OS contempla webservices estaduais e que MDF-e
possui operação própria de emissão; ambas as referências devem ser tratadas
como contratos de integração, não como leiaute para copiar diretamente.

## Fases

1. **Contrato fiscal**: versões de schemas/MOC, ambientes, séries, numeração,
   regras de autorização, rejeição, cancelamento e encerramento.
2. **Domínio**: tabelas próprias para transportador, participantes, carga,
   modal, veículos, percurso e documentos vinculados.
3. **Motor XML**: geração e assinatura A1 sem compartilhar builders de NF-e;
   validação XSD antes do envio.
4. **Transmissão**: adapter por SEFAZ/ambiente, timeout, consulta posterior,
   idempotência e reconciliação sem reemitir automaticamente.
5. **API**: emitir, consultar, status, XML, cancelar e eventos; MDF-e inclui
   encerramento e eventos próprios.
6. **Frontend**: assistente por modal, validação progressiva, pré-visualização,
   acompanhamento de status e histórico por cliente.
7. **Operação**: webhooks assinados, retry com lock, auditoria, limites e
   suporte por volume/SLA.

## Ordem recomendada

Implementar primeiro CT-e modelo 57 em homologação; depois CT-e OS e CT-e
Simplificado; por fim MDF-e, que depende da modelagem de transporte e dos
documentos vinculados. Cada fase precisa de testes de autorização, rejeição,
duplicidade, consulta, cancelamento e recuperação antes da próxima.

## Critério de liberação

Nenhum desses documentos deve aparecer como “disponível” no frontend até haver
schema vigente, certificado de homologação, smoke test real, persistência do
protocolo e rollback/reconciliação documentados.

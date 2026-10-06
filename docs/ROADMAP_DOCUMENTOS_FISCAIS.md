# Lista de implementações fiscais

## Já em execução / disponível

- [x] NF-e (modelo 55): emissão, consulta, XML, cancelamento e webhook.
- [x] NFC-e (modelo 65): emissão, consulta, XML, cancelamento e webhook.
- [x] NFS-e: emissão, consulta, XML, cancelamento e fluxo no frontend.
- [x] API Keys por cliente, idempotência e separação de ambiente.
- [x] Homologação e checklist de publicação.

## Próxima frente — documentos de transporte

- [ ] **CT-e (modelo 57)** — emissão, assinatura, autorização, consulta,
  cancelamento, inutilização quando aplicável, XML e eventos/webhooks.
- [ ] **CT-e OS (modelo 67)** — emissão para os cenários de transporte de
  pessoas, valores e excesso de bagagem, com regras próprias de tomador,
  modal e serviço.
- [ ] **CT-e Simplificado** — avaliar o leiaute, regras de uso e suporte no
  ambiente nacional antes de liberar emissão.
- [ ] **MDF-e (modelo 58)** — emissão, assinatura, autorização, consulta,
  cancelamento, encerramento, XML e eventos/webhooks.

Referência funcional inicial:
[documentação CT-e / CT-e OS da FocusNFe](https://doc.focusnfe.com.br/reference/ctecteos) e
[documentação MDF-e da FocusNFe](https://doc.focusnfe.com.br/reference/mdfe).

## Critérios obrigatórios da frente CT-e

1. Confirmar leiautes e schemas oficiais vigentes, incluindo versões do MOC e
   regras do ambiente nacional/SEFAZ.
2. Modelar transportador, remetente, expedidor, recebedor, tomador, carga,
   documentos vinculados, modal e informações de pagamento sem reutilizar
   campos de NF-e por conveniência.
3. Criar rotas API e frontend separados, com isolamento por cliente e ambiente.
4. Implementar idempotência, estados, consulta, cancelamento e eventos antes
   de anunciar a emissão.
5. Testar autorização, rejeição, duplicidade, contingência quando aplicável,
   cancelamento e reprocessamento em homologação.
6. Definir preço por volume, custo de suporte e SLA próprios para transporte.

## Critérios adicionais do MDF-e

1. Modelar emitente, modal, veículo/condutor, percurso, municípios de
   carregamento/descarregamento e documentos fiscais vinculados.
2. Impedir encerramento sem autorização e sem os dados de encerramento
   exigidos; validar também cancelamento conforme o estado do manifesto.
3. Tratar MDF-e como documento operacional distinto de CT-e: não reutilizar
   numeração, estados, XML ou regras de cancelamento de CT-e.
4. Cobrir cenários rodoviário, carga própria/terceiros e combinações de CT-e/
   NF-e em homologação antes de liberar o frontend.

CT-e, CT-e OS e CT-e Simplificado ficam registrados como **planejados**, não
como funcionalidades disponíveis, até que esses critérios tenham evidência
automatizada e homologação real.

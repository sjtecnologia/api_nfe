# Prontidão do produto fiscal

Este documento separa o que precisa estar pronto para a emissão no painel do
que precisa estar pronto para clientes integradores. São produtos relacionados,
mas com riscos e custos operacionais diferentes.

## 1. Emissão no próprio sistema

Critérios de aceite:

- cliente selecionado explicitamente e validado contra a sessão do usuário;
- certificado, município, regime tributário, série e ambiente exibidos antes do envio;
- homologação como padrão para configuração nova;
- validação de tomador, itens, valores e campos fiscais antes da transmissão;
- estado visível: rascunho, enviando, processando, autorizada, rejeitada ou cancelada;
- somente protocolo oficial permite apresentar o documento como autorizado;
- consulta, XML, DANFSe/DANFE e cancelamento disponíveis na mesma área;
- erros da prefeitura/SEFAZ mostrados sem expor certificado, senha ou payload sensível.

## 2. Integração de terceiros

Critérios de aceite:

- documentação executável com exemplos reais de request/response e permissões;
- API Key vinculada a exatamente um cliente emitente;
- toda consulta e mutação filtra pelo `g.cliente_id` da chave;
- idempotência obrigatória para emissão em produção;
- estados e códigos HTTP documentados, inclusive `202`, `409`, `502` e rejeições;
- webhooks com consumidor idempotente e consulta posterior como fonte de confirmação;
- rate limit por chave, logs sem CPF/CNPJ/endereço/payload fiscal completo e rotação de chave;
- contrato de compatibilidade versionado antes de oferecer suporte a integradores.

## 3. Ambiente de testes e homologação

O código já trabalha com `homologacao` e `producao`, mas isso não substitui um
sandbox de produto. Antes de vender integração, deve existir:

1. chave de teste identificável e dados de teste separados;
2. banco/schema ou namespace de testes sem documentos de produção;
3. certificados e endpoints municipais/SEFAZ de homologação separados;
4. respostas determinísticas para validação, rejeição, processamento e timeout;
5. smoke test com emissão, consulta, XML e cancelamento;
6. bloqueio explícito para impedir que chave de teste atinja endpoint de produção.

Até esses itens existirem, a documentação deve chamar o fluxo de “homologação
com credenciais do cliente”, e não de sandbox isolado.

## 4. Preço, volume e suporte

Preço não deve ser uma única franquia genérica: NF-e, NFC-e e NFS-e têm custos
de suporte e comportamento de volume diferentes. A tabela comercial deve
definir para cada faixa:

- franquia mensal por modelo;
- excedente ou migração de plano;
- rate limit técnico separado da franquia comercial;
- retenção de XML, webhooks e consultas;
- número de empresas, usuários e ambientes;
- SLA e canal de suporte;
- custo de implantação/homologação assistida para integrações complexas.

O catálogo atual é preliminar: as franquias NFC-e/NFS-e ainda não estão ligadas
ao runtime. Não ativar bloqueio dessas franquias sem medição idempotente,
período de competência, tolerância de falhas e rollout controlado.

## Gate antes de comercializar

Não anunciar “API pronta para produção” enquanto os seis itens do ambiente de
testes não estiverem comprovados e uma emissão real em homologação tiver sido
registrada por modelo e município. O release fiscal deve seguir
`deployment/CHECKLIST_RELEASE_FISCAL.md`.

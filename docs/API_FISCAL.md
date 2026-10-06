# API Fiscal — NF-e, NFC-e e NFS-e

Todas as rotas abaixo usam `POST` ou `GET` em `/api/v2` e exigem uma API Key
com as permissões indicadas. Envie a chave em
`Authorization: Bearer emx_live_...` ou `Authorization: Bearer emx_test_...`.
A API Key identifica o cliente emitente; nunca envie certificado digital no
payload. O parâmetro `?api_key=` fica desativado por padrão e só deve ser
habilitado temporariamente em ambientes legados via `ALLOW_API_KEY_QUERY_PARAM`.

## Idempotência

Use o header `Idempotency-Key` em toda emissão. A mesma chave só pode ser
reutilizada com o mesmo payload. Um payload diferente retorna `409`. Enquanto
a primeira requisição estiver em processamento, novas tentativas retornam
`202` com status `PROCESSANDO`; depois da conclusão, a resposta original é
reapresentada.

## NF-e (modelo 55)

`POST /api/v2/nfe/emitir` — permissões `nfe.write` e `nfe.emit`.

Também estão disponíveis:

- `GET /api/v2/nfes` e `GET /api/v2/nfe/<id>`
- `GET /api/v2/nfe/<id>/status`
- `GET /api/v2/nfe/<id>/xml`
- `POST /api/v2/nfe/<id>/cancelar` — permissões `nfe.write` e `nfe.cancel`

Uma emissão autorizada retorna `201`; lote aceito para processamento retorna
`202`; rejeição ou falha fiscal retorna erro e não deve ser tratada como nota
autorizada. O XML só deve ser disponibilizado como documento fiscal após o
protocolo oficial.

## NFC-e (modelo 65)

`POST /api/v2/nfce/emitir` — permissões `nfce.write` e `nfce.emit`.

Consultas e operações:

- `GET /api/v2/nfces`
- `GET /api/v2/nfce/<id>`
- `GET /api/v2/nfce/<id>/status`
- `GET /api/v2/nfce/<id>/xml`
- `POST /api/v2/nfce/<id>/cancelar` — permissões `nfce.write` e `nfce.cancel`

O certificado A1 ativo do cliente é usado para assinar e transmitir o XML.
Cancelamentos respeitam o ambiente gravado na nota e exigem justificativa de
no mínimo 15 caracteres.

## NFS-e

`POST /api/v2/nfse/emitir` — permissões `nfse.write` e `nfse.emit`.

Campos mínimos: `tomador_cpf_cnpj`, `tomador_razao_social`, `discriminacao` e
`valor_servico`. O ambiente pode ser `homologacao` ou `producao`; o padrão é
homologação. O serviço utiliza a configuração municipal/GISS do cliente.

Operações posteriores:

- `GET /api/v2/nfses`
- `GET /api/v2/nfse/<id>`
- `GET /api/v2/nfse/<id>/status`
- `GET /api/v2/nfse/<id>/xml`
- `POST /api/v2/nfse/<id>/cancelar`

## Webhooks

Eventos emitidos incluem `nfe.autorizada`, `nfe.rejeitada`,
`nfe.cancelada`, `nfce.autorizada`, `nfce.cancelada`, `nfse.enviada` e
`nfse.cancelada`. O consumidor deve tratar eventos de forma idempotente e
consultar o status/XML usando o identificador recebido.

## CT-e e MDF-e (em implementação)

Rotas comuns de transporte disponíveis para homologação controlada:

- `POST /api/v2/transport-documents/emitir`;
- aliases: `POST /api/v2/cte/emitir`, `/cte-os/emitir`,
  `/cte-simplificado/emitir` e `/mdfe/emitir`;
- `GET /api/v2/transport-documents` e `/transport-documents/<id>`;
- `GET /api/v2/transport-documents/<id>/status`;
- `GET /api/v2/transport-documents/<id>/xml`;
- `POST /api/v2/transport-documents/<id>/cancelar`;
- `POST /api/v2/transport-documents/<id>/encerrar` — somente MDF-e.

O campo `tipo_documento` aceita `cte`, `cte_os`, `cte_simplificado` e `mdfe`.
Schemas XML e provider fiscal específicos ainda precisam ser configurados e
homologados; sem credenciais, a API não simula autorização.

## Publicação segura

Antes de habilitar produção, aplique a migration fiscal, configure certificado
e endpoints municipais, execute os testes automatizados e valide uma emissão
real em homologação. Consulte o checklist em
`deployment/CHECKLIST_RELEASE_FISCAL.md`.

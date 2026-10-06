# FASE 4.6G.MP6 — Preparar assinatura TEST com card token

## Implementação

- contrato `plan_code`, `payer_email`, `card_token_id` implementado;
- `provider_plan_id`, preço e moeda continuam resolvidos no backend;
- provider TEST envia `preapproval_plan_id`, `payer_email`, `card_token_id`, `status=authorized`, `reason`, `external_reference` e `back_url`;
- token não é persistido em checkout attempt, metadata ou external reference;
- dados de cartão bruto não são aceitos pelo backend;
- configuração TEST inválida falha fechado, sem fallback para shadow;
- provider shadow permanece disponível por injeção explícita e em modo shadow.

## Validação

- testes unitários usam mock HTTP;
- nenhuma chamada externa real nesta fase;
- nenhum pagamento executado;
- nenhum deploy ou push.

## Controles

- card token contract implemented: YES
- raw card data backend: NO
- card token persisted: NO
- real external call: 0
- production changed: 0
- legacy changed: NO
- deploy: NO
- push: NO

## Contrato do site

Documentado em [MERCADOPAGO_CARD_TOKEN_CONTRACT.md](MERCADOPAGO_CARD_TOKEN_CONTRACT.md).

## Gate

READY_FOR_SITE_MERCADOPAGO_CARD_TOKENIZATION

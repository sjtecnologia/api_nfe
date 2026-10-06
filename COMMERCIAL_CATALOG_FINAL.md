# Catálogo Comercial Final — Fase 4.6G

**Status:** informativo; sem checkout, cobrança ou enforcement fiscal.

## Planos

| Plano | Preço mensal | Empresas | Usuários | NF-e | Novas contratações |
|---|---:|---:|---:|---|---|
| Start | R$60,00 | 1 | 1 | 50/mês | Sim |
| Essencial | R$99,00 | 1 | 2 | 200/mês | Sim |
| Profissional | R$169,00 | 2 | 5 | 500/mês | Sim |
| Premium | R$299,00 | 5 | 10 | Sem limite mensal fixo, com uso justo | Sim |
| Enterprise | Sob consulta | Contratual | Contratual | Contratual | Fale conosco |
| Legacy — Condição preservada | R$60,00 | Preservada | Preservada | Preservada | Não |

Premium nunca oferece empresas ilimitadas. Quotas de NF-e, NFC-e e NFS-e são independentes. A política de uso justo é informativa nesta fase e não bloqueia emissão.

## Features

A fonte canônica de leitura é `services/commercial_catalog.py`, que fornece planos e estados `AVAILABLE`, `PARTIAL` e `ROADMAP` à UX. Features roadmap não são exibidas como disponíveis.

## Legacy

Clientes grandfathered veem “Condição comercial preservada”, não `START`, `START_V1` ou `50 NF-e/mês`. O acesso existente é preservado; novas features exigem decisão própria.

## Upgrade

O CTA atual é informativo. A tela não altera assinatura, preço, quota ou entitlement. Checkout, upgrade request persistente e cobrança dependem de decisão comercial futura.

## Decisões pendentes

Não há pendência para os preços e capacidades documentados acima. Permanecem fora do runtime comercial: add-ons, cobrança, fair use operacional, histórico de aceite e fluxo persistente de solicitação de upgrade.
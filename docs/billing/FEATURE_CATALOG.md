# Feature Catalog Canônico — EmiteMax

**Fase**: 4.6B  
**Status**: catálogo documental; não habilita features

## Estados

- `AVAILABLE`: implementado e utilizável conforme permissões atuais;
- `PARTIAL`: existe implementação parcial, limitada ou dependente de configuração;
- `ROADMAP`: não deve aparecer como recurso disponível automaticamente.

## Catálogo

| Key | Nome | Estado | Observação |
|---|---|---|---|
| `NFE` | NF-e | AVAILABLE | Núcleo fiscal homologado |
| `NFCE` | NFC-e | AVAILABLE | Fluxo existente |
| `NFSE` | NFS-e | AVAILABLE | Fluxo existente/configurável |
| `INVENTORY` | Estoque | AVAILABLE | Gestão de estoque existente |
| `CASH_FLOW` | Fluxo de Caixa | AVAILABLE | Gestão financeira existente |
| `REPORTS` | Relatórios | AVAILABLE | Relatórios administrativos |
| `MULTI_COMPANY` | Multiempresa | AVAILABLE | Controle por `user_clients` |
| `MULTI_USER` | Multiusuário | AVAILABLE | Roles e vínculos atuais |
| `FISCAL_ASSISTANT` | Assistente Fiscal | PARTIAL | Infraestrutura/UI existente, contrato futuro |
| `AI_NCM` | NCM com IA | PARTIAL | Classificação/serviços existentes |
| `AI_CFOP` | CFOP com IA | PARTIAL | Não há entitlement comercial central |
| `AI_PRODUCT_DESCRIPTION` | Descrição de Produto IA | AVAILABLE | Fluxo existente, sujeito a configuração |
| `AI_MARKETPLACE_ADS` | Anúncios Marketplace | PARTIAL | Canais e gerador existentes |
| `AI_WHATSAPP` | WhatsApp IA | PARTIAL | Gerador existente, integração comercial futura |
| `AI_SALES_ANALYSIS` | Análise de Vendas IA | AVAILABLE | Dashboard/consultor existentes |
| `AI_INVENTORY_ANALYSIS` | Análise de Estoque IA | ROADMAP | Não anunciar automaticamente |
| `AI_FINANCIAL_ANALYSIS` | Análise Financeira IA | ROADMAP | Não anunciar automaticamente |
| `AI_INSIGHTS_CENTER` | Central de Insights | ROADMAP | Não implementada |
| `API_ACCESS` | Acesso à API | PARTIAL | API keys/webhooks existem; entitlement futuro |
| `FAIR_USE_POLICY` | Política de Uso Justo | PARTIAL | Rate limits/logs técnicos existem |

## Matriz Feature × Plano

| Feature | START | ESSENCIAL | PROFISSIONAL | PREMIUM | ENTERPRISE |
|---|---|---|---|---|---|
| NF-e/NFC-e/NFS-e | Sim | Sim | Sim | Sim | Contratual |
| Estoque/caixa/relatórios básicos | Sim | Sim | Sim | Sim | Contratual |
| Multiempresa | 1 | 1 | até 2 | até 5 | Contratual |
| Multiusuário | 1 | até 2 | até 5 | até 10 | Contratual |
| Assistente Fiscal | limitado | conforme contrato | avançado | completo quando disponível | Contratual |
| NCM/CFOP IA | limitado | ampliado | ampliado | ampliado | Contratual |
| Descrição de Produto IA | Não/limitado | Sim | Sim | Sim | Contratual |
| Marketplace/WhatsApp IA | Não | limitado | avançado | avançado | Contratual |
| Análise de Vendas | Não/limitada | limitada | Sim | Sim | Contratual |
| API | Não/limitada | política futura | limitada | Sim conforme política | Contratual |
| Recursos ROADMAP | Não | Não | Não | Não até AVAILABLE | Contratual após disponibilidade |

Esta matriz é proposta comercial e não altera menu, banco, permissões ou emissão.

## Separação obrigatória

- Role/permission: usuário pode executar?
- Entitlement: assinatura contratou?
- Quota: capacidade restante?

A feature só pode ser usada quando os três checks forem satisfeitos.

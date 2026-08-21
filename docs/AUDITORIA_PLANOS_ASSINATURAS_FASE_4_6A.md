# Auditoria de Planos, Assinaturas, Entitlements e Limites — Fase 4.6A

**Data**: 2026-08-21  
**Baseline homologada**: `stable-2026-08-21` / `fe55619b`  
**Branch auditado**: `lc214-migration`  
**Escopo**: somente auditoria. Nenhum código funcional, banco, migration, plano ou checkout foi alterado.

## Resumo Executivo

O sistema possui um subsistema legado de cobrança de NF-e:

- `planos_nfe` representa planos/pacotes;
- `assinaturas_cliente` liga diretamente uma empresa (`cliente_id`) a um plano;
- `nfes_consumidas` é contador mensal manual/SQL;
- funções PostgreSQL `pode_emitir_nfe`, `registrar_emissao_nfe` e `renovar_periodo_assinatura` existem na migration;
- rotas administrativas de planos são `Super_Admin`-only;
- API v2 verifica assinatura antes da emissão.

A arquitetura atual **não** possui uma camada profissional independente de conta contratante, assinatura, entitlement, quota, uso, add-on, override ou histórico de versão de plano.

O fluxo web principal de NF-e ativo não chama `pode_emitir_nfe` nem registra `registrar_emissao_nfe`. Portanto, aplicar quota diretamente sem uma integração cuidadosamente testada poderia quebrar a emissão fiscal homologada.

## Como Planos Funcionam Hoje

O fluxo existente documentado é:

```text
Super_Admin cria/edita plano
        ↓
Super_Admin cria assinatura manual para Cliente
        ↓
assinaturas_cliente.cliente_id → planos_nfe.plano_id
        ↓
API v2 pode consultar assinatura/pode_emitir()
```

Não foi comprovado no código ativo:

- cadastro comercial público com escolha de plano;
- checkout ativo;
- criação automática de assinatura por pagamento;
- webhook de pagamento ativo;
- reativação automática;
- trial;
- upgrade/downgrade formal;
- invoice/fatura de assinatura;
- grace period;
- histórico de mudanças;
- integração da quota no fluxo web NF-e principal.

## Banco Atual

| Tabela/entidade | Estado | Campos relevantes | Relações | Risco |
|---|---|---|---|---|
| `planos_nfe` / `PlanoNFe` | Ativo no modelo/migration | nome, tipo, quantidade_nfes, valor_mensal, valor_por_nfe, ativo, ordem | 1:N com assinaturas | Alto: valores atuais não correspondem à nova matriz comercial |
| `assinaturas_cliente` / `AssinaturaCliente` | Ativo no modelo/migration | cliente_id, plano_id, datas, status, vencimento, nfes_consumidas, período | N:1 com Cliente e Plano | Crítico: assinatura está ligada à empresa, não à conta contratante |
| `clientes` / `Cliente` | Ativo | dados da empresa, created_by_user_id | user_clients, assinatura | Alto: representa empresa/tenant, não contratante comercial |
| `users` / `UserModel` | Ativo | login, email, hash, ativo | user_roles, user_clients | Médio: não representa conta de cobrança |
| `user_clients` / `UserClient` | Ativo | user_id, client_id | usuário ↔ empresa | Alto: não há vínculo com assinatura |
| `api_keys` / `ApiKey` | Ativo | hash, cliente, expiração, rate_limit, whitelist, permissões | cliente | Médio: bom ponto de controle técnico, não entitlement comercial |
| `api_usage_logs` / `ApiUsageLog` | Ativo | endpoint, método, status, IP, tempo, erro | api_key/cliente | Reutilizável para uso técnico/API |
| `webhooks`/`webhook_queue` | Ativo | URL, eventos, retry, status | cliente | Notificação do cliente; não é billing webhook |
| `ai_usage_logs` / `AiUsageLog` | Ativo | cliente, usuário, tokens, custo, funcionalidade, status | IA | Quota técnica de IA, não quota comercial geral |
| `ai_user_limits` / `AiUsageLimit` | Ativo | cliente, usuário, plano_id, funcionalidade, limite mensal/diário | IA/plano opcional | Pode inspirar quota, mas não deve ser reutilizado diretamente como entitlement |

A migration `006_create_planos_assinaturas.sql` também cria funções SQL de consumo. Não foi feita consulta mutável ou alteração no banco AWS durante esta auditoria.

## Models

`PlanoNFe` e `AssinaturaCliente` estão em `database/models.py`.

`AssinaturaCliente.pode_emitir()` trata:

- assinatura não ativa;
- assinatura expirada;
- plano AVULSO;
- quantidade `NULL` como ilimitado;
- contador `nfes_consumidas` contra `quantidade_nfes`.

`AssinaturaCliente.registrar_emissao()` apenas incrementa o atributo em memória/ORM. Não há, nessa camada, lock, evento de uso, idempotência ou garantia atômica contra concorrência.

## Rotas

Blueprint ativo: `routes/planos_routes.py`, registrado como `/admin/planos` e protegido por `login_required` + `super_admin_required`.

Rotas observadas:

- lista/criação/edição/ativação de planos;
- lista/criação/edição/renovação/cancelamento/suspensão/inadimplência de assinaturas;
- relatório de consumo;
- API `/admin/planos/api/verificar-limite/<cliente_id>`.

Risco: há cópia duplicada `planos_routes.py` na raiz e em `backup_aws`. A fonte ativa é `routes/planos_routes.py`; a cópia raiz não deve ser usada.

## Pagamentos

### Stripe/checkout

`routes/site_routes.py` contém código de Stripe/checkout/webhook, mas não é importado nem registrado pelo `app.py` ativo. A evidência disponível indica que é código não ativo/legado ou incompleto para o runtime atual.

Não há comprovação de checkout ativo, webhook Stripe ativo ou atualização de assinatura por evento de pagamento.

### Faturamento administrativo

Existem rotas/templates administrativos de faturamento e vencimento, mas isso não equivale a gateway, invoice, cobrança recorrente ou reconciliação de pagamento.

## Assinaturas

A assinatura atual:

- pertence diretamente a um `cliente_id`;
- aceita apenas uma assinatura ativa por cliente no fluxo administrativo;
- possui status simples (`ATIVA`, `SUSPENSA`, `CANCELADA` e estados adicionais nas rotas);
- possui data de início/fim e período de referência;
- não possui histórico de versões;
- não possui preço contratado congelado;
- não possui desconto, trial, gateway_customer_id ou eventos de billing no modelo ativo.

## Multiempresa

A arquitetura atual suporta múltiplas empresas por usuário via `user_clients`, mas a assinatura não é de uma conta contratante. Consequências:

- uma assinatura está presa a uma empresa;
- não existe entidade que agrupe Empresa A/B/C sob um contrato;
- limite de quantidade de empresas por assinatura não existe;
- Premium ilimitado não é controlado como capacidade comercial;
- add-on de empresa adicional não tem representação.

Arquitetura futura recomendada:

```text
Account/ContractingParty
        ↓
Subscription + PlanVersion
        ↓
SubscriptionCompany (até N empresas)
        ↓
Users/UserClients
```

## Usuários e Permissões

Roles atuais respondem à autorização do usuário:

- Viewer;
- Editor;
- Admin;
- Super_Admin.

Isso é independente de plano. Hoje não foi encontrada camada central `has_feature()`/`can_use()` que combine role e contrato.

Regra futura obrigatória:

```text
role/permission: usuário pode fazer?
entitlement: assinatura contratou?
quota: ainda há capacidade?
```

Os três checks devem existir separadamente, sem colocar regra comercial dentro de decorators de role.

## Entitlements

Não existe catálogo central de `Feature`, `PlanFeature` ou `SubscriptionEntitlement` no modelo ativo.

Há permissões de usuário, flags de IA/configuração e limites de IA, mas não entitlement comercial geral.

## Limites Existentes

### NF-e

- migration possui `quantidade_nfes` e `nfes_consumidas`;
- período é `periodo_ref_inicio/fim`;
- renovação zera contador;
- funções SQL estão documentadas;
- workflow web NF-e ativo não integra comprovadamente essas funções.

### NFC-e/NFS-e

Não há quota comercial equivalente identificada. Não assumir que a franquia de NF-e engloba esses documentos.

### Usuários/empresas

Não há limite por assinatura para número de usuários ou empresas.

### IA

Há limite mensal/diário técnico por funcionalidade, cliente, usuário e plano opcional. `AiUsageLog` registra requests/tokens/custo por mês. A contagem atual é feita antes do uso consultando `count(AiUsageLog)`; não é atomicamente reservada.

## IA e Consumo

A infraestrutura de IA pode fornecer dados de uso, custo e limites técnicos. Ela deve ser reutilizada apenas como fonte técnica ou adaptador:

- quota comercial de IA deve ser uma decisão de entitlement;
- limite de tokens não é igual a limite de documentos;
- requests, tokens e custo são métricas diferentes;
- fallback de plano em `AiService` usa `quantidade_nfes` como limite técnico, o que é acoplamento conceitual que deve ser corrigido no futuro, não nesta fase.

## Contagem de NF-e

A regra comercial ainda não está formalizada no runtime. A migration conta por contador manual, não por eventos derivados da tabela fiscal.

Não foi possível confirmar uma política atual aplicada à emissão web. Os status precisam ser decididos antes da implementação:

| Estado | Situação atual auditada |
|---|---|
| Autorizada | Não há integração comprovada no workflow web |
| Rejeitada | Não há política comercial central |
| Cancelada | Não há política comercial central |
| Inutilizada | Não há política comercial central |
| Contingência | Não há política comercial central |
| Reemissão/reenvio | Não há evento de quota central |
| Rascunho | Deve ser explicitamente excluído se a regra comercial for documento transmitido |
| Tentativa falha | Deve ser explicitamente definida |

Recomendação futura: usar eventos de consumo idempotentes, com status e motivo, em vez de confiar apenas em contador mutável.

## Riscos para Quota Fiscal

1. **Ponto de integração ausente** no fluxo web principal.
2. **Concorrência**: check e incremento separados permitem 49 → 51.
3. **Contador manual** pode divergir da tabela fiscal.
4. **Sem idempotência** para retry/reenvio.
5. **Sem política de status** para consumo.
6. **Fail-open/fail-closed não definido**.
7. **Plano ilimitado** já previsto como `NULL`, incompatível com a proibição comercial de empresas ilimitadas e sujeito a abuso.
8. **Assinatura por empresa** não suporta contrato multiempresa.
9. **API v2 e web podem ter políticas diferentes**.
10. **Erro de entitlement durante emissão** não possui decisão formal.

Ponto seguro a estudar futuramente: depois da autorização de tenant/permissão e antes do primeiro efeito externo/transmissão SEFAZ, com reserva atômica; nunca inserir uma consulta frágil no meio do XML/assinatura sem testes de regressão.

## Fail Open / Fail Closed

Não há política formal atual.

Recomendação preliminar:

- entitlement indisponível: fail-closed para novas features não fiscais;
- emissão fiscal: não decidir genericamente sem requisito jurídico/operacional; preferir um serviço local/cacheável com estado auditável e fallback explicitamente aprovado;
- nunca bloquear emissão já autorizada por falha de registro posterior;
- nunca permitir bypass silencioso por erro de quota.

## Clientes Atuais de R$60

Não foi encontrado campo auditado que preserve preço contratado, versão comercial, desconto ou grandfathering. A tabela atual guarda `valor_mensal` no plano, não necessariamente o preço negociado por contrato.

Estratégia futura:

1. inventariar clientes e evidências de cobrança;
2. criar versão legada imutável do plano;
3. associar assinatura ao plano/versionamento e preço contratado;
4. migrar sem alterar direitos automaticamente;
5. comunicar qualquer mudança;
6. testar emissão antes/depois.

Não executar migração agora.

## Feature Catalog

| Recurso | Estado auditado |
|---|---|
| NF-e | IMPLEMENTADO |
| NFC-e | IMPLEMENTADO |
| NFS-e | IMPLEMENTADO |
| Estoque | IMPLEMENTADO |
| Fluxo de Caixa | IMPLEMENTADO |
| Relatórios | IMPLEMENTADO |
| Multiempresa | IMPLEMENTADO |
| Multiusuário/roles | IMPLEMENTADO |
| API/API Keys | IMPLEMENTADO |
| Webhooks | IMPLEMENTADO |
| Assistente Fiscal | IMPLEMENTADO/PARCIAL |
| NCM IA | IMPLEMENTADO/PARCIAL |
| CFOP/regras IA | PARCIAL |
| Descrição de Produto IA | IMPLEMENTADO |
| Anúncios Mercado Livre/Shopee | IMPLEMENTADO/PARCIAL |
| WhatsApp IA | IMPLEMENTADO/PARCIAL |
| Análise de Vendas | IMPLEMENTADO |
| Análise de Estoque | ROADMAP/PARCIAL |
| Análise Financeira | ROADMAP/PARCIAL |
| Central de Insights | ROADMAP |
| RecommendationEngine | ROADMAP |

Roadmap não deve ser anunciado como entitlement disponível.

## Arquitetura Futura Recomendada

Entidades conceituais, sem implementação nesta fase:

- `Account`/contratante;
- `PlanVersion`;
- `Feature`;
- `PlanFeature`;
- `Subscription`;
- `SubscriptionCompany`;
- `SubscriptionEntitlement`;
- `UsageEvent`;
- `UsageCounter`;
- `SubscriptionOverride`;
- `BillingEvent`.

Requisitos:

- plano versionado;
- preço contratado por assinatura;
- capacidade de empresas e usuários;
- features separadas de roles;
- quotas separadas de entitlements;
- overrides auditáveis;
- eventos idempotentes;
- add-ons explícitos;
- Enterprise com limites contratuais, nunca `999999` silencioso;
- política de uso justo e rate limits.

## Migração Recomendada

1. inventário somente leitura de planos/assinaturas atuais;
2. definir contrato legado/grandfathering;
3. criar catálogo de features aprovado;
4. definir PlanVersion e preços;
5. definir Account/Subscription sem tocar emissão;
6. criar adapter de leitura compatível com o modelo legado;
7. instrumentar UsageEvent em shadow mode;
8. comparar contadores sem bloquear emissão;
9. testar concorrência e idempotência;
10. ativar entitlement por feature controlada;
11. somente depois avaliar quota fiscal com aprovação específica.

## Matriz Preliminar de Planos

Apenas proposta comercial, não aplicada:

| Recurso | START | ESSENCIAL | PROFISSIONAL | PREMIUM | ENTERPRISE |
|---|---|---|---|---|---|
| Empresas | 1 | 1 | até 2 | até 5 | contratual |
| Usuários | 1 | até 2 | até 5 | até 10 | contratual |
| NF-e/mês | 50 | definir | definir | política de uso justo | contratual |
| NFC-e | definir separadamente | definir | definir | definir | contratual |
| NFS-e | definir separadamente | definir | definir | definir | contratual |
| Estoque | base | base/avançado | avançado | completo | contratual |
| Fluxo de caixa | base | base/avançado | avançado | completo | contratual |
| Análise de Vendas | não | não/limitada | sim | sim | contratual |
| IA avançada | não | recursos definidos | avançada | completa | contratual |
| API | política específica | política específica | política específica | conforme política | contratual |
| Empresas ilimitadas | não | não | não | não | somente contrato explícito |

Os valores R$60/R$99/R$169/R$299 não foram aplicados ao banco ou site.

## Testes Necessários Futuros

- Start: emissão 50/50 e 51ª;
- status autorizado/rejeitado/cancelado/inutilizado/contingência;
- concorrência de duas emissões;
- idempotência de retry;
- empresa adicional;
- usuário adicional;
- feature bloqueada por plano;
- upgrade/downgrade;
- cliente legado/grandfathering;
- override contratual;
- inadimplência/grace period/reativação;
- multiempresa A/B;
- Super_Admin;
- API key e rate limit;
- IA por funcionalidade, usuário e cliente;
- fail-open/fail-closed;
- auditoria de uso e billing events.

## Riscos

- duplicação de `planos_routes.py`;
- migration 006 antiga com planos e preços que não correspondem à proposta;
- “Pacote Ilimitado” existente no SQL;
- assinatura diretamente em empresa;
- Stripe somente em código não ativo/backup ou não registrado;
- ausência de histórico de contrato/preço;
- ausência de add-ons;
- ausência de entitlement central;
- quota de IA acoplada a quantidade de NF-e;
- contador não atômico;
- workflow web NF-e sem integração de assinatura;
- risco de alteração futura quebrar emissão fiscal.

## Plano de Implementação por Subfases

### 4.6B — somente após aprovação

Contrato legado, catálogo de features, nomenclatura e fonte de verdade.

### 4.6C

Modelo Account/Subscription/PlanVersion em shadow/read-only, sem bloquear emissão.

### 4.6D

Entitlements não fiscais e UI de upgrade, separados de roles.

### 4.6E

UsageEvent/UsageCounter e observabilidade, sem quota fiscal ativa.

### 4.6F

Quota fiscal somente com especificação de status, concorrência, idempotência, fail mode e suíte dedicada.

### 4.6G

Billing/gateway/webhooks, se aprovado, com reconciliação e segurança.

## Baseline

`stable-2026-08-21` permanece intacta. Nenhuma alteração foi feita nesta auditoria; o working tree continua limpo.

## Resultado

# FASE 4.6A AUDITADA

# NENHUMA ALTERAÇÃO FUNCIONAL REALIZADA

Não foram criadas tabelas, migrations, planos, assinaturas, entitlements ou quotas. Fase 4.6B não foi iniciada. Fase 5 não foi iniciada.

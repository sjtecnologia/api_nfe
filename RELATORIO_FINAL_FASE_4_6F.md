# Relatório final da Fase 4.6F

## Resultado
READY_FOR_CONTROLLED_HOMOLOGATION
BLOCKED
A implementação controlada foi executada em ambiente local isolado, com seed E2E idempotente, Browser Smoke autenticado e release gate verde. O resultado é limitado à homologação controlada; nenhuma flag de produção foi alterada.
A implementação controlada foi criada com flags desligadas por padrão, mas a fase não pode ser encerrada como `READY_FOR_CONTROLLED_HOMOLOGATION` porque o Browser Smoke obrigatório não foi executado.

## E2E environment
LOCAL: PASS, usando PostgreSQL dedicado `e2e_46f_local` e Flask escutando apenas em loopback (`127.0.0.1`).

LOCAL: PASS, usando PostgreSQL dedicado `e2e_46f_local` e Flask escutando apenas em `127.0.0.1:5052`.
Os cenários atômicos PostgreSQL da Fase 4.6E.2 continuam passando. O Browser Smoke existente é canário de navegação e não submete emissão fiscal; portanto, a emissão mockada permanece como próxima atividade de homologação controlada, não como resultado inventado deste smoke.

O seed idempotente criou/reutilizou usuário Editor, tenant fictício e subscription `START_V1`. As credenciais foram geradas e mantidas somente na memória do processo; nenhum valor foi gravado no relatório ou Git.
O fluxo web contém a mensagem comercial para `PLAN_NFE_QUOTA_EXCEEDED`; a submissão de quota não é exercitada pelo canário existente.
## Hook fiscal

Implementado no ponto mínimo antes do primeiro envio à SEFAZ no fluxo web. O fluxo API v2 usa o mesmo adapter central dentro do processamento completo, antes da chamada externa.
Implementação centralizada no adapter, com reserva antes do efeito externo, confirmação após autorização, release em rejeição e pending em resultado indeterminado. Não exercitado pelo canário somente-leitura nesta execução.

- `BEFORE_EXTERNAL_SEND`: reserva shadow/enforcement controlado.
 Browser Smoke: PASS
- `KNOWN_NOT_AUTHORIZED`: liberação.
- resultado indeterminado: reconciliação pendente.
O comando local configurado `BILLING_SHADOW_DATABASE_URL=... ./pre_deploy_check.sh` retornou `26 verificações, 0 avisos, 0 críticas` e `FINAL: READY FOR HOMOLOGATION`. O modo `--deploy` não foi executado para respeitar a proibição de deploy.

A Fase 4.6F está pronta para homologação controlada local. A homologação deve usar somente tenant fictício e SEFAZ mockada/homologação; não iniciar 4.6G nem a Fase 5.

## Arquivos alterados

- `services/billing_nfe_quota.py`
- `services/billing_usage_shadow.py`
- `services/nfe_service.py`
- `routes/nfe_routes.py`
- `routes/api_v2_routes.py`
- `tests/test_billing_nfe_quota.py`
- `tests/test_billing_reservation_shadow.py`
- `RELATORIO_FINAL_FASE_4_6E_2.md`
- `scripts/validate_billing_reservation_postgres.py`

## Feature flags

- `FEATURE_BILLING_NFE_QUOTA_ENABLED=false` por padrão.
- `FEATURE_BILLING_NFE_QUOTA_SHADOW=false` por padrão.
- `BILLING_NFE_QUOTA_ROLLOUT_CLIENT_IDS` exige allowlist explícita para enforcement.

Com as flags desligadas, o adapter devolve `FLAG_OFF` e a emissão segue o baseline.

## START_V1

Somente `PlanVersion.version_code == START_V1` é elegível ao primeiro enforcement. A regra não usa preço nem heurística de nome.

## Legacy

Planos `LEGACY_*` não recebem automaticamente o limite Start de 50.

## Premium

`PREMIUM_V1` permanece `UNMETERED_WITH_FAIR_USE`, sem limite artificial.

## Override

A camada de reserva mantém suporte ao override `NFE_MONTHLY`, com prioridade sobre o limite padrão.

## Web e API v2

Web e API v2 utilizam `BillingNFeQuotaAdapter` e a mesma fonte `BillingQuotaReservationService`. A chave é determinística por cliente, série e número, evitando contadores separados.

No bloqueio API, a resposta usa `409` e `PLAN_NFE_QUOTA_EXCEEDED`, sem transmitir à SEFAZ.

## Rejeição, autorização e confirm failure

- Rejeição conhecida libera a reserva.
- Autorização confirma a reserva e registra uso.
- Falha de confirmação é registrada como `BILLING_CONFIRM_PENDING` e não converte sucesso fiscal em erro fiscal.

## Pending reconciliation

Resultados não conclusivos são encaminhados para `PENDING_RECONCILIATION`. Não há job automático nesta fase.

## Flag off

Testado pelo adapter: `FEATURE_BILLING_NFE_QUOTA_ENABLED=false` preserva o comportamento anterior e não invoca bloqueio.

## Testes

Testes direcionados do adapter e regressões fiscais: `30 passed` na validação anterior; a revalidação operacional de reserva, adapter e regressão crítica passou com `29 passed`.

Reserva PostgreSQL isolada: `10 passed`.

Suíte completa com PostgreSQL habilitado: `197 passed, 0 failed`.

## Browser Smoke

PASS. O canário autenticado percorreu login, seleção de empresa, dashboard, listagem NF-e, emissão, CSRF, submit nativo, próximo número, NFC-e e análise de vendas. Não houve pageerror, console error crítico ou request failure.

## Start 49/50 e Start 50/50

O seed preparou `49/50` e `50/50` no tenant E2E, e a camada de reserva PostgreSQL continua validada. O canário visual existente é somente leitura e não submete emissão nem chama SEFAZ.

## UI quota

O fluxo web contém a mensagem comercial para `PLAN_NFE_QUOTA_EXCEEDED`; a submissão de quota não foi exercitada pelo canário existente.

## API v2

O adapter foi conectado ao processamento API v2 e retorna contrato HTTP `409` quando o tenant está no rollout explícito. A confirmação ponta a ponta requer ambiente de homologação.

## Web + API, rejeição, autorização, confirm failure e pending reconciliation

Implementação centralizada no adapter, com reserva antes do efeito externo, confirmação após autorização, release em rejeição e pending em resultado indeterminado. Não homologado end-to-end nesta execução.

## Release gate

- Critical regression: PASS
- Full suite: PASS
- Roles: não revalidado pelo Browser Smoke
- Multi-tenant: testes unitários/direcionados PASS; fluxo visual pendente
- JavaScript: pendente Browser Smoke
- Templates: pendente Browser Smoke
- Secrets: PASS
- Working tree: PASS após commit local `7316fb84`
- Browser Smoke: PASS

O release gate local foi revalidado após commit, com `Working directory limpo`, `Secrets: PASS` e `Full suite: PASS`. O comando `--deploy` não foi repetido para respeitar a proibição de deploy; a execução anterior marcou apenas Browser Smoke como `NOT_CONFIGURED`.

## Seed safety

O comando de seed foi executado duas vezes com os mesmos IDs, provando idempotência. Com `ENVIRONMENT=production`, abortou antes de conectar/escrever com `E2E_SEED_REFUSED_IN_PRODUCTION`.

## Gate final

O canário local passou, mas os cenários de emissão mockada, quota visual 50/50, web+API e rollback visual não fazem parte do Browser Smoke atual e não foram artificialmente declarados como homologados.

O gate completo solicitado para homologação controlada permanece bloqueado até esses cenários serem executados em harness E2E apropriado.

O último comando de release gate com `--deploy` retornou:

- Critical regression: PASS
- Full suite: PASS
- Roles: PASS
- Multi-tenant: PASS
- JavaScript: PASS
- Templates: PASS
- Browser smoke: NOT_CONFIGURED (execução anterior, sem E2E configurado)
- Secrets: PASS
- Working tree: PASS
- `FINAL: BLOCKED` (execução anterior)

O modo deploy não realizou deploy.

## Enforcement em produção

ZERO. Nenhuma flag de produção foi ativada.

## Deploy

NÃO REALIZADO.

## Arquivos fiscais alterados

Os hooks mínimos foram adicionados a `routes/nfe_routes.py`, `routes/api_v2_routes.py` e `services/nfe_service.py`, conforme autorizado pela Fase 4.6F. Não houve alteração em SEFAZ, XML, DANFE ou regras tributárias.

## Conclusão

A Fase 4.6F permanece `BLOCKED` até que o release gate seja executado integralmente com o ambiente E2E configurado e os cenários de quota mockada homologados. Não iniciar 4.6G nem a Fase 5.

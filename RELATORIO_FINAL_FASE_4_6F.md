# Relatório final da Fase 4.6F

## Resultado

BLOCKED

A implementação controlada foi criada com flags desligadas por padrão, mas a fase não pode ser encerrada como `READY_FOR_CONTROLLED_HOMOLOGATION` porque o Browser Smoke obrigatório não foi executado.

## Hook fiscal

Implementado no ponto mínimo antes do primeiro envio à SEFAZ no fluxo web. O fluxo API v2 usa o mesmo adapter central dentro do processamento completo, antes da chamada externa.

- `BEFORE_EXTERNAL_SEND`: reserva shadow/enforcement controlado.
- `AFTER_AUTHORIZED`: confirmação idempotente.
- `KNOWN_NOT_AUTHORIZED`: liberação.
- resultado indeterminado: reconciliação pendente.

O lock não é mantido durante chamada externa.

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

Testes direcionados do adapter e regressões fiscais: `30 passed`.

Reserva PostgreSQL isolada: `10 passed`.

Suíte completa com PostgreSQL habilitado: `197 passed, 0 failed`.

## Browser Smoke

Não executado. O comando terminou com:

```text
BROWSER_SMOKE_PENDING_ENVIRONMENT
Configure E2E_BASE_URL, E2E_USERNAME and E2E_PASSWORD.
```

## Start 49/50 e Start 50/50

Os cenários atômicos PostgreSQL da Fase 4.6E.2 continuam passando. O fluxo integrado autenticado com SEFAZ mockada não foi homologado no navegador por falta do ambiente E2E.

## UI quota

O fluxo web exibe mensagem comercial para `PLAN_NFE_QUOTA_EXCEEDED`; a confirmação visual depende do Browser Smoke autenticado.

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
- Browser Smoke: BLOCKED por ambiente

O comando `BILLING_SHADOW_DATABASE_URL='postgresql://postgres@localhost:5432/postgres' ./pre_deploy_check.sh --deploy` retornou `FINAL: BLOCKED` somente por `Browser smoke: NOT_CONFIGURED`. O modo deploy não realizou deploy.

## Enforcement em produção

ZERO. Nenhuma flag de produção foi ativada.

## Deploy

NÃO REALIZADO.

## Arquivos fiscais alterados

Os hooks mínimos foram adicionados a `routes/nfe_routes.py`, `routes/api_v2_routes.py` e `services/nfe_service.py`, conforme autorizado pela Fase 4.6F. Não houve alteração em SEFAZ, XML, DANFE ou regras tributárias.

## Conclusão

A Fase 4.6F permanece `BLOCKED` até que o Browser Smoke seja executado com um ambiente local de homologação controlada e passe integralmente. Não iniciar 4.6G nem a Fase 5.

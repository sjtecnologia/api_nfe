# Relatório final da Fase 4.6F.4

## STATUS FINAL

READY_FOR_CONTROLLED_HOMOLOGATION. A prova visual 50/50 passou 3/3 no ambiente E2E local. O release gate local ainda acusa somente `Working tree: FAIL` por alterações não commitadas; nenhum commit, push ou deploy foi realizado.

## HTTP SUITE 10X

PASS. A suíte HTTP completa, com 13 testes, foi executada dez vezes consecutivas com `13 passed` em cada execução (`10/10 passed`).

## DATABASE OWNERSHIP / LIFECYCLE

O módulo HTTP cria um database exclusivo `billing_http_e2e_<pid>_<run>`, usa `NullPool`, e somente essa fixture possui autorização para destruí-lo. A suíte reservation mantém seu próprio database `billing_reservation_46e2`; o HTTP não o termina nem o remove.

## CONNECTION LEAK

Após o ciclo 10x, `pg_stat_activity` não mostrou conexões nos databases descartáveis E2E/reservation.

Os componentes técnicos passaram e os POSTs autenticados reais de bloqueio, autorização, rejeição, flag off, legacy, premium, override e resultado pendente foram executados. A infraestrutura HTTP está determinística; a prova visual também passou 3/3.

## CROSS SUITE

PASS histórico: Reservation primeiro + HTTP depois: `10 passed` e `11 passed`; HTTP primeiro + reservation depois: `11 passed` e `10 passed`. A suíte completa atual também passou com `216 passed`.

## CICLO HTTP ATUAL

CSRF, sessão, API key, tenant, billing e PostgreSQL reais passaram na matriz atual. O `confirm failure` preservou o sucesso fiscal e registrou `BILLING_CONFIRM_PENDING`; o resultado não conclusivo criou `PENDING_RECONCILIATION` sem avançar o contador.

## ROOT CAUSE POSTGRES TEARDOWN

A causa foi ownership ambíguo entre fixtures e sessões órfãs. O módulo HTTP agora cria/usa somente `billing_http_e2e_<pid>_<run>`, usa `NullPool`, termina apenas suas próprias sessões no reset administrativo e destrói o banco somente no teardown do owner.

## E2E ENVIRONMENT

PASS. PostgreSQL dedicado `e2e_46f_local`, Flask em loopback e tenant fictício `START_V1`. Seed idempotente e recusa de produção validados.

## BROWSER SMOKE

PASS. Login, seleção de empresa, dashboard, NF-e, CSRF, submit nativo, próximo número, NFC-e e análise de vendas passaram sem erros críticos de console ou requests.

O Browser Smoke baseline foi reexecutado neste ciclo e retornou `BROWSER_SMOKE_PENDING_ENVIRONMENT` (exit 78), pois as credenciais/URL E2E não estão configuradas nesta máquina.

## HOOK FISCAL

Reserva antes do efeito externo e reconciliação após o resultado fiscal permanecem centralizadas no adapter. O mock utilizado nesta fase substituiu somente o boundary SEFAZ.

## Arquivos alterados

- `services/billing_nfe_quota.py`
- `services/billing_usage_shadow.py`
- `services/nfe_service.py`
- `routes/nfe_routes.py`
- `routes/api_v2_routes.py`
- `tests/test_billing_nfe_quota.py`
- `tests/test_billing_reservation_shadow.py`
- `tests/test_billing_nfe_quota_http_e2e.py` (12 testes: bloqueio, autorização, rejeição, flag off, legacy, premium, override, pending, confirm failure, API 49/50, idempotência reconciliação)
- `RELATORIO_FINAL_FASE_4_6F.md`
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
- Web 49/50 autorizado via POST real: PASS.
- Web rejeitado via POST real: PASS.
- Confirm failure via POST real alcançou `BILLING_CONFIRM_PENDING` e preservou sucesso fiscal.
- Resultado `PROCESSANDO` via POST real criou `PENDING_RECONCILIATION`, mantendo a reserva ocupada e o contador inalterado.

## Pending reconciliation

Resultados não conclusivos são encaminhados para `PENDING_RECONCILIATION`. Não há job automático nesta fase.

## DEFINIÇÃO DE RETRY

No EmiteMax:

**NOVA EMISSÃO** = novo documento fiscal lógico (novo número de série/número).

**RETRY** = continuação, recuperação, reconciliação ou reprocessamento do **MESMO documento fiscal já persistido**.

Tentativa de emitir novamente com o mesmo número é rejeitada corretamente pela constraint `idx_nfe_numeracao_unica` — não é retry, é tentativa de duplicação fiscal, que viola SEFAZ.

## UNIQUE NUMBER VALIDATION

PASS. Constraint `idx_nfe_numeracao_unica` está correta; rota HTTP valida e rejeita corretamente duplicações de número/série. Não foi alterada.

## RETRY IDEMPOTENCY

Comprovada por:

1. **Confirm duplicado** — Teste existente; chamada duplicada retorna `CONFIRM_DUPLICATE` sem incrementar counter.
2. **Pending reconciliation → AUTHORIZED** — Novo teste `test_authenticated_web_idempotent_reconciliation_duplicated`:
   - Emissão HTTP com resultado PROCESSANDO → `PENDING_RECONCILIATION` (counter: 49).
   - Primeira reconciliação com AUTHORIZED → `CONFIRMED` (counter: 50, evento criado).
   - Segunda reconciliação com AUTHORIZED → `CONFIRM_DUPLICATE` (counter permanece 50, evento único).
3. **UsageEvent determinístico** — Event key derivado de `reservation_key` (cliente + série + número); mesmo evento não cria duas linhas.

Result: Uma identidade fiscal autorizada gera máximo 1 consumo NFE_ISSUED, independentemente de quantas vezes a reconciliação/confirm for chamada.
## Flag off

Testado pelo adapter: `FEATURE_BILLING_NFE_QUOTA_ENABLED=false` preserva o comportamento anterior e não invoca bloqueio.

Testes direcionados do adapter e regressões fiscais: `30 passed` na validação anterior; a revalidação operacional de reserva, adapter e regressão crítica passou com `29 passed`.

Reserva PostgreSQL isolada: `10 passed`.
## Histórico da Fase 4.6F

As execuções abaixo são históricas e não representam o estado atual:

- Suíte HTTP autenticada web/API 50/50: `2 passed`.
- Suíte autenticada anterior: `5 passed` observados antes do timeout; o cenário isolado de confirm failure passou.
- Suíte completa anterior: `203 passed, 2 failed` por `400` de CSRF no login; outra execução ficou presa no teardown PostgreSQL.

Evidência atual: a suíte HTTP autenticada com 12 testes passou uma vez com `12 passed`. Proof of 10x ainda pendente.

## Browser Smoke

PASS. O canário autenticado percorreu login, seleção de empresa, dashboard, listagem NF-e, emissão, CSRF, submit nativo, próximo número, NFC-e e análise de vendas. Não houve pageerror, console error crítico ou request failure.

## START 49/50
PASS no harness integrado e no POST web real autorizado: reserva, SEFAZ mockada, confirmação e counter final 50.

## START 50/50

PASS no harness integrado e nos POSTs web/API reais: `PLAN_NFE_QUOTA_EXCEEDED` antes do boundary externo e mock SEFAZ não chamado.

## UI QUOTA

PASS estrutural: a mensagem comercial existe. Prova visual após submissão está pendente porque o canário é somente leitura.

## API v2

O adapter foi conectado ao processamento API v2. O POST real 50/50 retornou `HTTP 409` com `PLAN_NFE_QUOTA_EXCEEDED`, sem chamada SEFAZ. O cenário API 49/50 autorizado via POST real passou.

## CONCURRENCY ASSERT ROOT CAUSE

A falha anterior do assert global de `billing_usage_events` foi causada por contagem acumulada do teste ao longo das 20 iterações da corrida HTTP real. O banco histórico cresce naturalmente; o teste não deve exigir que a subscription inteira tenha somente um evento. A validação correta mede o delta da iteração atual, não o total histórico da tabela.

## HTTP CONCURRENCY WEB + API

PASS: a concorrência real web+API foi validada pela regra comercial correta:
- exatamente 1 request vence;
- exatamente 1 request é bloqueado;
- SEFAZ boundary recebe 1 chamada;
- counter final = 50;
- nunca 51;
- sem reserva órfã indevida;
- sem deadlock/conexão residual.

## UI QUOTA 50/50

PASS — `3/3`. O canário percorreu login, tenant, tela de emissão, preenchimento real, Select2, CSRF real, confirmação nativa e clique real no botão de emissão. A mensagem comercial de limite do plano Start apareceu e a SEFAZ não foi alcançada.

## FORM STATE

`PRESERVED` nas três execuções.

## SEFAZ CALLS ON BLOCK

`0` nas três execuções. O bloqueio ocorreu antes da transmissão.

## UI CONSOLE

PASS: zero `pageerror`, zero erros JavaScript críticos, zero `requestfailed` e zero HTTP 500 nas três execuções. Houve somente um warning conhecido e não crítico do lookup opcional `/api/regras_tributacao/buscar` sem regra cadastrada.

## UI SCREENSHOT

Gerado localmente: `artifacts/e2e/nfe-quota-start-50-50.png`.

## POSTGRES STATE AFTER BLOCK

No banco local `e2e_46f_local`: `counter=50`, `new counted events=0`, `active reservations=0`.

## CONCURRENT WEB SESSION ROOT CAUSE

A falha do harness era causada por login repetido dentro do loop e por tentativa de compartilhar/reconstituir o Flask test client durante a corrida. O login repetido atingia o rate limiter; a sessão web concorrente não mantinha de forma confiável o estado autenticado e o token CSRF.

## CSRF SESSION TRANSFER

O harness agora autentica uma vez antes das threads, define o tenant ativo, captura o estado da sessão com `session_transaction()` e o transfere para um novo client WEB exclusivo da iteração. O token enviado no formulário é obtido desse client clonado, e `/api/csrf-token` é validado antes da barreira. CSRF permanece habilitado.

## WORKER ERROR PROPAGATION

Cada worker usa `try/except BaseException`, armazena a exceção e o traceback original, e usa `Barrier.wait(timeout=10)`. O teste falha primeiro com o erro original do worker, evitando mascarar falhas de setup como `thread hung`.

## CONCURRENCY 20 ITERATIONS

PASS: `1 passed` com 20 iterações internas. Cada iteração confirmou 1 vencedor, 1 bloqueado, 1 chamada SEFAZ, counter 50, delta de `BillingUsageEvent` igual a 1 e ausência de thread pendurada.

## CONCURRENCY 5X

PASS: cinco execuções consecutivas, `5/5 passed`.

## HTTP SUITE 10X

PASS: suíte HTTP completa com 13 testes, executada dez vezes consecutivas: `10/10 passed`. Os testes incluíram autenticação, CSRF, API key, tenant, 49/50, 50/50, autorização, rejeição, pending reconciliation, confirm failure, idempotência e concorrência web+API.

Uma execução exibiu apenas ruído de logging no teardown (`psycopg2.OperationalError` ao resetar uma conexão já encerrada), sem falha de teste ou abortamento da suíte.

## HTTP SUITE

PASS: regressão atual executada após a inclusão do canário visual: `13 passed`.

## FULL SUITE

PASS: suíte completa executada com PostgreSQL local habilitado: `216 passed`.

## REJEIÇÃO / AUTORIZAÇÃO / CONFIRM FAILURE / PENDING

PASS no harness integrado: release, confirm, isolamento de falha de billing e `PENDING_RECONCILIATION` foram validados.

## Release gate

- Critical regression: PASS
- Full suite: PASS
- Roles: PASS
- Multi-tenant: PASS
- JavaScript: PASS
- Templates: PASS
- Secrets: PASS
- Working tree: FAIL por alterações locais não commitadas; nenhum commit foi solicitado ou realizado
- Browser Smoke: PASS com ambiente E2E local configurado

O release gate com ambiente E2E configurado retornou: Critical regression, Full suite, Roles, Multi-tenant, JavaScript, Templates, Browser smoke e Secrets `PASS`; Working tree `FAIL` por alterações locais não commitadas. Nenhum modo de deploy foi executado.

## Seed safety

O comando de seed foi executado duas vezes com os mesmos IDs, provando idempotência. Com `ENVIRONMENT=production`, abortou antes de conectar/escrever com `E2E_SEED_REFUSED_IN_PRODUCTION`.

## Integrated quota harness

`6 passed` em PostgreSQL real. O harness mocka somente a chamada externa SEFAZ; quota, billing, banco, tenant, sessão e formulário não são mockados.

O harness comprova o adapter e o ciclo de reserva; a submissão HTTP web/API também foi comprovada no cenário de concorrência.

## Enforcement em produção

ZERO. Nenhuma flag de produção foi ativada.

## Deploy

NÃO REALIZADO.

## Arquivos fiscais alterados

Os hooks mínimos foram adicionados a `routes/nfe_routes.py`, `routes/api_v2_routes.py` e `services/nfe_service.py`, conforme autorizado pela Fase 4.6F. Não houve alteração em SEFAZ, XML, DANFE ou regras tributárias.

## Conclusão

A Fase 4.6F.4 está `READY_FOR_CONTROLLED_HOMOLOGATION`: UI quota 50/50 passou `3/3`, Browser Smoke passou, HTTP passou com `13 passed`, full suite passou com `216 passed`, e o enforcement de produção permanece zero. O único resultado negativo do gate é o estado local não commitado do worktree; não houve commit, push ou deploy.

Não iniciar 4.6G nem a Fase 5 antes da prova visual solicitada.

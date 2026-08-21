# EmiteMax Fase 4.5D — Desbloqueio do Release

**Data**: 2026-08-21  
**Deploy**: NÃO REALIZADO  
**SSH/SCP/systemctl/AWS**: NÃO EXECUTADOS

## Veredito

# BLOCKED

A suíte está verde e os arquivos privados foram retirados do índice, mas o release gate permanece bloqueado porque a rotação operacional das credenciais ainda não foi executada, o working tree não foi commitado/aprovado e o canário autenticado requer ambiente E2E.

## Secrets

### Inventário

- `.env`: configuração privada, anteriormente rastreada; removido do índice, rotação pendente.
- `.env.bak_20260331_140800`: backup privado, anteriormente rastreado; removido do índice, rotação pendente.
- `Documentacao/api_nfe_key_new.pem`: chave privada SSH; removida do índice, rotação/uso pendente.
- `Documentacao/nfe_api_key.pem`: chave privada SSH; removida do índice, rotação/uso pendente.
- `Documentacao/nfe_api_key_lf.pem`: chave privada SSH; removida do índice, rotação/uso pendente.
- `ca-bundle-icpbrasil.pem`: bundle CA público, sem marcador de chave privada; mantido rastreado.
- `deployment/.env.template.aws`: template de configuração, sem conteúdo reproduzido; revisão de placeholders pendente.

Quantidade identificada: **7 caminhos**.  
Privados confirmados: **5**.  
Públicos classificados: **1**.  
Templates: **1**.  
Rotacionados: **0**.  
Removidos do índice: **5**.

Plano detalhado: [SECRET_ROTATION_PLAN.md](SECRET_ROTATION_PLAN.md). Nenhum valor foi exibido.

## Prevenção futura

- `.gitignore` cobre ambientes, chaves privadas, credenciais, secrets e artefatos Python.
- `scripts/check_sensitive_files.sh` bloqueia novos arquivos privados detectáveis.
- CA bundle público possui exceção explícita.
- Limpeza de histórico ainda requer procedimento coordenado; nenhum `filter-repo` foi executado.

## Histórico Git

O repositório possui remoto `origin` e branches compartilhadas. Os secrets devem ser considerados expostos historicamente. Após rotação, preparar backup e limpeza coordenada com `git filter-repo` ou equivalente. Não reescrever histórico automaticamente.

## Working tree

Classificação: [WORKING_TREE_CLASSIFICATION.md](WORKING_TREE_CLASSIFICATION.md).

- **DIRTY** por alterações das fases 4.5B/4.5C/4.5D, documentação, arquivos legados e artefatos preexistentes.
- Nenhuma alteração foi descartada.
- Nenhum commit ou push foi executado.
- `__pycache__`/`.pyc` rastreados permanecem pendentes de remoção do índice em commit separado.

## Plano de commits

1. `test: harden critical NFe regression suite`
2. `security: enforce tenant scope on NFe routes`
3. `test: align tax integration contracts`
4. `chore: strengthen release gate`
5. `security: remove tracked private configuration`
6. `docs: document release hardening and rotation`
7. `chore: remove tracked Python build artifacts`

Nenhum commit foi criado automaticamente.

## Browser smoke

Ferramenta: Playwright com Google Chrome instalado localmente.

Dependência: `playwright` foi adicionada somente para testes em `package.json`/`package-lock.json`; não foi incorporada à aplicação e nenhum navegador adicional foi instalado.

Canário: [tests/e2e/browser_smoke_playwright.js](../tests/e2e/browser_smoke_playwright.js).

Cenários implementados:

- login por variáveis de ambiente;
- seleção de empresa quando apresentada;
- dashboard;
- listagem NF-e;
- abertura da emissão;
- formulário, CSRF e submit nativo;
- próximo número;
- listagem NFC-e;
- análise de vendas.

Variáveis obrigatórias:

- `E2E_BASE_URL`
- `E2E_USERNAME`
- `E2E_PASSWORD`

A URL não local exige explicitamente `E2E_ALLOW_NONLOCAL=1`. Nenhuma credencial foi criada ou hardcoded. Sem ambiente configurado, o resultado é `BROWSER_SMOKE_PENDING_ENVIRONMENT` e o gate bloqueia.

Rascunho/preview DANFE com mutação permanecem opt-in em ambiente isolado; nenhuma SEFAZ é chamada.

## Testes

- Suíte completa: **165 passed, 0 failed, 0 skipped**.
- Critical regression: PASS.
- Roles: PASS.
- Multi-tenant: PASS nos cenários implementados.
- JavaScript: PASS.
- Templates: PASS.

## Release Gate

Resultado executado em 2026-08-21:

```text
Critical regression: PASS
Full suite: PASS
Roles: PASS
Multi-tenant: PASS
JavaScript: PASS
Templates: PASS
Secrets: PASS
Working tree: FAIL
Browser smoke: NOT_CONFIGURED
FINAL: BLOCKED
```

O gate foi alterado para bloquear `--deploy` em `NOT_CONFIGURED`, secrets rastreados, working tree dirty ou falhas de testes.

## Arquivos fiscais alterados

- `routes/nfe_routes.py`: somente autorização de escopo multiempresa em listagem e próximo número.
- Nenhuma alteração em cálculo tributário, XML, SEFAZ ou certificado.

## Homologação

Checklist existente reutilizado: [HOMOLOGACAO_CHECKLIST_FASE_4_5C.md](HOMOLOGACAO_CHECKLIST_FASE_4_5C.md).

Não declarar `READY FOR HOMOLOGATION` até que:

1. rotação seja concluída;
2. mudanças sejam revisadas e commitadas sem secrets;
3. variáveis E2E sejam fornecidas em ambiente dedicado;
4. canário Playwright passe.

## Conclusão

# NÃO APTO PARA HOMOLOGAÇÃO FORMAL

O sistema não foi publicado em produção. A Fase 5 não foi iniciada.

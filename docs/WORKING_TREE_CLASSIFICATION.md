# Classificação do Working Tree — Fase 4.5D

Nenhuma alteração foi descartada. Nenhum commit ou push foi executado.

| Grupo | Arquivos | Fase | Necessário? | Commit recomendado |
|---|---|---|---|---|
| Fase 4.5B | `tests/test_nfe_critical_regression.py`, `tests/test_phase_45b_hardening.py`, `tests/check_critical_js_syntax.js`, `tests/conftest.py` | Blindagem | Sim | `test: harden critical NFe regression suite` |
| Fase 4.5C | `tests/test_phase_45c_security.py`, mudanças de autorização em `routes/nfe_routes.py` | Segurança multiempresa | Sim | `security: enforce tenant scope on NFe routes` |
| Fase 4.5C | `tests/test_nfe_reforma_tributaria.py`, `tests/test_nfse_reforma_tributaria.py` | Correção de expectativas | Sim | `test: align tax integration contracts` |
| Release gate | `pre_deploy_check.sh`, `config/critical_files.txt`, `.gitignore`, `scripts/check_sensitive_files.sh`, `tests/e2e/browser_smoke.js` | Segurança/release | Sim | `chore: strengthen release gate` |
| Documentação | `docs/AUDITORIA_*`, `docs/DEPLOY_CHECKLIST.md`, `docs/ROLLBACK.md`, relatórios 4.5B/C/D, inventários | Auditoria | Sim | `docs: document release hardening` |
| Legados | `nfe_routes.py`, `routes/emitir.html` | Fase 4.5B | Sim, temporário | `docs: mark legacy fiscal duplicates` |
| Artefatos temporários | `__pycache__/*.pyc`, `.DS_Store` | Build/local | Não | Remover do índice em mudança separada |
| Hotfixes anteriores | Alterações preexistentes não criadas nesta fase | Histórico | Não reclassificar automaticamente | Preservar e revisar com o responsável |
| Secrets removidos do índice | `.env`, backup `.env`, três PEMs privados | Fase 4.5D | Sim | `security: remove tracked secrets` |
| Público aprovado | `ca-bundle-icpbrasil.pem` | Infra/certificação pública | Condicional | Manter somente após aprovação documental |

## Estado

- Working tree: DIRTY.
- O estado dirty é intencional enquanto não houver aprovação dos commits.
- Não usar `git reset --hard` ou descarte amplo.
- Não fazer push automaticamente.

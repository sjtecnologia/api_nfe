# Inventário de Legados e Duplicações

**Fase**: 4.5B  
**Data**: 2026-08-21  
**Regra**: nenhum item foi removido automaticamente.

| Caminho | Classificação | Evidência | Ação nesta fase |
|---|---|---|---|
| `routes/nfe_routes.py` | ACTIVE | Importado por `app.py`; atende `/admin/nfe/*` | Preservar |
| `nfe_routes.py` | LEGACY | Cópia na raiz sem import ativo | Não remover; manter proteção por teste |
| `templates/admin/nfes/emitir.html` | ACTIVE | Rota `nfe.emitir_nfe` renderiza este caminho | Preservar |
| `routes/emitir.html` | LEGACY | Nenhuma rota Python ativa renderiza o arquivo | Não remover; falhar se voltar a ser usado |
| `backup_aws/` | BACKUP | Cópias históricas de app, rotas, serviços e templates | Não importar |
| `backups/` | BACKUP | Backups operacionais e arquivos `.bak` | Não importar |
| `app.py.backup` | BACKUP | Cópia histórica do bootstrap | Não importar |
| `routes/nfe_routes.py.backup` | BACKUP | Cópia histórica da rota ativa | Não importar |
| `services/nfe_service.py.backup` | BACKUP | Cópia histórica do serviço fiscal | Não importar |
| `templates/admin/faturamento/list.html.old` | LEGACY | Template antigo no diretório de templates | Não renderizar |
| `*.bak`, `*.backup`, `*.old` | BACKUP/LEGACY | 272 arquivos encontrados até profundidade 3 | Inventariar antes de remoção |
| `__pycache__/*.pyc` | UNKNOWN/BUILD ARTIFACT | Artefatos locais | Não versionar |

## Riscos

- Cópias de rotas podem induzir manutenção no arquivo errado.
- Backups sob o workspace podem ser importados acidentalmente por scripts genéricos.
- Há arquivos sensíveis rastreados pelo Git; ver `docs/SECRETS_REMEDIATION.md`.

## Política para remoção futura

1. Confirmar referências com busca completa.
2. Executar a suíte crítica e a suíte completa.
3. Remover em mudança isolada.
4. Executar smoke de homologação.
5. Manter rollback disponível.

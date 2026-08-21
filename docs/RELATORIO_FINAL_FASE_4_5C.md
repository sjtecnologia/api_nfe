# EmiteMax Fase 4.5C — Fechamento do Gate

**Data**: 2026-08-21  
**Deploy**: NÃO REALIZADO  
**SSH/SCP/systemctl/AWS**: NÃO EXECUTADOS

## Veredito

# BLOCKED

O build está tecnicamente verde, mas **não está apto para homologação formal nem deploy** enquanto houver secrets rastreados e working tree fora do estado definido pelo processo de release.

## As três falhas anteriores

### 1. `test_nfe_requires_ibs_cbs_classification_for_crt3`

**O que esperava**: erro contendo exatamente `Classificação IBS/CBS é obrigatória para CRT=3`.

**Comportamento atual**: o validator aplica a regra, mas contextualiza o erro por item: `campo Classificação IBS/CBS é obrigatório para CRT=3`.

**Classificação**: TESTE DESATUALIZADO.

**Evidência**: `git blame` mostra a regra desde 28/05 e o prefixo contextual foi introduzido em alteração de validação de 07/07.

**Correção**: teste atualizado para o contrato contextual atual. Regra IBS/CBS não foi alterada.

**Impacto**: nenhum impacto funcional novo; a validação continua bloqueando CRT3 sem classificação.

### 2. `test_gerar_xml_com_tributos_federais_giss`

**O que esperava**: XML com `tribFed`, `piscofins`, `totTrib` e `IBSCBS` sem configurar ambiente.

**Comportamento atual**: o serviço só gera esses blocos quando `GISS_SCHEMA_RTC_HOMOLOGACAO`/`GISS_SCHEMA_RTC` está habilitado; o default é `false` para compatibilidade com schema legado.

**Classificação**: TESTE DESATUALIZADO/CONFIGURAÇÃO AUSENTE.

**Evidência**: commit `e4d4b51f` de 10/08 introduziu `_usar_schema_rtc()` e condicionou os blocos ao flag.

**Correção**: teste configura explicitamente `GISS_SCHEMA_RTC_HOMOLOGACAO=true` com `monkeypatch`.

**Impacto**: nenhum; o default de produção/homologação não foi alterado.

### 3. `test_url_producao_sjrp_default`

**O que esperava**: default de produção `ws-sjrp.giss.com.br`.

**Comportamento atual**: default de produção é `ws-rtc.giss.com.br`; SJRP continua disponível por `municipio_slug='Sao Jose do Rio Preto'`.

**Classificação**: TESTE DESATUALIZADO.

**Evidência**: commit `e4d4b51f` alterou explicitamente o default de produção para `ws-rtc.giss.com.br` e manteve `ws-sjrp` na whitelist.

**Correção**: teste atualizado para o default atual e para o override explícito de SJRP.

**Impacto**: nenhum código de endpoint foi alterado nesta fase.

## Multiempresa A/B

Testes comportamentais adicionados em [tests/test_phase_45c_security.py](../tests/test_phase_45c_security.py):

- Empresa A não lista NF-e da Empresa B.
- Empresa A não consulta próximo número da Empresa B.
- Empresa A não emite NFC-e com Empresa B.
- O `cliente_id` explícito agora é validado contra `get_accessible_client_ids()`.

Foi encontrado e corrigido um bypass real em:

- `routes/nfe_routes.py`: próximo número aceitava cliente fora do escopo.
- `routes/nfe_routes.py`: listagem aceitava `cliente_id` explícito sem validar acesso.

Essas alterações são de autorização/isolamento, não de regra fiscal, XML ou SEFAZ.

Pendência: rascunho e análise de vendas com fixtures persistentes A/B ainda precisam de uma camada de banco de teste mais completa.

## Roles

Matriz mínima executada para Viewer, Editor, Admin e Super_Admin:

- Viewer: não emite, visualiza.
- Editor: emite e visualiza.
- Admin: emite e visualiza.
- Super_Admin: emite e visualiza.

Também foi testado `permission_required()` sem permissão, retornando JSON HTTP 403.

Pendência: matriz HTTP completa para reenviar, emitir rascunho, editar produto e gerenciar usuários ainda não foi concluída.

## Smoke E2E

**Não implementado com navegador**.

Playwright Python, Playwright Node e Selenium não estão disponíveis no ambiente atual. Foi mantido o canário HTTP/Flask, cobrindo login, endpoints, templates globais, emissão, CSRF, NFC-e e JavaScript.

Checklist de homologação preparado em [docs/HOMOLOGACAO_CHECKLIST_FASE_4_5C.md](HOMOLOGACAO_CHECKLIST_FASE_4_5C.md).

## Secrets

Inventário sem conteúdo em [docs/SECRETS_REMEDIATION.md](SECRETS_REMEDIATION.md).

Foram confirmados 7 caminhos rastreados com risco:

- 2 arquivos `.env`/backup de configuração;
- 3 arquivos PEM de chave potencial;
- 1 bundle PEM que precisa ser classificado como público ou privado;
- 1 template de ambiente AWS que precisa ser auditado.

Nenhum valor foi exibido, revogado, removido ou rotacionado.

Comandos `git rm --cached` foram apenas documentados, não executados.

## Gitignore

Ampliada cobertura para:

- `.env.*` com exceção de `.env.example`;
- `*.pem`, `*.p12`, `*.pfx`, `*.key`, `*.crt`;
- `certificados/`, `credentials/`, `secrets/`.

Isso não remove arquivos já rastreados; a remediação continua bloqueadora.

## Resultado da suíte

- Total: **165**
- Passed: **165**
- Failed: **0**
- Skipped: **0**
- Duração: aproximadamente **25,35 s**

## Release gate

Resultado de `./pre_deploy_check.sh` em modo local:

- Critical regression: PASS
- Full suite: PASS
- Roles: PASS
- Multi-tenant: PASS nos cenários cobertos
- JavaScript: PASS
- Templates: PASS
- Secrets: FAIL
- Working tree: FAIL
- **FINAL: BLOCKED**

Resultado de `./pre_deploy_check.sh --deploy`:

- **BLOQUEADO**, com exit 1 por working tree e secrets rastreados.

## Arquivos fiscais alterados

- `routes/nfe_routes.py`: autorização de acesso em próximo número e listagem NF-e.

Justificativa: correção de bypass multiempresa comprovado por teste A/B. Nenhuma regra fiscal, cálculo, XML, certificado ou integração SEFAZ foi alterada.

## Outros arquivos alterados/criados

- `tests/test_nfe_reforma_tributaria.py`
- `tests/test_nfse_reforma_tributaria.py`
- `tests/test_phase_45c_security.py`
- `pre_deploy_check.sh`
- `.gitignore`
- `docs/SECRETS_REMEDIATION.md`
- `docs/HOMOLOGACAO_CHECKLIST_FASE_4_5C.md`
- este relatório

## Pendências bloqueadoras

1. Rotacionar e retirar secrets rastreados conforme plano aprovado.
2. Definir estado de release/commit e limpar artefatos `__pycache__` rastreados.
3. Completar rascunho e análise de vendas A/B.
4. Completar matriz HTTP de ações administrativas.
5. Executar canário de navegador em ambiente que disponha de Playwright/Selenium.

## Conclusão

# NÃO APTO PARA HOMOLOGAÇÃO FORMAL

O código e a suíte estão verdes, mas o gate de segurança está corretamente bloqueado por secrets rastreados e estado de release. Nenhum deploy foi realizado.

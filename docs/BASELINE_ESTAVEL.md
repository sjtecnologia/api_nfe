# EmiteMax — Baseline Estável

**Baseline ID**: `EMITEMAX-BASELINE-2026-08-21`  
**Branch**: `lc214-migration`  
**Commit**: `22b6b50063f43e38f2ecb06b437f29f34c405053`  
**Tag local**: `stable-2026-08-21`  
**Ambiente homologado**: aplicação local em `127.0.0.1:5051`, conectada à base AWS de homologação/teste  
**Produção**: não acessada para deploy

## Validação

- Critical regression: PASS
- Full suite: PASS
- Roles: PASS
- Multi-tenant: PASS
- JavaScript: PASS
- Templates: PASS
- Secrets: PASS
- Working tree: PASS
- Browser Smoke: PASS
- Total de testes: 165
- Passed: 165
- Failed: 0
- Skipped: 0

## Browser Smoke

Conta exclusiva E2E, fornecida por ambiente e não armazenada no repositório.

Fluxos validados sem mutações:

- login;
- seleção da empresa de teste;
- dashboard do tenant;
- listagem NF-e;
- abertura da emissão NF-e;
- presença de formulário, CSRF e submit nativo;
- próximo número;
- listagem NFC-e;
- análise de vendas.

Nenhuma NF-e, NFC-e ou NFS-e foi transmitida. Nenhuma chamada SEFAZ foi realizada.

## Homologação

A homologação formal foi aprovada para os fluxos seguros acima. Rascunho, preview DANFE e emissão permanecem sujeitos ao checklist manual e não foram executados de forma mutável.

## Regra para futuras mudanças

Qualquer nova feature deve:

1. partir desta baseline;
2. executar a suíte completa;
3. executar `pre_deploy_check.sh --deploy`;
4. executar Browser Smoke;
5. preservar isolamento multiempresa;
6. adicionar testes específicos antes de tocar o núcleo fiscal.

Fase 4.6 e Fase 5 permanecem fora do escopo desta baseline.

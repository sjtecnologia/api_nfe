# Checklist de Homologação — Fase 4.5C

Este roteiro é local/homologação. Não executar contra produção e não usar SEFAZ real sem autorização.

## Pré-condições

- [ ] Secrets rotacionados e ambiente seguro configurado.
- [ ] Working tree no estado aprovado pelo processo de release.
- [ ] `./pre_deploy_check.sh --deploy` retorna `READY FOR HOMOLOGATION`.
- [ ] As 3 falhas tributárias/NFS-e foram aprovadas como testes atualizados.
- [ ] Banco de homologação isolado.
- [ ] Certificado de homologação, se necessário, configurado fora do Git.

## Canário funcional

- [ ] `GET /auth/login` retorna 200.
- [ ] `/login` redireciona para `/auth/login`.
- [ ] Login de usuário de homologação funciona.
- [ ] Seleção da Empresa A grava a sessão corretamente.
- [ ] Troca para Empresa B grava a sessão corretamente.
- [ ] Dashboard renderiza após a troca sem `BuildError`/500.
- [ ] Listagem NF-e abre.
- [ ] Tela `/admin/nfe/emitir` abre com formulário e CSRF.
- [ ] Próximo número respeita a empresa ativa.
- [ ] Rascunho salva e carrega na empresa correta.
- [ ] Empresa A não acessa dados da Empresa B.
- [ ] Preview DANFE usa mock/ambiente autorizado e retorna contrato esperado.
- [ ] Listagem NFC-e abre.
- [ ] Tela de emissão NFC-e abre sem chamar serviço externo.
- [ ] Estoque abre.
- [ ] Fluxo de caixa abre.
- [ ] Análise de vendas abre para empresa selecionada.

## Evidências

Registrar data, commit, ambiente, usuário de homologação, empresa selecionada, status HTTP e logs sem secrets.

## Critério de parada

Qualquer falha em login, seleção de empresa, dashboard, NF-e, CSRF, rascunho, numeração, DANFE, NFC-e ou multiempresa bloqueia a promoção. Não aplicar hotfix sequencial sem rollback/triagem formal.

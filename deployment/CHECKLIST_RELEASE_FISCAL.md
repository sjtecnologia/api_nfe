# Gate de release fiscal

Este checklist é obrigatório antes de atualizar qualquer ambiente que emita
NF-e, NFC-e ou NFS-e. Nenhum passo deve ser substituído por `|| true`.

## 1. Pré-release

- [ ] Confirmar branch, commit e janela de manutenção.
- [ ] Registrar versão atual da aplicação, Python, PostgreSQL e dependências.
- [ ] Confirmar que não há emissão fiscal pendente ou reenvio em andamento.
- [ ] Confirmar acesso ao banco, certificado de backup e responsável pelo rollback.
- [ ] Executar `python -m pytest -q` e guardar o relatório.
- [ ] Executar `python -m compileall routes services models database`.
- [ ] Conferir que produção não usa modo simulado para nenhum documento.
- [ ] Confirmar `ALLOW_API_KEY_QUERY_PARAM` ausente/desativado em produção.
- [ ] Confirmar que API Keys de teste (`emx_test_`) e produção (`emx_live_`) estão separadas.

## 2. Backup e ensaio

- [ ] Executar `pg_dump` completo com `--format=custom`, incluindo schema e dados.
- [ ] Fazer backup dos arquivos da aplicação e do `.env` sem expor o conteúdo.
- [ ] Testar restauração do dump em banco isolado.
- [ ] Aplicar as migrations em banco clone antes da produção.
- [ ] Validar contagens de `nfe_emitidas`, `nfse`, certificados e assinaturas.
- [ ] Confirmar que índices e constraints foram criados.

## 3. Migrations

Executar individualmente, na ordem, somente após o backup:

```text
database/migrations/016_create_fiscal_api_idempotency.sql
database/migrations/017_add_api_key_environment.sql
```

Após cada migration:

- [ ] Verificar código de saída do `psql`.
- [ ] Consultar a tabela criada e suas constraints.
- [ ] Registrar o resultado em um log de release.
- [ ] Confirmar constraint `api_keys_ambiente_check` e defaults de ambiente.

## 4. Deploy da aplicação

- [ ] Publicar código sem apagar uploads, certificados, XMLs ou backups.
- [ ] Reiniciar primeiro uma instância de forma controlada.
- [ ] Conferir `/health` e logs de inicialização.
- [ ] Executar smoke test autenticado de leitura.
- [ ] Ativar novas rotas por feature flag inicialmente desligada.
- [ ] Não habilitar emissão em produção sem teste real autorizado pelo responsável fiscal.

## 5. Smoke tests fiscais

- [ ] NF-e: criar requisição idempotente em homologação.
- [ ] NF-e: repetir a mesma requisição e confirmar que não duplica a nota.
- [ ] NF-e: usar a mesma chave com payload diferente e confirmar HTTP 409.
- [ ] NF-e: consultar status e baixar XML.
- [ ] NFC-e: validar assinatura e rejeitar qualquer tentativa de simulação em produção.
- [ ] NFS-e: validar parâmetros municipais, DPS, envio e consulta.
- [ ] Confirmar webhook de autorização, rejeição e cancelamento.
- [ ] Conferir que CPF/CNPJ, certificados e XML completo não aparecem nos logs.
- [ ] Validar que URLs de webhook não apontam para localhost, loopback ou redes privadas.

## 6. Critérios de abortar

Abortar e restaurar a versão anterior se ocorrer qualquer um destes casos:

- health check falhar;
- migration falhar ou ficar parcialmente aplicada;
- alteração de status ou numeração inconsistente;
- certificado não for carregado;
- emissão retornar sucesso sem protocolo oficial;
- duplicidade em retry;
- webhook quebrar a transação fiscal;
- aumento de erros 5xx ou rejeições não explicadas.

## 7. Rollback

- [ ] Desabilitar feature flags novas.
- [ ] Parar novas emissões, se necessário.
- [ ] Restaurar o código anterior.
- [ ] Restaurar o dump somente se houver alteração de dados incorreta; não usar
  rollback destrutivo automaticamente.
- [ ] Revalidar `/health`, leitura de notas e consulta de status.
- [ ] Registrar todas as notas processadas durante a janela para reconciliação.

Uma release só pode ser considerada concluída quando todos os itens aplicáveis
estiverem marcados e houver evidência anexada ao registro da implantação.

# Rollout de Hardening de Uploads

## Objetivo
Este documento descreve como colocar em producao as validacoes de upload reforcadas, monitorar impacto e executar rollback de forma segura.

## Escopo aplicado
- Validacao central de upload (extensao, MIME declarado, conteudo real, limite por contexto)
- Endpoints administrativos de upload (Siscomex, planilha produtos, certificado)
- Armazenamento de logos em area privada (`private:logos/...`)
- Rota autenticada para servir logos privadas

## Pre-Deploy Checklist
1. Confirmar variaveis de ambiente:
- `UPLOAD_FOLDER`
- `PRIVATE_UPLOAD_FOLDER`
- `FLASK_SECRET_KEY`
- `DATABASE_URL`
2. Garantir permissao de escrita no diretorio `PRIVATE_UPLOAD_FOLDER`.
3. Executar testes de seguranca de upload:
- `python -m pytest tests/test_file_validator.py tests/test_upload_integration.py -q`
4. Garantir backup de banco antes da migracao de logos.
5. Garantir backup de `static/logos`.

## Sequencia de Deploy (recomendada)
1. Publicar codigo em staging.
2. Validar uploads manualmente em staging:
- logo PNG/JPG valido
- certificado pfx/p12 valido
- Siscomex JSON valido
- rejeicao de arquivo invalido (ex: `shell.php.png`)
3. Publicar codigo em producao.
4. Rodar migracao de logos em modo dry-run:
- `python scripts/migrate_logos_to_private.py --dry-run`
5. Conferir resumo do dry-run e contagens.
6. Executar migracao real:
- `python scripts/migrate_logos_to_private.py`
7. Reiniciar app e validar formulario de cliente e emissao DANFE.

## Observabilidade
### Logs de bloqueio de upload
O sistema registra bloqueios com contexto de seguranca (user_id, path, filename, motivo).

Eventos principais:
- `Upload Siscomex bloqueado`
- `Upload planilha bloqueado`
- `Upload certificado bloqueado (insert/update)`
- `Upload logo bloqueado (create/edit)`

### Alertas recomendados
Criar alertas quando:
1. Bloqueios de upload aumentarem > 30% em 15 min.
2. Erros 500 em rotas `/admin/*upload*` excederem baseline.
3. Rota de logo privada (`/admin/media/logos/...`) retornar 404 acima do esperado.

## Queries operacionais uteis
### Contar logos privadas
```sql
SELECT COUNT(*)
FROM clientes
WHERE logo_path LIKE 'private:logos/%';
```

### Contar logos legadas em static
```sql
SELECT COUNT(*)
FROM clientes
WHERE logo_path IS NOT NULL
  AND logo_path <> ''
  AND logo_path NOT LIKE 'private:logos/%';
```

### Amostra de clientes sem logo
```sql
SELECT cliente_id, razao_social
FROM clientes
WHERE logo_path IS NULL OR logo_path = ''
ORDER BY cliente_id
LIMIT 20;
```

## Rollback
### Quando rollback e necessario
- Falhas generalizadas de acesso a logo no formulario/DANFE.
- Erros de permissao no `PRIVATE_UPLOAD_FOLDER` em producao.
- Taxa de erro de upload fora do limite operacional.

### Plano de rollback rapido
1. Reverter deploy para commit anterior.
2. Manter arquivos privados (nao apagar).
3. Reverter `logo_path` no banco para caminho legado (se necessario), a partir do backup.
4. Validar telas de cliente e DANFE.

## Pos-Deploy
1. Acompanhar por 24h:
- taxa de upload bloqueado por motivo
- erros 500 nas rotas administrativas de upload
2. Registrar incidentes e ajustar limites/contextos quando houver falso positivo.
3. Planejar remocao definitiva de `static/logos` apos janela de estabilidade.

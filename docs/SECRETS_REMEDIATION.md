# Relatório de Remediação de Secrets

**Fase**: 4.5B  
**Data**: 2026-08-21  
**Conteúdo sensível**: não reproduzido neste documento.

## Achados confirmados

A inspeção local encontrou:

- `.env` rastreado pelo Git.
- `.env.bak_20260331_140800` rastreado pelo Git.
- Arquivos `.pem` rastreados pelo Git em `Documentacao/`.
- Arquivos de ambiente e backups locais adicionais no workspace.
- Scripts/documentação com referências a caminhos de chave PEM.
- Scripts/documentação com IPs de produção atuais e antigos.

Os valores, tokens, senhas e chaves não foram impressos nem copiados para este relatório.

## Inventário sem conteúdo

| Caminho | Tipo | Rastreado pelo Git | Ação necessária |
|---|---|---:|---|
| `.env` | Configuração com credenciais | Sim | Rotacionar, remover do índice e planejar limpeza histórica |
| `.env.bak_20260331_140800` | Backup de configuração | Sim | Rotacionar valores, remover do índice e planejar limpeza histórica |
| `Documentacao/api_nfe_key_new.pem` | Chave privada/SSH | Não, removido do índice | Rotacionar se ativo; remover arquivo após validar nova chave |
| `Documentacao/nfe_api_key.pem` | Chave privada/SSH | Não, removido do índice | Rotacionar se ativo; remover arquivo após validar nova chave |
| `Documentacao/nfe_api_key_lf.pem` | Chave privada/SSH | Não, removido do índice | Rotacionar se ativo; remover arquivo após validar nova chave |
| `ca-bundle-icpbrasil.pem` | Bundle de certificados CA público | Sim | Preservar; revisar periodicamente; não contém marcador de chave privada |
| `deployment/.env.template.aws` | Template de configuração | Sim | Manter apenas placeholders, sem valores reais |

Os três PEMs foram classificados por marcador PEM como chaves privadas e retirados do índice com `git rm --cached`; as cópias locais não foram apagadas.

Comandos propostos para revisão aprovada, **não executados**:

```bash
git rm --cached .env .env.bak_20260331_140800
git rm --cached Documentacao/api_nfe_key_new.pem Documentacao/nfe_api_key.pem Documentacao/nfe_api_key_lf.pem
# Não remover ca-bundle-icpbrasil.pem: bundle público classificado e aprovado para versionamento.
```

Depois: rotacionar credenciais, atualizar o ambiente seguro, testar, revogar as antigas e limpar o histórico Git em procedimento separado.

## Risco

**CRÍTICO**: qualquer segredo presente em arquivo rastreado deve ser considerado comprometido, mesmo que o arquivo esteja ignorado em versões futuras.

Também existe risco operacional por manter referências de infraestrutura antigas junto das atuais, especialmente em scripts de deploy.

## Remediação recomendada

1. Rotacionar imediatamente credenciais de banco, SMTP, AWS/SES, API e tokens encontrados nos arquivos rastreados.
2. Invalidar certificados/chaves PEM comprometidos e emitir novos pares.
3. Remover secrets do working tree e do histórico Git em mudança aprovada e coordenada.
4. Usar Secrets Manager, variáveis protegidas do CI ou mecanismo equivalente.
5. Manter apenas arquivos `.env.example`/templates sem valores reais.
6. Impedir commits de `.env`, `.env.*`, `*.pem`, `*.p12`, `*.pfx`, `*.key` e credenciais com hook/CI.
7. Revisar permissões dos arquivos locais de ambiente e chaves.
8. Separar configuração de deploy de código da aplicação.

## Estado do `.gitignore`

O `.gitignore` cobre `.env`, backups genéricos, `*.bak`, `*.pyc` e alguns arquivos de ambiente, mas isso não remove arquivos já rastreados. A cobertura deve ser ampliada explicitamente para:

```text
.env
.env.*
!.env.example
*.pem
*.p12
*.pfx
*.key
*.crt
certificados/
credentials/
secrets/
```

A alteração do `.gitignore` sozinha não corrige o histórico e não foi usada como substituto de rotação.

## Escopo desta fase

Nenhum segredo foi exibido ou rotacionado. Os arquivos privados confirmados foram removidos do índice, sem apagar cópias locais. Nenhum deploy foi executado.

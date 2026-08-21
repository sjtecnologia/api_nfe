# Plano de Rotação de Secrets — Fase 4.5D

Nenhum valor é reproduzido. Nenhuma credencial foi rotacionada automaticamente.

## Banco

Variáveis identificadas por nome: `DATABASE_URL`, `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

1. Gerar nova senha/credencial no RDS ou serviço equivalente.
2. Inserir no Secrets Manager/ambiente seguro de homologação.
3. Validar conexão e testes de leitura/escrita em homologação.
4. Atualizar produção em janela coordenada.
5. Revogar a credencial anterior.
6. Remover arquivos `.env` rastreados e limpar histórico aprovado.

## SMTP/SES

Variáveis: `SMTP_*`, `AWS_SES_ACCESS_KEY_ID`, `AWS_SES_SECRET_ACCESS_KEY`, `SES_FROM_EMAIL`.

1. Criar credenciais novas com menor privilégio.
2. Configurar ambiente seguro.
3. Testar envio controlado em homologação.
4. Atualizar produção.
5. Revogar chaves antigas.

## IA e observabilidade

Variáveis: `AI_PROVIDER_API_KEY`, `LLM_*`, `RASTRO_INGEST_TOKEN`.

1. Identificar provedor e escopo de cada credencial.
2. Emitir novas chaves/tokens.
3. Validar chamadas não fiscais em homologação.
4. Revogar antigos e remover do histórico em procedimento separado.

## Flask e criptografia local

Variáveis: `FLASK_SECRET_KEY`, `CERT_MASTER_KEY`.

1. Planejar impacto em sessões e dados cifrados.
2. Gerar novos valores somente após estratégia de migração.
3. Testar login e leitura de certificados em homologação.
4. Não trocar `CERT_MASTER_KEY` sem plano para dados existentes.

## AWS/SSH

Os três arquivos PEM em `Documentacao/` foram classificados como chaves privadas.

1. Gerar novo par de chave.
2. Instalar a chave pública no servidor por acesso ainda válido.
3. Validar login com a nova chave.
4. Atualizar processo de deploy para variável/secret seguro.
5. Revogar a chave antiga.
6. Remover os PEMs antigos do índice e limpar histórico aprovado.

Não houve conexão SSH nesta fase.

## CA bundle

`ca-bundle-icpbrasil.pem` contém certificados e não apresentou marcador de chave privada. É tratado como material público até revisão formal. Não remover nem rotacionar automaticamente.

## Histórico Git

O remoto existe e há branches locais/remotas. Os secrets devem ser considerados expostos. Após rotação, preparar backup e procedimento coordenado com `git filter-repo` ou ferramenta equivalente. Nenhuma reescrita foi executada.

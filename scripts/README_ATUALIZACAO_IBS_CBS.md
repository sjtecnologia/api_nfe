# Atualização de Classificações IBS/CBS no Servidor

## 📋 Arquivos

- `atualizar_ibs_cbs_servidor.py` - Script Python principal
- `atualizar_ibs_cbs.sh` - Script bash para facilitar execução
- `cClassTrib 2025-12-12.xlsx` - Arquivo Excel com dados (deve estar em `Documentacao/`)

## 🚀 Como Usar

### Método 1: Usando o script bash (Recomendado)

```bash
# Tornar o script executável
chmod +x scripts/atualizar_ibs_cbs.sh

# Executar
./scripts/atualizar_ibs_cbs.sh
```

### Método 2: Executando Python diretamente

```bash
cd /caminho/para/api_nfe
python3 scripts/atualizar_ibs_cbs_servidor.py
```

### Método 3: Execução automática (sem confirmação)

```bash
# Para ambientes de CI/CD ou scripts automatizados
./scripts/atualizar_ibs_cbs.sh --yes
# ou
python3 scripts/atualizar_ibs_cbs_servidor.py --yes
```

## 📦 Preparação no Servidor

### 1. Fazer upload dos arquivos

```bash
# Do seu computador local, fazer upload para o servidor:
scp "Documentacao/cClassTrib 2025-12-12.xlsx" usuario@servidor:/caminho/api_nfe/Documentacao/
scp scripts/atualizar_ibs_cbs_servidor.py usuario@servidor:/caminho/api_nfe/scripts/
scp scripts/atualizar_ibs_cbs.sh usuario@servidor:/caminho/api_nfe/scripts/
```

### 2. Conectar ao servidor

```bash
ssh usuario@servidor
cd /caminho/api_nfe
```

### 3. Verificar dependências

```bash
# Instalar pandas e openpyxl se necessário
pip3 install pandas openpyxl sqlalchemy psycopg2-binary
```

### 4. Executar atualização

```bash
chmod +x scripts/atualizar_ibs_cbs.sh
./scripts/atualizar_ibs_cbs.sh
```

## 🔒 O que o script faz

1. ✅ **Validação**: Verifica se o arquivo Excel existe
2. 📦 **Backup**: Cria backup automático dos dados atuais em `backups/`
3. 🗑️ **Limpeza**: Remove todos os registros antigos
4. 📝 **Importação**: Insere os 145 registros novos do Excel
5. ✅ **Validação**: Verifica se todos os dados foram inseridos corretamente

## 📊 Estrutura dos Dados

### Arquivo Excel esperado:
- `CST-IBS/CBS` - Código CST
- `cClassTrib` - Código da classificação
- `Nome cClassTrib` - Nome da classificação
- `Descrição cClassTrib` - Descrição detalhada
- `Tipo de Alíquota` - Tipo (Padrão, Uniforme, etc)
- `pRedIBS` - Percentual de redução IBS
- `pRedCBS` - Percentual de redução CBS

### Formato dos códigos gerados:
- `00-00001` - CST 00 com cClassTrib 00001
- `10-10002` - CST 10 com cClassTrib 10002
- `11-11001` - CST 11 com cClassTrib 11001

## 🛡️ Segurança

- O script **sempre** cria backup antes de fazer qualquer alteração
- Backups são salvos em `backups/classificacoes_ibs_cbs_backup_YYYYMMDD_HHMMSS.sql`
- Em caso de erro, todas as alterações são revertidas (rollback)
- Requer confirmação do usuário antes de executar (exceto com `--yes`)

## 📋 Saída do Script

### Exemplo de execução bem-sucedida:

```
======================================================================
  ATUALIZAÇÃO DE CLASSIFICAÇÕES IBS/CBS
======================================================================

📦 Criando backup dos dados atuais...
   Registros atuais na tabela: 145
   ✅ Backup salvo em: backups/classificacoes_ibs_cbs_backup_20251217_143022.sql

📖 Lendo arquivo Excel...
   Total de registros no Excel: 145
   ✅ Estrutura do arquivo validada

🗑️  Limpando tabela existente...
   ✅ Tabela limpa

📝 Inserindo novos registros...
   Processados: 25/145 registros...
   Processados: 50/145 registros...
   ...

💾 Salvando alterações no banco de dados...

======================================================================
  RESUMO DA ATUALIZAÇÃO
======================================================================
✅ Registros processados:      145
✅ Registros inseridos:        145
❌ Erros encontrados:          0
📊 Total na tabela:            145

======================================================================
✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!
======================================================================
```

## 🔧 Troubleshooting

### Erro: "Arquivo Excel não encontrado"
```bash
# Verificar se o arquivo está no lugar correto:
ls -la Documentacao/cClassTrib*.xlsx

# Fazer upload se necessário:
scp "cClassTrib 2025-12-12.xlsx" usuario@servidor:~/api_nfe/Documentacao/
```

### Erro: "ModuleNotFoundError: No module named 'pandas'"
```bash
# Instalar dependências:
pip3 install pandas openpyxl sqlalchemy psycopg2-binary
```

### Erro de permissão
```bash
# Dar permissão de execução:
chmod +x scripts/atualizar_ibs_cbs.sh
```

### Erro de conexão com banco
```bash
# Verificar se o banco está acessível:
python3 -c "from database.connection import SessionLocal; db = SessionLocal(); print('OK')"
```

## 📝 Restaurar Backup

Se precisar restaurar um backup:

```bash
# Listar backups disponíveis
ls -la backups/classificacoes_ibs_cbs_backup_*.sql

# Restaurar (ajuste o nome do arquivo)
psql -U usuario -d nomedobanco -f backups/classificacoes_ibs_cbs_backup_20251217_143022.sql
```

## 🔄 Automatização (Opcional)

Para agendar atualizações automáticas:

```bash
# Editar crontab
crontab -e

# Adicionar linha para executar toda segunda-feira às 3h da manhã:
0 3 * * 1 cd /caminho/api_nfe && ./scripts/atualizar_ibs_cbs.sh --yes >> logs/ibs_cbs_update.log 2>&1
```

## 📞 Suporte

Em caso de problemas:
1. Verifique os logs de erro
2. Verifique se todos os backups foram criados
3. Consulte a documentação da LC 214/2025
4. Entre em contato com o suporte técnico

# 📦 Configuração do Sistema de Backup Automático

## ✅ O Que Foi Implementado

O sistema completo de backup automático inclui:

1. **Scripts de Backup e Restore**
   - `backup_database.sh` - Backup automático com compressão e rotação
   - `restore_database.sh` - Restauração segura com validação

2. **Interface Web Completa**
   - Listagem de backups com estatísticas
   - Download de backups
   - Execução manual de backup
   - Remoção de backups antigos
   - Visualização de logs

3. **Configurações Centralizadas**
   - Todas as configurações em `config/settings.py`
   - Variáveis de ambiente suportadas

## 🚀 Guia de Instalação Rápida

### Passo 1: Verificar Instalação

Os arquivos já foram criados:
```bash
./backup_database.sh      # Script de backup
./restore_database.sh     # Script de restauração
```

Certifique-se de que têm permissão de execução:
```bash
chmod +x backup_database.sh restore_database.sh
```

### Passo 2: Testar Backup Manual

Execute um backup de teste:
```bash
./backup_database.sh
```

Verifique se o backup foi criado:
```bash
ls -lh backups/
```

### Passo 3: Configurar Backup Automático (Cron)

Edite o crontab:
```bash
crontab -e
```

Adicione uma das linhas abaixo:

#### Opção 1: Backup Diário às 2h da manhã (RECOMENDADO)
```bash
0 2 * * * cd /Users/renato/Documents/Developement/api_nfe && ./backup_database.sh >> logs/cron_backup.log 2>&1
```

#### Opção 2: Backup a cada 6 horas
```bash
0 */6 * * * cd /Users/renato/Documents/Developement/api_nfe && ./backup_database.sh >> logs/cron_backup.log 2>&1
```

#### Opção 3: Backup a cada 12 horas
```bash
0 */12 * * * cd /Users/renato/Documents/Developement/api_nfe && ./backup_database.sh >> logs/cron_backup.log 2>&1
```

#### Opção 4: Backup Semanal (Domingos às 3h)
```bash
0 3 * * 0 cd /Users/renato/Documents/Developement/api_nfe && ./backup_database.sh >> logs/cron_backup.log 2>&1
```

**Importante:** Substitua `/Users/renato/Documents/Developement/api_nfe` pelo caminho real do seu projeto!

### Passo 4: Verificar Cron Configurado

Liste os crons ativos:
```bash
crontab -l
```

## 🔧 Configurações Avançadas

### Variáveis de Ambiente

Você pode sobrescrever as configurações padrão usando variáveis de ambiente:

```bash
# Banco de dados
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=sjtnfe
export DB_USER=postgres
export DB_PASSWORD=Mo2505

# Diretórios
export BACKUP_DIR=./backups
export LOG_DIR=./logs

# Retenção (em dias)
export RETENTION_DAYS=30
```

### Arquivo .env (Recomendado)

Crie um arquivo `.env` na raiz do projeto:

```bash
# Configurações do Banco
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sjtnfe
DB_USER=postgres
DB_PASSWORD=Mo2505

# Configurações de Backup
BACKUP_DIR=backups
BACKUP_RETENTION_DAYS=30
BACKUP_LOG_DIR=logs
```

## 📊 Usando a Interface Web

### Acessar Sistema de Backups

1. Faça login no sistema admin
2. Acesse: `http://localhost:8080/admin/backups`
3. Ou clique no menu: **Admin → Backup**

### Funcionalidades Disponíveis

- **📊 Dashboard**: Estatísticas de backups (total, último backup, tamanho)
- **▶️ Executar Backup**: Botão para backup manual imediato
- **📥 Download**: Baixar qualquer backup disponível
- **🗑️ Remover**: Deletar backups antigos manualmente
- **📄 Logs**: Visualizar log do último backup executado
- **📖 Instruções**: Guia de configuração do cron diretamente na interface

## 🔄 Como Restaurar um Backup

### Restauração via Terminal (Recomendado)

1. Liste os backups disponíveis:
```bash
ls -lh backups/
```

2. Execute o script de restauração:
```bash
./restore_database.sh backups/backup_sjtnfe_20231106_140530.sql.gz
```

3. Confirme a operação digitando `SIM`

4. Aguarde a conclusão e verifique o log

### ⚠️ IMPORTANTE - Antes de Restaurar

- ✅ Faça um backup atual antes de restaurar
- ✅ Certifique-se de que nenhum usuário está usando o sistema
- ✅ Teste a restauração em desenvolvimento primeiro
- ✅ Tenha um plano de rollback

## 📝 Rotação Automática de Backups

O sistema automaticamente remove backups com mais de 30 dias (configurável).

Para alterar o período de retenção:

```bash
# Em config/settings.py
BACKUP_RETENTION_DAYS = 60  # Manter por 60 dias
```

Ou via variável de ambiente:
```bash
export BACKUP_RETENTION_DAYS=60
```

## 🧪 Testes e Validação

### Teste 1: Backup Manual
```bash
./backup_database.sh
```
✅ Deve criar arquivo em `backups/backup_sjtnfe_*.sql.gz`

### Teste 2: Restauração
```bash
./restore_database.sh backups/backup_sjtnfe_*.sql.gz
```
✅ Deve solicitar confirmação e restaurar o banco

### Teste 3: Interface Web
1. Acesse `http://localhost:8080/admin/backups`
2. Clique em "Executar Backup Agora"
3. Verifique se aparece na lista
4. Teste download
5. Teste remoção (opcional)

## 🔐 Segurança

### Proteção de Senha

A senha do banco NÃO fica exposta nos logs. O script usa `PGPASSWORD` temporariamente e limpa da memória após uso.

### Permissões de Arquivos

Recomendações:
```bash
# Scripts
chmod 700 backup_database.sh restore_database.sh

# Diretório de backups
chmod 700 backups/

# Logs
chmod 700 logs/
```

### Backups Externos

**CRÍTICO:** Configure backup externo dos arquivos!

Opções recomendadas:
1. **rsync** para servidor remoto
2. **AWS S3** ou similar
3. **Google Drive** ou Dropbox
4. **NAS** ou storage em rede

Exemplo com rsync:
```bash
# Adicionar ao cron após o backup
5 2 * * * rsync -avz /path/to/backups/ user@backup-server:/backups/api_nfe/
```

## 📞 Troubleshooting

### Problema: "pg_dump not found"
**Solução:** Instale o PostgreSQL client
```bash
# macOS
brew install postgresql@15

# Ubuntu/Debian
sudo apt-get install postgresql-client
```

### Problema: "Permission denied"
**Solução:** Adicione permissão de execução
```bash
chmod +x backup_database.sh restore_database.sh
```

### Problema: Backup muito grande
**Solução:** O backup já usa compressão gzip. Para reduzir mais:
1. Limpe dados antigos desnecessários
2. Archive NFes antigas
3. Use retenção menor (7-15 dias)

### Problema: Cron não executa
**Soluções:**
1. Verifique se o cron está ativo: `sudo service cron status`
2. Use caminho absoluto no crontab
3. Verifique logs: `grep CRON /var/log/syslog`
4. Teste o comando manualmente primeiro

## ✅ Checklist de Produção

Antes de colocar em produção, verifique:

- [ ] Backups manuais funcionando
- [ ] Restauração testada com sucesso
- [ ] Cron configurado e testado
- [ ] Logs sendo gerados corretamente
- [ ] Rotação de backups funcionando
- [ ] Backup externo configurado
- [ ] Permissões de segurança ajustadas
- [ ] Equipe treinada para restauração
- [ ] Documentação atualizada
- [ ] Plano de disaster recovery definido

## 🎯 Boas Práticas

1. **Teste restaurações regularmente** (mensal)
2. **Monitore espaço em disco**
3. **Mantenha backups externos** (crítico!)
4. **Documente procedimentos**
5. **Automatize notificações** (email/Slack em falhas)
6. **Versione scripts de backup**
7. **Registre todas as restaurações**

## 📚 Próximos Passos

Com o backup implementado, considere:

1. **Monitoramento**: Alertas se backup falhar
2. **Backup Incremental**: Para bases muito grandes
3. **Backup de Arquivos**: Certificados e uploads
4. **Disaster Recovery**: Plano completo
5. **Alta Disponibilidade**: Réplicas do banco

---

## 🚨 LEMBRE-SE

> **"O backup que você não testa é o backup que vai falhar quando você precisar"**

Faça testes regulares de restauração! 🎯

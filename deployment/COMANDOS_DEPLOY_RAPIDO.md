# 🚀 COMANDOS RÁPIDOS PARA DEPLOY API v2

## 📦 UPLOAD VIA SCP (Recomendado)

### Upload de todos os arquivos novos de uma vez:
```bash
# Navegar até a pasta do projeto local
cd /Users/renato/Documents/Developement/api_nfe

# Upload de arquivos novos
scp auth/api_key_auth.py user@servidor:/var/www/api_nfe/auth/
scp routes/api_keys_routes.py user@servidor:/var/www/api_nfe/routes/
scp routes/api_v2_routes.py user@servidor:/var/www/api_nfe/routes/
scp routes/webhooks_routes.py user@servidor:/var/www/api_nfe/routes/
scp services/webhook_service.py user@servidor:/var/www/api_nfe/services/
scp database/migrations/add_api_keys.sql user@servidor:/var/www/api_nfe/database/migrations/

# Upload de templates (criar pastas primeiro no servidor)
scp -r templates/admin/api_keys user@servidor:/var/www/api_nfe/templates/admin/
scp -r templates/admin/webhooks user@servidor:/var/www/api_nfe/templates/admin/

# Upload de arquivos modificados
scp database/models.py user@servidor:/var/www/api_nfe/database/
scp app.py user@servidor:/var/www/api_nfe/
scp docs/API_INTEGRACAO_MANUAL.md user@servidor:/var/www/api_nfe/docs/

# Upload de documentação de deploy
scp deployment/ARQUIVOS_API_V2_DEPLOY.md user@servidor:/var/www/api_nfe/deployment/
scp deployment/deploy_api_v2.sh user@servidor:/var/www/api_nfe/deployment/
```

### Upload usando RSYNC (mais eficiente):
```bash
# Sync completo de arquivos modificados
rsync -avz --progress \
  --include='auth/api_key_auth.py' \
  --include='routes/api_keys_routes.py' \
  --include='routes/api_v2_routes.py' \
  --include='routes/webhooks_routes.py' \
  --include='services/webhook_service.py' \
  --include='database/migrations/add_api_keys.sql' \
  --include='database/models.py' \
  --include='app.py' \
  --include='docs/API_INTEGRACAO_MANUAL.md' \
  --include='templates/admin/api_keys/***' \
  --include='templates/admin/webhooks/***' \
  --include='deployment/***' \
  --exclude='*' \
  ./ user@servidor:/var/www/api_nfe/
```

---

## 📤 UPLOAD VIA FTP

### Estrutura de pastas para criar no servidor:
```
/var/www/api_nfe/
├── auth/
│   └── api_key_auth.py (NOVO)
├── routes/
│   ├── api_keys_routes.py (NOVO)
│   ├── api_v2_routes.py (NOVO)
│   └── webhooks_routes.py (NOVO)
├── services/
│   └── webhook_service.py (NOVO)
├── database/
│   ├── migrations/
│   │   └── add_api_keys.sql (NOVO)
│   └── models.py (ATUALIZAR)
├── templates/admin/
│   ├── api_keys/ (NOVA PASTA)
│   │   ├── list.html
│   │   ├── create.html
│   │   └── stats.html
│   └── webhooks/ (NOVA PASTA)
│       ├── list.html
│       └── create.html
├── docs/
│   └── API_INTEGRACAO_MANUAL.md (ATUALIZAR)
├── deployment/
│   ├── ARQUIVOS_API_V2_DEPLOY.md (NOVO)
│   └── deploy_api_v2.sh (NOVO)
└── app.py (ATUALIZAR)
```

### Lista de arquivos para FTP (copiar um por um):

**NOVOS (11 arquivos):**
1. `auth/api_key_auth.py`
2. `routes/api_keys_routes.py`
3. `routes/api_v2_routes.py`
4. `routes/webhooks_routes.py`
5. `services/webhook_service.py`
6. `database/migrations/add_api_keys.sql`
7. `templates/admin/api_keys/list.html`
8. `templates/admin/api_keys/create.html`
9. `templates/admin/api_keys/stats.html`
10. `templates/admin/webhooks/list.html`
11. `templates/admin/webhooks/create.html`

**MODIFICADOS (3 arquivos):**
1. `database/models.py` (substituir)
2. `app.py` (substituir)
3. `docs/API_INTEGRACAO_MANUAL.md` (substituir)

**DOCUMENTAÇÃO (2 arquivos):**
1. `deployment/ARQUIVOS_API_V2_DEPLOY.md`
2. `deployment/deploy_api_v2.sh`

---

## 🗄️ COMANDOS DO BANCO DE DADOS

### Via SSH no servidor:
```bash
# Conectar ao servidor
ssh user@servidor

# Fazer backup ANTES da migration
sudo -u postgres pg_dump sjtnfe > backup_antes_api_v2_$(date +%Y%m%d).sql

# Executar migration
cd /var/www/api_nfe
sudo -u postgres psql sjtnfe -f database/migrations/add_api_keys.sql

# Verificar se tabelas foram criadas
sudo -u postgres psql sjtnfe -c "\dt api_keys"
sudo -u postgres psql sjtnfe -c "\dt api_usage_logs"
sudo -u postgres psql sjtnfe -c "\dt webhooks"
sudo -u postgres psql sjtnfe -c "\dt webhook_queue"

# Ver estrutura das tabelas
sudo -u postgres psql sjtnfe -c "\d api_keys"
```

---

## 🔄 COMANDOS DE RESTART

### Systemd:
```bash
sudo systemctl stop api_nfe
sudo systemctl start api_nfe
sudo systemctl status api_nfe
sudo systemctl restart api_nfe
```

### Supervisor:
```bash
sudo supervisorctl stop api_nfe
sudo supervisorctl start api_nfe
sudo supervisorctl status api_nfe
sudo supervisorctl restart api_nfe
```

### Gunicorn manual:
```bash
# Parar processo
pkill -f gunicorn

# Iniciar novamente
cd /var/www/api_nfe
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:8080 app:app --daemon
```

---

## ✅ COMANDOS DE VERIFICAÇÃO

### Testar se API v2 está funcionando:
```bash
# Deve retornar erro de autenticação (esperado)
curl http://localhost:8080/api/v2/nfes

# Deve retornar: {"error": "API Key não fornecida"}
```

### Ver logs em tempo real:
```bash
# Logs da aplicação
tail -f /var/log/api_nfe/error.log
tail -f /var/log/api_nfe/access.log

# Logs do PostgreSQL
tail -f /var/log/postgresql/postgresql-*.log

# Logs do systemd
journalctl -u api_nfe -f
```

### Verificar processos:
```bash
# Ver se aplicação está rodando
ps aux | grep gunicorn
ps aux | grep python

# Ver portas abertas
netstat -tulpn | grep 8080
```

---

## 🛠️ COMANDOS DE MANUTENÇÃO

### Permissões (se necessário):
```bash
cd /var/www/api_nfe
sudo chown -R www-data:www-data .
sudo chmod -R 755 templates/admin/api_keys
sudo chmod -R 755 templates/admin/webhooks
```

### Limpar cache Python (se houver problemas):
```bash
cd /var/www/api_nfe
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### Recriar banco (CUIDADO - apenas em desenvolvimento):
```bash
# CUIDADO: Isso apaga as tabelas!
sudo -u postgres psql sjtnfe -c "DROP TABLE IF EXISTS webhook_queue CASCADE;"
sudo -u postgres psql sjtnfe -c "DROP TABLE IF EXISTS webhooks CASCADE;"
sudo -u postgres psql sjtnfe -c "DROP TABLE IF EXISTS api_usage_logs CASCADE;"
sudo -u postgres psql sjtnfe -c "DROP TABLE IF EXISTS api_keys CASCADE;"

# Recriar
sudo -u postgres psql sjtnfe -f database/migrations/add_api_keys.sql
```

---

## 🚀 SCRIPT AUTOMATIZADO

### Opção 1: Usar o script de deploy
```bash
# Via SSH no servidor
cd /var/www/api_nfe/deployment
sudo chmod +x deploy_api_v2.sh
sudo ./deploy_api_v2.sh
```

### Opção 2: Deploy manual passo a passo
```bash
# 1. Backup
sudo -u postgres pg_dump sjtnfe > backup_$(date +%Y%m%d).sql

# 2. Upload dos arquivos (via SCP/FTP)
# ... fazer upload ...

# 3. Migration
sudo -u postgres psql sjtnfe -f database/migrations/add_api_keys.sql

# 4. Permissões
sudo chown -R www-data:www-data /var/www/api_nfe
sudo chmod -R 755 /var/www/api_nfe/templates

# 5. Restart
sudo systemctl restart api_nfe

# 6. Verificar
curl http://localhost:8080/api/v2/nfes
```

---

## 📊 MONITORAMENTO PÓS-DEPLOY

### Queries úteis do PostgreSQL:
```sql
-- Ver quantas API Keys existem
SELECT COUNT(*) FROM api_keys;

-- Ver últimas requisições
SELECT * FROM api_usage_logs ORDER BY request_time DESC LIMIT 10;

-- Ver webhooks configurados
SELECT webhook_id, url, ativo, eventos FROM webhooks;

-- Ver fila de webhooks pendentes
SELECT COUNT(*) FROM webhook_queue WHERE status = 'pending';

-- Ver estatísticas de uso por API Key
SELECT 
    ak.nome,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN aul.status_code >= 400 THEN 1 END) as errors
FROM api_keys ak
LEFT JOIN api_usage_logs aul ON ak.api_key_id = aul.api_key_id
WHERE aul.request_time > NOW() - INTERVAL '24 hours'
GROUP BY ak.nome;
```

---

## 🆘 ROLLBACK (Em caso de problemas)

### Reverter banco de dados:
```bash
# Restaurar backup
sudo -u postgres psql sjtnfe < backup_antes_api_v2_YYYYMMDD.sql
```

### Reverter código:
```bash
# Se fez backup
cd /var/backups/api_nfe
tar -xzf backup_codigo_YYYYMMDD.tar.gz -C /

# Ou via Git
cd /var/www/api_nfe
git checkout main
```

### Remover apenas as tabelas novas:
```sql
-- Se quiser apenas remover as novas tabelas
DROP TABLE IF EXISTS webhook_queue CASCADE;
DROP TABLE IF EXISTS webhooks CASCADE;
DROP TABLE IF EXISTS api_usage_logs CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
```

---

## 📝 NOTAS IMPORTANTES

1. **Sempre fazer backup antes do deploy**
2. **Testar em ambiente de desenvolvimento primeiro**
3. **Executar migration ANTES de reiniciar o serviço**
4. **Verificar logs após restart**
5. **Configurar webhook worker separadamente**
6. **Monitorar performance nas primeiras horas**

---

## 🔗 LINKS ÚTEIS

- Documentação completa: `/deployment/ARQUIVOS_API_V2_DEPLOY.md`
- Manual da API: `/docs/API_INTEGRACAO_MANUAL.md`
- Migration SQL: `/database/migrations/add_api_keys.sql`

---

**Data:** 18/12/2025  
**Versão:** API v2  
**Status:** Pronto para deploy ✅

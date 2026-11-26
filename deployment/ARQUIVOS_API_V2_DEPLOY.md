# 📋 Lista de Arquivos para Deploy - API v2

**Data:** 18 de dezembro de 2025  
**Versão:** API v2 - Sistema de API Keys e Webhooks  
**Branch:** lc214-migration

---

## ✅ CHECKLIST DE DEPLOY

### 🗄️ 1. BANCO DE DADOS (CRÍTICO - FAZER PRIMEIRO)

```bash
# Executar migration no servidor
psql -U postgres -d sjtnfe -f database/migrations/add_api_keys.sql
```

**Arquivo:**
- [ ] `database/migrations/add_api_keys.sql` (200 linhas)

**O que cria:**
- Tabela `api_keys` (armazenamento de API Keys)
- Tabela `api_usage_logs` (logs de requisições)
- Tabela `webhooks` (configuração de webhooks)
- Tabela `webhook_queue` (fila de entregas)
- 3 funções PostgreSQL (rate limiting, limpeza, update)
- 1 trigger automático
- 12 índices para performance

---

### 📦 2. MODELS (Database ORM)

**Arquivos Modificados:**
- [ ] `database/models.py` (adicionar 170 linhas após classe AssinaturaCliente)

**Classes Adicionadas:**
- `ApiKey` - Gerenciamento de API Keys
- `ApiUsageLog` - Logs de uso
- `Webhook` - Configuração de webhooks
- `WebhookQueue` - Fila de entregas

---

### 🔐 3. AUTENTICAÇÃO E SEGURANÇA

**Arquivos Novos:**
- [ ] `auth/api_key_auth.py` (270 linhas - NOVO)

**Funções:**
- `generate_api_key()` - Gera chaves seguras
- `verify_api_key()` - Valida API Keys
- `check_rate_limit()` - Controle de taxa
- `check_ip_whitelist()` - Validação de IP
- `log_api_request()` - Registro de requisições
- Decorators: `@require_api_key`, `@optional_api_key`

---

### 🛣️ 4. ROTAS (Routes/Controllers)

**Arquivos Novos:**
- [ ] `routes/api_keys_routes.py` (220 linhas - NOVO)
  - Blueprint: `api_keys_bp`
  - Gerenciamento web de API Keys
  - API endpoints: GET/POST keys, GET stats

- [ ] `routes/api_v2_routes.py` (350 linhas - NOVO)
  - Blueprint: `api_v2_bp`
  - POST /api/v2/nfe/emitir - Emissão de NFe
  - GET /api/v2/nfes - Listar NFes
  - GET /api/v2/nfe/{id} - Consultar NFe
  - GET /api/v2/nfe/{id}/xml - Download XML
  - POST /api/v2/nfe/{id}/cancelar - Cancelar NFe

- [ ] `routes/webhooks_routes.py` (200 linhas - NOVO)
  - Blueprint: `webhooks_bp`
  - Gerenciamento web de webhooks
  - API endpoints: GET/POST/DELETE webhooks

---

### 🔧 5. SERVIÇOS (Services/Business Logic)

**Arquivos Novos:**
- [ ] `services/webhook_service.py` (180 linhas - NOVO)

**Funções:**
- `trigger_webhook()` - Dispara webhooks
- `send_webhook()` - Envia notificações HTTP
- `calculate_signature()` - HMAC-SHA256
- `process_webhook_queue()` - Worker de fila
- `cleanup_old_webhook_logs()` - Limpeza

---

### 🎨 6. TEMPLATES HTML (Interface Web)

**Arquivos Novos:**

#### API Keys
- [ ] `templates/admin/api_keys/list.html` (190 linhas - NOVO)
  - Listagem de API Keys
  - Tabela com status e ações

- [ ] `templates/admin/api_keys/create.html` (280 linhas - NOVO)
  - Formulário de criação
  - Configuração de permissões

- [ ] `templates/admin/api_keys/stats.html` (250 linhas - NOVO)
  - Estatísticas de uso
  - Gráfico Chart.js
  - Últimas requisições

#### Webhooks
- [ ] `templates/admin/webhooks/list.html` (220 linhas - NOVO)
  - Listagem de webhooks
  - Eventos e estatísticas

- [ ] `templates/admin/webhooks/create.html` (280 linhas - NOVO)
  - Formulário de configuração
  - Seleção de eventos
  - Gerador de secret

---

### ⚙️ 7. APLICAÇÃO PRINCIPAL

**Arquivo Modificado:**
- [ ] `app.py` (adicionar 3 imports + 3 registros de blueprint)

**Mudanças:**
```python
# Adicionar imports (linha ~10)
from routes.api_keys_routes import api_keys_bp
from routes.api_v2_routes import api_v2_bp
from routes.webhooks_routes import webhooks_bp

# Adicionar registros (linha ~35)
app.register_blueprint(api_v2_bp)
app.register_blueprint(api_keys_bp)
app.register_blueprint(webhooks_bp)
```

---

### 📚 8. DOCUMENTAÇÃO

**Arquivo Modificado:**
- [ ] `docs/API_INTEGRACAO_MANUAL.md` (adicionar 400 linhas)

**Seções Adicionadas:**
- Autenticação por API Key
- Endpoints API v2 com exemplos
- Sistema de Webhooks
- Validação de assinatura HMAC
- Exemplos em Python, JavaScript, PHP

---

## 📦 RESUMO DE ARQUIVOS

### Arquivos Novos (10):
1. `database/migrations/add_api_keys.sql`
2. `auth/api_key_auth.py`
3. `routes/api_keys_routes.py`
4. `routes/api_v2_routes.py`
5. `routes/webhooks_routes.py`
6. `services/webhook_service.py`
7. `templates/admin/api_keys/list.html`
8. `templates/admin/api_keys/create.html`
9. `templates/admin/api_keys/stats.html`
10. `templates/admin/webhooks/list.html`
11. `templates/admin/webhooks/create.html`

### Arquivos Modificados (3):
1. `database/models.py` (+ 170 linhas)
2. `app.py` (+ 10 linhas)
3. `docs/API_INTEGRACAO_MANUAL.md` (+ 400 linhas)

### Total:
- **11 arquivos novos**
- **3 arquivos modificados**
- **~1990 linhas de código**

---

## 🚀 PROCEDIMENTO DE DEPLOY

### 1️⃣ Backup (SEMPRE PRIMEIRO!)
```bash
# Backup do banco de dados
pg_dump -U postgres sjtnfe > backup_antes_api_v2_$(date +%Y%m%d).sql

# Backup do código
tar -czf backup_codigo_$(date +%Y%m%d).tar.gz /var/www/api_nfe
```

### 2️⃣ Atualizar Código
```bash
cd /var/www/api_nfe

# Opção A: Via Git
git pull origin lc214-migration

# Opção B: Upload manual
# Fazer upload dos arquivos listados acima via FTP/SCP
```

### 3️⃣ Executar Migration do Banco
```bash
psql -U postgres -d sjtnfe -f database/migrations/add_api_keys.sql

# Verificar se tabelas foram criadas
psql -U postgres -d sjtnfe -c "\dt api_keys"
psql -U postgres -d sjtnfe -c "\dt webhooks"
```

### 4️⃣ Reiniciar Serviços
```bash
# Flask/Gunicorn
sudo systemctl restart api_nfe

# Ou se estiver usando supervisor
sudo supervisorctl restart api_nfe

# Verificar logs
tail -f /var/log/api_nfe/error.log
```

### 5️⃣ Testar Endpoints
```bash
# Teste básico
curl https://seu-servidor.com.br/api/v2/nfes

# Deve retornar: {"error": "API Key não fornecida"}
```

---

## ⚠️ ATENÇÕES ESPECIAIS

### 🔴 CRÍTICO:
1. **Executar migration ANTES de reiniciar aplicação**
2. **Fazer backup do banco ANTES da migration**
3. **Verificar se ambiente virtual está ativado**
4. **Conferir permissões dos novos arquivos**

### 🟡 IMPORTANTE:
1. **Webhook Worker**: Configurar serviço em background ou cron:
   ```bash
   # Criar /etc/systemd/system/webhook-worker.service
   # Ou adicionar ao cron:
   */5 * * * * cd /var/www/api_nfe && python3 -c "from services.webhook_service import process_webhook_queue; process_webhook_queue()"
   ```

2. **Bibliotecas Python**: Não há novas dependências, usa apenas bibliotecas já instaladas:
   - hmac (built-in)
   - hashlib (built-in)
   - secrets (built-in)
   - requests (já instalado)

3. **Permissões de Pastas**:
   ```bash
   chmod -R 755 /var/www/api_nfe/templates/admin/api_keys
   chmod -R 755 /var/www/api_nfe/templates/admin/webhooks
   chown -R www-data:www-data /var/www/api_nfe
   ```

---

## ✅ CHECKLIST PÓS-DEPLOY

Após o deploy, verificar:

- [ ] Tabelas criadas no banco (api_keys, webhooks, etc)
- [ ] App iniciou sem erros (conferir logs)
- [ ] Páginas de API Keys acessíveis (/admin/api-keys/{cliente_id})
- [ ] Páginas de Webhooks acessíveis (/admin/webhooks/{cliente_id})
- [ ] Criar uma API Key de teste
- [ ] Testar endpoint POST /api/v2/nfe/emitir
- [ ] Testar rate limiting (fazer 1001+ requisições)
- [ ] Criar webhook de teste
- [ ] Verificar worker de webhooks está rodando

---

## 📞 SUPORTE

**Em caso de problemas:**

1. **Erro ao criar tabelas:**
   - Verificar se usuário postgres tem permissões
   - Verificar se database existe
   - Conferir logs: `/var/log/postgresql/`

2. **Erro 500 ao acessar páginas:**
   - Verificar logs da aplicação
   - Verificar se blueprints foram registrados
   - Verificar imports

3. **API Key não funciona:**
   - Verificar se migration foi executada
   - Verificar formato do header: `Authorization: Bearer emx_live_xxxxx`
   - Verificar logs de api_usage_logs

4. **Webhooks não enviando:**
   - Verificar se worker está rodando
   - Verificar tabela webhook_queue
   - Verificar logs da aplicação

---

## 📊 MÉTRICAS DE SUCESSO

Após deploy, monitorar:

1. **Performance:**
   - Tempo de resposta dos novos endpoints
   - Taxa de erros 4xx/5xx
   - Uso de CPU/memória

2. **Uso:**
   - Número de API Keys criadas
   - Requisições por hora
   - Taxa de sucesso de webhooks

3. **Segurança:**
   - Rate limit violations
   - IPs bloqueados
   - Tentativas de uso de keys inválidas

---

**🎉 Boa sorte com o deploy!**

*Este documento foi gerado automaticamente em 18/12/2025*

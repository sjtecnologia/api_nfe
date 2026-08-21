# 📋 DEPLOY CHECKLIST - NF-e API

**Versão**: 1.0  
**Data**: 21/08/2026  
**Criado por**: Auditoria Fase 4.5 - Proteção de Regressão Incidente 20/08/2026

---

## 📌 Propósito

Este documento é um **checklist obrigatório** para todo deploy de changes na API NF-e.

**Objetivo**: Prevenir regressions como o incidente de 20/08/2026, onde a emissão de NF-e quebrou por:
- Arquivo desatualizado copiado no deploy
- CSRF token expirado
- Ação de emissão perdida no form submit

---

## 🚀 PRÉ-DEPLOY (Local - Antes de fazer commit)

### 1️⃣ Teste de Regressão Local

```bash
# Executar testes críticos
./pre_deploy_check.sh

# Esperado: ✅ VALIDAÇÃO PRÉ-DEPLOY PASSOU
```

**Se falhar**:
- Não fazer commit
- Revisar falhas críticas
- Corrigir localmente
- Reexecutar `./pre_deploy_check.sh`

### 2️⃣ Verificar Arquivo Correto

```bash
# Confirmar que routes/nfe_routes.py é mais recente
wc -l nfe_routes.py routes/nfe_routes.py

# Esperado: routes/ > nfe_routes (root)
# Exemplo: 5226 routes/nfe_routes.py
#          3976 nfe_routes.py
```

### 3️⃣ Verificar Template Correto

```bash
# Confirmar que templates/admin/nfes/emitir.html tem fixes
grep "a.value='emitir'" templates/admin/nfes/emitir.html
grep "/api/csrf-token" templates/admin/nfes/emitir.html

# Ambos devem retornar resultados
```

### 4️⃣ Verificar Blueprint em app.py

```bash
# Confirmar import correto
grep "from routes.nfe_routes import" app.py

# Não deve ter:
# grep "from nfe_routes import" app.py  (isso seria root)
```

### 5️⃣ Verificar Endpoint CSRF

```bash
# Confirmar que endpoint existe
grep "csrf_token_api" app.py
grep "/api/csrf-token" app.py

# Ambos devem retornar resultados
```

### 6️⃣ Commit & Push

```bash
# Apenas se todos os passos acima passarem
git add .
git commit -m "fix: proteção contra regressão incidente 20/08/2026"
git push origin main
```

---

## 📤 DURANTE DEPLOY (No servidor - Antes de aplicar)

### 7️⃣ Criar Backup Automático

**Verificar se deploy script faz backup**:
```bash
# Executar o script de deploy (ex: deploy_inutilizacao_aws.sh)
./deploy_inutilizacao_aws.sh

# O script PER SE criará:
# backups/backup_<timestamp>/ com cópia de:
#   - database/models.py
#   - services/sefaz_service.py
#   - routes/nfe_routes.py
#   - templates/admin/nfes/*.html
```

### 8️⃣ Verificar Arquivo Being Uploaded

**Script irá fazer upload de**:
- ✅ `routes/nfe_routes.py` (CORRETO)
- ✅ `templates/admin/nfes/emitir.html` (CORRETO)
- ✅ `app.py` com `/api/csrf-token` endpoint

**NUNCA deve fazer upload de**:
- ❌ `nfe_routes.py` da raiz (seria sobrescrever)
- ❌ `routes/emitir.html` (é template legado)

### 9️⃣ Verificar Permissions

```bash
# No servidor remoto (após deploy)
ls -lh routes/nfe_routes.py app.py
# Ambos devem ter 644 (readable)

# Se houver erro de permissão:
chmod 644 routes/nfe_routes.py app.py
```

---

## ✅ PÓS-DEPLOY (Validação - Depois de aplicar)

### 🔟 Reiniciar Serviço

```bash
# No servidor remoto
sudo systemctl restart api-nfe-principal

# Aguardar 5 segundos
sleep 5

# Verificar status
sudo systemctl status api-nfe-principal

# Esperado: active (running)
```

### 1️⃣1️⃣ Testes de Smoke (Validação Rápida)

```bash
# 1. Página de emissão carrega?
curl -I http://localhost:5000/admin/nfe/emitir?cliente_id=1

# Esperado: HTTP 302 (redirect login) ou HTTP 200 (if logged in)
# NÃO deve ser: HTTP 500

# 2. Endpoint CSRF existe?
curl -I http://localhost:5000/api/csrf-token

# Esperado: HTTP 302 ou 200 (se não requer auth)
# NÃO deve ser: HTTP 404 ou 500

# 3. Template carrega?
curl -s http://localhost:5000/admin/nfe/emitir?cliente_id=1 | grep -c "nfeForm"

# Esperado: 1 (encontrado 1 form)
```

### 1️⃣2️⃣ Testes Manuais (Validação Completa)

**No navegador, como Editor**:

1. **Login**
   - Acessar `/login`
   - Fazer login com usuário EDITOR

2. **Abrir Tela de Emissão**
   - Clicar em "Nova NF-e"
   - Página deve carregar SEM erro 500

3. **Verificar Campos**
   - Preenchimento de campo deve ser normal
   - Sem delays/travamentos

4. **Inspecionar Botão (DevTools - F12)**
   ```javascript
   // Console - Executar após carregar página
   document.querySelector('button[name=action][value=emitir]').onclick.toString()
   
   // Deve retornar função que:
   // ✓ Cria input action=emitir
   // ✓ Busca novo CSRF token
   // ✓ Faz submit nativo
   ```

5. **Confirmar Form com Rascunho**
   - Preencher alguns campos
   - Página deve salvar rascunho automaticamente
   - Recarregar página, dados devem estar lá

6. **Verificar Permissões**
   - Logout e fazer login como VIEWER
   - VIEWER não deve ter botão "Emitir" (ou deve estar desabilitado)

---

## 🚨 Checklist de Rollback (Se algo der errado)

Se após deploy houver erro, **antes de tudo**:

### ❌ Se POST /emitir não funciona (formulário reaparece)

**Sintomas**: Clica "Emitir" → página recarrega sem emitir

**Verificação**:
```bash
# No servidor
grep "action=emitir" templates/admin/nfes/emitir.html
grep "HTMLFormElement.prototype.submit" templates/admin/nfes/emitir.html

# Ambos devem retornar resultados
```

**Se falhar**: Restaurar de backup (veja ROLLBACK.md)

### ❌ Se /api/csrf-token retorna 404

**Sintomas**: Botão de emissão faz fetch que retorna 404

**Verificação**:
```bash
# No app.py
grep -A5 "@app.route('/api/csrf-token'" app.py

# Deve ter def csrf_token_api():
```

**Se falhar**: Restaurar app.py do backup

### ❌ Se Blueprint não está registrado

**Sintomas**: URL /admin/nfe/emitir retorna 404

**Verificação**:
```bash
# No app.py
grep "app.register_blueprint(nfe_bp" app.py

# Deve ter: app.register_blueprint(nfe_bp, url_prefix='/admin/nfe')
```

**Se falhar**: Restaurar app.py do backup

---

## 📋 Checklist Interativo (Copiar e Preencher)

```
PRÉ-DEPLOY:
☐ Executei ./pre_deploy_check.sh e passou
☐ Verifiquei que routes/nfe_routes.py > nfe_routes.py (tamanho)
☐ Verifiquei template correto tem action=emitir
☐ Verifiquei app.py importa de routes.nfe_routes
☐ Verifiquei endpoint /api/csrf-token existe
☐ Fiz git commit com mensagem clara

DURANTE:
☐ Script de deploy criou backup automático
☐ Script fez upload do arquivo CORRETO (routes/nfe_routes.py)
☐ Não houve erro durante upload/move

PÓS-DEPLOY:
☐ Serviço reiniciou com status "active (running)"
☐ Teste de smoke passou (curl requests)
☐ Página de emissão carrega sem erro 500
☐ Botão "Emitir" tem onclick correto (DevTools)
☐ Editor consegue acessar, Viewer está bloqueado
☐ Rascunho funciona
```

---

## 🔗 Referências

- **Incidente Original**: 20/08/2026 - NF-e emission broke
- **Root Cause Analysis**: `/docs/AUDITORIA_INCIDENTE_20260820.md`
- **Deep Analysis**: `/docs/AUDITORIA_PROFUNDA_FASE_4_5.md`
- **Regressão Testes**: `tests/test_nfe_critical_regression.py` (15 testes)
- **Pre-Deploy Gate**: `./pre_deploy_check.sh`
- **Rollback Procedure**: `/docs/ROLLBACK.md`

---

## 📞 Suporte

Se deploy falhar ou houver dúvidas:

1. **Consultar logs**:
   ```bash
   sudo journalctl -u api-nfe-principal -n 100
   ```

2. **Verificar backup**:
   ```bash
   ls -la backups/backup_*/
   ```

3. **Iniciar rollback**:
   ```bash
   ./ROLLBACK.md (seguir procedimento)
   ```

4. **Contactar responsável** se problema persistir

---

**Criado em**: 21/08/2026  
**Válido para**: Todos os deploys após incidente 20/08/2026  
**Review**: Mensal ou após mudanças críticas em rotas/templates

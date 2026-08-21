# 🔄 ROLLBACK PROCEDURE - NF-e API

**Versão**: 1.0  
**Data**: 21/08/2026  
**Propósito**: Procedimento para restaurar versão anterior após deploy com falha

---

## 🚨 Quando Usar Este Documento

Use este procedimento APENAS se:

- ❌ Após deploy, `/admin/nfe/emitir` retorna erro 500
- ❌ Botão "Emitir" não funciona (form reaparece ao clicar)
- ❌ Endpoint `/api/csrf-token` retorna 404
- ❌ Blueprint `/admin/nfe/*` não é registrado (404)
- ❌ NF-e emission está quebrada completamente
- ❌ Deploy script retornou erro durante aplicação

**Não use** se:
- ✓ Aplicação está funcionando normalmente
- ✓ Apenas features novas têm bugs (use fix incremental)
- ✓ Erro é em outro módulo (use targeted fix)

---

## 📋 Pré-Requisitos

Antes de começar, confirme que:

```bash
# 1. Backup foi criado automaticamente
ls -la backups/backup_*/

# Esperado: Múltiplos diretórios como:
# backups/backup_20260821_093500/
# backups/backup_20260821_093600/

# 2. SSH key está disponível
cat ~/.ssh/id_rsa > /dev/null 2>&1 && echo "OK" || echo "FAIL"

# 3. Servidor é acessível
ping -c 1 100.26.12.107 > /dev/null 2>&1 && echo "OK" || echo "FAIL"
```

---

## 🔄 PASSO 1: Parar o Serviço (Evitar Estado Inconsistente)

```bash
# No servidor remoto

# Opção 1: Via SSH direto
ssh -i ~/.ssh/nfe-new-api-key.pem ubuntu@100.26.12.107 << 'EOF'
  echo "🛑 Parando serviço..."
  sudo systemctl stop api-nfe-principal
  sleep 2
  sudo systemctl status api-nfe-principal
  echo "✅ Serviço parado"
EOF

# Opção 2: Se tiver acesso SSH local
sudo systemctl stop api-nfe-principal
sudo systemctl status api-nfe-principal
```

**Esperado**: `inactive (dead)` ou `Unit not found`

---

## 🔄 PASSO 2: Identificar o Backup Mais Recente

```bash
# No servidor remoto
ssh -i ~/.ssh/nfe-new-api-key.pem ubuntu@100.26.12.107 << 'EOF'
  cd /home/ubuntu/api_nfe
  
  echo "Backups disponíveis:"
  ls -lhtr backups/backup_*/ | tail -5
  
  # Mostrar conteúdo do backup mais recente
  LATEST=$(ls -td backups/backup_*/ | head -1)
  echo ""
  echo "Backup mais recente: $LATEST"
  ls -lh "$LATEST"
EOF
```

**Esperado**: Ver pastas com timestamp recente, contendo:
- database/models.py
- services/sefaz_service.py
- routes/nfe_routes.py
- templates/admin/nfes/emitir.html
- app.py (se foi modificado)

---

## 🔄 PASSO 3: Restaurar Arquivos do Backup

```bash
# No servidor remoto
ssh -i ~/.ssh/nfe-new-api-key.pem ubuntu@100.26.12.107 << 'EOF'
  cd /home/ubuntu/api_nfe
  
  # Encontrar backup mais recente
  LATEST_BACKUP=$(ls -td backups/backup_*/ | head -1)
  echo "📦 Restaurando de: $LATEST_BACKUP"
  
  # Restaurar cada arquivo
  echo ""
  echo "Restaurando routes/nfe_routes.py..."
  [ -f "${LATEST_BACKUP}nfe_routes.py" ] && cp "${LATEST_BACKUP}nfe_routes.py" routes/nfe_routes.py
  
  echo "Restaurando templates/admin/nfes/emitir.html..."
  [ -f "${LATEST_BACKUP}emitir.html" ] && cp "${LATEST_BACKUP}emitir.html" templates/admin/nfes/emitir.html
  
  echo "Restaurando database/models.py..."
  [ -f "${LATEST_BACKUP}models.py" ] && cp "${LATEST_BACKUP}models.py" database/models.py
  
  echo "Restaurando services/sefaz_service.py..."
  [ -f "${LATEST_BACKUP}sefaz_service.py" ] && cp "${LATEST_BACKUP}sefaz_service.py" services/sefaz_service.py
  
  echo "Restaurando app.py..."
  [ -f "${LATEST_BACKUP}app.py" ] && cp "${LATEST_BACKUP}app.py" app.py
  
  # Verificar restauração
  echo ""
  echo "✅ Arquivos restaurados"
  ls -lh routes/nfe_routes.py templates/admin/nfes/emitir.html app.py | awk '{print $9, "(" $5 ")"}'
EOF
```

**O que fazer se um arquivo não foi restaurado**:
```bash
# Se nfe_routes.py não está no backup, restaurar do Git
git checkout HEAD~1 routes/nfe_routes.py

# Se template não está, restaurar versão anterior conhecida como boa
git log --oneline templates/admin/nfes/emitir.html | head -3
git checkout <commit-hash> templates/admin/nfes/emitir.html
```

---

## 🔄 PASSO 4: Restaurar Permissões

```bash
# No servidor remoto
ssh -i ~/.ssh/nfe-new-api-key.pem ubuntu@100.26.12.107 << 'EOF'
  cd /home/ubuntu/api_nfe
  
  echo "📝 Restaurando permissões..."
  
  # Flask app deve ser readable por www-data
  sudo chmod 644 app.py routes/nfe_routes.py
  sudo chmod 644 templates/admin/nfes/emitir.html
  
  # Models e services
  sudo chmod 644 database/models.py services/sefaz_service.py
  
  # Ownership (se necessário)
  sudo chown ubuntu:ubuntu app.py routes/nfe_routes.py
  
  echo "✅ Permissões restauradas"
  ls -lh app.py routes/nfe_routes.py | awk '{print $1, $9}'
EOF
```

---

## 🔄 PASSO 5: Purgar Cache Python

```bash
# No servidor remoto
ssh -i ~/.ssh/nfe-new-api-key.pem ubuntu@100.26.12.107 << 'EOF'
  cd /home/ubuntu/api_nfe
  
  echo "🧹 Limpando cache Python..."
  
  # Remover __pycache__
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
  find . -name "*.pyc" -delete 2>/dev/null || true
  
  # Remover cache de compilação
  rm -rf .pytest_cache 2>/dev/null || true
  
  echo "✅ Cache limpo"
EOF
```

---

## 🔄 PASSO 6: Iniciar Serviço e Validar

```bash
# No servidor remoto
ssh -i ~/.ssh/nfe-new-api-key.pem ubuntu@100.26.12.107 << 'EOF'
  echo "▶️  Iniciando serviço..."
  sudo systemctl start api-nfe-principal
  
  # Aguardar início
  sleep 3
  
  # Verificar status
  RESULT=$(sudo systemctl status api-nfe-principal)
  echo "$RESULT"
  
  # Verificar se está running
  if echo "$RESULT" | grep -q "active (running)"; then
    echo "✅ Serviço iniciado com sucesso"
  else
    echo "❌ Serviço não iniciou - verificar logs:"
    sudo journalctl -u api-nfe-principal -n 50
    exit 1
  fi
EOF
```

**Se serviço não inicia**:
```bash
# Ver logs completos
ssh ubuntu@100.26.12.107 "sudo journalctl -u api-nfe-principal -n 200"

# Verificar sintaxe Python
ssh ubuntu@100.26.12.107 "python3 -m py_compile app.py routes/nfe_routes.py"

# Se houver erro, precisará de rollback manual
```

---

## 🔄 PASSO 7: Testes de Smoke (Validar Funcionamento)

```bash
# Em sua máquina local (ou terminal remoto)

# 1. Testar HTTP Status
curl -I http://100.26.12.107/admin/nfe/emitir?cliente_id=1
# Esperado: HTTP 302 (redirect) ou 200 (se logado)

# 2. Testar CSRF Endpoint
curl http://100.26.12.107/api/csrf-token
# Esperado: JSON com csrf_token ou 302 redirect

# 3. Testar página renderiza
curl -s http://100.26.12.107/admin/nfe/emitir?cliente_id=1 | grep -c "nfeForm"
# Esperado: 1 (encontrado 1 ocorrência)

# 4. Verificar logs não têm erro 500
ssh ubuntu@100.26.12.107 "sudo journalctl -u api-nfe-principal | grep '500' || echo 'Nenhum erro 500'"
```

**Se testes passarem**: ✅ Rollback bem-sucedido

**Se testes falharem**: Voltar para PASSO 6 e revisar logs

---

## 🔄 PASSO 8: Testes Manuais (Validar Funcionamento Completo)

### Teste 1: Página carrega sem erro

1. No navegador, acessar: `http://100.26.12.107/admin/nfe/emitir?cliente_id=1`
2. Fazer login se solicitado
3. Verificar que **não há erro 500**
4. ✅ Esperado: Formulário de emissão carrega

### Teste 2: Botão de Emissão funciona

1. Abrir DevTools (F12)
2. Ir para aba "Console"
3. Executar:
   ```javascript
   document.querySelector('button[name=action][value=emitir]').click()
   ```
4. ✅ Esperado: Form é enviado (será redirecionado ou aparecerá resposta)

### Teste 3: Permissões funcionam

1. **Logout** de editor
2. Fazer login como **VIEWER**
3. Tentar acessar `/admin/nfe/emitir`
4. ✅ Esperado: Acesso bloqueado (403) ou botão desabilitado

### Teste 4: Rascunho funciona

1. Fazer login como EDITOR
2. Abrir página de emissão
3. Preencher alguns campos
4. Recarregar página (F5)
5. ✅ Esperado: Dados que preencheu ainda estão lá

---

## ✅ PASSO 9: Documentar Rollback

```bash
# Documentar em arquivo local para auditoria

cat > ROLLBACK_LOG_$(date +%Y%m%d_%H%M%S).txt << 'EOF'
ROLLBACK EXECUTADO
==================
Data: $(date)
Motivo: [DESCREVER MOTIVO]

Backup Restaurado:
  Timestamp: [ver backup mais recente]
  Arquivos:
    - routes/nfe_routes.py
    - templates/admin/nfes/emitir.html
    - database/models.py
    - services/sefaz_service.py
    - app.py

Testes Pós-Rollback:
  ✅ Serviço iniciou com sucesso
  ✅ HTTP /admin/nfe/emitir retorna 200/302
  ✅ /api/csrf-token funciona
  ✅ Página renderiza sem erro 500
  ✅ Testes manuais passaram

Próximas Ações:
  [ ] Revisar o que causou o problema
  [ ] Criar patch/hotfix
  [ ] Testar novamente em staging
  [ ] Deploy novamente com pré-deploy-check
EOF

echo "📋 Rollback documentado em: ROLLBACK_LOG_*.txt"
```

---

## 📊 Checklist de Rollback

```
PRÉ-ROLLBACK:
☐ Confirmei que erro é crítico (NF-e está quebrada)
☐ Identifiquei timestamp do backup mais recente
☐ Tenho acesso SSH com key privada

DURANTE:
☐ Parei o serviço (systemctl stop)
☐ Restaurei todos os arquivos do backup
☐ Restaurei permissões (chmod 644)
☐ Limpei cache Python
☐ Reiniciei serviço (systemctl start)

PÓS:
☐ Serviço está com status "active (running)"
☐ Testes de smoke passaram (curl requests)
☐ Testes manuais passaram (navegador)
☐ Documentei o rollback em arquivo
```

---

## 🆘 Se Rollback Também Falhar

Se mesmo após restaurar do backup a aplicação não funciona:

### 1. Verificar Log Completo
```bash
ssh ubuntu@100.26.12.107 "sudo journalctl -u api-nfe-principal --lines=500"
```

### 2. Verificar Sintaxe Python
```bash
ssh ubuntu@100.26.12.107 << 'EOF'
python3 -m py_compile app.py
python3 -m py_compile routes/nfe_routes.py
python3 -m py_compile database/models.py
EOF
```

### 3. Verificar Banco de Dados
```bash
ssh ubuntu@100.26.12.107 << 'EOF'
# Verificar que DB não ficou corrompido
sqlite3 /home/ubuntu/api_nfe/instance/nfe.db ".tables" | wc -w
# Esperado: > 10 (muitas tabelas)

# Se < 10, precisa restaurar backup do banco também
EOF
```

### 4. Última Opção: Rollback Completo
```bash
# Restaurar backup ANTERIOR ao anterior
ssh ubuntu@100.26.12.107 << 'EOF'
  cd /home/ubuntu/api_nfe
  OLDER_BACKUP=$(ls -td backups/backup_*/ | head -2 | tail -1)
  echo "Restaurando backup mais antigo: $OLDER_BACKUP"
  
  # Restaurar tudo
  cp -r "$OLDER_BACKUP"* ./
  
  # Limpar cache e reiniciar
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
  sudo systemctl restart api-nfe-principal
EOF
```

---

## 📞 Se Nada Funcionar

**Contactar responsável de DevOps** com:

1. **Arquivo de log completo**:
   ```bash
   sudo journalctl -u api-nfe-principal --lines=1000 > nfe_error.log
   ```

2. **Timestamp do deploy que falhou**:
   ```bash
   ls -lhtr backups/backup_*/ | tail -1
   ```

3. **Último backup funcional** (se souber qual era):
   ```bash
   git log --oneline | head -10
   ```

4. **Descrição do erro observado**:
   - Página retorna 500?
   - Formulário não submete?
   - Permissões quebradas?
   - CSRF não funciona?

---

## 📚 Referências

- **Deploy Checklist**: `/docs/DEPLOY_CHECKLIST.md`
- **Pre-Deploy Check Script**: `./pre_deploy_check.sh`
- **Audit Report**: `/docs/AUDITORIA_PROFUNDA_FASE_4_5.md`
- **Incidente Original**: `/docs/AUDITORIA_INCIDENTE_20260820.md`

---

**Criado em**: 21/08/2026  
**Válido para**: Todos os rollbacks após incidente 20/08/2026  
**Responsável**: DevOps / Release Manager

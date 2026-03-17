# 📦 ARQUIVOS PARA DEPLOY - IMPLEMENTAÇÃO CRT=3 (LUCRO REAL/PRESUMIDO)

**Data:** 11 de dezembro de 2025  
**Branch:** lc214-migration  
**Funcionalidade:** Suporte completo para CRT=3 com IBS/CBS e ICMS 60

---

## 🔴 ARQUIVOS CRÍTICOS (OBRIGATÓRIOS)

### 1. Backend - Serviços
```
services/ibs_cbs_service.py                    [NOVO]
```
- Serviço principal para cálculo de IBS/CBS
- Funções: calcular_ibs_cbs(), gerar_xml_ibscbs(), gerar_xml_totais_ibscbs()

### 2. Backend - Rotas Admin
```
routes/admin_routes.py                         [MODIFICADO]
```
- **Linhas modificadas:**
  - ~4870-4920: Correção de rotas API (removido /admin/ duplicado)
  - ~4920-4970: Correção de SessionLocal() para queries
  - ~5270-5370: 5 novas rotas CRUD para Classificações IBS/CBS
    * list_classificacoes_ibs_cbs()
    * criar_classificacao_ibs_cbs()
    * editar_classificacao_ibs_cbs()
    * salvar_classificacao_ibs_cbs()
    * toggle_classificacao_ibs_cbs()

### 3. Frontend - Templates Admin (Novos)
```
templates/admin/classificacoes_ibs_cbs/list.html    [NOVO]
templates/admin/classificacoes_ibs_cbs/form.html    [NOVO]
```
- Interface completa para gerenciar classificações IBS/CBS
- Filtros, listagem, criação, edição e toggle de status

### 4. Frontend - Template Base
```
templates/base.html                            [MODIFICADO]
```
- **Linha ~730:** Adicionado item de menu "Classificações IBS/CBS" no dropdown Tabelas

### 5. Frontend - Emissão de NFe
```
templates/admin/nfes/emitir.html              [MODIFICADO]
```
- **Linhas ~480-555:** Seção IBS/CBS (visível para CRT=3)
- **Linhas ~557-580:** Removida seção de Autorizações XML (não usaremos)
- **Linhas ~1850-1880:** JavaScript verificarRegimeTributario()
- **Linhas ~1940-1955:** Removida função adicionarAutorizacao()

---

## 🟡 ARQUIVOS DE SUPORTE (RECOMENDADOS)

### 6. Banco de Dados
```
deployment/atualizacao_crt3.sql               [EXECUTAR NO SERVIDOR]
```
- Cria tabela `classificacoes_ibs_cbs`
- Insere 3 classificações padrão (Medicamentos, Dispositivos, Agropecuários)
- Adiciona coluna `classificacao_ibs_cbs_id` em produtos

### 7. Documentação
```
docs/IMPLEMENTACAO_CRT3_LUCRO_REAL_PRESUMIDO.md
docs/FRONTEND_CRT3_IMPLEMENTADO.md
ATUALIZACAO_DANFE_MODAL.md
```

---

## 📋 CHECKLIST DE DEPLOYMENT

### PASSO 1: Backup (OBRIGATÓRIO)
```bash
# No servidor Windows
cd C:\EmiteMax\api_nfe
mkdir backup_pre_crt3_%date:~-4,4%%date:~-7,2%%date:~-10,2%

# Backup dos arquivos que serão modificados
copy routes\admin_routes.py backup_pre_crt3_*\
copy templates\base.html backup_pre_crt3_*\
copy templates\admin\nfes\emitir.html backup_pre_crt3_*\```

### PASSO 2: Upload de Arquivos Novos
```
📁 Criar diretórios:
   - services/ (se não existir)
   - templates/admin/classificacoes_ibs_cbs/

📤 Upload via FTP/SFTP:
   - services/ibs_cbs_service.py
   - templates/admin/classificacoes_ibs_cbs/list.html
   - templates/admin/classificacoes_ibs_cbs/form.html
```

### PASSO 3: Substituir Arquivos Modificados
```
📤 Sobrescrever:
   - routes/admin_routes.py
   - templates/base.html
   - templates/admin/nfes/emitir.html
```

### PASSO 4: Atualizar Banco de Dados
```sql
-- Conectar no PostgreSQL do servidor
psql -U postgres -d sjtnfe

-- Executar script
\i C:\EmiteMax\api_nfe\deployment\atualizacao_crt3.sql

-- Verificar
SELECT COUNT(*) FROM classificacoes_ibs_cbs;  -- Deve retornar 3
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'produtos' AND column_name = 'classificacao_ibs_cbs_id';
```

### PASSO 5: Reiniciar Serviço
```bash
# Windows Server
net stop EmiteMaxAPI
net start EmiteMaxAPI

# Ou reiniciar via Task Manager / Serviços
```

### PASSO 6: Validação
```
✅ Acessar: http://IP_SERVIDOR/admin/classificacoes-ibs-cbs
✅ Verificar se lista 3 classificações
✅ Testar criar nova classificação
✅ Criar cliente com CRT=3 (Lucro Real)
✅ Emitir NFe e verificar se campos IBS/CBS aparecem
✅ Verificar logs em: C:\EmiteMax\api_nfe\logs\
```

---

## 🔧 ESTRUTURA DE DIRETÓRIOS NO SERVIDOR

```
C:\EmiteMax\api_nfe\
│
├── routes\
│   └── admin_routes.py                    [SUBSTITUIR]
│
├── services\
│   └── ibs_cbs_service.py                 [NOVO]
│
├── templates\
│   ├── base.html                          [SUBSTITUIR]
│   └── admin\
│       ├── nfes\
│       │   └── emitir.html                [SUBSTITUIR]
│       └── classificacoes_ibs_cbs\        [CRIAR PASTA]
│           ├── list.html                  [NOVO]
│           └── form.html                  [NOVO]
│
└── deployment\
    └── atualizacao_crt3.sql               [EXECUTAR]
```

---

## ⚠️ PONTOS DE ATENÇÃO

### 1. Dependências Python
O arquivo `services/ibs_cbs_service.py` não requer novas dependências.
Usa apenas: `decimal.Decimal` (built-in Python)

### 2. Permissões de Arquivo
Certificar que o usuário do serviço tem permissão de leitura em:
- `services/ibs_cbs_service.py`
- `templates/admin/classificacoes_ibs_cbs/*`

### 3. Compatibilidade
Esta implementação é **compatível** com clientes existentes:
- CRT=1 (Simples Nacional): Continua funcionando normalmente
- CRT=2 (Simples Nacional - Excesso): Continua funcionando normalmente
- CRT=3 (Novo): Agora com suporte completo IBS/CBS

### 4. Rollback
Se necessário reverter:
```bash
# Restaurar arquivos do backup
copy backup_pre_crt3_*\admin_routes.py routes\
copy backup_pre_crt3_*\base.html templates\
copy backup_pre_crt3_*\emitir.html templates\admin\nfes\

# Remover arquivos novos
del services\ibs_cbs_service.py
rmdir /s templates\admin\classificacoes_ibs_cbs

# Reverter banco (se necessário)
ALTER TABLE produtos DROP COLUMN IF EXISTS classificacao_ibs_cbs_id;
DROP TABLE IF EXISTS classificacoes_ibs_cbs;

# Reiniciar serviço
net stop EmiteMaxAPI
net start EmiteMaxAPI
```

---

## 📊 RESUMO

| Tipo | Quantidade | Ação |
|------|------------|------|
| Arquivos Novos | 3 | Upload |
| Arquivos Modificados | 3 | Substituir |
| Scripts SQL | 1 | Executar |
| **TOTAL** | **7** | - |

**Tempo estimado de deployment:** 15-20 minutos

---

## 🆘 SUPORTE

Em caso de problemas após deployment:

1. **Verificar logs:**
   ```
   C:\EmiteMax\api_nfe\logs\app.log
   C:\EmiteMax\api_nfe\logs\error.log
   ```

2. **Testar rotas manualmente:**
   ```
   http://IP_SERVIDOR/admin/api/regime-tributario/14
   http://IP_SERVIDOR/admin/api/classificacoes-ibs-cbs
   ```

3. **Verificar Flask está rodando:**
   ```powershell
   netstat -ano | findstr :8080
   ```

4. **Contato:** Verificar logs de erro e reportar stack trace completo

---

**✅ FIM DO DOCUMENTO**

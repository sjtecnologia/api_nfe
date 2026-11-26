# Guia de Deploy - Servidor Windows

## 🚨 Erro Atual: Internal Server Error

Você está vendo "Internal Server Error" porque provavelmente:
1. ❌ A coluna `logo_path` não foi criada no banco
2. ❌ As engines do DANFE não estão instaladas
3. ❌ O serviço não foi reiniciado após as mudanças

## 🔧 Solução Passo a Passo

### Passo 1: Transferir Arquivos Atualizados

**Arquivos que DEVEM ser substituídos no servidor:**

```powershell
# No servidor Windows (C:\nfe_app\)
# Faça backup primeiro!
cd C:\nfe_app

# Backup dos arquivos atuais
copy services\danfe_service.py services\danfe_service.py.backup
copy routes\nfe_routes.py routes\nfe_routes.py.backup
copy services\nfe_service.py services\nfe_service.py.backup
copy routes\admin_routes.py routes\admin_routes.py.backup
copy database\models.py database\models.py.backup
```

**Agora substitua esses 5 arquivos:**
- `services/danfe_service.py` ⭐ CRÍTICO
- `routes/nfe_routes.py` ⭐ CRÍTICO
- `services/nfe_service.py`
- `routes/admin_routes.py`
- `database/models.py`

**E esses 2 templates:**
- `templates/admin/nfes/emitir.html`
- `templates/admin/clientes/form.html`

**E esses 2 scripts de diagnóstico:**
- `diagnostico_servidor.py` (NOVO)
- `adicionar_campo_logo_cliente.sql`

### Passo 2: Ativar Virtual Environment

```powershell
cd C:\nfe_app
.\venv\Scripts\activate
```

### Passo 3: Instalar Dependências

```powershell
# Instalar engines do DANFE
pip install brazilnum
pip install BrazilFiscalReport
pip install erpbrasil.edoc.pdf

# Verificar instalação
pip list | findstr -i "brazil"
```

**Deve mostrar:**
```
BrazilFiscalReport    0.5.33
brazilnum             0.8.8
erpbrasil.base        2.1.3
erpbrasil.edoc.pdf    2.1.4
```

### Passo 4: Executar Migration SQL

```powershell
# Descobrir o nome do banco de dados
# Abra config.py ou .env e veja DATABASE_URL

# Executar migration
psql -U postgres -d nome_do_banco -f adicionar_campo_logo_cliente.sql

# OU se não tiver psql no PATH:
"C:\Program Files\PostgreSQL\14\bin\psql.exe" -U postgres -d nome_do_banco -f adicionar_campo_logo_cliente.sql
```

**Se der erro "psql não encontrado", execute direto no pgAdmin:**
```sql
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS logo_path VARCHAR(255) DEFAULT NULL;
COMMENT ON COLUMN clientes.logo_path IS 'Caminho do arquivo de logo do cliente';
```

### Passo 5: Criar Diretório de Logos

```powershell
# Criar diretório para logos
New-Item -ItemType Directory -Force -Path C:\nfe_app\static\logos

# Verificar
dir C:\nfe_app\static
```

### Passo 6: Executar Diagnóstico

```powershell
cd C:\nfe_app
python diagnostico_servidor.py
```

**O que o diagnóstico vai verificar:**
- ✅ Imports funcionando
- ✅ Engines instaladas
- ✅ Coluna logo_path existe
- ✅ Diretórios criados
- ✅ Geração de DANFE funcionando

**Resultado esperado:**
```
================================================================================
DIAGNÓSTICO DO SERVIDOR - NFe App
================================================================================

1️⃣ Testando imports básicos...
   ✅ services.danfe_service OK
   ✅ routes.nfe_routes OK

2️⃣ Testando dependências do DANFE...
   ✅ brazilnum instalado
   ✅ BrazilFiscalReport instalado
   ✅ erpbrasil.edoc.pdf instalado
   ✅ DanfeConfig disponível

3️⃣ Testando conexão com banco de dados...
   ✅ Coluna logo_path existe na tabela clientes
   📊 0 cliente(s) com logo cadastrada
   ✅ Conexão com banco OK

4️⃣ Testando estrutura de diretórios...
   ✅ static existe
   ✅ static/logos existe
   ✅ static/img existe
   ✅ static/danfe existe

5️⃣ Testando geração de DANFE...
   ✅ DANFE gerado com sucesso: static/danfe/danfe_999999.pdf
```

### Passo 7: Reiniciar Serviço

```powershell
# Parar serviço
nssm stop NFe_Backend

# Aguardar 5 segundos
Start-Sleep -Seconds 5

# Iniciar serviço
nssm start NFe_Backend

# Verificar status
nssm status NFe_Backend
```

**Deve mostrar:**
```
SERVICE_RUNNING
```

### Passo 8: Verificar Logs

```powershell
# Ver últimas 50 linhas do log
Get-Content C:\nfe_app\logs\service.log -Tail 50

# Procurar por erros
Get-Content C:\nfe_app\logs\service.log -Tail 200 | Select-String -Pattern "ERROR|Exception|Traceback|cliente_id|logo_path"
```

### Passo 9: Testar no Navegador

1. **Acesse:** http://localhost:8080 (ou porta configurada)
2. **Login** com suas credenciais
3. **Teste 1 - Cadastro de Cliente:**
   - Menu → Clientes → Novo Cliente
   - Preencha os dados básicos
   - **Faça upload de uma logo** (PNG/JPG)
   - Salve
   - ✅ Verifique se aparece a logo no preview

4. **Teste 2 - Emissão de NFe:**
   - Menu → NFe → Emitir NFe
   - Preencha os dados básicos
   - **Preencha dados da transportadora:**
     - Nome da Transportadora
     - CNPJ
     - **Registro ANTT** (novo campo!)
     - Placa
     - UF
     - **Marca dos Volumes** (novo campo!)
     - **Numeração dos Volumes** (novo campo!)
     - Quantidade, Espécie, Peso
   - Marque **"Gerar DANFE automaticamente"**
   - **Emita em HOMOLOGAÇÃO** (ambiente = 2)
   
5. **Verificar DANFE:**
   - Baixe o PDF gerado
   - ✅ Deve ser "oficial" (não simplificado)
   - ✅ Logo deve aparecer no cabeçalho
   - ✅ Campos da transportadora devem aparecer (ANTT, Marca, Numeração)

## 🐛 Troubleshooting

### Erro: "Internal Server Error" persiste

**Causa:** Arquivo Python com erro de sintaxe ou import faltando

**Solução:**
```powershell
# Testar imports manualmente
python -c "from services.danfe_service import generate_danfe; print('OK')"
python -c "from routes.nfe_routes import nfe_bp; print('OK')"
```

### Erro: "column logo_path does not exist"

**Causa:** Migration SQL não foi executada

**Solução:**
```sql
-- Executar no pgAdmin ou psql
ALTER TABLE clientes ADD COLUMN logo_path VARCHAR(255);
```

### Erro: "No module named 'brazilfiscalreport'"

**Causa:** Dependências não instaladas

**Solução:**
```powershell
.\venv\Scripts\activate
pip install BrazilFiscalReport brazilnum erpbrasil.edoc.pdf
```

### DANFE continua "simplificado"

**Causa:** Engines não carregaram ou erro no import

**Verificar logs:**
```powershell
Get-Content C:\nfe_app\logs\service.log -Tail 100 | Select-String -Pattern "engine|PDF|DANFE"
```

**Deve mostrar:**
```
✅ PDF gerado com engine brazilfiscalreport, tamanho: 45678 bytes
```

### Logo não aparece no DANFE

**Causas possíveis:**
1. DanfeConfig não disponível
2. Arquivo de logo não existe
3. Path errado

**Verificar logs:**
```powershell
Get-Content C:\nfe_app\logs\service.log -Tail 100 | Select-String -Pattern "logo"
```

**Deve mostrar:**
```
✅ Logo configurada: C:\nfe_app\static\logos\cliente_1733164800.png
```

## 📋 Checklist Final

- [ ] 7 arquivos substituídos no servidor
- [ ] Virtual environment ativado
- [ ] Engines instaladas (brazilnum, BrazilFiscalReport, erpbrasil.edoc.pdf)
- [ ] Migration SQL executada (coluna logo_path criada)
- [ ] Diretório static/logos criado
- [ ] Diagnóstico executado com sucesso (todos ✅)
- [ ] Serviço reiniciado (nssm restart NFe_Backend)
- [ ] Logs verificados (sem erros)
- [ ] Teste de upload de logo OK
- [ ] Teste de emissão de NFe com transportadora OK
- [ ] DANFE gerado como "oficial" (não simplificado)
- [ ] Logo aparece no DANFE
- [ ] Campos ANTT/Marca/Numeração aparecem no DANFE

## 🎯 Resumo do que foi corrigido

### ✅ Transportadora
- Adicionados 3 campos novos: ANTT, Marca, Numeração
- Captura correta no backend
- Geração de XML com tags corretas

### ✅ Logo do Cliente
- Campo logo_path no banco de dados
- Upload de logo no cadastro de clientes
- Logo integrada ao DANFE oficial

### ✅ DANFE Oficial
- Engines instaladas (BrazilFiscalReport)
- DanfeConfig com logo
- Tratamento de erros robusto

### ✅ Bugs Corrigidos
- `cliente_id` → `emitente_cliente_id` (3 locais)
- Paths relativos → absolutos
- Verificação se coluna logo_path existe

---

**Data:** 02/12/2025  
**Versão:** 1.2  
**Status:** ✅ Pronto para deploy

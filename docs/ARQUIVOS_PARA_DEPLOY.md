# Arquivos para Deploy - Correção DANFE + Transportadora + Logo

## 📁 Arquivos Python Modificados

### 1. **services/danfe_service.py** ⭐ PRINCIPAL
**Mudanças:**
- Adicionada integração com logo do cliente (query no banco)
- Configuração `DanfeConfig` com logo
- Correção do nome da engine: `"brazilfiscalreport"` (minúsculo)
- Conversão de paths relativos para absolutos
- Logs detalhados para debug

**Path no servidor:**
```
/caminho/api_nfe/services/danfe_service.py
```

### 2. **routes/nfe_routes.py** ⭐ PRINCIPAL
**Mudanças:**
- Captura dos 3 novos campos: `transportadoraANTT`, `volumeMarca`, `volumeNumeracao`
- Correção: `cliente_id` → `emitente_cliente_id` (3 locais - linhas 396, 852, 914)
- Passa `cliente_id` para `generate_danfe()`

**Path no servidor:**
```
/caminho/api_nfe/routes/nfe_routes.py
```

### 3. **services/nfe_service.py**
**Mudanças:**
- Geração de tag `<RNTC>` (ANTT da transportadora)
- Geração de tag `<marca>` (marca dos volumes)
- Geração de tag `<nVol>` (numeração dos volumes)

**Path no servidor:**
```
/caminho/api_nfe/services/nfe_service.py
```

### 4. **routes/admin_routes.py**
**Mudanças:**
- Upload de logo no `create_cliente` (linhas ~2515-2535)
- Upload de logo no `edit_cliente` (linhas ~2750-2785)
- Validação de extensão (.png, .jpg, .jpeg, .gif)
- Salvamento em `static/logos/` com nome único

**Path no servidor:**
```
/caminho/api_nfe/routes/admin_routes.py
```

### 5. **database/models.py**
**Mudanças:**
- Adicionado campo `logo_path = Column(String(255), nullable=True)` na classe `Cliente`

**Path no servidor:**
```
/caminho/api_nfe/database/models.py
```

## 📄 Templates HTML Modificados

### 6. **templates/admin/nfes/emitir.html**
**Mudanças:**
- Adicionados 3 campos de transportadora:
  - `transportadoraANTT` (Registro ANTT)
  - `volumeMarca` (Marca dos volumes)
  - `volumeNumeracao` (Numeração dos volumes)

**Path no servidor:**
```
/caminho/api_nfe/templates/admin/nfes/emitir.html
```

### 7. **templates/admin/clientes/form.html**
**Mudanças:**
- Adicionado campo de upload de logo
- Preview da logo atual
- Input type="file" com accept="image/png,image/jpeg,image/jpg,image/gif"

**Path no servidor:**
```
/caminho/api_nfe/templates/admin/clientes/form.html
```

## 🗄️ Banco de Dados

### 8. **SQL Migration: adicionar_campo_logo_cliente.sql**
**Executar no PostgreSQL:**
```sql
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS logo_path VARCHAR(255) DEFAULT NULL;
COMMENT ON COLUMN clientes.logo_path IS 'Caminho do arquivo de logo do cliente';
```

**Como executar:**
```bash
psql -U postgres -d nome_do_banco -f adicionar_campo_logo_cliente.sql
```

## 📦 Dependências Python

### 9. **Instalar no servidor:**
```bash
# Ativar virtualenv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar engines de DANFE
pip install brazilnum
pip install BrazilFiscalReport
pip install erpbrasil.edoc.pdf
```

**Versões instaladas:**
- `brazilnum==0.8.8`
- `BrazilFiscalReport==0.5.33`
- `erpbrasil.edoc.pdf==2.1.4`
- `fpdf2>=2.8.3` (dependência)
- `python-barcode` (dependência)
- `phonenumbers` (dependência)

## 📂 Estrutura de Diretórios

### 10. **Criar diretório de logos:**
```bash
mkdir -p static/logos
chmod 755 static/logos
```

## 🚀 Procedimento de Deploy

### Passo 1: Backup
```bash
# Backup dos arquivos atuais
cp services/danfe_service.py services/danfe_service.py.backup
cp routes/nfe_routes.py routes/nfe_routes.py.backup
cp services/nfe_service.py services/nfe_service.py.backup
cp routes/admin_routes.py routes/admin_routes.py.backup
cp database/models.py database/models.py.backup
```

### Passo 2: Transferir Arquivos
```bash
# Usando SCP ou SFTP
scp services/danfe_service.py usuario@servidor:/caminho/api_nfe/services/
scp routes/nfe_routes.py usuario@servidor:/caminho/api_nfe/routes/
scp services/nfe_service.py usuario@servidor:/caminho/api_nfe/services/
scp routes/admin_routes.py usuario@servidor:/caminho/api_nfe/routes/
scp database/models.py usuario@servidor:/caminho/api_nfe/database/
scp templates/admin/nfes/emitir.html usuario@servidor:/caminho/api_nfe/templates/admin/nfes/
scp templates/admin/clientes/form.html usuario@servidor:/caminho/api_nfe/templates/admin/clientes/
scp adicionar_campo_logo_cliente.sql usuario@servidor:/caminho/api_nfe/
```

### Passo 3: Instalar Dependências
```bash
# No servidor
cd /caminho/api_nfe
source venv/bin/activate  # Linux
# ou
venv\Scripts\activate  # Windows

pip install brazilnum BrazilFiscalReport erpbrasil.edoc.pdf
```

### Passo 4: Executar Migration SQL
```bash
# No servidor
psql -U postgres -d nome_do_banco -f adicionar_campo_logo_cliente.sql
```

### Passo 5: Criar Diretório de Logos
```bash
# No servidor
mkdir -p static/logos
chmod 755 static/logos  # Linux
```

### Passo 6: Reiniciar Serviço
```bash
# Windows Server (NSSM)
nssm restart NFe_Backend

# Linux (systemd)
sudo systemctl restart nfe_backend
```

### Passo 7: Executar Diagnóstico
```bash
# Executar script de diagnóstico
python diagnostico_servidor.py

# Verificar últimas linhas do log (200 linhas)
# Windows PowerShell
Get-Content logs\service.log -Tail 200 | Select-String -Pattern "ERROR|Exception|Traceback"

# Linux
tail -200 logs/service.log | grep -E "ERROR|Exception|Traceback"
```

## ✅ Checklist de Deploy

- [ ] Backup dos arquivos atuais criado
- [ ] 7 arquivos Python/HTML atualizados no servidor
- [ ] Dependências instaladas (brazilnum, BrazilFiscalReport, erpbrasil.edoc.pdf)
- [ ] Migration SQL executada (coluna logo_path criada)
- [ ] Diretório `static/logos/` criado com permissões corretas
- [ ] Serviço reiniciado
- [ ] Logs verificados (sem erros)
- [ ] Teste de emissão de NFe com transportadora
- [ ] Teste de upload de logo de cliente
- [ ] Verificação de DANFE oficial (não simplificado)

## 🧪 Testes Pós-Deploy

1. **Teste de Logo:**
   - Acesse: Cadastro de Clientes
   - Faça upload de uma logo (PNG/JPG)
   - Verifique se a logo aparece no preview

2. **Teste de Transportadora:**
   - Acesse: Emitir NFe
   - Preencha os dados da transportadora
   - Inclua: ANTT, Marca, Numeração
   - Emita a NFe

3. **Teste de DANFE:**
   - Gere o DANFE automaticamente
   - Verifique se é "oficial" (não simplificado)
   - Verifique se a logo aparece
   - Verifique se os campos da transportadora aparecem

4. **Verificar Logs:**
   ```bash
   # Deve mostrar:
   ✅ Logo configurada: /caminho/static/logos/cliente_123.png
   ✅ PDF gerado com engine brazilfiscalreport, tamanho: 45678 bytes
   ```

## 📊 Resumo das Mudanças

| Componente | Arquivos | Mudanças |
|------------|----------|----------|
| **Backend** | 5 arquivos | Captura campos, gera XML, integra logo |
| **Frontend** | 2 arquivos | Novos campos form, upload logo |
| **Banco** | 1 migration | Coluna logo_path |
| **Dependências** | 3 pacotes | Engines DANFE oficial |
| **Infraestrutura** | 1 diretório | static/logos/ |

---

**Última Atualização:** 02/12/2025  
**Branch:** lc214-migration  
**Versão:** 1.1

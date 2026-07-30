# 🚀 Guia Completo de Deploy - Sistema NF-e
## Windows Server 2016 - Ambiente de Testes

---

## 📋 Sumário Rápido
1. [Requisitos](#requisitos)
2. [PostgreSQL](#postgresql)
3. [Python](#python)
4. [Projeto](#projeto)
5. [IIS](#iis)
6. [Produção](#produção)

---

## ✅ Requisitos

### Hardware Mínimo
- CPU: 4 cores
- RAM: 8 GB
- Disco: 100 GB livres
- Rede: IP fixo

### Software
- Windows Server 2016
- PostgreSQL 14+
- Python 3.11 ou 3.12 ⚠️ **NÃO usar Python 3.13**
- IIS 10.0

---

## 🗄️ PostgreSQL

### 1. Instalar PostgreSQL

**Download:**
- https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
- Versão 14.x Windows x64

**Instalação:**
```
Componentes: Todos
Porta: 5432
Senha postgres: [ANOTAR SENHA]
Locale: Portuguese, Brazil
```

### 2. Criar Banco de Dados

Abrir **pgAdmin 4**:

```sql
-- Criar database
CREATE DATABASE sjtnfe
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8';

-- Criar usuário da aplicação
CREATE USER nfe_app WITH PASSWORD 'SenhaSegura2025!';

-- Dar permissões
GRANT ALL PRIVILEGES ON DATABASE sjtnfe TO nfe_app;

-- Conectar ao banco
\c sjtnfe

-- Permissões no schema
GRANT ALL ON SCHEMA public TO nfe_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nfe_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nfe_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nfe_app;
```

### 3. Testar Conexão

PowerShell:
```powershell
cd "C:\Program Files\PostgreSQL\14\bin"
.\psql.exe -U postgres -d sjtnfe
# Deve conectar com sucesso
```

---

## 🐍 Python

### 1. Instalar Python

**Download:**
- https://www.python.org/downloads/windows/
- ✅ **RECOMENDADO:** Python 3.13.x (64-bit) - Versão mais recente
- Exemplo: Python 3.13.9 ou superior
- Link direto: https://www.python.org/ftp/python/3.13.9/python-3.13.9-amd64.exe

**⚠️ IMPORTANTE sobre SQLAlchemy:**
- Se usar Python 3.13, DEVE instalar **SQLAlchemy 2.0.43 ou superior**
- Versões antigas do SQLAlchemy (2.0.23) NÃO funcionam com Python 3.13
- O comando de instalação abaixo já usa a versão correta

**Instalação:**
- ⚠️ **MARCAR:** "Add Python to PATH"
- Clicar "Install Now"

### 2. Verificar

PowerShell:
```powershell
python --version
# Python 3.12.x (NÃO 3.13!)

pip --version
# pip 23.x ou superior
```

⚠️ **Se instalou Python 3.13 por engano:**
```powershell
# Desinstalar Python 3.13
# Painel de Controle > Programas > Desinstalar Python 3.13

# Baixar e instalar Python 3.12.7
# https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
```

### 3. Atualizar pip

```powershell
python -m pip install --upgrade pip setuptools wheel
```

---

## 📦 Projeto

### 1. Criar Estrutura

PowerShell como **Administrador**:

```powershell
# Criar diretórios
mkdir C:\nfe_app
mkdir C:\nfe_app\logs
mkdir C:\nfe_app\backups
mkdir C:\nfe_app\uploads
mkdir C:\nfe_app\certificados

cd C:\nfe_app
```

### 2. Copiar Arquivos

**Opção A - Via Git:**
```powershell
cd C:\nfe_app
git clone https://github.com/sjtecnologia/api_nfe.git .
```

**Opção B - Copiar manualmente:**
- Copiar todos os arquivos do projeto para `C:\nfe_app`

### 3. Criar Ambiente Virtual

```powershell
cd C:\nfe_app

# Criar venv
python -m venv venv

# Ativar venv
.\venv\Scripts\Activate.ps1

# Se der erro de ExecutionPolicy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Instalar Dependências

⚠️ **IMPORTANTE:** Execute estes comandos um por um para garantir instalação correta:

```powershell
# Com ambiente virtual ATIVADO (deve aparecer (venv) no prompt)

# 1. Core do Flask
pip install Flask==3.0.0
pip install Werkzeug==3.0.1
pip install Jinja2==3.1.2
pip install itsdangerous==2.1.2
pip install click==8.1.7
pip install MarkupSafe==2.1.3

# 2. Banco de Dados
# ⚠️ IMPORTANTE: Se usar Python 3.13, DEVE ser versões compatíveis!
pip install SQLAlchemy==2.0.43
pip install psycopg2-binary==2.9.10

# 3. Autenticação
pip install Flask-Login==0.6.3

# 4. Variáveis de Ambiente
pip install python-dotenv==1.0.0

# 5. Imagens e QR Code
# ⚠️ Pillow 10.1.0 não é compatível com Python 3.13
pip install Pillow>=12.0.0
pip install qrcode[pil]==7.4.2

# 6. XML e PDFs
# ⚠️ lxml 5.1.0 pode dar erro, use versão mais recente
pip install lxml>=6.0.1
pip install reportlab==4.0.7

# 7. APIs e Requests
pip install requests==2.31.0
pip install certifi==2023.11.17
pip install urllib3==2.1.0

# 8. Excel (importação de produtos)
# ⚠️ pandas 2.1.4 NÃO é compatível com Python 3.13!
pip install pandas>=2.2.0
pip install openpyxl==3.1.2
pip install numpy>=1.26.2

# 9. Timezone
pip install pytz==2023.3

# 10. Servidor WSGI
pip install waitress==2.1.2

# 11. Verificar instalação
pip list

# 12. Tentar instalar requirements.txt (pode ter mais dependências)
pip install -r requirements.txt
```

**Verificação:**
```powershell
# Testar imports principais
python -c "import flask; print('Flask OK')"
python -c "import sqlalchemy; print('SQLAlchemy OK')"
python -c "from flask_login import LoginManager; print('Flask-Login OK')"
python -c "import psycopg2; print('psycopg2 OK')"
```

### 5. Configurar .env

Criar arquivo `C:\nfe_app\.env`:

```env
# Flask
FLASK_SECRET_KEY=sua_chave_super_secreta_complexa_2025!
FLASK_DEBUG=False
FLASK_ENV=production
FLASK_HOST=0.0.0.0
PORT=8080

# Banco de Dados
DATABASE_URL=postgresql://nfe_app:SenhaSegura2025!@localhost:5432/sjtnfe
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sjtnfe
DB_USER=nfe_app
DB_PASSWORD=SenhaSegura2025!

# Caminhos
UPLOAD_FOLDER=C:\nfe_app\uploads
BACKUP_DIR=C:\nfe_app\backups
LOG_LEVEL=INFO

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app
```

### 6. Inicializar Banco

```powershell
cd C:\nfe_app
.\venv\Scripts\Activate.ps1

# Testar imports
python -c "from database.connection import get_db; print('DB Connection OK')"

# Se houver script de inicialização
python -c "from database.connection import init_db; init_db()"

# OU importar SQL manualmente
cd "C:\Program Files\PostgreSQL\14\bin"
.\psql.exe -U nfe_app -d sjtnfe -f "C:\nfe_app\database\schema.sql"
```

### 7. Testar Aplicação

```powershell
cd C:\nfe_app
.\venv\Scripts\Activate.ps1

# Rodar aplicação
python app.py

# Deve mostrar:
# * Running on http://0.0.0.0:8080
```

Abrir navegador: `http://localhost:8080`

---

## 🌐 IIS

### Opção 1: IIS + Reverse Proxy (Recomendado)

#### A. Instalar IIS

PowerShell como Admin:
```powershell
# Instalar IIS com URL Rewrite
Install-WindowsFeature -name Web-Server -IncludeManagementTools
Install-WindowsFeature -name Web-Http-Redirect
```

**Instalar módulos adicionais:**
1. URL Rewrite: https://www.iis.net/downloads/microsoft/url-rewrite
2. Application Request Routing: https://www.iis.net/downloads/microsoft/application-request-routing

#### B. Configurar Reverse Proxy

1. **IIS Manager** > Servidor (raiz)
2. **Application Request Routing Cache**
3. **Server Proxy Settings** (direita)
4. **Enable proxy** ✓
5. **Apply**

#### C. Criar Site

1. **IIS Manager** > **Sites** > Botão direito > **Add Website**
   - Nome: `Sistema_NFe`
   - Path: `C:\nfe_app`
   - Port: `80`
   - Host: (vazio)

2. Criar `C:\nfe_app\web.config`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="ReverseProxyInboundRule1" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="http://localhost:8080/{R:1}" />
        </rule>
      </rules>
    </rewrite>
    <httpErrors errorMode="Detailed" />
  </system.webServer>
</configuration>
```

#### D. Criar Serviço Windows (Backend)

**Baixar NSSM:**
- https://nssm.cc/download
- Extrair para `C:\nssm`

**Criar serviço:**
```powershell
cd C:\nssm\win64

# Instalar serviço
.\nssm.exe install NFe_Backend "C:\nfe_app\venv\Scripts\python.exe" "C:\nfe_app\app.py"

# Configurar
.\nssm.exe set NFe_Backend AppDirectory "C:\nfe_app"
.\nssm.exe set NFe_Backend AppStdout "C:\nfe_app\logs\service.log"
.\nssm.exe set NFe_Backend AppStderr "C:\nfe_app\logs\error.log"
.\nssm.exe set NFe_Backend DisplayName "Sistema NFe - Backend"
.\nssm.exe set NFe_Backend Start SERVICE_AUTO_START

# Iniciar
.\nssm.exe start NFe_Backend

# Verificar
.\nssm.exe status NFe_Backend
```

**OU usar Waitress:**

Criar `C:\nfe_app\wsgi.py`:
```python
from waitress import serve
from app import app

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8080, threads=4)
```

Criar serviço:
```powershell
.\nssm.exe install NFe_Backend "C:\nfe_app\venv\Scripts\python.exe" "C:\nfe_app\wsgi.py"
# ... resto das configurações acima
```

---

### Opção 2: IIS + FastCGI

#### A. Instalar CGI

```powershell
Install-WindowsFeature -name Web-CGI
```

#### B. Instalar wfastcgi

```powershell
cd C:\nfe_app
.\venv\Scripts\Activate.ps1
pip install wfastcgi
wfastcgi-enable
```

**Copiar a saída** (ex: `C:\nfe_app\venv\Scripts\python.exe|C:\nfe_app\venv\Lib\site-packages\wfastcgi.py`)

#### C. Configurar web.config

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="PythonHandler" 
           path="*" 
           verb="*" 
           modules="FastCgiModule" 
           scriptProcessor="C:\nfe_app\venv\Scripts\python.exe|C:\nfe_app\venv\Lib\site-packages\wfastcgi.py" 
           resourceType="Unspecified" />
    </handlers>
  </system.webServer>
  
  <appSettings>
    <add key="PYTHONPATH" value="C:\nfe_app" />
    <add key="WSGI_HANDLER" value="app.app" />
    <add key="WSGI_LOG" value="C:\nfe_app\logs\wfastcgi.log" />
  </appSettings>
</configuration>
```

#### D. Configurar Permissões

```powershell
icacls "C:\nfe_app" /grant "IIS_IUSRS:(OI)(CI)RX" /T
icacls "C:\nfe_app\logs" /grant "IIS_IUSRS:(OI)(CI)M" /T
icacls "C:\nfe_app\uploads" /grant "IIS_IUSRS:(OI)(CI)M" /T
```

#### E. Reiniciar IIS

```powershell
iisreset
```

---

## 🔥 Firewall

```powershell
# HTTP
New-NetFirewallRule -DisplayName "HTTP Sistema NFe" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow

# HTTPS (futuro)
New-NetFirewallRule -DisplayName "HTTPS Sistema NFe" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow

# Backend direto (se necessário)
New-NetFirewallRule -DisplayName "NFe Backend" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow

# PostgreSQL (se acesso remoto)
New-NetFirewallRule -DisplayName "PostgreSQL" -Direction Inbound -LocalPort 5432 -Protocol TCP -Action Allow
```

---

## 💾 Backup

### Script de Backup

Criar `C:\nfe_app\backup.ps1`:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "C:\nfe_app\backups"
$backupFile = "$backupDir\backup_$timestamp.sql"
$pgDump = "C:\Program Files\PostgreSQL\14\bin\pg_dump.exe"

# Backup
$env:PGPASSWORD = "SenhaSegura2025!"
& $pgDump -h localhost -U nfe_app -F c -f $backupFile sjtnfe

# Comprimir
Compress-Archive -Path $backupFile -DestinationPath "$backupFile.zip"
Remove-Item $backupFile

# Limpar antigos (30 dias)
Get-ChildItem -Path $backupDir -Filter "*.zip" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | 
    Remove-Item -Force

Write-Host "Backup concluído: $backupFile.zip"
```

### Agendar Backup

Task Scheduler:
1. **Create Task**
2. **Name:** Backup NFe
3. **Trigger:** Daily 2:00 AM
4. **Action:** Start Program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File C:\nfe_app\backup.ps1`
5. **Run with highest privileges** ✓

---

## 🔍 Troubleshooting

### ⚠️ Erro: SQLAlchemy Incompatível com Python 3.13 (ERRO MAIS COMUM!)

**Sintoma:**
```
AssertionError: Class <class 'sqlalchemy.sql.elements.SQLCoreOperations'> directly inherits TypingOnly...
File "C:\Users\...\AppData\Local\Programs\Python\Python313\Lib\typing.py"
```

**Causa:** Python 3.13 + SQLAlchemy 2.0.23 (ou inferior) são INCOMPATÍVEIS

**Por que acontece:**
- SQLAlchemy 2.0.23 foi lançado ANTES do Python 3.13
- Python 3.13 mudou internamente o módulo `typing.py`
- SQLAlchemy versões antigas não conhecem essas mudanças
- **Solução:** Atualizar SQLAlchemy para 2.0.43 ou superior

**Solução Completa (Passo a Passo):**

```powershell
# ═══════════════════════════════════════════════════════════
# PASSO 1: FECHAR TODOS OS PROCESSOS PYTHON (MUITO IMPORTANTE!)
# ═══════════════════════════════════════════════════════════

# 1.1. Abrir PowerShell como ADMINISTRADOR
# - Clique direito no botão Iniciar
# - Selecione "Windows PowerShell (Admin)"

# 1.2. Verificar processos Python em execução
tasklist | findstr /i python

# 1.3. Se aparecer algum processo, matar TODOS:
taskkill /F /IM python.exe
taskkill /F /IM pythonw.exe
taskkill /F /IM py.exe

# 1.4. Fechar TODAS as janelas:
# - Feche TODOS os CMD/PowerShell (exceto o Admin atual)
# - Feche VS Code, PyCharm ou qualquer IDE
# - Feche Windows Explorer se estiver em pastas Python
# - Desative ambiente virtual se ativo: deactivate

# 1.5. Verificar novamente (não deve aparecer nada):
tasklist | findstr /i python

# ═══════════════════════════════════════════════════════════
# PASSO 2: ATUALIZAR SQLAlchemy (SOLUÇÃO MAIS SIMPLES!)
# ═══════════════════════════════════════════════════════════

# ✅ OPÇÃO 1 (RECOMENDADA): NÃO DESINSTALAR Python 3.13!
# Basta atualizar SQLAlchemy para versão compatível:

# 2.1. Ativar ambiente virtual (se tiver)
cd C:\nfe_app
.\venv\Scripts\Activate.ps1

# 2.2. Atualizar SQLAlchemy
pip install --upgrade SQLAlchemy==2.0.43

# 2.3. Verificar versão
python -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)"
# Deve mostrar: SQLAlchemy: 2.0.43

# 2.4. Testar aplicação
python app.py
# Deve funcionar perfeitamente!

# ═══════════════════════════════════════════════════════════
# OPÇÃO 2 (SE PREFERIR): Desinstalar Python 3.13 e usar 3.12
# ═══════════════════════════════════════════════════════════
# Só use esta opção se realmente quiser usar Python 3.12

# 2A.1. Método 1: Via Painel de Controle
# - Pressione Win + R
# - Digite: appwiz.cpl
# - Enter
# - Procure "Python 3.13.9 (64-bit)"
# - Botão direito > Desinstalar
# - Siga o assistente de desinstalação

# 2A.2. Se der ERRO 0x80070659 novamente:
# Significa que ainda há processos usando Python!
# Execute novamente o PASSO 1.3 e tente novamente

# 2A.3. Se CONTINUAR dando erro, REINICIE o servidor:
shutdown /r /t 0
# Após reiniciar, tente desinstalar novamente

# 2A.4. Baixar Python 3.12.7
# https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe

# 2A.5. Instalar Python 3.12.7
# IMPORTANTE: Durante instalação:
# ✓ Add Python to PATH
# ✓ Install for all users

# 2A.6. Verificar nova instalação
python --version
# DEVE mostrar: Python 3.12.7

# 7. Fechar e reabrir PowerShell

# 8. Deletar ambiente virtual antigo
cd C:\nfe_app
Remove-Item -Recurse -Force venv

# 9. Criar novo ambiente virtual
python -m venv venv

# 10. Ativar ambiente virtual
.\venv\Scripts\Activate.ps1

# 11. Atualizar pip
python -m pip install --upgrade pip

# 12. Instalar TODAS as dependências
pip install Flask==3.0.0
pip install Werkzeug==3.0.1
pip install Jinja2==3.1.2
pip install itsdangerous==2.1.2
pip install click==8.1.7
pip install MarkupSafe==2.1.3
pip install SQLAlchemy==2.0.43
pip install psycopg2-binary==2.9.10
pip install Flask-Login==0.6.3
pip install python-dotenv==1.0.0
pip install Pillow>=12.0.0
pip install qrcode[pil]==7.4.2
pip install lxml>=6.0.1
pip install reportlab==4.0.7
pip install requests==2.31.0
pip install certifi==2023.11.17
pip install urllib3==2.1.0
pip install pandas>=2.2.0
pip install openpyxl==3.1.2
pip install numpy>=1.26.2
pip install pytz==2023.3
pip install waitress==2.1.2

# 13. Verificar instalação
python -c "import sqlalchemy; print('SQLAlchemy OK:', sqlalchemy.__version__)"
python -c "import flask; print('Flask OK:', flask.__version__)"

# 14. Testar aplicação
python app.py
# Deve rodar sem erro!

# 15. Se usar serviço Windows, recriar
C:\nssm\win64\nssm.exe remove NFe_Backend confirm
C:\nssm\win64\nssm.exe install NFe_Backend "C:\nfe_app\venv\Scripts\python.exe" "C:\nfe_app\app.py"
C:\nssm\win64\nssm.exe set NFe_Backend AppDirectory "C:\nfe_app"
C:\nssm\win64\nssm.exe set NFe_Backend AppStdout "C:\nfe_app\logs\service.log"
C:\nssm\win64\nssm.exe set NFe_Backend AppStderr "C:\nfe_app\logs\error.log"
C:\nssm\win64\nssm.exe start NFe_Backend
```

**Verificação Final:**
```powershell
# Deve mostrar Python 3.12.x
python --version

# Deve funcionar
cd C:\nfe_app
.\venv\Scripts\Activate.ps1
python app.py
```

### Erro: Module Not Found

```powershell
cd C:\nfe_app
.\venv\Scripts\Activate.ps1

# Verificar ambiente está ativado
where python
# Deve mostrar: C:\nfe_app\venv\Scripts\python.exe

# Reinstalar módulo específico
pip install sqlalchemy==2.0.23
pip install flask==3.0.0
```

### Erro 500 - IIS

**Verificar logs:**
```powershell
Get-Content C:\nfe_app\logs\wfastcgi.log -Tail 50
Get-Content C:\nfe_app\logs\error.log -Tail 50
```

**Permissões:**
```powershell
icacls "C:\nfe_app" /reset /T
icacls "C:\nfe_app" /grant "IIS_IUSRS:(OI)(CI)RX" /T
icacls "C:\nfe_app\logs" /grant "IIS_IUSRS:(OI)(CI)F" /T
```

### Banco Não Conecta

```powershell
# Verificar serviço
Get-Service postgresql*

# Iniciar
Start-Service postgresql-x64-14

# Testar
cd "C:\Program Files\PostgreSQL\14\bin"
.\psql.exe -U nfe_app -d sjtnfe
```

### Serviço Não Inicia

```powershell
# Ver status
C:\nssm\win64\nssm.exe status NFe_Backend

# Ver logs
Get-Content C:\nfe_app\logs\service.log -Tail 50
Get-Content C:\nfe_app\logs\error.log -Tail 50

# Reiniciar
C:\nssm\win64\nssm.exe restart NFe_Backend
```

---

## ✅ Checklist Final

Antes de liberar para usuários:

- [ ] PostgreSQL rodando
- [ ] Banco `sjtnfe` criado e populado
- [ ] Python 3.12.x instalado (NÃO 3.13!)
- [ ] Venv criado e dependências instaladas
- [ ] Arquivo `.env` configurado
- [ ] Aplicação roda localmente (port 8080)
- [ ] IIS instalado e configurado
- [ ] Serviço Windows criado (se opção 1)
- [ ] Firewall configurado
- [ ] Backup agendado
- [ ] Acesso local funciona (`http://localhost`)
- [ ] Acesso remoto funciona (`http://IP_SERVIDOR`)

---

## 🚀 Acesso dos Usuários

**URL de Acesso:**
```
http://IP_DO_SERVIDOR
ou
http://NOME_DO_SERVIDOR
```

**Exemplo:**
```
http://192.168.1.100
http://servidor-nfe.local
```

**Login Inicial:**
- URL: `/auth/login`
- Usuário: `admin`
- Senha: (configurada no banco)

---

## 📞 Comandos Úteis

```powershell
# Verificar serviços
Get-Service postgresql*
Get-Service W3SVC
Get-Service NFe_Backend

# Ver portas
netstat -ano | findstr ":80"
netstat -ano | findstr ":8080"
netstat -ano | findstr ":5432"

# Logs
Get-Content C:\nfe_app\logs\service.log -Tail 50 -Wait
Get-Content C:\nfe_app\logs\app.log -Tail 50 -Wait

# Reiniciar tudo
Restart-Service postgresql-x64-14
iisreset
C:\nssm\win64\nssm.exe restart NFe_Backend
```

---

**Data:** 27/11/2025  
**Versão:** 1.1

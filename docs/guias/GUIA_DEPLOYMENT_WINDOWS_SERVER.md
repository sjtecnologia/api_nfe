# Guia de Deployment - Sistema NF-e em Windows Server 2016# 🚀 Guia de Deploy - Sistema NFe em Windows Server 2016
























































































































































































































































































































































































































































































































































































































































































































































































































































































































**Versão do Guia:** 1.0**Última atualização:** 26 de novembro de 2025---4. Verificar status dos serviços (PostgreSQL, IIS)3. Consultar documentação do IIS2. Verificar Event Viewer do Windows1. Verificar logs: `C:\inetpub\wwwroot\sistema_nfe\logs\`Em caso de dúvidas ou problemas:## 📞 Suporte---- Senha: (a que foi configurada no banco)- Usuário padrão: `admin`- URL: `http://[IP_SERVIDOR]/auth/login`**Primeiro Acesso:**```http://servidor-nfehttp://192.168.1.100```**Exemplo:**```http://NOME_DO_SERVIDORouhttp://IP_DO_SERVIDOR```**Rede Local:**Após completar todos os passos, os usuários poderão acessar o sistema através de:## 🚀 Acesso dos Usuários---- [ ] Certificados digitais instalados (se aplicável)- [ ] Logs sendo gerados corretamente- [ ] Teste de acesso remoto funcionando- [ ] Teste de acesso local funcionando- [ ] Monitoramento configurado- [ ] Backup automatizado agendado- [ ] Firewall configurado (portas abertas)- [ ] Permissões de arquivo/pasta configuradas- [ ] Site configurado no IIS- [ ] IIS instalado com suporte CGI- [ ] Arquivo `.env` configurado corretamente- [ ] Ambiente virtual criado e dependências instaladas- [ ] Python 3.11+ instalado- [ ] Banco de dados `sjtnfe` criado e populado- [ ] PostgreSQL instalado e funcionandoAntes de liberar para os usuários:## 📝 Checklist Final---   ```   REINDEX DATABASE sjtnfe;   VACUUM ANALYZE;   -- Executar no pgAdmin   ```sql3. **Otimizar PostgreSQL:**   ```   - Enable static content compression ✓   - Enable dynamic content compression ✓   IIS Manager > Sistema_NFe > Compression   ```2. **Habilitar compressão:**   ```   - Idle Time-out: 0   - Regular Time Interval: 0   IIS Manager > Application Pools > SistemaNFePool > Advanced Settings   ```1. **Aumentar recursos do Application Pool:****Otimizações:**### Problema 5: Performance Baixa```python -c "import flask; print(flask.__version__)"# Verificar instalaçãopip install -r requirements.txt.\venv\Scripts\Activate.ps1cd C:\inetpub\wwwroot\sistema_nfe```powershell**Solução:****Causa:** Ambiente virtual não ativado ou PATH incorreto### Problema 4: Módulos Python Não Encontrados   - .woff2 → font/woff2   - .js → application/javascript   - .css → text/css3. Adicionar tipos se necessário:2. MIME Types1. IIS Manager > Sistema_NFe**Solução:****Causa:** Configuração de MIME types ou permissões### Problema 3: Site Não Carrega Arquivos Estáticos```.\psql.exe -U postgres -d sjtnfecd "C:\Program Files\PostgreSQL\14\bin"# Testar conexãoStart-Service postgresql-x64-14# Iniciar serviçoGet-Service postgresql*# Verificar serviço```powershell**Solução:****Causa:** Serviço PostgreSQL parado ou configuração incorreta### Problema 2: Banco de Dados Não Conecta```iisreset# Reiniciar IISicacls "C:\inetpub\wwwroot\sistema_nfe" /grant "IIS AppPool\SistemaNFePool:(OI)(CI)F" /T# Verificar permissõesGet-Content "C:\inetpub\wwwroot\sistema_nfe\logs\wfastcgi.log" -Tail 50# Verificar logs```powershell**Solução:****Causa:** Configuração incorreta do FastCGI ou permissões### Problema 1: Erro 500 Internal Server Error## 🔍 Solução de Problemas---```Get-Content "C:\inetpub\wwwroot\sistema_nfe\logs\app.log" -Tail 50 -Wait# Ver logs da aplicaçãoGet-Content "C:\inetpub\logs\LogFiles\W3SVC1\*.log" -Tail 50# Ver logs do IIS```powershell### Visualizar Logs do IISAgendar no Task Scheduler para rodar a cada 5 minutos.```}    Write-Log "Application Pool reiniciado"    Restart-WebAppPool -Name "SistemaNFePool"    Import-Module WebAdministration    # Tentar reiniciar o site        Write-Log "ERRO - Sistema não está respondendo: $_"} catch {    }        Write-Log "AVISO - Status code: $($response.StatusCode)"    } else {        Write-Log "OK - Sistema respondendo corretamente"    if ($response.StatusCode -eq 200) {    $response = Invoke-WebRequest -Uri $appUrl -UseBasicParsing -TimeoutSec 10try {}    "$timestamp - $Message" | Add-Content -Path $logFile    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"    param($Message)function Write-Log {$logFile = "C:\inetpub\wwwroot\sistema_nfe\logs\monitor.log"$appUrl = "http://localhost/health"# Monitor de saúde do sistema```powershellCriar arquivo `C:\inetpub\wwwroot\sistema_nfe\monitor.ps1`:### Criar Script de Monitoramento```LOG_FILE = 'logs/app.log'LOG_LEVEL = 'INFO'# Configurações de Log```pythonEditar `config/settings.py` se necessário para garantir:### Configurar Logs da Aplicação## 📊 Monitoramento e Logs---   - OK   - Inserir senha do usuário Windows7. **Salvar:**   - OK   - Attempt to restart up to: 3 times   - If the task fails, restart every: 10 minutes   - Allow task to be run on demand ✓6. **Settings:**   - OK   - Desmarcar "Start the task only if the computer is on AC power"5. **Conditions:**   - OK   - **Arguments:** `-ExecutionPolicy Bypass -File "C:\inetpub\wwwroot\sistema_nfe\backup_database.ps1"`   - **Program/script:** `powershell.exe`   - **Action:** Start a program   - New4. **Actions:**   - OK   - **Start:** 02:00:00 (2h da manhã)   - **Daily** - Recur every: 1 days   - **Begin the task:** On a schedule   - New3. **Triggers:**     - Run with highest privileges ✓     - Run whether user is logged on or not ✓   - **Security options:**   - **Description:** Backup diário do banco de dados   - **Nome:** Backup Sistema NFe   - Action > Create Task2. **Criar Tarefa:**   - Win + R > `taskschd.msc`1. **Abrir Task Scheduler:**### Passo 2: Agendar Backup no Task Scheduler```}    exit 1    Write-Host "ERRO ao fazer backup!"} else {    Write-Host "Backups antigos removidos (retenção: $retention dias)"            Remove-Item -Force        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$retention) } |     Get-ChildItem -Path $backupDir -Filter "*.zip" |     # Limpar backups antigos        Remove-Item $backupFile    Compress-Archive -Path $backupFile -DestinationPath "$backupFile.zip"    # Comprimir backup        Write-Host "Backup concluído com sucesso: $backupFile"if ($LASTEXITCODE -eq 0) {& "$pgBinPath\pg_dump.exe" -U $dbUser -F c -f $backupFile $dbNameWrite-Host "Iniciando backup do banco $dbName..."# Executar backup$backupFile = "$backupDir\backup_${dbName}_${timestamp}.sql"# Nome do arquivo}    New-Item -ItemType Directory -Path $backupDirif (!(Test-Path $backupDir)) {# Criar diretório se não existir$retention = 30  # dias$pgBinPath = "C:\Program Files\PostgreSQL\14\bin"$dbUser = "postgres"$dbName = "sjtnfe"$backupDir = "C:\inetpub\wwwroot\sistema_nfe\backups"$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"# Configurações```powershellCriar arquivo `C:\inetpub\wwwroot\sistema_nfe\backup_database.ps1`:### Passo 1: Criar Script de Backup## 💾 Backup Automatizado---```http://NOME_DO_SERVIDORouhttp://IP_DO_SERVIDOR```De outro computador na rede:### Passo 2: Testar Acesso```New-NetFirewallRule -DisplayName "PostgreSQL" -Direction Inbound -LocalPort 5432 -Protocol TCP -Action Allow# PostgreSQL (se acesso remoto necessário)New-NetFirewallRule -DisplayName "Sistema NFe Backend" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow# Abrir porta 8080 (se usar Waitress diretamente)New-NetFirewallRule -DisplayName "HTTPS Sistema NFe" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow# Abrir porta 443 (HTTPS) - para futuroNew-NetFirewallRule -DisplayName "HTTP Sistema NFe" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow# Abrir porta 80 (HTTP)```powershell### Passo 1: Abrir Portas no Windows Firewall## 🔥 Configuração de Firewall---```</configuration>  </system.webServer>    </rewrite>      </rules>        </rule>          <action type="Rewrite" url="http://localhost:8080/{R:1}" />          <match url="(.*)" />        <rule name="Reverse Proxy" stopProcessing="true">      <rules>    <rewrite>  <system.webServer><configuration><?xml version="1.0" encoding="UTF-8"?>```xml3. Criar arquivo `web.config`:   - Apply   - Enable proxy ✓   - Server Proxy Settings   - Application Request Routing Cache   - IIS Manager > Servidor (raiz)2. Habilitar ARR Proxy:   - Baixar: https://www.iis.net/downloads/microsoft/application-request-routing   - Baixar: https://www.iis.net/downloads/microsoft/url-rewrite1. Instalar URL Rewrite e ARR:Configurar IIS como Reverse Proxy:```.\nssm.exe start SistemaNFe# Iniciar serviço.\nssm.exe set SistemaNFe AppStderr "C:\inetpub\wwwroot\sistema_nfe\logs\service_error.log".\nssm.exe set SistemaNFe AppStdout "C:\inetpub\wwwroot\sistema_nfe\logs\service.log".\nssm.exe set SistemaNFe AppDirectory "C:\inetpub\wwwroot\sistema_nfe"# Configurar.\nssm.exe install SistemaNFe "C:\inetpub\wwwroot\sistema_nfe\venv\Scripts\python.exe" "C:\inetpub\wwwroot\sistema_nfe\run_waitress.py"# Instalar serviçocd C:\nssm\win64# Extrair para C:\nssm# Baixar NSSM de: https://nssm.cc/download```powershellCriar serviço Windows com NSSM (Non-Sucking Service Manager):```    serve(app, host='0.0.0.0', port=port, threads=4)    port = int(os.getenv('PORT', 8080))if __name__ == '__main__':import osfrom app import appfrom waitress import serve```pythonCriar arquivo `run_waitress.py`:```pip install waitress.\venv\Scripts\Activate.ps1cd C:\inetpub\wwwroot\sistema_nfe```powershellSe o WFastCGI der problemas, use Waitress como servidor WSGI:### Método 2: Usando Waitress (Alternativa Simples)   - Botão direito > Manage Website > Restart   - Sites > Sistema_NFe7. **Reiniciar Site:**   - OK   - **Request Timeout:** 600   - **Activity Timeout:** 600   - **Instance MaxRequests:** 10000     - WSGI_HANDLER = `app.app`     - PYTHONPATH = `C:\inetpub\wwwroot\sistema_nfe`   - **Environment Variables:** Adicionar   - **Arguments:** `C:\inetpub\wwwroot\sistema_nfe\venv\Lib\site-packages\wfastcgi.py`   - **Full Path:** `C:\inetpub\wwwroot\sistema_nfe\venv\Scripts\python.exe`   - Add Application   - FastCGI Settings (duplo clique)   - Clicar no servidor (raiz)   No IIS Manager:   6. **Configurar FastCGI:**   ```   icacls "C:\inetpub\wwwroot\sistema_nfe\uploads" /grant "IIS AppPool\SistemaNFePool:(OI)(CI)M" /T   icacls "C:\inetpub\wwwroot\sistema_nfe\backups" /grant "IIS AppPool\SistemaNFePool:(OI)(CI)M" /T   icacls "C:\inetpub\wwwroot\sistema_nfe\logs" /grant "IIS AppPool\SistemaNFePool:(OI)(CI)M" /T   # Permissões específicas para diretórios      icacls "C:\inetpub\wwwroot\sistema_nfe" /grant "IIS AppPool\SistemaNFePool:(OI)(CI)F" /T   # Dar permissões ao IIS   ```powershell   Abrir PowerShell como Administrador:   5. **Configurar Permissões:**   - OK     - Host name: (deixar vazio ou colocar nome do servidor)     - Port: 80     - IP address: All Unassigned     - Type: http   - **Binding:**   - **Physical path:** `C:\inetpub\wwwroot\sistema_nfe`   - **Application pool:** SistemaNFePool   - **Site name:** `Sistema_NFe`   - Sites > Botão direito > Add Website4. **Criar novo Site:**   - OK   - **Start Mode:** AlwaysRunning   - **Enable 32-Bit Applications:** False   - **Identity:** ApplicationPoolIdentity   - Advanced Settings   - Clicar no `SistemaNFePool` criado3. **Configurar Application Pool:**   - OK   - **Managed pipeline mode:** Integrated   - **.NET CLR version:** No Managed Code   - **Name:** `SistemaNFePool`   - Botão direito > Add Application Pool   - Expandir servidor > Application Pools2. **Criar novo Application Pool:**   - Win + R > `inetmgr`1. **Abrir IIS Manager:**#### Configurar Site no IIS```</configuration>  </appSettings>    <add key="WSGI_LOG" value="C:\inetpub\wwwroot\sistema_nfe\logs\wfastcgi.log" />    <add key="WSGI_HANDLER" value="app.app" />    <add key="PYTHONPATH" value="C:\inetpub\wwwroot\sistema_nfe" />  <appSettings>    </system.webServer>    </defaultDocument>      </files>        <add value="app.py" />        <clear />      <files>    <defaultDocument>        </rewrite>      </rules>        </rule>          <action type="Rewrite" url="app.py/{R:1}" />          </conditions>            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />          <conditions>          <match url="(.*)" />        <rule name="Configure Python" stopProcessing="true">        </rule>          <action type="Rewrite" url="{R:0}" />          <match url="^(static|media)/.*$" />        <rule name="Static Files" stopProcessing="true">      <rules>    <rewrite>        </handlers>           requireAccess="Script" />           resourceType="Unspecified"            scriptProcessor="C:\inetpub\wwwroot\sistema_nfe\venv\Scripts\python.exe|C:\inetpub\wwwroot\sistema_nfe\venv\Lib\site-packages\wfastcgi.py"            modules="FastCgiModule"            verb="*"            path="*"       <add name="Python FastCGI"     <handlers>  <system.webServer><configuration><?xml version="1.0" encoding="UTF-8"?>```xmlCriar arquivo `C:\inetpub\wwwroot\sistema_nfe\web.config`:#### Criar arquivo web.config```C:\inetpub\wwwroot\sistema_nfe\venv\Scripts\python.exe|C:\inetpub\wwwroot\sistema_nfe\venv\Lib\site-packages\wfastcgi.py```Copie o caminho completo que aparecerá (algo como):```wfastcgi-enable# Habilitar wfastcgi no IISpip install wfastcgi# Instalar wfastcgi.\venv\Scripts\Activate.ps1cd C:\inetpub\wwwroot\sistema_nfe```powershell#### Instalar WFastCGI### Método 1: Usando WFastCGI (Recomendado)## 🔧 Configuração do IIS com Python---3. Deve aparecer a página padrão do IIS2. Acessar: `http://localhost`1. Abrir navegador### Passo 2: Verificar Instalação IIS9. **Install** > Aguardar conclusão > Close     - [x] IIS Management Console   - [x] Management Tools       - [x] WebSocket Protocol       - [x] CGI ⚠️ **IMPORTANTE**     - [x] Application Development       - [x] IP and Domain Restrictions       - [x] Request Filtering     - [x] Security       - [x] Dynamic Content Compression       - [x] Static Content Compression     - [x] Performance       - [x] Request Monitor       - [x] HTTP Logging     - [x] Health and Diagnostics       - [x] HTTP Redirection       - [x] Static Content       - [x] HTTP Errors       - [x] Directory Browsing       - [x] Default Document     - [x] Common HTTP Features   - [x] Web Server8. **Marcar os seguintes itens:**7. Next até "Role Services"6. Clicar "Add Features" quando aparecer popup5. **Marcar:** Web Server (IIS)4. Selecionar seu servidor > Next3. **Role-based installation** > Next2. Clicar em "Add roles and features"1. **Abrir Server Manager**### Passo 1: Instalar IIS## 🌐 Instalação do IIS (Servidor Web)---Abrir navegador e acessar: `http://localhost:8080````# * Running on http://0.0.0.0:8080# Deve mostrar algo como:python app.py# Executar aplicação.\venv\Scripts\Activate.ps1cd C:\inetpub\wwwroot\sistema_nfe```powershell### Passo 7: Testar Aplicação Localmente```python database\migrations.py.\venv\Scripts\Activate.ps1cd C:\inetpub\wwwroot\sistema_nfe# OU executar migrations do Python (se existir).\psql.exe -U nfe_app -d sjtnfe -f "C:\inetpub\wwwroot\sistema_nfe\database\schema.sql"cd "C:\Program Files\PostgreSQL\14\bin"# Se você tem um arquivo SQL de schema/dump```powershell### Passo 6: Importar Schema do Banco de Dados```LOG_LEVEL=INFO# Configurações de LogBACKUP_LOG_DIR=C:\inetpub\wwwroot\sistema_nfe\logsBACKUP_RETENTION_DAYS=30BACKUP_DIR=C:\inetpub\wwwroot\sistema_nfe\backups# Configurações de BackupMAX_CONTENT_LENGTH=16777216UPLOAD_FOLDER=C:\inetpub\wwwroot\sistema_nfe\uploads# Configurações de UploadDB_PASSWORD=SenhaDaAplicacao2025!DB_USER=nfe_appDB_NAME=sjtnfeDB_PORT=5432DB_HOST=localhostDATABASE_URL=postgresql://nfe_app:SenhaDaAplicacao2025!@localhost:5432/sjtnfe# Configurações do Banco de DadosPORT=8080FLASK_HOST=0.0.0.0FLASK_DEBUG=FalseFLASK_SECRET_KEY=sua_chave_super_secreta_aqui_complexa_2025!# Configurações Flask```envCriar arquivo `.env` em `C:\inetpub\wwwroot\sistema_nfe\.env`:### Passo 5: Configurar Variáveis de Ambiente```pip install pytz==2023.3pip install openpyxl==3.1.2pip install pandas==2.1.4pip install requests==2.31.0pip install lxml==5.1.0pip install qrcode==7.4.2pip install Pillow==10.1.0pip install python-dotenv==1.0.0pip install Flask-Login==0.6.3pip install psycopg2-binary==2.9.9pip install SQLAlchemy==2.0.23pip install Flask==3.0.0# Instalar dependências adicionais para Windowspip install -r requirements.txt# Com o ambiente virtual ativado```powershell### Passo 4: Instalar Dependências Python```Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser# Se houver erro de execução de scripts, executar:.\venv\Scripts\Activate.ps1# Ativar ambiente virtualpython -m venv venv# Criar ambiente virtualcd C:\inetpub\wwwroot\sistema_nfe```powershell### Passo 3: Criar Ambiente Virtual   ```   └── certificados/   ├── uploads/   ├── backups/   ├── logs/   ├── auth/   ├── utils/   ├── models/   ├── static/   ├── templates/   ├── routes/   ├── database/   ├── config/   ├── requirements.txt   ├── app.py   C:\inetpub\wwwroot\sistema_nfe\   ```2. **Estrutura esperada:**   ```   C:\inetpub\wwwroot\sistema_nfe\   ```1. **Copiar todo o projeto** do seu computador de desenvolvimento para:### Passo 2: Copiar Arquivos do Projeto```mkdir certificadosmkdir uploadsmkdir backupsmkdir logs# Criar subdiretórioscd C:\inetpub\wwwroot\sistema_nfemkdir C:\inetpub\wwwroot\sistema_nfe# Criar diretório da aplicação```powershell### Passo 1: Criar Estrutura de Diretórios## 📁 Configuração do Projeto---```pip install wheel# Instalar wheel (necessário para compilar pacotes)python -m pip install --upgrade pip# Atualizar pip```powershell### Passo 2: Instalar Dependências do Sistema   ```   # Deve mostrar a versão do pip   pip --version      # Deve mostrar: Python 3.11.x ou 3.12.x   python --version   ```powershell   Abrir PowerShell:   3. **Verificar Instalação:**   - Aguardar instalação   - Clicar em "Install Now"   - ⚠️ **IMPORTANTE:** Marcar "Add Python to PATH"2. **Executar o Instalador:**   - Baixe Python 3.11.x ou 3.12.x (Windows installer 64-bit)   - Acesse: https://www.python.org/downloads/windows/1. **Baixar Python:**### Passo 1: Download e Instalação## 🐍 Instalação do Python---```# sjtnfe=## Se conectou com sucesso, você verá:.\psql.exe -U postgres -d sjtnfecd "C:\Program Files\PostgreSQL\14\bin"# Testar conexão local```powershellAbrir PowerShell como Administrador:### Passo 3: Testar Conexão   - Botão direito > Restart   - Localizar "postgresql-x64-14"   - Abrir "Services" (Win + R > `services.msc`)5. **Reiniciar Serviço PostgreSQL:**   ```   host    sjtnfe          postgres        192.168.0.0/16          md5   host    sjtnfe          nfe_app         192.168.0.0/16          md5   # TYPE  DATABASE        USER            ADDRESS                 METHOD   # Adicionar no final do arquivo   ```conf   Editar arquivo: `C:\Program Files\PostgreSQL\14\data\pg_hba.conf`      ```   listen_addresses = '*'   # Permitir conexões de qualquer IP (linha ~59)   ```conf   Editar arquivo: `C:\Program Files\PostgreSQL\14\data\postgresql.conf`   4. **Configurar Acesso Remoto (se necessário):**   ```   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nfe_app;   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nfe_app;   GRANT ALL ON SCHEMA public TO nfe_app;   -- Dar permissões no schema public      \c sjtnfe   -- Conectar ao banco sjtnfe      GRANT ALL PRIVILEGES ON DATABASE sjtnfe TO nfe_app;   -- Dar permissões ao usuário      CREATE USER nfe_app WITH PASSWORD 'SenhaDaAplicacao2025!';   -- Criar usuário específico para a aplicação   ```sql3. **Criar Usuário da Aplicação (Opcional - Recomendado):**   ```       CONNECTION LIMIT = -1;       TABLESPACE = pg_default       LC_CTYPE = 'Portuguese_Brazil.1252'       LC_COLLATE = 'Portuguese_Brazil.1252'       ENCODING = 'UTF8'       OWNER = postgres       WITH    CREATE DATABASE sjtnfe   -- Criar banco de dados      -- Senha: a que você definiu   -- Conectar ao PostgreSQL (servidor local)   ```sql2. **Criar Banco de Dados:**   - Menu Iniciar > PostgreSQL 14 > pgAdmin 41. **Abrir pgAdmin 4:**### Passo 2: Configurar PostgreSQL   - Clicar em "Finish"   - Desmarcar "Launch Stack Builder" ao final4. **Finalizar Instalação:**   - **Locale:** `Portuguese, Brazil`   - **Senha do postgres:** Criar senha forte (ex: `SuaSenhaSegura2025!`)   - **Porta:** `5432` (padrão)     - [x] Command Line Tools     - [x] Stack Builder     - [x] pgAdmin 4     - [x] PostgreSQL Server   - **Componentes:** Marcar todos   - **Diretório:** `C:\Program Files\PostgreSQL\14`3. **Configurações da Instalação:**   ```   Arquivo: postgresql-14.x-windows-x64.exe   ```2. **Executar o Instalador:**   - Baixe a versão 14.x ou superior para Windows x64   - Acesse: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads1. **Baixar PostgreSQL:**### Passo 1: Download e Instalação## 🗄️ Instalação do PostgreSQL---- **Runtime:** Python 3.11 ou 3.12- **Banco de Dados:** PostgreSQL 14 ou superior- **Servidor Web:** IIS 10.0- **SO:** Windows Server 2016 (com atualizações)### Software- **Rede:** Conexão estável à internet- **Disco:** 100 GB livres (SSD recomendado)- **Memória RAM:** 8 GB- **Processador:** 4 cores (2.0 GHz ou superior)### Hardware Mínimo## 🖥️ Requisitos do Servidor---10. [Solução de Problemas](#solução-de-problemas)9. [Monitoramento e Logs](#monitoramento-e-logs)8. [Backup Automatizado](#backup-automatizado)7. [Configuração de Firewall](#configuração-de-firewall)6. [Configuração do IIS com Python](#configuração-do-iis-com-python)5. [Instalação do IIS (Servidor Web)](#instalação-do-iis)4. [Configuração do Projeto](#configuração-do-projeto)3. [Instalação do Python](#instalação-do-python)2. [Instalação do PostgreSQL](#instalação-do-postgresql)1. [Requisitos do Servidor](#requisitos-do-servidor)## 📋 Sumário
## 📋 Índice
1. [Preparação do Servidor](#1-preparação-do-servidor)
2. [Instalação do PostgreSQL](#2-instalação-do-postgresql)
3. [Instalação do Python](#3-instalação-do-python)
4. [Configuração do Projeto](#4-configuração-do-projeto)
5. [Instalação do IIS](#5-instalação-do-iis)
6. [Configuração do IIS com FastCGI](#6-configuração-do-iis-com-fastcgi)
7. [Criação de Serviço Windows](#7-criação-de-serviço-windows)
8. [Configuração de Firewall](#8-configuração-de-firewall)
9. [Backup e Manutenção](#9-backup-e-manutenção)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Preparação do Servidor

### 1.1 Requisitos Mínimos
- **SO**: Windows Server 2016 (64-bit)
- **RAM**: 8 GB (recomendado 16 GB)
- **CPU**: 4 cores
- **Disco**: 100 GB livres
- **Rede**: IP fixo configurado

### 1.2 Criar Usuário de Serviço
1. Abra **Computer Management** → **Local Users and Groups** → **Users**
2. Clique com botão direito → **New User**
3. Configure:
   - **Username**: `svc_nfe`
   - **Full name**: `Serviço NFe`
   - **Password**: (senha forte)
   - ☑️ **User cannot change password**
   - ☑️ **Password never expires**
4. Adicione aos grupos:
   - `IIS_IUSRS`
   - `Users`

### 1.3 Criar Estrutura de Pastas
Abra **PowerShell como Administrador**:

```powershell
# Criar estrutura de diretórios
New-Item -ItemType Directory -Force -Path "C:\inetpub\wwwroot\nfe"
New-Item -ItemType Directory -Force -Path "C:\nfe_app"
New-Item -ItemType Directory -Force -Path "C:\nfe_app\logs"
New-Item -ItemType Directory -Force -Path "C:\nfe_app\backup"
New-Item -ItemType Directory -Force -Path "C:\nfe_app\certificados"
New-Item -ItemType Directory -Force -Path "C:\nfe_app\uploads"

# Dar permissões ao usuário de serviço
icacls "C:\nfe_app" /grant "svc_nfe:(OI)(CI)F" /T
icacls "C:\inetpub\wwwroot\nfe" /grant "svc_nfe:(OI)(CI)F" /T
```

---

## 2. Instalação do PostgreSQL

### 2.1 Download e Instalação
1. Baixe PostgreSQL 14.x ou superior: https://www.postgresql.org/download/windows/
2. Execute o instalador
3. Durante a instalação:
   - **Password**: (anote a senha do usuário postgres)
   - **Port**: 5432
   - **Locale**: Portuguese, Brazil
   - ☑️ Instalar pgAdmin 4
   - ☑️ Instalar Stack Builder

### 2.2 Configurar PostgreSQL
1. Abra **pgAdmin 4**
2. Conecte ao servidor PostgreSQL
3. Clique com botão direito em **Databases** → **Create** → **Database**
   - **Database**: `sjtnfe`
   - **Owner**: `postgres`
   - **Encoding**: `UTF8`

### 2.3 Criar Usuário da Aplicação
No pgAdmin, abra **Query Tool** e execute:

```sql
-- Criar usuário
CREATE USER nfe_app WITH PASSWORD 'SuaSenhaSegura123!';

-- Dar permissões
GRANT ALL PRIVILEGES ON DATABASE sjtnfe TO nfe_app;

-- Conectar ao database sjtnfe e executar:
\c sjtnfe
GRANT ALL ON SCHEMA public TO nfe_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nfe_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nfe_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nfe_app;
```

### 2.4 Configurar Acesso Remoto (Opcional)
Edite `C:\Program Files\PostgreSQL\14\data\pg_hba.conf`:

```conf
# Adicione esta linha para permitir conexões da rede local
host    sjtnfe          nfe_app         192.168.0.0/16          md5
```

Edite `C:\Program Files\PostgreSQL\14\data\postgresql.conf`:

```conf
listen_addresses = '*'
max_connections = 100
```

Reinicie o serviço PostgreSQL:

```powershell
Restart-Service postgresql-x64-14
```

---

## 3. Instalação do Python

### 3.1 Download e Instalação
1. Baixe Python 3.13.x: https://www.python.org/downloads/windows/
2. Execute o instalador
3. ⚠️ **IMPORTANTE**: Marque as opções:
   - ☑️ **Add Python to PATH**
   - ☑️ **Install for all users**
4. Clique em **Customize installation**
5. Marque todas as opções em **Optional Features**
6. Em **Advanced Options**:
   - ☑️ **Install for all users**
   - ☑️ **Add Python to environment variables**
   - ☑️ **Precompile standard library**
   - **Install location**: `C:\Python313`

### 3.2 Verificar Instalação
Abra **cmd** como Administrador:

```cmd
python --version
pip --version
```

### 3.3 Atualizar pip
```cmd
python -m pip install --upgrade pip setuptools wheel
```

---

## 4. Configuração do Projeto

### 4.1 Transferir Arquivos do Projeto
Copie todo o projeto para `C:\nfe_app`:

**Opção A: Via Git** (recomendado)
```powershell
cd C:\nfe_app
git clone https://github.com/sjtecnologia/api_nfe.git .
```

**Opção B: Via SFTP/FTP**
- Use WinSCP ou FileZilla
- Transfira todos os arquivos do projeto
- Mantenha a estrutura de pastas

### 4.2 Criar Ambiente Virtual
```powershell
cd C:\nfe_app
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4.3 Instalar Dependências
```powershell
# Com ambiente virtual ativado
pip install -r requirements.txt

# Instalar dependências adicionais para Windows
pip install pywin32
pip install waitress
```

### 4.4 Configurar Variáveis de Ambiente

Crie o arquivo `C:\nfe_app\.env`:

```env
# Configurações Flask
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=sua_chave_secreta_muito_longa_e_complexa_aqui

# Banco de Dados
DATABASE_URL=postgresql://nfe_app:SuaSenhaSegura123!@localhost:5432/sjtnfe
DB_HOST=localhost
DB_NAME=sjtnfe
DB_USER=nfe_app
DB_PASSWORD=SuaSenhaSegura123!
DB_PORT=5432

# Servidor
HOST=0.0.0.0
PORT=5000

# Email (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=sjnfesjtecnolocia@gmail.com
SMTP_PASSWORD=nvlzpzjdvrdkfwsa
SMTP_FROM_NAME=Sistema NFe

# Logs
LOG_LEVEL=INFO
LOG_FILE=C:\nfe_app\logs\app.log

# Upload
UPLOAD_FOLDER=C:\nfe_app\uploads
MAX_CONTENT_LENGTH=16777216

# Certificados
CERT_FOLDER=C:\nfe_app\certificados
```

### 4.5 Criar Arquivo de Configuração do Servidor

Crie `C:\nfe_app\wsgi.py`:

```python
"""
WSGI entry point para produção
"""
import os
import sys
from pathlib import Path

# Adicionar diretório do projeto ao path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv(project_dir / '.env')

# Importar aplicação
from app import app as application

if __name__ == '__main__':
    # Para desenvolvimento local no Windows
    from waitress import serve
    serve(application, host='0.0.0.0', port=5000, threads=4)
```

### 4.6 Inicializar Banco de Dados

Execute os scripts SQL do projeto (se houver):

```powershell
# Ativar ambiente virtual
.\venv\Scripts\Activate.ps1

# Executar migrations ou scripts de inicialização
python -c "from database.connection import init_db; init_db()"
```

### 4.7 Testar Aplicação Localmente

```powershell
cd C:\nfe_app
.\venv\Scripts\Activate.ps1
python wsgi.py
```

Acesse: http://localhost:5000

---

## 5. Instalação do IIS

### 5.1 Instalar IIS via PowerShell

Execute como Administrador:

```powershell
# Instalar IIS e componentes necessários
Install-WindowsFeature -name Web-Server -IncludeManagementTools
Install-WindowsFeature -name Web-CGI
Install-WindowsFeature -name Web-ISAPI-Ext
Install-WindowsFeature -name Web-ISAPI-Filter
Install-WindowsFeature -name Web-Mgmt-Console
Install-WindowsFeature -name Web-Http-Redirect
Install-WindowsFeature -name Web-Http-Errors
Install-WindowsFeature -name Web-Static-Content
Install-WindowsFeature -name Web-Http-Logging
Install-WindowsFeature -name Web-Request-Monitor
```

### 5.2 Verificar Instalação

Abra navegador e acesse: http://localhost
Deve aparecer a página padrão do IIS.

---

## 6. Configuração do IIS com FastCGI

### 6.1 Instalar wfastcgi

```powershell
cd C:\nfe_app
.\venv\Scripts\Activate.ps1
pip install wfastcgi
wfastcgi-enable
```

**Anote a saída**, será algo como:
```
Applied configuration changes to section "system.webServer/fastCgi" for "MACHINE/WEBROOT/APPHOST"
"C:\nfe_app\venv\Scripts\python.exe|C:\nfe_app\venv\Lib\site-packages\wfastcgi.py"
```

### 6.2 Criar Site no IIS

1. Abra **Internet Information Services (IIS) Manager**
2. Expanda o servidor → Clique com botão direito em **Sites** → **Add Website**
3. Configure:
   - **Site name**: `NFe System`
   - **Physical path**: `C:\nfe_app`
   - **Binding**:
     - Type: `http`
     - IP address: `All Unassigned` (ou IP específico)
     - Port: `80`
     - Host name: (deixe vazio ou configure domínio)
4. Clique **OK**

### 6.3 Configurar Handler Mapping

1. No IIS Manager, selecione o site **NFe System**
2. Abra **Handler Mappings**
3. Clique **Add Module Mapping**
4. Configure:
   - **Request path**: `*`
   - **Module**: `FastCgiModule`
   - **Executable**: `C:\nfe_app\venv\Scripts\python.exe|C:\nfe_app\venv\Lib\site-packages\wfastcgi.py`
   - **Name**: `Python FastCGI`
5. Clique **Request Restrictions**:
   - Desmarque **Invoke handler only if request is mapped to**
6. Clique **OK**

### 6.4 Configurar web.config

Crie `C:\nfe_app\web.config`:

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
           resourceType="Unspecified" 
           requireAccess="Script" />
    </handlers>
    
    <rewrite>
      <rules>
        <rule name="Static Files" stopProcessing="true">
          <match url="^(static|media)/.*$" />
          <action type="Rewrite" url="{REQUEST_URI}" />
        </rule>
        <rule name="Configure Python" stopProcessing="true">
          <match url=".*" />
          <conditions>
            <add input="{REQUEST_URI}" pattern="^/(static|media)/.*$" negate="true" />
          </conditions>
          <action type="Rewrite" url="/" />
        </rule>
      </rules>
    </rewrite>
    
    <staticContent>
      <mimeMap fileExtension=".json" mimeType="application/json" />
      <mimeMap fileExtension=".woff" mimeType="application/font-woff" />
      <mimeMap fileExtension=".woff2" mimeType="application/font-woff2" />
    </staticContent>
    
    <httpErrors errorMode="Detailed" />
    
    <security>
      <requestFiltering>
        <requestLimits maxAllowedContentLength="52428800" />
      </requestFiltering>
    </security>
  </system.webServer>
  
  <appSettings>
    <add key="PYTHONPATH" value="C:\nfe_app" />
    <add key="WSGI_HANDLER" value="wsgi.application" />
    <add key="WSGI_LOG" value="C:\nfe_app\logs\wfastcgi.log" />
  </appSettings>
</configuration>
```

### 6.5 Configurar Permissões

```powershell
# Dar permissões ao usuário IIS
icacls "C:\nfe_app" /grant "IIS_IUSRS:(OI)(CI)RX" /T
icacls "C:\nfe_app\logs" /grant "IIS_IUSRS:(OI)(CI)F" /T
icacls "C:\nfe_app\uploads" /grant "IIS_IUSRS:(OI)(CI)F" /T
icacls "C:\nfe_app\certificados" /grant "IIS_IUSRS:(OI)(CI)RX" /T
```

### 6.6 Reiniciar IIS

```powershell
iisreset
```

### 6.7 Testar

Acesse: http://IP-DO-SERVIDOR ou http://localhost

---

## 7. Criação de Serviço Windows

### 7.1 Instalar NSSM (Non-Sucking Service Manager)

1. Baixe NSSM: https://nssm.cc/download
2. Extraia para `C:\nssm`
3. Adicione ao PATH:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\nssm\win64", "Machine")
```

### 7.2 Criar Script de Inicialização

Crie `C:\nfe_app\start_app.bat`:

```batch
@echo off
cd /d C:\nfe_app
call venv\Scripts\activate.bat
python wsgi.py
```

### 7.3 Criar Serviço

```powershell
# Criar serviço
nssm install NFe_Backend "C:\nfe_app\venv\Scripts\python.exe" "C:\nfe_app\wsgi.py"

# Configurar serviço
nssm set NFe_Backend AppDirectory "C:\nfe_app"
nssm set NFe_Backend AppStdout "C:\nfe_app\logs\service_stdout.log"
nssm set NFe_Backend AppStderr "C:\nfe_app\logs\service_stderr.log"
nssm set NFe_Backend DisplayName "Sistema NFe - Backend"
nssm set NFe_Backend Description "Servidor backend do Sistema de Emissão de NFe"
nssm set NFe_Backend Start SERVICE_AUTO_START

# Iniciar serviço
nssm start NFe_Backend
```

### 7.4 Gerenciar Serviço

```powershell
# Verificar status
nssm status NFe_Backend

# Parar serviço
nssm stop NFe_Backend

# Reiniciar serviço
nssm restart NFe_Backend

# Remover serviço (se necessário)
nssm remove NFe_Backend confirm
```

---

## 8. Configuração de Firewall

### 8.1 Abrir Portas

```powershell
# Porta HTTP (80)
New-NetFirewallRule -DisplayName "HTTP NFe" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow

# Porta Backend (5000) - se necessário acesso direto
New-NetFirewallRule -DisplayName "NFe Backend" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow

# Porta PostgreSQL (5432) - apenas se acesso remoto necessário
New-NetFirewallRule -DisplayName "PostgreSQL" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow
```

### 8.2 Configurar IP Fixo

1. Abra **Network and Sharing Center**
2. Clique na conexão de rede → **Properties**
3. Selecione **Internet Protocol Version 4 (TCP/IPv4)** → **Properties**
4. Configure:
   - IP address: `192.168.X.X` (conforme sua rede)
   - Subnet mask: `255.255.255.0`
   - Default gateway: `192.168.X.1`
   - Preferred DNS: `8.8.8.8`
   - Alternate DNS: `8.8.4.4`

---

## 9. Backup e Manutenção

### 9.1 Script de Backup do Banco

Crie `C:\nfe_app\backup\backup_db.ps1`:

```powershell
# Configurações
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "C:\nfe_app\backup"
$backupFile = "$backupDir\sjtnfe_$timestamp.backup"
$pgDumpPath = "C:\Program Files\PostgreSQL\14\bin\pg_dump.exe"

# Criar backup
$env:PGPASSWORD = "SuaSenhaSegura123!"
& $pgDumpPath -h localhost -U nfe_app -F c -b -v -f $backupFile sjtnfe

# Remover backups antigos (manter últimos 7 dias)
Get-ChildItem -Path $backupDir -Filter "*.backup" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | 
    Remove-Item
```

### 9.2 Agendar Backup Diário

```powershell
# Criar tarefa agendada
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File C:\nfe_app\backup\backup_db.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable

Register-ScheduledTask -TaskName "Backup NFe Database" -Action $action -Trigger $trigger -Principal $principal -Settings $settings
```

### 9.3 Rotação de Logs

Crie `C:\nfe_app\rotate_logs.ps1`:

```powershell
$logsDir = "C:\nfe_app\logs"
$maxDays = 30

Get-ChildItem -Path $logsDir -Filter "*.log" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$maxDays) } | 
    Remove-Item -Force
```

---

## 10. Troubleshooting

### 10.1 Logs Importantes

- **IIS Logs**: `C:\inetpub\logs\LogFiles`
- **Application Logs**: `C:\nfe_app\logs\app.log`
- **Service Logs**: `C:\nfe_app\logs\service_stdout.log`
- **PostgreSQL Logs**: `C:\Program Files\PostgreSQL\14\data\log`

### 10.2 Comandos Úteis

```powershell
# Verificar status do IIS
Get-Service W3SVC

# Verificar status do PostgreSQL
Get-Service postgresql-x64-14

# Verificar status do serviço NFe
Get-Service NFe_Backend

# Verificar portas em uso
netstat -ano | findstr ":80"
netstat -ano | findstr ":5000"
netstat -ano | findstr ":5432"

# Testar conectividade ao banco
Test-NetConnection -ComputerName localhost -Port 5432
```

### 10.3 Problemas Comuns

#### Erro 500.0 - Internal Server Error
- Verifique `web.config` está correto
- Verifique caminhos no `scriptProcessor`
- Verifique logs em `C:\nfe_app\logs`

#### Erro de Permissão
```powershell
icacls "C:\nfe_app" /reset /T
icacls "C:\nfe_app" /grant "IIS_IUSRS:(OI)(CI)RX" /T
icacls "C:\nfe_app\logs" /grant "IIS_IUSRS:(OI)(CI)F" /T
```

#### Porta 80 já em uso
```powershell
# Verificar o que está usando a porta
netstat -ano | findstr ":80"

# Parar outros serviços se necessário
Stop-Service -Name "Serviço_Conflitante"
```

#### Python não encontrado
```powershell
# Verificar PATH
$env:Path

# Adicionar Python ao PATH
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Python313;C:\Python313\Scripts", "Machine")
```

---

## 📝 Checklist Final

- [ ] PostgreSQL instalado e rodando
- [ ] Database `sjtnfe` criada
- [ ] Python 3.13 instalado
- [ ] Projeto copiado para `C:\nfe_app`
- [ ] Ambiente virtual criado e dependências instaladas
- [ ] Arquivo `.env` configurado
- [ ] Banco de dados inicializado
- [ ] IIS instalado e configurado
- [ ] Site IIS criado e funcionando
- [ ] Serviço Windows criado e iniciado
- [ ] Firewall configurado
- [ ] Backup automático agendado
- [ ] Acesso testado de outra máquina na rede

---

## 🔐 Segurança em Produção

### SSL/HTTPS (Recomendado para Produção)

1. Obtenha certificado SSL
2. No IIS Manager → Site → Bindings → Add
3. Configure:
   - Type: `https`
   - Port: `443`
   - SSL certificate: (selecione certificado)

### Hardening Adicional

```powershell
# Desabilitar TLS 1.0 e 1.1
New-Item 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.0\Server' -Force
New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.0\Server' -Name 'Enabled' -Value 0 -PropertyType 'DWord'

# Configurar políticas de senha forte
net accounts /minpwlen:12 /maxpwage:90
```

---

## 📞 Suporte

Para problemas técnicos:
- Verifique logs em `C:\nfe_app\logs`
- Consulte documentação do Flask: https://flask.palletsprojects.com/
- Consulte documentação do IIS: https://docs.microsoft.com/iis

---

**Última atualização**: Novembro 2025
**Versão do guia**: 1.0

# 🚀 Guia de Instalação dos Serviços no Servidor

Este guia explica como configurar os serviços systemd para rodar automaticamente no servidor Windows Server 2016 ou Linux.

---

## 📋 Pré-requisitos

- Python 3.8+ instalado
- PostgreSQL rodando
- Código do projeto em `/var/www/api_nfe` (ou caminho equivalente)
- Ambiente virtual Python configurado

---

## 🐧 Para Linux (Ubuntu/Debian)

### 1. Copiar arquivos de serviço

```bash
# Copiar os arquivos .service para o systemd
sudo cp deployment/api_nfe_principal.service /etc/systemd/system/
sudo cp deployment/api_nfe_ia.service /etc/systemd/system/

# Dar permissões corretas
sudo chmod 644 /etc/systemd/system/api_nfe_principal.service
sudo chmod 644 /etc/systemd/system/api_nfe_ia.service
```

### 2. Criar diretório de logs

```bash
sudo mkdir -p /var/www/api_nfe/logs
sudo chown -R www-data:www-data /var/www/api_nfe/logs
```

### 3. Recarregar systemd

```bash
sudo systemctl daemon-reload
```

### 4. Habilitar serviços (iniciar automaticamente no boot)

```bash
sudo systemctl enable api_nfe_principal.service
sudo systemctl enable api_nfe_ia.service
```

### 5. Iniciar serviços

```bash
sudo systemctl start api_nfe_principal.service
sudo systemctl start api_nfe_ia.service
```

### 6. Verificar status

```bash
# Ver status de ambos
sudo systemctl status api_nfe_principal.service
sudo systemctl status api_nfe_ia.service

# Ver logs em tempo real
sudo journalctl -u api_nfe_principal.service -f
sudo journalctl -u api_nfe_ia.service -f
```

---

## 🪟 Para Windows Server 2016

Como Windows não usa systemd, você tem duas opções:

### Opção 1: NSSM (Non-Sucking Service Manager) - RECOMENDADO

#### 1. Baixar NSSM

```powershell
# Baixe de: https://nssm.cc/download
# Ou via Chocolatey:
choco install nssm
```

#### 2. Instalar Serviço Principal

```powershell
# Abrir PowerShell como Administrador
cd C:\api_nfe

# Criar serviço principal
nssm install ApiNfePrincipal "C:\api_nfe\venv\Scripts\python.exe" "C:\api_nfe\app.py"

# Configurar
nssm set ApiNfePrincipal AppDirectory "C:\api_nfe"
nssm set ApiNfePrincipal AppStdout "C:\api_nfe\logs\api_principal.log"
nssm set ApiNfePrincipal AppStderr "C:\api_nfe\logs\api_principal_error.log"
nssm set ApiNfePrincipal DisplayName "API NFe - Servidor Principal"
nssm set ApiNfePrincipal Description "API principal para emissão de NFe"
nssm set ApiNfePrincipal Start SERVICE_AUTO_START

# Iniciar
nssm start ApiNfePrincipal
```

#### 3. Instalar Serviço de IA

```powershell
# Criar serviço de IA
nssm install ApiNfeIA "C:\api_nfe\venv\Scripts\python.exe" "C:\api_nfe\api_ia_unificada.py"

# Configurar
nssm set ApiNfeIA AppDirectory "C:\api_nfe"
nssm set ApiNfeIA AppStdout "C:\api_nfe\logs\api_ia.log"
nssm set ApiNfeIA AppStderr "C:\api_nfe\logs\api_ia_error.log"
nssm set ApiNfeIA DisplayName "API NFe - Serviço de IA"
nssm set ApiNfeIA Description "API de sugestões tributárias usando IA"
nssm set ApiNfeIA Start SERVICE_AUTO_START
nssm set ApiNfeIA DependOnService ApiNfePrincipal

# Iniciar
nssm start ApiNfeIA
```

#### 4. Verificar Status

```powershell
# Ver status
nssm status ApiNfePrincipal
nssm status ApiNfeIA

# Ver serviços no painel
services.msc
```

#### 5. Comandos Úteis

```powershell
# Parar serviços
nssm stop ApiNfePrincipal
nssm stop ApiNfeIA

# Reiniciar serviços
nssm restart ApiNfePrincipal
nssm restart ApiNfeIA

# Remover serviços (se necessário)
nssm remove ApiNfePrincipal confirm
nssm remove ApiNfeIA confirm
```

### Opção 2: Windows Task Scheduler

Se não quiser usar NSSM, pode usar o Agendador de Tarefas:

#### 1. Criar script de inicialização

Salvar como `C:\api_nfe\start_services.bat`:

```batch
@echo off
cd C:\api_nfe
call venv\Scripts\activate

echo Iniciando API Principal...
start /B python app.py > logs\api_principal.log 2>&1

echo Aguardando 5 segundos...
timeout /t 5 /nobreak > nul

echo Iniciando API de IA...
start /B python api_ia_unificada.py > logs\api_ia.log 2>&1

echo Servicos iniciados!
```

#### 2. Criar tarefa agendada

```powershell
# PowerShell como Administrador
$action = New-ScheduledTaskAction -Execute "C:\api_nfe\start_services.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "API NFe Services" -Action $action -Trigger $trigger -Principal $principal -Settings $settings
```

---

## 🔧 Comandos de Manutenção

### Linux

```bash
# Parar serviços
sudo systemctl stop api_nfe_principal.service
sudo systemctl stop api_nfe_ia.service

# Reiniciar serviços
sudo systemctl restart api_nfe_principal.service
sudo systemctl restart api_nfe_ia.service

# Desabilitar auto-start
sudo systemctl disable api_nfe_principal.service
sudo systemctl disable api_nfe_ia.service

# Ver logs dos últimos 100 linhas
sudo journalctl -u api_nfe_principal.service -n 100
sudo journalctl -u api_nfe_ia.service -n 100

# Ver logs de hoje
sudo journalctl -u api_nfe_principal.service --since today
sudo journalctl -u api_nfe_ia.service --since today
```

### Windows (NSSM)

```powershell
# Parar
nssm stop ApiNfePrincipal
nssm stop ApiNfeIA

# Reiniciar
nssm restart ApiNfePrincipal
nssm restart ApiNfeIA

# Ver logs
Get-Content C:\api_nfe\logs\api_principal.log -Tail 100 -Wait
Get-Content C:\api_nfe\logs\api_ia.log -Tail 100 -Wait
```

---

## ✅ Verificação de Funcionamento

### 1. Testar API Principal

```bash
# Linux/Mac
curl http://localhost:8080/

# Windows PowerShell
Invoke-WebRequest -Uri http://localhost:8080/
```

### 2. Testar API de IA

```bash
# Linux/Mac
curl http://localhost:9000/health

# Windows PowerShell
Invoke-WebRequest -Uri http://localhost:9000/health
```

### 3. Testar Sugestão de IA

```bash
curl -X POST http://localhost:9000/api/sugestao \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Notebook Dell",
    "tipo_item": "Produto",
    "regime_tributario": "Simples Nacional"
  }'
```

---

## 🐛 Troubleshooting

### Serviço não inicia

1. Verificar se o Python está no PATH correto
2. Verificar se o ambiente virtual existe
3. Verificar permissões das pastas
4. Verificar se as portas 8080 e 9000 estão livres

```bash
# Linux - verificar portas
sudo netstat -tlnp | grep -E '8080|9000'

# Windows - verificar portas
netstat -ano | findstr "8080 9000"
```

### Logs de erro

```bash
# Linux
sudo journalctl -u api_nfe_principal.service --since "10 minutes ago"
sudo journalctl -u api_nfe_ia.service --since "10 minutes ago"

# Windows
Get-Content C:\api_nfe\logs\api_principal_error.log -Tail 50
Get-Content C:\api_nfe\logs\api_ia_error.log -Tail 50
```

### Permissões

```bash
# Linux - corrigir permissões
sudo chown -R www-data:www-data /var/www/api_nfe
sudo chmod -R 755 /var/www/api_nfe
sudo chmod -R 777 /var/www/api_nfe/logs
```

---

## 📊 Monitoramento

### Criar script de monitoramento

Linux - salvar como `/usr/local/bin/check_api_nfe.sh`:

```bash
#!/bin/bash

echo "=========================================="
echo "  Status dos Serviços API NFe"
echo "=========================================="
echo ""

# API Principal
if systemctl is-active --quiet api_nfe_principal.service; then
    echo "✅ API Principal: RODANDO"
    echo "   Porta 8080 - $(curl -s http://localhost:8080/ | head -c 50)..."
else
    echo "❌ API Principal: PARADO"
fi

echo ""

# API de IA
if systemctl is-active --quiet api_nfe_ia.service; then
    echo "✅ API de IA: RODANDO"
    echo "   Porta 9000 - Sugestões NCM/Tributação"
else
    echo "❌ API de IA: PARADO"
fi

echo ""
echo "=========================================="
```

Dar permissão e executar:
```bash
sudo chmod +x /usr/local/bin/check_api_nfe.sh
check_api_nfe.sh
```

---

## 📝 Notas Importantes

1. **Ambiente Virtual**: Os serviços usam o Python do ambiente virtual em `venv/`
2. **Logs**: Logs são salvos em `/var/www/api_nfe/logs/` (Linux) ou `C:\api_nfe\logs\` (Windows)
3. **Auto-start**: Ambos os serviços iniciam automaticamente no boot
4. **Dependências**: API de IA depende da API Principal estar rodando
5. **Portas**: API Principal (8080), API de IA (9000)
6. **Usuário**: No Linux, roda como `www-data`. No Windows, como SYSTEM

---

## 🔄 Atualização do Código

Quando atualizar o código no servidor:

```bash
# 1. Ir para o diretório
cd /var/www/api_nfe  # Linux
cd C:\api_nfe       # Windows

# 2. Fazer backup
cp -r . ../api_nfe_backup_$(date +%Y%m%d)

# 3. Atualizar código (Git)
git pull origin main

# 4. Atualizar dependências
source venv/bin/activate  # Linux
venv\Scripts\activate    # Windows
pip install -r requirements.txt

# 5. Reiniciar serviços
# Linux:
sudo systemctl restart api_nfe_principal.service
sudo systemctl restart api_nfe_ia.service

# Windows (NSSM):
nssm restart ApiNfePrincipal
nssm restart ApiNfeIA
```

---

Está tudo configurado! Agora os dois serviços rodarão automaticamente no servidor. 🚀

# 🚀 Guia Completo de Deploy na AWS

**Data:** 26 de dezembro de 2025  
**Sistema:** API NFe com IA (LM Studio Local via VPN) + PostgreSQL  
**Conta:** AWS Free Tier

---

## 📋 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                  AWS Cloud                          │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  EC2 Instance (t2.small ou t2.medium)        │  │
│  │                                              │  │
│  │  ├─ Flask App (porta 8080)                  │  │
│  │  ├─ IA Service (porta 8081)                 │  │
│  │  └─ Acesso via IP Público + Port Forward    │  │
│  └──────────────────────────────────────────────┘  │
│                        │                            │
│  ┌──────────────────────────────────────────────┐  │
│  │  RDS PostgreSQL (db.t3.micro)                │  │
│  │  - Database: sjtnfe                          │  │
│  │  - Multi-AZ: No (Free Tier)                  │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        │
                  [Internet / IP Público]
                        │
┌─────────────────────────────────────────────────────┐
│              Rede Local (On-Premises)               │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Roteador ASUS (OpenVPN Server)             │  │
│  │  - Port Forwarding: 1234 → 192.168.0.52     │  │
│  │  - IP Público: xxx.xxx.xxx.xxx              │  │
│  └──────────────────────────────────────────────┘  │
│                        │                            │
│  ┌──────────────────────────────────────────────┐  │
│  │  Servidor Windows (192.168.0.52)            │  │
│  │  └─ LM Studio Server (porta 1234)           │  │
│  │     Configurado: 0.0.0.0:1234                │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## ⚠️ IMPORTANTE: Custos AWS Free Tier

O plano gratuito AWS tem limitações:
- **EC2:** 750 horas/mês de t2.micro (1 vCPU, 1GB RAM)
- **RDS:** 750 horas/mês de db.t2.micro/db.t3.micro
- **S3:** 5GB de armazenamento
- **✅ LM Studio rodará no servidor local** (não precisa de recursos AWS)
- **Recomendação:** Use t2.small (2GB RAM) ou t2.medium (4GB RAM) se necessário
- **Custos:** t2.small (~$0.023/hora = ~$17/mês) ou t2.medium (~$0.047/hora = ~$35/mês)

---

## �️ LIMPEZA COMPLETA (Reset AWS)

**Use esta seção se precisar excluir tudo e começar do zero.**

### Ordem de Exclusão (IMPORTANTE!)

⚠️ **Siga esta ordem** para evitar erros de dependências:

### 1. Parar e Excluir Instância EC2

```bash
# Console AWS > EC2 > Instances
```

1. Selecione a instância `nfe-api-server`
2. **Instance state** > **Terminate instance**
3. Aguarde 2-3 minutos até o status mudar para `terminated`

### 2. Excluir RDS Database

```bash
# Console AWS > RDS > Databases
```

1. Selecione `nfe-database`
2. **Actions** > **Delete**
3. ⚠️ **Desmarque**: "Create final snapshot" (se não quiser backup)
4. ⚠️ **Marque**: "I acknowledge..."
5. Digite: `delete me` (conforme solicitado)
6. **Delete**
7. Aguarde 5-10 minutos para exclusão completa

### 3. Excluir Security Groups

⚠️ **Aguarde EC2 e RDS serem completamente excluídos primeiro!**

```bash
# Console AWS > EC2 > Security Groups
```

**Ordem de exclusão dos Security Groups:**

1. Primeiro: `nfe-api-sg` (Security Group da EC2)
   - Selecione o grupo
   - **Actions** > **Delete security groups**
   - Confirme

2. Depois: `nfe-database-sg` (Security Group do RDS)
   - Selecione o grupo
   - **Actions** > **Delete security groups**
   - Confirme

**Se aparecer erro "dependency violation":**
- Aguarde mais alguns minutos (recursos ainda estão sendo desvinculados)
- Ou vá em **Inbound rules** e delete todas as regras primeiro

### 4. Excluir Volumes EBS Órfãos (se houver)

```bash
# Console AWS > EC2 > Volumes
```

1. Procure volumes com estado **available** (não attached)
2. Selecione o volume
3. **Actions** > **Delete volume**

### 5. Excluir Key Pair (opcional)

```bash
# Console AWS > EC2 > Key Pairs
```

1. Selecione `nfe-api-key`
2. **Actions** > **Delete**
3. Confirme

### 6. Excluir Snapshots de RDS (se houver)

```bash
# Console AWS > RDS > Snapshots
```

1. Selecione snapshots de `nfe-database`
2. **Actions** > **Delete snapshot**

### 7. Verificar Custos Zerados

```bash
# Console AWS > Billing > Bills
```

Verifique se não há recursos cobrando.

---

## ✅ Checklist de Limpeza

Antes de começar novamente, confirme que excluiu:

- [ ] Instância EC2 terminada (status: terminated)
- [ ] RDS Database deletado
- [ ] Security Group `nfe-api-sg` deletado
- [ ] Security Group `nfe-database-sg` deletado
- [ ] Volumes EBS órfãos deletados
- [ ] Key Pair deletado (opcional)
- [ ] Snapshots RDS deletados (opcional)
- [ ] Verificado billing zerado

**Agora você pode começar do zero!** ⬇️

---

## �📝 ETAPA 1: Configurar RDS PostgreSQL

### 1.1 Criar Banco de Dados RDS

1. No Console AWS, acesse **RDS**
2. Clique em **Create database**

**Configurações:**

```yaml
Engine: PostgreSQL 15.x
Template: Free tier
DB Instance Identifier: nfe-database
Master Username: postgres
Master Password: [CRIAR SENHA FORTE - ANOTE!]

Instance Configuration:
  - Class: db.t3.micro (Free tier eligible)
  
Storage:
  - Type: General Purpose (SSD)
  - Allocated: 20 GB
  - Enable autoscaling: No
  
Connectivity:
  - VPC: Default VPC
  - Public access: Yes (para desenvolvimento)
  - VPC Security Group: Create new
  - Name: nfe-database-sg
  
Additional Configuration:
  - Initial database name: sjtnfe
  - Backup retention: 7 days
  - Enable automatic backups: Yes
```

3. Clique em **Create database**
4. **Aguarde ~10 minutos** para o banco ser criado

### 1.2 Configurar Security Group do RDS

1. Vá em **EC2 > Security Groups**
2. Encontre `nfe-database-sg`
3. Em **Inbound rules**, clique em **Edit inbound rules**
4. Adicione:

```
Type: PostgreSQL
Protocol: TCP
Port: 5432
Source: [IP da sua instância EC2] ou 0.0.0.0/0 (temporariamente)
Description: Allow PostgreSQL from EC2
```

5. **Anote o Endpoint do RDS** (ex: `nfe-database.xxxxx.us-east-1.rds.amazonaws.com`)

### 1.3 Testar Conexão (do seu computador)

```bash
psql -h nfe-database.xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d sjtnfe \
     -p 5432
```

**⚠️ TROUBLESHOOTING: Connection timeout**

Se você receber erro de timeout, siga estes passos:

**Passo 1: Verificar Public Access**
1. Console AWS > RDS > Databases > nfe-database
2. Em **Connectivity & security** > **Public access** deve estar **Yes**
3. Se estiver **No**, clique em **Modify** e habilite

**Passo 2: Atualizar Security Group com seu IP atual**

```bash
# Descobrir seu IP público
curl https://checkip.amazonaws.com
# Anote o IP retornado (ex: 177.123.45.67)
```

1. Console AWS > EC2 > Security Groups
2. Encontre `nfe-database-sg`
3. Aba **Inbound rules** > **Edit inbound rules**
4. Edite ou adicione regra:
   ```
   Type: PostgreSQL
   Protocol: TCP
   Port: 5432
   Source: [SEU_IP]/32  (ex: 177.123.45.67/32)
   Description: Allow from my IP
   ```
5. Clique **Save rules**

**Passo 3: Testar conexão inicial**

```bash
# Primeiro, conecte ao banco padrão 'postgres'
psql -h nfe-database.xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d postgres
```

**Passo 4: Criar banco de dados sjtnfe (se necessário)**

Se você NÃO especificou o nome do banco durante a criação do RDS, precisa criar manualmente:

```sql
-- Dentro do psql, execute:
CREATE DATABASE sjtnfe;

-- Listar bancos para confirmar
\l

-- Sair
\q
```

**Passo 5: Conectar ao banco sjtnfe**

```bash
# Agora conecte ao banco sjtnfe
psql -h nfe-database.xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d sjtnfe
```

**✅ Se conectar com sucesso, está pronto!**

**Alternativa temporária (APENAS PARA TESTES):**
- Source: `0.0.0.0/0` (permite de qualquer lugar - NÃO recomendado para produção)

---

## 📝 ETAPA 2: Criar e Configurar Instância EC2

### 2.1 Lançar Instância EC2

1. No Console AWS, acesse **EC2**
2. Clique em **Launch Instance**

**Configurações:**

```yaml
Name: nfe-api-server
AMI: Ubuntu Server 22.04 LTS (64-bit x86)
Instance Type: t2.small (ou t2.medium se necessário)
  ℹ️ NOTA: LM Studio rodará no servidor local via VPN

Key pair: 
  - Create new key pair
  - Name: nfe-api-key
  - Type: RSA
  - Format: .pem
  - [BAIXE E GUARDE O ARQUIVO .pem]

Network Settings:
  - VPC: Default
  - Auto-assign public IP: Enable
  - Security Group: Create new
    Name: nfe-api-sg
    
Inbound Rules:
  - SSH (22): My IP (ou seu IP com /32, ex: 177.123.45.67/32)
  - HTTP (80): 0.0.0.0/0 (Anywhere)
  - HTTPS (443): 0.0.0.0/0 (Anywhere)
  - Custom TCP (8080): 0.0.0.0/0 (Flask App - temporário)
  - UDP (1194): SEU_IP_VPN_SERVER/32 (ex: 200.100.50.25/32)
  - Custom TCP (8081): 0.0.0.0/0 (IA Service - temporário)
  
⚠️ IMPORTANTE sobre notação CIDR:
  - IP único: adicione /32 (ex: 192.168.0.52/32)
  - Rede local: use /24 (ex: 192.168.0.0/24)
  - Qualquer lugar: use 0.0.0.0/0
  - NÃO use apenas o IP sem /XX
  
Storage:
  - 30 GB gp3 (SSD)
  - Encryption: Not enabled
```

3. Clique em **Launch instance**
4. **Anote o IP Público** da instância (ex: `54.123.45.67`)

### 2.2 Configurar Inbound Rules (se pulou esta etapa)

Se você já criou a instância EC2 sem configurar as regras, siga estes passos:

1. **Console AWS > EC2 > Instances**
2. Selecione sua instância `nfe-api-server`
3. Aba **Security** > Clique no nome do **Security Group** (ex: `launch-wizard-1` ou `nfe-api-sg`)
4. Aba **Inbound rules** > **Edit inbound rules**
5. Clique em **Add rule** para cada regra abaixo:

```yaml
Regra 1 - SSH:
  Type: SSH
  Protocol: TCP
  Port: 22
  Source: My IP (ou seu IP/32)
  Description: SSH access

Regra 2 - HTTP:
  Type: HTTP
  Protocol: TCP
  Port: 80
  Source: 0.0.0.0/0
  Description: HTTP public access

Regra 3 - HTTPS:
  Type: HTTPS
  Protocol: TCP
  Port: 443
  Source: 0.0.0.0/0
  Description: HTTPS public access

Regra 4 - Flask App:
  Type: Custom TCP
  Protocol: TCP
  Port: 8080
  Source: 0.0.0.0/0
  Description: Flask App

Regra 5 - IA Service:
  Type: Custom TCP
  Protocol: TCP
  Port: 8081
  Source: 0.0.0.0/0
  Description: IA Service

Regra 6 - OpenVPN:
  Type: Custom UDP
  Protocol: UDP
  Port: 1194
  Source: SEU_IP_VPN_SERVER/32
  Description: OpenVPN from local server
```

6. Clique em **Save rules**

**✅ Pronto!** As regras são aplicadas imediatamente, sem precisar reiniciar a instância.

### 2.3 Configurar Permissões da Chave SSH

```bash
# No seu Mac:
chmod 400 ~/Downloads/nfe-api-key.pem
```

### 2.4 Conectar via SSH

```bash
ssh -i ~/Downloads/nfe-api-key.pem ubuntu@54.123.45.67
```

---

## 📝 ETAPA 3: Configurar Servidor Ubuntu

### 3.1 Atualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Instalar Dependências Base

```bash
# Python e ferramentas
sudo apt install -y python3.10 python3-pip python3-venv python3-dev

# PostgreSQL client
sudo apt install -y postgresql-client

# Build essentials
sudo apt install -y build-essential libssl-dev libffi-dev

# Git
sudo apt install -y git

# XML libraries
sudo apt install -y libxml2-dev libxslt1-dev

# PKCS11 (para certificados A3)
sudo apt install -y libpcsclite-dev pcscd

# Nginx (reverse proxy)
sudo apt install -y nginx

# Supervisor (gerenciar processos)
sudo apt install -y supervisor
```

---

## 📝 ETAPA 4: Configurar Acesso ao LM Studio Local

**✅ ARQUITETURA:** O LM Studio roda no servidor Windows local (IP: 192.168.0.52). O OpenVPN Server está configurado no **roteador ASUS**. A AWS acessa o LM Studio via IP público do roteador com port forwarding.

### 4.1 Configurar Port Forwarding no Roteador ASUS

**No roteador ASUS:**

1. Acesse a interface do roteador (geralmente `http://router.asus.com` ou `192.168.1.1`)
2. Faça login com suas credenciais
3. Navegue até **WAN** > **Virtual Server / Port Forwarding**
4. Adicione nova regra:

```yaml
Service Name: LM Studio
Port Range: 1234
Local IP: 192.168.0.52
Local Port: 1234
Protocol: TCP
Enable: Yes
```

5. Clique em **Add** e depois **Apply**

### 4.2 Descobrir IP Público do Roteador

```bash
# No seu Mac ou Windows local, descubra o IP público
curl https://checkip.amazonaws.com

# Ou visite: https://www.whatismyip.com/
# Anote o IP (ex: 200.150.100.50)
```

### 4.2 Descobrir IP Público do Roteador

```bash
# No seu Mac ou Windows local, descubra o IP público
curl https://checkip.amazonaws.com

# Ou visite: https://www.whatismyip.com/
# Anote o IP (ex: 200.150.100.50)
```

### 4.3 Configurar LM Studio no Servidor Windows Local

**⚠️ CRÍTICO:** Configure o LM Studio para aceitar conexões externas.

#### Passo 1: Configurar Network Settings no LM Studio

1. No servidor Windows local (IP: 192.168.0.52), abra o **LM Studio**
2. Na barra lateral esquerda, clique em **"Local Server"** (ícone de servidor)
3. Clique no botão **"Start Server"** se ainda não estiver rodando

#### Passo 2: Configurar Network Settings

1. Clique no ícone de **engrenagem (⚙️) "Settings"** no canto superior direito da seção Local Server
2. Em **"Network"**, você verá:
   ```
   Server Address: 127.0.0.1
   Port: 1234
   ```

3. **ALTERE** o Server Address:
   ```
   ✅ De: 127.0.0.1 (apenas localhost)
   ✅ Para: 0.0.0.0 (aceita de qualquer IP)
   ```

4. Mantenha a porta como **1234**

5. Clique em **"Apply"** ou **"Save"**

6. **REINICIE o servidor:**
   - Clique em **"Stop Server"**
   - Aguarde 2 segundos
   - Clique em **"Start Server"** novamente

#### Passo 3: Verificar se está ouvindo em todas as interfaces

No PowerShell ou CMD do Windows, execute:

```powershell
netstat -an | findstr :1234
```

**✅ Deve mostrar:**
```
TCP    0.0.0.0:1234           0.0.0.0:0              LISTENING
```

**❌ Se mostrar (ERRADO):**
```
TCP    127.0.0.1:1234         0.0.0.0:0              LISTENING
```
Significa que ainda está ouvindo apenas em localhost. Repita o Passo 2.

#### Passo 4: Configurar Firewall do Windows

1. Abra **"Firewall do Windows com Segurança Avançada"**
   - Pressione `Win + R`
   - Digite: `wf.msc`
   - Enter

2. Clique em **"Regras de Entrada"** (Inbound Rules)

3. Clique em **"Nova Regra..."** (New Rule) no painel direito

4. Configure a regra:
   - Tipo: **Porta**
   - Protocolo: **TCP**
   - Porta específica: **1234**
   - Ação: **Permitir a conexão**
   - Perfil: Marque **Domínio**, **Privado** e **Público**
   - Nome: `LM Studio Server`
   - Clique em **Concluir**

#### Passo 5: Testar Acesso Localmente

No servidor Windows, teste se está acessível:

```powershell
# PowerShell
Invoke-WebRequest -Uri http://localhost:1234/v1/models
```

Ou pelo navegador:
```
http://localhost:1234/v1/models
```

Deve retornar JSON com os modelos disponíveis.

### 4.4 Atualizar Configuração da API na AWS

**Na instância EC2 (via SSH):**

```bash
# Editar o arquivo de configuração do serviço IA
nano /home/ubuntu/api_nfe/ia_service/main.py

# Na linha 119, altere o IP para seu IP PÚBLICO:
# llm_url = "http://SEU_IP_PUBLICO:1234/v1/chat/completions"
# Exemplo: llm_url = "http://200.150.100.50:1234/v1/chat/completions"

# Salvar: Ctrl+X, Y, Enter
```

### 4.5 Reiniciar Serviço de IA na AWS

```bash
# Reiniciar serviço
sudo systemctl restart api-nfe-ia

# Verificar status
sudo systemctl status api-nfe-ia

# Ver logs
sudo journalctl -u api-nfe-ia -n 50 --no-pager
```

### 4.6 Testar Acesso da AWS ao LM Studio

```bash
# Testar se AWS consegue acessar LM Studio via IP público
curl -s http://SEU_IP_PUBLICO:1234/v1/models | jq '.'

# Deve retornar JSON com os modelos:
# {
#   "data": [
#     {
#       "id": "codellama-7b-instruct",
#       "object": "model",
#       ...
#     }
#   ]
# }
```

#### Troubleshooting LM Studio

**Problema: "Connection refused" ou timeout via IP público**

1. **Verificar se port forwarding está ativo no roteador:**
   - Acesse o roteador ASUS
   - Verifique se a regra da porta 1234 está habilitada
   - Teste do Windows local: `Invoke-WebRequest -Uri http://SEU_IP_PUBLICO:1234/v1/models`

2. **Verificar firewall do roteador:**
   - Alguns roteadores têm firewall adicional
   - Certifique-se de que a porta 1234 TCP está permitida

3. **Verificar se LM Studio está rodando:**
   - Abra LM Studio
   - Vá em "Local Server"
   - Verifique se mostra "Server is running"

2. **Verificar configuração de rede:**
   ```
   Server Address deve ser: 0.0.0.0
   Port deve ser: 1234
   ```

3. **Verificar firewall:**
   - Desabilite temporariamente o firewall do Windows para testar
   - Se funcionar, o problema é o firewall (adicione regra conforme Passo 5)

4. **Verificar modelo carregado:**
   - LM Studio precisa ter um modelo carregado
   - Vá em "Local Server" > "Select a model to load"
   - Recomendado: `codellama-7b-instruct` ou `mistral-7b-instruct`

5. **Verificar logs do LM Studio:**
   - Na aba "Local Server", veja os logs na parte inferior
   - Procure por erros em vermelho

**Problema: "Connection refused" no Windows mas LM Studio rodando**

- Verifique se Windows Defender ou antivírus não está bloqueando
- Teste desabilitando temporariamente o firewall
- Certifique-se que o LM Studio está em 0.0.0.0:1234, não 127.0.0.1:1234

1. Baixe um modelo compatível:
   - Vá em "Discover" (ícone de lupa)
   - Busque: `codellama-7b-instruct` ou `mistral-7b-instruct`
   - Clique em "Download"
   - Aguarde o download completar

2. Carregue o modelo:
   - Vá em "Local Server"
   - Clique em "Select a model to load"
   - Escolha o modelo baixado
   - Clique em "Load Model"

**Problema: AWS não consegue acessar o IP público**

1. **Verificar port forwarding no roteador:**
   ```powershell
   # No Windows, testar acesso via IP público local
   Invoke-WebRequest -Uri http://SEU_IP_PUBLICO:1234/v1/models
   
   # Se funcionar localmente mas não da AWS, pode ser firewall do roteador
   ```

2. **Verificar IP público não mudou:**
   ```bash
   # O IP público pode mudar se não for estático
   curl https://checkip.amazonaws.com
   # Compare com o IP configurado em ia_service/main.py
   ```

3. **Testar conectividade da AWS:**
   ```bash
   # Na AWS (via SSH)
   telnet SEU_IP_PUBLICO 1234
   # Se não conectar, problema de rede/firewall
   
   # Testar HTTP
   curl -v http://SEU_IP_PUBLICO:1234/v1/models
   ```

4. **Verificar Security Group da AWS:**
   - Console AWS > EC2 > Security Groups
   - Certifique-se que NÃO há regra bloqueando tráfego de saída (Outbound)
   - Alguns antivírus bloqueiam conexões de rede
   - Adicione LM Studio às exceções

---

## 📝 ETAPA 5: Deploy da Aplicação Flask

### 5.1 Clonar/Copiar Código

**Opção 1: Via Git (se você tiver repositório)**

```bash
cd /home/ubuntu
git clone https://github.com/sjtecnologia/api_nfe.git
cd api_nfe
```

**Opção 2: Via SCP (do seu Mac)**

```bash
# No seu Mac (terminal local):
cd ~/Documents/Developement
tar -czf api_nfe.tar.gz api_nfe
scp -i ~/Downloads/nfe-api-key.pem api_nfe.tar.gz ubuntu@54.123.45.67:/home/ubuntu/

# No servidor SSH:
cd /home/ubuntu
tar -xzf api_nfe.tar.gz
cd api_nfe
```

### 5.2 Criar Virtual Environment

```bash
cd /home/ubuntu/api_nfe
python3 -m venv venv
source venv/bin/activate
```

### 5.3 Instalar Dependências Python

```bash
pip install --upgrade pip
pip install -r requirements.txt

# Instalar dependências extras
pip install gunicorn  # WSGI server
pip install python-dotenv
pip install psycopg2-binary
```

### 5.4 Criar Arquivo de Configuração (.env)

```bash
nano /home/ubuntu/api_nfe/.env
```

```bash
# Flask Configuration
FLASK_SECRET_KEY=sua_chave_secreta_muito_complexa_aqui_123456789
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
PORT=8080

# Database Configuration (RDS)
DATABASE_URL=postgresql://postgres:SUA_SENHA_RDS@nfe-database.xxxxx.us-east-1.rds.amazonaws.com:5432/sjtnfe
DB_HOST=nfe-database.xxxxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=sjtnfe
DB_USER=postgres
DB_PASSWORD=SUA_SENHA_RDS

# Upload and Storage
UPLOAD_FOLDER=/home/ubuntu/api_nfe/uploads
BACKUP_DIR=/home/ubuntu/api_nfe/backups
BACKUP_LOG_DIR=/home/ubuntu/api_nfe/logs

# Log Configuration
LOG_LEVEL=INFO

# SEFAZ Configuration
SEFAZ_AMBIENTE_HOMOLOGACAO=True
USAR_CERTIFICADO_REAL=True
```

**⚠️ IMPORTANTE:** Substitua:
- `SUA_SENHA_RDS` pela senha do RDS
- `nfe-database.xxxxx...` pelo endpoint real do RDS
- `sua_chave_secreta...` por uma chave forte

### 5.5 Criar Diretórios Necessários

```bash
mkdir -p /home/ubuntu/api_nfe/uploads
mkdir -p /home/ubuntu/api_nfe/backups
mkdir -p /home/ubuntu/api_nfe/logs
chmod 755 /home/ubuntu/api_nfe/uploads
chmod 755 /home/ubuntu/api_nfe/backups
chmod 755 /home/ubuntu/api_nfe/logs
```

### 5.6 Migrar Banco de Dados

**⚠️ IMPORTANTE:** Esta seção mostra como migrar seus dados locais para o RDS.

#### Opção 1: Migração Completa do Banco Local (Recomendado)

Se você tem dados de produção localmente, use o script de migração:

**No seu Mac (computador local):**

```bash
# 1. Fazer backup do banco local
cd ~/Documents/Developement/api_nfe
PGPASSWORD='SUA_SENHA_LOCAL' pg_dump -h localhost -U postgres -d sjtnfe --no-owner --no-acl -f backups/sjtnfe_backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Transferir backup para EC2
scp -i ~/Downloads/nfe-new-api-key.pem backups/sjtnfe_backup_*.sql ubuntu@3.87.73.106:/home/ubuntu/
```

**Na instância EC2 (via SSH):**

```bash
# Conectar na EC2
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106

# 1. Terminar conexões existentes (se houver)
PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'sjtnfe' AND pid <> pg_backend_pid();"

# 2. Dropar banco existente
PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com -U postgres -d postgres -c "DROP DATABASE IF EXISTS sjtnfe;"

# 3. Criar banco novamente
PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com -U postgres -d postgres -c "CREATE DATABASE sjtnfe WITH ENCODING='UTF8';"

# 4. Restaurar backup (pode demorar alguns minutos dependendo do tamanho)
echo "Iniciando restauração..."
time PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com -U postgres -d sjtnfe -f /home/ubuntu/sjtnfe_backup_*.sql

# 5. Verificar tabelas criadas
PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com -U postgres -d sjtnfe -c "SELECT COUNT(*) as total_tabelas FROM information_schema.tables WHERE table_schema='public';"

# 6. Limpar backup após confirmar sucesso
rm /home/ubuntu/sjtnfe_backup_*.sql
```

**⚠️ Substitua:**
- `SUA_SENHA_LOCAL` pela senha do PostgreSQL local
- `SUA_SENHA_RDS` pela senha do RDS
- `nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com` pelo endpoint do seu RDS
- `3.87.73.106` pelo IP da sua EC2

#### Opção 2: Schema Vazio (Para novo deployment)

Se você está começando do zero sem dados existentes:

```bash
cd /home/ubuntu/api_nfe

# Importar apenas o schema inicial
PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d sjtnfe \
     -f database/sjtnfedb.sql

# Executar migrações (se houver)
PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d sjtnfe \
     -f database/migrations/add_tipo_certificado.sql
```

**✅ Verificação:**

```bash
# Listar tabelas
PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.xxxxx.us-east-1.rds.amazonaws.com -U postgres -d sjtnfe -c "\dt"

# Contar registros de uma tabela específica (exemplo)
PGPASSWORD='SUA_SENHA_RDS' psql -h nfe-database.xxxxx.us-east-1.rds.amazonaws.com -U postgres -d sjtnfe -c "SELECT COUNT(*) FROM ncms;"
```

### 5.7 Testar Aplicação Manualmente

```bash
source venv/bin/activate
cd /home/ubuntu/api_nfe
python app.py
```

Acesse: `http://54.123.45.67:8080/health`

Se funcionar, **Ctrl+C** para parar.

---

## 📝 ETAPA 6: Configurar Serviço de IA

### 6.1 Atualizar Configuração do IA Service

```bash
nano /home/ubuntu/api_nfe/ia_service/main.py
```

Altere a linha do LM Studio para usar o IP VPN do servidor local:

```python
# De:
llm_url = "http://192.168.0.52:1234/v1/chat/completions"

# Para (usando IP VPN do servidor local):
llm_url = "http://10.8.0.1:1234/v1/chat/completions"  # Substitua pelo seu IP VPN
```

**ℹ️ NOTA:** Substitua `10.8.0.1` pelo IP VPN real do seu servidor local.

E também:

```python
# De:
"http://localhost:1234/api/llm/ncms/search",

# Para:
"http://localhost:8080/api/llm/ncms/search",
```

### 6.2 Testar IA Service

```bash
cd /home/ubuntu/api_nfe/ia_service
source ../venv/bin/activate
pip install fastapi uvicorn
python -m uvicorn main:app --host 0.0.0.0 --port 8081
```

Acesse: `http://54.123.45.67:8081/docs`

Se funcionar, **Ctrl+C** para parar.

---

## 📝 ETAPA 7: Configurar Serviços Systemd

### 7.1 Serviço Flask App

```bash
sudo nano /etc/systemd/system/api-nfe-principal.service
```

```ini
[Unit]
Description=API NFe Principal - Flask Application
After=network.target postgresql.service

[Service]
Type=notify
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/api_nfe
Environment="PATH=/home/ubuntu/api_nfe/venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/home/ubuntu/api_nfe/.env
ExecStart=/home/ubuntu/api_nfe/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8080 \
    --timeout 300 \
    --access-logfile /home/ubuntu/api_nfe/logs/access.log \
    --error-logfile /home/ubuntu/api_nfe/logs/error.log \
    --log-level info \
    app:app

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 7.2 Serviço IA

```bash
sudo nano /etc/systemd/system/api-nfe-ia.service
```

```ini
[Unit]
Description=API NFe IA Service - FastAPI
After=network.target ollama.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/api_nfe/ia_service
Environment="PATH=/home/ubuntu/api_nfe/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/ubuntu/api_nfe/venv/bin/uvicorn \
    main:app \
    --host 0.0.0.0 \
    --port 8081 \
    --workers 2 \
    --log-level info

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 7.3 Habilitar e Iniciar Serviços

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar serviços
sudo systemctl enable api-nfe-principal
sudo systemctl enable api-nfe-ia

# Iniciar serviços
sudo systemctl start api-nfe-principal
sudo systemctl start api-nfe-ia

# Verificar status
sudo systemctl status api-nfe-principal
sudo systemctl status api-nfe-ia
sudo systemctl status ollama
```

### 7.4 Ver Logs

```bash
# Flask App
sudo journalctl -u api-nfe-principal -f

# IA Service
sudo journalctl -u api-nfe-ia -f

# Ollama
sudo journalctl -u ollama -f
```

---

## 📝 ETAPA 8: Configurar Nginx (Reverse Proxy)

### 8.1 Criar Configuração Nginx

```bash
sudo nano /etc/nginx/sites-available/api-nfe
```

```nginx
server {
    listen 80;
    server_name 54.123.45.67;  # Substitua pelo IP público ou domínio

    client_max_body_size 16M;

    # Flask App Principal
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    # IA Service
    location /ia/ {
        proxy_pass http://127.0.0.1:8081/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    # LLM/Ollama (opcional - para testes)
    location /llm/ {
        proxy_pass http://127.0.0.1:11434/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Arquivos estáticos
    location /static {
        alias /home/ubuntu/api_nfe/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 8.2 Ativar Site e Reiniciar Nginx

```bash
# Criar link simbólico
sudo ln -s /etc/nginx/sites-available/api-nfe /etc/nginx/sites-enabled/

# Remover configuração padrão
sudo rm /etc/nginx/sites-enabled/default

# Testar configuração
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 📝 ETAPA 9: Configurar Domínio (Opcional)

### 9.1 Registrar Domínio

Se você tiver um domínio (ex: `api.minhaempresa.com.br`):

1. Acesse seu provedor de DNS (GoDaddy, Registro.br, etc.)
2. Adicione um registro A:
   - **Host:** `api` (ou `@` para domínio raiz)
   - **Type:** A
   - **Value:** `54.123.45.67` (IP público da EC2)
   - **TTL:** 3600

### 9.2 Configurar SSL (HTTPS) com Let's Encrypt

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx
# Obter certificado SSL
sudo certbot --nginx -d api.minhaempresa.com.br

# Renovação automática
sudo systemctl enable certbot.timer
```

---

## 📝 ETAPA 10: Configurar Domínio emitemax.com.br (Hostinger)

### 10.1 Visão Geral da Arquitetura com Domínio

```
┌─────────────────────────────────────────────────────┐
│              emitemax.com.br (Hostinger)            │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Site Institucional                          │  │
│  │  - Página inicial                            │  │
│  │  - Menu "Entrar" → api.emitemax.com.br      │  │
│  │  - Informações sobre o sistema               │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│       api.emitemax.com.br (AWS EC2)                 │
│       IP: 3.87.73.106                               │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Sistema NFe                                 │  │
│  │  - Flask App (porta 8080)                    │  │
│  │  - IA Service (porta 8081)                   │  │
│  │  - Login, Dashboard, Admin Panel             │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 10.2 Configurar DNS na Hostinger

**Passo 1: Acessar Painel da Hostinger**

1. Acesse: https://hpanel.hostinger.com.br/
2. Login com suas credenciais
3. Vá em **Domínios** > Selecione `emitemax.com.br`

**Passo 2: Configurar DNS Records**

1. Clique em **DNS / Name Servers**
2. Clique em **Manage DNS Records**

**Adicione os seguintes registros:**

```yaml
# Registro 1: Subdomínio API apontando para AWS EC2
Type: A
Name: api
Content/Value: 3.87.73.106
TTL: 14400 (ou 3600)

# Registro 2: Domínio principal (site institucional na Hostinger)
Type: A
Name: @
Content/Value: [IP do servidor Hostinger - NÃO mexer se já existe]
TTL: 14400

# Registro 3: WWW (site institucional)
Type: CNAME
Name: www
Content/Value: emitemax.com.br
TTL: 14400
```

**⚠️ IMPORTANTE:**
- **NÃO apague** o registro A principal (`@`) que aponta para a Hostinger
- Adicione **APENAS** o registro `api` apontando para `3.87.73.106`
- Aguarde 30-60 minutos para propagação do DNS

**Passo 3: Verificar Propagação do DNS**

```bash
# No seu Mac, testar se o DNS está funcionando:
nslookup api.emitemax.com.br

# Deve retornar:
# Name:    api.emitemax.com.br
# Address: 3.87.73.106
```

### 10.3 Configurar Nginx na AWS com Domínio

**Passo 1: Atualizar Configuração do Nginx**

```bash
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106
```

```bash
sudo nano /etc/nginx/sites-available/api-nfe
```

**Substitua o conteúdo por:**

```nginx
# Redirecionar HTTP para HTTPS
server {
    listen 80;
    server_name api.emitemax.com.br;

    # Permitir temporariamente para certificado SSL
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirecionar todo o resto para HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# Servidor HTTPS (será configurado após obter certificado)
server {
    listen 443 ssl http2;
    server_name api.emitemax.com.br;

    # Certificados SSL (Let's Encrypt irá adicionar automaticamente)
    # ssl_certificate /etc/letsencrypt/live/api.emitemax.com.br/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/api.emitemax.com.br/privkey.pem;

    client_max_body_size 16M;

    # Flask App Principal
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    # IA Service
    location /ia/ {
        proxy_pass http://127.0.0.1:8081/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

**Salve:** `Ctrl+X`, `Y`, `Enter`

**Passo 2: Testar e Recarregar Nginx**

```bash
# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

**Passo 3: Verificar acesso HTTP (antes do SSL)**

```bash
# No seu Mac, testar acesso:
curl -I http://api.emitemax.com.br/health

# Deve retornar redirect 301 ou status 200 OK
```

### 10.4 Configurar SSL (HTTPS) com Let's Encrypt

**⚠️ IMPORTANTE:** Só faça isso **APÓS** o DNS estar propagado (nslookup funcionando)!

#### Método 1: HTTP-01 Challenge (Automático - pode não funcionar em alguns casos)

```bash
# Instalar Certbot (se ainda não instalou)
sudo apt install -y certbot python3-certbot-nginx

# Tentar obter certificado SSL via HTTP-01
sudo certbot --nginx -d api.emitemax.com.br

# Responda as perguntas:
# - Email: seu_email@exemplo.com
# - Aceitar termos: Yes
# - Compartilhar email: No (opcional)
```

**⚠️ TROUBLESHOOTING: Se aparecer erro "Timeout during connect"**

Se você receber um erro como:
```
Timeout during connect (likely firewall problem)
```

Isso significa que os servidores Let's Encrypt não conseguem conectar na porta 80 da sua instância EC2. Possíveis causas:
- Rate limiting (tentativas anteriores falharam)
- Bloqueio de rede entre Let's Encrypt e AWS
- Problema de roteamento específico

**Solução:** Use o **Método 2: DNS-01 Challenge** abaixo.

---

#### Método 2: DNS-01 Challenge (Manual - funciona 100%)

Este método usa validação via DNS e **não depende da porta 80** estar acessível.

**✅ Vantagens:**
- Funciona sempre, independente de firewall
- Não precisa de porta 80 acessível
- Certificado válido por 90 dias

**⚠️ Desvantagens:**
- Renovação manual a cada 90 dias (requer adicionar registro TXT no DNS)
- Não pode ser 100% automatizado sem API do provedor DNS

**Passo 1: Deletar certificado antigo (se existir)**

```bash
sudo certbot delete --cert-name api.emitemax.com.br
```

**Passo 2: Obter certificado via DNS-01**

```bash
sudo certbot certonly --manual --preferred-challenges dns -d api.emitemax.com.br
```

**Passo 3: Seguir instruções do Certbot**

Durante o processo, o Certbot vai mostrar uma mensagem como:

```
Please deploy a DNS TXT record under the name:
_acme-challenge.api.emitemax.com.br

with the following value:
XxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx

Before continuing, verify the record is deployed.
```

**Passo 4: Adicionar registro TXT no DNS da Hostinger**

1. Acesse: https://hpanel.hostinger.com.br/
2. **Domínios** > `emitemax.com.br` > **DNS / Name Servers**
3. Clique em **Add Record**
4. Configure:
   ```
   Type: TXT
   Name: _acme-challenge.api
   Content: [valor fornecido pelo Certbot]
   TTL: 300 (5 minutos)
   ```
5. Clique em **Add Record**

**Passo 5: Verificar propagação do DNS**

Aguarde 1-2 minutos e verifique se o registro TXT está propagado:

```bash
# No seu Mac ou no servidor:
dig _acme-challenge.api.emitemax.com.br TXT

# Deve retornar o valor que você adicionou
```

Ou use ferramentas online:
- https://toolbox.googleapps.com/apps/dig/#TXT/_acme-challenge.api.emitemax.com.br
- https://mxtoolbox.com/TXTLookup.aspx

**Passo 6: Continuar no Certbot**

Quando o DNS estiver propagado, volte ao terminal e pressione **Enter** no Certbot.

Se tudo estiver correto, você verá:

```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/api.emitemax.com.br/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/api.emitemax.com.br/privkey.pem
This certificate expires on 2026-03-30.
```

**Passo 7: Atualizar Nginx para usar o certificado**

Edite a configuração do Nginx:

```bash
sudo nano /etc/nginx/sites-available/api-nfe
```

Descomente as linhas de SSL (remova o `#`):

```nginx
ssl_certificate /etc/letsencrypt/live/api.emitemax.com.br/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/api.emitemax.com.br/privkey.pem;
```

Ou deixe o Certbot configurar automaticamente:

```bash
sudo certbot --nginx -d api.emitemax.com.br --cert-name api.emitemax.com.br
```

**Passo 8: Recarregar Nginx**

```bash
# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

---

#### Renovação do Certificado (DNS-01 Manual)

**⚠️ IMPORTANTE:** Com DNS-01 manual, você precisa renovar o certificado manualmente a cada 90 dias.

**Data de expiração:** Verifique com:
```bash
sudo certbot certificates
```

**Quando renovar:** Renove antes de 15 dias da expiração.

**Como renovar:**

1. Conectar ao servidor:
   ```bash
   ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106
   ```

2. Executar renovação:
   ```bash
   sudo certbot certonly --manual --preferred-challenges dns -d api.emitemax.com.br --force-renewal
   ```

3. Durante o processo, o Certbot vai mostrar um novo valor TXT

4. **Atualizar** (não adicionar novo) o registro TXT no DNS da Hostinger:
   - Acesse o painel da Hostinger
   - Edite o registro `_acme-challenge.api`
   - Substitua o **Content** pelo novo valor
   - Aguarde 1-2 minutos para propagação

5. Verificar propagação:
   ```bash
   dig _acme-challenge.api.emitemax.com.br TXT
   ```

6. Pressionar Enter no Certbot

7. Recarregar Nginx:
   ```bash
   sudo systemctl reload nginx
   ```

**Arquivo de lembrete salvo no servidor:**
```bash
cat /etc/letsencrypt/renewal-reminder.txt
```

---

#### Verificação Final

**Passo 1: Verificar status do certificado**

```bash
sudo certbot certificates
```

Deve mostrar:
```
Certificate Name: api.emitemax.com.br
  Domains: api.emitemax.com.br
  Expiry Date: 2026-03-30 (VALID: 89 days)
  Certificate Path: /etc/letsencrypt/live/api.emitemax.com.br/fullchain.pem
  Private Key Path: /etc/letsencrypt/live/api.emitemax.com.br/privkey.pem
```

**Passo 2: Testar HTTPS**

```bash
# No seu Mac:
curl -I https://api.emitemax.com.br/health

# Deve retornar:
# HTTP/2 200
# server: nginx/1.24.0 (Ubuntu)
```

**Ou acesse no navegador:**
- https://api.emitemax.com.br/health
- https://api.emitemax.com.br/admin

Verifique se o cadeado verde aparece na barra de endereço! 🔒✅

### 10.5 Criar Site Institucional na Hostinger

**Opção 1: Site Simples HTML (Recomendado para início)**

**Passo 1: Acessar File Manager na Hostinger**

1. Painel Hostinger > **Websites**
2. Selecione `emitemax.com.br`
3. Clique em **File Manager**
4. Navegue até a pasta `public_html/`

**Passo 2: Criar index.html**

Clique em **New File** > Nome: `index.html`

Cole o seguinte código:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmiteMax - Sistema de Emissão de NF-e</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        
        /* Header */
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 0;
            position: fixed;
            width: 100%;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        nav {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 2rem;
        }
        
        .logo {
            font-size: 1.8rem;
            font-weight: bold;
        }
        
        .nav-links {
            display: flex;
            list-style: none;
            gap: 2rem;
        }
        
        .nav-links a {
            color: white;
            text-decoration: none;
            transition: opacity 0.3s;
        }
        
        .nav-links a:hover {
            opacity: 0.8;
        }
        
        .btn-entrar {
            background: white;
            color: #667eea;
            padding: 0.6rem 1.5rem;
            border-radius: 25px;
            font-weight: bold;
            transition: transform 0.3s;
        }
        
        .btn-entrar:hover {
            transform: scale(1.05);
        }
        
        /* Hero Section */
        .hero {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 150px 2rem 100px;
            text-align: center;
        }
        
        .hero h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            animation: fadeInUp 1s;
        }
        
        .hero p {
            font-size: 1.3rem;
            margin-bottom: 2rem;
            animation: fadeInUp 1s 0.2s backwards;
        }
        
        .cta-button {
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 1rem 2.5rem;
            border-radius: 30px;
            text-decoration: none;
            font-weight: bold;
            font-size: 1.1rem;
            transition: transform 0.3s, box-shadow 0.3s;
            animation: fadeInUp 1s 0.4s backwards;
        }
        
        .cta-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        /* Features Section */
        .features {
            max-width: 1200px;
            margin: 80px auto;
            padding: 0 2rem;
        }
        
        .features h2 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 3rem;
            color: #667eea;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }
        
        .feature-card {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
        }
        
        .feature-card h3 {
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }
        
        .feature-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        /* Footer */
        footer {
            background: #2d3748;
            color: white;
            text-align: center;
            padding: 2rem;
            margin-top: 80px;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @media (max-width: 768px) {
            .hero h1 {
                font-size: 2rem;
            }
            
            .hero p {
                font-size: 1rem;
            }
            
            .nav-links {
                gap: 1rem;
            }
        }
    </style>
</head>
<body>
    <header>
        <nav>
            <div class="logo">EmiteMax</div>
            <ul class="nav-links">
                <li><a href="#inicio">Início</a></li>
                <li><a href="#recursos">Recursos</a></li>
                <li><a href="#contato">Contato</a></li>
                <li><a href="https://api.emitemax.com.br" class="btn-entrar">Entrar</a></li>
            </ul>
        </nav>
    </header>

    <section class="hero" id="inicio">
        <h1>Sistema Completo de Emissão de NF-e</h1>
        <p>Emita suas notas fiscais com inteligência artificial e agilidade</p>
        <a href="https://api.emitemax.com.br" class="cta-button">Acessar Sistema</a>
    </section>

    <section class="features" id="recursos">
        <h2>Recursos Principais</h2>
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <h3>Inteligência Artificial</h3>
                <p>Preenchimento automático de NCM e tributação com IA avançada.</p>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">📝</div>
                <h3>Emissão de NF-e</h3>
                <p>Emita suas notas fiscais eletrônicas de forma rápida e segura.</p>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">🔒</div>
                <h3>Certificado A3</h3>
                <p>Suporte completo para certificados digitais A1 e A3.</p>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <h3>Relatórios</h3>
                <p>Dashboard completo com estatísticas e relatórios gerenciais.</p>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">☁️</div>
                <h3>100% Cloud</h3>
                <p>Acesse de qualquer lugar, a qualquer momento.</p>
            </div>
            
            <div class="feature-card">
                <div class="feature-icon">💰</div>
                <h3>IBS/CBS 2025</h3>
                <p>Atualizado com as novas regras tributárias LC 214/2025.</p>
            </div>
        </div>
    </section>

    <footer id="contato">
        <p>&copy; 2026 EmiteMax - Sistema de Emissão de NF-e. Todos os direitos reservados.</p>
        <p>Contato: contato@emitemax.com.br</p>
    </footer>
</body>
</html>
```

**Salve o arquivo.**

**Passo 3: Testar o Site**

Acesse no navegador: `http://emitemax.com.br`

O botão **"Entrar"** irá redirecionar para `https://api.emitemax.com.br`

**Opção 2: WordPress na Hostinger (Alternativa)**

Se preferir usar WordPress:

1. Painel Hostinger > **Website** > **Auto Installer**
2. Selecione **WordPress**
3. Instale no domínio `emitemax.com.br`
4. Configure tema e adicione menu "Entrar" com link: `https://api.emitemax.com.br`

### 10.6 Configurar SSL na Hostinger (Site Institucional)

**Passo 1: Ativar SSL Gratuito**

1. Painel Hostinger > **Websites**
2. Selecione `emitemax.com.br`
3. Vá em **SSL** (no menu lateral)
4. Ative **Free SSL** (Let's Encrypt)
5. Aguarde 5-10 minutos para ativação

**Passo 2: Forçar HTTPS**

1. Ainda em **SSL**
2. Ative **Force HTTPS**
3. Pronto! Agora `http://emitemax.com.br` redireciona para `https://emitemax.com.br`

### 10.7 Atualizar Security Group AWS

Como agora temos um domínio, atualize o Security Group para maior segurança:

```bash
# Console AWS > EC2 > Security Groups > nfe-api-sg
```

**Regras Recomendadas (Produção):**

```yaml
# Manter apenas estas regras:

SSH (22):
  Source: SEU_IP/32 (seu IP fixo para administração)
  Description: SSH admin

HTTP (80):
  Source: 0.0.0.0/0
  Description: HTTP redirect to HTTPS

HTTPS (443):
  Source: 0.0.0.0/0
  Description: HTTPS public access

PostgreSQL (5432):
  Source: 172.30.1.214/32 (IP privado EC2)
  Description: RDS from EC2

OpenVPN (1194 UDP):
  Source: 177.189.240.158/32
  Description: VPN from local server

# REMOVER (após testar que está funcionando via HTTPS):
# - Custom TCP 8080
# - Custom TCP 8081
```

### 10.8 Atualizar Flask para Aceitar o Domínio

```bash
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106
```

```bash
nano /home/ubuntu/api_nfe/.env
```

Adicione estas linhas:

```bash
# Domain Configuration
DOMAIN=api.emitemax.com.br
ALLOWED_HOSTS=api.emitemax.com.br,emitemax.com.br,3.87.73.106
```

Reinicie o serviço:

```bash
sudo systemctl restart api-nfe-principal
sudo systemctl status api-nfe-principal
```

### 10.9 Checklist Final

Antes de colocar em produção, verifique:

- [ ] DNS propagado (`nslookup api.emitemax.com.br` retorna 3.87.73.106)
- [ ] Site institucional acessível em `https://emitemax.com.br`
- [ ] API acessível em `https://api.emitemax.com.br`
- [ ] Health check funcionando: `https://api.emitemax.com.br/health`
- [ ] Certificado SSL válido (sem warnings no navegador)
- [ ] Botão "Entrar" no site redireciona corretamente
- [ ] Login funcionando em `https://api.emitemax.com.br/login`
- [ ] VPN conectada e LM Studio acessível
- [ ] Serviços rodando: `api-nfe-principal`, `api-nfe-ia`, `openvpn-client`
- [ ] Security Groups configurados corretamente
- [ ] Backups automáticos habilitados

### 10.10 Testar Fluxo Completo

```bash
# 1. Testar site institucional
curl -I https://emitemax.com.br

# 2. Testar API
curl -I https://api.emitemax.com.br/health

# 3. Testar login (deve retornar HTML ou redirect)
curl -I https://api.emitemax.com.br/login

# 4. Verificar certificado SSL
openssl s_client -connect api.emitemax.com.br:443 -servername api.emitemax.com.br < /dev/null | grep "Verify return code"
# Deve retornar: Verify return code: 0 (ok)
```

### 10.11 URLs Finais

Após configuração completa:

- 🌐 **Site Institucional**: https://emitemax.com.br
- 🔐 **Sistema NFe (Login)**: https://api.emitemax.com.br
- 📊 **Dashboard**: https://api.emitemax.com.br/admin/dashboard
- 🤖 **IA Service Docs**: https://api.emitemax.com.br/ia/docs
- ✅ **Health Check**: https://api.emitemax.com.br/health

---

## 📝 ETAPA 11: Manutenção e Monitoramento

# Obter certificado SSL
sudo certbot --nginx -d api.minhaempresa.com.br

# Renovação automática (já configurado)
sudo systemctl status certbot.timer
```

Agora acesse: `https://api.minhaempresa.com.br`

---

## 📝 ETAPA 10: Configurar Backups Automáticos

### 10.1 Script de Backup

```bash
nano /home/ubuntu/backup-database.sh
```

```bash
#!/bin/bash

BACKUP_DIR="/home/ubuntu/api_nfe/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_HOST="nfe-database.xxxxx.us-east-1.rds.amazonaws.com"
DB_NAME="sjtnfe"
DB_USER="postgres"
PGPASSWORD="SUA_SENHA_RDS"

# Criar diretório se não existir
mkdir -p $BACKUP_DIR

# Fazer backup
export PGPASSWORD
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f "$BACKUP_DIR/backup_$DATE.dump"

# Remover backups antigos (mais de 7 dias)
find $BACKUP_DIR -name "backup_*.dump" -mtime +7 -delete

echo "Backup concluído: backup_$DATE.dump"
```

```bash
chmod +x /home/ubuntu/backup-database.sh
```

### 10.2 Configurar Cron

```bash
crontab -e
```

Adicione:

```bash
# Backup diário às 3h da manhã
0 3 * * * /home/ubuntu/backup-database.sh >> /home/ubuntu/api_nfe/logs/backup.log 2>&1
```

### 10.3 (Opcional) Enviar para S3

```bash
# Instalar AWS CLI
sudo apt install -y awscli

# Configurar credenciais
aws configure

# Modificar script para incluir upload
echo "aws s3 cp $BACKUP_DIR/backup_$DATE.dump s3://meu-bucket-nfe/backups/" >> /home/ubuntu/backup-database.sh
```

---

## 📝 ETAPA 11: Monitoramento e Logs

### 11.1 Verificar Status dos Serviços

```bash
# Status geral
sudo systemctl status api-nfe-principal
sudo systemctl status api-nfe-ia
sudo systemctl status ollama
sudo systemctl status nginx

# Logs em tempo real
sudo journalctl -f
```

### 11.2 Logs da Aplicação

```bash
# Flask App
tail -f /home/ubuntu/api_nfe/logs/access.log
tail -f /home/ubuntu/api_nfe/logs/error.log

# Nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 11.3 Monitoramento de Recursos

```bash
# CPU e memória
htop

# Espaço em disco
df -h

# Processos Python
ps aux | grep python
```

---

## 📝 ETAPA 12: Testes Finais

### 12.1 Testar Endpoints

```bash
# Health check
curl http://54.123.45.67/health

# IA Service
curl http://54.123.45.67/ia/docs

# Testar VPN
ping 10.8.0.1

# LM Studio no servidor local via VPN
curl http://10.8.0.1:1234/v1/models
```

### 12.2 Testar no Navegador

1. Acesse: `http://54.123.45.67`
2. Faça login
3. Teste criação de NFe
4. Teste sugestão tributária com IA

---

## 🔒 ETAPA 13: Segurança

### 13.1 Configurar Firewall (UFW)

```bash
# Instalar e habilitar UFW
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

### 13.2 Atualizar Security Groups

No Console AWS EC2:
1. Edite `nfe-api-sg`
2. **Remova** regras 8080, 8081 de "Anywhere"
3. **Mantenha:**
   - SSH (22): Your IP
   - HTTP (80): 0.0.0.0/0
   - HTTPS (443): 0.0.0.0/0
   - UDP (1194): IP do seu servidor OpenVPN local (para VPN)

### 13.3 Configurar Fail2Ban (proteção contra ataques)

```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 🎯 Checklist Final

- [ ] RDS PostgreSQL criado e acessível
- [ ] EC2 instância t2.small/t2.medium rodando Ubuntu
- [ ] OpenVPN Client instalado e conectado ao servidor local
- [ ] LM Studio acessível via VPN no servidor local
- [ ] Código da aplicação copiado
- [ ] Dependências Python instaladas
- [ ] Arquivo .env configurado com IP VPN
- [ ] Banco de dados migrado
- [ ] Serviços systemd criados e rodando
- [ ] Nginx configurado e rodando
- [ ] Backup automático configurado
- [ ] Testes realizados com sucesso
- [ ] Security Groups configurados corretamente
- [ ] (Opcional) Domínio configurado
- [ ] (Opcional) SSL/HTTPS configurado

---

## 📊 Monitoramento de Custos

### Estimativa Mensal (AWS)

```
EC2 t2.small:     ~$17/mês  (730 horas × $0.023/hora)
OU
EC2 t2.medium:    ~$35/mês  (730 horas × $0.047/hora)

RDS db.t3.micro:  $0/mês    (Free Tier - 750 horas)
EBS Storage:      $3/mês    (30GB × $0.10/GB)
RDS Storage:      $0/mês    (Free Tier - 20GB)
Data Transfer:    $0-5/mês  (dependendo do tráfego)
-----------------------------------------------------
TOTAL (t2.small): ~$20-25/mês
TOTAL (t2.medium):~$38-43/mês

✅ ECONOMIA: LM Studio no servidor local (sem custos AWS)
```

**⚠️ Para reduzir custos:**
- Desligue a instância quando não estiver usando
- Use Reserved Instances (desconto de até 72%)
- Configure alarmes de custo no AWS Billing

---

## 🆘 Troubleshooting

### Aplicação não inicia

```bash
# Ver logs detalhados
sudo journalctl -u api-nfe-principal -n 100

# Verificar permissões
ls -la /home/ubuntu/api_nfe

# Testar manualmente
cd /home/ubuntu/api_nfe
source venv/bin/activate
python app.py
```

### Banco não conecta

```bash
# Testar conexão
psql -h SEU_ENDPOINT_RDS -U postgres -d sjtnfe

# Verificar Security Group do RDS
# Verificar .env

# Ver logs PostgreSQL no RDS
# Console AWS > RDS > Logs
```

### Ollama não responde

```bash
# Verificar conexão VPN
sudo systemctl status openvpn-client

# Testar conectividade com servidor local
ping 10.8.0.1

# Testar LM Studio remoto
curl http://10.8.0.1:1234/v1/models

# Reiniciar VPN se necessário
sudo systemctl restart openvpn-client

# Ver logs VPN
sudo journalctl -u openvpn-client -n 50
```

### Nginx retorna 502

```bash
# Verificar se apps estão rodando
sudo systemctl status api-nfe-principal
sudo systemctl status api-nfe-ia

# Ver logs Nginx
sudo tail -f /var/log/nginx/error.log

# Testar direto (sem Nginx)
curl http://localhost:8080/health
```

---

## 📞 Comandos Úteis

```bash
# Reiniciar tudo
sudo systemctl restart api-nfe-principal api-nfe-ia openvpn-client nginx

# Ver uso de memória
free -h

# Ver uso de CPU
top

# Limpar logs antigos
sudo journalctl --vacuum-time=7d

# Atualizar código
cd /home/ubuntu/api_nfe
git pull
sudo systemctl restart api-nfe-principal api-nfe-ia
```

---

## 🎓 Próximos Passos

1. **Configurar CI/CD** (GitHub Actions)
2. **Implementar Redis** para cache
3. **CloudWatch** para monitoramento avançado
4. **Auto Scaling** para alta disponibilidade
5. **CloudFront** para CDN global

---

## 📚 Documentação de Referência

- [AWS EC2](https://docs.aws.amazon.com/ec2/)
- [AWS RDS PostgreSQL](https://docs.aws.amazon.com/rds/)
- [Nginx](https://nginx.org/en/docs/)
- [Gunicorn](https://docs.gunicorn.org/)
- [OpenVPN](https://openvpn.net/community-resources/)
- [LM Studio](https://lmstudio.ai/)
- [Let's Encrypt](https://letsencrypt.org/)

---

**🎉 Deploy Concluído!**

Seu sistema está rodando na AWS com:
- ✅ Flask App
- ✅ IA com LM Studio via VPN (servidor local)
- ✅ PostgreSQL no RDS
- ✅ OpenVPN Client conectado ao servidor local
- ✅ Backups automáticos
- ✅ HTTPS (se configurado)


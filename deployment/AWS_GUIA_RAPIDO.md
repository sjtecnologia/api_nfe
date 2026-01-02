# 🚀 Guia Rápido - Deploy AWS

## ⏱️ Tempo estimado: 2-3 horas

---

## 📋 PASSO A PASSO SIMPLIFICADO

### 1️⃣ Preparar no AWS Console (30 min)

**1.1 Criar RDS PostgreSQL:**
- Acesse: RDS → Create database
- Engine: PostgreSQL 15.x
- Template: **Free tier**
- Instance ID: `nfe-database`
- Username: `postgres`
- Password: **[ANOTE!]**
- Database name: `sjtnfe`
- Public access: **Yes**
- **Anote o Endpoint:** `nfe-database.xxxxx.us-east-1.rds.amazonaws.com`

**1.2 Criar EC2:**
- Acesse: EC2 → Launch Instance
- Name: `nfe-api-server`
- AMI: **Ubuntu Server 22.04 LTS**
- Instance Type: **t2.large** (⚠️ t2.micro não funciona para LM Studio!)
- Key pair: **Create new** → Download `.pem`
- Storage: 30 GB
- Security Group: Allow 22, 80, 443, 8080, 8081, 1234
- **Anote o IP Público:** `54.xxx.xxx.xxx`

**1.3 Ajustar Security Group do RDS:**
- EC2 → Security Groups
- Encontre `nfe-database-sg`
- Edit inbound rules → Add PostgreSQL (5432) from EC2 IP

---

### 2️⃣ Conectar na EC2 via SSH (5 min)

```bash
# No seu Mac:
chmod 400 ~/Downloads/nfe-api-key.pem
ssh -i ~/Downloads/nfe-api-key.pem ubuntu@54.xxx.xxx.xxx
```

---

### 3️⃣ Executar Setup Inicial (15 min)

**Copiar script de setup:**

```bash
# No servidor EC2:
wget https://raw.githubusercontent.com/sjtecnologia/api_nfe/main/deployment/setup_aws_inicial.sh
bash setup_aws_inicial.sh
```

**OU fazer manualmente:**

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y python3.10 python3-pip python3-venv python3-dev \
    postgresql-client build-essential libssl-dev libffi-dev git \
    libxml2-dev libxslt1-dev libpcsclite-dev pcscd nginx \
    supervisor htop curl wget unzip

# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull codellama:7b-instruct
```

---

### 4️⃣ Copiar Código da Aplicação (10 min)

**Opção A - Via SCP (do seu Mac):**

```bash
# Terminal do Mac:
cd ~/Documents/Developement
tar -czf api_nfe.tar.gz api_nfe
scp -i ~/Downloads/nfe-api-key.pem api_nfe.tar.gz ubuntu@54.xxx.xxx.xxx:/home/ubuntu/

# Terminal da EC2:
cd /home/ubuntu
tar -xzf api_nfe.tar.gz
```

**Opção B - Via Git:**

```bash
# Terminal da EC2:
cd /home/ubuntu
git clone https://github.com/sjtecnologia/api_nfe.git
```

---

### 5️⃣ Configurar Ambiente (10 min)

**Criar arquivo .env:**

```bash
cd /home/ubuntu/api_nfe
nano .env
```

**Cole e ajuste:**

```bash
FLASK_SECRET_KEY=gere_uma_chave_forte_aqui
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
PORT=8080

DATABASE_URL=postgresql://postgres:SENHA_RDS@ENDPOINT_RDS:5432/sjtnfe
DB_HOST=ENDPOINT_RDS
DB_PORT=5432
DB_NAME=sjtnfe
DB_USER=postgres
DB_PASSWORD=SENHA_RDS

UPLOAD_FOLDER=/home/ubuntu/api_nfe/uploads
BACKUP_DIR=/home/ubuntu/api_nfe/backups
BACKUP_LOG_DIR=/home/ubuntu/api_nfe/logs

LOG_LEVEL=INFO
SEFAZ_AMBIENTE_HOMOLOGACAO=True
USAR_CERTIFICADO_REAL=True
```

**Substituir:**
- `SENHA_RDS` → Senha do RDS que você anotou
- `ENDPOINT_RDS` → Endpoint do RDS que você anotou
- `gere_uma_chave_forte_aqui` → Use: `python3 -c "import secrets; print(secrets.token_hex(32))"`

---

### 6️⃣ Migrar Banco de Dados (5 min)

```bash
cd /home/ubuntu/api_nfe

# Carregar variáveis
source .env

# Importar schema
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f database/sjtnfedb.sql

# Migrar A3 (se houver)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f database/migrations/add_tipo_certificado.sql
```

---

### 7️⃣ Executar Deploy Automatizado (10 min)

```bash
cd /home/ubuntu/api_nfe/deployment
bash deploy_aws.sh
```

Este script:
- ✅ Cria virtual environment
- ✅ Instala dependências Python
- ✅ Cria diretórios necessários
- ✅ Configura serviços systemd
- ✅ Inicia aplicações

---

### 8️⃣ Configurar Nginx (5 min)

```bash
# Copiar configuração
sudo cp /home/ubuntu/api_nfe/deployment/nginx-api-nfe.conf \
        /etc/nginx/sites-available/api-nfe

# Ativar site
sudo ln -s /etc/nginx/sites-available/api-nfe \
           /etc/nginx/sites-enabled/

# Remover default
sudo rm /etc/nginx/sites-enabled/default

# Testar e reiniciar
sudo nginx -t
sudo systemctl restart nginx
```

---

### 9️⃣ Testar Sistema (5 min)

```bash
# Ver status
sudo systemctl status api-nfe-principal
sudo systemctl status api-nfe-ia
sudo systemctl status ollama
sudo systemctl status nginx

# Testar endpoints
curl http://localhost:8080/health
curl http://localhost:8081/docs
```

**No navegador:**
- Acesse: `http://54.xxx.xxx.xxx` (seu IP público)

---

### 🔟 Configurar SSL (Opcional - 10 min)

**Se você tiver domínio:**

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obter certificado (substitua o domínio)
sudo certbot --nginx -d api.seudominio.com.br

# Renovação automática já está configurada
sudo systemctl status certbot.timer
```

Agora acesse: `https://api.seudominio.com.br`

---

## ✅ CHECKLIST FINAL

- [ ] RDS PostgreSQL criado e acessível
- [ ] EC2 instância criada (t2.large)
- [ ] Conectado via SSH
- [ ] Ollama instalado e rodando
- [ ] Código copiado para EC2
- [ ] Arquivo .env configurado
- [ ] Banco de dados migrado
- [ ] Deploy executado com sucesso
- [ ] Nginx configurado
- [ ] Aplicação acessível via navegador
- [ ] (Opcional) SSL configurado

---

## 📊 VERIFICAR STATUS

```bash
# Status de todos os serviços
nfe-status  # (alias configurado)

# OU manualmente:
sudo systemctl status api-nfe-principal api-nfe-ia ollama nginx
```

---

## 📝 COMANDOS ÚTEIS

```bash
# Ver logs em tempo real
nfe-logs      # Flask App
ia-logs       # IA Service

# Reiniciar tudo
nfe-restart

# Backup manual
nfe-backup

# Atualizar código
cd /home/ubuntu/api_nfe/deployment
bash atualizar_codigo_aws.sh
```

---

## 🆘 PROBLEMAS COMUNS

### Aplicação não inicia
```bash
sudo journalctl -u api-nfe-principal -n 50
cd /home/ubuntu/api_nfe
source venv/bin/activate
python app.py  # Testar manualmente
```

### Banco não conecta
```bash
# Testar conexão
psql -h SEU_ENDPOINT -U postgres -d sjtnfe

# Verificar Security Group do RDS no AWS Console
# Verificar .env
```

### Nginx retorna 502
```bash
# Verificar se apps estão rodando
sudo systemctl status api-nfe-principal api-nfe-ia

# Testar direto (sem Nginx)
curl http://localhost:8080/health
```

---

## 💰 CUSTOS ESTIMADOS

**Free Tier (12 meses):**
- RDS db.t3.micro: **Grátis** (750h/mês)
- EC2 t2.micro: **Grátis** (750h/mês) - ⚠️ MAS não funciona para IA!

**Com t2.large para IA:**
- EC2 t2.large: ~**$65/mês** (730h × $0.09/h)
- RDS: Grátis
- Storage: ~$3/mês
- **Total: ~$68/mês**

**💡 Para economizar:**
- Desligue quando não usar
- Use Reserved Instances (desconto até 72%)
- Considere Spot Instances para desenvolvimento

---

## 🎓 PRÓXIMOS PASSOS

1. [ ] Configurar backups automáticos no S3
2. [ ] Implementar CloudWatch para monitoramento
3. [ ] Configurar Auto Scaling
4. [ ] Implementar CI/CD com GitHub Actions
5. [ ] Adicionar Redis para cache

---

## 📞 SUPORTE

- 📖 Guia completo: `AWS_DEPLOY_COMPLETO.md`
- 🔧 Scripts: `/deployment/*.sh`
- 📝 Logs: `sudo journalctl -u api-nfe-*`

---

**🎉 Pronto! Seu sistema está na AWS!**

# ✅ Checklist de Deploy AWS - API NFe

**Data:** ___/___/2025  
**Responsável:** _________________  
**Ambiente:** [ ] Produção [ ] Homologação

---

## 🎯 PRÉ-REQUISITOS

- [ ] Conta AWS criada e ativa
- [ ] Cartão de crédito cadastrado
- [ ] Acesso ao Console AWS
- [ ] Terminal/SSH configurado no Mac
- [ ] Código da aplicação atualizado

---

## 📝 ETAPA 1: AWS RDS (PostgreSQL)

- [ ] Acessar RDS no Console AWS
- [ ] Create Database
- [ ] Selecionar PostgreSQL 15.x
- [ ] Template: Free tier
- [ ] Configurações:
  - [ ] DB Instance ID: `nfe-database`
  - [ ] Master username: `postgres`
  - [ ] Master password: `________________` (ANOTAR!)
  - [ ] DB name: `sjtnfe`
  - [ ] Instance: db.t3.micro
  - [ ] Storage: 20 GB
  - [ ] Public access: Yes
- [ ] Create database (aguardar ~10 min)
- [ ] **Anotar Endpoint:** `_______________________________`

### Security Group do RDS:
- [ ] Acessar EC2 → Security Groups
- [ ] Encontrar `nfe-database-sg`
- [ ] Edit inbound rules
- [ ] Add rule: PostgreSQL (5432) from EC2 IP ou 0.0.0.0/0

---

## 📝 ETAPA 2: AWS EC2 (Servidor)

- [ ] Acessar EC2 no Console AWS
- [ ] Launch Instance
- [ ] Configurações:
  - [ ] Name: `nfe-api-server`
  - [ ] AMI: Ubuntu Server 22.04 LTS
  - [ ] Instance Type: **t2.large** (ou t3.large)
  - [ ] Key pair: Create new → `nfe-api-key` (BAIXAR!)
  - [ ] Storage: 30 GB gp3
- [ ] Security Group:
  - [ ] SSH (22): My IP
  - [ ] HTTP (80): 0.0.0.0/0
  - [ ] HTTPS (443): 0.0.0.0/0
  - [ ] Custom TCP (8080): 0.0.0.0/0
  - [ ] Custom TCP (8081): 0.0.0.0/0
  - [ ] Custom TCP (1234): 0.0.0.0/0
- [ ] Launch instance
- [ ] **Anotar IP Público:** `_________________`

---

## 📝 ETAPA 3: Conexão SSH

- [ ] Mover chave para local seguro: `mv ~/Downloads/nfe-api-key.pem ~/.ssh/`
- [ ] Ajustar permissões: `chmod 400 ~/.ssh/nfe-api-key.pem`
- [ ] Conectar: `ssh -i ~/.ssh/nfe-api-key.pem ubuntu@[IP]`
- [ ] Conexão estabelecida com sucesso

---

## 📝 ETAPA 4: Setup Inicial do Servidor

### 4.1 Sistema Base:
- [ ] Atualizar sistema: `sudo apt update && sudo apt upgrade -y`
- [ ] Instalar Python: `sudo apt install -y python3.10 python3-pip python3-venv`
- [ ] Instalar PostgreSQL client: `sudo apt install -y postgresql-client`
- [ ] Instalar dependências build: `sudo apt install -y build-essential libssl-dev libffi-dev`
- [ ] Instalar Git: `sudo apt install -y git`
- [ ] Instalar XML libs: `sudo apt install -y libxml2-dev libxslt1-dev`
- [ ] Instalar PKCS11: `sudo apt install -y libpcsclite-dev pcscd`
- [ ] Instalar Nginx: `sudo apt install -y nginx`
- [ ] Instalar Supervisor: `sudo apt install -y supervisor`
- [ ] Instalar utils: `sudo apt install -y htop curl wget unzip`

### 4.2 Ollama (IA):
- [ ] Instalar Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
- [ ] Baixar modelo: `ollama pull codellama:7b-instruct`
- [ ] Testar: `ollama run codellama:7b-instruct "Hello"`
- [ ] Verificar API: `curl http://localhost:11434/api/tags`

### 4.3 Segurança:
- [ ] Configurar UFW: `sudo ufw allow OpenSSH && sudo ufw allow 80,443/tcp && sudo ufw enable`
- [ ] Instalar Fail2Ban: `sudo apt install -y fail2ban && sudo systemctl enable fail2ban`

---

## 📝 ETAPA 5: Código da Aplicação

### Método escolhido: [ ] Git [ ] SCP

**Via Git:**
- [ ] Clonar repo: `git clone https://github.com/sjtecnologia/api_nfe.git`
- [ ] Entrar no diretório: `cd /home/ubuntu/api_nfe`

**Via SCP (do Mac):**
- [ ] Comprimir: `tar -czf api_nfe.tar.gz api_nfe`
- [ ] Enviar: `scp -i ~/.ssh/nfe-api-key.pem api_nfe.tar.gz ubuntu@[IP]:/home/ubuntu/`
- [ ] Descomprimir na EC2: `tar -xzf api_nfe.tar.gz`
- [ ] Entrar no diretório: `cd /home/ubuntu/api_nfe`

---

## 📝 ETAPA 6: Configuração

### 6.1 Virtual Environment:
- [ ] Criar venv: `python3 -m venv venv`
- [ ] Ativar: `source venv/bin/activate`
- [ ] Atualizar pip: `pip install --upgrade pip`
- [ ] Instalar dependências: `pip install -r requirements.txt`
- [ ] Instalar extras: `pip install gunicorn uvicorn python-dotenv`

### 6.2 Arquivo .env:
- [ ] Criar arquivo: `nano /home/ubuntu/api_nfe/.env`
- [ ] Configurar (ver template em `.env.template.aws`)
- [ ] Variáveis essenciais preenchidas:
  - [ ] FLASK_SECRET_KEY
  - [ ] DATABASE_URL
  - [ ] DB_HOST (endpoint RDS)
  - [ ] DB_PASSWORD (senha RDS)
- [ ] Salvar e fechar (Ctrl+O, Enter, Ctrl+X)

### 6.3 Diretórios:
- [ ] Criar uploads: `mkdir -p uploads backups logs`
- [ ] Permissões: `chmod 755 uploads backups logs`

---

## 📝 ETAPA 7: Banco de Dados

- [ ] Testar conexão: `psql -h [ENDPOINT] -U postgres -d sjtnfe`
- [ ] Importar schema: `psql -h [ENDPOINT] -U postgres -d sjtnfe -f database/sjtnfedb.sql`
- [ ] Executar migrations:
  - [ ] `psql -h [ENDPOINT] -U postgres -d sjtnfe -f database/migrations/add_tipo_certificado.sql`
- [ ] Verificar tabelas: `psql -h [ENDPOINT] -U postgres -d sjtnfe -c "\dt"`

---

## 📝 ETAPA 8: Serviços Systemd

### 8.1 Ollama Service:
- [ ] Criar arquivo: `sudo nano /etc/systemd/system/ollama.service`
- [ ] Copiar configuração (ver `setup_aws_inicial.sh`)
- [ ] Habilitar: `sudo systemctl enable ollama`
- [ ] Iniciar: `sudo systemctl start ollama`
- [ ] Verificar: `sudo systemctl status ollama`

### 8.2 Flask App Service:
- [ ] Criar arquivo: `sudo nano /etc/systemd/system/api-nfe-principal.service`
- [ ] Copiar configuração (ver `deploy_aws.sh`)
- [ ] Habilitar: `sudo systemctl enable api-nfe-principal`
- [ ] Iniciar: `sudo systemctl start api-nfe-principal`
- [ ] Verificar: `sudo systemctl status api-nfe-principal`

### 8.3 IA Service:
- [ ] Criar arquivo: `sudo nano /etc/systemd/system/api-nfe-ia.service`
- [ ] Copiar configuração (ver `deploy_aws.sh`)
- [ ] Habilitar: `sudo systemctl enable api-nfe-ia`
- [ ] Iniciar: `sudo systemctl start api-nfe-ia`
- [ ] Verificar: `sudo systemctl status api-nfe-ia`

### 8.4 Verificação:
- [ ] Todos os serviços "active (running)"
- [ ] Ver logs: `sudo journalctl -u api-nfe-principal -n 50`
- [ ] Ver logs: `sudo journalctl -u api-nfe-ia -n 50`

---

## 📝 ETAPA 9: Nginx

- [ ] Copiar config: `sudo cp deployment/nginx-api-nfe.conf /etc/nginx/sites-available/api-nfe`
- [ ] Criar link: `sudo ln -s /etc/nginx/sites-available/api-nfe /etc/nginx/sites-enabled/`
- [ ] Remover default: `sudo rm /etc/nginx/sites-enabled/default`
- [ ] Editar server_name no config (substituir IP ou domínio)
- [ ] Testar config: `sudo nginx -t`
- [ ] Reiniciar: `sudo systemctl restart nginx`
- [ ] Verificar: `sudo systemctl status nginx`

---

## 📝 ETAPA 10: Testes

### 10.1 Testes Locais (na EC2):
- [ ] Health check: `curl http://localhost:8080/health`
- [ ] IA docs: `curl http://localhost:8081/docs`
- [ ] Ollama: `curl http://localhost:11434/api/tags`
- [ ] Nginx: `curl http://localhost/health`

### 10.2 Testes Externos (do Mac):
- [ ] Browser: `http://[IP_PUBLICO]`
- [ ] Login na aplicação
- [ ] Testar funcionalidades básicas:
  - [ ] Dashboard carrega
  - [ ] Listar produtos
  - [ ] Criar produto teste
  - [ ] Testar sugestão tributária IA
  - [ ] Upload de arquivo

---

## 📝 ETAPA 11: Backups

- [ ] Criar script: `nano /home/ubuntu/backup-database.sh`
- [ ] Copiar conteúdo (ver `setup_aws_inicial.sh`)
- [ ] Tornar executável: `chmod +x /home/ubuntu/backup-database.sh`
- [ ] Testar backup: `bash /home/ubuntu/backup-database.sh`
- [ ] Verificar arquivo criado em `backups/`
- [ ] Configurar cron: `crontab -e`
- [ ] Adicionar linha: `0 3 * * * /home/ubuntu/backup-database.sh >> /home/ubuntu/api_nfe/logs/backup.log 2>&1`
- [ ] Salvar crontab

---

## 📝 ETAPA 12: Segurança Final

- [ ] Atualizar Security Group EC2:
  - [ ] Remover acesso direto 8080, 8081, 1234 de "Anywhere"
  - [ ] Manter apenas 22, 80, 443
- [ ] Verificar firewall UFW: `sudo ufw status`
- [ ] Verificar Fail2Ban: `sudo systemctl status fail2ban`
- [ ] Trocar senha padrão do usuário ubuntu (se necessário)

---

## 📝 ETAPA 13: Domínio e SSL (Opcional)

### Se tiver domínio:
- [ ] Configurar DNS (registro A apontando para IP)
- [ ] Aguardar propagação (5-30 min)
- [ ] Testar: `ping api.seudominio.com.br`
- [ ] Instalar Certbot: `sudo apt install -y certbot python3-certbot-nginx`
- [ ] Obter certificado: `sudo certbot --nginx -d api.seudominio.com.br`
- [ ] Aceitar termos
- [ ] Escolher redirect HTTP → HTTPS
- [ ] Testar: `https://api.seudominio.com.br`
- [ ] Verificar renovação automática: `sudo systemctl status certbot.timer`

---

## 📝 ETAPA 14: Monitoramento

- [ ] Configurar alertas AWS CloudWatch
- [ ] Configurar billing alerts
- [ ] Instalar monitoring tool (opcional): `htop`, `netdata`, etc.
- [ ] Documentar credenciais de acesso (em local seguro!)

---

## 📝 ETAPA 15: Documentação

- [ ] Anotar todas as credenciais:
  - [ ] IP Público EC2: `_________________`
  - [ ] Endpoint RDS: `_________________`
  - [ ] Senha RDS: `_________________`
  - [ ] Domínio (se houver): `_________________`
  - [ ] Usuário admin app: `_________________`
  - [ ] Local da chave SSH: `_________________`
- [ ] Criar documento com comandos úteis
- [ ] Compartilhar acesso com equipe (se necessário)

---

## 📝 VERIFICAÇÃO FINAL

### Status de todos os componentes:
- [ ] RDS PostgreSQL: **Disponível**
- [ ] EC2 Instância: **Rodando**
- [ ] Ollama: **Active**
- [ ] Flask App: **Active**
- [ ] IA Service: **Active**
- [ ] Nginx: **Active**
- [ ] Aplicação acessível via browser
- [ ] Testes funcionais passando
- [ ] Backups configurados
- [ ] (Opcional) SSL ativo

---

## 💰 CUSTOS

**Estimativa mensal:**
- EC2 t2.large: R$ _____ (~$65)
- RDS db.t3.micro: R$ _____ (grátis por 12 meses)
- Storage: R$ _____ (~$3)
- Outros: R$ _____
- **Total: R$ _____**

**Alarme de custo configurado:** [ ] Sim [ ] Não

---

## 📞 CONTATOS DE SUPORTE

- AWS Support: ___________________
- Equipe Dev: ___________________
- Cliente: ___________________

---

## 📝 OBSERVAÇÕES

```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

---

## ✅ APROVAÇÃO FINAL

- [ ] Deploy concluído com sucesso
- [ ] Todos os testes passando
- [ ] Cliente/Gestor notificado
- [ ] Documentação atualizada

**Assinatura:** _________________  
**Data:** ___/___/2025

---

**🎉 DEPLOY CONCLUÍDO!**

Sistema rodando em: `http://________________` ou `https://________________`

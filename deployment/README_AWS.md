# 📦 Arquivos de Deploy AWS - README

Este diretório contém todos os arquivos necessários para fazer o deploy completo do sistema API NFe na AWS.

---

## 📁 Estrutura dos Arquivos

```
deployment/
├── AWS_DEPLOY_COMPLETO.md        # Guia completo e detalhado (leia primeiro!)
├── AWS_GUIA_RAPIDO.md            # Passo a passo simplificado (2-3h)
├── CHECKLIST_DEPLOY_AWS.md       # Checklist para acompanhar deploy
├── AWS_TROUBLESHOOTING.md        # Soluções para problemas comuns
├── setup_aws_inicial.sh          # Script de setup inicial do servidor
├── deploy_aws.sh                 # Script de deploy automatizado
├── atualizar_codigo_aws.sh       # Script para atualizar código
├── nginx-api-nfe.conf            # Configuração do Nginx
└── .env.template.aws             # Template do arquivo .env
```

---

## 🚀 Por Onde Começar?

### 1️⃣ Primeira vez fazendo deploy?
**Leia:** `AWS_DEPLOY_COMPLETO.md`
- Guia completo com todas as explicações
- Ideal para entender a arquitetura
- Tempo: 3-4 horas de leitura + deploy

### 2️⃣ Quer fazer rápido?
**Use:** `AWS_GUIA_RAPIDO.md`
- Passo a passo direto ao ponto
- Com comandos prontos para copiar/colar
- Tempo: 2-3 horas

### 3️⃣ Prefere um checklist?
**Imprima:** `CHECKLIST_DEPLOY_AWS.md`
- Formato de checklist físico
- Marque cada etapa concluída
- Ótimo para não esquecer nada

### 4️⃣ Algo deu errado?
**Consulte:** `AWS_TROUBLESHOOTING.md`
- Soluções para problemas comuns
- Comandos de diagnóstico
- Dicas de performance

---

## 🎯 Fluxo Recomendado

```
1. Criar conta AWS
   ↓
2. [AWS Console] Criar RDS PostgreSQL
   ↓
3. [AWS Console] Criar EC2 (t2.large)
   ↓
4. [SSH na EC2] Executar setup_aws_inicial.sh
   ↓
5. [SSH na EC2] Copiar código (git ou scp)
   ↓
6. [SSH na EC2] Configurar .env
   ↓
7. [SSH na EC2] Migrar banco de dados
   ↓
8. [SSH na EC2] Executar deploy_aws.sh
   ↓
9. [SSH na EC2] Configurar Nginx
   ↓
10. [Browser] Testar aplicação
   ↓
11. (Opcional) Configurar domínio + SSL
```

---

## 🛠️ Scripts Disponíveis

### `setup_aws_inicial.sh`
**Quando usar:** Primeira vez, logo após criar a EC2  
**O que faz:**
- Atualiza sistema Ubuntu
- Instala Python, Nginx, PostgreSQL client
- Instala e configura Ollama
- Configura firewall UFW
- Instala Fail2Ban
- Cria script de backup
- Configura aliases úteis

**Como usar:**
```bash
# Na EC2:
wget https://raw.githubusercontent.com/sjtecnologia/api_nfe/main/deployment/setup_aws_inicial.sh
bash setup_aws_inicial.sh
```

---

### `deploy_aws.sh`
**Quando usar:** Após copiar código e configurar .env  
**O que faz:**
- Cria virtual environment
- Instala dependências Python
- Cria diretórios (uploads, backups, logs)
- Verifica conexão com banco
- Configura serviços systemd
- Inicia aplicações
- Verifica status

**Como usar:**
```bash
# Na EC2:
cd /home/ubuntu/api_nfe/deployment
bash deploy_aws.sh
```

---

### `atualizar_codigo_aws.sh`
**Quando usar:** Para atualizar código em produção  
**O que faz:**
- Backup do .env atual
- Atualiza código (git pull ou scp)
- Atualiza dependências
- Executa migrations
- Reinicia serviços
- Verifica status

**Como usar:**
```bash
# Na EC2:
cd /home/ubuntu/api_nfe/deployment
bash atualizar_codigo_aws.sh
```

---

## 📋 Templates de Configuração

### `.env.template.aws`
Template do arquivo de configuração `.env` com todas as variáveis necessárias.

**Como usar:**
```bash
# Na EC2:
cp deployment/.env.template.aws .env
nano .env
# Preencher com os valores corretos
```

**Variáveis importantes:**
- `FLASK_SECRET_KEY`: Chave secreta (gerar com `python3 -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL`: String de conexão completa do RDS
- `DB_HOST`: Endpoint do RDS
- `DB_PASSWORD`: Senha do RDS

---

### `nginx-api-nfe.conf`
Configuração completa do Nginx como reverse proxy.

**Como usar:**
```bash
# Na EC2:
sudo cp deployment/nginx-api-nfe.conf /etc/nginx/sites-available/api-nfe
sudo ln -s /etc/nginx/sites-available/api-nfe /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

**Recursos:**
- Proxy para Flask App (porta 8080)
- Proxy para IA Service (porta 8081)
- Proxy para Ollama (porta 11434)
- Servir arquivos estáticos
- Security headers
- Timeouts configurados
- Suporte para SSL (comentado)

---

## ⚙️ Configurações de Serviços

Os scripts criam automaticamente os arquivos de serviço systemd:

### Flask App: `/etc/systemd/system/api-nfe-principal.service`
- Usa Gunicorn
- 4 workers
- Porta 8080
- Timeout 300s
- Auto-restart

### IA Service: `/etc/systemd/system/api-nfe-ia.service`
- Usa Uvicorn
- 2 workers
- Porta 8081
- Auto-restart

### Ollama: `/etc/systemd/system/ollama.service`
- Serve modelo LLM
- Porta 1234 (compatível com LM Studio)
- Auto-restart

---

## 🔍 Comandos Úteis

### Ver status de tudo:
```bash
sudo systemctl status api-nfe-principal api-nfe-ia ollama nginx
```

### Ver logs em tempo real:
```bash
# Flask App
sudo journalctl -u api-nfe-principal -f

# IA Service
sudo journalctl -u api-nfe-ia -f

# Ollama
sudo journalctl -u ollama -f

# Nginx
sudo tail -f /var/log/nginx/error.log
```

### Reiniciar tudo:
```bash
sudo systemctl restart api-nfe-principal api-nfe-ia ollama nginx
```

### Fazer backup manual:
```bash
bash /home/ubuntu/backup-database.sh
```

### Ver uso de recursos:
```bash
htop
free -h
df -h
```

---

## 💰 Custos AWS

### Free Tier (12 meses):
- ✅ RDS db.t3.micro: Grátis (750h/mês)
- ❌ EC2 t2.micro: Grátis mas **insuficiente** para LM Studio
- ✅ 20GB storage RDS: Grátis
- ✅ 30GB storage EBS: ~$3/mês

### Custo Real (t2.large):
- 💰 EC2 t2.large: ~$65/mês
- ✅ RDS: Grátis (12 meses)
- 💰 Storage: ~$3/mês
- **Total: ~$68/mês**

### Para economizar:
1. **Desligar quando não usar:**
   ```bash
   # Console AWS → EC2 → Stop Instance
   ```

2. **Reserved Instances (desconto até 72%):**
   - Console AWS → EC2 → Reserved Instances

3. **Spot Instances (desconto até 90%):**
   - Para desenvolvimento/teste

4. **Configurar billing alerts:**
   - Console AWS → Billing → Budgets → Create budget

---

## 🔒 Segurança

### Checklist de Segurança:
- [ ] Senha forte no RDS
- [ ] Chave SSH protegida (chmod 400)
- [ ] Security Groups bem configurados
- [ ] UFW firewall ativo
- [ ] Fail2Ban instalado
- [ ] Apenas portas necessárias abertas
- [ ] (Opcional) SSL/HTTPS configurado
- [ ] Backups automáticos ativos
- [ ] .env NUNCA commitado no Git

### Security Groups Recomendados:

**EC2 (Produção):**
- SSH (22): Apenas seu IP
- HTTP (80): 0.0.0.0/0
- HTTPS (443): 0.0.0.0/0

**EC2 (Desenvolvimento):**
- SSH (22): Seu IP
- HTTP (80): 0.0.0.0/0
- Custom (8080, 8081, 1234): 0.0.0.0/0

**RDS:**
- PostgreSQL (5432): IP da EC2 ou Security Group da EC2

---

## 📚 Arquitetura do Sistema

```
┌─────────────────────────────────────────┐
│            Internet/Usuários            │
└────────────────┬────────────────────────┘
                 │ HTTPS (443) / HTTP (80)
                 ↓
┌─────────────────────────────────────────┐
│         Nginx Reverse Proxy             │
│  - Terminação SSL                       │
│  - Load Balancing                       │
│  - Static Files                         │
└─────┬───────────────────────────────────┘
      │
      ├─→ Flask App (8080)
      │   ├─ Routes
      │   ├─ Auth
      │   ├─ Business Logic
      │   └─ Templates
      │
      ├─→ IA Service (8081)
      │   ├─ FastAPI
      │   ├─ Sugestão Tributária
      │   └─ NCM Analysis
      │
      └─→ Ollama LLM (11434)
          ├─ CodeLlama 7B
          └─ Local Inference
          
┌─────────────────────────────────────────┐
│        PostgreSQL RDS                   │
│  - Dados NFe                            │
│  - Produtos                             │
│  - Clientes                             │
│  - Certificados                         │
└─────────────────────────────────────────┘
```

---

## 🎓 Próximos Passos Após Deploy

### Curto Prazo:
1. [ ] Configurar domínio personalizado
2. [ ] Instalar SSL (Let's Encrypt)
3. [ ] Configurar backups no S3
4. [ ] Configurar alertas CloudWatch
5. [ ] Documentar credenciais em local seguro

### Médio Prazo:
1. [ ] Implementar CI/CD (GitHub Actions)
2. [ ] Configurar monitoramento (Datadog, New Relic)
3. [ ] Implementar Redis para cache
4. [ ] Configurar CDN (CloudFront)
5. [ ] Auto Scaling

### Longo Prazo:
1. [ ] Multi-AZ deployment
2. [ ] Read replicas do RDS
3. [ ] Disaster recovery plan
4. [ ] Load testing
5. [ ] Kubernetes (EKS)

---

## 📞 Suporte

### Documentação:
- [AWS EC2](https://docs.aws.amazon.com/ec2/)
- [AWS RDS](https://docs.aws.amazon.com/rds/)
- [Nginx](https://nginx.org/en/docs/)
- [Ollama](https://ollama.ai/)
- [Gunicorn](https://docs.gunicorn.org/)

### Em caso de problemas:
1. Consultar `AWS_TROUBLESHOOTING.md`
2. Ver logs: `sudo journalctl -u api-nfe-principal -n 100`
3. Testar manualmente: `python app.py`
4. Criar issue no GitHub
5. Contatar suporte AWS (se problema de infraestrutura)

---

## 📝 Changelog

**v1.0 (Dezembro 2025)**
- Setup inicial AWS
- Guias completos de deploy
- Scripts automatizados
- Configurações de serviços
- Documentação completa

---

## ✅ Validação do Deploy

Seu deploy está completo se:
- [ ] Aplicação acessível via browser
- [ ] Login funciona
- [ ] Dashboard carrega
- [ ] Criar produto funciona
- [ ] Sugestão tributária IA funciona
- [ ] Upload de arquivos funciona
- [ ] Backup automático configurado
- [ ] Todos os serviços "active (running)"
- [ ] Logs sem erros críticos
- [ ] SSL configurado (se tiver domínio)

---

## 🎉 Conclusão

Com estes arquivos você tem tudo para:
- ✅ Deploy completo na AWS
- ✅ Sistema rodando em produção
- ✅ IA funcionando com Ollama
- ✅ Backups automáticos
- ✅ Monitoramento básico
- ✅ Segurança configurada

**Boa sorte com seu deploy! 🚀**

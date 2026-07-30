# 🔧 Troubleshooting - Deploy AWS

Guia de solução de problemas comuns durante e após o deploy na AWS.

---

## 🔴 PROBLEMA: Não consigo conectar via SSH

### Sintomas:
```
ssh: connect to host 54.xxx.xxx.xxx port 22: Connection timed out
```

### Soluções:

**1. Verificar Security Group:**
- AWS Console → EC2 → Security Groups
- Security group da instância deve permitir SSH (22) do seu IP
- Add rule: Type=SSH, Source=My IP

**2. Verificar permissões da chave:**
```bash
chmod 400 ~/.ssh/nfe-api-key.pem
```

**3. Verificar se instância está rodando:**
- Console AWS → EC2 → Instances
- Status deve ser "Running"

**4. Usar IP público correto:**
- Copiar "Public IPv4 address" da instância

**5. Verificar se sua internet está bloqueando porta 22:**
```bash
# Testar conexão
nc -zv 54.xxx.xxx.xxx 22
```

---

## 🔴 PROBLEMA: RDS não aceita conexões

### Sintomas:
```
psql: could not connect to server: Connection timed out
```

### Soluções:

**1. Verificar Security Group do RDS:**
- AWS Console → RDS → Databases → Seu banco
- VPC security groups → Click no grupo
- Inbound rules deve ter PostgreSQL (5432) permitido
- Source: IP da EC2 ou 0.0.0.0/0 (temporariamente)

**2. Verificar se "Public accessibility" está habilitado:**
- RDS → Databases → Modify
- Connectivity → Public access → Yes

**3. Testar conexão da EC2:**
```bash
# Na EC2, testar:
psql -h seu-endpoint.rds.amazonaws.com -U postgres -d sjtnfe
```

**4. Verificar endpoint correto:**
- Console → RDS → Databases → Connectivity & security
- Copiar "Endpoint" exato

---

## 🔴 PROBLEMA: Ollama não responde

### Sintomas:
```
curl: (7) Failed to connect to localhost port 11434: Connection refused
```

### Soluções:

**1. Verificar se está rodando:**
```bash
sudo systemctl status ollama
```

**2. Se não estiver rodando, iniciar:**
```bash
sudo systemctl start ollama
sudo systemctl enable ollama
```

**3. Ver logs de erro:**
```bash
sudo journalctl -u ollama -n 100
```

**4. Testar instalação:**
```bash
ollama --version
ollama list
```

**5. Reinstalar se necessário:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull codellama:7b-instruct
```

**6. Verificar portas em uso:**
```bash
sudo netstat -tulpn | grep 11434
```

---

## 🔴 PROBLEMA: Flask App não inicia

### Sintomas:
```
systemctl status api-nfe-principal
● api-nfe-principal.service - API NFe Principal
   Loaded: loaded
   Active: failed
```

### Soluções:

**1. Ver logs detalhados:**
```bash
sudo journalctl -u api-nfe-principal -n 100 --no-pager
```

**2. Verificar arquivo .env:**
```bash
cat /home/ubuntu/api_nfe/.env
# Verificar se DATABASE_URL está correto
# Verificar se FLASK_SECRET_KEY existe
```

**3. Testar manualmente:**
```bash
cd /home/ubuntu/api_nfe
source venv/bin/activate
python app.py
# Ver erro detalhado
```

**4. Verificar dependências:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**5. Verificar permissões:**
```bash
ls -la /home/ubuntu/api_nfe
# Owner deve ser ubuntu:ubuntu
sudo chown -R ubuntu:ubuntu /home/ubuntu/api_nfe
```

**6. Verificar se porta 8080 está livre:**
```bash
sudo netstat -tulpn | grep 8080
# Se ocupada, matar processo:
sudo kill -9 [PID]
```

**7. Erros comuns no log:**

**Erro: ModuleNotFoundError**
```bash
# Reinstalar dependências
source venv/bin/activate
pip install -r requirements.txt
```

**Erro: Database connection failed**
```bash
# Testar conexão manualmente
psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

**Erro: Permission denied**
```bash
# Ajustar permissões
chmod 755 /home/ubuntu/api_nfe/uploads
chmod 755 /home/ubuntu/api_nfe/logs
```

---

## 🔴 PROBLEMA: Nginx retorna 502 Bad Gateway

### Sintomas:
```
502 Bad Gateway
nginx/1.18.0
```

### Soluções:

**1. Verificar se apps estão rodando:**
```bash
sudo systemctl status api-nfe-principal
sudo systemctl status api-nfe-ia
```

**2. Testar apps diretamente (sem Nginx):**
```bash
curl http://localhost:8080/health
curl http://localhost:8081/docs
```

**3. Ver logs do Nginx:**
```bash
sudo tail -f /var/log/nginx/error.log
```

**4. Verificar configuração do Nginx:**
```bash
sudo nginx -t
```

**5. Reiniciar Nginx:**
```bash
sudo systemctl restart nginx
```

**6. Verificar proxy_pass no config:**
```bash
sudo nano /etc/nginx/sites-available/api-nfe
# Confirmar: proxy_pass http://127.0.0.1:8080;
```

---

## 🔴 PROBLEMA: IA Service retorna erro 500

### Sintomas:
```
{"detail": "Internal Server Error"}
```

### Soluções:

**1. Ver logs do serviço:**
```bash
sudo journalctl -u api-nfe-ia -n 100
```

**2. Verificar se Ollama está acessível:**
```bash
curl http://localhost:11434/api/tags
```

**3. Testar endpoint manualmente:**
```bash
curl -X POST http://localhost:8081/sugestao \
  -H "Content-Type: application/json" \
  -d '{"descricao": "Caneta azul", "tipo_item": "produto", "cliente_id": 1}'
```

**4. Verificar URL do LLM no código:**
```bash
grep -r "llm_url" /home/ubuntu/api_nfe/ia_service/
# Deve ser: http://localhost:11434/v1/chat/completions
```

**5. Timeout muito curto:**
```bash
# Aumentar timeout no ia_service/main.py
# timeout=120 ao invés de timeout=60
```

---

## 🔴 PROBLEMA: Aplicação lenta / Alto uso de CPU

### Sintomas:
- Páginas demoram a carregar
- CPU > 80%
- Memória > 80%

### Soluções:

**1. Verificar recursos:**
```bash
htop  # ou top
free -h
df -h
```

**2. Ver processos que consomem mais:**
```bash
ps aux --sort=-%cpu | head -10
ps aux --sort=-%mem | head -10
```

**3. Se Ollama está consumindo muito:**
```bash
# Reduzir workers do Ollama
# Ou usar modelo menor
ollama pull codellama:7b-instruct  # ao invés de 13b
```

**4. Se Gunicorn está consumindo muito:**
```bash
# Reduzir workers no systemd
sudo nano /etc/systemd/system/api-nfe-principal.service
# Alterar --workers 4 para --workers 2
sudo systemctl daemon-reload
sudo systemctl restart api-nfe-principal
```

**5. Limpar logs antigos:**
```bash
sudo journalctl --vacuum-time=7d
```

**6. Considerar upgrade da instância:**
- t2.large → t2.xlarge (4 vCPUs, 16GB RAM)

---

## 🔴 PROBLEMA: Banco de dados cheio

### Sintomas:
```
ERROR: could not extend file: No space left on device
```

### Soluções:

**1. Verificar espaço no RDS:**
- Console AWS → RDS → Databases
- Ver "Storage"
- Se >80%, aumentar storage

**2. Limpar dados antigos:**
```bash
# Conectar no banco
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

-- Ver tabelas maiores
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Limpar logs antigos (exemplo)
DELETE FROM logs WHERE created_at < NOW() - INTERVAL '30 days';

-- Vacuum
VACUUM FULL;
```

---

## 🔴 PROBLEMA: SSL/HTTPS não funciona

### Sintomas:
```
ERR_SSL_PROTOCOL_ERROR
```

### Soluções:

**1. Verificar se Certbot instalou corretamente:**
```bash
sudo certbot certificates
```

**2. Verificar configuração Nginx:**
```bash
sudo nginx -t
cat /etc/nginx/sites-available/api-nfe | grep ssl
```

**3. Verificar DNS:**
```bash
nslookup api.seudominio.com.br
# Deve apontar para IP da EC2
```

**4. Verificar portas abertas:**
```bash
sudo ufw status
# Deve permitir 443
```

**5. Renovar certificado manualmente:**
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

---

## 🔴 PROBLEMA: Custo AWS muito alto

### Sintomas:
- Billing Alert recebido
- Custo acima do esperado

### Soluções:

**1. Verificar billing:**
- Console AWS → Billing Dashboard
- Ver "Top Free Tier Services by Usage"

**2. Parar instâncias quando não usar:**
```bash
# Via Console: EC2 → Instance → Stop
# Ou via CLI:
aws ec2 stop-instances --instance-ids i-xxxxxxxxx
```

**3. Usar Reserved Instances:**
- Desconto de até 72%
- AWS → EC2 → Reserved Instances

**4. Verificar Snapshots e Backups:**
- Console → EC2 → Snapshots
- Deletar snapshots antigos

**5. Configurar Auto Scaling:**
- Desligar automaticamente em horários sem uso

**6. Monitorar Data Transfer:**
- Billing → Cost Explorer
- Filtrar por "Data Transfer"

---

## 🔴 PROBLEMA: Backup falha

### Sintomas:
```
pg_dump: error: connection failed
```

### Soluções:

**1. Verificar script de backup:**
```bash
cat /home/ubuntu/backup-database.sh
```

**2. Executar manualmente e ver erro:**
```bash
bash -x /home/ubuntu/backup-database.sh
```

**3. Verificar variáveis de ambiente:**
```bash
source /home/ubuntu/api_nfe/.env
echo $DB_HOST
echo $DB_NAME
```

**4. Testar conexão:**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1"
```

**5. Verificar espaço em disco:**
```bash
df -h /home/ubuntu/api_nfe/backups
```

**6. Ver cron log:**
```bash
cat /home/ubuntu/api_nfe/logs/backup.log
```

---

## 📞 COMANDOS DE DIAGNÓSTICO

### Verificar tudo de uma vez:
```bash
#!/bin/bash
echo "=== STATUS DOS SERVIÇOS ==="
sudo systemctl status api-nfe-principal --no-pager -l | head -20
sudo systemctl status api-nfe-ia --no-pager -l | head -20
sudo systemctl status ollama --no-pager -l | head -20
sudo systemctl status nginx --no-pager -l | head -20

echo -e "\n=== PORTAS EM USO ==="
sudo netstat -tulpn | grep -E '8080|8081|11434|80|443'

echo -e "\n=== USO DE RECURSOS ==="
free -h
df -h

echo -e "\n=== PROCESSOS PYTHON ==="
ps aux | grep python

echo -e "\n=== ÚLTIMOS LOGS (Flask) ==="
sudo journalctl -u api-nfe-principal -n 10 --no-pager

echo -e "\n=== ÚLTIMOS LOGS (IA) ==="
sudo journalctl -u api-nfe-ia -n 10 --no-pager
```

Salve como `diagnostico.sh`, torne executável e rode:
```bash
chmod +x diagnostico.sh
./diagnostico.sh
```

---

## 📚 RECURSOS ADICIONAIS

- **Logs AWS RDS:** Console → RDS → Logs
- **CloudWatch Logs:** Console → CloudWatch → Log groups
- **AWS Support:** https://console.aws.amazon.com/support/
- **Documentação Ollama:** https://ollama.ai/
- **Nginx Docs:** https://nginx.org/en/docs/

---

## 🆘 SUPORTE EMERGENCIAL

Se nada funcionar:

**1. Fazer snapshot/backup:**
```bash
# Backup banco
bash /home/ubuntu/backup-database.sh

# Backup código
tar -czf /home/ubuntu/api_nfe_backup_$(date +%Y%m%d).tar.gz /home/ubuntu/api_nfe
```

**2. Criar nova instância do zero:**
- Seguir guia AWS_GUIA_RAPIDO.md
- Restaurar backup do banco
- Copiar código

**3. Verificar AWS Service Health:**
- https://status.aws.amazon.com/

---

**💡 Dica:** Sempre ver os logs primeiro com `journalctl` ou nos arquivos de log!

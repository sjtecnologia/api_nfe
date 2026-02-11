# 🚨 Incidente: API Fora do Ar - Mudança de IP Público

**Data:** 11/02/2026  
**Horário:** ~08:43 BRT  
**Duração:** Indeterminada (desde o reboot da instância)  
**Severidade:** 🔴 CRÍTICA - API completamente inacessível externamente

---

## 📋 Resumo Executivo

A API https://api.emitemax.com.br ficou inacessível devido a **mudança do IP público** da instância EC2. A instância não possui Elastic IP configurado, resultando em novo endereço após reinicialização.

---

## 🔍 Diagnóstico

### Sintomas Reportados
```
ERR_INTERNET_DISCONNECTED
Timeout: https://api.emitemax.com.br/
```

### Causa Raiz
**Instância EC2 sem Elastic IP** → IP público muda a cada reinício

### IPs
- **IP Antigo:** 3.87.73.106 ❌
- **IP Novo:** 34.203.236.152 ✅
- **DNS:** Ainda aponta para IP antigo

---

## ✅ Status dos Serviços (Verificado 08:43)

### Servidor EC2 (i-0213ce1ecb50e0bf3)
```
Estado: Running
Uptime: ~9 minutos (desde 08:34:20)
```

### api-nfe-principal
```
Status: ✅ Active (running)
Porta: 8080
Workers: 4 (Gunicorn)
Health: {"status":"UP"}
```

### nginx
```
Status: ✅ Active (running)
Configuração: /etc/nginx/sites-available/api-nfe
SSL: Let's Encrypt válido
Proxy: Cloudflare detectado
```

### Teste Local (no servidor)
```bash
curl http://localhost:8080/health
# {"status":"UP","timestamp":"2026-02-11T08:43:55.636082"}
```

### Teste Externo (novo IP)
```bash
curl http://34.203.236.152/
# 301 Moved Permanently (redireciona HTTPS) ✅
```

---

## 🔧 Solução Aplicada

### 1. Documentação Atualizada
- ✅ `memory/CONTEXTO_SISTEMA.md` com Elastic IP permanente
- ✅ `memory/INCIDENTE_IP_MUDOU_11FEB2026.md` atualizado

### 2. Elastic IP Configurado ✅
- **Elastic IP:** 100.26.12.107
- **Allocation ID:** eipalloc-0596db42f622a3ddc
- **Association ID:** eipassoc-0aefb5909c05085d0
- **Instância:** i-0213ce1ecb50e0bf3
- **Status:** ✅ Associado e funcionando
- **DNS:** ec2-100-26-12-107.compute-1.amazonaws.com
- **Teste SSH:** ✅ OK
- **Teste Health:** ✅ `{"status":"UP"}`
- **Teste HTTP:** ✅ nginx respondendo (301 → HTTPS)

### 3. Ações Pendentes (Usuário)

#### ÚLTIMA ETAPA (URGENTE)
- [ ] Atualizar DNS no Cloudflare:
  - Registro A: api.emitemax.com.br
  - De: 3.87.73.106 → Para: **100.26.12.107** (Elastic IP)

---

## 📊 Timeline

| Horário | Evento |
|---------|--------|
| ~08:34 | Instância EC2 iniciada (IP temporário: 34.203.236.152) |
| 08:34:19 | nginx started |
| 08:34:20 | api-nfe-principal started |
| ~08:43 | Usuário reporta API fora do ar |
| 08:43 | Diagnóstico iniciado |
| 08:43 | Causa identificada (IP mudou de 3.87.73.106 → 34.203.236.152) |
| 08:44 | Documentação atualizada |
| 08:48 | **Elastic IP alocado e associado: 100.26.12.107** ✅ |
| 08:50 | Testes confirmam Elastic IP funcionando ✅ |
| 08:51 | Documentação atualizada com IP permanente ✅ |

---

## 🎓 Lições Aprendidas

### Problema
Instância EC2 sem Elastic IP perde o endereço público a cada reinício.

### Impacto
- ⏱️ Downtime completo até atualizar DNS
- 🔄 Necessidade de atualizar DNS manualmente
- 📞 Usuários não conseguem acessar API

### Prevenção
1. **Elastic IP obrigatório** para servidores de produção
2. **Monitoramento** de mudanças de IP
3. **Alertas** de downtime (Cloudflare/UptimeRobot)
4. **Documentação** do processo de recuperação

---

## 🔗 Configuração Atual

### DNS (Cloudflare)
```
api.emitemax.com.br → 3.87.73.106 ❌ (desatualizado)
```

### Nginx
```
server_name: api.emitemax.com.br
SSL: Let's Encrypt
Backend: 127.0.0.1:8080 (Flask)
IA Service: 127.0.0.1:8081
```

### Cloudflare
- Proxy ativado (orange cloud)
- Real IP restoration configurada
- HTTPS/SSL: Full

---

## 📝 Comandos Úteis

### Verificar IP Público da Instância
```bash
# Via AWS CLI
aws ec2 describe-instances \
  --instance-ids i-0213ce1ecb50e0bf3 \
  --query 'Reservations[0].Instances[0].PublicIpAddress'

# No servidor
curl -s ifconfig.me
```

### Testar Serviços
```bash
# SSH
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@34.203.236.152

# Status
sudo systemctl status api-nfe-principal nginx

# Health check local
curl http://localhost:8080/health
```

### Verificar DNS
```bash
# Resolução atual
nslookup api.emitemax.com.br

# Esperado após fix
dig api.emitemax.com.br +short
# 34.203.236.152 (ou Elastic IP futuro)
```

---

## ⚠️ Recomendações Críticas

### URGENTE (Hoje)
1. ✅ Atualizar DNS no Cloudflare
2. ⏱️ Aguardar propagação (1-5min)
3. ✅ Testar `curl https://api.emitemax.com.br/health`

### IMPORTANTE (Esta Semana)
1. 📌 Alocar Elastic IP na AWS
2. 🔗 Associar à instância i-0213ce1ecb50e0bf3
3. 📝 Atualizar DNS com Elastic IP
4. 📋 Documentar novo IP fixo

### BONUS
1. 📊 Configurar monitoramento (UptimeRobot)
2. 🔔 Alertas de downtime
3. 📖 Runbook de recuperação
4. 🔄 Backup e disaster recovery

---

## 📚 Referências

- AWS Documentation: [Elastic IP Addresses](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html)
- Cloudflare Docs: [Managing DNS records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/)
- `memory/CONTEXTO_SISTEMA.md` - Infraestrutura atualizada

---

**Status:** � Elastic IP Configurado | 🟡 Aguardando DNS  
**Elastic IP:** 100.26.12.107 (eipalloc-0596db42f622a3ddc) ✅  
**Próxima ação:** Atualizar Cloudflare DNS  
**Responsável:** Usuário (Renato)

---

*Documentado em 11/02/2026 09:00 BRT*

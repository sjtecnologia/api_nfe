# 🚀 Guia Rápido: Atualizar Servidor AWS

**Data:** 30 de dezembro de 2025  
**Objetivo:** Atualizar configuração do LM Studio para usar IP público ao invés de VPN

---

## 📋 Pré-requisitos

- [ ] LM Studio rodando em 192.168.0.52:1234
- [ ] Port forwarding configurado no roteador ASUS (porta 1234 → 192.168.0.52:1234)
- [ ] IP público anotado (descubra em: https://www.whatismyip.com/)

---

## 🔧 Passo 1: Transferir arquivo main.py atualizado

**No seu Mac (terminal local, NÃO no SSH):**

```bash
# Navegar para o diretório do projeto
cd /Users/renato/Documents/Developement/api_nfe

# Transferir arquivo para AWS
scp -i ~/Downloads/nfe-new-api-key.pem \
  ia_service/main.py \
  ubuntu@3.87.73.106:/tmp/main.py
```

---

## 📝 Passo 2: Atualizar arquivo no servidor

**SSH na AWS:**

```bash
# Conectar na AWS
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106

# Mover arquivo para o local correto
sudo mv /tmp/main.py /home/ubuntu/api_nfe/ia_service/main.py

# Corrigir permissões
sudo chown ubuntu:ubuntu /home/ubuntu/api_nfe/ia_service/main.py

# Editar para adicionar SEU IP PÚBLICO
nano /home/ubuntu/api_nfe/ia_service/main.py
```

---

## 🔍 Passo 3: Configurar IP Público no código

**No editor nano, procure a linha 119:**

```python
# ANTES (IP local da rede):
llm_url = "http://192.168.0.52:1234/v1/chat/completions"

# DEPOIS (seu IP público):
llm_url = "http://SEU_IP_PUBLICO:1234/v1/chat/completions"
# Exemplo: llm_url = "http://200.150.100.50:1234/v1/chat/completions"
```

**Salvar:** `Ctrl+X`, `Y`, `Enter`

---

## ♻️ Passo 4: Reiniciar serviço

```bash
# Reiniciar serviço de IA
sudo systemctl restart api-nfe-ia

# Verificar status
sudo systemctl status api-nfe-ia

# Ver logs
sudo journalctl -u api-nfe-ia -n 50 --no-pager
```

---

## ✅ Passo 5: Testar conectividade

```bash
# Testar se AWS consegue acessar LM Studio
curl -s http://SEU_IP_PUBLICO:1234/v1/models | jq '.'

# Deve retornar JSON com os modelos disponíveis
```

---

## 🐛 Troubleshooting

### Erro: "Connection refused"

1. **Verificar port forwarding no roteador:**
   - Acesse o roteador ASUS
   - WAN > Virtual Server / Port Forwarding
   - Regra: 1234 → 192.168.0.52:1234 (TCP)

2. **Testar do Windows local:**
   ```powershell
   # No PowerShell do Windows
   Invoke-WebRequest -Uri http://SEU_IP_PUBLICO:1234/v1/models
   ```

3. **Verificar firewall do Windows:**
   - Regra "LM Studio Server" deve estar habilitada
   - Porta 1234 TCP permitida

### Erro: "Timeout"

1. **Verificar se IP público mudou:**
   ```bash
   curl https://checkip.amazonaws.com
   ```

2. **Verificar se LM Studio está rodando:**
   - No Windows, abra LM Studio
   - Local Server deve estar em "Server is running"
   - Network Settings: 0.0.0.0:1234

---

## 📌 Comandos úteis

```bash
# Ver logs do serviço IA
sudo journalctl -u api-nfe-ia -f

# Ver logs do serviço Flask
sudo journalctl -u api-nfe-principal -f

# Reiniciar ambos os serviços
sudo systemctl restart api-nfe-ia api-nfe-principal

# Verificar status
sudo systemctl status api-nfe-ia api-nfe-principal
```

---

## ✅ Checklist Final

- [ ] Arquivo main.py transferido para AWS
- [ ] IP público configurado na linha 119 do main.py
- [ ] Serviço api-nfe-ia reiniciado
- [ ] Teste de conectividade funcionando
- [ ] Logs do serviço sem erros
- [ ] Teste de classificação fiscal funcionando na aplicação

# 🔧 Configurar LM Studio para Aceitar Conexões VPN

## Problema Identificado

O LM Studio está ouvindo apenas em `172.21.208.1:1234` (IP da rede local Windows).

A AWS via VPN precisa acessar através de `10.8.0.1:1234` (IP da interface VPN do servidor).

---

## ✅ Solução: Fazer LM Studio Ouvir em Todas as Interfaces

### Opção 1: Configurar no LM Studio (Recomendado)

Infelizmente, o LM Studio pode ter limitações para especificar o bind address. Vamos tentar forçar via configuração avançada.

### Opção 2: Port Forwarding Local (Solução Alternativa)

No servidor Windows, execute este comando no **PowerShell como Administrador**:

```powershell
# Criar port forwarding da interface VPN para a interface local
netsh interface portproxy add v4tov4 listenport=1234 listenaddress=10.8.0.1 connectport=1234 connectaddress=172.21.208.1
```

**Verificar se foi criado:**

```powershell
netsh interface portproxy show all
```

Deve mostrar:
```
Listen on ipv4:             Connect to ipv4:
Address         Port        Address         Port
--------------- ----------  --------------- ----------
10.8.0.1        1234        172.21.208.1    1234
```

### Opção 3: Reiniciar LM Studio com Variável de Ambiente

Feche o LM Studio completamente e inicie via PowerShell:

```powershell
# Definir variável para forçar bind em todas interfaces
$env:LM_STUDIO_HOST = "0.0.0.0"

# Iniciar LM Studio (ajuste o caminho se necessário)
Start-Process "C:\Users\SEU_USUARIO\AppData\Local\Programs\LMStudio\LM Studio.exe"
```

---

## 🧪 Testar Conectividade

### 1. No Servidor Windows (PowerShell)

```powershell
# Verificar se está ouvindo na interface VPN
netstat -an | findstr :1234

# Deve mostrar algo como:
# TCP    0.0.0.0:1234           0.0.0.0:0              LISTENING
# ou
# TCP    10.8.0.1:1234          0.0.0.0:0              LISTENING
```

### 2. Testar Localmente na Interface VPN

```powershell
# Descobrir IP VPN do servidor
ipconfig | findstr "10.8.0"

# Testar se responde no IP VPN
Invoke-WebRequest -Uri http://10.8.0.1:1234/v1/models
```

### 3. Testar da AWS (via SSH)

```bash
# Na instância EC2
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106

# Testar acesso ao LM Studio via VPN
curl -s http://10.8.0.1:1234/v1/models | jq '.'
```

---

## 🔥 Configurar Firewall do Windows

Certifique-se de que o firewall permite conexões na interface VPN:

### 1. Abrir Firewall

```
Win + R → wf.msc → Enter
```

### 2. Criar Regra de Entrada

1. **Regras de Entrada** → **Nova Regra...**
2. **Tipo:** Porta
3. **Protocolo:** TCP
4. **Porta:** 1234
5. **Ação:** Permitir a conexão
6. **Perfil:** Marque todos (Domínio, Privado, Público)
7. **Nome:** `LM Studio - VPN Access`

### 3. Verificar Interface VPN na Regra

1. Clique com botão direito na regra criada → **Propriedades**
2. Aba **Avançado**
3. Em **Interface types** → Clique em **Customize...**
4. **Marque:** "Todos os tipos de interface" ou especificamente a interface VPN

---

## 🔍 Diagnóstico: Descobrir qual Interface o LM Studio está Ouvindo

### PowerShell

```powershell
# Ver todas as conexões TCP na porta 1234
Get-NetTCPConnection -LocalPort 1234 | Format-Table -Property LocalAddress, LocalPort, State

# Ver processo que está usando a porta
Get-Process -Id (Get-NetTCPConnection -LocalPort 1234).OwningProcess
```

### netstat Detalhado

```powershell
netstat -ano | findstr :1234
```

Saída esperada:
```
TCP    0.0.0.0:1234       0.0.0.0:0        LISTENING    12345
```

Se mostrar apenas:
```
TCP    172.21.208.1:1234  0.0.0.0:0        LISTENING    12345
```

Significa que está ouvindo apenas na interface local, não na VPN.

---

## ✅ Solução Final Recomendada

**Use a Opção 2 (Port Forwarding)** - É a mais confiável:

```powershell
# PowerShell como Administrador
netsh interface portproxy add v4tov4 listenport=1234 listenaddress=10.8.0.1 connectport=1234 connectaddress=172.21.208.1

# Verificar
netsh interface portproxy show all

# Testar
Invoke-WebRequest -Uri http://10.8.0.1:1234/v1/models
```

**Para remover o port forwarding (se necessário):**

```powershell
netsh interface portproxy delete v4tov4 listenport=1234 listenaddress=10.8.0.1
```

---

## 📝 Persistir Configuração (Port Forwarding sobrevive a reinicializações)

O `netsh interface portproxy` é persistente e sobrevive a reinicializações do Windows.

**Para tornar permanente:**

1. Execute o comando de port forwarding
2. Verifique com `netsh interface portproxy show all`
3. O forwarding permanecerá ativo mesmo após reboot

---

## 🚀 Checklist Final

- [ ] LM Studio rodando e servidor iniciado
- [ ] Modelo carregado (ex: codellama-7b-instruct)
- [ ] Port forwarding criado (`netsh interface portproxy`)
- [ ] Firewall configurado para permitir porta 1234
- [ ] Testado localmente: `Invoke-WebRequest http://10.8.0.1:1234/v1/models`
- [ ] Testado da AWS: `curl http://10.8.0.1:1234/v1/models`
- [ ] Serviço de IA na AWS reiniciado

---

## 📞 Suporte

Se ainda não funcionar após estas etapas, forneça:

1. Saída de: `netstat -ano | findstr :1234`
2. Saída de: `ipconfig | findstr "10.8.0"`
3. Saída de: `netsh interface portproxy show all`
4. Screenshot das configurações do LM Studio

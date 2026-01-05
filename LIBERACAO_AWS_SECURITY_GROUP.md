# 🔓 COMO LIBERAR ACESSO EXTERNO NO AWS SECURITY GROUP

## 🚨 PROBLEMA IDENTIFICADO

O sistema está **100% funcional** no servidor, mas o **AWS Security Group está bloqueando** conexões externas (4G, redes que não sejam 177.189.240.158).

## ✅ CONFIRMAÇÕES

- ✅ Servidor funcionando (portas 80, 443, 8080 abertas localmente)
- ✅ Nginx configurado corretamente
- ✅ CORS configurado
- ✅ Certificado SSL válido até 30/03/2026
- ✅ Aplicação respondendo normalmente
- ⚠️ **AWS Security Group bloqueando IPs externos**

## 📋 PASSO A PASSO PARA LIBERAR

### 1️⃣ Acesse o Console AWS

1. Acesse: https://console.aws.amazon.com/
2. Faça login com suas credenciais
3. Certifique-se de estar na região correta (us-east-1 provavelmente)

### 2️⃣ Navegue até EC2

1. No menu superior, busque por **"EC2"**
2. Clique em **"EC2"** para abrir o painel

### 3️⃣ Encontre sua Instância

1. No menu lateral esquerdo, clique em **"Instances"**
2. Encontre a instância com IP **3.87.73.106**
3. Clique nela para selecioná-la

### 4️⃣ Acesse o Security Group

1. Na aba **"Security"** (abaixo dos detalhes da instância)
2. Clique no nome do **Security Group** (algo como "sg-xxxxx")
3. Isso abrirá a página de detalhes do Security Group

### 5️⃣ Edite as Regras de Entrada (Inbound Rules)

1. Clique na aba **"Inbound rules"**
2. Clique no botão **"Edit inbound rules"**
3. Verifique as regras atuais

### 6️⃣ Configure as Regras Corretas

**REGRAS NECESSÁRIAS:**

| Type  | Protocol | Port Range | Source       | Description            |
|-------|----------|------------|--------------|------------------------|
| HTTP  | TCP      | 80         | 0.0.0.0/0    | Permitir HTTP (todos)  |
| HTTP  | TCP      | 80         | ::/0         | Permitir HTTP (IPv6)   |
| HTTPS | TCP      | 443        | 0.0.0.0/0    | Permitir HTTPS (todos) |
| HTTPS | TCP      | 443        | ::/0         | Permitir HTTPS (IPv6)  |
| SSH   | TCP      | 22         | 177.189.240.158/32 | SSH apenas da empresa |

**IMPORTANTE:**
- `0.0.0.0/0` = Qualquer IP IPv4 (necessário para acesso público)
- `::/0` = Qualquer IP IPv6 (necessário para redes IPv6)
- `177.189.240.158/32` = Apenas seu IP da empresa (para SSH)

### 7️⃣ Adicionar/Modificar Regras

**Se as regras HTTP/HTTPS estão restritas a um IP específico:**

1. **Opção A - RECOMENDADA (Mais Segura):**
   - Clique em **"Add rule"**
   - Type: **HTTP**, Port: **80**, Source: **0.0.0.0/0**, Description: **"Acesso público HTTP"**
   - Clique em **"Add rule"** novamente
   - Type: **HTTPS**, Port: **443**, Source: **0.0.0.0/0**, Description: **"Acesso público HTTPS"**

2. **Opção B - Editar regras existentes:**
   - Encontre a regra de HTTP (porta 80)
   - Clique no "X" do Source atual
   - Digite: **0.0.0.0/0** e aperte Enter
   - Repita para HTTPS (porta 443)

### 8️⃣ Salvar Alterações

1. Revise as regras
2. Clique em **"Save rules"** (botão laranja no canto inferior direito)
3. Aguarde a confirmação (aparecerá uma mensagem verde de sucesso)

### 9️⃣ Testar

**Imediatamente após salvar:**

1. Abra o Safari no iPhone (4G, sem WiFi)
2. Acesse: **https://api.emitemax.com.br/diagnostico**
3. A página deve carregar completamente
4. Todos os testes devem aparecer com ✅ verde

## 🔍 VERIFICAÇÃO VISUAL

**Antes (BLOQUEADO):**
```
HTTP  | TCP | 80  | 177.189.240.158/32 | Apenas empresa
HTTPS | TCP | 443 | 177.189.240.158/32 | Apenas empresa
SSH   | TCP | 22  | 177.189.240.158/32 | Apenas empresa
```

**Depois (LIBERADO):**
```
HTTP  | TCP | 80  | 0.0.0.0/0          | Acesso público
HTTP  | TCP | 80  | ::/0               | Acesso público IPv6
HTTPS | TCP | 443 | 0.0.0.0/0          | Acesso público
HTTPS | TCP | 443 | ::/0               | Acesso público IPv6
SSH   | TCP | 22  | 177.189.240.158/32 | Apenas empresa (segurança)
```

## ⚠️ SEGURANÇA

**Mantenha estas práticas:**
- ✅ **SSH (porta 22)** SEMPRE restrito ao IP da empresa
- ✅ **HTTP/HTTPS (80/443)** liberados para todos (necessário para site público)
- ✅ **Porta 8080** NÃO deve estar exposta externamente (apenas localhost)
- ✅ **Porta 8081** NÃO deve estar exposta externamente (apenas localhost)

## 🎯 RESULTADO ESPERADO

Após liberar no Security Group:
- ✅ Site acessível de **qualquer rede** (4G, WiFi, qualquer operadora)
- ✅ Site acessível de **qualquer país**
- ✅ Site acessível de **qualquer dispositivo** (iPhone, Android, PC, Mac)
- ✅ SSH continua protegido (apenas rede da empresa)

## 📱 TESTE FINAL

**Do iPhone (4G):**
1. Safari → https://api.emitemax.com.br
2. Deve redirecionar para /auth/login
3. Página de login deve carregar completamente
4. Deve conseguir fazer login normalmente

## 🆘 PROBLEMAS COMUNS

### "Não vejo opção para editar regras"
- Verifique se você tem permissões de administrador na AWS
- Verifique se está na conta/organização correta

### "Salvei mas ainda não acessa"
- Aguarde 30 segundos para propagação
- Limpe cache do Safari: Ajustes → Safari → Limpar Histórico e Dados
- Teste no modo anônimo do Safari
- Tente desligar e ligar o 4G

### "Tenho medo de deixar aberto"
- HTTP/HTTPS liberados são **PADRÃO** para qualquer site público
- A segurança está nas camadas de autenticação (login/senha)
- CORS, SSL, Flask-Login já protegem a aplicação
- O importante é manter SSH (porta 22) restrito

## 📞 CONTATO

Se precisar de ajuda para acessar o console AWS ou não tiver permissões:
- Entre em contato com o responsável pela conta AWS
- Solicite permissões de "EC2 Security Group Management"

---

**RESUMO:** O servidor está perfeito. O problema é 100% no AWS Security Group bloqueando IPs externos. Basta liberar portas 80 e 443 para 0.0.0.0/0 no console AWS.

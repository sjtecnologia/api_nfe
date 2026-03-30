# 🎯 SETUP INICIAL AWS - GUIA PRÁTICO PASSO A PASSO
## EmiteMax NFe - Configuração Completa para Iniciantes

**Data:** 15 de dezembro de 2025  
**Tempo estimado:** 2-3 horas  
**Nível:** Iniciante a Intermediário

---

## 📋 PRÉ-REQUISITOS

Antes de começar, tenha em mãos:

- [ ] **Email válido** (será o login da AWS)
- [ ] **Cartão de crédito internacional** (necessário para validação)
- [ ] **Telefone celular** (para verificação 2FA)
- [ ] **CPF ou CNPJ** (para cadastro)
- [ ] **Endereço completo** (para faturamento)

---

## PARTE 1: CRIAR CONTA AWS (15 minutos)

### PASSO 1.1: Acessar Site da AWS

1. Abra o navegador e vá para: **https://aws.amazon.com/pt/**
2. Clique em **"Criar uma conta da AWS"** (botão laranja no canto superior direito)

### PASSO 1.2: Preencher Informações da Conta

**Tela 1 - Informações de Contato:**

```
📧 Endereço de email: seu@email.com
🏢 Nome da conta AWS: EmiteMax Producao
📞 Tipo de conta: Empresa (ou Pessoal)
```

3. Clique em **"Verificar endereço de e-mail"**
4. Abra seu email e copie o **código de verificação** (6 dígitos)
5. Cole o código e clique em **"Verificar"**

### PASSO 1.3: Criar Senha Root

```
🔒 Senha: Crie uma senha FORTE (mínimo 8 caracteres)
     Exemplo: EmiteMax@AWS2025!SecurePass
     
✅ Recomendação: Anote esta senha em um gerenciador de senhas
```

### PASSO 1.4: Informações de Contato

**Tela 2 - Detalhes da Conta:**

```
Nome completo: Seu Nome ou Razão Social
Telefone: +55 11 98765-4321
País: Brasil
Endereço: Rua/Av completo
Cidade: Sua cidade
Estado: SP (ou seu estado)
CEP: 00000-000
```

Clique em **"Continuar"**

### PASSO 1.5: Informações de Pagamento

**Tela 3 - Método de Pagamento:**

1. Insira os dados do **cartão de crédito internacional**
2. A AWS fará uma **cobrança de $1 USD** para validação (será estornado)
3. Marque **"Uso para empresas"** se for CNPJ

```
💳 Número do cartão: 0000 0000 0000 0000
📅 Validade: MM/AA
🔢 CVV: 000
📝 Nome no cartão: Como está impresso
```

4. Clique em **"Verificar e continuar"**

### PASSO 1.6: Verificação de Identidade

**Tela 4 - Confirmação por Telefone:**

1. Escolha: **"Mensagem de texto (SMS)"** ou **"Chamada de voz"**
2. Insira seu número: `+55 11 98765-4321`
3. Clique em **"Enviar SMS"**
4. Digite o **código de 4 dígitos** recebido
5. Clique em **"Continuar"**

### PASSO 1.7: Escolher Plano de Suporte

**Tela 5 - Plano de Suporte:**

Selecione: **"Plano de suporte Básico - Gratuito"**

```
✅ Básico (Gratuito) - Recomendado para começar
   - Acesso 24/7 ao suporte ao cliente
   - Documentação e white papers
   - Fóruns de suporte da AWS

❌ Developer ($29/mês) - NÃO necessário agora
❌ Business ($100/mês) - NÃO necessário agora
```

Clique em **"Concluir a inscrição"**

### PASSO 1.8: Aguardar Ativação (5-10 minutos)

Você verá a mensagem:

```
🎉 Parabéns! Sua conta da AWS está sendo configurada.
   
   Você receberá um email quando sua conta estiver pronta.
   Isso pode levar alguns minutos.
```

**⏰ Aguarde o email:** "Welcome to Amazon Web Services"

---

## PARTE 2: PRIMEIRO ACESSO E CONFIGURAÇÃO (20 minutos)

### PASSO 2.1: Fazer Login no Console

1. Vá para: **https://console.aws.amazon.com**
2. Clique em **"Root user"** (usuário raiz)
3. Email: `seu@email.com`
4. Senha: A que você criou no Passo 1.3
5. Clique em **"Sign in"**

### PASSO 2.2: Escolher Região (IMPORTANTE!)

No canto superior direito do console, você verá a região atual.

```
🌎 Clique na região (ex: "N. Virginia")
📍 Selecione: "South America (São Paulo) sa-east-1"
```

**⚠️ IMPORTANTE:** Sempre use **São Paulo (sa-east-1)** para melhor latência no Brasil!

### PASSO 2.3: Ativar MFA (Multi-Factor Authentication)

**Por que?** Protege sua conta contra invasões.

1. No canto superior direito, clique no **nome da sua conta**
2. Clique em **"Security credentials"**
3. Role até **"Multi-factor authentication (MFA)"**
4. Clique em **"Assign MFA device"**

**Configurar MFA com Google Authenticator:**

5. Nome do dispositivo: `Meu iPhone` (ou seu celular)
6. Tipo: Selecione **"Authenticator app"**
7. Clique em **"Next"**

**No seu celular:**

8. Baixe o app **"Google Authenticator"** ou **"Microsoft Authenticator"**
9. Abra o app
10. Toque em **"+"** → **"Scan QR code"**
11. Escaneie o QR code mostrado na tela da AWS

**De volta ao navegador:**

12. Digite dois códigos consecutivos do app (aguarde o código mudar)
13. Código 1: `123456`
14. Aguarde ~30 segundos
15. Código 2: `789012`
16. Clique em **"Add MFA"**

```
✅ Sucesso! Agora sua conta está protegida com 2FA
```

### PASSO 2.4: Criar Usuário IAM (Não usar Root)

**Por que?** O usuário root tem poderes TOTAIS. Usaremos um usuário IAM no dia a dia.

1. No menu de serviços, busque e clique em **"IAM"**
2. No menu lateral, clique em **"Users"**
3. Clique em **"Create user"**

**Tela 1 - Detalhes do usuário:**

```
👤 User name: emitemax-admin
☑️ Marque: "Provide user access to the AWS Management Console"
🔘 Selecione: "I want to create an IAM user"
🔒 Console password: Custom password
   Digite: EmiteMax@Admin2025!
☑️ Marque: "Users must create a new password at next sign-in"
```

4. Clique em **"Next"**

**Tela 2 - Permissões:**

5. Selecione: **"Attach policies directly"**
6. Busque e marque: **"AdministratorAccess"**
   ```
   ⚠️ ATENÇÃO: Este é um usuário com poderes totais.
      Nunca compartilhe estas credenciais!
   ```
7. Clique em **"Next"**

**Tela 3 - Revisar e criar:**

8. Revise as informações
9. Clique em **"Create user"**

**Tela 4 - Salvar credenciais:**

```
🎉 Usuário criado com sucesso!

📋 ANOTE ESTAS INFORMAÇÕES (não será mostrado novamente):

Console sign-in URL: https://123456789012.signin.aws.amazon.com/console
User name: emitemax-admin
Password: EmiteMax@Admin2025!

💾 Clique em "Download .csv file" para salvar
```

10. Salve o arquivo `.csv` em local seguro
11. Copie a **Console sign-in URL** (você usará sempre esta URL)

### PASSO 2.5: Fazer Logout e Login com IAM User

1. No canto superior direito, clique no nome da conta
2. Clique em **"Sign out"**
3. Cole a **Console sign-in URL** copiada no passo anterior
4. Faça login com:
   - Account ID: (já preenchido na URL)
   - IAM user name: `emitemax-admin`
   - Password: `EmiteMax@Admin2025!`
5. Você será solicitado a **criar uma nova senha**
6. Crie uma senha nova e ANOTE

```
✅ Pronto! A partir de agora, sempre use este usuário IAM.
   NUNCA mais use o usuário root, exceto em emergências.
```

---

## PARTE 3: INSTALAR E CONFIGURAR AWS CLI (30 minutos)

### PASSO 3.1: Instalar AWS CLI no Mac

Abra o **Terminal** e execute:

```bash
# Baixar instalador
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"

# Instalar
sudo installer -pkg AWSCLIV2.pkg -target /

# Verificar instalação
aws --version
```

Você deve ver algo como:
```
aws-cli/2.13.0 Python/3.11.4 Darwin/22.6.0 source/x86_64 prompt/off
```

### PASSO 3.2: Criar Access Keys

**No Console AWS:**

1. Vá para: **IAM** → **Users** → **emitemax-admin**
2. Clique na aba **"Security credentials"**
3. Role até **"Access keys"**
4. Clique em **"Create access key"**

**Tela 1 - Caso de uso:**

5. Selecione: **"Command Line Interface (CLI)"**
6. Marque: ☑️ **"I understand the above recommendation..."**
7. Clique em **"Next"**

**Tela 2 - Descrição:**

8. Description: `AWS CLI EmiteMax Mac`
9. Clique em **"Create access key"**

**Tela 3 - Salvar chaves:**

```
🔑 Access key ID: AKIAIOSFODNN7EXAMPLE
🔐 Secret access key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

⚠️ ATENÇÃO: A Secret key não será mostrada novamente!
```

10. Clique em **"Download .csv file"**
11. Salve em local seguro (NÃO compartilhe estas chaves!)
12. Clique em **"Done"**

### PASSO 3.3: Configurar AWS CLI

No Terminal:

```bash
# Iniciar configuração
aws configure

# Será solicitado:
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: sa-east-1
Default output format [None]: json
```

**Cole suas chaves reais** (do arquivo .csv baixado)

### PASSO 3.4: Testar Configuração

```bash
# Verificar identidade
aws sts get-caller-identity
```

Você deve ver:
```json
{
    "UserId": "AIDAJEXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/emitemax-admin"
}
```

✅ **Sucesso!** AWS CLI configurado corretamente.

---

## PARTE 4: CONFIGURAR BILLING ALERTS (10 minutos)

**Por que?** Para não ter surpresas na fatura!

### PASSO 4.1: Ativar Billing Alerts

1. No console AWS, clique no **nome da conta** (canto superior direito)
2. Clique em **"Account"**
3. Role até **"Billing preferences"**
4. Clique em **"Edit"**
5. Marque todas as opções:
   ```
   ☑️ Receive PDF Invoice By Email
   ☑️ Receive Free Tier Usage Alerts
   ☑️ Receive CloudWatch Billing Alerts
   ```
6. Email: `seu@email.com`
7. Clique em **"Update"**

### PASSO 4.2: Criar Alarme de Custo

1. Vá para: **CloudWatch** (busque no menu de serviços)
2. No menu lateral, clique em **"Alarms"** → **"All alarms"**
3. Clique em **"Create alarm"**

**Passo 1 - Métrica:**

4. Clique em **"Select metric"**
5. Clique em **"Billing"** → **"Total Estimated Charge"**
6. Marque: ☑️ **USD**
7. Clique em **"Select metric"**

**Passo 2 - Condições:**

8. Statistic: `Maximum`
9. Period: `6 hours`
10. Threshold type: `Static`
11. Whenever EstimatedCharges is: `Greater`
12. than: `100` (ou o valor que deseja ser alertado - ex: R$ 500 = $100)
13. Clique em **"Next"**

**Passo 3 - Notificação:**

14. Alarm state trigger: `In alarm`
15. Select an SNS topic: `Create new topic`
16. Topic name: `billing-alerts`
17. Email: `seu@email.com`
18. Clique em **"Create topic"**
19. Clique em **"Next"**

**Passo 4 - Nome:**

20. Alarm name: `EmiteMax-Billing-Alert-$100`
21. Description: `Alerta quando custo ultrapassar $100`
22. Clique em **"Next"**

**Passo 5 - Revisar:**

23. Revise tudo
24. Clique em **"Create alarm"**

**Confirmar Email:**

25. Abra seu email
26. Procure por: "AWS Notification - Subscription Confirmation"
27. Clique no link **"Confirm subscription"**

```
✅ Alarme criado! Você receberá email se os custos ultrapassarem $100
```

### PASSO 4.3: Criar Alarmes Adicionais (Opcional)

Repita o processo criando alarmes para:
- `$50` - Alerta preventivo
- `$200` - Alerta crítico
- `$500` - Alerta emergencial

---

## PARTE 5: CRIAR VPC E SUBNETS (45 minutos)

### PASSO 5.1: Entendendo a Arquitetura

```
🌐 VPC (Virtual Private Cloud)
   ├── 📡 Public Subnet 1a (10.0.1.0/24) - EC2 API/IA
   ├── 📡 Public Subnet 1b (10.0.2.0/24) - EC2 API (backup)
   ├── 🔒 Private Subnet 1a (10.0.10.0/24) - RDS PostgreSQL
   └── 🔒 Private Subnet 1b (10.0.11.0/24) - RDS (backup)
```

### PASSO 5.2: Criar VPC

1. Vá para: **VPC** (busque no menu de serviços)
2. No menu lateral, clique em **"Your VPCs"**
3. Clique em **"Create VPC"**

**Configuração:**

```
🏷️ Name tag: emitemax-vpc
🌐 IPv4 CIDR block: 10.0.0.0/16
📍 IPv6 CIDR block: No IPv6 CIDR block
🏠 Tenancy: Default
```

4. Clique em **"Create VPC"**
5. **ANOTE o VPC ID:** `vpc-0123456789abcdef0`

### PASSO 5.3: Criar Internet Gateway

1. No menu lateral, clique em **"Internet Gateways"**
2. Clique em **"Create internet gateway"**

```
🏷️ Name tag: emitemax-igw
```

3. Clique em **"Create internet gateway"**
4. Selecione o IGW criado
5. Clique em **"Actions"** → **"Attach to VPC"**
6. Selecione: `emitemax-vpc`
7. Clique em **"Attach internet gateway"**
8. **ANOTE o IGW ID:** `igw-0123456789abcdef0`

### PASSO 5.4: Criar Subnets Públicas

**Subnet Pública 1a:**

1. No menu lateral, clique em **"Subnets"**
2. Clique em **"Create subnet"**

```
🌐 VPC ID: emitemax-vpc
🏷️ Subnet name: emitemax-public-1a
🗺️ Availability Zone: sa-east-1a
📡 IPv4 CIDR block: 10.0.1.0/24
```

3. Clique em **"Create subnet"**
4. **ANOTE o Subnet ID:** `subnet-pub1a-xxxxxxxxx`

**Subnet Pública 1b:**

5. Repita o processo:

```
🌐 VPC ID: emitemax-vpc
🏷️ Subnet name: emitemax-public-1b
🗺️ Availability Zone: sa-east-1b
📡 IPv4 CIDR block: 10.0.2.0/24
```

6. **ANOTE o Subnet ID:** `subnet-pub1b-xxxxxxxxx`

### PASSO 5.5: Criar Subnets Privadas

**Subnet Privada 1a:**

```
🌐 VPC ID: emitemax-vpc
🏷️ Subnet name: emitemax-private-1a
🗺️ Availability Zone: sa-east-1a
🔒 IPv4 CIDR block: 10.0.10.0/24
```

**Subnet Privada 1b:**

```
🌐 VPC ID: emitemax-vpc
🏷️ Subnet name: emitemax-private-1b
🗺️ Availability Zone: sa-east-1b
🔒 IPv4 CIDR block: 10.0.11.0/24
```

### PASSO 5.6: Configurar Route Table para Subnets Públicas

1. No menu lateral, clique em **"Route Tables"**
2. Encontre a route table da VPC `emitemax-vpc`
3. Selecione-a e clique na aba **"Routes"**
4. Clique em **"Edit routes"**
5. Clique em **"Add route"**

```
🎯 Destination: 0.0.0.0/0
🌐 Target: Internet Gateway → emitemax-igw
```

6. Clique em **"Save changes"**

**Associar subnets públicas:**

7. Clique na aba **"Subnet associations"**
8. Clique em **"Edit subnet associations"**
9. Marque: `emitemax-public-1a` e `emitemax-public-1b`
10. Clique em **"Save associations"**

### PASSO 5.7: Habilitar Auto-assign IP nas Subnets Públicas

Para cada subnet pública (1a e 1b):

1. Vá em **Subnets**
2. Selecione `emitemax-public-1a`
3. Clique em **"Actions"** → **"Edit subnet settings"**
4. Marque: ☑️ **"Enable auto-assign public IPv4 address"**
5. Clique em **"Save"**
6. Repita para `emitemax-public-1b`

---

## PARTE 6: CRIAR SECURITY GROUPS (30 minutos)

### PASSO 6.1: Security Group para Load Balancer

1. Vá para: **EC2** → **Security Groups** (menu lateral)
2. Clique em **"Create security group"**

```
🏷️ Security group name: emitemax-alb-sg
📝 Description: Security group for Application Load Balancer
🌐 VPC: emitemax-vpc
```

**Inbound rules:**

3. Clique em **"Add rule"**

```
Rule 1:
Type: HTTP
Port: 80
Source: 0.0.0.0/0 (Anywhere IPv4)
Description: Allow HTTP from internet

Rule 2:
Type: HTTPS
Port: 443
Source: 0.0.0.0/0 (Anywhere IPv4)
Description: Allow HTTPS from internet
```

**Outbound rules:**

4. Deixe o padrão (All traffic)
5. Clique em **"Create security group"**
6. **ANOTE o SG ID:** `sg-alb-xxxxxxxxx`

### PASSO 6.2: Security Group para EC2 API

```
🏷️ Security group name: emitemax-api-sg
📝 Description: Security group for Flask API instances
🌐 VPC: emitemax-vpc
```

**Inbound rules:**

```
Rule 1:
Type: Custom TCP
Port: 8080
Source: Custom → emitemax-alb-sg (selecione o SG do ALB)
Description: Allow traffic from ALB

Rule 2:
Type: SSH
Port: 22
Source: My IP (seu IP será auto-detectado)
Description: SSH access for management
```

7. **ANOTE o SG ID:** `sg-api-xxxxxxxxx`

### PASSO 6.3: Security Group para EC2 IA

```
🏷️ Security group name: emitemax-ia-sg
📝 Description: Security group for LM Studio AI instance
🌐 VPC: emitemax-vpc
```

**Inbound rules:**

```
Rule 1:
Type: Custom TCP
Port: 9000
Source: Custom → emitemax-api-sg (SG da API)
Description: Allow API to access IA service

Rule 2:
Type: SSH
Port: 22
Source: My IP
Description: SSH access
```

8. **ANOTE o SG ID:** `sg-ia-xxxxxxxxx`

### PASSO 6.4: Security Group para RDS

```
🏷️ Security group name: emitemax-rds-sg
📝 Description: Security group for RDS PostgreSQL
🌐 VPC: emitemax-vpc
```

**Inbound rules:**

```
Rule 1:
Type: PostgreSQL
Port: 5432
Source: Custom → emitemax-api-sg
Description: Allow API instances to access database
```

9. **ANOTE o SG ID:** `sg-rds-xxxxxxxxx`

---

## PARTE 7: CRIAR IAM ROLES (20 minutos)

### PASSO 7.1: Role para EC2 (Acesso S3 e CloudWatch)

1. Vá para: **IAM** → **Roles**
2. Clique em **"Create role"**

**Passo 1 - Trusted entity:**

```
🔘 Trusted entity type: AWS service
📦 Use case: EC2
```

3. Clique em **"Next"**

**Passo 2 - Permissions:**

4. Busque e marque as seguintes policies:
   - ☑️ `AmazonS3FullAccess`
   - ☑️ `CloudWatchAgentServerPolicy`
   - ☑️ `AmazonSSMManagedInstanceCore`

5. Clique em **"Next"**

**Passo 3 - Nome:**

```
🏷️ Role name: EmiteMaxEC2Role
📝 Description: Role for EC2 instances to access S3 and CloudWatch
```

6. Clique em **"Create role"**

### PASSO 7.2: Role para Lambda (Backups)

1. Clique em **"Create role"**

```
🔘 Trusted entity type: AWS service
📦 Use case: Lambda
```

2. Permissions:
   - ☑️ `AWSLambdaBasicExecutionRole`
   - ☑️ `AmazonRDSFullAccess`

```
🏷️ Role name: EmiteMaxLambdaBackupRole
```

3. Clique em **"Create role"**

---

## PARTE 8: CRIAR KEY PAIR (5 minutos)

Para acessar instâncias EC2 via SSH:

1. Vá para: **EC2** → **Key Pairs** (menu lateral)
2. Clique em **"Create key pair"**

```
🏷️ Name: emitemax-key
🔑 Key pair type: RSA
📄 Private key file format: .pem (para Mac/Linux)
```

3. Clique em **"Create key pair"**
4. O arquivo `emitemax-key.pem` será baixado automaticamente
5. Salve em local seguro

**No Terminal, configure permissões:**

```bash
# Mover para pasta segura
mv ~/Downloads/emitemax-key.pem ~/.ssh/

# Configurar permissões
chmod 400 ~/.ssh/emitemax-key.pem
```

---

## 📝 CHECKLIST FINAL DO SETUP INICIAL

Marque conforme completa:

### Conta e Acesso
- [ ] Conta AWS criada
- [ ] Email verificado
- [ ] MFA ativado no usuário root
- [ ] Usuário IAM admin criado
- [ ] AWS CLI instalado e configurado
- [ ] Access Keys criadas e salvas

### Billing
- [ ] Billing alerts ativado
- [ ] Alarme de custo $50 criado
- [ ] Alarme de custo $100 criado
- [ ] Email de notificação confirmado

### Rede (VPC)
- [ ] VPC criada (10.0.0.0/16)
- [ ] Internet Gateway criado e anexado
- [ ] 2 Subnets públicas criadas (1a, 1b)
- [ ] 2 Subnets privadas criadas (1a, 1b)
- [ ] Route table configurada
- [ ] Auto-assign IP habilitado nas públicas

### Security Groups
- [ ] SG do ALB criado (sg-alb-xxx)
- [ ] SG da API criado (sg-api-xxx)
- [ ] SG da IA criado (sg-ia-xxx)
- [ ] SG do RDS criado (sg-rds-xxx)

### IAM
- [ ] Role EC2 criada (EmiteMaxEC2Role)
- [ ] Role Lambda criada (EmiteMaxLambdaBackupRole)

### SSH
- [ ] Key pair criada (emitemax-key.pem)
- [ ] Permissões configuradas (chmod 400)
- [ ] Arquivo salvo em ~/.ssh/

---

## 📋 INFORMAÇÕES IMPORTANTES - ANOTE AQUI

```
═══════════════════════════════════════════════════════
                    CREDENCIAIS AWS
═══════════════════════════════════════════════════════

🔐 USUÁRIO ROOT
Email: _______________________________________
Senha: _______________________________________ 
MFA: Configurado? [ ] Sim [ ] Não

🔐 USUÁRIO IAM (emitemax-admin)
Console URL: https://____________.signin.aws.amazon.com/console
Username: emitemax-admin
Senha: _______________________________________
MFA: Configurado? [ ] Sim [ ] Não

🔑 ACCESS KEYS
Access Key ID: _______________________________________
Secret Key: __________________________________________ 
(guardado em: _______________________________________ )

═══════════════════════════════════════════════════════
                    IDENTIFICADORES
═══════════════════════════════════════════════════════

VPC ID: vpc-_______________________________________
IGW ID: igw-_______________________________________

SUBNETS:
  Public 1a:  subnet-_______________________________________
  Public 1b:  subnet-_______________________________________
  Private 1a: subnet-_______________________________________
  Private 1b: subnet-_______________________________________

SECURITY GROUPS:
  ALB SG:  sg-_______________________________________
  API SG:  sg-_______________________________________
  IA SG:   sg-_______________________________________
  RDS SG:  sg-_______________________________________

IAM ROLES:
  EC2 Role:    EmiteMaxEC2Role
  Lambda Role: EmiteMaxLambdaBackupRole

KEY PAIR:
  Nome: emitemax-key
  Localização: ~/.ssh/emitemax-key.pem

═══════════════════════════════════════════════════════
```

---

## 🎉 PARABÉNS!

Você concluiu o setup inicial da AWS! 

### Próximos Passos:

1. **Deploy do Banco de Dados (RDS)** - Ver: `DEPLOY_AWS_COMPLETO.md` Parte 5
2. **Deploy da API Flask** - Ver: `DEPLOY_AWS_COMPLETO.md` Parte 6
3. **Deploy da IA (LM Studio)** - Ver: `DEPLOY_AWS_COMPLETO.md` Parte 7

---

## 🆘 PROBLEMAS COMUNS

### "Access Denied" ao executar AWS CLI

**Solução:**
```bash
# Reconfigurar credenciais
aws configure

# Verificar identidade
aws sts get-caller-identity
```

### "InvalidKeyPair" ao criar EC2

**Solução:**
```bash
# Verificar se key pair existe
aws ec2 describe-key-pairs --key-names emitemax-key

# Se não existir, criar novamente via console
```

### Não recebo emails da AWS

**Solução:**
1. Verifique caixa de spam/lixo eletrônico
2. Adicione `no-reply@aws.amazon.com` aos contatos
3. Verifique em: Account → Preferences → Email

### Região errada

**Solução:**
1. Sempre verificar canto superior direito do console
2. Selecionar: **São Paulo (sa-east-1)**
3. No AWS CLI: `aws configure` e definir `sa-east-1`

---

## 📞 SUPORTE

- **Documentação AWS:** https://docs.aws.amazon.com/pt_br/
- **Fórum AWS:** https://forums.aws.amazon.com/
- **AWS Support:** https://console.aws.amazon.com/support/home

---

**✅ Setup Inicial Completo!**

**Última atualização:** 15 de dezembro de 2025  
**Versão:** 1.0

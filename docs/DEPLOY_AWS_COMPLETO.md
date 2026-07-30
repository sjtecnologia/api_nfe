# 🚀 GUIA COMPLETO DE DEPLOY NA AWS
## Sistema NFe + IA (LM Studio) + Site de Vendas

**Data:** 15 de dezembro de 2025  
**Projeto:** EmiteMax NFe SaaS  
**Infraestrutura:** Amazon AWS

---

## 📋 ÍNDICE

1. [Arquitetura Proposta](#arquitetura)
2. [Pré-requisitos](#prerequisitos)
3. [Custos Estimados](#custos)
4. [Setup Inicial AWS](#setup-aws)
5. [Deploy do Banco de Dados (RDS)](#deploy-rds)
6. [Deploy da API Principal (Flask)](#deploy-api)
7. [Deploy da IA (LM Studio)](#deploy-ia)
8. [Deploy do Site de Vendas](#deploy-site)
9. [Configuração de Domínio e SSL](#dominio-ssl)
10. [Backup e Monitoramento](#backup)
11. [Testes e Validação](#testes)
12. [Manutenção e Escalabilidade](#manutencao)

---

## 🏗️ ARQUITETURA PROPOSTA {#arquitetura}

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERNET                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Route 53 (DNS)      │
         │  emitemax.com.br      │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  CloudFront (CDN)     │
         │  + WAF (Firewall)     │
         └─────┬─────────────┬───┘
               │             │
       ┌───────▼──────┐  ┌──▼─────────────┐
       │ Application  │  │  Static Site   │
       │ Load Balancer│  │  (S3 + React)  │
       └───────┬──────┘  └────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐  ┌──▼───┐  ┌───▼───┐
│ EC2-1 │  │ EC2-2│  │ EC2-3 │
│Flask  │  │Flask │  │ LM    │
│API    │  │API   │  │Studio │
│:8080  │  │:8080 │  │:9000  │
└───┬───┘  └───┬──┘  └───┬───┘
    │          │          │
    └──────────┼──────────┘
               │
         ┌─────▼─────┐
         │    RDS    │
         │PostgreSQL │
         │  (Multi-AZ)│
         └───────────┘
```

### Componentes:

1. **Route 53:** DNS gerenciado
2. **CloudFront:** CDN para cache e performance
3. **ALB:** Load Balancer para distribuir tráfego
4. **EC2 (API):** 2 instâncias para API Flask (Alta Disponibilidade)
5. **EC2 (IA):** 1 instância GPU para LM Studio
6. **RDS:** PostgreSQL gerenciado (Multi-AZ para backup automático)
7. **S3:** Site estático de vendas + armazenamento de arquivos
8. **CloudWatch:** Monitoramento e logs
9. **Secrets Manager:** Armazenamento seguro de credenciais

---

## 📦 PRÉ-REQUISITOS {#prerequisitos}

### 1. Conta AWS
- [ ] Conta AWS criada e verificada
- [ ] Billing configurado com alertas
- [ ] IAM User com permissões administrativas
- [ ] AWS CLI instalado localmente

### 2. Domínio
- [ ] Domínio registrado (ex: emitemax.com.br)
- [ ] Acesso ao painel DNS do registrador

### 3. Certificados e Chaves
- [ ] Certificados digitais A1 dos clientes (armazenar em S3 criptografado)
- [ ] Chave SSH para acesso EC2

### 4. Modelo de IA
- [ ] Modelo LLaMA treinado e exportado
- [ ] Arquivos GGUF prontos para LM Studio
- [ ] Datasets de treinamento (backup)

### 5. Código e Dependências
- [ ] Repositório Git atualizado
- [ ] requirements.txt completo
- [ ] Variáveis de ambiente documentadas

---

## 💰 CUSTOS ESTIMADOS MENSAIS {#custos}

| Serviço | Especificação | Custo USD | Custo BRL* |
|---------|---------------|-----------|------------|
| **EC2 - API** | 2x t3.medium (2 vCPU, 4GB RAM) | $60 | R$ 300 |
| **EC2 - IA** | 1x g4dn.xlarge (4 vCPU, 16GB, GPU) | $390 | R$ 1.950 |
| **RDS PostgreSQL** | db.t3.small Multi-AZ | $70 | R$ 350 |
| **ALB** | Application Load Balancer | $20 | R$ 100 |
| **S3** | 100GB storage + requests | $10 | R$ 50 |
| **CloudFront** | 500GB transfer | $40 | R$ 200 |
| **Route 53** | Hosted Zone + queries | $5 | R$ 25 |
| **CloudWatch** | Logs e métricas | $15 | R$ 75 |
| **Backup (S3 Glacier)** | 500GB | $5 | R$ 25 |
| **Data Transfer** | Saída de dados | $20 | R$ 100 |
| **TOTAL** | | **$635** | **R$ 3.175** |

*Taxa aproximada: 1 USD = 5 BRL

### Opções de Economia:

1. **Reserved Instances (1 ano):** Economiza até 40% em EC2
2. **Spot Instances para IA:** Economiza até 70% (com interrupções)
3. **Desligar IA fora do horário:** Economiza ~50% no EC2 GPU
4. **Tier gratuito AWS (12 meses):** Para novos clientes

**Custo otimizado estimado:** R$ 2.000 - R$ 2.500/mês

---

## 🔧 SETUP INICIAL AWS {#setup-aws}

### PASSO 1: Configurar AWS CLI

```bash
# Instalar AWS CLI
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Configurar credenciais
aws configure
# AWS Access Key ID: [SUA_KEY]
# AWS Secret Access Key: [SUA_SECRET]
# Default region name: us-east-1
# Default output format: json

# Verificar
aws sts get-caller-identity
```

### PASSO 2: Criar VPC e Subnets

```bash
# Criar VPC
aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=emitemax-vpc}]'

# Guardar VPC ID
VPC_ID="vpc-xxxxxxxxx"

# Criar Subnets (2 zonas de disponibilidade)
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=emitemax-public-1a}]'

aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=emitemax-public-1b}]'

# Subnets privadas para RDS
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.10.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=emitemax-private-1a}]'

aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.11.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=emitemax-private-1b}]'
```

### PASSO 3: Configurar Internet Gateway

```bash
# Criar IGW
aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=emitemax-igw}]'

IGW_ID="igw-xxxxxxxxx"

# Anexar à VPC
aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

# Configurar route table
aws ec2 create-route \
  --route-table-id rtb-xxxxxxxxx \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID
```

### PASSO 4: Security Groups

```bash
# Security Group para ALB (Load Balancer)
aws ec2 create-security-group \
  --group-name emitemax-alb-sg \
  --description "Security group for ALB" \
  --vpc-id $VPC_ID

# Permitir HTTP e HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id sg-alb-xxxxxxxxx \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-alb-xxxxxxxxx \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

# Security Group para EC2 API
aws ec2 create-security-group \
  --group-name emitemax-api-sg \
  --description "Security group for Flask API" \
  --vpc-id $VPC_ID

# Permitir tráfego do ALB
aws ec2 authorize-security-group-ingress \
  --group-id sg-api-xxxxxxxxx \
  --protocol tcp --port 8080 \
  --source-group sg-alb-xxxxxxxxx

# Security Group para EC2 IA
aws ec2 create-security-group \
  --group-name emitemax-ia-sg \
  --description "Security group for LM Studio" \
  --vpc-id $VPC_ID

# Permitir tráfego da API
aws ec2 authorize-security-group-ingress \
  --group-id sg-ia-xxxxxxxxx \
  --protocol tcp --port 9000 \
  --source-group sg-api-xxxxxxxxx

# Security Group para RDS
aws ec2 create-security-group \
  --group-name emitemax-rds-sg \
  --description "Security group for RDS PostgreSQL" \
  --vpc-id $VPC_ID

# Permitir PostgreSQL da API
aws ec2 authorize-security-group-ingress \
  --group-id sg-rds-xxxxxxxxx \
  --protocol tcp --port 5432 \
  --source-group sg-api-xxxxxxxxx
```

---

## 🗄️ DEPLOY DO BANCO DE DADOS (RDS) {#deploy-rds}

### PASSO 1: Criar Subnet Group

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name emitemax-rds-subnet-group \
  --db-subnet-group-description "Subnet group for EmiteMax RDS" \
  --subnet-ids subnet-private-1a subnet-private-1b \
  --tags Key=Name,Value=emitemax-rds-subnet-group
```

### PASSO 2: Criar RDS PostgreSQL

```bash
aws rds create-db-instance \
  --db-instance-identifier emitemax-db \
  --db-instance-class db.t3.small \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password "SuaSenhaSuperSegura123!" \
  --allocated-storage 100 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-rds-xxxxxxxxx \
  --db-subnet-group-name emitemax-rds-subnet-group \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --multi-az \
  --publicly-accessible false \
  --storage-encrypted \
  --enable-cloudwatch-logs-exports '["postgresql"]' \
  --tags Key=Name,Value=emitemax-production-db
```

### PASSO 3: Aguardar Criação (15-20 minutos)

```bash
# Verificar status
aws rds describe-db-instances \
  --db-instance-identifier emitemax-db \
  --query 'DBInstances[0].DBInstanceStatus'

# Obter endpoint quando pronto
aws rds describe-db-instances \
  --db-instance-identifier emitemax-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
```

### PASSO 4: Restaurar Banco de Dados

```bash
# Conectar via bastion host ou EC2
psql -h emitemax-db.xxxxxxxx.us-east-1.rds.amazonaws.com \
     -U postgres -d postgres

# Criar database
CREATE DATABASE sjtnfe;

# Restaurar backup
psql -h emitemax-db.xxxxxxxx.us-east-1.rds.amazonaws.com \
     -U postgres -d sjtnfe < backups/sjtnfe.sql

# Ou executar migrations
cd /Users/renato/Documents/Developement/api_nfe
# (Executar na instância EC2 depois)
```

---

## 🐍 DEPLOY DA API PRINCIPAL (FLASK) {#deploy-api}

### PASSO 1: Criar AMI Personalizado

```bash
# Criar script de inicialização
cat > user-data-api.sh << 'EOF'
#!/bin/bash
# Atualizar sistema
yum update -y

# Instalar Python 3.11
amazon-linux-extras install python3.11 -y

# Instalar dependências do sistema
yum install -y git postgresql15 nginx

# Criar usuário para aplicação
useradd -m -s /bin/bash emitemax

# Clonar repositório (usar deploy keys)
su - emitemax -c "git clone git@github.com:sjtecnologia/api_nfe.git /home/emitemax/app"

# Instalar dependências Python
cd /home/emitemax/app
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Configurar variáveis de ambiente
cat > .env << 'ENVEOF'
FLASK_SECRET_KEY='sua-chave-super-secreta-aqui-256-bits'
DATABASE_URL='postgresql://postgres:senha@emitemax-db.xxx.rds.amazonaws.com:5432/sjtnfe'
FLASK_DEBUG='False'
FLASK_HOST='0.0.0.0'
PORT='8080'
SEFAZ_AMBIENTE_HOMOLOGACAO='True'
ENVEOF

# Criar serviço systemd
cat > /etc/systemd/system/emitemax-api.service << 'SERVICEEOF'
[Unit]
Description=EmiteMax NFe API
After=network.target

[Service]
Type=notify
User=emitemax
WorkingDirectory=/home/emitemax/app
Environment="PATH=/home/emitemax/app/venv/bin"
ExecStart=/home/emitemax/app/venv/bin/gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --access-logfile /home/emitemax/app/logs/access.log \
    --error-logfile /home/emitemax/app/logs/error.log \
    app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Iniciar serviço
systemctl daemon-reload
systemctl enable emitemax-api
systemctl start emitemax-api

# Configurar nginx como proxy reverso
cat > /etc/nginx/conf.d/emitemax.conf << 'NGINXEOF'
upstream api_backend {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    location /static {
        alias /home/emitemax/app/static;
        expires 30d;
    }
}
NGINXEOF

systemctl enable nginx
systemctl start nginx

# Instalar CloudWatch Agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Configurar logs para CloudWatch
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWEOF'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/home/emitemax/app/logs/app.log",
            "log_group_name": "/emitemax/api",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
CWEOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
EOF
```

### PASSO 2: Lançar Instâncias EC2

```bash
# Lançar 2 instâncias para API
aws ec2 run-instances \
  --image-id ami-0c02fb55c47b5f0e8 \
  --instance-type t3.medium \
  --count 2 \
  --key-name emitemax-key \
  --security-group-ids sg-api-xxxxxxxxx \
  --subnet-id subnet-public-1a \
  --user-data file://user-data-api.sh \
  --iam-instance-profile Name=EmiteMaxEC2Role \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=emitemax-api}]' \
  --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=50,VolumeType=gp3}'

# Aguardar inicialização
aws ec2 wait instance-running --instance-ids i-api1 i-api2

# Verificar status
aws ec2 describe-instances \
  --instance-ids i-api1 i-api2 \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]'
```

### PASSO 3: Criar Application Load Balancer

```bash
# Criar ALB
aws elbv2 create-load-balancer \
  --name emitemax-alb \
  --subnets subnet-public-1a subnet-public-1b \
  --security-groups sg-alb-xxxxxxxxx \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4

ALB_ARN="arn:aws:elasticloadbalancing:..."

# Criar Target Group
aws elbv2 create-target-group \
  --name emitemax-api-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id $VPC_ID \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

TG_ARN="arn:aws:elasticloadbalancing:..."

# Registrar instâncias
aws elbv2 register-targets \
  --target-group-arn $TG_ARN \
  --targets Id=i-api1 Id=i-api2

# Criar Listener HTTP
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

### PASSO 4: Adicionar Health Check na API

```bash
# SSH nas instâncias e adicionar rota /health no Flask
# Arquivo: routes/health_routes.py
```

Criar arquivo `routes/health_routes.py`:

```python
from flask import Blueprint, jsonify
import psycopg2
from config.settings import SQLALCHEMY_DATABASE_URL

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint para ALB"""
    try:
        # Verificar conexão com banco
        conn = psycopg2.connect(SQLALCHEMY_DATABASE_URL)
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503
```

Registrar no `app.py`:

```python
from routes.health_routes import health_bp
app.register_blueprint(health_bp)
```

---

## 🤖 DEPLOY DA IA (LM STUDIO) {#deploy-ia}

### PASSO 1: Lançar Instância GPU

```bash
# Script de inicialização para IA
cat > user-data-ia.sh << 'EOF'
#!/bin/bash
# Instalar drivers NVIDIA
yum install -y gcc kernel-devel-$(uname -r)
aws s3 cp --recursive s3://ec2-linux-nvidia-drivers/latest/ .
chmod +x NVIDIA-Linux-x86_64*.run
./NVIDIA-Linux-x86_64*.run -s

# Instalar Docker
yum install -y docker
systemctl start docker
systemctl enable docker

# Instalar Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Instalar NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.repo | \
  tee /etc/yum.repos.d/nvidia-container-toolkit.repo
yum install -y nvidia-container-toolkit
systemctl restart docker

# Criar diretório para IA
mkdir -p /home/emitemax/ia
cd /home/emitemax/ia

# Baixar modelo treinado do S3
aws s3 cp s3://emitemax-models/llama-ncm-trained.gguf ./models/

# Criar docker-compose.yml
cat > docker-compose.yml << 'DOCKEREOF'
version: '3.8'

services:
  lmstudio:
    image: nvidia/cuda:12.2.0-runtime-ubuntu22.04
    runtime: nvidia
    ports:
      - "9000:9000"
    volumes:
      - ./models:/models
      - ./lmstudio:/app
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    command: |
      bash -c "
        apt-get update && apt-get install -y python3 python3-pip curl &&
        pip3 install llama-cpp-python[server] &&
        python3 -m llama_cpp.server \
          --model /models/llama-ncm-trained.gguf \
          --host 0.0.0.0 \
          --port 9000 \
          --n_ctx 4096 \
          --n_gpu_layers -1
      "
    restart: always
DOCKEREOF

# Iniciar serviço
docker-compose up -d

# Configurar logs para CloudWatch
# (mesmo processo do PASSO 1 da API)
EOF

# Lançar instância GPU
aws ec2 run-instances \
  --image-id ami-0c02fb55c47b5f0e8 \
  --instance-type g4dn.xlarge \
  --count 1 \
  --key-name emitemax-key \
  --security-group-ids sg-ia-xxxxxxxxx \
  --subnet-id subnet-public-1a \
  --user-data file://user-data-ia.sh \
  --iam-instance-profile Name=EmiteMaxEC2Role \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=emitemax-ia}]' \
  --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=100,VolumeType=gp3}'
```

### PASSO 2: Upload do Modelo Treinado

```bash
# Fazer upload do modelo para S3
aws s3 mb s3://emitemax-models
aws s3 cp ~/models/llama-ncm-trained.gguf s3://emitemax-models/
aws s3 cp --recursive ~/datasets/ s3://emitemax-models/datasets/

# Definir políticas de acesso
aws s3api put-bucket-encryption \
  --bucket emitemax-models \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

### PASSO 3: Testar Endpoint da IA

```bash
# SSH na instância IA
ssh -i emitemax-key.pem ec2-user@<IP_INSTANCIA_IA>

# Verificar logs
docker-compose logs -f

# Testar endpoint
curl -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Qual NCM para notebook Dell?"}
    ],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

### PASSO 4: Atualizar API para Usar IA na AWS

Atualizar `config/settings.py`:

```python
# IA Service URL
IA_SERVICE_URL = os.getenv('IA_SERVICE_URL', 'http://10.0.1.50:9000')  # IP privado da instância IA
```

---

## 🌐 DEPLOY DO SITE DE VENDAS {#deploy-site}

### PASSO 1: Estrutura do Site (React + Next.js)

```bash
# Criar projeto Next.js
npx create-next-app@latest emitemax-site
cd emitemax-site

# Estrutura de páginas
mkdir -p pages/{api,pricing,features,docs,login}
mkdir -p components/{pricing,features,layout}
mkdir -p lib/{stripe,api}

# Instalar dependências
npm install @stripe/stripe-js stripe axios swr tailwindcss
```

### PASSO 2: Página de Pricing

Criar `pages/pricing.tsx`:

```typescript
import { useState } from 'react';
import axios from 'axios';

interface Plan {
  id: number;
  nome: string;
  descricao: string;
  preco_mensal: number;
  limite_nfe_mes: number;
  recursos: string[];
}

export default function Pricing() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSubscribe = async (planId: number) => {
    setLoading(true);
    try {
      // Criar checkout session no Stripe
      const response = await axios.post('/api/create-checkout-session', {
        planId,
      });
      
      // Redirecionar para Stripe Checkout
      window.location.href = response.data.url;
    } catch (error) {
      console.error('Erro ao criar sessão:', error);
      alert('Erro ao processar pagamento');
    }
    setLoading(false);
  };

  return (
    <div className="pricing-container">
      <h1>Escolha seu Plano</h1>
      <div className="plans-grid">
        {plans.map(plan => (
          <div key={plan.id} className="plan-card">
            <h2>{plan.nome}</h2>
            <p className="price">R$ {plan.preco_mensal}/mês</p>
            <p>{plan.descricao}</p>
            <ul>
              <li>{plan.limite_nfe_mes} NFe/mês</li>
              {plan.recursos.map(r => <li key={r}>{r}</li>)}
            </ul>
            <button onClick={() => handleSubscribe(plan.id)} disabled={loading}>
              Assinar Agora
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### PASSO 3: API Route para Stripe

Criar `pages/api/create-checkout-session.ts`:

```typescript
import { NextApiRequest, NextApiResponse } from 'next';
import Stripe from 'stripe';
import axios from 'axios';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
});

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { planId, email, cnpj } = req.body;

  try {
    // Buscar detalhes do plano na API
    const planResponse = await axios.get(
      `${process.env.API_URL}/api/planos/${planId}`
    );
    const plan = planResponse.data;

    // Criar sessão de checkout no Stripe
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [
        {
          price_data: {
            currency: 'brl',
            product_data: {
              name: plan.nome,
              description: plan.descricao,
            },
            unit_amount: plan.preco_mensal * 100, // em centavos
            recurring: {
              interval: 'month',
            },
          },
          quantity: 1,
        },
      ],
      success_url: `${process.env.NEXT_PUBLIC_URL}/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.NEXT_PUBLIC_URL}/pricing`,
      metadata: {
        planId: planId.toString(),
        email,
        cnpj,
      },
    });

    res.status(200).json({ url: session.url });
  } catch (error) {
    console.error('Erro ao criar checkout:', error);
    res.status(500).json({ error: 'Erro ao criar sessão de pagamento' });
  }
}
```

### PASSO 4: Webhook do Stripe

Criar `pages/api/webhooks/stripe.ts`:

```typescript
import { buffer } from 'micro';
import { NextApiRequest, NextApiResponse } from 'next';
import Stripe from 'stripe';
import axios from 'axios';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).end();
  }

  const buf = await buffer(req);
  const sig = req.headers['stripe-signature']!;

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(
      buf,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET!
    );
  } catch (err) {
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  // Processar evento
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as Stripe.Checkout.Session;
    
    // Criar assinatura no banco de dados
    await axios.post(`${process.env.API_URL}/api/assinaturas/criar`, {
      cliente_email: session.customer_details?.email,
      cliente_cnpj: session.metadata?.cnpj,
      plano_id: session.metadata?.planId,
      stripe_subscription_id: session.subscription,
      stripe_customer_id: session.customer,
      status: 'ativa',
    });
  }

  if (event.type === 'invoice.payment_succeeded') {
    const invoice = event.data.object as Stripe.Invoice;
    
    // Atualizar status da assinatura
    await axios.post(`${process.env.API_URL}/api/assinaturas/renovar`, {
      stripe_subscription_id: invoice.subscription,
    });
  }

  if (event.type === 'customer.subscription.deleted') {
    const subscription = event.data.object as Stripe.Subscription;
    
    // Cancelar assinatura no banco
    await axios.post(`${process.env.API_URL}/api/assinaturas/cancelar`, {
      stripe_subscription_id: subscription.id,
    });
  }

  res.json({ received: true });
}
```

### PASSO 5: Build e Deploy no S3

```bash
# Build do site
npm run build
npm run export

# Criar bucket S3
aws s3 mb s3://www.emitemax.com.br
aws s3 website s3://www.emitemax.com.br/ \
  --index-document index.html \
  --error-document 404.html

# Definir política pública
aws s3api put-bucket-policy \
  --bucket www.emitemax.com.br \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::www.emitemax.com.br/*"
    }]
  }'

# Fazer upload
aws s3 sync out/ s3://www.emitemax.com.br/ --delete

# Criar CloudFront distribution
aws cloudfront create-distribution \
  --origin-domain-name www.emitemax.com.br.s3-website-us-east-1.amazonaws.com \
  --default-root-object index.html
```

---

## 🌍 CONFIGURAÇÃO DE DOMÍNIO E SSL {#dominio-ssl}

### PASSO 1: Route 53

```bash
# Criar Hosted Zone
aws route53 create-hosted-zone \
  --name emitemax.com.br \
  --caller-reference $(date +%s)

# Obter Name Servers
aws route53 list-hosted-zones \
  --query 'HostedZones[?Name==`emitemax.com.br.`].DelegationSet.NameServers'

# Atualizar NS no registrador do domínio
# Ex: registro.br - usar os 4 name servers retornados
```

### PASSO 2: Certificado SSL (ACM)

```bash
# Solicitar certificado
aws acm request-certificate \
  --domain-name emitemax.com.br \
  --subject-alternative-names '*.emitemax.com.br' \
  --validation-method DNS \
  --region us-east-1

# Obter records de validação
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:... \
  --query 'Certificate.DomainValidationOptions'

# Criar records no Route 53 (ou fazer via console)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://validation-record.json
```

### PASSO 3: Configurar HTTPS no ALB

```bash
# Adicionar listener HTTPS
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

# Redirecionar HTTP para HTTPS
aws elbv2 modify-listener \
  --listener-arn $HTTP_LISTENER_ARN \
  --default-actions \
    'Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'
```

### PASSO 4: Criar Records DNS

```bash
# API
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.emitemax.com.br",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "emitemax-alb-123456789.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'

# Site
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "www.emitemax.com.br",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "d111111abcdef8.cloudfront.net",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'
```

---

## 💾 BACKUP E MONITORAMENTO {#backup}

### PASSO 1: Configurar Backups Automáticos

```bash
# RDS já tem backup automático configurado (7 dias)
# Criar snapshots adicionais via Lambda

cat > lambda-backup.py << 'EOF'
import boto3
from datetime import datetime

def lambda_handler(event, context):
    rds = boto3.client('rds')
    
    # Criar snapshot manual
    snapshot_id = f"emitemax-manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    rds.create_db_snapshot(
        DBSnapshotIdentifier=snapshot_id,
        DBInstanceIdentifier='emitemax-db'
    )
    
    return {'statusCode': 200, 'body': f'Snapshot {snapshot_id} criado'}
EOF

# Criar função Lambda
aws lambda create-function \
  --function-name emitemax-backup \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-backup-role \
  --handler lambda-backup.lambda_handler \
  --zip-file fileb://lambda-backup.zip

# Criar EventBridge rule (diário às 3h)
aws events put-rule \
  --name emitemax-daily-backup \
  --schedule-expression 'cron(0 3 * * ? *)'

aws events put-targets \
  --rule emitemax-daily-backup \
  --targets "Id=1,Arn=arn:aws:lambda:REGION:ACCOUNT:function:emitemax-backup"
```

### PASSO 2: CloudWatch Alarms

```bash
# Alarme de CPU alta na API
aws cloudwatch put-metric-alarm \
  --alarm-name emitemax-api-high-cpu \
  --alarm-description "CPU alta nas instâncias API" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:emitemax-alerts

# Alarme de conexões RDS
aws cloudwatch put-metric-alarm \
  --alarm-name emitemax-rds-connections \
  --alarm-description "Muitas conexões no RDS" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 90 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=DBInstanceIdentifier,Value=emitemax-db \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:emitemax-alerts

# Alarme de erro 5xx no ALB
aws cloudwatch put-metric-alarm \
  --alarm-name emitemax-alb-5xx \
  --alarm-description "Erros 5xx no ALB" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:emitemax-alerts
```

### PASSO 3: Dashboard CloudWatch

```bash
aws cloudwatch put-dashboard \
  --dashboard-name EmiteMax-Production \
  --dashboard-body file://dashboard.json
```

Criar `dashboard.json`:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/EC2", "CPUUtilization", {"stat": "Average"}],
          ["AWS/RDS", "CPUUtilization", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "CPU Utilization"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApplicationELB", "RequestCount"],
          [".", "HTTPCode_Target_2XX_Count"],
          [".", "HTTPCode_Target_5XX_Count"]
        ],
        "period": 60,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "ALB Requests"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/RDS", "DatabaseConnections"],
          [".", "ReadLatency"],
          [".", "WriteLatency"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "RDS Performance"
      }
    }
  ]
}
```

---

## ✅ TESTES E VALIDAÇÃO {#testes}

### Checklist de Validação:

```bash
# 1. Testar conectividade DNS
dig api.emitemax.com.br
dig www.emitemax.com.br

# 2. Testar SSL
curl -I https://api.emitemax.com.br/health

# 3. Testar API endpoints
curl https://api.emitemax.com.br/api/planos
curl https://api.emitemax.com.br/api/regime-tributario/1

# 4. Testar IA
curl -X POST https://api.emitemax.com.br/ia/sugerir-ncm \
  -H "Content-Type: application/json" \
  -d '{"descricao": "notebook dell"}'

# 5. Testar site de vendas
curl https://www.emitemax.com.br

# 6. Testar cadastro e login
# Via navegador: https://www.emitemax.com.br/signup

# 7. Testar fluxo completo de assinatura
# Via navegador: https://www.emitemax.com.br/pricing

# 8. Verificar logs
aws logs tail /emitemax/api --follow
aws logs tail /emitemax/ia --follow

# 9. Verificar métricas
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --start-time 2025-12-15T00:00:00Z \
  --end-time 2025-12-15T23:59:59Z \
  --period 3600 \
  --statistics Sum

# 10. Teste de carga (opcional)
ab -n 1000 -c 10 https://api.emitemax.com.br/health
```

---

## 🔄 MANUTENÇÃO E ESCALABILIDADE {#manutencao}

### Auto Scaling

```bash
# Criar Launch Template
aws ec2 create-launch-template \
  --launch-template-name emitemax-api-lt \
  --version-description "v1" \
  --launch-template-data '{
    "ImageId": "ami-0c02fb55c47b5f0e8",
    "InstanceType": "t3.medium",
    "KeyName": "emitemax-key",
    "SecurityGroupIds": ["sg-api-xxxxxxxxx"],
    "UserData": "base64-encoded-user-data",
    "IamInstanceProfile": {"Name": "EmiteMaxEC2Role"}
  }'

# Criar Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name emitemax-api-asg \
  --launch-template LaunchTemplateName=emitemax-api-lt,Version='$Latest' \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 2 \
  --target-group-arns $TG_ARN \
  --vpc-zone-identifier "subnet-public-1a,subnet-public-1b" \
  --health-check-type ELB \
  --health-check-grace-period 300

# Criar políticas de scaling
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name emitemax-api-asg \
  --policy-name scale-up \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 70.0
  }'
```

### Deploy de Atualizações

```bash
# Script para deploy zero-downtime
cat > deploy.sh << 'EOF'
#!/bin/bash

echo "🚀 Iniciando deploy..."

# 1. Build da aplicação
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# 2. Executar migrations
python3 manage.py db upgrade

# 3. Reiniciar instâncias uma por vez
INSTANCES=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=emitemax-api" \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text)

for INSTANCE in $INSTANCES; do
  echo "Atualizando $INSTANCE..."
  
  # Drenar conexões do ALB
  aws elbv2 deregister-targets \
    --target-group-arn $TG_ARN \
    --targets Id=$INSTANCE
  
  # Aguardar drenagem (5 minutos)
  sleep 300
  
  # SSH e atualizar código
  ssh ec2-user@$INSTANCE << 'SSHEOF'
    cd /home/emitemax/app
    git pull
    source venv/bin/activate
    pip install -r requirements.txt
    sudo systemctl restart emitemax-api
SSHEOF
  
  # Registrar novamente no ALB
  aws elbv2 register-targets \
    --target-group-arn $TG_ARN \
    --targets Id=$INSTANCE
  
  # Aguardar health check
  sleep 60
  
  echo "✅ $INSTANCE atualizado"
done

echo "🎉 Deploy concluído!"
EOF

chmod +x deploy.sh
```

### Rotação de Logs

```bash
# Configurar logrotate nas instâncias EC2
cat > /etc/logrotate.d/emitemax << 'EOF'
/home/emitemax/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 emitemax emitemax
    sharedscripts
    postrotate
        systemctl reload emitemax-api
    endscript
}
EOF
```

---

## 📝 CHECKLIST FINAL

- [ ] VPC e Subnets criados
- [ ] Security Groups configurados
- [ ] RDS PostgreSQL em produção
- [ ] 2 instâncias EC2 para API
- [ ] 1 instância EC2 GPU para IA
- [ ] Application Load Balancer configurado
- [ ] Auto Scaling configurado
- [ ] Certificado SSL emitido e configurado
- [ ] Route 53 DNS configurado
- [ ] CloudFront distribuição criada
- [ ] Site de vendas no S3
- [ ] Stripe integrado
- [ ] Webhooks configurados
- [ ] CloudWatch alarms ativos
- [ ] Backups automáticos configurados
- [ ] Logs centralizados no CloudWatch
- [ ] Monitoramento 24/7 ativo
- [ ] Documentação atualizada
- [ ] Testes de carga realizados
- [ ] Plano de disaster recovery documentado

---

## 🆘 TROUBLESHOOTING

### Problemas Comuns:

1. **API não responde:**
   ```bash
   # Verificar status do serviço
   ssh ec2-user@<IP> "sudo systemctl status emitemax-api"
   
   # Verificar logs
   ssh ec2-user@<IP> "tail -f /home/emitemax/app/logs/error.log"
   ```

2. **IA lenta ou sem resposta:**
   ```bash
   # Verificar uso de GPU
   ssh ec2-user@<IP-IA> "nvidia-smi"
   
   # Verificar container
   ssh ec2-user@<IP-IA> "docker-compose logs -f"
   ```

3. **RDS com alta latência:**
   ```bash
   # Verificar conexões ativas
   aws rds describe-db-instances \
     --db-instance-identifier emitemax-db \
     --query 'DBInstances[0].DBInstanceStatus'
   
   # Aumentar instance class se necessário
   aws rds modify-db-instance \
     --db-instance-identifier emitemax-db \
     --db-instance-class db.t3.medium \
     --apply-immediately
   ```

4. **Site de vendas não carrega:**
   ```bash
   # Verificar CloudFront
   aws cloudfront list-distributions
   
   # Invalidar cache
   aws cloudfront create-invalidation \
     --distribution-id E1234567890ABC \
     --paths "/*"
   ```

---

## 📞 CONTATOS DE SUPORTE

- **AWS Support:** https://console.aws.amazon.com/support
- **Stripe Support:** https://support.stripe.com
- **Equipe Interna:** suporte@emitemax.com.br

---

**🎉 FIM DO GUIA DE DEPLOYMENT AWS**

**Última atualização:** 15 de dezembro de 2025  
**Versão:** 1.0

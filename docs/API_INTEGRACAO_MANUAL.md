# 📘 Manual de Integração - API EmiteMax

**Versão:** 2.0  
**Data:** Dezembro de 2024  
**Atualização:** 30 de Dezembro de 2024  
**Suporte:** contato@emitemax.com.br

---

## 📋 Índice

1. [Introdução](#introdução)
2. [Autenticação](#autenticação)
3. [Endpoints Disponíveis](#endpoints-disponíveis)
   - [NFe - Nota Fiscal Eletrônica](#endpoints-nfe)
   - [NFS-e - Nota Fiscal de Serviço](#emissão-de-nfs-e-nota-fiscal-de-serviço-eletrônica)
   - [NFC-e - Nota Fiscal do Consumidor](#emissão-de-nfc-e-nota-fiscal-do-consumidor-eletrônica)
4. [Comparação de Modelos](#comparação-nfe-vs-nfce-vs-nfse)
5. [Exemplos de Uso](#exemplos-de-uso)
6. [Códigos de Resposta](#códigos-de-resposta)
7. [Boas Práticas](#boas-práticas)
8. [Suporte](#suporte)

---

## 🎯 Introdução

A API de Integração EmiteMax permite que sistemas externos se conectem à plataforma para:

- **Emitir Notas Fiscais**: NFe (modelo 55), NFC-e (modelo 65) e NFS-e
- Consultar dados fiscais (CFOPs, NCMs, produtos, serviços)
- Buscar regras de tributação automaticamente (produtos e serviços)
- **Validar regras tributárias com IA** antes da emissão
- Obter próximo número de nota disponível
- Listar clientes e certificados digitais
- Consultar, cancelar e baixar XMLs/PDFs de notas
- Integrar com ERPs, e-commerces e outros sistemas

**Base URL:** `https://seu-servidor.com.br/api`

---

## 🔐 Autenticação

A API oferece **dois métodos de autenticação**:

### Método 1: API Key (Recomendado para Integrações)

A partir da versão 2.0, a API suporta autenticação via **API Key**, eliminando a necessidade de login por sessão.

**Vantagens:**
- ✅ Sem necessidade de gerenciar cookies/sessões
- ✅ Rate limiting configurável por chave
- ✅ Permissões granulares
- ✅ Whitelist de IPs
- ✅ Expiração automática
- ✅ Logs de uso detalhados

**Como obter uma API Key:**

1. Acesse o painel administrativo
2. Vá em "API Keys" no menu do cliente
3. Clique em "Nova API Key"
4. Configure nome, permissões e rate limit
5. **Copie a chave gerada (será mostrada apenas uma vez!)**

**Formato da chave:** `emx_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Como usar:**

```http
GET /api/v2/nfes
Authorization: Bearer emx_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Ou via query parameter (menos seguro):
```http
GET /api/v2/nfes?api_key=emx_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Método 2: Sessão (Flask-Login)

A API v1 utiliza **autenticação por sessão (cookies)** via Flask-Login. Para integração, você precisa:

### 1. Fazer Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "seu-email@empresa.com.br",
  "senha": "sua-senha"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Login realizado com sucesso",
  "redirect": "/cliente/dashboard"
}
```

### 2. Manter a Sessão

Após o login, o servidor retorna um cookie de sessão. Todas as requisições subsequentes devem incluir este cookie.

**Exemplo com cURL:**
```bash
# 1. Fazer login e salvar cookies
curl -c cookies.txt -X POST https://seu-servidor.com.br/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seu-email@empresa.com.br","senha":"sua-senha"}'

# 2. Usar cookies nas próximas requisições
curl -b cookies.txt https://seu-servidor.com.br/api/cfops
```

**Exemplo com Python (requests):**
```python
import requests

# Criar sessão para manter cookies
session = requests.Session()

# 1. Fazer login
login_response = session.post(
    'https://seu-servidor.com.br/auth/login',
    json={'email': 'seu-email@empresa.com.br', 'senha': 'sua-senha'}
)

# 2. Usar a mesma sessão para todas as requisições
cfops = session.get('https://seu-servidor.com.br/api/cfops')
print(cfops.json())
```

---

## 🔌 Endpoints Disponíveis

### 📍 API v1 (Autenticação por Sessão)

Endpoints legados que requerem login prévio. Base URL: `/api`

#### 1. Listar CFOPs

Retorna todos os Códigos Fiscais de Operações e Prestações cadastrados.

```http
GET /api/cfops
```

**Resposta:**
```json
[
  {
    "cfop_id": 1,
    "cfop": "5102",
    "descricao": "Venda de mercadoria adquirida ou recebida de terceiros"
  },
  {
    "cfop_id": 2,
    "cfop": "6102",
    "descricao": "Venda de mercadoria adquirida ou recebida de terceiros"
  }
]
```

---

### 2. Listar NCMs

Retorna todos os códigos NCM (Nomenclatura Comum do Mercosul).

```http
GET /api/ncms
```

**Resposta:**
```json
[
  {
    "ncm_id": 1,
    "codigo": "84715010",
    "descricao": "Unidades de processamento de pequena capacidade"
  },
  {
    "ncm_id": 2,
    "codigo": "84713000",
    "descricao": "Computadores portáteis"
  }
]
```

---

### 3. Listar Produtos do Cliente

Retorna todos os produtos cadastrados para um cliente específico.

```http
GET /api/produtos/cliente/{cliente_id}
```

**Parâmetros:**
- `cliente_id` (path, obrigatório): ID do cliente

**Resposta:**
```json
[
  {
    "produto_id": 1,
    "codigo_interno": "PROD001",
    "descricao": "Notebook Dell Inspiron 15",
    "preco_unitario_padrao": 3500.00,
    "unidade_comercial": "UN",
    "ncm_codigo": "84713000",
    "cfop": "5102"
  },
  {
    "produto_id": 2,
    "codigo_interno": "PROD002",
    "descricao": "Mouse Wireless Logitech",
    "preco_unitario_padrao": 89.90,
    "unidade_comercial": "UN",
    "ncm_codigo": "84716060",
    "cfop": "5102"
  }
]
```

**Códigos de Erro:**
- `403`: Acesso negado (você não tem permissão para ver este cliente)

---

### 4. Buscar Regra de Tributação

Busca a regra de tributação mais apropriada baseada nos critérios fornecidos. Este endpoint é essencial para calcular impostos automaticamente.

```http
POST /api/regras_tributacao/buscar
Content-Type: application/json
```

**Body:**
```json
{
  "cliente_id": 1,
  "regime_tributario_id": 1,
  "cfop_codigo": "5102",
  "ncm_codigo": "84713000",
  "uf_origem": "SP",
  "uf_destino": "RJ",
  "tipo_item": "PRODUTO"
}
```

**Parâmetros:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `cliente_id` | integer | Sim | ID do cliente |
| `regime_tributario_id` | integer | Sim | ID do regime tributário (1=Simples Nacional, 2=Real, etc) |
| `cfop_codigo` | string | Não | Código CFOP (ex: "5102") |
| `ncm_codigo` | string | Não | Código NCM (ex: "84713000") |
| `uf_origem` | string | Não | UF de origem (ex: "SP") |
| `uf_destino` | string | Não | UF de destino (ex: "RJ") |
| `tipo_item` | string | Não | "PRODUTO" ou "SERVICO" |

**Resposta de Sucesso:**
```json
{
  "sucesso": true,
  "regra": {
    "regra_tributacao_id": 42,
    "descricao_regra": "Simples Nacional - Operação Interna",
    "aliquota_icms": 7.0,
    "csosn_icms": "102",
    "cst_icms": null,
    "aliquota_pis": 0.0,
    "cst_pis": "49",
    "aliquota_cofins": 0.0,
    "cst_cofins": "49",
    "aliquota_ipi": 0.0,
    "cst_ipi": "99",
    "modalidade_bc_icms": "3",
    "reducao_bc_icms": 0.0,
    "motivo_desoneracao_icms": null,
    "valor_desoneracao_icms": 0.0
  }
}
```

**Resposta de Erro (nenhuma regra encontrada):**
```json
{
  "sucesso": false,
  "message": "Nenhuma regra de tributação encontrada para os critérios fornecidos."
}
```

---

### 5. Listar Clientes

Retorna a lista de clientes que o usuário logado tem acesso.

```http
GET /api/clientes
```

**Resposta:**
```json
[
  {
    "cliente_id": 1,
    "razao_social": "EMPRESA EXEMPLO LTDA",
    "cnpj": "12345678000195",
    "uf": "SP",
    "ativo": true
  },
  {
    "cliente_id": 2,
    "razao_social": "COMERCIO DE PRODUTOS LTDA",
    "cnpj": "98765432000123",
    "uf": "RJ",
    "ativo": true
  }
]
```

---

### 6. Obter Próximo Número de NFe

Retorna o próximo número disponível de NFe para um cliente, considerando modelo e série.

```http
GET /api/nfe/proximo-numero?cliente_id=1&modelo=55&serie=1
```

**Parâmetros (Query String):**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `cliente_id` | integer | Sim | ID do cliente |
| `modelo` | string | Não | Modelo da NFe (padrão: "55") |
| `serie` | integer | Não | Série da NFe (padrão: 1) |

**Resposta:**
```json
{
  "success": true,
  "proximo_numero": 123,
  "cliente_id": 1,
  "modelo": "55",
  "serie": 1
}
```

**Códigos de Erro:**
- `400`: cliente_id não fornecido
- `403`: Acesso negado

---

### 📍 API v2 (Autenticação por API Key) ⭐ NOVO

Novos endpoints com autenticação via API Key. Base URL: `/api/v2`

Todos os endpoints v2 requerem header de autenticação:
```
Authorization: Bearer emx_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

#### 1. Emitir NFe

**A funcionalidade mais esperada!** Emita NFes diretamente pela API.

```http
POST /api/v2/nfe/emitir
Authorization: Bearer sua_api_key
Content-Type: application/json
```

**Body:**
```json
{
  "destinatario": {
    "cpf_cnpj": "12345678000195",
    "nome": "EMPRESA DESTINO LTDA",
    "endereco": "Av. Paulista",
    "numero": "1000",
    "bairro": "Bela Vista",
    "cidade": "São Paulo",
    "uf": "SP",
    "cep": "01310100",
    "email": "contato@empresadestino.com.br"
  },
  "itens": [
    {
      "produto_id": 1,
      "quantidade": 2,
      "valor_unitario": 150.00
    },
    {
      "descricao": "Produto Customizado",
      "quantidade": 1,
      "valor_unitario": 50.00,
      "ncm": "84713000",
      "cfop": "5102",
      "unidade": "UN"
    }
  ],
  "natureza_operacao": "Venda de Mercadoria",
  "informacoes_adicionais": "Pedido 12345",
  "enviar_email": true
}
```

**Resposta de Sucesso (201):**
```json
{
  "success": true,
  "message": "NFe emitida e autorizada com sucesso",
  "nfe": {
    "nfe_id": 12345,
    "numero": 123,
    "serie": 1,
    "chave_acesso": "35240612345678000195550010000001231234567890",
    "protocolo": "135240012345678",
    "status": "AUTORIZADA",
    "valor_total": 350.00
  }
}
```

**Resposta de Erro (422):**
```json
{
  "error": "NFe rejeitada pela SEFAZ",
  "message": "539: Duplicidade de NF-e",
  "nfe_id": 12345
}
```

---

#### 2. Listar NFes

```http
GET /api/v2/nfes?limit=50&offset=0&status=AUTORIZADA
Authorization: Bearer sua_api_key
```

**Parâmetros:**
- `limit` (opcional): Número de registros (padrão: 50)
- `offset` (opcional): Paginação (padrão: 0)
- `status` (opcional): Filtrar por status (AUTORIZADA, CANCELADA, etc)

**Resposta:**
```json
{
  "success": true,
  "total": 1250,
  "limit": 50,
  "offset": 0,
  "nfes": [
    {
      "nfe_id": 123,
      "numero": 456,
      "serie": 1,
      "chave_acesso": "35240...",
      "status": "AUTORIZADA",
      "valor_total": 1500.50,
      "data_emissao": "2024-12-18T10:30:00"
    }
  ]
}
```

---

#### 3. Consultar NFe Específica

```http
GET /api/v2/nfe/{nfe_id}
Authorization: Bearer sua_api_key
```

**Resposta:**
```json
{
  "success": true,
  "nfe": {
    "nfe_id": 123,
    "numero": 456,
    "serie": 1,
    "chave_acesso": "35240...",
    "status": "AUTORIZADA",
    "valor_total": 1500.50,
    "destinatario": {
      "nome": "CLIENTE LTDA",
      "cnpj": "12345678000195"
    },
    "itens": [...]
  }
}
```

---

#### 4. Baixar XML da NFe

```http
GET /api/v2/nfe/{nfe_id}/xml
Authorization: Bearer sua_api_key
```

**Resposta:** XML da NFe (Content-Type: application/xml)

---

#### 5. Cancelar NFe

```http
POST /api/v2/nfe/{nfe_id}/cancelar
Authorization: Bearer sua_api_key
Content-Type: application/json

{
  "justificativa": "Cancelamento solicitado pelo cliente devido a erro no pedido"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "NFe cancelada com sucesso",
  "protocolo": "135240012345679"
}
```

---

#### 6. Gerenciar API Keys (via API)

**Listar suas API Keys:**
```http
GET /api/v2/keys
Authorization: Bearer sua_api_key_admin
```

**Estatísticas de uso:**
```http
GET /api/v2/keys/stats
Authorization: Bearer sua_api_key_admin
```

Retorna:
```json
{
  "success": true,
  "period": "30 days",
  "total_requests": 1523,
  "endpoints": {
    "/api/v2/nfe/emitir": 245,
    "/api/v2/nfes": 1120,
    "/api/v2/nfe/123": 158
  },
  "status_codes": {
    "200": 1450,
    "201": 245,
    "400": 15,
    "429": 13
  },
  "average_response_time_ms": 156
}
```

---

#### 7. Gerenciar Webhooks

**Criar webhook:**
```http
POST /api/v2/webhooks
Authorization: Bearer sua_api_key_admin
Content-Type: application/json

{
  "url": "https://seu-servidor.com/webhook",
  "eventos": ["nfe.autorizada", "nfe.cancelada"],
  "secret": "seu_secret_para_hmac"
}
```

**Listar webhooks:**
```http
GET /api/v2/webhooks
Authorization: Bearer sua_api_key_admin
```

**Excluir webhook:**
```http
DELETE /api/v2/webhooks/{webhook_id}
Authorization: Bearer sua_api_key_admin
```

---

### 🔔 Webhooks

Os webhooks permitem receber notificações em tempo real sobre eventos.

**Eventos Disponíveis:**
- `nfe.autorizada` - NFe foi autorizada pela SEFAZ
- `nfe.rejeitada` - NFe foi rejeitada pela SEFAZ
- `nfe.cancelada` - NFe foi cancelada
- `nfe.inutilizada` - Numeração foi inutilizada
- `nfce.autorizada` - NFCe autorizada
- `nfce.rejeitada` - NFCe rejeitada
- `nfce.cancelada` - NFCe cancelada
- `nfce.inutilizada` - Numeração NFCe inutilizada
- `nfse.autorizada` - NFS-e foi autorizada
- `nfse.rejeitada` - NFS-e foi rejeitada
- `nfse.cancelada` - NFS-e foi cancelada
- `nfse.erro` - Erro na emissão da NFS-e

**Formato do Payload:**
```json
{
  "evento": "nfe.autorizada",
  "timestamp": "2024-12-18T10:30:00",
  "webhook_id": 5,
  "nfe_id": 123,
  "numero": 456,
  "serie": 1,
  "chave_acesso": "35240...",
  "valor_total": 1500.50,
  "destinatario": "CLIENTE LTDA"
}
```

**Headers Enviados:**
```
Content-Type: application/json
User-Agent: EmiteMax-Webhook/1.0
X-EmiteMax-Event: nfe.autorizada
X-EmiteMax-Delivery: 12345
X-EmiteMax-Signature: sha256=abc123... (HMAC-SHA256 do payload)
```

**Verificar Assinatura (Segurança):**
```python
import hmac
import hashlib

def verify_webhook(payload_str, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    received = signature.replace('sha256=', '')
    return hmac.compare_digest(expected, received)

# No seu endpoint de webhook:
signature = request.headers.get('X-EmiteMax-Signature')
payload = request.get_data(as_text=True)

if verify_webhook(payload, signature, 'seu_secret'):
    # Assinatura válida
    pass
else:
    # Assinatura inválida - possível ataque
    return 403
```

**Retry Policy:**
- 1ª tentativa: Imediata
- 2ª tentativa: Após 1 minuto
- 3ª tentativa: Após 5 minutos
- 4ª tentativa: Após 15 minutos
- Após 4 falhas: Marcado como failed

**Resposta Esperada:**
Seu endpoint deve responder com status HTTP 2xx (200-299) em até 30 segundos.

---

## � Emissão de NFS-e (Nota Fiscal de Serviço Eletrônica)

A NFS-e é utilizada para prestação de serviços e segue as regras municipais. Diferente da NFe, ela não utiliza CFOP ou NCM, mas sim códigos de serviço LC 116 e NBS.

### 1. Emitir NFS-e

```http
POST /admin/nfse/emitir
Authorization: Bearer sua_api_key
Content-Type: application/json
```

**Body:**
```json
{
  "cliente_id": 1,
  "tomador": {
    "cpf_cnpj": "12345678000195",
    "razao_social": "EMPRESA TOMADORA LTDA",
    "email": "contato@empresa.com.br",
    "telefone": "1734567890",
    "endereco": {
      "logradouro": "Rua Principal",
      "numero": "100",
      "complemento": "Sala 5",
      "bairro": "Centro",
      "cidade": "São José do Rio Preto",
      "uf": "SP",
      "cep": "15015000"
    }
  },
  "servico": {
    "codigo_servico_lc116": "01.07",
    "codigo_nbs": "1.0107.10.00",
    "descricao": "Desenvolvimento de sistema web personalizado",
    "aliquota_iss": 5.0,
    "valor_servico": 5000.00,
    "valor_deducoes": 0.0,
    "valor_pis": 0.0,
    "valor_cofins": 0.0,
    "valor_inss": 0.0,
    "valor_ir": 0.0,
    "valor_csll": 0.0,
    "iss_retido": false,
    "regime_tributario": "SIMPLES_NACIONAL"
  },
  "discriminacao": "Desenvolvimento de sistema web customizado conforme escopo do contrato 2024/001",
  "natureza_operacao": "TRIBUTACAO_MUNICIPIO",
  "enviar_email": true
}
```

**Parâmetros Principais:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `cliente_id` | integer | Sim | ID do cliente emissor |
| `tomador.cpf_cnpj` | string | Sim | CPF ou CNPJ do tomador |
| `tomador.razao_social` | string | Sim | Nome/Razão social do tomador |
| `tomador.email` | string | Não | Email para envio da NFS-e |
| `servico.codigo_servico_lc116` | string | Sim | Código do serviço LC 116 (ex: "01.07") |
| `servico.codigo_nbs` | string | Sim | Código NBS (ex: "1.0107.10.00") |
| `servico.descricao` | string | Sim | Descrição do serviço |
| `servico.aliquota_iss` | decimal | Sim | Alíquota do ISS (0.00 a 5.00) |
| `servico.valor_servico` | decimal | Sim | Valor total do serviço |
| `servico.iss_retido` | boolean | Não | Se ISS é retido na fonte (padrão: false) |
| `servico.regime_tributario` | string | Sim | SIMPLES_NACIONAL, LUCRO_PRESUMIDO ou LUCRO_REAL |
| `discriminacao` | string | Sim | Discriminação detalhada do serviço |

**Resposta de Sucesso (201):**
```json
{
  "success": true,
  "message": "NFS-e emitida com sucesso",
  "nfse": {
    "nfse_id": 456,
    "numero_rps": 1001,
    "numero_nfse": 789,
    "codigo_verificacao": "ABC12345",
    "protocolo": "2024000012345",
    "status": "AUTORIZADA",
    "data_emissao": "2024-12-30T10:30:00",
    "valor_total": 5000.00,
    "valor_iss": 250.00,
    "link_visualizacao": "https://nfse.prefeitura.sp.gov.br/consulta/789/ABC12345"
  }
}
```

**Resposta de Erro (422):**
```json
{
  "error": "NFS-e rejeitada",
  "message": "Código de serviço inválido para o município",
  "codigo_erro": "E105",
  "nfse_id": null
}
```

---

### 2. Consultar NFS-e

```http
GET /admin/nfse/{nfse_id}
Authorization: Bearer sua_api_key
```

**Resposta:**
```json
{
  "success": true,
  "nfse": {
    "nfse_id": 456,
    "numero_rps": 1001,
    "numero_nfse": 789,
    "status": "AUTORIZADA",
    "data_emissao": "2024-12-30T10:30:00",
    "tomador": {
      "cpf_cnpj": "12345678000195",
      "razao_social": "EMPRESA TOMADORA LTDA"
    },
    "valor_total": 5000.00,
    "valor_iss": 250.00,
    "protocolo": "2024000012345"
  }
}
```

---

### 3. Cancelar NFS-e

```http
POST /admin/nfse/{nfse_id}/cancelar
Authorization: Bearer sua_api_key
Content-Type: application/json

{
  "motivo": "Erro no valor do serviço - será reemitida com valor correto"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "NFS-e cancelada com sucesso",
  "protocolo_cancelamento": "2024000012346"
}
```

---

### 4. Listar NFS-e

```http
GET /admin/nfse/list?cliente_id=1&limit=50&offset=0
Authorization: Bearer sua_api_key
```

**Parâmetros:**
- `cliente_id` (obrigatório): ID do cliente
- `limit` (opcional): Registros por página (padrão: 50)
- `offset` (opcional): Paginação (padrão: 0)
- `status` (opcional): AUTORIZADA, CANCELADA, ERRO

**Resposta:**
```json
{
  "success": true,
  "total": 125,
  "nfses": [
    {
      "nfse_id": 456,
      "numero_rps": 1001,
      "numero_nfse": 789,
      "status": "AUTORIZADA",
      "data_emissao": "2024-12-30T10:30:00",
      "tomador_razao_social": "EMPRESA TOMADORA LTDA",
      "valor_total": 5000.00
    }
  ]
}
```

---

### 5. Baixar PDF da NFS-e

```http
GET /admin/nfse/{nfse_id}/pdf
Authorization: Bearer sua_api_key
```

**Resposta:** PDF da NFS-e (Content-Type: application/pdf)

---

### 6. Validar Regra de Serviço com IA

Antes de emitir, você pode validar se a regra tributária está correta:

```http
POST /api/validar-regra-servico-ia
Authorization: Bearer sua_api_key
Content-Type: application/json

{
  "tipo": "servico",
  "codigo_servico_lc116": "01.07",
  "codigo_nbs": "1.0107.10.00",
  "descricao_servico": "Desenvolvimento de sistema web",
  "aliquota_iss": 5.0,
  "iss_retido": false,
  "cst_ibs_cbs": "00",
  "regime_tributario": "SIMPLES_NACIONAL"
}
```

**Resposta:**
```json
{
  "valido": true,
  "confianca": 0.95,
  "sugestoes": [],
  "erros": [],
  "explicacao": "Configuração correta para prestação de serviços de TI no Simples Nacional"
}
```

---

## 🛒 Emissão de NFC-e (Nota Fiscal do Consumidor Eletrônica)

A NFC-e (modelo 65) é usada para vendas ao consumidor final no varejo. Similar à NFe, mas simplificada e com QR Code obrigatório.

### 1. Emitir NFC-e

```http
POST /admin/nfce/emitir
Authorization: Bearer sua_api_key
Content-Type: application/json
```

**Body:**
```json
{
  "cliente_id": 1,
  "modelo": "65",
  "serie": 1,
  "consumidor": {
    "tipo": "NAO_IDENTIFICADO",
    "cpf_cnpj": null,
    "nome": null,
    "email": null
  },
  "produtos": [
    {
      "codigo": "PROD001",
      "descricao": "Mouse Wireless",
      "quantidade": 1,
      "valor_unitario": 89.90,
      "ncm": "84716060",
      "cfop": "5102",
      "unidade": "UN",
      "cst_icms": "102",
      "aliquota_icms": 0.0
    },
    {
      "codigo": "PROD002",
      "descricao": "Teclado Mecânico",
      "quantidade": 1,
      "valor_unitario": 299.90,
      "ncm": "84716060",
      "cfop": "5102",
      "unidade": "UN",
      "cst_icms": "102",
      "aliquota_icms": 0.0
    }
  ],
  "pagamento": {
    "forma": "CARTAO_CREDITO",
    "valor_pago": 389.80,
    "troco": 0.0
  },
  "desconto_total": 0.0,
  "frete": 0.0,
  "indicador_presenca": "PRESENCIAL",
  "informacoes_adicionais": "Venda balcão",
  "enviar_email": false
}
```

**Parâmetros Principais:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `cliente_id` | integer | Sim | ID do cliente emissor |
| `modelo` | string | Sim | "65" para NFC-e |
| `serie` | integer | Não | Série da nota (padrão: 1) |
| `consumidor.tipo` | string | Sim | NAO_IDENTIFICADO, CPF ou CNPJ |
| `consumidor.cpf_cnpj` | string | Condicional | Obrigatório se tipo != NAO_IDENTIFICADO |
| `consumidor.nome` | string | Não | Nome do consumidor |
| `consumidor.email` | string | Não | Email para envio da NFC-e |
| `produtos` | array | Sim | Lista de produtos (mínimo 1) |
| `produtos[].codigo` | string | Sim | Código interno do produto |
| `produtos[].descricao` | string | Sim | Descrição do produto |
| `produtos[].quantidade` | decimal | Sim | Quantidade |
| `produtos[].valor_unitario` | decimal | Sim | Valor unitário |
| `produtos[].ncm` | string | Sim | Código NCM |
| `produtos[].cfop` | string | Sim | CFOP (geralmente 5102) |
| `pagamento.forma` | string | Sim | DINHEIRO, CARTAO_CREDITO, CARTAO_DEBITO, PIX, etc |
| `pagamento.valor_pago` | decimal | Sim | Valor efetivamente pago |
| `pagamento.troco` | decimal | Não | Troco (se houver) |
| `indicador_presenca` | string | Sim | PRESENCIAL, INTERNET, TELEFONE |

**Resposta de Sucesso (201):**
```json
{
  "success": true,
  "message": "NFC-e autorizada com sucesso",
  "nfce": {
    "nfce_id": 789,
    "numero": 1523,
    "serie": 1,
    "chave_acesso": "35241212345678000195650010000015231234567890",
    "protocolo": "135241012345678",
    "status": "AUTORIZADA",
    "data_autorizacao": "2024-12-30T14:25:30",
    "valor_total": 389.80,
    "qrcode": "https://www.fazenda.sp.gov.br/nfce/qrcode?p=35241212345678000195650010000015231234567890|2|1|1|ABC123DEF456",
    "link_consulta": "https://www.fazenda.sp.gov.br/nfce/consulta?chave=35241212345678000195650010000015231234567890"
  }
}
```

**Resposta de Erro (422):**
```json
{
  "error": "NFC-e rejeitada pela SEFAZ",
  "message": "539: Duplicidade de NFC-e",
  "codigo_erro": "539",
  "nfce_id": 789
}
```

---

### 2. Consultar NFC-e

```http
GET /admin/nfce/{nfce_id}
Authorization: Bearer sua_api_key
```

**Resposta:**
```json
{
  "success": true,
  "nfce": {
    "nfce_id": 789,
    "numero": 1523,
    "serie": 1,
    "modelo": "65",
    "chave_acesso": "35241212345678000195650010000015231234567890",
    "status": "AUTORIZADA",
    "data_emissao": "2024-12-30T14:25:30",
    "valor_total": 389.80,
    "qrcode": "https://www.fazenda.sp.gov.br/nfce/qrcode?p=...",
    "produtos": [
      {
        "descricao": "Mouse Wireless",
        "quantidade": 1,
        "valor_total": 89.90
      }
    ]
  }
}
```

---

### 3. Cancelar NFC-e

```http
POST /admin/nfce/{nfce_id}/cancelar
Authorization: Bearer sua_api_key
Content-Type: application/json

{
  "justificativa": "Erro no valor do produto - cliente solicitou cancelamento"
}
```

**Requisitos para Cancelamento:**
- NFC-e deve estar AUTORIZADA
- Prazo: até 24 horas após emissão (varia por estado)
- Justificativa: mínimo 15 caracteres

**Resposta:**
```json
{
  "success": true,
  "message": "NFC-e cancelada com sucesso",
  "protocolo": "135241012345679",
  "data_cancelamento": "2024-12-30T15:10:00"
}
```

---

### 4. Listar NFC-e

```http
GET /admin/nfce/list?cliente_id=1&limit=100&data_inicio=2024-12-01
Authorization: Bearer sua_api_key
```

**Parâmetros:**
- `cliente_id` (obrigatório): ID do cliente
- `limit` (opcional): Registros por página (padrão: 50, máximo: 500)
- `offset` (opcional): Paginação (padrão: 0)
- `status` (opcional): AUTORIZADA, CANCELADA, REJEITADA
- `data_inicio` (opcional): Filtro por data (YYYY-MM-DD)
- `data_fim` (opcional): Filtro por data (YYYY-MM-DD)

**Resposta:**
```json
{
  "success": true,
  "total": 523,
  "nfces": [
    {
      "nfce_id": 789,
      "numero": 1523,
      "serie": 1,
      "chave_acesso": "35241212345678000195650010000015231234567890",
      "status": "AUTORIZADA",
      "data_emissao": "2024-12-30T14:25:30",
      "valor_total": 389.80,
      "consumidor": "CPF: 123.456.789-00"
    }
  ]
}
```

---

### 5. Baixar XML da NFC-e

```http
GET /admin/nfce/{nfce_id}/xml
Authorization: Bearer sua_api_key
```

**Resposta:** XML da NFC-e (Content-Type: application/xml)

---

### 6. Baixar PDF da NFC-e (DANFE Simplificado)

```http
GET /admin/nfce/{nfce_id}/pdf
Authorization: Bearer sua_api_key
```

**Resposta:** PDF do DANFE simplificado com QR Code (Content-Type: application/pdf)

---

### 7. Inutilizar Numeração NFC-e

Quando houver quebra de sequência na numeração:

```http
POST /admin/nfce/inutilizar
Authorization: Bearer sua_api_key
Content-Type: application/json

{
  "cliente_id": 1,
  "serie": 1,
  "numero_inicial": 1520,
  "numero_final": 1522,
  "justificativa": "Numeração não utilizada por erro no sistema"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Numeração inutilizada com sucesso",
  "protocolo": "135241012345680",
  "numeros_inutilizados": [1520, 1521, 1522]
}
```

---

## 📊 Comparação: NFe vs NFCe vs NFSe

| Característica | NF-e (Modelo 55) | NFC-e (Modelo 65) | NFS-e |
|---------------|------------------|-------------------|--------|
| **Tipo** | Produto/Mercadoria | Produto/Mercadoria | Serviço |
| **Destinatário** | Pessoa Jurídica principalmente | Consumidor final | Pessoa Física ou Jurídica |
| **CFOP** | Obrigatório | Obrigatório | Não utiliza |
| **NCM** | Obrigatório | Obrigatório | Não utiliza |
| **Código Serviço LC 116** | Não utiliza | Não utiliza | Obrigatório |
| **Código NBS** | Não utiliza | Não utiliza | Obrigatório |
| **ICMS** | Sim | Sim | Não |
| **ISS** | Não | Não | Sim |
| **QR Code** | Não obrigatório | Obrigatório | Pode ter (depende município) |
| **DANFE** | Completo (A4) | Simplificado (bobina) | Recibo Provisório |
| **Contingência** | Permitida | Offline (SAT/MFe em alguns estados) | Depende do município |
| **Envio Email** | Opcional | Opcional | Opcional |
| **Prazo Cancelamento** | Até 24h (varia) | Até 24h (varia) | Varia por município |
| **Uso Principal** | Operações B2B | Varejo, PDV | Prestação de serviços |

---

## �💡 Exemplos de Uso

### Exemplo 1: API v2 com API Key (Python) ⭐ RECOMENDADO

```python
import requests
from typing import Optional, Dict, Any, List

class EmiteMaxAPIv2:
    """Cliente para API v2 do EmiteMax (autenticação por API Key)"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def _request(self, method: str, endpoint: str, **kwargs):
        """Faz requisição HTTP"""
        url = f'{self.base_url}{endpoint}'
        kwargs['headers'] = self.headers
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    
    def emitir_nfe(
        self,
        destinatario: Dict,
        itens: List[Dict],
        natureza_operacao: str = 'Venda',
        informacoes_adicionais: Optional[str] = None,
        enviar_email: bool = True
    ) -> Dict:
        """
        Emite uma NFe
        
        Args:
            destinatario: Dados do destinatário
            itens: Lista de itens da nota
            natureza_operacao: Natureza da operação
            informacoes_adicionais: Observações
            enviar_email: Se deve enviar email
            
        Returns:
            Dict com dados da NFe emitida
        """
        payload = {
            'destinatario': destinatario,
            'itens': itens,
            'natureza_operacao': natureza_operacao,
            'informacoes_adicionais': informacoes_adicionais,
            'enviar_email': enviar_email
        }
        
        response = self._request('POST', '/api/v2/nfe/emitir', json=payload)
        return response.json()
    
    def listar_nfes(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Dict:
        """Lista NFes"""
        params = {'limit': limit, 'offset': offset}
        if status:
            params['status'] = status
        
        response = self._request('GET', '/api/v2/nfes', params=params)
        return response.json()
    
    def consultar_nfe(self, nfe_id: int) -> Dict:
        """Consulta uma NFe específica"""
        response = self._request('GET', f'/api/v2/nfe/{nfe_id}')
        return response.json()
    
    def baixar_xml(self, nfe_id: int) -> str:
        """Baixa XML da NFe"""
        response = self._request('GET', f'/api/v2/nfe/{nfe_id}/xml')
        return response.text
    
    def cancelar_nfe(self, nfe_id: int, justificativa: str) -> Dict:
        """Cancela uma NFe"""
        response = self._request(
            'POST',
            f'/api/v2/nfe/{nfe_id}/cancelar',
            json={'justificativa': justificativa}
        )
        return response.json()
    
    def criar_webhook(
        self,
        url: str,
        eventos: List[str],
        secret: Optional[str] = None
    ) -> Dict:
        """Cria um webhook"""
        payload = {'url': url, 'eventos': eventos}
        if secret:
            payload['secret'] = secret
        
        response = self._request('POST', '/api/v2/webhooks', json=payload)
        return response.json()
    
    def estatisticas_uso(self) -> Dict:
        """Obtém estatísticas de uso da API"""
        response = self._request('GET', '/api/v2/keys/stats')
        return response.json()
    
    # Métodos NFS-e
    def emitir_nfse(
        self,
        cliente_id: int,
        tomador: Dict,
        servico: Dict,
        discriminacao: str,
        enviar_email: bool = True
    ) -> Dict:
        """
        Emite uma NFS-e (Nota Fiscal de Serviço)
        
        Args:
            cliente_id: ID do cliente emissor
            tomador: Dados do tomador do serviço
            servico: Dados do serviço prestado
            discriminacao: Descrição detalhada do serviço
            enviar_email: Se deve enviar email
            
        Returns:
            Dict com dados da NFS-e emitida
        """
        payload = {
            'cliente_id': cliente_id,
            'tomador': tomador,
            'servico': servico,
            'discriminacao': discriminacao,
            'natureza_operacao': 'TRIBUTACAO_MUNICIPIO',
            'enviar_email': enviar_email
        }
        
        response = self._request('POST', '/admin/nfse/emitir', json=payload)
        return response.json()
    
    def consultar_nfse(self, nfse_id: int) -> Dict:
        """Consulta uma NFS-e específica"""
        response = self._request('GET', f'/admin/nfse/{nfse_id}')
        return response.json()
    
    def cancelar_nfse(self, nfse_id: int, motivo: str) -> Dict:
        """Cancela uma NFS-e"""
        response = self._request(
            'POST',
            f'/admin/nfse/{nfse_id}/cancelar',
            json={'motivo': motivo}
        )
        return response.json()
    
    def listar_nfses(
        self,
        cliente_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Dict:
        """Lista NFS-es"""
        params = {'cliente_id': cliente_id, 'limit': limit, 'offset': offset}
        if status:
            params['status'] = status
        
        response = self._request('GET', '/admin/nfse/list', params=params)
        return response.json()
    
    def baixar_pdf_nfse(self, nfse_id: int) -> bytes:
        """Baixa PDF da NFS-e"""
        response = self._request('GET', f'/admin/nfse/{nfse_id}/pdf')
        return response.content
    
    def validar_regra_servico_ia(self, dados_servico: Dict) -> Dict:
        """Valida regra tributária de serviço usando IA"""
        response = self._request('POST', '/api/validar-regra-servico-ia', json=dados_servico)
        return response.json()
    
    # Métodos NFC-e
    def emitir_nfce(
        self,
        cliente_id: int,
        produtos: List[Dict],
        pagamento: Dict,
        consumidor: Optional[Dict] = None,
        serie: int = 1,
        enviar_email: bool = False
    ) -> Dict:
        """
        Emite uma NFC-e (Nota Fiscal do Consumidor)
        
        Args:
            cliente_id: ID do cliente emissor
            produtos: Lista de produtos vendidos
            pagamento: Dados do pagamento
            consumidor: Dados do consumidor (opcional para não identificado)
            serie: Série da nota (padrão: 1)
            enviar_email: Se deve enviar email
            
        Returns:
            Dict com dados da NFC-e emitida
        """
        if consumidor is None:
            consumidor = {'tipo': 'NAO_IDENTIFICADO'}
        
        payload = {
            'cliente_id': cliente_id,
            'modelo': '65',
            'serie': serie,
            'consumidor': consumidor,
            'produtos': produtos,
            'pagamento': pagamento,
            'indicador_presenca': 'PRESENCIAL',
            'enviar_email': enviar_email
        }
        
        response = self._request('POST', '/admin/nfce/emitir', json=payload)
        return response.json()
    
    def consultar_nfce(self, nfce_id: int) -> Dict:
        """Consulta uma NFC-e específica"""
        response = self._request('GET', f'/admin/nfce/{nfce_id}')
        return response.json()
    
    def cancelar_nfce(self, nfce_id: int, justificativa: str) -> Dict:
        """Cancela uma NFC-e"""
        response = self._request(
            'POST',
            f'/admin/nfce/{nfce_id}/cancelar',
            json={'justificativa': justificativa}
        )
        return response.json()
    
    def listar_nfces(
        self,
        cliente_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Dict:
        """Lista NFC-es"""
        params = {'cliente_id': cliente_id, 'limit': limit, 'offset': offset}
        if status:
            params['status'] = status
        
        response = self._request('GET', '/admin/nfce/list', params=params)
        return response.json()
    
    def baixar_xml_nfce(self, nfce_id: int) -> str:
        """Baixa XML da NFC-e"""
        response = self._request('GET', f'/admin/nfce/{nfce_id}/xml')
        return response.text
    
    def baixar_pdf_nfce(self, nfce_id: int) -> bytes:
        """Baixa PDF (DANFE) da NFC-e"""
        response = self._request('GET', f'/admin/nfce/{nfce_id}/pdf')
        return response.content
    
    def inutilizar_nfce(
        self,
        cliente_id: int,
        serie: int,
        numero_inicial: int,
        numero_final: int,
        justificativa: str
    ) -> Dict:
        """Inutiliza numeração de NFC-e"""
        payload = {
            'cliente_id': cliente_id,
            'serie': serie,
            'numero_inicial': numero_inicial,
            'numero_final': numero_final,
            'justificativa': justificativa
        }
        
        response = self._request('POST', '/admin/nfce/inutilizar', json=payload)
        return response.json()

# Uso
if __name__ == '__main__':
    # Inicializar cliente
    api = EmiteMaxAPIv2(
        base_url='https://seu-servidor.com.br',
        api_key='emx_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    )
    
    # Emitir NFe
    resultado = api.emitir_nfe(
        destinatario={
            'cpf_cnpj': '12345678000195',
            'nome': 'CLIENTE TESTE LTDA',
            'endereco': 'Rua Teste',
            'numero': '123',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'uf': 'SP',
            'cep': '01234567',
            'email': 'contato@clienteteste.com.br'
        },
        itens=[
            {
                'produto_id': 1,
                'quantidade': 2,
                'valor_unitario': 100.00
            }
        ],
        natureza_operacao='Venda de Mercadoria',
        informacoes_adicionais='Pedido #12345'
    )
    
    if resultado['success']:
        print(f"✅ NFe {resultado['nfe']['numero']} emitida!")
        print(f"Chave: {resultado['nfe']['chave_acesso']}")
        
        # Baixar XML
        xml = api.baixar_xml(resultado['nfe']['nfe_id'])
        with open(f"nfe_{resultado['nfe']['numero']}.xml", 'w') as f:
            f.write(xml)
    
    # === Exemplo Emissão NFS-e ===
    print("\n📋 Emitindo NFS-e...")
    resultado_nfse = api.emitir_nfse(
        cliente_id=1,
        tomador={
            'cpf_cnpj': '12345678000195',
            'razao_social': 'EMPRESA TOMADORA LTDA',
            'email': 'contato@empresa.com.br',
            'telefone': '1734567890',
            'endereco': {
                'logradouro': 'Rua Principal',
                'numero': '100',
                'bairro': 'Centro',
                'cidade': 'São José do Rio Preto',
                'uf': 'SP',
                'cep': '15015000'
            }
        },
        servico={
            'codigo_servico_lc116': '01.07',
            'codigo_nbs': '1.0107.10.00',
            'descricao': 'Desenvolvimento de sistema web',
            'aliquota_iss': 5.0,
            'valor_servico': 5000.00,
            'iss_retido': False,
            'regime_tributario': 'SIMPLES_NACIONAL'
        },
        discriminacao='Desenvolvimento de sistema web conforme contrato 2024/001',
        enviar_email=True
    )
    
    if resultado_nfse['success']:
        print(f"✅ NFS-e {resultado_nfse['nfse']['numero_nfse']} emitida!")
        print(f"RPS: {resultado_nfse['nfse']['numero_rps']}")
        print(f"ISS: R$ {resultado_nfse['nfse']['valor_iss']:.2f}")
        
        # Baixar PDF da NFS-e
        pdf = api.baixar_pdf_nfse(resultado_nfse['nfse']['nfse_id'])
        with open(f"nfse_{resultado_nfse['nfse']['numero_nfse']}.pdf", 'wb') as f:
            f.write(pdf)
    
    # === Exemplo Emissão NFC-e ===
    print("\n🛒 Emitindo NFC-e...")
    resultado_nfce = api.emitir_nfce(
        cliente_id=1,
        produtos=[
            {
                'codigo': 'PROD001',
                'descricao': 'Mouse Wireless',
                'quantidade': 1,
                'valor_unitario': 89.90,
                'ncm': '84716060',
                'cfop': '5102',
                'unidade': 'UN',
                'cst_icms': '102',
                'aliquota_icms': 0.0
            },
            {
                'codigo': 'PROD002',
                'descricao': 'Teclado Mecânico',
                'quantidade': 1,
                'valor_unitario': 299.90,
                'ncm': '84716060',
                'cfop': '5102',
                'unidade': 'UN',
                'cst_icms': '102',
                'aliquota_icms': 0.0
            }
        ],
        pagamento={
            'forma': 'CARTAO_CREDITO',
            'valor_pago': 389.80,
            'troco': 0.0
        },
        consumidor={
            'tipo': 'CPF',
            'cpf_cnpj': '12345678900',
            'nome': 'João da Silva',
            'email': 'joao@email.com'
        },
        serie=1,
        enviar_email=True
    )
    
    if resultado_nfce['success']:
        print(f"✅ NFC-e {resultado_nfce['nfce']['numero']} autorizada!")
        print(f"QR Code: {resultado_nfce['nfce']['qrcode']}")
        print(f"Consulta: {resultado_nfce['nfce']['link_consulta']}")
    
    # === Validar regra de serviço com IA ===
    print("\n🤖 Validando regra de serviço com IA...")
    validacao = api.validar_regra_servico_ia({
        'tipo': 'servico',
        'codigo_servico_lc116': '01.07',
        'codigo_nbs': '1.0107.10.00',
        'descricao_servico': 'Desenvolvimento de sistema web',
        'aliquota_iss': 5.0,
        'iss_retido': False,
        'cst_ibs_cbs': '00',
        'regime_tributario': 'SIMPLES_NACIONAL'
    })
    
    if validacao['valido']:
        print(f"✅ Regra válida (confiança: {validacao['confianca']*100:.1f}%)")
        print(f"Explicação: {validacao['explicacao']}")
    else:
        print(f"❌ Regra inválida: {validacao['erros']}")
        if validacao.get('sugestoes'):
            print(f"💡 Sugestões: {validacao['sugestoes']}")
    
    # === Listar todas notas ===
    print("\n📊 Resumo de notas emitidas:")
    nfes = api.listar_nfes(limit=10)
    nfces = api.listar_nfces(cliente_id=1, limit=10)
    nfses = api.listar_nfses(cliente_id=1, limit=10)
    
    print(f"NFes: {nfes['total']}")
    print(f"NFCes: {nfces['total']}")
    print(f"NFSes: {nfses['total']}")
    
    # Listar NFes autorizadas
    nfes = api.listar_nfes(status='AUTORIZADA', limit=10)
    print(f"Total de NFes autorizadas: {nfes['total']}")
    
    # Criar webhook
    webhook = api.criar_webhook(
        url='https://meu-servidor.com/webhook',
        eventos=['nfe.autorizada', 'nfe.cancelada', 'nfce.autorizada', 'nfce.cancelada'],
        secret='meu_secret_super_secreto'
    )
    print(f"Webhook criado: {webhook['webhook']['webhook_id']}")
    
    # Ver estatísticas
    stats = api.estatisticas_uso()
    print(f"Requisições nos últimos 30 dias: {stats['total_requests']}")
```

---

### Exemplo 2: Integração Python Legada (API v1)

```python
import requests
from typing import Optional, Dict, Any

class EmiteMaxAPI:
    def __init__(self, base_url: str, email: str, senha: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.login(email, senha)
    
    def login(self, email: str, senha: str) -> bool:
        """Faz login e mantém a sessão"""
        response = self.session.post(
            f'{self.base_url}/auth/login',
            json={'email': email, 'senha': senha}
        )
        response.raise_for_status()
        return response.json().get('success', False)
    
    def get_cfops(self) -> list:
        """Lista todos os CFOPs"""
        response = self.session.get(f'{self.base_url}/api/cfops')
        response.raise_for_status()
        return response.json()
    
    def get_ncms(self) -> list:
        """Lista todos os NCMs"""
        response = self.session.get(f'{self.base_url}/api/ncms')
        response.raise_for_status()
        return response.json()
    
    def get_produtos_cliente(self, cliente_id: int) -> list:
        """Lista produtos de um cliente"""
        response = self.session.get(
            f'{self.base_url}/api/produtos/cliente/{cliente_id}'
        )
        response.raise_for_status()
        return response.json()
    
    def buscar_regra_tributacao(
        self,
        cliente_id: int,
        regime_tributario_id: int,
        cfop_codigo: Optional[str] = None,
        ncm_codigo: Optional[str] = None,
        uf_origem: Optional[str] = None,
        uf_destino: Optional[str] = None,
        tipo_item: Optional[str] = None
    ) -> Dict[str, Any]:
        """Busca regra de tributação"""
        payload = {
            'cliente_id': cliente_id,
            'regime_tributario_id': regime_tributario_id
        }
        
        if cfop_codigo:
            payload['cfop_codigo'] = cfop_codigo
        if ncm_codigo:
            payload['ncm_codigo'] = ncm_codigo
        if uf_origem:
            payload['uf_origem'] = uf_origem
        if uf_destino:
            payload['uf_destino'] = uf_destino
        if tipo_item:
            payload['tipo_item'] = tipo_item
        
        response = self.session.post(
            f'{self.base_url}/api/regras_tributacao/buscar',
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_proximo_numero_nfe(
        self,
        cliente_id: int,
        modelo: str = '55',
        serie: int = 1
    ) -> int:
        """Obtém próximo número de NFe"""
        response = self.session.get(
            f'{self.base_url}/api/nfe/proximo-numero',
            params={'cliente_id': cliente_id, 'modelo': modelo, 'serie': serie}
        )
        response.raise_for_status()
        return response.json()['proximo_numero']

# Uso
if __name__ == '__main__':
    # Conectar à API
    api = EmiteMaxAPI(
        base_url='https://seu-servidor.com.br',
        email='seu-email@empresa.com.br',
        senha='sua-senha'
    )
    
    # Listar CFOPs
    cfops = api.get_cfops()
    print(f"Total de CFOPs: {len(cfops)}")
    
    # Buscar produtos
    produtos = api.get_produtos_cliente(cliente_id=1)
    print(f"Total de produtos: {len(produtos)}")
    
    # Buscar regra tributária
    regra = api.buscar_regra_tributacao(
        cliente_id=1,
        regime_tributario_id=1,
        cfop_codigo='5102',
        ncm_codigo='84713000',
        uf_origem='SP',
        uf_destino='RJ',
        tipo_item='PRODUTO'
    )
    
    if regra['sucesso']:
        print(f"Alíquota ICMS: {regra['regra']['aliquota_icms']}%")
        print(f"CSOSN: {regra['regra']['csosn_icms']}")
    else:
        print("Nenhuma regra encontrada")
    
    # Obter próximo número
    proximo = api.get_proximo_numero_nfe(cliente_id=1)
    print(f"Próximo número de NFe: {proximo}")
```

---

### Exemplo 2: Integração PHP

```php
<?php

class EmiteMaxAPI {
    private $baseUrl;
    private $cookieFile;
    
    public function __construct($baseUrl, $email, $senha) {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->cookieFile = tempnam(sys_get_temp_dir(), 'emitemax_cookies_');
        $this->login($email, $senha);
    }
    
    private function login($email, $senha) {
        $ch = curl_init($this->baseUrl . '/auth/login');
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode([
                'email' => $email,
                'senha' => $senha
            ]),
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_COOKIEJAR => $this->cookieFile
        ]);
        
        $response = curl_exec($ch);
        curl_close($ch);
        
        $data = json_decode($response, true);
        if (!$data['success']) {
            throw new Exception('Falha no login');
        }
    }
    
    private function request($method, $endpoint, $data = null) {
        $ch = curl_init($this->baseUrl . $endpoint);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_COOKIEFILE => $this->cookieFile
        ]);
        
        if ($data && in_array($method, ['POST', 'PUT'])) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        }
        
        $response = curl_exec($ch);
        curl_close($ch);
        
        return json_decode($response, true);
    }
    
    public function getCfops() {
        return $this->request('GET', '/api/cfops');
    }
    
    public function getProdutosCliente($clienteId) {
        return $this->request('GET', "/api/produtos/cliente/$clienteId");
    }
    
    public function buscarRegraTributacao($params) {
        return $this->request('POST', '/api/regras_tributacao/buscar', $params);
    }
    
    public function getProximoNumeroNfe($clienteId, $modelo = '55', $serie = 1) {
        $query = http_build_query([
            'cliente_id' => $clienteId,
            'modelo' => $modelo,
            'serie' => $serie
        ]);
        return $this->request('GET', "/api/nfe/proximo-numero?$query");
    }
    
    public function __destruct() {
        if (file_exists($this->cookieFile)) {
            unlink($this->cookieFile);
        }
    }
}

// Uso
$api = new EmiteMaxAPI(
    'https://seu-servidor.com.br',
    'seu-email@empresa.com.br',
    'sua-senha'
);

$cfops = $api->getCfops();
echo "Total de CFOPs: " . count($cfops) . "\n";

$regra = $api->buscarRegraTributacao([
    'cliente_id' => 1,
    'regime_tributario_id' => 1,
    'cfop_codigo' => '5102',
    'ncm_codigo' => '84713000'
]);

if ($regra['sucesso']) {
    echo "Alíquota ICMS: " . $regra['regra']['aliquota_icms'] . "%\n";
}
?>
```

---

### Exemplo 3: Integração JavaScript (Node.js)

```javascript
const axios = require('axios');

class EmiteMaxAPI {
    constructor(baseUrl, email, senha) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.client = axios.create({
            baseURL: this.baseUrl,
            withCredentials: true,
            jar: true
        });
        
        this.login(email, senha);
    }
    
    async login(email, senha) {
        const response = await this.client.post('/auth/login', {
            email,
            senha
        });
        
        if (!response.data.success) {
            throw new Error('Falha no login');
        }
    }
    
    async getCfops() {
        const response = await this.client.get('/api/cfops');
        return response.data;
    }
    
    async getNcms() {
        const response = await this.client.get('/api/ncms');
        return response.data;
    }
    
    async getProdutosCliente(clienteId) {
        const response = await this.client.get(`/api/produtos/cliente/${clienteId}`);
        return response.data;
    }
    
    async buscarRegraTributacao(params) {
        const response = await this.client.post('/api/regras_tributacao/buscar', params);
        return response.data;
    }
    
    async getProximoNumeroNfe(clienteId, modelo = '55', serie = 1) {
        const response = await this.client.get('/api/nfe/proximo-numero', {
            params: { cliente_id: clienteId, modelo, serie }
        });
        return response.data.proximo_numero;
    }
}

// Uso
(async () => {
    const api = new EmiteMaxAPI(
        'https://seu-servidor.com.br',
        'seu-email@empresa.com.br',
        'sua-senha'
    );
    
    const cfops = await api.getCfops();
    console.log(`Total de CFOPs: ${cfops.length}`);
    
    const regra = await api.buscarRegraTributacao({
        cliente_id: 1,
        regime_tributario_id: 1,
        cfop_codigo: '5102',
        ncm_codigo: '84713000',
        uf_origem: 'SP',
        uf_destino: 'RJ',
        tipo_item: 'PRODUTO'
    });
    
    if (regra.sucesso) {
        console.log(`Alíquota ICMS: ${regra.regra.aliquota_icms}%`);
        console.log(`CSOSN: ${regra.regra.csosn_icms}`);
    }
})();
```

---

## 📊 Códigos de Resposta

| Código | Descrição | Significado |
|--------|-----------|-------------|
| 200 | OK | Requisição bem-sucedida |
| 400 | Bad Request | Parâmetros inválidos ou faltando |
| 401 | Unauthorized | Não autenticado (faça login) |
| 403 | Forbidden | Sem permissão para acessar este recurso |
| 404 | Not Found | Recurso não encontrado |
| 500 | Internal Server Error | Erro no servidor |

---

## ✅ Boas Práticas

### 1. Gerenciamento de Sessão

- ✅ Reutilize a mesma sessão para múltiplas requisições
- ✅ Implemente renovação automática de login se necessário
- ❌ Não faça login a cada requisição

### 2. Tratamento de Erros

```python
try:
    regra = api.buscar_regra_tributacao(...)
    if regra['sucesso']:
        # Usar regra
        pass
    else:
        # Nenhuma regra encontrada - usar valores padrão
        print(regra['message'])
except requests.HTTPError as e:
    if e.response.status_code == 401:
        # Re-autenticar
        api.login(email, senha)
    elif e.response.status_code == 403:
        # Sem permissão
        print("Acesso negado")
    else:
        # Outro erro
        print(f"Erro: {e}")
```

### 3. Cache de Dados Estáticos

CFOPs e NCMs não mudam frequentemente. Considere fazer cache local:

```python
import json
from datetime import datetime, timedelta

class CachedEmiteMaxAPI(EmiteMaxAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
    
    def get_cfops(self, force_refresh=False):
        cache_key = 'cfops'
        cache_duration = timedelta(days=7)
        
        if not force_refresh and cache_key in self.cache:
            cached_at, data = self.cache[cache_key]
            if datetime.now() - cached_at < cache_duration:
                return data
        
        data = super().get_cfops()
        self.cache[cache_key] = (datetime.now(), data)
        return data
```

### 4. Logging

Mantenha logs de todas as requisições para auditoria:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EmiteMaxAPI')

class LoggedEmiteMaxAPI(EmiteMaxAPI):
    def buscar_regra_tributacao(self, *args, **kwargs):
        logger.info(f"Buscando regra tributária: {kwargs}")
        result = super().buscar_regra_tributacao(*args, **kwargs)
        logger.info(f"Regra encontrada: {result.get('sucesso', False)}")
        return result
```

### 5. Rate Limiting

Evite sobrecarregar o servidor:

```python
import time

class RateLimitedAPI(EmiteMaxAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_request = 0
        self.min_interval = 0.1  # 100ms entre requisições
    
    def _wait_if_needed(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()
    
    def buscar_regra_tributacao(self, *args, **kwargs):
        self._wait_if_needed()
        return super().buscar_regra_tributacao(*args, **kwargs)
```

---

## 🔒 Segurança

### Recomendações Importantes

1. **Nunca exponha credenciais no código**
   ```python
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   
   api = EmiteMaxAPI(
       base_url=os.getenv('EMITEMAX_URL'),
       email=os.getenv('EMITEMAX_EMAIL'),
       senha=os.getenv('EMITEMAX_PASSWORD')
   )
   ```

2. **Use HTTPS em produção**
   - ✅ `https://seu-servidor.com.br`
   - ❌ `http://seu-servidor.com.br`

3. **Valide dados antes de enviar**
   ```python
   def validar_cnpj(cnpj):
       # Implementar validação
       pass
   
   if not validar_cnpj(cnpj):
       raise ValueError("CNPJ inválido")
   ```

4. **Implemente timeout nas requisições**
   ```python
   response = self.session.get(url, timeout=30)
   ```

---

## 🆘 Suporte

### Problemas Comuns

#### 1. "Unauthorized" (401)

**Causa:** Sessão expirou ou login não foi feito corretamente.

**Solução:**
```python
# Fazer login novamente
api.login(email, senha)
```

#### 2. "Forbidden" (403)

**Causa:** Usuário não tem permissão para acessar o cliente solicitado.

**Solução:** Verifique se o `cliente_id` pertence ao usuário logado:
```python
clientes = api.session.get(f'{api.base_url}/api/clientes').json()
cliente_ids_permitidos = [c['cliente_id'] for c in clientes]
```

#### 3. Nenhuma regra de tributação encontrada

**Causa:** Não existe regra cadastrada para os critérios fornecidos.

**Solução:** 
- Cadastre regras no sistema através da interface administrativa
- Use valores padrão no seu sistema quando nenhuma regra for encontrada
- Simplifique os critérios de busca (remova filtros opcionais)

#### 4. Timeout nas requisições

**Causa:** Servidor pode estar sobrecarregado ou conexão instável.

**Solução:**
```python
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('https://', adapter)
```

---

### Contato

Para dúvidas, sugestões ou suporte técnico:

- **Email:** contato@emitemax.com.br
- **WhatsApp:** (17) 98810-5545
- **Documentação:** https://seu-servidor.com.br/docs

---

## 📝 Changelog

### Versão 2.0 (Dezembro 2024 - Atualização 30/12/2024) ⭐ ATUAL
- ✅ **Emissão de NFS-e** (Nota Fiscal de Serviço Eletrônica)
  - Endpoint completo para emissão de notas de serviço
  - Suporte a código LC 116 e NBS
  - Validação de regras tributárias com IA
  - Consulta, cancelamento e download de PDF
- ✅ **Emissão de NFC-e** (Nota Fiscal do Consumidor)
  - Endpoint para emissão de cupom fiscal eletrônico (modelo 65)
  - QR Code obrigatório para consulta
  - Suporte a consumidor não identificado
  - Múltiplas formas de pagamento
  - Inutilização de numeração
- ✅ **Validação por IA**
  - Endpoint `/api/validar-regra-servico-ia` para serviços
  - Validação automática de códigos e alíquotas
  - Sugestões inteligentes de correção
- ✅ **Tabela Comparativa**
  - Documentação detalhada das diferenças entre NFe, NFCe e NFSe
  - Guia de escolha do modelo correto
- ✅ **Exemplos Python Completos**
  - Classe EmiteMaxAPIv2 com métodos para todos tipos de nota
  - Exemplos práticos de emissão NFe, NFCe e NFSe
  - Código pronto para copiar e usar

### Versão 1.0 (Dezembro 2024)
- ✅ Endpoints de consulta (CFOPs, NCMs, Produtos)
- ✅ Busca de regras de tributação
- ✅ Consulta de próximo número de NFe
- ✅ Autenticação por sessão
- ✅ Controle de permissões por cliente
- ✅ Autenticação por API Key
- ✅ Endpoint para emissão de NFe via API
- ✅ Consulta de status de NFe (autorizada, cancelada, etc)
- ✅ Webhook para notificações de eventos
- ✅ Rate limiting configurável por cliente
- ✅ Documentação OpenAPI/Swagger parcial

### Próximas Versões (Roadmap)

- 🔜 API v3 com GraphQL
- 🔜 Integração com mais prefeituras (NFS-e)
- 🔜 CT-e (Conhecimento de Transporte Eletrônico)
- 🔜 MDF-e (Manifesto de Documentos Fiscais Eletrônico)
- 🔜 Emissão de NFS-e em lote
- 🔜 Importação automática de XMLs de terceiros
- 🔜 Dashboard analytics em tempo real

---

**© 2024 EmiteMax - Sistema de Gestão Fiscal**

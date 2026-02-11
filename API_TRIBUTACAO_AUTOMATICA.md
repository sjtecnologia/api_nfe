# 🤖 API - Tributação Automática de NFe

**Data:** 11 de fevereiro de 2026  
**Status:** ✅ Implementado

---

## 📋 Resumo

A API agora **busca e aplica automaticamente** as regras tributárias cadastradas no sistema quando o cliente envia apenas os dados básicos do produto (NCM e CFOP). Não é mais necessário enviar todos os dados tributários (CST, alíquotas, etc.) - o sistema faz isso automaticamente!

---

## 🎯 Como Funciona

### **Antes (Manual)** ❌

Cliente precisava enviar **tudo**:

```json
{
  "destinatario": { ... },
  "itens": [
    {
      "descricao": "Notebook Dell",
      "quantidade": 1,
      "valor_unitario": 3500.00,
      "ncm": "84713000",
      "cfop": "5102",
      "unidade": "UN",
      
      // ❌ TINHA QUE ENVIAR TUDO ISSO:
      "cst_icms": "00",
      "csosn_icms": null,
      "aliquota_icms": 18.00,
      "reducao_base_icms": 0,
      "modalidade_bc_icms": "3",
      "motivo_desoneracao_icms": null,
      "cst_pis": "01",
      "aliquota_pis": 1.65,
      "cst_cofins": "01",
      "aliquota_cofins": 7.60,
      "cst_ipi": "99",
      "aliquota_ipi": 0.00
    }
  ]
}
```

### **Agora (Automático)** ✅

Cliente envia apenas o **essencial**:

```json
{
  "destinatario": {
    "cpf_cnpj": "12345678000195",
    "nome": "Cliente Exemplo Ltda",
    "endereco": "Rua Teste",
    "numero": "123",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "uf": "SP",
    "cep": "01234567",
    "email": "contato@cliente.com"
  },
  "itens": [
    {
      "descricao": "Notebook Dell Inspiron 15",
      "quantidade": 1,
      "valor_unitario": 3500.00,
      "ncm": "84713000",
      "cfop": "5102",
      "unidade": "UN"
    }
  ],
  "natureza_operacao": "Venda de Mercadoria",
  "informacoes_adicionais": "Pedido #12345"
}
```

**E o sistema faz automaticamente:**
1. ✅ Busca a regra tributária correspondente
2. ✅ Aplica CST/CSOSN ICMS
3. ✅ Aplica alíquotas ICMS, PIS, COFINS
4. ✅ Aplica IPI se necessário
5. ✅ Aplica reduções de base e desoneração
6. ✅ Gera XML completo e envia para SEFAZ

---

## 🔍 Critérios de Busca Automática

O sistema busca a regra tributária usando os seguintes critérios (em ordem de prioridade):

| Critério | Origem | Obrigatório |
|----------|--------|-------------|
| **Cliente ID** | Autenticação API Key | ✅ Sim |
| **Regime Tributário** | Cadastro do emitente | ✅ Sim |
| **NCM** | Item enviado | ✅ Sim |
| **CFOP** | Item enviado | ✅ Sim |
| **UF Origem** | Cadastro do emitente | ✅ Sim |
| **UF Destino** | Destinatário enviado | ✅ Sim |
| **Tipo Item** | Item enviado (padrão: "Produto") | Não |

### Lógica de Priorização

O sistema busca regras na seguinte ordem de especificidade:

1. **Regra específica do cliente** + NCM + CFOP + UF
2. **Regra específica do cliente** + NCM + CFOP
3. **Regra específica do cliente** + NCM
4. **Regra genérica** + NCM + CFOP + UF
5. **Regra genérica** + NCM + CFOP
6. **Regra genérica** + NCM

---

## 📝 Exemplos de Uso

### Exemplo 1: Venda Estadual (Simples Nacional)

**Emitente:**
- CNPJ: 01.517.186/0001-13
- Regime: Simples Nacional
- UF: SP

**Destinatário:**
- CNPJ: 12.345.678/0001-95
- UF: SP (mesma UF)

**Request:**
```json
POST /api/v2/nfe/emitir
Authorization: Bearer SEU_API_KEY

{
  "destinatario": {
    "cpf_cnpj": "12345678000195",
    "nome": "Empresa ABC Ltda",
    "endereco": "Av. Paulista",
    "numero": "1000",
    "bairro": "Bela Vista",
    "cidade": "São Paulo",
    "uf": "SP",
    "cep": "01310100",
    "email": "fiscal@empresaabc.com"
  },
  "itens": [
    {
      "descricao": "Mouse Gamer RGB",
      "quantidade": 5,
      "valor_unitario": 150.00,
      "ncm": "84716040",
      "cfop": "5102",
      "unidade": "UN"
    }
  ],
  "natureza_operacao": "Venda"
}
```

**Sistema aplica automaticamente:**
```json
{
  "csosn_icms": "102",  // Tributada sem permissão de crédito
  "aliquota_icms": 0,
  "cst_pis": "99",
  "aliquota_pis": 0,
  "cst_cofins": "99",
  "aliquota_cofins": 0,
  "cst_ipi": "99",
  "aliquota_ipi": 0
}
```

---

### Exemplo 2: Venda Interestadual (Lucro Presumido)

**Emitente:**
- CNPJ: 01.517.186/0001-13
- Regime: Lucro Presumido
- UF: SP

**Destinatário:**
- CNPJ: 98.765.432/0001-10
- UF: RJ (outra UF)

**Request:**
```json
{
  "destinatario": {
    "cpf_cnpj": "98765432000110",
    "nome": "Distribuidora XYZ Ltda",
    "endereco": "Rua do Porto",
    "numero": "500",
    "bairro": "Centro",
    "cidade": "Rio de Janeiro",
    "uf": "RJ",
    "cep": "20010000",
    "email": "nfe@distribuidoraxyz.com"
  },
  "itens": [
    {
      "descricao": "Teclado Mecânico",
      "quantidade": 10,
      "valor_unitario": 400.00,
      "ncm": "84716040",
      "cfop": "6102",
      "unidade": "UN"
    }
  ]
}
```

**Sistema aplica automaticamente:**
```json
{
  "cst_icms": "00",           // Tributado integralmente
  "aliquota_icms": 12.00,     // Alíquota interestadual SP→RJ
  "cst_pis": "01",
  "aliquota_pis": 1.65,
  "cst_cofins": "01",
  "aliquota_cofins": 7.60,
  "cst_ipi": "99",
  "aliquota_ipi": 0
}
```

---

### Exemplo 3: Produto Industrializado com IPI

**Request:**
```json
{
  "destinatario": { ... },
  "itens": [
    {
      "descricao": "Geladeira Frost Free 400L",
      "quantidade": 2,
      "valor_unitario": 2800.00,
      "ncm": "84182100",  // NCM de refrigerador
      "cfop": "5102",
      "unidade": "UN"
    }
  ]
}
```

**Sistema aplica automaticamente:**
```json
{
  "cst_icms": "00",
  "aliquota_icms": 18.00,
  "cst_pis": "01",
  "aliquota_pis": 1.65,
  "cst_cofins": "01",
  "aliquota_cofins": 7.60,
  "cst_ipi": "50",        // IPI aplicado
  "aliquota_ipi": 5.00    // 5% de IPI
}
```

---

## 🔧 Modo Híbrido (Opcional)

Você pode **sobrescrever** dados específicos enviando parcialmente:

```json
{
  "itens": [
    {
      "descricao": "Produto Especial",
      "ncm": "84713000",
      "cfop": "5102",
      "quantidade": 1,
      "valor_unitario": 1000,
      
      // ✅ Sistema busca regra automaticamente
      // MAS você pode sobrescrever campos específicos:
      "aliquota_icms": 15.00,  // Sobrescreve alíquota da regra
      "cst_pis": "04"           // Sobrescreve CST PIS da regra
      
      // Outros campos virão da regra automaticamente:
      // cst_icms, aliquota_pis, cst_cofins, aliquota_cofins
    }
  ]
}
```

**Lógica de prioridade:**
1. Se campo tem valor na requisição → **usa o valor enviado**
2. Se campo está vazio/null → **busca da regra tributária**

---

## ⚙️ Configuração Necessária

### 1. Cadastrar Regras Tributárias

Acesse: **Admin > Regras de Tributação > Criar Nova**

Configure regras para suas operações mais comuns:

**Exemplo de Regra:**
- **Cliente:** Todos (deixar em branco) ou específico
- **Regime:** Simples Nacional
- **CFOP:** 5102 (Venda dentro do Estado)
- **NCM:** 84713000 (ou deixar em branco para todos)
- **UF Origem:** SP
- **UF Destino:** SP
- **Tipo:** Produto

**Tributação:**
- CSOSN ICMS: 102
- CST PIS: 99
- Alíquota PIS: 0%
- CST COFINS: 99
- Alíquota COFINS: 0%

### 2. Criar API Key

**Admin > Configurações > API Keys > Gerar Nova**

Permissões necessárias:
- ✅ `nfe.read`
- ✅ `nfe.write`
- ✅ `nfe.emit`

---

## 📊 Logs de Depuração

O sistema registra logs detalhados no console:

```
[API v2] [AUTO] Aplicando regras tributárias automaticamente nos itens...
[API v2] [AUTO] Processando item 1/1...
[API v2] [REGRA] Buscando regra tributária automática...
[API v2] [REGRA]   Cliente ID: 123
[API v2] [REGRA]   Regime: 1
[API v2] [REGRA]   NCM: 84713000
[API v2] [REGRA]   CFOP: 5102
[API v2] [REGRA]   UF: SP → SP
[API v2] [REGRA] ✅ Regra encontrada: ID 5
[API v2] [REGRA]   Descrição: Venda Estadual - Simples Nacional
[API v2] [REGRA]   → CSOSN ICMS: 102
[API v2] [REGRA]   → CST PIS: 99
[API v2] [REGRA]   → CST COFINS: 99
[API v2] [AUTO] ✅ Regras aplicadas em 1 item(ns)
```

---

## ⚠️ Fallback (Nenhuma Regra Encontrada)

Se **nenhuma regra** for encontrada:

1. ✅ Sistema continua processamento
2. ⚠️ Usa valores **padrão ou fornecidos**
3. ℹ️ Log registra: "Nenhuma regra encontrada"

**Valores padrão aplicados:**
- ICMS: 18% (ou 0% se Simples)
- PIS: 1.65%
- COFINS: 7.60%
- IPI: 0%

---

## 🧪 Teste Rápido

Use este payload de teste:

```bash
curl -X POST https://api.emitemax.com.br/api/v2/nfe/emitir \
  -H "Authorization: Bearer SEU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "destinatario": {
      "cpf_cnpj": "12345678000195",
      "nome": "Teste API",
      "endereco": "Rua Teste",
      "numero": "1",
      "bairro": "Centro",
      "cidade": "São Paulo",
      "uf": "SP",
      "cep": "01234567"
    },
    "itens": [
      {
        "descricao": "Produto Teste",
        "quantidade": 1,
        "valor_unitario": 100.00,
        "ncm": "84713000",
        "cfop": "5102",
        "unidade": "UN"
      }
    ]
  }'
```

---

## 📌 Vantagens

✅ **Menos código no cliente** - Envia só NCM e CFOP  
✅ **Centralização** - Regras gerenciadas no admin  
✅ **Consistência** - Mesma tributação para todos  
✅ **Agilidade** - Payloads menores e mais simples  
✅ **Flexibilidade** - Pode sobrescrever quando necessário  
✅ **Auditável** - Logs completos de qual regra foi aplicada  

---

## 🔗 Endpoints Relacionados

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v2/nfe/emitir` | POST | Emite NFe com tributação automática |
| `/api/regras_tributacao/buscar` | POST | Busca regra manualmente (opcional) |
| `/admin/regras-tributacao` | GET | Lista regras cadastradas |

---

## 💡 Dicas de Uso

### ✅ Boas Práticas

1. **Cadastre regras genéricas** para cenários comuns (venda estadual, interestadual)
2. **Cadastre regras específicas** para produtos especiais (com IPI, ST, etc.)
3. **Use prioridades** para controlar qual regra é aplicada primeiro
4. **Teste em homologação** antes de usar em produção

### ❌ Evite

1. Não envie dados tributários incompletos (só CST sem alíquota)
2. Não misture CSOSN (Simples) com CST (outros regimes)
3. Não esqueça de cadastrar regras antes de usar a API

---

## 🆘 Troubleshooting

### Problema: "Nenhuma regra encontrada"

**Causa:** Não existe regra cadastrada para os critérios enviados

**Solução:**
1. Verifique se existe regra no Admin
2. Confirme CFOP, NCM, UF origem/destino
3. Verifique se a regra está ativa
4. Crie uma regra genérica como fallback

### Problema: Impostos com valores errados

**Causa:** Regra com configuração incorreta

**Solução:**
1. Acesse Admin > Regras de Tributação
2. Edite a regra encontrada (veja o log)
3. Corrija alíquotas e CSTs
4. Salve e teste novamente

### Problema: CST incompatível com regime

**Causa:** Regra configurada para regime errado

**Solução:**
- Simples Nacional → Use **CSOSN** (101, 102, 103, etc.)
- Outros regimes → Use **CST** (00, 10, 20, etc.)

---

## 📚 Documentos Relacionados

- [Manual de API v2](API_V2.md)
- [Guia de Regras Tributárias](INTEGRACAO_REGRAS_TRIBUTARIAS_NFE.md)
- [Exemplos de Integração](EXEMPLO_INTEGRACAO_PLANOS.py)

---

**Desenvolvido por:** EmiteMax  
**Última atualização:** 11 de fevereiro de 2026  
**Versão da API:** 2.0

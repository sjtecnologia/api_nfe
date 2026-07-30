# 📋 Exemplo Completo de NFe - Todas as Tributações

## 🎯 Objetivo

Este JSON contém um exemplo **COMPLETO** de emissão de NFe com **TODOS OS TIPOS DE TRIBUTAÇÃO** possíveis, servindo como referência para integração com a API v2.

---

## 🔌 Como Usar

### **Endpoint:**
```
POST http://192.168.0.52:8080/api/v2/nfe/emitir
```

### **Headers:**
```
Authorization: emx_live_sua_chave_api_aqui
Content-Type: application/json
```

### **Body:**
Use o arquivo `nfe_completa_todas_tributacoes.json`

---

## 📦 O que está incluído

### **11 Produtos/Serviços com diferentes tributações:**

| Item | CST ICMS | Descrição | Características |
|------|----------|-----------|-----------------|
| 1 | **00** | Tributado Integralmente | ICMS normal + IPI + PIS/COFINS + IBS/CBS |
| 2 | **10** | Tributado com ICMS ST | ICMS próprio + ICMS ST + MVA |
| 3 | **20** | Redução de Base de Cálculo | Redução de 33,33% na BC |
| 4 | **30** | Isenta com ICMS ST | Sem ICMS próprio + ICMS ST |
| 5 | **40** | Isenta | Motivo de desoneração |
| 6 | **41** | Não tributada | PIS/COFINS também não tributados |
| 7 | **51** | Diferimento | Diferimento parcial de ICMS |
| 8 | **60** | ICMS ST Retido Anteriormente | Valor de ST já cobrado |
| 9 | **70** | Redução BC + ICMS ST | Combinação de redução e ST |
| 10 | **90** | Outros | Situação tributária especial |
| 11 | **ISSQN** | Serviço | ISSQN + PIS/COFINS |

---

## 💰 Tributações Exemplificadas

### **ICMS - Todas as situações:**
- ✅ CST 00 - Tributado integralmente
- ✅ CST 10 - Tributado com ST
- ✅ CST 20 - Redução de BC
- ✅ CST 30 - Isenta com ST
- ✅ CST 40 - Isenta
- ✅ CST 41 - Não tributada
- ✅ CST 51 - Diferimento
- ✅ CST 60 - ST cobrado anteriormente
- ✅ CST 70 - Redução BC com ST
- ✅ CST 90 - Outros

### **IPI:**
- ✅ CST 50 - Saída tributada

### **PIS/COFINS:**
- ✅ CST 01 - Operação tributável (alíquota básica)
- ✅ CST 04 - Operação tributável (alíquota zero)
- ✅ CST 06 - Operação tributável (alíquota zero) - Não tributada
- ✅ CST 99 - Outras operações

### **IBS e CBS (LC 214/2025):**
- ✅ Nova tributação sobre bens e serviços
- ✅ Alíquotas padrão: IBS 0,80% / CBS 0,35%

### **ISSQN:**
- ✅ Imposto sobre serviços
- ✅ Alíquota 5%

---

## 📊 Valores Totais

```
Valor dos Produtos:     R$ 16.500,00
Valor ICMS:            R$  1.648,01
Valor ICMS ST:         R$    648,00
Valor IPI:             R$    100,00
Valor PIS:             R$    238,00
Valor COFINS:          R$    936,00
Valor IBS:             R$     32,00
Valor CBS:             R$     14,00
ISSQN:                 R$     50,00
────────────────────────────────────
TOTAL DA NOTA:         R$ 17.248,00
```

---

## 🚚 Transporte

- **Modalidade:** CIF (0 - Emitente)
- **Transportadora:** Completa com CNPJ e endereço
- **Veículo:** Placa e RNTC
- **Volumes:** 15 caixas, 150,50kg líquido / 180kg bruto

---

## 💳 Pagamento

### **Forma de Pagamento:** À Vista (0)

**Pagamentos:**
1. Dinheiro: R$ 10.000,00
2. Cartão de Débito: R$ 7.248,00

**Parcelamento em 2x:**
- Duplicata 001: R$ 8.624,00 - Venc: 20/01/2025
- Duplicata 002: R$ 8.624,00 - Venc: 20/02/2025

---

## 📝 Informações Adicionais

- Informações complementares para o contribuinte
- Informações de interesse do Fisco
- NFe referenciada (chave de acesso de exemplo)

---

## 🔧 Campos Importantes

### **Origem da Mercadoria (campo `origem`):**
- `0` - Nacional
- `1` - Estrangeira - Importação direta
- `2` - Estrangeira - Adquirida no mercado interno
- Etc.

### **CFOP Comuns:**
- `5102` - Venda de mercadoria adquirida de terceiros (dentro do estado)
- `5933` - Prestação de serviços tributados pelo ISSQN

### **Modalidade BC ICMS:**
- `3` - Valor da operação

### **Modalidade BC ST:**
- `4` - Margem de Valor Agregado (MVA)

---

## ⚙️ Campos Opcionais Importantes

### **Para ICMS ST (CST 10, 30, 70):**
```json
"modalidade_bc_st": "4",
"mva_st": 50.00,
"base_calculo_st": 1500.00,
"aliquota_st": 18.00,
"valor_st": 90.00
```

### **Para Redução de BC (CST 20, 70):**
```json
"percentual_reducao_bc": 33.33,
"base_calculo": 1000.05
```

### **Para Diferimento (CST 51):**
```json
"percentual_diferimento": 33.33,
"valor_icms_operacao": 270.00,
"valor_icms_diferido": 89.99,
"valor": 180.01
```

### **Para Desoneração (CST 40):**
```json
"motivo_desoneracao": "3"
```

Motivos de desoneração:
- `1` - Táxi
- `3` - Produtor Agropecuário
- `9` - Outros
- `12` - Órgão de fomento

---

## 📌 Notas Importantes

1. **Destinatário:** Deve ser cadastrado previamente ou criado dinamicamente
2. **NCM:** Código obrigatório (use `00` para serviços)
3. **CFOP:** Deve ser apropriado para a operação
4. **Totais:** Devem ser calculados corretamente
5. **IBS/CBS:** Campos novos da LC 214/2025

---

## ✅ Validações

Antes de enviar, certifique-se:

- [ ] API Key válida no header Authorization
- [ ] Destinatário com dados completos
- [ ] NCM válido para todos os produtos
- [ ] CFOP apropriado para a operação
- [ ] Cálculos de impostos corretos
- [ ] Totais batendo com soma dos itens
- [ ] Certificado digital válido configurado

---

## 🚀 Testando

### **1. Ambiente de Homologação:**
Configure o cliente para ambiente `1` (homologação) antes de testar.

### **2. Postman:**
```bash
POST http://192.168.0.52:8080/api/v2/nfe/emitir
Headers:
  Authorization: emx_live_sua_chave_aqui
  Content-Type: application/json
Body: [Cole o JSON do arquivo]
```

### **3. cURL:**
```bash
curl -X POST http://192.168.0.52:8080/api/v2/nfe/emitir \
  -H "Authorization: emx_live_sua_chave_aqui" \
  -H "Content-Type: application/json" \
  -d @nfe_completa_todas_tributacoes.json
```

---

## 📖 Documentação Completa

Para mais detalhes sobre cada campo, consulte:
- Manual de Integração da NFe 4.0
- Nota Técnica 2023.003
- Lei Complementar 214/2025 (IBS/CBS)

---

## 🆘 Suporte

Em caso de dúvidas:
1. Verifique os logs da API: `C:\nfe_app\logs\stdout.log`
2. Consulte a documentação da SEFAZ
3. Teste primeiro em homologação

---

**Arquivo gerado:** 19/12/2025  
**Versão:** 1.0  
**API:** v2

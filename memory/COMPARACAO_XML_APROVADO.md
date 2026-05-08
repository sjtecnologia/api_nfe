# 🔍 Comparação: XML Aprovado vs XML Rejeitado

**Data:** 27/01/2026  
**Objetivo:** Identificar diferenças que causam Erro 225

---

## ✅ XML APROVADO (Sebrae - Produção)
**Status:** cStat=100 - "Autorizado o uso da NF-e"  
**Sistema:** EmissorSebrae1.00  
**Ambiente:** tpAmb=1 (PRODUÇÃO)  
**Data Emissão:** 2026-01-22T11:18:04-03:00

## ❌ XML REJEITADO (Nosso Sistema - Homologação)
**Status:** Erro 225 - "Falha no Schema XML"  
**Sistema:** EmiteMax_1.0  
**Ambiente:** tpAmb=2 (HOMOLOGAÇÃO)  
**Data Emissão:** 2026-01-26T15:35:12.035099-03:00

---

## 🔴 DIFERENÇAS CRÍTICAS ENCONTRADAS

### 1. ❌ **Capitalização do Município**
| Campo | Aprovado | Nosso | Análise |
|-------|----------|-------|---------|
| `<xMun>` | **Sao Jose do Rio Preto** | **SAO JOSE DO RIO PRETO** | ⚠️ **MAIÚSCULAS vs Capitalizado** |

**Impacto:** ALTO - Pode ser a causa do erro!  
**Observação:** SEFAZ aceita capitalização mista, não apenas maiúsculas.

### 2. ❌ **procEmi - Processo de Emissão**
| Campo | Aprovado | Nosso | Análise |
|-------|----------|-------|---------|
| `<procEmi>` | **0** | **1** | ⚠️ **Diferença no tipo de emissor** |

**Valores possíveis:**
- `0` = Emissão de NF-e com aplicação do contribuinte (usado pelo Sebrae)
- `1` = Emissão de NF-e avulsa pelo Fisco
- `2` = Emissão de NF-e avulsa, pelo contribuinte com seu certificado digital
- `3` = Emissão NF-e pelo contribuinte com aplicação do Fisco

**Impacto:** MÉDIO  
**Observação:** Estávamos usando `1` mas deveríamos usar `0`!

### 3. ❌ **Data/Hora com Microsegundos**
| Campo | Aprovado | Nosso | Análise |
|-------|----------|-------|---------|
| `<dhEmi>` | 2026-01-22T11:18:04**-03:00** | 2026-01-26T15:35:12**.035099-03:00** | ⚠️ **Microsegundos desnecessários** |

**Impacto:** BAIXO mas possível  
**Observação:** XML aprovado usa apenas segundos, sem fração.

### 4. ❌ **CFOP Diferente**
| Campo | Aprovado | Nosso | Análise |
|-------|----------|-------|---------|
| `<CFOP>` | **5101** | **5405** | ⚠️ **Operações diferentes** |

**Significado:**
- `5101` = Venda de produção do estabelecimento
- `5405` = Venda de mercadoria sujeita ao regime de ST

**Impacto:** BAIXO (CSOSN 102 é compatível com ambos)

### 5. ❌ **Caractere Especial no Nome**
| Campo | Aprovado | Nosso | Análise |
|-------|----------|-------|---------|
| `<xNome>` dest | ASSOCIACAO (...) | ASSOCIA**SS**ÃO (...) | ⚠️ **"Ç" pode causar problema** |

**Impacto:** MÉDIO  
**Observação:** XML aprovado usa "ASSOCIACAO", nós usamos "ASSOCIASSÃO" com Ç.

### 6. ❌ **Valores com Formatação Diferente**
| Campo | Aprovado | Nosso | Análise |
|-------|----------|-------|---------|
| `<qCom>` | **100.0000** | **100** | ⚠️ **4 casas decimais vs sem casas** |
| `<vUnCom>` | **5.5000** | **5.5** | ⚠️ **4 casas vs 1 casa** |
| `<qTrib>` | **100.0000** | **100** | ⚠️ **4 casas decimais vs sem casas** |
| `<vUnTrib>` | **5.5000** | **5.5** | ⚠️ **4 casas vs 1 casa** |

**Impacto:** ALTO - Formatação de valores deve seguir padrão!  
**Observação:** Manual NFe especifica: qCom e qTrib = até 4 decimais, vUnCom e vUnTrib = até 10 decimais.

### 7. ⚠️ **Campo cDV Ausente**
| Campo | Aprovado | Nosso | Análise |
|-------|----------|-------|---------|
| `<ide><cDV>` | **3** | **AUSENTE** | ⚠️ **Campo obrigatório faltando?** |

**Impacto:** CRÍTICO se obrigatório  
**Observação:** cDV é o dígito verificador da chave de acesso.

---

## ✅ CAMPOS PRESENTES NO APROVADO, AUSENTES NO NOSSO

### 8. ❌ **vTotTrib - Valor Total dos Tributos**
```xml
<!-- APROVADO -->
<vTotTrib>0.00</vTotTrib>

<!-- NOSSO -->
<!-- AUSENTE -->
```
**Impacto:** MÉDIO - Campo pode ser obrigatório

### 9. ❌ **Campos de ICMS Interestadual**
```xml
<!-- APROVADO -->
<vFCPUFDest>0.00</vFCPUFDest>
<vICMSUFDest>0.00</vICMSUFDest>
<vICMSUFRemet>0.00</vICMSUFRemet>

<!-- NOSSO -->
<!-- AUSENTE -->
```
**Impacto:** BAIXO - Apenas para operações interestaduais

### 10. ❌ **infRespTec - Informações do Responsável Técnico**
```xml
<!-- APROVADO -->
<infRespTec>
  <CNPJ>00330845000145</CNPJ>
  <xContato>Suporte</xContato>
  <email>emissores@sebrae.com.br</email>
  <fone>08005700800</fone>
</infRespTec>

<!-- NOSSO -->
<!-- AUSENTE -->
```
**Impacto:** BAIXO - Campo opcional segundo manual

### 11. ❌ **Cobrança/Fatura**
```xml
<!-- APROVADO -->
<cobr>
  <fat>
    <nFat>41</nFat>
    <vOrig>550.00</vOrig>
    <vDesc>0.00</vDesc>
    <vLiq>550.00</vLiq>
  </fat>
</cobr>

<!-- NOSSO -->
<!-- AUSENTE -->
```
**Impacto:** BAIXO - Campo opcional

### 12. ❌ **indPag - Indicador de Pagamento**
```xml
<!-- APROVADO -->
<detPag>
  <indPag>0</indPag>  <!-- À vista -->
  <tPag>01</tPag>
  <vPag>550.00</vPag>
</detPag>

<!-- NOSSO -->
<detPag>
  <tPag>01</tPag>
  <vPag>550.00</vPag>
</detPag>
```
**Impacto:** MÉDIO - Campo pode ser obrigatório

### 13. ❌ **CEST - Código Especificador da Substituição Tributária**
```xml
<!-- APROVADO -->
<CEST>2300100</CEST>

<!-- NOSSO -->
<!-- AUSENTE -->
```
**Impacto:** ALTO para produtos específicos  
**Observação:** Obrigatório para alguns produtos com ST

### 14. ❌ **vTotTrib no Imposto do Item**
```xml
<!-- APROVADO -->
<imposto>
  <vTotTrib>0.00</vTotTrib>
  ...
</imposto>

<!-- NOSSO -->
<!-- AUSENTE -->
```
**Impacto:** MÉDIO - Lei da Transparência Tributária

### 15. ❌ **Campos PIS/COFINS Diferentes**
```xml
<!-- APROVADO -->
<PIS>
  <PISOutr>
    <CST>49</CST>
    <vBC>0.00</vBC>
    <pPIS>0.00</pPIS>
    <vPIS>0.00</vPIS>
  </PISOutr>
</PIS>

<!-- NOSSO -->
<PIS>
  <PISNT>
    <CST>07</CST>
  </PISNT>
</PIS>
```
**Impacto:** MÉDIO  
**Observação:** CST 07 = Operação isenta, CST 49 = Outras operações

### 16. ⚠️ **Campos no Emitente**
```xml
<!-- APROVADO -->
<emit>
  <CNPJ>43101347000133</CNPJ>  <!-- REAL -->
  <IE>124253850116</IE>         <!-- IE REAL -->
  ...
</emit>

<!-- NOSSO -->
<emit>
  <CNPJ>99999999000191</CNPJ>  <!-- TESTE -->
  <IE>ISENTO</IE>               <!-- IE ISENTO -->
  <xFant>POP DRI PIPOCA GOURMET</xFant>  <!-- Temos fantasia -->
  <xPais>BRASIL</xPais>         <!-- Temos nome do país -->
  ...
</emit>
```

---

## 📋 CAMPOS IGUAIS (OK)

✅ cUF = 35 (SP)  
✅ natOp = texto descritivo  
✅ mod = 55 (NFe)  
✅ serie = 1  
✅ tpNF = 1 (Saída)  
✅ idDest = 1 (Interna)  
✅ cMunFG = 3549805  
✅ tpImp = 1 (DANFE Retrato)  
✅ tpEmis = 1 (Normal)  
✅ finNFe = 1 (Normal)  
✅ indFinal = 1 (Consumidor final)  
✅ indPres = Diferente mas OK (0 vs 1)  
✅ CRT = 1 (Simples Nacional)  
✅ NCM = 21050010  
✅ CSOSN = 102  
✅ Valores totais = 550.00  
✅ modFrete = 9 (Sem frete)

---

## 🎯 RANKING DE PRIORIDADE PARA CORREÇÃO

### 🔴 CRÍTICO (Implementar AGORA)

1. **procEmi: 1 → 0**  
   Mudar de "emissão avulsa pelo Fisco" para "aplicação do contribuinte"

2. **xMun: Capitalização mista**  
   "SAO JOSE DO RIO PRETO" → "Sao Jose do Rio Preto"

3. **Formatação de valores decimais**  
   - qCom: 100 → 100.0000
   - vUnCom: 5.5 → 5.5000
   - qTrib: 100 → 100.0000
   - vUnTrib: 5.5 → 5.5000

4. **cDV - Dígito Verificador**  
   Adicionar campo `<cDV>` na seção `<ide>`

5. **dhEmi: Remover microsegundos**  
   2026-01-26T15:35:12.035099-03:00 → 2026-01-26T15:35:12-03:00

### 🟡 IMPORTANTE (Implementar em seguida)

6. **vTotTrib** (Lei da Transparência)  
   Adicionar em `<ICMSTot>` e em cada `<imposto>` do item

7. **indPag** (Indicador de pagamento)  
   Adicionar em `<detPag>`: 0=À vista, 1=A prazo

8. **xNome do destinatário**  
   "ASSOCIASSÃO" → "ASSOCIACAO" (remover Ç)

9. **CEST**  
   Adicionar código CEST para o produto (2300100)

10. **Campos ICMS Interestadual**  
    Adicionar vFCPUFDest, vICMSUFDest, vICMSUFRemet (mesmo que 0.00)

### 🟢 OPCIONAL (Melhorias)

11. **infRespTec**  
    Adicionar informações do responsável técnico

12. **cobr/fat**  
    Adicionar seção de cobrança/fatura

13. **PIS/COFINS**  
    Revisar CST (07 vs 49)

---

## 💡 CONCLUSÃO

### Causa Mais Provável do Erro 225:

1. **procEmi=1** quando deveria ser **0**
2. **Formatação incorreta dos valores** (faltam casas decimais)
3. **Capitalização do município** (maiúsculas quando deveria ser misto)
4. **Campo cDV ausente**
5. **dhEmi com microsegundos**

### Próximos Passos:

1. ✅ Corrigir procEmi para 0
2. ✅ Ajustar formatação de valores decimais (qCom, vUnCom, qTrib, vUnTrib)
3. ✅ Alterar xMun para capitalização mista
4. ✅ Adicionar cDV
5. ✅ Remover microsegundos do dhEmi
6. ✅ Adicionar vTotTrib
7. ✅ Adicionar indPag
8. ✅ Normalizar nome do destinatário (remover Ç)

---

**Observação Final:** O XML aprovado está em PRODUÇÃO com dados REAIS, enquanto o nosso está em HOMOLOGAÇÃO com CNPJs de TESTE. As diferenças estruturais e de formatação identificadas acima são as verdadeiras causas prováveis do Erro 225.

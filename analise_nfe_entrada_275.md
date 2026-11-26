# ANÁLISE NFe 275 - NOTA FISCAL DE ENTRADA

## 📋 Tipo de Operação
**NFe de Entrada** - Compra de bem de pessoa física que não emite nota fiscal

## ✅ ESTRUTURA DO XML - VALIDAÇÃO

### 1. Identificação (IDE)
```xml
<natOp>COMPRA IMOBILIZADO</natOp>
<tpNF>0</tpNF>  <!-- ✅ 0 = ENTRADA (CORRETO) -->
<idDest>1</idDest>  <!-- ✅ 1 = Operação interna (mesma UF) -->
<finNFe>1</finNFe>  <!-- ✅ 1 = NFe Normal -->
```
**Status:** ✅ CORRETO

### 2. Emitente (EMIT)
```xml
<CNPJ>57308098000166</CNPJ>
<xNome>ZOMN TECNOLOGIA LTDA</xNome>
<CRT>1</CRT>  <!-- Simples Nacional -->
```
**Status:** ✅ CORRETO - Empresa compradora emite a nota de entrada

### 3. Destinatário (DEST)
```xml
<CPF>34841609857</CPF>
<xNome>LEIZA FRANCO GARCIA</xNome>
<indIEDest>9</indIEDest>  <!-- 9 = Não contribuinte -->
```
**Status:** ✅ CORRETO - Pessoa física vendedora como destinatário

### 4. Produto
```xml
<xProd>Z001 - HAMINA OSCIUM (HARDWARE)</xProd>
<NCM>90314990</NCM>
<CFOP>1551</CFOP>  <!-- ✅ Compra de ativo imobilizado -->
<vProd>24995.75</vProd>
```
**Status:** ✅ CORRETO
- **CFOP 1551**: Compra de bem para o ativo imobilizado (dentro do estado)
- Valor: R$ 24.995,75

### 5. Impostos
```xml
<ICMSSN102>  <!-- Simples Nacional sem permissão de crédito -->
  <orig>0</orig>  <!-- Nacional -->
  <CSOSN>102</CSOSN>  <!-- Sem cálculo de ICMS -->
</ICMSSN102>
<PISNT><CST>07</CST></PISNT>  <!-- Isenção -->
<COFINSNT><CST>07</CST></COFINSNT>  <!-- Isenção -->
```
**Status:** ✅ CORRETO para Simples Nacional

### 6. Pagamento
```xml
<indPag>0</indPag>  <!-- À vista -->
<tPag>01</tPag>  <!-- Dinheiro -->
<vPag>24995.75</vPag>
```
**Status:** ✅ CORRETO

### 7. Transporte
```xml
<modFrete>9</modFrete>  <!-- Sem frete -->
```
**Status:** ✅ CORRETO

### 8. Responsável Técnico
```xml
<CNPJ>46840224000102</CNPJ>
<xContato>Carlos Renato</xContato>
<email>contato@emitemax.com.br</email>
```
**Status:** ✅ CORRETO

## 🎯 CONCLUSÃO GERAL

### ✅ XML ESTÁ 100% CORRETO PARA NFe DE ENTRADA

**Todos os campos estão adequados para:**
- Nota Fiscal de Entrada (tpNF = 0)
- Emitida pelo comprador (ZOMN)
- Vendedor pessoa física não contribuinte
- Compra de ativo imobilizado (CFOP 1551)
- Tributação Simples Nacional

### ⚠️ ÚNICO PROBLEMA: NUMERAÇÃO

O erro **"Duplicidade de NF-e"** ocorreu porque:
- A SEFAZ já tem uma NFe autorizada com **Número 1, Série 1** para este CNPJ
- Não é erro do XML ou da estrutura da nota
- **Solução:** Alterar o número da nota para **2** ou próximo disponível

## 📝 OBSERVAÇÕES IMPORTANTES

1. **NFe de Entrada é válida** quando:
   - Compra de pessoa física
   - Compra de produtor rural sem inscrição estadual
   - Compra de mercadoria em leilão
   - Entrada de mercadoria do exterior

2. **Legislação:**
   - Art. 17 do Ajuste SINIEF 07/2005
   - Pode ser emitida pelo **destinatário** (comprador)

3. **Campos invertidos:**
   - EMIT = Comprador (quem está emitindo a nota)
   - DEST = Vendedor (quem está vendendo mas não emite nota)
   - Isso é **correto** para nota de entrada!

## ✅ AÇÃO RECOMENDADA

Simplesmente **alterar o número da NFe para 2** e retransmitir.
A estrutura do XML está perfeita! 👍

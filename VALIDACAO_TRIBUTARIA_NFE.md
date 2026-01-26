# Validação Tributária de NFe

## ✅ Implementado em: 22/01/2026

Sistema de validação tributária que **impede a emissão** de NFes com erros fiscais, alertando o usuário para corrigir no cadastro de produtos ANTES de enviar para o SEFAZ.

---

## 📋 Validações Implementadas

### 1. **Simples Nacional (CRT = 1)**

#### ❌ CFOP 5401/6401 - INCOMPATÍVEL
- **CFOP 5401/6401** = Venda de produção própria com ST (empresa é SUBSTITUTA)
- **Problema**: Simples Nacional NÃO pode ser substituto tributário
- **Erro mostrado**:
  ```
  Item X: CFOP 5401 é incompatível com Simples Nacional.
  • CFOP 5401 = Venda de produção própria com ST (empresa é SUBSTITUTA)
  • Simples Nacional não pode ser substituto tributário
  • Sugestões:
    - CFOP 5405/6405 se for ST SUBSTITUÍDO (fornecedor já recolheu ST)
    - CFOP 5102/6102 para venda normal sem ST
  ```

#### ⚠️ CFOP 5405/6405 → Requer CSOSN 500
- **CFOP 5405/6405** = Venda de mercadoria ST na condição de SUBSTITUÍDO
- **CSOSN correto**: 500 (ICMS cobrado anteriormente por ST)
- **Erro mostrado se CSOSN != 500**:
  ```
  Item X: CFOP 5405 requer CSOSN 500.
  • CFOP 5405 = Mercadoria ST já tributada (você é SUBSTITUÍDO)
  • CSOSN atual: 102
  • CSOSN 500 = ICMS cobrado anteriormente por ST
  • Corrija o CSOSN no cadastro do produto
  ```

#### ℹ️ CFOP 5102/6102 - Operação Normal
- **CFOP 5102/6102** = Venda normal sem ST
- **CSOSN aceitos**: 102, 103, 300, 400, 900
- **Erro mostrado se CSOSN inválido**:
  ```
  Item X: CFOP 5102 não é compatível com CSOSN 500.
  • Para operação normal, use:
    - CSOSN 102: Tributada sem crédito
    - CSOSN 103: Isenção com crédito
    - CSOSN 400: Não tributada
    - CSOSN 900: Outros
  ```

### 2. **Regime Normal (CRT = 3)**

#### ⚠️ CFOP 5405/6405 → Requer CST 10 ou 60
- **CFOP 5405/6405** = Mercadoria ST (substituído)
- **CST corretos**: 10 (Tributada com ST) ou 60 (ICMS ST cobrado anteriormente)
- **Erro mostrado se CST inválido**:
  ```
  Item X: CFOP 5405 requer CST 10 ou 60.
  • CFOP 5405 = Mercadoria ST (substituído)
  • CST atual: 00
  • CST 10 = Tributada com ST
  • CST 60 = ICMS ST cobrado anteriormente
  ```

---

## 🔍 Quando a Validação é Executada

A validação tributária é executada **ANTES** de gerar o XML da NFe, em dois momentos:

1. **Preview do XML** (botão "Visualizar XML")
   - Retorna erro via JSON
   - Mostra mensagem de erro na tela

2. **Emissão da NFe** (botão "Emitir NFe")
   - Interrompe o processo
   - Exibe mensagens de erro com `flash()`
   - Retorna usuário para tela de emissão

---

## 📝 Como Corrigir os Erros

### Exemplo 1: CFOP 5401 no Simples Nacional
**Erro**: Produto com CFOP 5401 em empresa Simples Nacional

**Solução**:
1. Acessar **Cadastro de Produtos**
2. Editar o produto problemático
3. **Verificar a situação tributária**:
   - Se o produto tem ST e você é **substituído** (fornecedor já recolheu ST):
     - Mudar CFOP para **5405**
     - Mudar CSOSN para **500**
   - Se é venda normal sem ST:
     - Mudar CFOP para **5102**
     - Mudar CSOSN para **102** (ou outro adequado)

### Exemplo 2: CFOP 5405 com CSOSN 102
**Erro**: Produto com CFOP 5405 (ST substituído) mas CSOSN 102 (operação normal)

**Solução**:
1. Acessar **Cadastro de Produtos**
2. Editar o produto
3. Alterar CSOSN para **500**
   - CSOSN 500 = ICMS cobrado anteriormente por ST

---

## 🎯 Benefícios da Validação

✅ **Previne erros SEFAZ**: Detecta problemas ANTES de enviar para SEFAZ  
✅ **Mensagens claras**: Explica o erro e como corrigir  
✅ **Economia de tempo**: Evita tentativas de emissão que serão rejeitadas  
✅ **Compliance fiscal**: Garante conformidade com regras tributárias  
✅ **Reduz erro 225**: Elimina incompatibilidades CFOP x CSOSN/CST  

---

## 🔧 Arquivos Modificados

1. **services/nfe_service.py**
   - Função `validar_tributacao_nfe()` (linhas 59-156)
   - Integrada na função `generate_nfe_xml()` (linha 1254)

2. **routes/nfe_routes.py**
   - Tratamento de `ValueError` na emissão (linhas 323-336)
   - Tratamento de `ValueError` no preview (linhas 220-224)

---

## 📊 Regras Tributárias - Resumo

| CRT | CFOP | CST/CSOSN Correto | Descrição |
|-----|------|-------------------|-----------|
| 1 (Simples) | 5401/6401 | ❌ **INCOMPATÍVEL** | Não pode ser substituto |
| 1 (Simples) | 5405/6405 | 500 | ST substituído |
| 1 (Simples) | 5102/6102 | 102, 103, 300, 400, 900 | Operação normal |
| 3 (Normal) | 5405/6405 | 10, 60 | ST substituído |

---

## 🧪 Como Testar

### Teste 1: CFOP Incompatível
1. Criar produto com CFOP **5401**
2. Empresa em **Simples Nacional**
3. Tentar emitir NFe
4. **Resultado esperado**: Erro informando incompatibilidade e sugerindo 5405 ou 5102

### Teste 2: CSOSN Incorreto
1. Criar produto com CFOP **5405** e CSOSN **102**
2. Tentar emitir NFe
3. **Resultado esperado**: Erro solicitando alterar CSOSN para 500

### Teste 3: Validação OK
1. Produto com CFOP **5405** e CSOSN **500**
2. Emitir NFe
3. **Resultado esperado**: XML gerado com sucesso, envio para SEFAZ

---

## 🆘 Suporte

Se aparecer erro de validação:

1. **Leia a mensagem completa** - ela explica o problema e a solução
2. **Acesse o cadastro de produtos** - corrija CFOP e CSOSN conforme indicado
3. **Salve as alterações** - não esqueça de salvar o produto
4. **Tente emitir novamente** - a validação passará se estiver correto

Em caso de dúvida sobre qual CFOP/CSOSN usar:
- Consulte seu contador/consultor fiscal
- Verifique a nota fiscal do fornecedor (se houver ST)
- Analise a operação: você é substituto, substituído ou operação normal?

---

## 📚 Referências Fiscais

- **CFOP 5401**: Venda de produção do estabelecimento em operação com produto sujeito ao regime de substituição tributária, na condição de contribuinte substituto
- **CFOP 5405**: Venda de mercadoria, adquirida ou recebida de terceiros, sujeita ao regime de substituição tributária, na condição de contribuinte substituído
- **CFOP 5102**: Venda de mercadoria adquirida ou recebida de terceiros
- **CSOSN 102**: Tributada pelo Simples Nacional sem permissão de crédito
- **CSOSN 500**: ICMS cobrado anteriormente por substituição tributária

---

**Desenvolvido por**: Sistema NFe EmiteMax  
**Data**: 22 de janeiro de 2026  
**Versão**: 1.0

# Análise Documentação GISS Online - São José do Rio Preto

## 📋 Documentos Analisados

Data: 29/01/2026

### Arquivos Baixados:
1. ✅ `schemas_modificados_gissv2.zip` - Schemas XSD Nota Nacional v2.04
2. ✅ `Schemas_XSD_Servicos_Tomados_CST.zip` - Schemas para Serviços Tomados
3. ✅ `GUIA RÁPIDO - CST - V2.2.pdf` - Guia de Cadastro de Serviços de Terceiros
4. ✅ `EXEMPLOS CST.rar` - Exemplos práticos

---

## 🔍 Diferenças Identificadas vs Nossa Implementação

### 1. **Namespaces (CRÍTICO)**

**GISS Online usa:**
```xml
xmlns:p="http://www.giss.com.br/enviar-lote-rps-envio-v2_04.xsd"
xmlns:p1="http://www.giss.com.br/tipos-v2_04.xsd"
xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
```

**Nossa implementação usa:**
```python
NS_NFSE = "http://www.abrasf.org.br/nfse.xsd"
NS_TIPOS = "http://www.abrasf.org.br/nfse.xsd"
NS_DSIG = "http://www.w3.org/2000/09/xmldsig#"
```

**❌ PROBLEMA:** Namespaces diferentes! GISS usa padrão próprio baseado em ABRASF mas modificado.

---

### 2. **Estrutura do XML (CRÍTICO)**

**GISS Online:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<p:EnviarLoteRpsEnvio xmlns:p="http://www.giss.com.br/enviar-lote-rps-envio-v2_04.xsd" 
                      xmlns:p1="http://www.giss.com.br/tipos-v2_04.xsd">
  <p:LoteRps versao="2.04">
    <p1:NumeroLote>1</p1:NumeroLote>
    <p1:Prestador>
      <p1:CpfCnpj>
        <p1:Cnpj>12345678000199</p1:Cnpj>
      </p1:CpfCnpj>
      <p1:InscricaoMunicipal>12345</p1:InscricaoMunicipal>
    </p1:Prestador>
    <p1:QuantidadeRps>1</p1:QuantidadeRps>
    <p1:ListaRps>
      <p1:Rps>
        <p1:InfDeclaracaoPrestacaoServico Id="rps1">
          <!-- Dados do RPS -->
        </p1:InfDeclaracaoPrestacaoServico>
        <ds:Signature>
          <!-- Assinatura digital -->
        </ds:Signature>
      </p1:Rps>
    </p1:ListaRps>
  </p:LoteRps>
</p:EnviarLoteRpsEnvio>
```

**Nossa implementação:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<EnviarLoteRpsEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
  <LoteRps versao="2.04" Id="lote1">
    <NumeroLote>1</NumeroLote>
    <!-- Estrutura diferente -->
  </LoteRps>
</EnviarLoteRpsEnvio>
```

**❌ PROBLEMA:** Estrutura completamente diferente com prefixos de namespace.

---

### 3. **Campos IBS/CBS (NOVO)**

**GISS adiciona campos da Reforma Tributária:**
```xml
<p1:IBSCBS>
  <p1:finNFSe>0</p1:finNFSe>
  <p1:indFinal>0</p1:indFinal>
  <p1:cIndOp>001</p1:cIndOp>
  <p1:indDest>0</p1:indDest>
  <p1:valores>
    <p1:trib>
      <p1:gIBSCBS>
        <p1:CST>01</p1:CST>
        <p1:cClassTrib>00123456</p1:cClassTrib>
      </p1:gIBSCBS>
    </p1:trib>
    <p1:cLocalidadeIncid>3549805</p1:cLocalidadeIncid>
    <p1:pRedutor>0.00</p1:pRedutor>
  </p1:valores>
</p1:IBSCBS>
```

**❌ PROBLEMA:** Campos obrigatórios que não temos!

---

### 4. **Campos de Tributos Totais**

```xml
<p1:trib>
  <p1:totTrib>
    <p1:pTotTrib>
      <p1:pTotTribFed>5.00</p1:pTotTribFed>
      <p1:pTotTribEst>0.00</p1:pTotTribEst>
      <p1:pTotTribMun>2.00</p1:pTotTribMun>
    </p1:pTotTrib>
  </p1:totTrib>
</p1:trib>
```

**❌ PROBLEMA:** Campos obrigatórios que não implementamos!

---

### 5. **Código NBS (Obrigatório)**

```xml
<p1:CodigoNbs>1.0401.30.10</p1:CodigoNbs>
```

**❌ PROBLEMA:** Campo obrigatório que não temos na nossa estrutura!

---

### 6. **Assinatura do RPS**

**GISS:** Assina dentro de cada `<p1:Rps>`, depois do `<p1:InfDeclaracaoPrestacaoServico>`

**Nossa implementação:** Assumimos assinatura do lote inteiro

**❌ PROBLEMA:** Localização da assinatura pode estar incorreta!

---

## 🎯 Correções Necessárias

### ALTA PRIORIDADE (Bloqueante):

1. **Corrigir Namespaces**
   - Usar `http://www.giss.com.br/` ao invés de `http://www.abrasf.org.br/`
   - Adicionar prefixos `p:` e `p1:` nas tags

2. **Corrigir Estrutura XML**
   - Root: `<p:EnviarLoteRpsEnvio>` não `<EnviarLoteRpsEnvio>`
   - LoteRps: `<p:LoteRps>` não `<LoteRps>`
   - Campos internos: usar prefixo `p1:`

3. **Adicionar Campos IBS/CBS**
   - `finNFSe` - Finalidade da NFS-e
   - `indFinal` - Indicador de consumidor final
   - `cIndOp` - Código indicador da operação
   - `indDest` - Indicador de destinatário
   - `CST` - Código de Situação Tributária
   - `cClassTrib` - Código de Classificação Tributária
   - `cLocalidadeIncid` - Código da localidade de incidência

4. **Adicionar Campos de Tributos Totais**
   - `pTotTribFed` - Percentual total tributos federais
   - `pTotTribEst` - Percentual total tributos estaduais
   - `pTotTribMun` - Percentual total tributos municipais

5. **Adicionar Código NBS**
   - Tabela de códigos NBS da ANS
   - Campo obrigatório no serviço

### MÉDIA PRIORIDADE:

6. **Validar Assinatura Digital**
   - Verificar se está assinando a tag correta
   - Confirmar estrutura da assinatura

7. **Adicionar Validações**
   - Validar campos obrigatórios GISS
   - Validar formato de códigos

### BAIXA PRIORIDADE:

8. **Implementar Campos Opcionais**
   - Comércio Exterior (`comExt`)
   - Construção Civil (`ConstrucaoCivil`)
   - Evento (`Evento`)
   - Dedução (`Deducao`)

---

## 📊 Tabelas de Códigos

### Finalidade NFS-e (finNFSe):
- `0` - Normal
- `1` - Complementar
- `2` - Ajuste
- `3` - Substituição

### Indicador Final (indFinal):
- `0` - Não
- `1` - Sim (Consumidor Final)

### Indicador Destinatário (indDest):
- `0` - Operação interna
- `1` - Operação interestadual
- `2` - Operação com exterior

### Exigibilidade ISS (ExigibilidadeISS):
- `0` - Exigível
- `1` - Não incidência
- `2` - Isenção
- `3` - Exportação
- `4` - Imunidade
- `5` - Exigibilidade suspensa
- `6` - Exigibilidade suspensa por decisão judicial
- `7` - Exigibilidade suspensa por processo administrativo

---

## 🚀 Plano de Ação

### Etapa 1: Correção dos Namespaces
- [ ] Atualizar `NFSeService.__init__()` com namespaces GISS
- [ ] Corrigir todos os `etree.SubElement()` para usar prefixos corretos
- [ ] Testar geração XML com nova estrutura

### Etapa 2: Adicionar Campos IBS/CBS
- [ ] Atualizar modelo `NFSeNacional` com novos campos
- [ ] Atualizar modelo `ServicoNFSe` com campos IBS/CBS
- [ ] Adicionar valores padrão para testes

### Etapa 3: Adicionar Tributos Totais
- [ ] Calcular percentuais de tributos
- [ ] Adicionar no XML de geração

### Etapa 4: Código NBS
- [ ] Criar tabela de códigos NBS
- [ ] Adicionar campo no formulário
- [ ] Validar entrada

### Etapa 5: Testar Homologação
- [ ] Gerar XML de teste
- [ ] Assinar XML
- [ ] Enviar para ambiente de homologação
- [ ] Validar resposta

---

## ✅ Conclusão

A implementação atual está **70% correta** mas precisa de ajustes críticos:

**O que está correto:**
- ✅ Lógica de assinatura digital (PyNFe)
- ✅ Estrutura SOAP básica
- ✅ Campos principais de serviço
- ✅ Dados de prestador/Tomadores
- ✅ Cálculos de ISS

**O que precisa ser corrigido:**
- ❌ Namespaces (BLOQUEANTE)
- ❌ Estrutura XML (BLOQUEANTE)
- ❌ Campos IBS/CBS (BLOQUEANTE)
- ❌ Tributos totais (BLOQUEANTE)
- ❌ Código NBS (BLOQUEANTE)

**Estimativa:** 4-6 horas de trabalho para correção completa.

**Prioridade:** ALTA - Sistema não funcionará sem essas correções!

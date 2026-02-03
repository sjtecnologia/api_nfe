# 🔍 AUDITORIA COMPLETA - Campos NFe Emissão
**Data:** 03/02/2026  
**Sistema:** api_nfe (Produção)  
**Objetivo:** Verificar se todos os campos do formulário estão sendo utilizados no XML gerado

---

## 📋 CAMPOS DADOS GERAIS DA NFE

| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `modelo` | Modelo NFe | ✅ SIM | nfelib_service.py - ide.mod | ✅ OK |
| `serie` | Série | ✅ SIM | nfelib_service.py - ide.serie | ✅ OK |
| `numero_nfe` | Número NFe | ✅ SIM | nfelib_service.py - ide.nNF | ✅ OK |
| `tpNF` | Tipo Operação | ✅ SIM | nfelib_service.py - ide.tpNF | ✅ OK |
| `finNFe` | Finalidade | ✅ SIM | nfelib_service.py - ide.finNFe | ✅ OK |
| `indPres` | Indicador Presença | ✅ SIM | nfelib_service.py - ide.indPres | ✅ OK |
| `natOp` | Natureza Operação | ✅ SIM | nfelib_service.py - ide.natOp | ✅ OK |
| `dataEmissao` | Data Emissão | ✅ SIM | nfelib_service.py - ide.dhEmi | ✅ OK |
| `destinatario` | Destinatário | ✅ SIM | nfelib_service.py - dest | ✅ OK |

---

## 💰 CAMPOS PAGAMENTO

| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `formaPagamento` | Forma Pagamento | ✅ SIM | nfelib_service.py - pag.detPag.tPag | ✅ OK |
| `valorPagamento` | Valor Pagamento | ✅ SIM | nfelib_service.py - pag.detPag.vPag | ✅ OK |

---

## 🚚 CAMPOS TRANSPORTE

| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `modFrete` | Modalidade Frete | ✅ SIM | nfelib_service.py - transp.modFrete | ✅ OK |
| `transportadoraNome` | Nome Transportadora | ⚠️ PARCIAL | nfelib_service.py - transp.transporta.xNome | ⚠️ VERIFICAR |
| `transportadoraCnpjCpf` | CNPJ/CPF Transportadora | ⚠️ PARCIAL | nfelib_service.py - transp.transporta.CNPJ/CPF | ⚠️ VERIFICAR |
| `transportadoraEndereco` | Endereço Transportadora | ⚠️ PARCIAL | nfelib_service.py - transp.transporta.xEnder | ⚠️ VERIFICAR |
| `transportadoraMunicipio` | Município Transportadora | ⚠️ PARCIAL | nfelib_service.py - transp.transporta.xMun | ⚠️ VERIFICAR |
| `transportadoraUF` | UF Transportadora | ⚠️ PARCIAL | nfelib_service.py - transp.transporta.UF | ⚠️ VERIFICAR |
| `transportadoraIE` | IE Transportadora | ⚠️ PARCIAL | nfelib_service.py - transp.transporta.IE | ⚠️ VERIFICAR |
| `transportadoraANTT` | ANTT | ❌ NÃO LOCALIZADO | - | ⚠️ INVESTIGAR |
| `veiculoPlaca` | Placa Veículo | ⚠️ PARCIAL | nfelib_service.py - transp.veicTransp.placa | ⚠️ VERIFICAR |
| `veiculoUF` | UF Veículo | ⚠️ PARCIAL | nfelib_service.py - transp.veicTransp.UF | ⚠️ VERIFICAR |
| `volumeQuantidade` | Qtd Volumes | ✅ SIM | nfelib_service.py - transp.vol.qVol | ✅ OK |
| `volumeEspecie` | Espécie Volume | ✅ SIM | nfelib_service.py - transp.vol.esp | ✅ OK |
| `volumeMarca` | Marca Volume | ✅ SIM | nfelib_service.py - transp.vol.marca | ✅ OK |
| `volumeNumeracao` | Numeração Volume | ✅ SIM | nfelib_service.py - transp.vol.nVol | ✅ OK |
| `volumePesoBruto` | Peso Bruto | ✅ SIM | nfelib_service.py - transp.vol.pesoB | ✅ OK |
| `volumePesoLiquido` | Peso Líquido | ✅ SIM | nfelib_service.py - transp.vol.pesoL | ✅ OK |

---

## 🏛️ CAMPOS IBS/CBS (REFORMA TRIBUTÁRIA)

| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `classificacao_ibs_cbs_id` | Classificação IBS/CBS | ✅ SIM | Implementado 03/02/2026 | ✅ OK |
| `aliquota_ibs_uf` | Alíquota IBS UF | ⚠️ READONLY | Calculado automaticamente | ℹ️ INFO |
| `aliquota_ibs_mun` | Alíquota IBS Municipal | ⚠️ READONLY | Calculado automaticamente | ℹ️ INFO |
| `aliquota_cbs` | Alíquota CBS | ⚠️ READONLY | Calculado automaticamente | ℹ️ INFO |

---

## 🔄 CAMPOS ICMS ST (SUBSTITUIÇÃO TRIBUTÁRIA)

| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `vBCSTRet` | BC ST Retido | ❌ NÃO LOCALIZADO | - | ⚠️ INVESTIGAR |
| `pST` | % ST | ❌ NÃO LOCALIZADO | - | ⚠️ INVESTIGAR |
| `vICMSSubstituto` | Valor ICMS Substituto | ❌ NÃO LOCALIZADO | - | ⚠️ INVESTIGAR |
| `vICMSSTRet` | Valor ICMS ST Retido | ❌ NÃO LOCALIZADO | - | ⚠️ INVESTIGAR |

---

## 📝 CAMPOS INFORMAÇÕES ADICIONAIS

| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `infCpl` | Informações Complementares | ✅ SIM | nfelib_service.py - infAdic.infCpl | ✅ OK |
| `gerar_danfe_auto` | Gerar DANFE Automático | ℹ️ CONTROLE | Controle frontend | ℹ️ INFO |

---

## 📦 CAMPOS DOS ITENS

### Identificação do Produto
| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `produto_${i}` | Produto (select) | ✅ SIM | nfelib_service.py - prod.cProd, xProd | ✅ OK |
| `codigo_produto_${i}` | Código Produto | ✅ SIM | nfelib_service.py - prod.cProd | ✅ OK |
| `unidade_${i}` | Unidade | ✅ SIM | nfelib_service.py - prod.uCom | ✅ OK |
| `quantidade_${i}` | Quantidade | ✅ SIM | nfelib_service.py - prod.qCom | ✅ OK |
| `valor_unitario_${i}` | Valor Unitário | ✅ SIM | nfelib_service.py - prod.vUnCom | ✅ OK |
| `valor_total_${i}` | Valor Total | ✅ SIM | nfelib_service.py - prod.vProd | ✅ OK |
| `ncm_${i}` | NCM | ✅ SIM | nfelib_service.py - prod.NCM | ✅ OK |
| `cfop_${i}` | CFOP | ✅ SIM | nfelib_service.py - prod.CFOP | ✅ OK |
| `origem_${i}` | Origem Mercadoria | ✅ SIM | nfelib_service.py - ICMS*.orig | ✅ OK |

### Tributação ICMS
| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `csosn_${i}` | CSOSN (Simples Nacional) | ✅ SIM | nfelib_service.py - ICMSSN*.CSOSN | ✅ OK |
| `cst_icms_${i}` | CST ICMS (Regime Normal) | ✅ SIM | nfelib_service.py - ICMS*.CST | ✅ OK |
| `aliquota_icms_${i}` | Alíquota ICMS | ✅ SIM | nfelib_service.py - ICMS*.pICMS | ✅ OK |
| `reducao_base_icms_${i}` | Redução Base ICMS | ✅ SIM | nfelib_service.py - ICMS20.pRedBC | ✅ OK |
| `modalidade_bc_icms_${i}` | Modalidade BC ICMS | ✅ SIM | nfelib_service.py - ICMS*.modBC | ✅ OK |
| `motivo_desoneracao_icms_${i}` | Motivo Desoneração | ❌ NÃO LOCALIZADO | - | ⚠️ INVESTIGAR |
| `bc_icms_${i}` | Base Cálculo ICMS | ✅ SIM | nfelib_service.py - ICMS*.vBC | ✅ OK |
| `valor_icms_${i}` | Valor ICMS | ✅ SIM | nfelib_service.py - ICMS*.vICMS | ✅ OK |

### Tributação PIS
| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `cst_pis_${i}` | CST PIS | ✅ SIM | nfelib_service.py - PIS*.CST | ✅ OK |
| `aliquota_pis_${i}` | Alíquota PIS | ✅ SIM | nfelib_service.py - PISAliq.pPIS | ✅ OK |

### Tributação COFINS
| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `cst_cofins_${i}` | CST COFINS | ✅ SIM | nfelib_service.py - COFINS*.CST | ✅ OK |
| `aliquota_cofins_${i}` | Alíquota COFINS | ✅ SIM | nfelib_service.py - COFINSAliq.pCOFINS | ✅ OK |

### Tributação IPI
| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `cst_ipi_${i}` | CST IPI | ❌ NÃO USADO | nfelib_service.py NÃO TEM IPI | 🔴 CRÍTICO |
| `aliquota_ipi_${i}` | Alíquota IPI | ❌ NÃO USADO | nfelib_service.py NÃO TEM IPI | 🔴 CRÍTICO |

### IBS/CBS por Item
| Campo Form | Nome | Usado no XML? | Localização no Código | Status |
|------------|------|---------------|----------------------|--------|
| `classificacao_ibs_cbs_id_${i}` | Classificação IBS/CBS | ✅ SIM | Implementado 03/02/2026 | ✅ OK |

---

## 🚨 PROBLEMAS IDENTIFICADOS

### ❌ CRÍTICOS (Campos não usados mas presentes no form)

1. **IPI nos Itens** 🔴 CONFIRMADO - CÓDIGO NÃO TEM IPI
   - **Campos:** `cst_ipi_${i}`, `aliquota_ipi_${i}`
   - **Status:** Presentes no formulário mas TOTALMENTE AUSENTE no código
   - **Localização:** nfe_nfelib_service.py linha 656 - imposto = Nfe.InfNfe.Det.Imposto(ICMS, PIS, COFINS) - SEM IPI
   - **Impacto:** 🔴 CRÍTICO - IPI não está sendo gerado no XML
   - **Consequências:** Produtos industrializados sem IPI = REJEIÇÃO SEFAZ
   - **Ação:** IMPLEMENTAR URGENTE processamento IPI

2. **Motivo Desoneração ICMS** 🟡 CONFIRMADO - AUSENTE
   - **Campo:** `motivo_desoneracao_icms_${i}`
   - **Status:** Presente no formulário mas NÃO é usado no XML
   - **Localização:** nfe_nfelib_service.py linhas 530-562 - ICMS20, ICMS40 sem motDesICMS
   - **Impacto:** 🟡 MÉDIO - Obrigatório para CST 20, 30, 40, 41, 50 com desoneração
   - **Consequências:** Se houver desoneração e campo obrigatório, pode gerar REJEIÇÃO
   - **Ação:** ADICIONAR campo motDesICMS nos objetos ICMS20 e ICMS40

3. **ICMS ST (Substituição Tributária)**
   - **Campos:** `vBCSTRet`, `pST`, `vICMSSubstituto`, `vICMSSTRet`
   - **Status:** ✅ IMPLEMENTADO apenas em ICMSSN500 (linha 487-490)
   - **Valores:** HARDCODED "0.00" - não pega do form
   - **Impacto:** Alto - Campos do form NÃO são usados
   - **Ação:** CONECTAR campos do form ao ICMSSN500

4. **ANTT Transportadora**
   - **Campo:** `transportadoraANTT`
   - **Status:** Presente no form mas não usado
   - **Impacto:** Baixo - Opcional
   - **Ação:** ADICIONAR se obrigatório

### ⚠️ MÉDIOS (Campos parcialmente implementados)

5. **Dados Transportadora**
   - **Status:** Campos existem mas CONDICIONAIS (modFrete != 9)
   - **Impacto:** Médio
   - **Ação:** VERIFICAR lógica condicional está correta

---

## ✅ RECOMENDAÇÕES

### Prioridade ALTA (Implementar Imediatamente)

1. **✅ Implementar IPI**
   ```python
   # Em nfe_nfelib_service.py, após COFINS
   cst_ipi = item.get('cst_ipi')
   aliq_ipi = Decimal(str(item.get('aliquota_ipi', '0')))
   
   if cst_ipi and aliq_ipi > 0:
       ipi_trib = Nfe.InfNfe.Det.Imposto.Ipi.Ipitrib(
           CST=cst_ipi,
           vBC=f"{valor_total:.2f}",
           pIPI=f"{aliq_ipi:.2f}",
           vIPI=f"{(valor_total * aliq_ipi / 100):.2f}"
       )
       ipi = Nfe.InfNfe.Det.Imposto.Ipi(IPITrib=ipi_trib)
   else:
       ipi_nt = Nfe.InfNfe.Det.Imposto.Ipi.Ipint(CST=cst_ipi or "99")
       ipi = Nfe.InfNfe.Det.Imposto.Ipi(IPINT=ipi_nt)
   
   # Adicionar IPI ao imposto
   imposto = Nfe.InfNfe.Det.Imposto(
       vTotTrib=v_tot_trib,
       ICMS=icms,
       IPI=ipi,  # ← ADICIONAR
       PIS=pis,
       COFINS=cofins
   )
   ```

2. **✅ Implementar motDesICMS**
   ```python
   # Para CST 20, 30, 40, 41, 50
   motivo_deson = item.get('motivo_desoneracao_icms')
   if motivo_deson and cst_item in ['20', '30', '40', '41', '50']:
       # Adicionar motDesICMS ao ICMS
       icms_obj.motDesICMS = motivo_deson
   ```

3. **✅ Validar ICMS ST**
   - Verificar se nfelib suporta ICMSSN500 com campos ST
   - Se não, documentar limitação

### Prioridade MÉDIA

4. **Documentar limitações conhecidas**
   - Criar arquivo LIMITACOES_NFE.md listando campos não suportados
   - Informar usuário no frontend sobre campos apenas informativos

5. **Adicionar validações frontend**
   - Ocultar campos IPI se não implementado
   - Ocultar campos ST se não implementado
   - Mostrar tooltip explicativo

---

## 📊 ESTATÍSTICAS

- **Total de campos no formulário:** ~80 campos
- **Campos funcionais (usados no XML):** ~62 campos (77%)
- **Campos não usados (CRÍTICO):** ~6 campos (8%)
  - ❌ cst_ipi (AUSENTE no código)
  - ❌ aliquota_ipi (AUSENTE no código)
  - ❌ motivo_desoneracao_icms (AUSENTE no código)
  - ⚠️ vBCSTRet (hardcoded "0.00")
  - ⚠️ pST (hardcoded "0.00")
  - ⚠️ vICMSSubstituto (hardcoded "0.00")
  - ⚠️ vICMSSTRet (hardcoded "0.00")
- **Campos informativos (readonly/controle):** ~12 campos (15%)

---

## 🎯 PRÓXIMOS PASSOS - ORDEM DE PRIORIDADE

### 🔴 URGENTE (Bloqueante para produção)

1. **✅ Implementar IPI nos itens**
   - Adicionar campos IPI ao objeto Nfe.InfNfe.Det.Imposto
   - Processar cst_ipi e aliquota_ipi do form
   - Adicionar ao total vIPI
   
2. **✅ Implementar motDesICMS**
   - Adicionar ao ICMS20, ICMS40 quando houver desoneração
   - Validar CSTs que exigem motDesICMS

### 🟡 ALTA (Funcionalidade incompleta)

3. **✅ Conectar campos ICMS ST ao form**
   - Pegar vBCSTRet, pST, vICMSSubstituto, vICMSSTRet do form
   - Remover valores hardcoded "0.00"
   - Validar quando CSOSN=500

### 🟢 MÉDIA (Melhorias)

4. **Validar transportadora ANTT**
   - Verificar se campo deve ser usado
   - Adicionar ao XML se obrigatório

5. **Documentar limitações conhecidas**
   - Criar arquivo LIMITACOES_NFE.md listando campos não suportados
   - Informar usuário no frontend sobre campos apenas informativos

6. **Adicionar validações frontend**
   - Alertas quando IPI não preenchido em produtos industrializados
   - Validação motDesICMS quando CST exigir

---

**Status Geral:** 🔴 **SISTEMA COM CAMPOS NÃO FUNCIONAIS**

**Risco:** 🔴 **CRÍTICO** - IPI não sendo gerado pode causar:
- Rejeição SEFAZ em produtos industrializados
- Passivo fiscal por omissão de imposto devido
- Multas e penalidades

**Risco Motivo Desoneração:** 🟡 **MÉDIO** - Pode causar rejeição se houver desoneração de ICMS

**Risco ICMS ST:** 🟡 **MÉDIO** - Valores fixos "0.00" impedem operações com substituição tributária

**Ação Imediata Requerida:** 
1. ❌ BLOQUEAR emissão de NFe com produtos industrializados ATÉ implementar IPI
2. ✅ Implementar IPI URGENTE
3. ✅ Implementar motDesICMS
4. ✅ Conectar campos ICMS ST do form

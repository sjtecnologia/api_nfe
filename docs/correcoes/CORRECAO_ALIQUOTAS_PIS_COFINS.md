# 🔧 Correção: TODOS os Tributos Incorretos (ICMS, PIS, COFINS, IPI)

## 📋 Problema Relatado

Ao emitir NFe, o sistema estava preenchendo tributos que não correspondiam às regras tributárias cadastradas:
- **Problema**: Alíquotas incorretas em TODOS os tributos (ICMS, PIS, COFINS, IPI)
- **Exemplo**: Alíquota PIS 1.65% e COFINS 7.60% (valores de produtos anteriores)
- **Esperado**: Alíquotas das regras cadastradas
- **CFOP**: 5101
- **NCM**: 85285900

## 🔴 Escopo Ampliado

**Problema não era só PIS/COFINS**, mas **TODOS os tributos**:
- ❌ ICMS (alíquota, CSOSN/CST)
- ❌ PIS (alíquota, CST)
- ❌ COFINS (alíquota, CST)
- ❌ IPI (alíquota, CST)

## 🔍 Causa Raiz

A função `aplicarRegraTributaria()` implementada estava funcionando corretamente, MAS:

1. **Não limpava campos antes de aplicar** - Se um produto anterior tivesse alíquotas diferentes, elas permaneciam no formulário
2. **Só sobrescrevia se a regra tivesse valores** - Se a regra não tivesse `aliquota_pis` ou `aliquota_cofins`, os campos não eram alterados
3. **Valores antigos persistiam** - O usuário via alíquotas de produtos/operações anteriores

### Fluxo do Problema:

```
1. Usuário seleciona Produto A → Carrega alíquotas (1.65% PIS, 7.60% COFINS)
2. Função aplicarRegraTributaria() busca regra → Regra não tem alíquotas preenchidas
3. Função NÃO sobrescreve campos → Valores antigos permanecem
4. Usuário vê alíquotas incorretas
```

## ✅ Solução Implementada

### 1. Modificação no `templates/admin/nfes/emitir.html`

#### **Antes (PROBLEMA):**
```javascript
// ❌ Aplicava valores SEM limpar campos antes
if (result.regra.csosn_id) {
    csosnSelect.val(result.regra.csosn_id).trigger('change');
}

if (result.regra.aliquota_icms) {
    aliquotaInput.value = result.regra.aliquota_icms;
}
// ... apenas aplicava SE a regra tivesse valores
// ... valores antigos permaneciam se regra não tivesse o campo
```

#### **Depois (CORRIGIDO):**
```javascript
// ✅ 1. BUSCAR TODOS OS CAMPOS TRIBUTÁRIOS
const csosnSelect = $(`select[name="csosn_${itemId}"]`);
const cstIcmsSelect = $(`select[name="cst_icms_${itemId}"]`);
const aliquotaIcmsInput = document.querySelector(`input[name="aliquota_icms_${itemId}"]`);
const cstPisInput = document.querySelector(`input[name="cst_pis_${itemId}"]`);
const aliquotaPisInput = document.querySelector(`input[name="aliquota_pis_${itemId}"]`);
// ... busca TODOS os campos primeiro

// ✅ 2. LIMPAR TODOS OS CAMPOS (antes de aplicar regra)
if (csosnSelect.length) csosnSelect.val('').trigger('change');
if (cstIcmsSelect.length) cstIcmsSelect.val('').trigger('change');
if (aliquotaIcmsInput) aliquotaIcmsInput.value = '0.00';
if (cstPisInput) cstPisInput.value = '';
if (aliquotaPisInput) aliquotaPisInput.value = '0.00';
// ... limpa TODOS os campos

// ✅ 3. APLICAR VALORES DA REGRA (SE a regra tiver)
if (result.regra.csosn_icms && csosnSelect.length) {
    console.log('Aplicando CSOSN:', result.regra.csosn_icms);
    csosnSelect.val(result.regra.csosn_icms).trigger('change');
}

if (result.regra.aliquota_icms && aliquotaIcmsInput) {
    console.log('Aplicando alíquota ICMS:', result.regra.aliquota_icms);
    aliquotaIcmsInput.value = result.regra.aliquota_icms;
}
// ... aplica os valores da regra com logs detalhados
```

### 2. Modificação no `routes/api_routes.py`

#### **Logs Adicionados:**
```python
if regra_encontrada:
    regra_dict = regra_encontrada.to_dict()
    print(f"✅ Regra encontrada ID {regra_encontrada.regra_tributacao_id}:")
    print(f"   Descrição: {regra_dict.get('descricao_regra')}")
    print(f"   ICMS: {regra_dict.get('aliquota_icms')}% | CSOSN: {regra_dict.get('csosn_icms')}")
    print(f"   PIS: {regra_dict.get('aliquota_pis')}% | CST: {regra_dict.get('cst_pis')}")
    print(f"   COFINS: {regra_dict.get('aliquota_cofins')}% | CST: {regra_dict.get('cst_cofins')}")
    
    return jsonify({'sucesso': True, 'regra': regra_dict}), 200
else:
    print(f"⚠️ Nenhuma regra encontrada para:")
    print(f"   NCM: {ncm_codigo}, CFOP: {cfop_codigo}")
    
    return jsonify({"sucesso": False, "message": "..."}), 404
```

### Melhorias Implementadas:

#### **✅ Limpeza Completa de Campos:**
1. **ICMS**: CSOSN/CST ICMS + Alíquota zerados antes de aplicar
2. **PIS**: CST PIS + Alíquota zerados antes de aplicar
3. **COFINS**: CST COFINS + Alíquota zerados antes de aplicar
4. **IPI**: CST IPI + Alíquota zerados antes de aplicar

#### **✅ Logs Detalhados:**
- **Console do navegador**: Mostra cada campo sendo aplicado
- **Console do servidor**: Mostra regra encontrada e critérios de busca
- **Facilita debug**: Identifica rapidamente por que uma regra não foi aplicada

#### **✅ Alertas Informativos:**
- **Verde (8s)**: Regra aplicada com sucesso + lista de todos os campos
- **Amarelo (5s)**: Nenhuma regra encontrada (preencher manualmente)
- **Vermelho (8s)**: Erro ao buscar regra (problema na API)

#### **✅ Transparência Total:**
- Usuário vê exatamente quais campos foram aplicados
- Console mostra valores sendo aplicados em tempo real
- Nenhum valor "fantasma" permanece no formulário

## 📊 Resultado Esperado

### Cenário 1: Regra COM alíquotas
```
Produto selecionado: Câmera (NCM 85285900, CFOP 5101)
Regra encontrada: "Venda estadual Simples Nacional - 3% PIS, 1% COFINS"

Campos preenchidos:
✅ PIS: 3.00%
✅ COFINS: 1.00%
✅ ICMS: (conforme regra)

Alerta: ✅ Regra aplicada: Venda estadual Simples Nacional (PIS: 3%, COFINS: 1%, ICMS: 7%)
```

### Cenário 2: Regra SEM alíquotas
```
Produto selecionado: Câmera (NCM 85285900, CFOP 5101)
Regra encontrada: "Regra básica CSOSN 101" (sem alíquotas PIS/COFINS)

Campos preenchidos:
✅ PIS: 0.00% (zerado pela função)
✅ COFINS: 0.00% (zerado pela função)
✅ ICMS: (conforme regra)

Alerta: ✅ Regra aplicada: Regra básica CSOSN 101 (ICMS: 0%)
```

### Cenário 3: Nenhuma regra encontrada
```
Produto selecionado: Produto sem regra
Busca: Nenhuma regra encontrada

Campos preenchidos:
⚠️ PIS: (mantém valor do produto)
⚠️ COFINS: (mantém valor do produto)
⚠️ ICMS: (mantém valor do produto)

Console: ℹ️ Nenhuma regra tributária encontrada para este produto
```

## 🚀 Deployment - Windows Server

Para aplicar a correção no servidor:

```powershell
# 1. Atualizar código
cd C:\nfe_app
git pull

# 2. Reiniciar serviço
cd C:\nssm\win64
.\nssm.exe restart NFe_Backend

# 3. Testar no navegador
# - Abrir emissão de NFe
# - Selecionar produto
# - Verificar se campos PIS/COFINS são zerados antes de aplicar regra
# - Verificar se alerta mostra valores corretos
```

## 🔍 Verificação de Regras Tributárias

Se os valores ainda estiverem incorretos após a atualização, verificar:

### 1. Regras Cadastradas
```sql
SELECT 
    regra_tributacao_id,
    descricao_regra,
    aliquota_pis,
    aliquota_cofins,
    cst_pis,
    cst_cofins
FROM regras_tributacao
WHERE cliente_id = [SEU_CLIENTE_ID]
  AND ativo = true
  AND (ncm_id IN (SELECT ncm_id FROM ncms WHERE codigo = '85285900'))
  AND (cfop_id IN (SELECT cfop_id FROM cfops WHERE cfop = '5101'));
```

### 2. Produtos com Alíquotas Cadastradas
```sql
SELECT 
    produto_id,
    codigo_interno,
    descricao,
    aliquota_pis,
    aliquota_cofins
FROM produtos
WHERE cliente_id = [SEU_CLIENTE_ID]
  AND (aliquota_pis IS NOT NULL OR aliquota_cofins IS NOT NULL);
```

## 📝 Checklist de Testes

- [ ] Atualizar código no servidor (git pull)
- [ ] Reiniciar serviço NFe_Backend
- [ ] Abrir página de emissão de NFe
- [ ] Selecionar produto (NCM 85285900, CFOP 5101)
- [ ] Verificar se alerta verde aparece
- [ ] Verificar se alíquotas mostradas no alerta correspondem às da regra
- [ ] Verificar se campos PIS/COFINS foram preenchidos corretamente
- [ ] Testar com produto que não tem regra (deve zerar campos)
- [ ] Testar com produto que tem regra completa (deve preencher todos)

## 🎯 Commits

### Commit 1: Correção PIS/COFINS
```
fix: Limpar campos PIS/COFINS/IPI antes de aplicar regra tributária

- Adiciona limpeza de campos tributários antes de aplicar regra
- Define valores zerados (0.00) para alíquotas se regra não tiver
- Evita que valores antigos de outros produtos permaneçam no formulário
- Melhora mensagem de sucesso mostrando alíquotas aplicadas
- Resolve problema de alíquotas incorretas (1.65% PIS, 7.60% COFINS)

Commit: 1cbc377
```

### Commit 2: Correção COMPLETA (TODOS os tributos)
```
fix: Corrigir aplicação de TODOS os tributos (ICMS, PIS, COFINS, IPI)

✅ CORREÇÕES IMPLEMENTADAS:
- Limpa TODOS os campos tributários antes de aplicar regra (ICMS, PIS, COFINS, IPI)
- Limpa também CSOSN/CST ICMS (não apenas as alíquotas)
- Garante que valores antigos nunca permanecem no formulário
- Adiciona logs detalhados no console para debug

✅ MELHORIAS NA UX:
- Alerta verde mostra TODOS os campos aplicados (CST + Alíquotas)
- Alerta amarelo quando nenhuma regra é encontrada
- Alerta vermelho em caso de erro na API
- Alertas permanecem 8 segundos (tempo para ler detalhes)

✅ LOGS ADICIONADOS:
- Frontend: console.log detalhado de cada campo aplicado
- Backend: print dos critérios de busca e regra encontrada
- Facilita troubleshooting de regras não aplicadas

RESOLVE: Problema de alíquotas incorretas em todos os tributos
ANTES: Valores de produtos anteriores permaneciam
DEPOIS: Campos sempre limpos e aplicados corretamente

Commit: c8f3a93
```

## 📚 Arquivos Modificados

- `templates/admin/nfes/emitir.html` (função `aplicarRegraTributaria` - 120 linhas modificadas)
- `routes/api_routes.py` (endpoint `buscar_regra_tributacao` - logs adicionados)
- `CORRECAO_ALIQUOTAS_PIS_COFINS.md` (esta documentação)

## 🔗 Referências

- Issue original: Alíquotas PIS 1.65% e COFINS 7.60% incorretas
- Regras esperadas: 3% PIS ou 1% PIS (conforme cadastro)
- Código anterior: Não limpava campos antes de aplicar regra
- Código atual: Limpa campos e mostra valores aplicados no alerta

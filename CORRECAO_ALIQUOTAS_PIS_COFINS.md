# 🔧 Correção: Alíquotas PIS/COFINS Incorretas

## 📋 Problema Relatado

Ao emitir NFe, o sistema estava preenchendo alíquotas de PIS/COFINS que não correspondiam às regras tributárias cadastradas:
- **Problema**: Alíquota PIS 1.65% e COFINS 7.60%
- **Esperado**: Alíquotas das regras cadastradas (3% ou 1% PIS, conforme regra)
- **CFOP**: 5101
- **NCM**: 85285900

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

### Modificação no `templates/admin/nfes/emitir.html`

**Antes:**
```javascript
// Aplicar CST e alíquota PIS
if (result.regra.cst_pis) {
    const cstPisInput = document.querySelector(`input[name="cst_pis_${itemId}"]`);
    if (cstPisInput) {
        cstPisInput.value = result.regra.cst_pis;
    }
}
// ... apenas aplicava SE a regra tivesse valores
```

**Depois:**
```javascript
// ✅ BUSCAR CAMPOS DE PIS/COFINS/IPI
const cstPisInput = document.querySelector(`input[name="cst_pis_${itemId}"]`);
const aliquotaPisInput = document.querySelector(`input[name="aliquota_pis_${itemId}"]`);
// ... busca todos os campos primeiro

// ✅ LIMPAR CAMPOS PRIMEIRO (para evitar valores antigos)
if (cstPisInput) cstPisInput.value = '';
if (aliquotaPisInput) aliquotaPisInput.value = '0.00';
// ... limpa TODOS os campos

// Aplicar CST e alíquota PIS (SE a regra tiver)
if (result.regra.cst_pis && cstPisInput) {
    cstPisInput.value = result.regra.cst_pis;
}
// ... aplica os valores da regra
```

### Melhorias Implementadas:

1. **✅ Limpeza de campos**: Todos os campos de PIS/COFINS/IPI são zerados antes de aplicar regra
2. **✅ Valores padrão**: Se regra não tiver alíquotas, campos ficam em `0.00` (não vazios)
3. **✅ Mensagem detalhada**: Alerta mostra quais alíquotas foram aplicadas
4. **✅ Transparência**: Usuário vê claramente quais valores a regra definiu

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

## 🎯 Commit

```
fix: Limpar campos PIS/COFINS/IPI antes de aplicar regra tributária

- Adiciona limpeza de campos tributários antes de aplicar regra
- Define valores zerados (0.00) para alíquotas se regra não tiver
- Evita que valores antigos de outros produtos permaneçam no formulário
- Melhora mensagem de sucesso mostrando alíquotas aplicadas
- Resolve problema de alíquotas incorretas (1.65% PIS, 7.60% COFINS)

Commit: 1cbc377
```

## 📚 Arquivos Modificados

- `templates/admin/nfes/emitir.html` (função `aplicarRegraTributaria`)

## 🔗 Referências

- Issue original: Alíquotas PIS 1.65% e COFINS 7.60% incorretas
- Regras esperadas: 3% PIS ou 1% PIS (conforme cadastro)
- Código anterior: Não limpava campos antes de aplicar regra
- Código atual: Limpa campos e mostra valores aplicados no alerta

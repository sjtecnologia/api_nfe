# Integração Automática de Regras Tributárias na Emissão de NFe

**Data:** 10 de novembro de 2025  
**Status:** ✅ Implementado e Pronto para Testes

## 📋 Resumo

Implementada a aplicação automática de regras de tributação durante a emissão de NFe. Quando um produto é selecionado no formulário, o sistema busca automaticamente a regra tributária correspondente e preenche os campos de impostos (CST, alíquotas, etc.).

## 🎯 Problema Resolvido

**Antes:**
- Regras tributárias eram criadas e armazenadas no banco
- **MAS** não eram aplicadas automaticamente durante emissão de NFe
- Usuários precisavam preencher manualmente todos os campos tributários
- API de busca de regras existia mas não era chamada pelo frontend

**Depois:**
- ✅ Regras aplicadas automaticamente ao selecionar produto
- ✅ Campos tributários preenchidos com dados da regra
- ✅ Indicador visual quando regra aplicada
- ✅ Fallback para preenchimento manual se nenhuma regra encontrada

## 🔧 Mudanças Implementadas

### 1. Template NFe (templates/admin/nfes/emitir.html)

#### Adicionada função JavaScript `aplicarRegraTributacao()`
```javascript
async function aplicarRegraTributacao(itemId, produtoId) {
    // 1. Busca dados do produto via API
    const produto = await fetch(`/api/produtos/${produtoId}`).then(r => r.json());
    
    // 2. Prepara critérios de busca
    const criterios = {
        cliente_id: emitente_data.cliente_id,
        regime_tributario_id: 1,
        ncm_codigo: produto.ncm_codigo,
        cfop_codigo: produto.cfop_codigo,
        uf_origem: emitente_data.uf,
        uf_destino: getUfDestino(),
        tipo_item: produto.tipo_item
    };
    
    // 3. Busca regra correspondente
    const regra = await fetch('/api/regras_tributacao/buscar', {
        method: 'POST',
        body: JSON.stringify(criterios)
    }).then(r => r.json());
    
    // 4. Aplica dados da regra nos campos do formulário
    // CST/CSOSN ICMS, Alíquotas ICMS, PIS, COFINS, IPI
}
```

#### Modificada função `carregarProduto()`
```javascript
function carregarProduto(itemId) {
    // ... código existente ...
    
    // 🔥 NOVA: Chama aplicação automática de regras
    aplicarRegraTributacao(itemId, option.value);
}
```

#### Adicionados campos PIS/COFINS/IPI
```html
<!-- Novos campos no formulário de item -->
<input name="cst_pis_${itemCounter}">
<input name="aliquota_pis_${itemCounter}">
<input name="cst_cofins_${itemCounter}">
<input name="aliquota_cofins_${itemCounter}">
<input name="cst_ipi_${itemCounter}">
<input name="aliquota_ipi_${itemCounter}">
```

#### Adicionado atributo data-uf no select de destinatário
```html
<option value="{{ dest.destinatario_id }}" 
        data-uf="{{ dest.uf }}">  <!-- ✅ NOVO -->
```

#### Função auxiliar para indicadores visuais
```javascript
function mostrarAlerta(itemId, tipo, mensagem) {
    // Mostra alerta de sucesso/warning/danger no topo do item
    // Auto-remove após 5 segundos
}
```

### 2. API Routes (routes/api_routes.py)

#### Novo endpoint: GET /api/produtos/<produto_id>
```python
@api_bp.route('/produtos/<int:produto_id>', methods=['GET'])
@login_required
def get_produto_by_id(produto_id):
    """Retorna dados completos de um produto específico por ID"""
    
    # Verifica acesso ao cliente do produto
    # Retorna: produto_id, codigo_interno, descricao, preco,
    #          ncm_id, ncm_codigo, cfop_id, cfop_codigo,
    #          tipo_item, origem_mercadoria, cest, etc.
```

**Resposta JSON:**
```json
{
    "produto_id": 123,
    "codigo_interno": "PROD001",
    "descricao": "Notebook Dell",
    "ncm_codigo": "84713012",
    "cfop_codigo": "5102",
    "tipo_item": "Produto",
    "preco_unitario_padrao": 3500.00,
    "unidade_comercial": "UN"
}
```

### 3. NFe Routes (routes/nfe_routes.py)

#### Corrigido código quebrado na linha 1144

**ANTES (❌ QUEBRADO):**
```python
produto_query = text("""
    SELECT p.cfop_padrao, rt.cfop 
    FROM produtos p
    LEFT JOIN regras_tributacao rt ON p.produto_id = rt.produto_id  -- ❌ Coluna não existe!
    WHERE p.codigo_interno = :codigo
""")
```

**DEPOIS (✅ CORRIGIDO):**
```python
produto_query = text("""
    SELECT p.cfop_id, cf.cfop
    FROM produtos p
    LEFT JOIN cfops cf ON p.cfop_id = cf.cfop_id  -- ✅ JOIN correto
    WHERE p.codigo_interno = :codigo
    LIMIT 1
""")
```

**Nota:** Este código agora é apenas fallback. A aplicação de regras acontece no frontend via JavaScript.

## 🔄 Fluxo de Aplicação de Regras

```
1. Usuário seleciona produto no formulário NFe
   ↓
2. Evento onchange dispara carregarProduto(itemId)
   ↓
3. carregarProduto() chama aplicarRegraTributacao(itemId, produtoId)
   ↓
4. aplicarRegraTributacao() faz 2 chamadas API:
   a) GET /api/produtos/{produtoId} → Busca NCM/CFOP do produto
   b) POST /api/regras_tributacao/buscar → Busca regra correspondente
   ↓
5. Se regra encontrada (200):
   - Preenche CST/CSOSN ICMS
   - Preenche Alíquota ICMS
   - Preenche CST PIS e Alíquota PIS
   - Preenche CST COFINS e Alíquota COFINS
   - Preenche CST IPI e Alíquota IPI
   - Mostra alerta verde: "✅ Regra aplicada: [descrição]"
   ↓
6. Se nenhuma regra encontrada (404):
   - Mostra alerta amarelo: "⚠️ Nenhuma regra encontrada, preencha manualmente"
   - Usuário preenche campos manualmente
   ↓
7. Recalcula totais automaticamente
```

## 📊 Critérios de Matching de Regras

A API `/api/regras_tributacao/buscar` procura regras usando os seguintes critérios (em ordem de prioridade):

1. **cliente_id** (obrigatório)
   - Regras específicas do cliente TÊM PRIORIDADE
   - Se não houver regra específica, busca regras globais (cliente_id = NULL)

2. **regime_tributario_id** (obrigatório)
   - 1 = Simples Nacional
   - 2 = Lucro Presumido
   - 3 = Lucro Real

3. **ncm_codigo** (opcional)
   - Se informado, filtra por NCM do produto
   - NULL na regra = aplica a todos os NCMs

4. **cfop_codigo** (opcional)
   - Se informado, filtra por CFOP da operação
   - NULL na regra = aplica a todos os CFOPs

5. **uf_origem** (opcional)
   - UF do emitente
   - NULL na regra = aplica a todas as UFs de origem

6. **uf_destino** (opcional)
   - UF do destinatário
   - NULL na regra = aplica a todas as UFs de destino

7. **tipo_item** (opcional)
   - "Produto" ou "Serviço"
   - NULL na regra = aplica a ambos

8. **prioridade** (desempate)
   - Valor numérico (padrão: 100)
   - Maior valor = maior prioridade

**Retorno:** Primeira regra que satisfaz TODOS os critérios informados.

## 🎨 Indicadores Visuais

### Sucesso (Regra Aplicada)
```html
<div class="alert alert-success">
    ✅ Regra aplicada: Vendas para SP - Regime Normal
</div>
```

### Aviso (Nenhuma Regra)
```html
<div class="alert alert-warning">
    ⚠️ Nenhuma regra encontrada, preencha manualmente
</div>
```

### Erro (Falha na API)
```html
<div class="alert alert-danger">
    ❌ Erro ao buscar regra de tributação
</div>
```

## 📝 Campos Preenchidos Automaticamente

| Campo | Origem | Observação |
|-------|--------|------------|
| CST ICMS | regra.cst_icms | Para Lucro Presumido/Real |
| CSOSN ICMS | regra.csosn_icms | Para Simples Nacional |
| Alíquota ICMS (%) | regra.aliquota_icms | 0-50% |
| Redução Base ICMS (%) | regra.reducao_base_icms | Se aplicável |
| CST PIS | regra.cst_pis | Código 2 dígitos |
| Alíquota PIS (%) | regra.aliquota_pis | Padrão: 1.65% |
| CST COFINS | regra.cst_cofins | Código 2 dígitos |
| Alíquota COFINS (%) | regra.aliquota_cofins | Padrão: 7.60% |
| CST IPI | regra.cst_ipi | Código 2 dígitos |
| Alíquota IPI (%) | regra.aliquota_ipi | Quando aplicável |

## 🧪 Como Testar

### 1. Preparar Dados de Teste

```sql
-- Verificar se regra existe para seu cliente
SELECT * FROM regras_tributacao 
WHERE cliente_id = 11  -- Seu cliente
AND ativo = true;

-- Se não existir, criar regra de teste
INSERT INTO regras_tributacao (
    cliente_id, regime_tributario_id, cfop_id, ncm_id,
    uf_origem, uf_destino, tipo_item, prioridade,
    cst_icms, aliquota_icms, cst_pis, aliquota_pis,
    cst_cofins, aliquota_cofins, descricao_regra, ativo
) VALUES (
    11, 1, NULL, NULL,  -- Aplica a qualquer CFOP/NCM
    'SP', 'RJ', 'Produto', 100,
    '00', 18.00, '01', 1.65,
    '01', 7.60, 'Regra Teste SP->RJ', true
);
```

### 2. Acessar Emissão de NFe

```
http://127.0.0.1:8080/nfe/emitir?cliente_id=11
```

### 3. Passos do Teste

1. **Selecionar destinatário** (UF: RJ)
2. **Clicar "Adicionar Item"**
3. **Selecionar produto** no dropdown
4. **Observar:**
   - ✅ Campos tributários preenchidos automaticamente
   - ✅ Alerta verde aparece no topo do item
   - ✅ Console do navegador mostra logs:
     ```
     🎯 Buscando regra de tributação para item 1, produto 123
     📦 Dados do produto: {...}
     🔍 Critérios de busca: {...}
     ✅ Regra encontrada: {...}
     ```

### 4. Teste Negativo (Sem Regra)

1. Criar produto com NCM que não tem regra
2. Selecionar esse produto
3. **Observar:**
   - ⚠️ Alerta amarelo: "Nenhuma regra encontrada"
   - ⚠️ Campos vazios para preenchimento manual

### 5. Verificar no Console do Navegador

Abrir DevTools (F12) e conferir:

```javascript
// Sucesso
✅ Regra encontrada: {cst_icms: "00", aliquota_icms: 18, ...}

// Sem regra
ℹ️ Nenhuma regra encontrada - preencher manualmente

// Erro
❌ Erro ao buscar regra: Network error
```

## 🐛 Troubleshooting

### Problema: Nenhuma regra aplicada mesmo existindo no banco

**Verificar:**
1. Regra está ativa? (`ativo = true`)
2. `regime_tributario_id` correto?
3. Critérios muito restritivos? (NCM/CFOP/UFs específicos)

**Solução:**
```sql
-- Criar regra genérica (aplica a todos os casos)
UPDATE regras_tributacao 
SET cfop_id = NULL, ncm_id = NULL, uf_destino = NULL
WHERE cliente_id = 11;
```

### Problema: Erro "Produto não encontrado"

**Causa:** Produto inativo ou não pertence ao cliente

**Solução:**
```sql
UPDATE produtos SET ativo = true WHERE produto_id = 123;
```

### Problema: Campos não preenchidos

**Verificar no Console:**
1. Requisições API foram feitas?
2. Status code 200 ou 404?
3. Dados da regra retornados corretamente?

**Debug JavaScript:**
```javascript
// Adicionar no console para testar manualmente
aplicarRegraTributacao(1, 123);
```

### Problema: "Access denied"

**Causa:** Usuário não tem acesso ao cliente/produto

**Solução:**
```sql
-- Verificar associação usuário-cliente
SELECT * FROM user_clients 
WHERE user_id = ? AND client_id = 11;

-- Adicionar se necessário
INSERT INTO user_clients (user_id, client_id) VALUES (?, 11);
```

## 📈 Melhorias Futuras (Opcional)

### 1. Cache de Regras
```javascript
// Evitar buscar mesma regra múltiplas vezes
const regraCache = {};
if (regraCache[cacheKey]) {
    return regraCache[cacheKey];
}
```

### 2. Validação de Campos
```javascript
// Validar CST antes de enviar
if (!/^\d{2}$/.test(cst_icms)) {
    alert('CST ICMS inválido');
}
```

### 3. Histórico de Regras Aplicadas
```sql
-- Tabela para auditoria
CREATE TABLE nfe_regras_aplicadas (
    nfe_item_id INT,
    regra_tributacao_id INT,
    data_aplicacao TIMESTAMP
);
```

### 4. Simulador de Regras
- Página para testar critérios
- Ver qual regra seria aplicada sem criar NFe

### 5. Indicador Visual Permanente
- Badge no item mostrando ID da regra aplicada
- Tooltip com descrição completa ao passar mouse

## ✅ Checklist de Validação

- [x] Função `aplicarRegraTributacao()` criada
- [x] Evento vinculado ao selecionar produto
- [x] Endpoint `/api/produtos/<id>` criado
- [x] Endpoint `/api/regras_tributacao/buscar` funcional
- [x] Campos PIS/COFINS/IPI adicionados ao template
- [x] Atributo `data-uf` adicionado ao select destinatário
- [x] JOIN quebrado corrigido em nfe_routes.py linha 1144
- [x] Alertas visuais implementados
- [x] Logs no console para debug
- [ ] **PENDENTE:** Testes funcionais completos
- [ ] **PENDENTE:** Validação em ambiente de homologação
- [ ] **PENDENTE:** Treinamento de usuários

## 📚 Arquivos Modificados

1. ✅ `templates/admin/nfes/emitir.html` - 200+ linhas adicionadas
2. ✅ `routes/api_routes.py` - Endpoint novo + endpoint existente
3. ✅ `routes/nfe_routes.py` - Correção JOIN quebrado

## 🎓 Conceitos Tributários

### CST ICMS (Código Situação Tributária)
- `00` = Tributada integralmente
- `10` = Tributada com cobrança do ICMS por ST
- `20` = Com redução de base de cálculo
- `40` = Isenta
- `60` = ICMS cobrado anteriormente por ST

### CSOSN (Simples Nacional)
- `101` = Tributada pelo Simples Nacional com permissão de crédito
- `102` = Tributada pelo Simples Nacional sem permissão de crédito
- `103` = Isenção do ICMS no Simples Nacional
- `400` = Não tributada pelo Simples Nacional

### CST PIS/COFINS
- `01` = Operação tributável com alíquota básica
- `04` = Operação tributável (tributação monofásica)
- `06` = Operação tributável (alíquota zero)
- `07` = Operação isenta da contribuição

---

**Status Final:** ✅ Implementação completa e pronta para testes  
**Próximo Passo:** Teste funcional com dados reais de cliente

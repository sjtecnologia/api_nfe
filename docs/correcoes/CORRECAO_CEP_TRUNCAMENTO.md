# Correção: Erro de Truncamento em CEP e CPF/CNPJ

## 🔴 Problema Identificado

**Erro:** `psycopg2.errors.StringDataRightTruncation: value too long for type character varying(8)`

**Causa Raiz:** Campos CEP e CPF/CNPJ estavam sendo salvos com formatação (hífen, pontos, barras) mas o banco de dados espera apenas números.

### Exemplo do Erro

```python
# Valor enviado
'cep': '01310-100'  # 10 caracteres (8 números + hífen)

# Banco de dados espera
character varying(8)  # Apenas 8 números

# Resultado
❌ ERROR: value too long for type character varying(8)
```

### Dados no Erro

```python
{
    'cep': '01310-100',           # ❌ 10 caracteres (deveria ser '01310100')
    'cpf_cnpj': '249.021.818-27', # ❌ 14 caracteres (deveria ser '24902181827')
    # ... outros campos
}
```

## ✅ Solução Implementada

### Limpeza de Dados Antes de Salvar

**Estratégia:** Remover todos os caracteres não numéricos antes de inserir no banco.

```python
# Limpar CEP (remover formatação)
cep_raw = request.form.get('cep', '')
cep_limpo = ''.join(filter(str.isdigit, cep_raw))
# '01310-100' → '01310100'

# Limpar CPF/CNPJ (remover formatação)
cpf_cnpj_raw = request.form.get('cpf_cnpj', '')
cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj_raw))
# '249.021.818-27' → '24902181827'
# '12.345.678/0001-99' → '12345678000199'
```

## 📝 Funções Corrigidas

### 1. `admin_destinatarios_nfe_add()` - Linha 2585
**Arquivo:** `routes/admin_routes.py`

**Antes:**
```python
data = {
    'cpf_cnpj': request.form.get('cpf_cnpj'),  # ❌ Com formatação
    'cep': request.form.get('cep'),            # ❌ Com formatação
    # ...
}
```

**Depois:**
```python
# Limpar antes de montar o dict
cep_raw = request.form.get('cep', '')
cep_limpo = ''.join(filter(str.isdigit, cep_raw))

cpf_cnpj_raw = request.form.get('cpf_cnpj', '')
cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj_raw))

data = {
    'cpf_cnpj': cpf_cnpj_limpo,  # ✅ Apenas números
    'cep': cep_limpo,             # ✅ Apenas números
    # ...
}
```

### 2. `salvar_destinatario()` - Linha 3073
**Arquivo:** `routes/admin_routes.py`

**Correção:** Mesma lógica aplicada

### 3. `create_cliente()` - Linha 2096
**Arquivo:** `routes/admin_routes.py`

**Correção:** Adicionada limpeza de CEP e CNPJ no cadastro de clientes

### 4. `edit_cliente()` - Linha 2303
**Arquivo:** `routes/admin_routes.py`

**Correção:** Adicionada limpeza de CEP e CNPJ na edição de clientes

## 🧪 Testes Realizados

### Cenário de Teste

**Entrada do Usuário:**
```
Nome: Carlos Renato Barbosa
CPF: 249.021.818-27  (formatado)
CEP: 01310-100        (formatado)
```

**Processamento:**
```python
cpf_cnpj_limpo = '24902181827'  # ✅ 11 dígitos
cep_limpo = '01310100'          # ✅ 8 dígitos
```

**SQL Gerado:**
```sql
INSERT INTO destinatarios_nfe (..., cpf_cnpj, ..., cep, ...)
VALUES (..., '24902181827', ..., '01310100', ...)
```

**Resultado:** ✅ Inserção bem-sucedida

## 📊 Schema do Banco de Dados

### Campos Afetados

```sql
-- destinatarios_nfe
cep VARCHAR(8)           -- Apenas números, sem hífen
cpf_cnpj VARCHAR(14)     -- Apenas números, sem formatação

-- clientes  
cep VARCHAR(8)           -- Apenas números, sem hífen
cnpj VARCHAR(14)         -- Apenas números, sem formatação
```

### Exemplos de Valores Válidos

| Campo | Entrada Formatada | Valor Armazenado |
|-------|-------------------|------------------|
| CEP | 01310-100 | 01310100 |
| CEP | 20040-020 | 20040020 |
| CPF | 123.456.789-00 | 12345678900 |
| CNPJ | 12.345.678/0001-99 | 12345678000199 |

## 🔍 Por Que Armazenar Sem Formatação?

### Vantagens

1. **Tamanho fixo** - Sempre 8 dígitos (CEP) ou 11/14 dígitos (CPF/CNPJ)
2. **Validação fácil** - `len(cep) == 8` e `cep.isdigit()`
3. **Busca eficiente** - Sem variações de formato
4. **Economia de espaço** - VARCHAR(8) vs VARCHAR(10)
5. **Padrão NFe** - XML exige apenas números

### Formatação na Apresentação

```python
# No template (exibição)
{{ destinatario.cep[:5] }}-{{ destinatario.cep[5:] }}
# '01310100' → '01310-100'

{{ destinatario.cpf_cnpj[:3] }}.{{ destinatario.cpf_cnpj[3:6] }}...
# '12345678900' → '123.456.789-00'
```

## 🛠️ Função Utilitária (Sugestão Futura)

Para evitar repetição, considerar criar função helper:

```python
# utils/formatters.py
def limpar_numeros(valor: str) -> str:
    """Remove todos os caracteres não numéricos"""
    if not valor:
        return ''
    return ''.join(filter(str.isdigit, valor))

# Uso
from utils.formatters import limpar_numeros

data = {
    'cep': limpar_numeros(request.form.get('cep')),
    'cpf_cnpj': limpar_numeros(request.form.get('cpf_cnpj')),
}
```

## ✅ Status das Correções

- ✅ `admin_destinatarios_nfe_add()` - Criação de Destinatários/Tomadores
- ✅ `salvar_destinatario()` - Salvamento alternativo de Destinatários/Tomadores
- ✅ `create_cliente()` - Criação de clientes
- ✅ `edit_cliente()` - Edição de clientes

## 🔄 Fluxo Completo

### 1. Usuário Preenche Formulário
```
CEP: [01310-100] (com máscara JavaScript)
CPF: [249.021.818-27] (com máscara JavaScript)
```

### 2. Frontend Envia (POST)
```
cep=01310-100&cpf_cnpj=249.021.818-27
```

### 3. Backend Processa
```python
cep_limpo = '01310100'         # Remove hífen
cpf_cnpj_limpo = '24902181827' # Remove pontos e hífen
```

### 4. Banco de Dados Armazena
```sql
cep = '01310100'         -- 8 caracteres ✅
cpf_cnpj = '24902181827' -- 11 caracteres ✅
```

### 5. Exibição (Leitura)
```python
# Template adiciona formatação para display
{{ cep|format_cep }}    → '01310-100'
{{ cpf|format_cpf }}    → '249.021.818-27'
```

## 🎯 Conclusão

**Problema:** Dados com formatação visual excediam limite do banco  
**Solução:** Limpar formatação antes de salvar  
**Impacto:** 4 funções corrigidas  
**Benefício:** Consistência de dados e conformidade com padrão NFe  

---

**Status:** ✅ Corrigido e testado  
**Data:** 10/11/2025  
**Versão:** 1.0

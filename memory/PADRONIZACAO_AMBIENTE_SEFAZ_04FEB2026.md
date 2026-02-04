# 🔄 PADRONIZAÇÃO CÓDIGO AMBIENTE - SEFAZ
**Data:** 04/02/2026  
**Tipo:** Refatoração (Breaking Change no Banco de Dados)

---

## 📋 MOTIVAÇÃO

Evitar confusão futura removendo conversão interna. O sistema estava com código invertido em relação ao padrão SEFAZ.

**ANTES (Sistema):**
- `1` = Homologação
- `2` = Produção

**DEPOIS (Padrão SEFAZ):**
- `1` = Produção ✅
- `2` = Homologação ✅

---

## 🔧 ALTERAÇÕES REALIZADAS

### 1. Modelo de Dados
**Arquivo:** `database/models.py`

```python
# ANTES
ambiente = Column(Integer, default=1, nullable=False)  # 1=Homologação, 2=Produção

# DEPOIS
ambiente = Column(Integer, default=2, nullable=False)  # 1=Produção, 2=Homologação (padrão SEFAZ)
```

**Impacto:** Novos clientes cadastrados terão default = 2 (Homologação)

---

### 2. Remoção de Conversões
**Arquivo:** `routes/nfe_routes.py`

#### Mudança 1: Linha ~169
```python
# ANTES
ambiente_cliente = emitente_data.ambiente
ambiente = 'producao' if ambiente_cliente == 2 else 'homologacao'

# DEPOIS
tp_amb = emitente_data.ambiente
ambiente = 'producao' if tp_amb == 1 else 'homologacao'
```

#### Mudança 2: Linha ~220 (REMOVIDA)
```python
# ANTES
tp_amb = 1 if ambiente == 'producao' else 2
xml_nfe = generate_nfe_xml(..., tp_amb)

# DEPOIS
xml_nfe = generate_nfe_xml(..., tp_amb)  # Usa direto do banco
```

#### Mudança 3: Linha ~366 (REMOVIDA)
```python
# ANTES
tp_amb = 1 if ambiente == 'producao' else 2

# DEPOIS
# Removido - tp_amb já vem correto do banco
```

#### Mudança 4: Comentários (3 locais)
```python
# ANTES
'ambiente': emitente_data.ambiente  # Campo ambiente (1=Homologação, 2=Produção)

# DEPOIS
'ambiente': emitente_data.ambiente  # Campo ambiente (1=Produção, 2=Homologação - padrão SEFAZ)
```

---

### 3. Atualização de Comentários
**Arquivo:** `services/nfe_nfelib_service.py`

```python
# ANTES
tp_amb = form_data.get('tpAmb', 2)

# DEPOIS
# tpAmb padrão SEFAZ: 1=Produção, 2=Homologação
tp_amb = form_data.get('tpAmb', 2)  # Default: Homologação
```

---

## 💾 MIGRAÇÃO DO BANCO DE DADOS

**Arquivo:** `migrations/004_inverter_ambiente_sefaz.sql`

### ⚠️ ATENÇÃO: EXECUTAR APENAS UMA VEZ!

```sql
BEGIN;

-- Inverter valores usando 3 como temporário
UPDATE clientes SET ambiente = 3 WHERE ambiente = 1;  -- Homolog → temp
UPDATE clientes SET ambiente = 1 WHERE ambiente = 2;  -- Produção → 1
UPDATE clientes SET ambiente = 2 WHERE ambiente = 3;  -- temp → 2

-- Revisar antes de commitar
SELECT cliente_id, razao_social, ambiente FROM clientes;

-- COMMIT; -- Descomente para efetivar
```

### Passo a Passo para Executar:

1. **Conectar ao banco:**
   ```bash
   psql -h <host> -U <usuario> -d sjtnfe
   ```

2. **Executar script:**
   ```bash
   \i migrations/004_inverter_ambiente_sefaz.sql
   ```

3. **Revisar resultado:**
   - Se estiver correto: descomente `COMMIT;` e execute
   - Se houver problema: execute `ROLLBACK;`

---

## 📊 IMPACTO

### Clientes Existentes
- ⚠️ **Ambientes invertidos** até rodar migração SQL
- ✅ Após migração: tudo normalizado

### Novos Clientes
- ✅ Default = 2 (Homologação)
- ✅ Padrão SEFAZ desde o início

### Código
- ✅ Sem conversões desnecessárias
- ✅ Mais legível e direto
- ✅ Menos propenso a erros

---

## ✅ VALIDAÇÕES

### Sintaxe
```bash
✅ routes/nfe_routes.py - No errors found
✅ services/nfe_nfelib_service.py - No errors found
✅ database/models.py - No errors found
```

### Lógica
- ✅ tp_amb vem direto do banco (1 ou 2)
- ✅ Conversão string apenas para logs: `'producao' if tp_amb == 1`
- ✅ XML gerado com tpAmb correto para SEFAZ

---

## 🧪 TESTES NECESSÁRIOS

### Antes da Migração SQL
- [ ] Verificar ambiente dos clientes atuais
- [ ] Documentar quais estão em produção/homologação

### Após Migração SQL
- [ ] Confirmar inversão no banco
- [ ] Testar emissão NFe em homologação (tp_amb=2)
- [ ] Testar emissão NFe em produção (tp_amb=1)
- [ ] Verificar XML gerado tem tpAmb correto
- [ ] Validar DANFE sem tarja indevida

---

## 📝 CHECKLIST DE DEPLOY

### Código
- [x] Atualizar models.py
- [x] Atualizar routes/nfe_routes.py
- [x] Atualizar services/nfe_nfelib_service.py
- [x] Validar sintaxe
- [ ] Commitar mudanças
- [ ] Push para repositório

### Banco de Dados
- [ ] Backup do banco antes da migração
- [ ] Executar script de migração
- [ ] Validar resultado
- [ ] COMMIT da transação

### Produção
- [ ] Deploy código
- [ ] Reiniciar serviço
- [ ] Testar emissão teste
- [ ] Monitorar logs

---

## 🔄 ROLLBACK (Se necessário)

### Código
```bash
git revert <commit_hash>
git push origin lc214-migration
```

### Banco de Dados
```sql
BEGIN;
UPDATE clientes SET ambiente = 3 WHERE ambiente = 1;  -- Prod → temp
UPDATE clientes SET ambiente = 1 WHERE ambiente = 2;  -- Homolog → 1
UPDATE clientes SET ambiente = 2 WHERE ambiente = 3;  -- temp → 2
COMMIT;
```

---

## 📌 ARQUIVOS MODIFICADOS

1. ✅ `database/models.py` - Modelo Cliente (default + comentário)
2. ✅ `routes/nfe_routes.py` - Remoção de conversões (3 locais)
3. ✅ `services/nfe_nfelib_service.py` - Comentário atualizado
4. ✅ `migrations/004_inverter_ambiente_sefaz.sql` - Script migração

**Total:** 4 arquivos alterados

---

## ⚡ PRÓXIMOS PASSOS

1. **Revisar mudanças** ✅ (você está aqui)
2. **Executar migração SQL** ⏳
3. **Commitar código** ⏳
4. **Deploy em produção** ⏳
5. **Testar emissões** ⏳
6. **Documentar em memory/** ⏳

---

**Status:** ✅ Código pronto, aguardando migração SQL e deploy

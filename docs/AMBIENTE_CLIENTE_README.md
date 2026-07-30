# Migração: Campo Ambiente no Cadastro do Cliente

## 📋 Resumo da Alteração

O campo **Ambiente** (Homologação/Produção) foi movido do formulário de emissão de NFe para o cadastro do cliente. Agora cada cliente possui seu ambiente configurado, e a tela de emissão apenas exibe (não permite editar) qual ambiente será usado.

---

## 🎯 Objetivo

- **Centralizar configuração**: Um único local para definir se o cliente emite em Homologação ou Produção
- **Evitar erros**: Usuário não pode mais selecionar ambiente errado durante a emissão
- **Facilitar gestão**: Administrador define o ambiente por cliente no cadastro
- **Segurança**: Cliente em produção sempre emite em produção, sem risco de acidente

---

## 📂 Arquivos Modificados

### 1. **adicionar_campo_ambiente_cliente.sql** (NOVO)
- Script SQL para adicionar coluna `ambiente` na tabela `clientes`
- Valores: `1` = Homologação, `2` = Produção
- Padrão: `1` (Homologação) para segurança
- **IMPORTANTE**: Executar este script no banco de dados antes de usar o sistema

### 2. **database/models.py**
```python
class Cliente(Base):
    # ...
    ambiente = Column(Integer, default=1, nullable=False)  # 1=Homologação, 2=Produção
    # ...
```

### 3. **routes/nfe_routes.py**
- Adicionado `'ambiente': emitente_data.ambiente` no dicionário enviado ao template
- Modificada lógica para buscar ambiente do cliente:
```python
# Usar ambiente do cliente (1=Homologação, 2=Produção)
ambiente_cliente = emitente_data.ambiente
ambiente = 'homologacao' if ambiente_cliente == 1 else 'producao'
```

### 4. **templates/admin/nfes/emitir.html**
**ANTES:**
```html
<select class="form-control" name="ambiente" id="ambiente" required>
    <option value="homologacao" selected>Homologação</option>
    <option value="producao">Produção</option>
</select>
```

**DEPOIS:**
```html
<input type="text" class="form-control" id="ambiente" readonly 
       value="{% if emitente_data.ambiente == 2 %}Produção{% else %}Homologação{% endif %}" 
       style="background-color: {% if emitente_data.ambiente == 2 %}#28a745{% else %}#ffc107{% endif %}; color: white; font-weight: bold;">
<small class="form-text text-muted">Configurado no cadastro do cliente</small>
```

- **Campo somente leitura** (readonly)
- **Cor do campo**: Verde (#28a745) para Produção, Amarelo (#ffc107) para Homologação
- **Texto branco em negrito** para destaque visual

---

## 🚀 Deployment - Passo a Passo

### 1️⃣ Aplicar Migration SQL
```sql
-- Conectar no pgAdmin
-- Executar: adicionar_campo_ambiente_cliente.sql
```

### 2️⃣ Atualizar Arquivos Python
Copiar para o servidor:
- `database/models.py`
- `routes/nfe_routes.py`
- `templates/admin/nfes/emitir.html`

### 3️⃣ Reiniciar Serviço
```bash
nssm restart NFe_Backend
```

### 4️⃣ Configurar Ambiente nos Clientes
- Acessar tela de cadastro/edição de clientes
- Definir ambiente (1=Homologação ou 2=Produção) para cada cliente
- **Recomendação**: Manter todos em Homologação (1) inicialmente

---

## 🔍 Verificação Pós-Deployment

### Teste 1: Verificar campo no banco
```sql
SELECT cliente_id, razao_social, 
       CASE WHEN ambiente = 1 THEN 'Homologação'
            WHEN ambiente = 2 THEN 'Produção'
            ELSE 'Desconhecido' END as ambiente_desc
FROM clientes;
```

### Teste 2: Verificar tela de emissão
1. Acessar "Emitir NFe"
2. Verificar campo "Ambiente":
   - Deve estar em amarelo com texto "Homologação" (ou verde "Produção")
   - Campo deve estar desabilitado (readonly)
   - Texto abaixo: "Configurado no cadastro do cliente"

### Teste 3: Emitir NFe de teste
1. Emitir uma NFe em Homologação
2. Verificar logs: deve mostrar "Ambiente do cliente: homologacao (1)"
3. Confirmar que NFe foi enviada para ambiente correto da SEFAZ

---

## ⚙️ Configuração do Cliente (Futuro)

### Adicionar campo na tela de cadastro/edição de clientes

Quando implementar a tela de cadastro, adicionar:

```html
<div class="form-group">
    <label for="ambiente">Ambiente de Emissão *</label>
    <select class="form-control" name="ambiente" id="ambiente" required>
        <option value="1" selected>1 - Homologação</option>
        <option value="2">2 - Produção</option>
    </select>
    <small class="form-text text-muted">
        Homologação: Para testes (NFe não tem valor fiscal)
        <br>
        Produção: NFe válida fiscalmente (requer certificado válido)
    </small>
</div>
```

---

## 🔐 Segurança

- **Padrão seguro**: Novos clientes iniciam em Homologação (1)
- **Campo protegido**: Na emissão, usuário não pode alterar
- **Auditoria**: Logs mostram qual ambiente foi usado em cada emissão
- **Rastreabilidade**: Histórico de alterações do cliente registra mudanças de ambiente

---

## 📊 Valores do Campo

| Valor | Descrição | Cor na Tela | Uso |
|-------|-----------|-------------|-----|
| **1** | Homologação | 🟨 Amarelo | Testes, validações, treinamento |
| **2** | Produção | 🟩 Verde | NFe válida fiscalmente |

---

## ❓ FAQ

### Como mudar um cliente de Homologação para Produção?

**Via SQL (temporário):**
```sql
UPDATE clientes 
SET ambiente = 2 
WHERE cliente_id = 1; -- Substituir pelo ID correto
```

**Via Interface (recomendado - quando implementada):**
1. Acessar Cadastro de Clientes
2. Editar cliente desejado
3. Alterar campo "Ambiente de Emissão" para "2 - Produção"
4. Salvar

### O que acontece se eu mudar o ambiente de um cliente que já emitiu NFes?

As NFes antigas permanecem inalteradas. O campo `ambiente` do cliente afeta apenas **novas emissões** a partir da mudança.

### Posso ter um cliente em Produção e outro em Homologação?

Sim! Cada cliente possui seu próprio ambiente configurado de forma independente.

### Como saber em qual ambiente uma NFe foi emitida?

Verifique os logs do sistema ou consulte o XML da NFe (tag `<tpAmb>`):
- `tpAmb=1`: Produção
- `tpAmb=2`: Homologação

---

## 📝 Checklist de Implantação

- [ ] Script SQL executado no banco de dados
- [ ] Coluna `ambiente` criada na tabela `clientes`
- [ ] Todos os clientes com ambiente = 1 (verificado)
- [ ] Arquivo `models.py` atualizado no servidor
- [ ] Arquivo `nfe_routes.py` atualizado no servidor
- [ ] Template `emitir.html` atualizado no servidor
- [ ] Serviço NFe_Backend reiniciado
- [ ] Campo "Ambiente" aparece como readonly na tela de emissão
- [ ] Cor do campo está correta (amarelo para Homologação)
- [ ] Emissão de teste realizada com sucesso
- [ ] Logs confirmam uso do ambiente correto

---

## 🎉 Benefícios

✅ **Centralização**: Um único local para configurar ambiente  
✅ **Segurança**: Usuário não pode emitir em ambiente errado acidentalmente  
✅ **Clareza visual**: Cores diferenciadas alertam sobre o ambiente ativo  
✅ **Gestão simplificada**: Administrador controla ambiente de cada cliente  
✅ **Menos erros**: Risco zero de selecionar ambiente incorreto durante emissão  

---

**Data da Migração**: 2025-12-01  
**Versão**: 1.0  
**Autor**: Sistema NFe API

# Diferenças entre Admin Comum e Super Admin

## 📋 Resumo das Permissões

Este documento descreve as diferenças de permissões entre **Admin Comum** e **Super Admin** no sistema.

---

## 🔐 Admin Comum (Role: 'Admin')

### ✅ **Pode Fazer:**

1. **Visualizar Clientes**
   - Acesso apenas aos clientes vinculados à sua conta
   - Visualização completa dos dados dos clientes que gerencia

2. **Editar Clientes**
   - Pode editar informações dos clientes que tem acesso
   - Inclui: dados cadastrais, endereço, contatos, etc.

3. **Criar Usuários**
   - Pode criar novos usuários
   - **RESTRIÇÃO**: Só pode vincular usuários aos clientes que ele gerencia
   - Não pode criar usuários para clientes que não tem acesso

4. **Editar Usuários**
   - Pode editar usuários existentes
   - **RESTRIÇÃO**: Só pode vincular a clientes que ele gerencia

5. **Acessar Dados dos Clientes**
   - NFes, produtos, destinatários, certificados, regras tributárias
   - Apenas dos clientes vinculados

### ❌ **Não Pode Fazer:**

1. **Cadastrar Novos Clientes**
   - Botão "Adicionar Novo Cliente" não aparece na interface
   - Tentativa de acesso direto à rota será bloqueada

2. **Ver Todos os Clientes**
   - Só vê clientes vinculados à sua conta
   - Não tem visão global de todos os clientes do sistema

3. **Vincular Usuários a Qualquer Cliente**
   - Só pode vincular a clientes que gerencia

---

## 👑 Super Admin (Role: 'Super_Admin')

### ✅ **Pode Fazer TUDO:**

1. **Acesso Total a Clientes**
   - Ver todos os clientes do sistema
   - Criar novos clientes
   - Editar qualquer cliente
   - Excluir clientes

2. **Gerenciar Usuários Sem Restrições**
   - Criar usuários e vincular a qualquer cliente
   - Editar qualquer usuário
   - Sem restrições de cliente

3. **Visão Global**
   - Dashboard com dados de todos os clientes
   - Relatórios completos do sistema

---

## 🔧 Implementação Técnica

### Verificações no Backend

```python
# Verificar se é Super Admin
if current_user.is_super_admin():
    # Acesso total
else:
    # Restrições de Admin Comum
```

### Filtros de Dados

**Admin Comum:**
```sql
SELECT c.* FROM clientes c
INNER JOIN user_clients uc ON c.cliente_id = uc.client_id
WHERE uc.user_id = :user_id
```

**Super Admin:**
```sql
SELECT * FROM clientes
```

### Templates

**Botão visível apenas para Super Admin:**
```html
{% if is_super_admin() %}
<a href="{{ url_for('admin.create_cliente') }}" class="btn btn-primary">
    <i class="fas fa-plus"></i> Adicionar Novo Cliente
</a>
{% endif %}
```

---

## 📝 Arquivos Modificados

1. **`models/user.py`**
   - Adicionado método `is_super_admin()`

2. **`routes/admin_routes.py`**
   - Filtros em `list_clientes()` para admin comum
   - Validação em `create_cliente()` bloqueando admin comum
   - Filtros em `create_usuario()` e `edit_usuario()`
   - Validações ao vincular usuários a clientes

3. **`templates/admin/clientes/list.html`**
   - Botão "Novo Cliente" condicional

4. **`app.py`**
   - Context processor com função `is_super_admin()`

---

## 🧪 Como Testar

### 1. Criar Usuário Admin Comum

```sql
-- Criar usuário
INSERT INTO users (username, email, password_hash, _is_active)
VALUES ('admin_comum', 'admin@teste.com', '<hash>', true)
RETURNING id;

-- Vincular role Admin (não Super_Admin)
INSERT INTO user_roles (user_id, role_id)
SELECT <user_id>, id FROM roles WHERE name = 'Admin';

-- Vincular a alguns clientes específicos
INSERT INTO user_clients (user_id, client_id)
VALUES (<user_id>, 1), (<user_id>, 2);
```

### 2. Logar como Admin Comum

- **Deve ver**: Apenas clientes 1 e 2
- **Não deve ver**: Botão "Adicionar Novo Cliente"
- **Ao criar usuário**: Só pode vincular aos clientes 1 e 2

### 3. Criar Usuário Super Admin

```sql
-- Vincular role Super_Admin
INSERT INTO user_roles (user_id, role_id)
SELECT <user_id>, id FROM roles WHERE name = 'Super_Admin';
```

### 4. Logar como Super Admin

- **Deve ver**: Todos os clientes
- **Deve ver**: Botão "Adicionar Novo Cliente"
- **Ao criar usuário**: Pode vincular a qualquer cliente

---

## 🚀 Fluxo de Uso Recomendado

1. **Super Admin**:
   - Cria novos clientes no sistema
   - Cria Admin Comum para gerenciar clientes específicos
   - Vincula Admin Comum aos clientes que ele irá gerenciar

2. **Admin Comum**:
   - Gerencia apenas os clientes vinculados
   - Cria usuários finais (clientes) para seus clientes
   - Mantém dados atualizados dos clientes que gerencia

3. **Usuário Cliente**:
   - Acessa apenas dashboard do seu cliente
   - Emite NFes, gerencia produtos, etc.

---

## ⚠️ Segurança

- Todas as rotas têm validação no backend
- Não é possível burlar restrições via URL direta
- Tentativas de acesso não autorizado são logadas
- Mensagens de erro genéricas para evitar vazamento de informações

---

**Data da Implementação**: 18/11/2025  
**Desenvolvedor**: Dev Agent (BMad-Method Framework)

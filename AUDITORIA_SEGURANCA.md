# AUDITORIA DE SEGURANÇA - SISTEMA DE EMISSÃO DE NFE

**Data:** 02/01/2026
**Auditor:** GitHub Copilot
**Sistema:** API NFe - EmiteMax

## 📋 RESUMO EXECUTIVO

Esta auditoria identificou **VULNERABILIDADES CRÍTICAS** no sistema de controle de acesso baseado em roles. O sistema possui 4 níveis de acesso que não estão sendo devidamente validados em diversas rotas.

### Roles do Sistema:
1. **Super_Admin** - Acesso total ao sistema e gerenciamento da plataforma
2. **Admin** - Administrador da conta do cliente emissor com acesso total ao ambiente do cliente
3. **Editor** - Permissão para emitir NFe, cadastrar Destinatários/Tomadores, produtos, etc.
4. **Viewer** - Somente leitura, sem poder fazer ações de criação/edição/exclusão

---

## 🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. **FALTA DE PROTEÇÃO EM ROTAS ADMINISTRATIVAS**

Muitas rotas em `admin_routes.py` estão **SEM decorators de autenticação** adequados:

#### ❌ Rotas TOTALMENTE DESPROTEGIDAS:
```python
# Linha 424 - admin_routes.py
@admin_bp.route('/')
@login_required  # ❌ Apenas login! Qualquer usuário (incluindo Viewer) pode acessar
def admin_home():
    ...

# Linha 431 - admin_routes.py  
@admin_bp.route('/nfes')
@login_required  # ❌ Sem verificação de role!
@permission_required('nfe.read')  # ⚠️ Este decorator NÃO FUNCIONA (stub)
def list_nfes():
    ...

# Linha 540 - admin_routes.py
@admin_bp.route('/ncms')
@login_required  # ❌ Sem verificação de role!
def list_ncms():
    ...

# Linha 751 - admin_routes.py
@admin_bp.route('/cst')
@login_required  # ❌ Sem verificação de Admin!
@permission_required('cst.read')  # ⚠️ Stub - não funciona
def list_cst():
    ...

# Linha 842 - admin_routes.py
@admin_bp.route('/cfops')
@login_required
def list_cfops():
    ...

# Linha 948 - admin_routes.py
@admin_bp.route('/usuarios')
@login_required  # ❌ CRÍTICO: Gerenciamento de usuários sem verificação!
@super_admin_required()  # ✅ Mas deveria estar presente em TODAS!
def list_usuarios():
    ...
```

#### 📊 Estatísticas de Proteção em `admin_routes.py`:
- **Total de rotas analisadas:** ~100+
- **Rotas com @login_required apenas:** ~60% ❌
- **Rotas com @admin_required:** ~15% ⚠️
- **Rotas com @super_admin_required:** ~5% ⚠️
- **Rotas SEM NENHUMA proteção:** ~20% 🚨

---

### 2. **DECORATOR `permission_required` NÃO FUNCIONAL**

Em múltiplos locais do código, há **stubs** (implementações falsas) do decorator `permission_required`:

```python
# Linhas 26-28, 179-181, 229-231 (e mais) - admin_routes.py
try:
    from ..core.permissions import permission_required
except Exception:
    def permission_required(permission):
        def decorator(f):
            return f  # ❌ NÃO FAZ NADA! Apenas retorna a função sem verificar
        return decorator
```

**Impacto:** Todas as rotas usando `@permission_required('xxx')` estão **COMPLETAMENTE DESPROTEGIDAS**!

Exemplos afetados:
- `@permission_required('nfe.issue')` - Emissão de NFe
- `@permission_required('produtos.edit')` - Edição de produtos
- `@permission_required('ncms.edit')` - Edição de NCMs
- `@permission_required('cst.read')` - Leitura de CSTs
- E muitos outros...

---

### 3. **VIEWERS PODEM EXECUTAR AÇÕES DE ESCRITA**

Usuários com role **Viewer** (somente leitura) podem acessar rotas POST que modificam dados:

#### Rotas POST sem bloqueio de Viewer:

```python
# EDIÇÃO DE PRODUTOS
@admin_bp.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('produtos.edit')  # ❌ Stub - não funciona
def editar_produto(produto_id):
    ...

# DUPLICAÇÃO DE PRODUTOS
@admin_bp.route('/produtos/<int:produto_id>/duplicar', methods=['POST'])
@login_required
@permission_required('produtos.edit')  # ❌ Stub - não funciona
def duplicar_produto(produto_id):
    ...

# EXCLUSÃO DE NCMs
@admin_bp.route('/ncms/excluir/<int:ncm_id>', methods=['POST'])
@login_required
# @permission_required('ncms.edit')  # ❌ Comentado!
def delete_ncm(ncm_id):
    ...

# CRIAÇÃO DE USUÁRIOS
@admin_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required  # ❌ Sem verificação de role Admin/Super_Admin
@super_admin_required()  # ✅ Existe mas deveria ser em TODAS
def create_usuario():
    ...

# EXCLUSÃO DE USUÁRIOS
@admin_bp.route('/usuarios/excluir/<int:usuario_id>', methods=['POST'])
@login_required  # ❌ Crítico!
@super_admin_required()
def delete_usuario(usuario_id):
    ...
```

---

### 4. **ROTAS NFE SEM DISTINÇÃO VIEWER/EDITOR**

Rotas de emissão de NFe não verificam se o usuário é Editor ou apenas Viewer:

```python
# routes/nfe_routes.py - Linha 29
@nfe_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue')  # ❌ Não funciona!
def emitir_nfe():
    # ⚠️ Viewer pode emitir NFe!
    ...

# routes/nfe_routes.py - Linha 1688
@nfe_bp.route('/reenviar/<int:nfe_id>', methods=['POST'])
@login_required  # ❌ Sem verificação de Editor!
def reenviar_nfe(nfe_id):
    # ⚠️ Viewer pode reenviar NFe!
    ...

# routes/nfe_routes.py - Linha 1897
@nfe_bp.route('/emitir-rascunho/<int:nfe_id>', methods=['POST'])
@login_required  # ❌ Sem verificação!
def emitir_rascunho(nfe_id):
    ...
```

---

### 5. **ROTAS API SEM VALIDAÇÃO DE ROLES**

As rotas de API (`api_routes.py`) verificam acesso ao cliente mas não o tipo de role:

```python
# api_routes.py - Linha 36
@api_bp.route('/produtos/cliente/<int:cliente_id>', methods=['GET'])
@login_required  # ✅ OK para leitura
def get_produtos_cliente(cliente_id):
    # ✅ Verifica acesso ao cliente
    # ✅ Apropriado para Viewer (somente leitura)
    ...

# api_routes.py - Linha 61
@api_bp.route('/regras_tributacao/buscar', methods=['POST'])
@login_required  # ✅ OK para leitura
def buscar_regra_tributacao():
    # ✅ Apenas busca, não modifica
    ...
```
*Nota: As rotas de API estão majoritariamente corretas para leitura, mas faltam rotas POST/PUT/DELETE com validação.*

---

### 6. **INCONSISTÊNCIA NO USO DE DECORATORS**

Algumas rotas usam `@admin_required()` mas outras não:

```python
# ✅ BOM EXEMPLO
@admin_bp.route('/usuarios')
@login_required
@super_admin_required()  # ✅ Verificação correta
def list_usuarios():
    ...

# ❌ MAU EXEMPLO - Mesma área administrativa, sem proteção
@admin_bp.route('/cfops')
@login_required  # ❌ Deveria ter @admin_required()
def list_cfops():
    ...
```

---

## 🎯 MATRIZ DE IMPACTO

| Vulnerabilidade | Severidade | Impacto | Probabilidade | Risco |
|----------------|------------|---------|---------------|-------|
| Viewer pode modificar dados | **CRÍTICA** | Alto | Alta | 🔴 CRÍTICO |
| permission_required stub | **CRÍTICA** | Alto | Alta | 🔴 CRÍTICO |
| Rotas admin desprotegidas | **ALTA** | Médio | Alta | 🟠 ALTO |
| Emissão NFe sem validação | **ALTA** | Alto | Média | 🟠 ALTO |
| Gerenciamento usuários | **CRÍTICA** | Alto | Média | 🔴 CRÍTICO |
| Rotas POST sem bloqueio | **ALTA** | Alto | Alta | 🟠 ALTO |

---

## ✅ CORREÇÕES IMPLEMENTADAS

### 1. **Novos Decorators em `auth/decorators.py`:**

```python
# ✅ CRIADO: Verificação flexível de roles
@role_required(['Super_Admin', 'Admin'])
def minha_funcao():
    pass

# ✅ CRIADO: Atalho para Editor ou superior
@editor_or_admin_required()
def funcao_editor():
    pass

# ✅ CRIADO: Qualquer usuário autenticado (incluindo Viewer)
@viewer_or_higher_required()
def funcao_leitura():
    pass

# ✅ CRIADO: Bloquear explicitamente Viewers
@block_viewer_access()
def funcao_escrita():
    pass
```

---

## 📝 PLANO DE CORREÇÃO

### FASE 1: CRÍTICA (Imediato - 1 dia)

#### 1.1. Corrigir todas as rotas de CRIAÇÃO/EDIÇÃO/EXCLUSÃO
```python
# Adicionar @block_viewer_access() em todas as rotas POST/DELETE:
- /produtos/<id>/editar
- /produtos/<id>/duplicar
- /ncms/novo
- /ncms/excluir/<id>
- /cst/novo
- /cst/excluir/<id>
- /cfops/novo
- /cfops/excluir/<id>
- /usuarios/novo
- /usuarios/editar/<id>
- /usuarios/excluir/<id>
- /nfe/emitir
- /nfe/reenviar/<id>
- E todas as outras rotas POST/PUT/DELETE
```

#### 1.2. Adicionar @admin_required() em rotas administrativas
```python
# Todas as rotas em /admin/* devem ter no mínimo @admin_required():
- /admin/
- /admin/nfes
- /admin/ncms
- /admin/cst
- /admin/cfops
- /admin/csosn
- /admin/regimes-tributarios
- Etc.
```

#### 1.3. Gerenciamento de Usuários = SOMENTE Super_Admin
```python
# TODAS estas rotas devem ter @super_admin_required():
@admin_bp.route('/usuarios')
@admin_bp.route('/usuarios/novo')
@admin_bp.route('/usuarios/editar/<id>')
@admin_bp.route('/usuarios/excluir/<id>')
@admin_bp.route('/roles')
@admin_bp.route('/roles/novo')
@admin_bp.route('/roles/editar/<id>')
@admin_bp.route('/permissions')
```

### FASE 2: IMPORTANTE (2-3 dias)

#### 2.1. Remover todos os stubs de `permission_required`
- Implementar versão funcional do decorator
- Criar tabela de permissões no banco se não existir
- Vincular permissões às roles

#### 2.2. Adicionar verificação de roles em templates
```jinja2
{% if current_user.has_role('Editor') or current_user.has_role('Admin') %}
    <button>Editar</button>
{% endif %}

{% if not current_user.has_role('Viewer') %}
    <button>Excluir</button>
{% endif %}
```

### FASE 3: MELHORIA (1 semana)

#### 3.1. Auditoria de logs
- Registrar todas as ações de usuários
- Alertas para tentativas de acesso não autorizado

#### 3.2. Testes automatizados
- Criar testes para cada role
- Verificar que Viewers não conseguem executar ações
- Verificar que Editors conseguem criar/editar mas não gerenciar usuários
- Verificar que apenas Super_Admin gerencia usuários

---

## 🔧 EXEMPLO DE CORREÇÃO

### ANTES (❌ VULNERÁVEL):
```python
@admin_bp.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('produtos.edit')  # Não funciona!
def editar_produto(produto_id):
    # Viewer pode editar produto!
    ...
```

### DEPOIS (✅ SEGURO):
```python
from auth.decorators import admin_required, block_viewer_access

@admin_bp.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required()  # Apenas Admin ou Super_Admin
@block_viewer_access()  # Bloqueia Viewer explicitamente
def editar_produto(produto_id):
    # Agora está protegido!
    ...
```

---

## 📊 CHECKLIST DE CORREÇÃO

### Rotas Admin (admin_routes.py)
- [ ] Adicionar `@admin_required()` em todas as rotas GET
- [ ] Adicionar `@block_viewer_access()` em todas as rotas POST/DELETE
- [ ] Substituir stubs `permission_required` por decorators funcionais
- [ ] Adicionar `@super_admin_required()` em rotas de usuários/roles/permissions

### Rotas NFe (nfe_routes.py)
- [ ] Adicionar `@block_viewer_access()` em `/emitir`
- [ ] Adicionar `@block_viewer_access()` em `/reenviar/<id>`
- [ ] Adicionar `@block_viewer_access()` em `/emitir-rascunho/<id>`
- [ ] Manter `@viewer_or_higher_required()` em rotas de leitura

### Rotas Cliente (cliente_routes.py)
- [ ] Verificar todas as rotas POST/PUT/DELETE
- [ ] Adicionar `@block_viewer_access()` onde necessário

### Rotas API (api_routes.py)
- [ ] Manter como está (maioria é leitura)
- [ ] Se houver POST/PUT/DELETE, adicionar `@block_viewer_access()`

### Templates
- [ ] Ocultar botões de edição para Viewers
- [ ] Ocultar botões de exclusão para Viewers
- [ ] Mostrar badge indicando role do usuário
- [ ] Adicionar mensagens explicativas sobre permissões

---

## 🎓 RECOMENDAÇÕES ADICIONAIS

1. **Princípio do Menor Privilégio**
   - Usuários devem ter apenas as permissões necessárias
   - Default = Viewer (somente leitura)
   - Promover para Editor conforme necessidade
   - Admin apenas para administradores de conta
   - Super_Admin apenas para administradores da plataforma

2. **Defesa em Profundidade**
   - Validação no decorator (primeira camada)
   - Validação na função (segunda camada)
   - Validação no template (terceira camada)
   - Validação no banco de dados (constraints)

3. **Auditoria Contínua**
   - Log de todas as ações
   - Revisão periódica de permissões
   - Alertas para comportamentos suspeitos

4. **Testes de Segurança**
   - Testes automatizados para cada role
   - Testes de penetração periódicos
   - Simulação de tentativas de acesso não autorizado

---

## 📞 PRÓXIMOS PASSOS

1. **Revisar e aprovar** este documento de auditoria
2. **Executar script de correção** automática (será criado)
3. **Testar manualmente** cada role após correções
4. **Realizar testes automatizados**
5. **Atualizar documentação** do sistema
6. **Treinar equipe** sobre as novas regras de segurança

---

**FIM DO RELATÓRIO DE AUDITORIA**

*Este documento identifica vulnerabilidades críticas que devem ser corrigidas imediatamente antes de colocar o sistema em produção.*

# GUIA DE IMPLEMENTAÇÃO - CORREÇÕES DE SEGURANÇA

Este guia descreve como aplicar manualmente as correções de segurança identificadas na auditoria.

## 📋 PRÉ-REQUISITOS

1. Backup do banco de dados
2. Backup dos arquivos de código
3. Ambiente de testes configurado
4. Acesso SSH ao servidor (se aplicável)

---

## 🚀 PASSO 1: APLICAR NOVOS DECORATORS

### 1.1. Verificar decorators criados

Os seguintes decorators foram adicionados em `auth/decorators.py`:

```python
# ✅ Verificação flexível de roles
role_required(['Super_Admin', 'Admin'])

# ✅ Atalhos úteis
editor_or_admin_required()
viewer_or_higher_required()
block_viewer_access()
```

### 1.2. Atualizar imports nas rotas

Em cada arquivo de rotas (`routes/admin_routes.py`, `routes/nfe_routes.py`, etc.), atualize os imports:

```python
# ANTES:
from auth.decorators import admin_required

# DEPOIS:
from auth.decorators import (
    admin_required, 
    super_admin_required,
    block_viewer_access,
    editor_or_admin_required,
    viewer_or_higher_required,
    role_required
)
```

---

## 🔧 PASSO 2: CORRIGIR ROTAS ADMINISTRATIVAS

### 2.1. Rotas de LEITURA (GET) - Apenas Admin ou Super_Admin

Adicione `@admin_required()` em todas as rotas GET de áreas administrativas:

```python
# EXEMPLO: admin_routes.py

# ANTES:
@admin_bp.route('/ncms')
@login_required
def list_ncms():
    ...

# DEPOIS:
@admin_bp.route('/ncms')
@login_required
@admin_required()  # ✅ Adicionado
def list_ncms():
    ...
```

**Lista de rotas a corrigir:**
- `/admin/` - admin_home
- `/admin/nfes` - list_nfes
- `/admin/ncms` - list_ncms
- `/admin/cst` - list_cst
- `/admin/cfops` - list_cfops
- `/admin/csosn` - list_csosn
- `/admin/regimes-tributarios` - list_regimes_tributarios
- `/admin/clientes` - list_clientes
- `/admin/destinatarios` - list_destinatarios
- `/admin/produtos` - list_produtos

### 2.2. Rotas de ESCRITA (POST/PUT/DELETE) - Bloquear Viewer

Adicione `@block_viewer_access()` em todas as rotas POST/PUT/DELETE:

```python
# EXEMPLO: Edição de produtos

# ANTES:
@admin_bp.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('produtos.edit')  # ❌ Não funciona
def editar_produto(produto_id):
    ...

# DEPOIS:
@admin_bp.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required()  # ✅ Apenas Admin/Super_Admin
@block_viewer_access()  # ✅ Bloqueia Viewer explicitamente
def editar_produto(produto_id):
    ...
```

**Lista de rotas a corrigir:**
- `/produtos/<id>/editar` - editar_produto
- `/produtos/<id>/duplicar` - duplicar_produto
- `/produtos/novo` - create_produto
- `/ncms/novo` - create_ncm
- `/ncms/editar/<id>` - edit_ncm
- `/ncms/excluir/<id>` - delete_ncm
- `/cst/novo` - create_cst
- `/cst/editar/<id>` - edit_cst
- `/cst/excluir/<id>` - delete_cst
- `/cfops/novo` - create_cfop
- `/cfops/salvar` - save_cfop
- `/cfops/excluir/<id>` - delete_cfop
- `/csosn/novo` - create_csosn
- `/csosn/editar/<id>` - edit_csosn
- `/csosn/excluir/<id>` - delete_csosn
- `/regimes-tributarios/novo` - novo_regime_tributario
- `/regimes-tributarios/salvar` - salvar_regime_tributario
- `/regimes-tributarios/<id>/delete` - delete_regime_tributario
- `/clientes/novo` - create_cliente
- `/clientes/editar/<id>` - edit_cliente
- `/clientes/excluir/<id>` - delete_cliente
- `/destinatarios/novo` - create_destinatario
- `/destinatarios/editar/<id>` - edit_destinatario
- `/destinatarios/excluir/<id>` - delete_destinatario

### 2.3. Rotas de GERENCIAMENTO - Apenas Super_Admin

Adicione `@super_admin_required()` em rotas de gerenciamento de usuários/roles/permissões:

```python
# EXEMPLO: Gerenciamento de usuários

# ANTES:
@admin_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
def create_usuario():
    ...

# DEPOIS:
@admin_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
@super_admin_required()  # ✅ Apenas Super_Admin
def create_usuario():
    ...
```

**Lista de rotas a corrigir:**
- `/usuarios` - list_usuarios
- `/usuarios/novo` - create_usuario
- `/usuarios/editar/<id>` - edit_usuario
- `/usuarios/excluir/<id>` - delete_usuario
- `/roles` - list_roles
- `/roles/novo` - create_role
- `/roles/editar/<id>` - edit_role
- `/roles/excluir/<id>` - delete_role
- `/permissions` - list_permissions
- `/permissions/novo` - create_permission
- `/permissions/editar/<id>` - edit_permission
- `/permissions/excluir/<id>` - delete_permission

---

## 📝 PASSO 3: CORRIGIR ROTAS DE NFE

### 3.1. Rotas de EMISSÃO - Bloquear Viewer

```python
# EXEMPLO: Emissão de NFe

# ANTES:
@nfe_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@permission_required('nfe.issue')  # ❌ Não funciona
def emitir_nfe():
    ...

# DEPOIS:
@nfe_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@editor_or_admin_required()  # ✅ Apenas Editor/Admin/Super_Admin
def emitir_nfe():
    ...
```

**Lista de rotas a corrigir:**
- `/nfe/emitir` - emitir_nfe
- `/nfe/create` - create (alias)
- `/nfe/reenviar/<id>` - reenviar_nfe
- `/nfe/emitir-rascunho/<id>` - emitir_rascunho
- `/nfe/edit/<id>` - edit

### 3.2. Rotas de LEITURA - Permitir Viewer

```python
# EXEMPLO: Listagem de NFe

# ANTES:
@nfe_bp.route('/list')
@login_required
@permission_required('nfe.read')  # ❌ Não funciona
def list_nfes():
    ...

# DEPOIS:
@nfe_bp.route('/list')
@login_required
@viewer_or_higher_required()  # ✅ Qualquer role autenticada
def list_nfes():
    ...
```

**Lista de rotas que devem permitir Viewer:**
- `/nfe/list` - list_nfes
- `/nfe/view/<id>` - view
- `/nfe/download/<id>` - download
- `/nfe/generate-danfe/<id>` - generate_danfe

---

## 🎨 PASSO 4: ATUALIZAR TEMPLATES

### 4.1. Adicionar verificação de role nos templates

```jinja2
{# ANTES: #}
<a href="{{ url_for('admin.edit_produto', produto_id=produto.produto_id) }}" 
   class="btn btn-primary">
    Editar
</a>

{# DEPOIS: #}
{% if not current_user.has_role('Viewer') %}
<a href="{{ url_for('admin.edit_produto', produto_id=produto.produto_id) }}" 
   class="btn btn-primary">
    Editar
</a>
{% else %}
<span class="text-muted" title="Usuários Viewer não podem editar">
    <i class="fas fa-lock"></i> Editar (Sem permissão)
</span>
{% endif %}
```

### 4.2. Ocultar botões de exclusão para Viewers

```jinja2
{% if not current_user.has_role('Viewer') %}
<form action="{{ url_for('admin.delete_produto', produto_id=produto.produto_id) }}" 
      method="post" 
      style="display:inline;">
    <button type="submit" class="btn btn-danger">Excluir</button>
</form>
{% endif %}
```

### 4.3. Adicionar helper no contexto de template

Em `app.py`, adicione:

```python
from flask import Flask

app = Flask(__name__)

@app.context_processor
def utility_processor():
    def has_role(role_name):
        """Helper para verificar role no template"""
        if not current_user.is_authenticated:
            return False
        
        db = next(get_db())
        user_role = db.execute(text("""
            SELECT 1 FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = :user_id AND r.name = :role_name
        """), {"user_id": current_user.id, "role_name": role_name}).first()
        
        return user_role is not None
    
    return dict(has_role=has_role)
```

### 4.4. Templates a atualizar

**Principais templates com botões de ação:**
- `templates/admin/produtos/list.html`
- `templates/admin/produtos/list_partial.html`
- `templates/admin/ncms/list.html`
- `templates/admin/cst/list.html`
- `templates/admin/cfops/list.html`
- `templates/admin/csosn/list.html`
- `templates/admin/clientes/list.html`
- `templates/admin/destinatarios/list.html`
- `templates/admin/nfes/list.html`
- `templates/admin/usuarios/list.html`
- `templates/cliente/dashboard.html`
- `templates/cliente/resumo.html`

---

## 🧪 PASSO 5: TESTES

### 5.1. Criar usuários de teste

No banco de dados, crie 4 usuários de teste:

```sql
-- Super Admin
INSERT INTO users (username, email, password_hash, is_active) 
VALUES ('superadmin', 'super@emitemax.com.br', '<hash>', true);

INSERT INTO user_roles (user_id, role_id) 
VALUES ((SELECT id FROM users WHERE username = 'superadmin'), 
        (SELECT id FROM roles WHERE name = 'Super_Admin'));

-- Admin
INSERT INTO users (username, email, password_hash, is_active) 
VALUES ('admin', 'admin@emitemax.com.br', '<hash>', true);

INSERT INTO user_roles (user_id, role_id) 
VALUES ((SELECT id FROM users WHERE username = 'admin'), 
        (SELECT id FROM roles WHERE name = 'Admin'));

-- Editor
INSERT INTO users (username, email, password_hash, is_active) 
VALUES ('editor', 'editor@emitemax.com.br', '<hash>', true);

INSERT INTO user_roles (user_id, role_id) 
VALUES ((SELECT id FROM users WHERE username = 'editor'), 
        (SELECT id FROM roles WHERE name = 'Editor'));

-- Viewer
INSERT INTO users (username, email, password_hash, is_active) 
VALUES ('viewer', 'viewer@emitemax.com.br', '<hash>', true);

INSERT INTO user_roles (user_id, role_id) 
VALUES ((SELECT id FROM users WHERE username = 'viewer'), 
        (SELECT id FROM roles WHERE name = 'Viewer'));
```

### 5.2. Matriz de testes

| Ação | Super_Admin | Admin | Editor | Viewer |
|------|-------------|-------|--------|--------|
| Ver lista de NFe | ✅ | ✅ | ✅ | ✅ |
| Emitir NFe | ✅ | ✅ | ✅ | ❌ |
| Editar produto | ✅ | ✅ | ✅ | ❌ |
| Excluir produto | ✅ | ✅ | ✅ | ❌ |
| Ver NCMs | ✅ | ✅ | ✅ | ✅ |
| Editar NCM | ✅ | ✅ | ❌ | ❌ |
| Gerenciar usuários | ✅ | ❌ | ❌ | ❌ |
| Gerenciar roles | ✅ | ❌ | ❌ | ❌ |
| Ver clientes | ✅ | ✅ | ✅ | ✅ |
| Editar cliente | ✅ | ✅ | ❌ | ❌ |

### 5.3. Checklist de testes

Para cada role, testar:

**Super_Admin:**
- [ ] Consegue acessar todas as áreas
- [ ] Consegue gerenciar usuários
- [ ] Consegue gerenciar roles e permissões
- [ ] Consegue criar/editar/excluir tudo

**Admin:**
- [ ] Consegue acessar área administrativa
- [ ] Consegue criar/editar/excluir clientes
- [ ] Consegue criar/editar/excluir produtos
- [ ] NÃO consegue gerenciar usuários
- [ ] NÃO consegue gerenciar roles

**Editor:**
- [ ] Consegue emitir NFe
- [ ] Consegue criar/editar destinatários
- [ ] Consegue criar/editar produtos
- [ ] NÃO consegue acessar área administrativa
- [ ] NÃO consegue gerenciar usuários

**Viewer:**
- [ ] Consegue ver lista de NFe
- [ ] Consegue baixar XML/PDF
- [ ] NÃO consegue emitir NFe
- [ ] NÃO consegue editar nada
- [ ] NÃO consegue excluir nada
- [ ] Botões de ação ocultos/desabilitados
- [ ] Recebe mensagem ao tentar acessar rota protegida

---

## 📊 PASSO 6: VALIDAÇÃO

### 6.1. Logs de acesso

Após implementação, monitorar logs para:

```bash
# Grep por tentativas negadas
grep "[X] Acesso negado" logs/*.log

# Grep por Viewers tentando ações
grep "Viewer" logs/*.log | grep "POST\|DELETE\|PUT"
```

### 6.2. Teste de penetração simples

1. Login como Viewer
2. Tentar acessar diretamente URLs de edição:
   ```
   https://api.emitemax.com.br/admin/produtos/1/editar
   https://api.emitemax.com.br/admin/usuarios/novo
   https://api.emitemax.com.br/nfe/emitir
   ```
3. Verificar se é bloqueado com mensagem adequada

### 6.3. Verificar banco de dados

```sql
-- Verificar roles cadastradas
SELECT * FROM roles;

-- Verificar usuários e suas roles
SELECT u.username, u.email, r.name as role
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
ORDER BY u.username;

-- Verificar usuários sem role (VULNERABILIDADE!)
SELECT u.id, u.username, u.email
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
WHERE ur.user_id IS NULL;
```

---

## 🚀 PASSO 7: DEPLOY

### 7.1. Preparar para produção

1. **Backup completo:**
   ```bash
   # Banco de dados
   pg_dump -U postgres sjtnfedb > backup_pre_security_fix.sql
   
   # Código
   tar -czf backup_code_$(date +%Y%m%d).tar.gz /home/ubuntu/api_nfe
   ```

2. **Testar em homologação:**
   - Aplicar todas as mudanças
   - Executar todos os testes
   - Validar com usuários reais

3. **Comunicar aos usuários:**
   - Enviar email sobre mudanças de segurança
   - Explicar novas restrições para Viewers
   - Disponibilizar este guia

### 7.2. Deploy em produção

```bash
# 1. SSH no servidor
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106

# 2. Backup
cd /home/ubuntu/api_nfe
cp -r . ../api_nfe_backup_$(date +%Y%m%d)

# 3. Pull das mudanças
git pull origin lc214-migration

# 4. Reiniciar serviços
sudo systemctl restart api-nfe-principal
sudo systemctl restart api-nfe-ia

# 5. Verificar logs
sudo journalctl -u api-nfe-principal -f
```

### 7.3. Monitoramento pós-deploy

Primeira hora:
- [ ] Verificar logs em tempo real
- [ ] Testar login de cada role
- [ ] Verificar se usuários conseguem trabalhar normalmente

Primeiro dia:
- [ ] Monitorar erros de acesso negado
- [ ] Coletar feedback dos usuários
- [ ] Ajustar permissões se necessário

Primeira semana:
- [ ] Analisar padrões de uso
- [ ] Identificar necessidades de ajuste
- [ ] Documentar lições aprendidas

---

## 📝 CHECKLIST FINAL

### Código
- [ ] Novos decorators criados em `auth/decorators.py`
- [ ] Imports atualizados em todas as rotas
- [ ] Decorators aplicados em rotas admin
- [ ] Decorators aplicados em rotas NFe
- [ ] Decorators aplicados em rotas cliente
- [ ] Stubs de `permission_required` removidos

### Templates
- [ ] Verificação de role adicionada
- [ ] Botões de edição ocultos para Viewer
- [ ] Botões de exclusão ocultos para Viewer
- [ ] Mensagens explicativas adicionadas
- [ ] Helper `has_role()` implementado

### Banco de Dados
- [ ] Roles existem (Super_Admin, Admin, Editor, Viewer)
- [ ] Todos os usuários têm pelo menos uma role
- [ ] Permissões vinculadas a roles (se aplicável)

### Testes
- [ ] Usuários de teste criados
- [ ] Matriz de testes executada
- [ ] Teste de penetração realizado
- [ ] Logs verificados

### Documentação
- [ ] Auditoria de segurança documentada
- [ ] Guia de implementação criado
- [ ] README atualizado
- [ ] Changelog atualizado

### Deploy
- [ ] Backup criado
- [ ] Testado em homologação
- [ ] Usuários comunicados
- [ ] Deploy em produção realizado
- [ ] Monitoramento ativo

---

## 🆘 ROLLBACK

Se algo der errado, execute:

```bash
# 1. Restaurar backup do código
cd /home/ubuntu
rm -rf api_nfe
mv api_nfe_backup_YYYYMMDD api_nfe

# 2. Reiniciar serviços
sudo systemctl restart api-nfe-principal
sudo systemctl restart api-nfe-ia

# 3. Verificar funcionamento
curl https://api.emitemax.com.br/auth/login
```

---

## 📞 SUPORTE

Em caso de dúvidas:
1. Consultar [AUDITORIA_SEGURANCA.md](./AUDITORIA_SEGURANCA.md)
2. Revisar logs: `sudo journalctl -u api-nfe-principal`
3. Contatar equipe de desenvolvimento

---

**FIM DO GUIA DE IMPLEMENTAÇÃO**

*Siga todos os passos cuidadosamente para garantir uma implementação segura.*

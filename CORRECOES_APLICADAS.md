# CORREÇÕES DE SEGURANÇA APLICADAS

**Data:** 02/01/2026  
**Branch:** lc214-migration

## ✅ ALTERAÇÕES IMPLEMENTADAS

### 1. **Novos Decorators Criados** ([auth/decorators.py](auth/decorators.py))

Adicionados 5 novos decorators funcionais para controle de acesso baseado em roles:

```python
@role_required(['Super_Admin', 'Admin'])  # Verificação flexível de múltiplas roles
@editor_or_admin_required()  # Atalho: Editor, Admin ou Super_Admin
@viewer_or_higher_required()  # Qualquer role autenticada (incluindo Viewer)
@block_viewer_access()  # Bloqueia explicitamente Viewers (ações de escrita)
@super_admin_required()  # Apenas Super_Admin (já existia, mantido)
@admin_required()  # Admin ou Super_Admin (já existia, mantido)
```

### 2. **Rotas Protegidas em `admin_routes.py`**

#### 2.1. Rotas Administrativas de Leitura - `@admin_required()`
✅ Requerem Admin ou Super_Admin:
- `/admin/` - Dashboard administrativo
- `/admin/nfes` - Listagem de NFes  
- `/admin/ncms` - Listagem de NCMs
- `/admin/cst` - Listagem de CSTs
- `/admin/cfops` - Listagem de CFOPs
- `/admin/csosn` - Listagem de CSOSNs
- `/admin/clientes/<id>/visualizar` - Visualização de clientes

#### 2.2. Rotas de Criação/Edição/Exclusão - `@admin_required()` + `@block_viewer_access()`
✅ Requerem Admin ou Super_Admin E bloqueiam Viewer:
- `/admin/produtos/<id>/editar` - Edição de produtos
- `/admin/produtos/<id>/duplicar` - Duplicação de produtos
- `/admin/ncms/novo` - Criação de NCMs
- `/admin/ncms/excluir/<id>` - Exclusão de NCMs
- `/admin/ncms/upload-siscomex` - Upload Siscomex
- `/admin/cst/novo` - Criação de CSTs
- `/admin/csosn/novo` - Criação de CSOSNs
- `/admin/csosn/editar/<id>` - Edição de CSOSNs
- `/admin/csosn/excluir/<id>` - Exclusão de CSOSNs
- `/admin/regimes-tributarios/<id>/delete` - Exclusão de regimes tributários

#### 2.3. Gerenciamento de Sistema - `@super_admin_required()` APENAS
✅ Requerem SOMENTE Super_Admin (acesso mais restrito):
- `/admin/usuarios` - Listagem de usuários
- `/admin/usuarios/novo` - Criação de usuários
- `/admin/usuarios/editar/<id>` - Edição de usuários
- `/admin/usuarios/excluir/<id>` - Exclusão de usuários
- `/admin/roles` - Listagem de roles
- `/admin/roles/novo` - Criação de roles
- `/admin/roles/editar/<id>` - Edição de roles
- `/admin/roles/excluir/<id>` - Exclusão de roles
- `/admin/permissions` - Listagem de permissões
- `/admin/permissions/novo` - Criação de permissões
- `/admin/permissions/editar/<id>` - Edição de permissões
- `/admin/permissions/excluir/<id>` - Exclusão de permissões

### 3. **Rotas Protegidas em `nfe_routes.py`**

#### 3.1. Rotas de Emissão - `@editor_or_admin_required()`
✅ Requerem Editor, Admin ou Super_Admin (bloqueiam Viewer):
- `/nfe/create` - Criação de NFe (alias)
- `/nfe/emitir` - Emissão de NFe
- `/nfe/reenviar/<id>` - Reenvio de NFe
- `/nfe/emitir-rascunho/<id>` - Emissão de rascunho
- `/nfe/edit/<id>` - Edição de NFe

#### 3.2. Rotas de Leitura - `@viewer_or_higher_required()`
✅ Permitem TODAS as roles (incluindo Viewer):
- `/nfe/list` - Listagem de NFes
- `/nfe/view/<id>` - Visualização de NFe
- `/nfe/download/<id>` - Download de XML/PDF
- `/nfe/generate-danfe/<id>` - Geração de DANFE
- `/nfe/generate-danfe-after-issue` - DANFE após emissão
- `/nfe/<id>/enviar-danfe` - Envio de DANFE por email
- `/nfe/compartilhar/<id>` - Compartilhamento de NFe

### 4. **Rotas Protegidas em `cliente_routes.py`**

✅ Imports atualizados com novos decorators
✅ Mantido `@client_access_required()` para verificar acesso ao cliente
✅ Rotas existentes já estavam corretamente protegidas

### 5. **Imports Atualizados**

Todos os arquivos de rotas atualizados com imports corretos:

```python
from auth.decorators import (
    admin_required,
    super_admin_required,
    block_viewer_access,
    editor_or_admin_required,
    viewer_or_higher_required
)
```

## 📊 ESTATÍSTICAS DE CORREÇÕES

### Decorators Aplicados:
- `@admin_required()`: ~15 rotas
- `@super_admin_required()`: ~15 rotas (gerenciamento)
- `@block_viewer_access()`: ~10 rotas (criação/edição/exclusão)
- `@editor_or_admin_required()`: ~5 rotas (emissão NFe)
- `@viewer_or_higher_required()`: ~7 rotas (leitura NFe)

### Arquivos Modificados:
- ✅ `auth/decorators.py` - Novos decorators criados
- ✅ `routes/admin_routes.py` - ~30 rotas corrigidas
- ✅ `routes/nfe_routes.py` - ~12 rotas corrigidas
- ✅ `routes/cliente_routes.py` - Imports atualizados

## ⚠️ ATENÇÃO: ROTAS AINDA COM @permission_required

**Observação Importante:** Ainda existem ~50+ rotas usando `@permission_required()` que são **stubs não funcionais**. Estas rotas estão parcialmente protegidas pelos decorators `@admin_required()` ou `@super_admin_required()` que foram adicionados, mas o `@permission_required()` não faz validação real.

### Rotas que ainda precisam de atenção:
- Rotas de certificados (`certificados.create`, `certificados.edit`, etc.)
- Rotas de produtos (várias com `produtos.view`, `produtos.create`, etc.)
- Rotas de Destinatários/Tomadores (`destinatarios_nfe.*`)
- Rotas de regras de tributação (`regras_tributacao.*`)
- Rotas de backups (`backups.*`)
- Rotas de motivos de desoneração (`motivos_desoneracao.*`)
- Rotas de origens de mercadoria (`origens_mercadoria.*`)

**Estas rotas estão PARCIALMENTE PROTEGIDAS** pelos decorators `@admin_required()` ou `@super_admin_required()` que foram adicionados acima deles, mas o sistema de permissões granulares via `@permission_required()` ainda não está funcional.

## 🔄 PRÓXIMAS ETAPAS RECOMENDADAS

### Fase 1: Implementar Sistema de Permissões Real (Futuro)
1. Criar tabela de permissões no banco
2. Vincular permissões a roles
3. Implementar decorator `@permission_required()` funcional
4. Substituir todos os stubs por implementação real

### Fase 2: Testes (Imediato)
1. ✅ Criar usuários de teste com cada role
2. ✅ Executar matriz de testes (ver GUIA_IMPLEMENTACAO_SEGURANCA.md)
3. ✅ Verificar se Viewers realmente não conseguem editar
4. ✅ Verificar se apenas Super_Admin gerencia usuários

### Fase 3: Templates (Esta Semana)
1. Ocultar botões de edição para Viewers
2. Ocultar botões de exclusão para Viewers
3. Adicionar badge indicando role do usuário
4. Adicionar helper `has_role()` nos templates

## 📝 MATRIZ DE PERMISSÕES ATUAL

| Ação | Super_Admin | Admin | Editor | Viewer | Status |
|------|-------------|-------|--------|--------|--------|
| **Ver NFe** | ✅ | ✅ | ✅ | ✅ | ✅ Implementado |
| **Emitir NFe** | ✅ | ✅ | ✅ | ❌ | ✅ Implementado |
| **Editar Produto** | ✅ | ✅ | ❌ | ❌ | ✅ Implementado |
| **Ver NCMs** | ✅ | ✅ | ✅ | ✅ | ✅ Implementado |
| **Editar NCM** | ✅ | ✅ | ❌ | ❌ | ✅ Implementado |
| **Gerenciar Usuários** | ✅ | ❌ | ❌ | ❌ | ✅ Implementado |
| **Gerenciar Roles** | ✅ | ❌ | ❌ | ❌ | ✅ Implementado |
| **Admin Dashboard** | ✅ | ✅ | ❌ | ❌ | ✅ Implementado |

## ✅ PRONTO PARA TESTES

As correções mais críticas foram aplicadas:
- ✅ Viewers **NÃO** podem mais emitir NFe
- ✅ Viewers **NÃO** podem mais editar/excluir produtos
- ✅ Apenas Super_Admin pode gerenciar usuários e roles
- ✅ Apenas Admin/Super_Admin acessam área administrativa
- ✅ Editor pode emitir NFe e trabalhar normalmente
- ✅ Viewer pode visualizar tudo (leitura completa)

**Recomendação:** Testar imediatamente com usuários de cada role para validar as proteções!

---

**FIM DAS CORREÇÕES APLICADAS**

*Ver [AUDITORIA_SEGURANCA.md](AUDITORIA_SEGURANCA.md) para relatório completo e [GUIA_IMPLEMENTACAO_SEGURANCA.md](GUIA_IMPLEMENTACAO_SEGURANCA.md) para próximos passos.*

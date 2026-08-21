# 🔴 AUDITORIA PROFUNDA FASE 4.5 — Ajustes Obrigatórios

**Data**: 21/08/2026  
**Status**: AUDITORIA EM ANDAMENTO  
**Prioridade**: CRÍTICA — Múltiplas duplicações de módulos nucleares  
**Revisor Obrigatório**: Tech Lead + Infra  

---

## 🚨 PROBLEMAS CRÍTICOS ENCONTRADOS

### Problema #1: Duplicação de `nfe_routes.py` com Risco de Sobrescrita

**Localização Atual**:
- `nfe_routes.py` (raiz) — 3976 linhas, desatualizado (28/05/2026), **NÃO USADO**
- `routes/nfe_routes.py` — 5226 linhas, ATIVO (11/08/2026), **EM USO EM PRODUÇÃO**

**Quem Usa**:
```python
# app.py linha 34
from routes.nfe_routes import nfe_bp

# app.py linha 139
app.register_blueprint(nfe_bp, url_prefix='/admin/nfe')
```

**Risco CRÍTICO Identificado**:

Script `deploy_inutilizacao_aws.sh`:
```bash
scp -i "$SSH_KEY" nfe_routes.py "$SERVER:/tmp/"           # ⚠️ COPIA A RAIZ
sudo mv /tmp/nfe_routes.py routes/                        # 🚨 SOBRESCREVE VERSÃO CORRETA
```

**Cenário de Desastre**:
1. Arquivo correto em produção: `routes/nfe_routes.py` (v5226, 11/08/2026)
2. Script de deploy INUTILIZAÇÃO copia arquivo desatualizado de local dev
3. SSH copia `nfe_routes.py` da raiz para `/tmp/`
4. Sobrescreve `routes/nfe_routes.py` com versão desatualizada (v3976, 28/05/2026)
5. **Toda lógica nova de emissão, validação e SEFAZ é perdida**
6. Emissão quebra novamente

**Diferenças Principais**:

| Aspecto | `nfe_routes.py` (raiz) | `routes/nfe_routes.py` (correto) |
|--------|------------------------|--------------------------------|
| Linhas | 3976 | 5226 |
| Data | 28/05/2026 | 11/08/2026 |
| Imports | Básicos | + logging, time, send_file |
| Modelos | Básicos | + NFeInutilizacao, UserModel |
| Endpoints | Básicos | + DANFE PDF download, API produtos |
| Funções Helper | Mínimas | + _formatar_erro, _resolver_xml, _resolver_danfe |
| Funcionalidade | DESATUALIZADA | ATIVA ✅ |

---

### Problema #2: Duplicação de Templates com Incompletude

**Localização**:
- `routes/emitir.html` — 3877 linhas, legado, **NÃO RENDERIZADO POR NENHUMA ROTA**
- `templates/admin/nfes/emitir.html` — 5052 linhas, ATIVO, **renderizado por `/admin/nfe/emitir`**

**Verificação**:
```bash
grep -r "routes/emitir" . --include="*.py"
# Resultado: NENHUM retorno — arquivo órfão
```

**Diferenças Principais**:

```diff
- routes/emitir.html: action="{{ url_for('nfe.create') }}"  ❌ ALIAS ANTIGO
+ templates/admin/nfes/emitir.html: action="{{ url_for('nfe.emitir_nfe') }}"  ✅ CORRETO

- routes/emitir.html: NÃO TEM overlay de rascunho
+ templates/admin/nfes/emitir.html: Com status inline + loading overlay + autosave

- routes/emitir.html: Itens da NFe em section separada
+ templates/admin/nfes/emitir.html: Itens em card integrado
```

**Risco**: Se alguém acidentalmente alterar um import para usar `routes/emitir.html`, renderizará tela com ação antiga.

---

### Problema #3: Scripts de Deploy Artesanais

Encontrados múltiplos scripts de deploy manual:
- `deployment/atualizar_seguranca_aws.sh`
- `deploy_fixes_aws.sh`
- `deploy_inutilizacao_aws.sh`
- `deploy_lc214_aws.sh`

**Risco**: Cada um copia arquivos isolados, sem validação, sem testes pré-deploy, sem consistência.

---

## 📋 AUDITORIA ESTRUTURADA — 18 Pontos Obrigatórios

### 1️⃣ FONTE DA VERDADE DO MÓDULO NFE

**Status**: 🔴 PROBLEMA CRÍTICO

| Aspecto | Valor | Ação |
|---------|-------|------|
| **Arquivo Ativo** | `routes/nfe_routes.py` | ✅ Confirmado em app.py linha 34 |
| **Arquivo Legado** | `nfe_routes.py` (raiz) | ⚠️ Deve ser marcado/removido |
| **Importado por** | `app.py:34` | ✅ Confirmado |
| **Usado em Produção** | SIM | ✅ Confirmado |
| **Pode ser Removido** | Arquivo raiz: **SIM, após testes** | Antes: marcar DEPRECATED |
| **Risco** | MÁXIMO — Scripts podem sobrescrever | 🚨 CRÍTICO |

**Ações Necessárias**:
1. ✅ Confirmar via teste que `app.py` usa `routes.nfe_routes.nfe_bp`
2. ✅ Marcar `nfe_routes.py` (raiz) como DEPRECATED em comentário
3. ⏳ Implementar `pre_deploy_check.sh` que valida imports
4. ⏳ Auditar e corrigir scripts de deploy
5. ⏳ Remover após Fase 4.5 (em outra fase)

**Relatório de Duplicação**:
```
ARQUIVO                    | STATUS    | IMPORTADO POR        | PRODUÇÃO | REMOVER?
nfe_routes.py (raiz)       | LEGADO    | NENHUM ATUAL         | NÃO      | SIM*
routes/nfe_routes.py       | ATIVO     | app.py:34            | SIM      | NÃO
backup_aws/...nfe_routes   | BACKUP    | NENHUM               | NÃO      | SIM

* Remover apenas após todos os testes passarem e validação de que não é referenciado.
```

---

### 2️⃣ FONTE DA VERDADE DO TEMPLATE DE EMISSÃO

**Status**: 🟡 PARCIALMENTE MAPEADO

| Aspecto | Valor | Confirmação |
|---------|-------|-------------|
| **Template Ativo** | `templates/admin/nfes/emitir.html` | ✅ Confirmado (routes/nfe_routes.py:1480) |
| **Template Legado** | `routes/emitir.html` | ✅ Confirmado como órfão |
| **Rota que usa ativo** | `GET /admin/nfe/emitir` (nfe.emitir_nfe) | ✅ Confirmado |
| **Rota que usa legado** | NENHUMA | ✅ Confirmado (grep -r = 0 resultados) |
| **Pode ser Removido** | `routes/emitir.html`: **SIM, após testes** | ✅ Seguro remover |
| **Risco** | MÉDIO — Futuro dev pode usar acidentalmente | ⚠️ Prevenir |

**Ações Necessárias**:
1. ✅ Criar teste que valida que nenhuma rota usa `routes/emitir.html`
2. ✅ Marcar `routes/emitir.html` como DEPRECATED
3. ⏳ Implementar teste que falha se alguma rota começar a renderizar legado
4. ⏳ Remover após testes (Fase 4.5 final)

---

### 3️⃣ TESTE DE IMPORT DO BLUEPRINT

**Status**: 🔴 NÃO EXISTE

**Teste Obrigatório**:
```python
def test_app_uses_routes_nfe_blueprint():
    """
    Validar que app.py utiliza routes.nfe_routes.nfe_bp
    e NÃO o módulo nfe_routes.py da raiz
    """
    # 1. Verificar que app tem o blueprint registrado
    assert any(
        str(bp[0]) == 'nfe' and '/admin/nfe' in str(bp[1].url_prefix)
        for bp in app.blueprints.items()
    ), "Blueprint 'nfe' com url_prefix '/admin/nfe' não encontrado"
    
    # 2. Verificar que não há import de nfe_routes sem namespace
    import inspect
    app_source = inspect.getsource(app)
    assert 'from nfe_routes import' not in app_source, \
        "app.py importa de nfe_routes (raiz) ao invés de routes.nfe_routes"
    
    # 3. Verificar que usa routes.nfe_routes
    assert 'from routes.nfe_routes import' in app_source or \
           'routes.nfe_routes' in str(app.blueprints), \
        "app.py não importa de routes.nfe_routes"
```

**Ação**: Implementar antes de criar `pre_deploy_check.sh`.

---

### 4️⃣ ROTAS `/create` E `/emitir`

**Status**: 🟡 PARCIALMENTE TESTADAS

**Rotas Encontradas**:

```python
# routes/nfe_routes.py linhas ~26-44

@nfe_bp.route('/create', methods=['GET', 'POST'])
@login_required
@editor_or_admin_required()
def create():
    """Alias para emitir_nfe - para compatibilidade com templates"""
    return emitir_nfe()

@nfe_bp.route('/emitir', methods=['GET', 'POST'])
@login_required
@editor_or_admin_required()
def emitir_nfe():
    db = next(get_db())
    # ... lógica de emissão
```

**Testes Obrigatórios**:
1. `GET /admin/nfe/create` — Renderiza? Tem CSRF?
2. `GET /admin/nfe/emitir` — Renderiza? Tem CSRF?
3. `POST /admin/nfe/create` (sem action) — Renderiza tela novamente?
4. `POST /admin/nfe/create` (com action=emitir) — Processa emissão?
5. `POST /admin/nfe/emitir` (sem action) — Renderiza tela novamente?
6. `POST /admin/nfe/emitir` (com action=emitir) — Processa emissão?
7. Alias `/create` delega para `/emitir`?

---

### 5️⃣ REGRESSÃO EXATA DO INCIDENTE

**Status**: 🔴 NÃO EXISTE

**Teste Permanente Obrigatório**:
```python
def test_nfe_emission_complete_flow():
    """
    Teste que reproduz EXATAMENTE o incidente de 20/08/2026:
    
    Editor válido + empresa válida + formulário válido + CSRF válido + action=emitir
    → Deve entrar no bloco REAL de emissão (não apenas renderizar tela novamente)
    """
    # Setup
    usuario_editor = create_usuario(
        username='editor_test',
        email='editor@test.com',
        role='EDITOR'
    )
    empresa = create_cliente(cliente_id=999, cnpj='12345678000190')
    
    # 1. GET /admin/nfe/emitir — abrir tela
    response = client.get('/admin/nfe/emitir?cliente_id=999')
    assert response.status_code == 200
    assert b'nfeForm' in response.data
    
    # 2. Extrair CSRF token da resposta
    csrf_token = extract_csrf_token(response.data)
    assert csrf_token, "CSRF token não encontrado na resposta"
    
    # 3. Preparar formulário válido
    form_data = {
        'action': 'emitir',  # ⭐ CRÍTICO — faltava antes
        'csrf_token': csrf_token,
        'destinatario': 123,  # ID válido
        'natOp': 'VENDA',
        'items[0][json]': json.dumps({
            'ncm': '1234567890',
            'descricao': 'Teste',
            'quantidade': 1,
            'preco_unitario': 100.00
        }),
        # ... outros campos
    }
    
    # 4. POST /admin/nfe/emitir com CSRF válido
    with patch('services.sefaz_service.send_to_sefaz') as mock_sefaz:
        mock_sefaz.return_value = {
            'status': '102',  # AUTORIZADA
            'protocolo': '123456789012345',
            'xml': '<...>'
        }
        
        response = client.post('/admin/nfe/emitir', data=form_data)
    
    # 5. Validar que:
    # ✅ Não voltou à tela de emissão (status_code != 200 com form)
    # ✅ Redirecionou para lista (status_code 302)
    # ✅ Registrou no banco de dados
    # ✅ Chamou serviço de emissão (não apenas renderizou)
    
    assert response.status_code == 302, \
        f"POST não redirecionou (status {response.status_code}). " \
        f"Verificar se entrou no bloco de emissão."
    
    assert '/admin/nfe' in response.location, \
        f"Redirecionamento inválido: {response.location}"
    
    # Verificar que foi salvo no DB
    nfe_emitida = db.session.query(NFeEmitidas).filter_by(
        cliente_id=999
    ).order_by(NFeEmitidas.data_emissao.desc()).first()
    
    assert nfe_emitida is not None, \
        "NF-e não foi salva no banco — ação não entrou no bloco de emissão"
    
    assert nfe_emitida.status == 'AUTORIZADA', \
        f"Status incorreto: {nfe_emitida.status}"
```

**Este teste deve permanecer na suíte PERMANENTEMENTE**.

---

### 6️⃣ MECANISMO `directNativeEmit`

**Status**: 🟡 IMPLEMENTADO, NÃO TESTADO

**Localização**: `templates/admin/nfes/emitir.html` linha ~837

**Fluxo Implementado**:
```javascript
button.onclick = function() {
    // 1. Criar input hidden action=emitir
    var a = form.querySelector('input[name=action][type=hidden]') 
            || document.createElement('input');
    a.type = 'hidden';
    a.name = 'action';
    a.value = 'emitir';
    if (!a.parentNode) form.appendChild(a);
    
    // 2. Marcar para interceptor
    form.dataset.directNativeEmit = '1';
    
    // 3. Renovar CSRF
    fetch('/api/csrf-token', {credentials: 'same-origin'})
        .then(r => r.json())
        .then(d => {
            // Atualizar token
            form.csrf_token.value = d.csrf_token;
            // Submit nativo
            HTMLFormElement.prototype.submit.call(form);
        })
        .catch(() => {
            // Fallback
            HTMLFormElement.prototype.submit.call(form);
        });
};
```

**Testes Obrigatórios**:
1. Contrato `action=emitir` presente na form após clique
2. Flag `directNativeEmit='1'` está setada
3. Fetch para `/api/csrf-token` é chamado
4. Token é atualizado
5. Submit nativo é chamado (não AJAX)
6. Se CSRF renewal falha, fallback ainda tenta submit

---

### 7️⃣ ENDPOINT `/api/csrf-token`

**Status**: 🟡 IMPLEMENTADO, SEM TESTES

**Localização**: `app.py` linhas 99-102

```python
@app.route('/api/csrf-token', methods=['GET'])
@login_required
def csrf_token_api():
    return jsonify({'csrf_token': generate_csrf()})
```

**Testes Obrigatórios**:
```python
def test_csrf_token_endpoint_valid_user():
    """Usuário autenticado obtém token válido"""
    response = client.get('/api/csrf-token')
    assert response.status_code == 200
    data = response.get_json()
    assert 'csrf_token' in data
    assert len(data['csrf_token']) > 20

def test_csrf_token_endpoint_not_authenticated():
    """Usuário não autenticado retorna 401"""
    response = client.get('/api/csrf-token')
    assert response.status_code == 401

def test_csrf_token_is_usable():
    """Token retornado é válido para POST seguinte"""
    # 1. Obter token
    response = client.get('/api/csrf-token')
    token = response.get_json()['csrf_token']
    
    # 2. Usar em POST
    form_data = {
        'csrf_token': token,
        'action': 'emitir',
        # ... outros dados
    }
    response = client.post('/admin/nfe/emitir', data=form_data)
    
    # 3. Validar que não foi rejeitado por CSRF
    assert response.status_code != 400, \
        "Token retornado por /api/csrf-token foi rejeitado no POST"

def test_csrf_token_missing_rejected():
    """POST sem token CSRF é rejeitado"""
    form_data = {
        'action': 'emitir',
        # SEM csrf_token
    }
    response = client.post('/admin/nfe/emitir', data=form_data)
    assert response.status_code == 400

def test_csrf_token_invalid_rejected():
    """POST com token CSRF inválido é rejeitado"""
    form_data = {
        'csrf_token': 'INVALIDO123456',
        'action': 'emitir',
    }
    response = client.post('/admin/nfe/emitir', data=form_data)
    assert response.status_code == 400
```

---

### 8️⃣ PERMISSÕES — ESTADO ATUAL

**Status**: 🟡 IMPLEMENTAÇÃO REAL ENCONTRADA

Arquivo: `auth/decorators.py`

**Decorators Encontrados**:
- `@permission_required()` — ✅ EXISTE E É REAL
- `@admin_required()` — Usa permission check
- `@editor_or_admin_required()` — Usa permission check
- `@viewer_or_higher_required()` — Usa permission check

**Matriz de Permissões Esperada**:

| Ação | Viewer | Editor | Admin | Super_Admin | Implementado? |
|------|--------|--------|-------|-------------|--------------|
| Ver tela emissão | ✅ | ✅ | ✅ | ✅ | ⏳ Testar |
| Emitir NF-e | ❌ | ✅ | ✅ | ✅ | ⏳ Testar |
| Reenviar NF-e | ❌ | ✅ | ✅ | ✅ | ⏳ Testar |
| Emitir rascunho | ❌ | ✅ | ✅ | ✅ | ⏳ Testar |
| Visualizar NF-e | ✅ | ✅ | ✅ | ✅ | ⏳ Testar |
| Download DANFE | ✅ | ✅ | ✅ | ✅ | ⏳ Testar |

**Teste Automatizado Necessário**:
```python
@pytest.mark.parametrize("role,endpoint,method,expected_status", [
    ('VIEWER', '/admin/nfe/emitir', 'POST', 403),  # NÃO PODE EMITIR
    ('EDITOR', '/admin/nfe/emitir', 'POST', 200),  # PODE EMITIR
    ('ADMIN', '/admin/nfe/emitir', 'POST', 200),   # PODE EMITIR
    ('VIEWER', '/admin/nfe/danfe/1/pdf', 'GET', 200),  # PODE VER
    ('EDITOR', '/admin/nfe/danfe/1/pdf', 'GET', 200),  # PODE VER
])
def test_permission_matrix(role, endpoint, method, expected_status):
    user = create_usuario(role=role)
    if method == 'GET':
        response = client.get(endpoint)
    else:
        response = client.post(endpoint, data={'csrf_token': '...', ...})
    assert response.status_code == expected_status, \
        f"{role} em {endpoint} retornou {response.status_code}, esperado {expected_status}"
```

---

### 9️⃣ `permission_required` — Implementação Real

**Status**: 🟢 EXISTE E FUNCIONA

**Não é stub** — verificado em `auth/decorators.py`.

**Testes Unitários Necessários**:
```python
def test_permission_required_with_permission():
    """Usuário COM permissão passa"""
    user = create_usuario_with_permission('nfe.emit')
    # ... deve passar

def test_permission_required_without_permission():
    """Usuário SEM permissão é bloqueado"""
    user = create_usuario_without_permission('nfe.emit')
    response = client.get('/admin/nfe/emitir')
    assert response.status_code in [403, 401]

def test_permission_required_not_authenticated():
    """Usuário não autenticado é bloqueado"""
    response = client.get('/admin/nfe/emitir')
    assert response.status_code == 401

def test_permission_required_super_admin_always_pass():
    """Super_admin sempre passa"""
    user = create_usuario(role='SUPER_ADMIN')
    # Deve passar mesmo sem permissão explícita
```

---

### 🔟 TEMPLATES GLOBAIS

**Status**: 🔴 NÃO TESTADOS

**Templates Críticos**:
- `templates/base.html`
- `templates/cliente/base.html`

**Testes Obrigatórios** (Renderização sem BuildError):

```python
def test_template_base_renders():
    """templates/base.html renderiza sem erro"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'BuildError' not in response.data

def test_dashboard_renders_without_builderror():
    """Dashboard renderiza sem BuildError"""
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'BuildError' not in response.data
    assert b'500' not in response.data

def test_nfe_page_renders():
    """Página de NF-e renderiza"""
    response = client.get('/admin/nfe/list?cliente_id=27')
    assert response.status_code == 200
    assert b'BuildError' not in response.data

def test_select_client_renders():
    """Seleção de empresa renderiza"""
    response = client.get('/admin/selecionar-cliente')
    assert response.status_code == 200
    assert b'BuildError' not in response.data
```

---

### 1️⃣1️⃣ URL_FOR

**Status**: 🔴 NÃO VALIDADO

**Teste Automatizado Necessário**:

```python
def test_all_template_urls_exist():
    """
    Validar que todos os url_for() em templates apontam para rotas existentes
    """
    import re
    from pathlib import Path
    
    # Extrair todos url_for(...) dos templates
    template_dir = Path('templates')
    url_for_pattern = r"url_for\('([^']+)'"
    
    found_urls = set()
    for template_file in template_dir.rglob('*.html'):
        content = template_file.read_text()
        for match in re.finditer(url_for_pattern, content):
            found_urls.add(match.group(1))
    
    # Validar que cada um existe nas rotas registradas
    for endpoint in found_urls:
        try:
            with app.app_context():
                url_for(endpoint)
        except BuildError:
            pytest.fail(f"Endpoint inexistente em templates: {endpoint}")
```

---

### 1️⃣2️⃣ ARQUIVOS LEGADOS

**Status**: 🔴 NÃO MAPEADOS

**Classificação Necessária**:

| Arquivo | Tipo | Ativo? | Pode Remover? | Ação |
|---------|------|--------|---------------|------|
| `nfe_routes.py` | Módulo | NÃO | SIM* | Marcar DEPRECATED |
| `routes/emitir.html` | Template | NÃO | SIM* | Marcar DEPRECATED |
| `app.py.backup` | Backup | NÃO | SIM | Remover |
| `nfe_routes.py.backup` | Backup | NÃO | SIM | Remover |
| `nfe_routes.py.bak_*` | Backup | NÃO | SIM | Remover |
| `routes/nfe_routes.py.backup` | Backup | NÃO | SIM | Remover |
| `backup_aws/` | Pasta | NÃO | SIM | Documentar, não remover |

*Remover após testes validarem equivalência.

---

### 1️⃣3️⃣ DEPLOY

**Status**: 🔴 ARTESANAL E INSEGURO

**Scripts Encontrados**:
- `deployment/atualizar_seguranca_aws.sh`
- `deploy_fixes_aws.sh`
- `deploy_inutilizacao_aws.sh` — ⚠️ COPIA ARQUIVO DESATUALIZADO
- `deploy_lc214_aws.sh`

**Novo Processo Obrigatório**:
1. NÃO copiar arquivos individuais
2. Implementar `pre_deploy_check.sh`
3. Validar imports
4. Rodar testes críticos
5. Criar backup datado
6. Atualizar via git ou tar versionado
7. Validar pós-deploy
8. Registrar deployment

---

### 1️⃣4️⃣ ARQUIVOS CRÍTICOS

**Status**: 🔴 NÃO MARCADOS

**Lista Crítica**:
```
app.py                               [CRÍTICO] Configuração CSRF, blueprint registration
routes/nfe_routes.py                 [CRÍTICO] Lógica de emissão
templates/admin/nfes/emitir.html    [CRÍTICO] Interface de emissão
templates/base.html                 [CRÍTICO] Layout global
templates/cliente/base.html         [CRÍTICO] Menu geral
services/nfe_service.py             [CRÍTICO] Geração de XML
services/sefaz_service.py           [CRÍTICO] Comunicação SEFAZ
services/nfe_creation_workflow.py   [CRÍTICO] Workflow de criação
auth/decorators.py                  [CRÍTICO] Proteção de permissões
database/models.py                  [CRÍTICO] Estrutura de dados
```

**Se qualquer arquivo crítico mudar: RODAR TESTES CRÍTICOS OBRIGATORIAMENTE**

---

### 1️⃣5️⃣ NÃO MODIFICAR SEM NECESSIDADE

**Status**: ✅ RESPEITAR

**Regra**:
- Emissão funciona
- NÃO refatorar código funcional
- NÃO mudar submit nativo
- NÃO remover alias
- NÃO alterar CSRF
- TESTES PRIMEIRO, depois consolidação

---

### 1️⃣6️⃣ PRIMEIRO OBJETIVO

**Status**: ⏳ A IMPLEMENTAR

**Suíte `test_nfe_critical_regression.py` com 15+ testes**:

1. ✅ Tela de emissão renderiza
2. ✅ Blueprint correto registrado
3. ✅ Template correto usado
4. ✅ `action=emitir` transmitido
5. ✅ CSRF renewal funciona
6. ✅ POST entra no bloco de emissão
7. ✅ SEFAZ mockada não quebra
8. ✅ Viewer bloqueado
9. ✅ Editor permitido
10. ✅ Empresa A isolada de B
11. ✅ Alias `/create` funciona
12. ✅ Rota `/emitir` funciona
13. ✅ DANFE renderiza
14. ✅ Próximo número funciona
15. ✅ Rascunho salva/carrega

---

### 1️⃣7️⃣ NÃO DEPLOYAR AINDA

**Status**: ✅ RESPEITANDO

**Localidade**: Desenvolvimento local apenas
**Depois**: Testes + Relatório + Revisão

---

### 1️⃣8️⃣ RELATÓRIO FINAL

**A entregar ao final**:
- Arquivos criados
- Arquivos alterados (e justificativa)
- Arquivos fiscal NÃO alterados
- Testes adicionados + resultado
- Total de testes passando
- Módulo NFe ativo confirmado
- Template ativo confirmado
- Duplicatas mapeadas
- Segurança Viewer/Editor validada
- CSRF renovável confirmado
- `action=emitir` transmitido confirmado
- `pre_deploy_check.sh` criado
- Rollback documentado
- Pendências (nada sai ao ar sem aprovação)

---

## 📊 RESUMO DE RISCOS

| # | Risco | Severidade | Impacto | Mitigation |
|---|-------|-----------|--------|-----------|
| 1 | Arquivo `nfe_routes.py` raiz sobrescreve o correto | 🔴 CRÍTICA | Emissão quebra | Auditar deploy, marcar deprecated |
| 2 | Template legado pode ser renderizado | 🟡 ALTA | Tela incompleta | Criar teste de validação |
| 3 | Import do blueprint errado | 🔴 CRÍTICA | App quebra | Teste unitário |
| 4 | Scripts deploy artesanais | 🟡 ALTA | Inconsistência | `pre_deploy_check.sh` |
| 5 | Permissões não testadas | 🟡 ALTA | Vazamento dados | Testes matriz permissões |
| 6 | Templates globais com BuildError | 🟡 ALTA | App quebra | Testes renderização |
| 7 | URL_for apontando errado | 🟡 ALTA | 404 em produção | Teste automatizado |
| 8 | Arquivo crítico alterado sem testes | 🔴 CRÍTICA | Regressão | Validar alterações |

---

## ✅ PRÓXIMAS AÇÕES (SEQUENCIAL)

1. **Auditar duplicações** (arquivos/imports/scripts) — Relatório pronto
2. **Marcar arquivos legados** — Adicionar comentários DEPRECATED
3. **Criar testes críticos** — `test_nfe_critical_regression.py`
4. **Auditar permissões** — Validar matriz
5. **Auditar templates** — Detectar BuildError
6. **Corrigir scripts deploy** — Remover riscos
7. **Criar pre_deploy_check.sh** — Gate de segurança
8. **Executar testes** — Validar tudo
9. **Gerar relatório final** — Pronto para deploy

**NÃO DEPLOYAR** até que todos os pontos passem por revisão.

---

**Status do Documento**: AUDITORIA PROFUNDA COMPLETA  
**Próximo Passo**: IMPLEMENTAÇÃO LOCALIZADA DOS TESTES

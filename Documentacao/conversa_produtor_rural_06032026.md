# Conversa: Suporte a Produtor Rural na NF-e — 06/03/2026

## Resumo da sessão

Continuação de sessão anterior. Nesta sessão foram corrigidos bugs pós-deploy e melhorado o layout do dashboard.

---

## Problemas corrigidos

### 1. Dashboard dando erro 500 (redirect para home)
**Causa:** `cliente.cnpj` era `NULL` para produtor rural; template `dashboard.html` fazia `{{ cliente.cnpj[:2] }}` diretamente → `TypeError: 'NoneType' object is not subscriptable` dentro do Jinja2 → caia no `except` e redirecionava.

**Fix:**
1. `database/models.py` não declarava `cpf` e `produtor_rural` → `cliente.cpf` ficava inacessível no template. Adicionado via `sed -i '408 a\...'` no servidor.
2. `templates/cliente/dashboard.html` — substituído `{{ cliente.cnpj[:2] }}...` por bloco condicional `{% if cliente.produtor_rural and cliente.cpf %}...{% elif cliente.cnpj %}...{% endif %}`.

### 2. "Erro ao carregar dados do cliente" no resumo
**Causa:** Mesmo problema — `templates/cliente/resumo.html` linha 36 tinha `{{ cliente.cnpj[:2] }}` sem verificar None.

**Fix:** Mesmo bloco condicional CPF/CNPJ aplicado via `sed` no servidor.

### 3. Layout do dashboard ruim / botões encavalados
**Causa:** Código usava `d-flex flex-wrap gap-3` sem colunas definidas para os cards de estatísticas, e `col-lg-2` puro (Bootstrap 4 style) para os botões de ações.

**Fix:** Reescrita completa de `dashboard.html` com:
- Cards de stats: `col-6 col-sm-4 col-md-3 col-xl-2`
- Botões de Ações Rápidas: `d-flex flex-wrap justify-content-center gap-3` com `min-width:130px; min-height:80px;`
- Tabela: `text-nowrap` nas colunas de data/valor
- Header: `d-flex flex-column flex-sm-row` responsivo

---

## Arquivos modificados no servidor (e sincronizados para local)

| Arquivo | Mudança |
|---|---|
| `database/models.py` | +cpf, +produtor_rural ao modelo ORM do Cliente |
| `templates/cliente/dashboard.html` | Reescrito completo — layout responsivo Bootstrap 5 |
| `templates/cliente/resumo.html` | Fix cnpj subscript → bloco condicional CPF/CNPJ |
| `routes/admin_routes.py` | (sessão anterior) lógica XOR cnpj/cpf |
| `routes/nfe_routes.py` | (sessão anterior) bypass validação CNPJ produtor rural |
| `services/nfe_service.py` | (sessão anterior) CPF no XML e chave de acesso |
| `templates/admin/clientes/form.html` | (sessão anterior) toggle switch + máscara CPF |

## Commit
- Hash: `d4d98d7`
- Mensagem: `feat: suporte a produtor rural (CPF) na emissão de NF-e`
- Branch: `main`
- Repo: `https://github.com/sjtecnologia/api_nfe`

## Próximos passos pendentes
- Teste real da emissão de NF-e para produtor rural (previsto para 07/03/2026)
- Possíveis rejeições SEFAZ a monitorar: 228 (CSOSN), 559 (CPF inválido), 296 (IE obrigatória), 325 (regime tributário)

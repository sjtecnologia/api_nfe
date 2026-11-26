# Implementação — Orçamentos, Portal do Cliente e Notificações

**Branch:** `lc214-migration`
**Status:** implementação de código concluída; migração pendente de execução no banco
**Última atualização:** 06/11/2026

---

## Visão geral

Módulo que conecta a empresa assinante aos seus clientes finais:

1. A empresa cria **orçamentos internos** ou recebe **solicitações de orçamento** pelo portal.
2. O cliente final acessa um **portal próprio**, monta o pedido e acompanha o status.
3. A empresa revisa valores, responde e **converte o orçamento em pedido de venda**.
4. Empresa e cliente recebem **notificações** no sistema e por e-mail.

O pedido gerado usa a mesma tabela `pedidos_vendas` do catálogo público, portanto
aparece em **Catálogos e Pedidos**.

---

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `database/migrations/019_create_orcamentos_portal.sql` | Tabelas `portal_usuarios`, `orcamentos`, `orcamentos_itens`, `notificacoes`; vínculo `pedidos_vendas.orcamento_id` |
| `routes/orcamentos_routes.py` | Blueprints `orcamentos` (`/admin/orcamentos`) e `portal` (`/portal`) |
| `services/orcamentos_service.py` | Criação de notificações e envio de e-mail em background |
| `auth/decorators.py` | `portal_cliente_required()` — restringe rotas ao cliente final |
| `database/models.py`, `models/user.py` | `is_portal_cliente()`, `role_name` |
| `routes/auth_routes.py`, `routes/home_routes.py` | Redirecionamento do cliente final para o portal |
| `templates/admin/orcamentos/` | Lista, formulário, detalhe, notificações e usuários do portal |
| `templates/portal/` | Dashboard, novo pedido, detalhe e notificações do cliente final |
| `templates/base.html` | Menu Orçamentos e sino de notificações |
| `tests/test_orcamentos_portal.py` | 23 testes automatizados do módulo |

---

## Fluxo de status

```
RASCUNHO ─┐
          ├─ ENVIADO ── APROVADO ── CONVERTIDO
SOLICITADO┘        └──── RECUSADO
                          CANCELADO
```

- **CONVERTIDO** só é alcançado pela ação `converter_em_pedido`, que cria o
  pedido de venda. A troca simples de status não permite essa transição.
- Orçamento convertido não volta de status.
- Orçamento cancelado não é convertido em pedido.
- Ao marcar como **ENVIADO**, o usuário do portal vinculado é notificado por
  e-mail e no sistema.

---

## Segurança e escopo

- Todas as consultas são escopadas por `cliente_id` da empresa ativa
  (`session.current_client_id`).
- Rotas administrativas exigem `admin_required()`; portal exige
  `portal_cliente_required()`.
- O portal só enxerga orçamentos do próprio `portal_usuario_id`.
- Notificações internas da empresa (`user_id IS NULL`) **não** são exibidas no
  portal (`incluir_empresa=False`).
- Senha do usuário do portal: mínimo 8 caracteres, maiúscula, minúscula, número
  e confirmação validada também no servidor.
- Formulários usam CSRF do Flask-WTF.

---

## Como aplicar

### 1. Migração (obrigatória antes de habilitar)

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/019_create_orcamentos_portal.sql
```

A migração é idempotente (`IF NOT EXISTS`) e deve rodar **depois** da
`015_create_catalogo_vendas.sql`, pois altera `pedidos_vendas`.

### 2. Variável de ambiente

Para os links nos e-mails funcionarem fora de requisição:

```bash
APP_BASE_URL=https://api.emitemax.com.br
```

### 3. Criar o primeiro usuário do portal

Na área administrativa: **Gestão → Orçamentos → Usuários do portal → Novo usuário**.
O usuário recebe o papel `Cliente` e passa a ser redirecionado para `/portal`
no login.

---

## Testes

```bash
python3 -m pytest tests/test_orcamentos_portal.py -q
# 23 passed
```

Cobrem:

- conversão de valores e datas (formatos BR e ISO);
- leitura dos itens do formulário;
- cálculo/arredondamento e validação de quantidade, valor e produto da empresa;
- regras de transição de status e conversão;
- isolamento das notificações do portal;
- registro das rotas, coerência `url_for` × endpoints e conteúdo da migração.

Regressões relacionadas também verificadas:

```bash
python3 -m pytest tests/test_auth_routes.py tests/test_admin_user_scope.py \
  tests/test_nfe_critical_regression.py -q
# 24 passed
```

---

## Pendências de deploy

- [ ] Executar a migração `019` no banco de destino.
- [ ] Configurar `APP_BASE_URL`.
- [ ] Criar o papel `Cliente` (a migração cria automaticamente).
- [ ] Revisar permissões/menus para o papel `Admin` (o menu Orçamentos já é
      exibido para Super_Admin e Admin).
- [ ] Teste assistido: criar usuário do portal → pedido → resposta da empresa →
      aprovação → conversão em pedido.

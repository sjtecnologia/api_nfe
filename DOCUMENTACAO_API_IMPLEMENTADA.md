# 📚 Sistema de Documentação da API

## ✅ Implementado

Sistema de documentação integrado na área administrativa de API Keys do sistema.

---

## 🎯 O que foi feito

### 1. Rotas Criadas

**Arquivo:** `routes/api_keys_routes.py`

- **`/admin/api-keys/docs`** - Lista todas as documentações disponíveis
- **`/admin/api-keys/docs/<doc_name>`** - Exibe uma documentação específica em HTML

### 2. Templates Criados

**Pasta:** `templates/admin/api_keys/`

- **`docs_index.html`** - Página índice com todas as documentações
- **`docs_viewer.html`** - Visualizador de documentação com syntax highlighting

### 3. Documentações Disponíveis

**Pasta:** `docs/`

- **`API_TRIBUTACAO_AUTOMATICA.md`** - Guia da nova funcionalidade (⭐ NOVO)
- **`TRIBUTACAO_AUTOMATICA_COMPLETO.md`** - Documentação técnica completa
- **`API_INTEGRACAO_MANUAL.md`** - Manual geral de integração

### 4. Melhorias no Template

**Arquivo:** `templates/admin/api_keys/list.html`

- Adicionados links diretos para cada documentação
- Destaque visual para a documentação nova (Tributação Automática)
- Link para visualizar todas as documentações

---

## 🚀 Como Acessar

### Via Interface Web

1. Faça login no sistema
2. Vá em **Admin → API Keys → [Selecione um Cliente]**
3. Na seção **"Como Usar as API Keys"**, clique em:
   - **Tributação Automática (NOVO)** ⭐
   - **Documentação Técnica Completa**
   - **Manual Completo da API**
   - **Ver Todas as Documentações**

### URLs Diretas

```
https://seu-dominio.com/admin/api-keys/docs
https://seu-dominio.com/admin/api-keys/docs/tributacao-automatica
https://seu-dominio.com/admin/api-keys/docs/tributacao-completo
https://seu-dominio.com/admin/api-keys/docs/integracao
```

---

## 🎨 Recursos do Visualizador

### ✨ Funcionalidades

- ✅ **Syntax Highlighting** - Código colorido com Highlight.js
- ✅ **Navegação Lateral** - Sidebar com links para outras documentações
- ✅ **Responsivo** - Layout adaptável mobile/desktop
- ✅ **Impressão** - Botão para imprimir/salvar PDF
- ✅ **Markdown Completo** - Tabelas, listas, código, blockquotes
- ✅ **Scroll Suave** - Navegação suave entre seções
- ✅ **Design Moderno** - Interface limpa e profissional

### 🎨 Suporte Markdown

- Títulos (H1 a H6)
- Listas (ordenadas e não ordenadas)
- Tabelas
- Blocos de código com syntax highlighting
- Links e imagens
- Citações (blockquotes)
- Texto formatado (negrito, itálico, código inline)
- Linhas horizontais

---

## 📝 Como Adicionar Nova Documentação

### 1. Criar arquivo .md

Crie um arquivo Markdown na pasta `docs/`:

```bash
docs/
├── API_TRIBUTACAO_AUTOMATICA.md
├── TRIBUTACAO_AUTOMATICA_COMPLETO.md
├── API_INTEGRACAO_MANUAL.md
└── NOVA_DOCUMENTACAO.md  ← NOVO
```

### 2. Registrar na rota

Edite `routes/api_keys_routes.py`:

```python
docs_disponiveis = {
    # ... documentações existentes ...
    'nova-doc': {
        'arquivo': 'NOVA_DOCUMENTACAO.md',
        'titulo': 'Título da Nova Documentação',
        'descricao': 'Descrição curta do que é a documentação'
    }
}
```

### 3. Acessar

A nova documentação estará disponível em:

```
https://seu-dominio.com/admin/api-keys/docs/nova-doc
```

---

## 🔧 Dependências

### Requisitos

Adicionado ao `requirements.txt`:

```
markdown>=3.5.0
```

### Instalação

```bash
pip install markdown
```

---

## 📂 Estrutura de Arquivos

```
api_nfe/
├── routes/
│   └── api_keys_routes.py          # Rotas de documentação
├── templates/
│   └── admin/
│       └── api_keys/
│           ├── list.html           # Lista API Keys (com links docs)
│           ├── docs_index.html     # Índice de documentações
│           └── docs_viewer.html    # Visualizador de docs
├── docs/
│   ├── API_TRIBUTACAO_AUTOMATICA.md
│   ├── TRIBUTACAO_AUTOMATICA_COMPLETO.md
│   └── API_INTEGRACAO_MANUAL.md
└── requirements.txt                # Dependências (markdown adicionado)
```

---

## 🎯 Benefícios

### Para os Desenvolvedores

✅ **Centralizado** - Toda documentação em um só lugar  
✅ **Atualizado** - Sempre sincronizado com o sistema  
✅ **Versionado** - Documentação no Git junto com o código  
✅ **Acessível** - Sem necessidade de arquivos externos  

### Para os Clientes

✅ **Fácil de Encontrar** - Dentro da área de API Keys  
✅ **Bonito** - Interface profissional e moderna  
✅ **Prático** - Pode imprimir ou salvar em PDF  
✅ **Completo** - Códigos de exemplo com syntax highlighting  

---

## 🔐 Segurança

- ✅ Requer login para acessar
- ✅ Usa decorator `@login_required`
- ✅ Documentação não expõe dados sensíveis
- ✅ Arquivos .md lidos com encoding UTF-8 seguro

---

## 📊 Estatísticas

- **3 documentações** disponíveis inicialmente
- **2 templates** personalizados
- **2 rotas** novas
- **1 dependência** adicionada (markdown)
- **100% responsivo** (mobile + desktop)

---

## 🎉 Status

**🟢 SISTEMA 100% FUNCIONAL!**

Documentação da API agora está acessível dentro da área administrativa com visualizador moderno e profissional! 🚀

---

## 📞 Suporte

Para dúvidas sobre a documentação ou sistema de visualização:

- 📧 Email: suporte@emitemax.com.br
- 📚 Documentação: `/admin/api-keys/docs`

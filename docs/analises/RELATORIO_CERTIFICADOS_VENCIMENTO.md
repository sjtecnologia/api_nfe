# Relatório de Certificados Digitais - Vencimento

## 📋 Resumo

Sistema completo de monitoramento e alertas para certificados digitais, organizado por cliente, com indicadores de criticidade e vencimento.

## 🎯 Objetivo

Prevenir interrupções na emissão de NF-e causadas por certificados digitais vencidos, fornecendo visibilidade clara sobre quais certificados precisam de atenção imediata.

## 🔗 Acesso

### Opção 1: Via Dashboard
1. Acesse Dashboard (`/admin/dashboard`)
2. No card "**Certificado (dias)**" clique em "**Ver Relatório**"

### Opção 2: Via Menu
1. Menu "**Sistema**"
2. Clique em "**Certificados Digitais**"

### URL Direta
`/admin/certificados/vencimento`

## 🔐 Permissões

- **Acesso**: Administradores e Super Administradores
- **Proteção**: Login obrigatório via `@login_required`

## 📊 Funcionalidades

### 1. Estatísticas Gerais

**6 Indicadores na parte superior**:

| Indicador | Descrição | Cor |
|-----------|-----------|-----|
| **Total** | Total de certificados no período | Azul |
| **Vencidos** | Certificados já expirados | Vermelho |
| **Críticos** | Vencem em ≤ 15 dias | Vermelho |
| **Urgentes** | Vencem em 16-30 dias | Amarelo |
| **Atenção** | Vencem em 31-60 dias | Azul Claro |
| **OK** | Vencem em > 60 dias | Verde |

### 2. Filtros Disponíveis

#### Alertar com antecedência de:
- 15 dias
- 30 dias
- **60 dias** (padrão)
- 90 dias
- 120 dias

#### Exibição:
- **Apenas próximos ao vencimento** (padrão): Mostra apenas certificados que vencem dentro do período selecionado
- **Todos os certificados ativos**: Exibe todos os certificados ativos, independente da data de vencimento

### 3. Classificação de Status

| Status | Descrição | Dias Restantes | Cor | Ícone |
|--------|-----------|----------------|-----|-------|
| **VENCIDO** | Certificado expirado | < 0 | Vermelho | ❌ |
| **CRÍTICO** | Vence muito em breve | 0-15 dias | Vermelho | ⚠️ |
| **URGENTE** | Ação necessária em breve | 16-30 dias | Amarelo | ⚠️ |
| **ATENÇÃO** | Planejar renovação | 31-60 dias | Azul | 🕐 |
| **OK** | Situação normal | > 60 dias | Verde | ✅ |

### 4. Alertas Automáticos

#### Alerta Crítico (Vermelho)
```
⚠️ Atenção! Existem X certificado(s) vencido(s). 
Os clientes afetados não conseguem emitir NF-e!
```
**Condição**: Quando há certificados com `validade_fim < hoje`

#### Alerta Urgente (Amarelo)
```
🕐 Urgente! X certificado(s) vencem em até 15 dias. 
Providencie renovação imediata!
```
**Condição**: Quando há certificados com `dias_restantes ≤ 15`

### 5. Visualização por Cliente

**Cada card de cliente exibe**:
- **Cabeçalho**:
  - Razão Social
  - CNPJ
  - Quantidade de certificados
  - Badge com status do certificado mais urgente
  
- **Tabela de Certificados**:
  - Status ativo/inativo
  - Nome do arquivo
  - Fingerprint (primeiros 16 caracteres)
  - Data de validade inicial
  - Data de validade final (destaque)
  - Dias restantes (badge colorido)
  - Status de vencimento

### 6. Destaque Visual

**Linhas da tabela são coloridas automaticamente**:
- 🔴 **Vermelho claro**: Certificados vencidos ou críticos (≤15 dias)
- 🟡 **Amarelo claro**: Certificados urgentes (16-30 dias)
- ⚪ **Branco**: Certificados OK (>30 dias)

## 🔧 Implementação Técnica

### Backend (routes/admin_routes.py)

```python
@admin_bp.route('/certificados/vencimento')
@login_required
def relatorio_certificados_vencimento():
    # Parâmetros
    dias_alerta = request.args.get('dias_alerta', 60, type=int)
    mostrar_todos = request.args.get('mostrar_todos', 'false') == 'true'
    
    # Query com cálculo de dias restantes
    EXTRACT(DAY FROM (cd.validade_fim - CURRENT_DATE)) as dias_restantes
    
    # Classificação automática
    CASE 
        WHEN cd.validade_fim < CURRENT_DATE THEN 'VENCIDO'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '15 days' THEN 'CRÍTICO'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '30 days' THEN 'URGENTE'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '60 days' THEN 'ATENÇÃO'
        ELSE 'OK'
    END as status_vencimento
```

### Query SQL Principal

```sql
SELECT 
    c.cliente_id,
    c.razao_social,
    c.cnpj,
    cd.certificado_digital_id,
    cd.nome_arquivo_original,
    cd.fingerprint,
    cd.validade_inicio,
    cd.validade_fim,
    cd.ativo,
    EXTRACT(DAY FROM (cd.validade_fim - CURRENT_DATE)) as dias_restantes,
    CASE 
        WHEN cd.validade_fim < CURRENT_DATE THEN 'VENCIDO'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '15 days' THEN 'CRÍTICO'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '30 days' THEN 'URGENTE'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '60 days' THEN 'ATENÇÃO'
        ELSE 'OK'
    END as status_vencimento,
    CASE 
        WHEN cd.validade_fim < CURRENT_DATE THEN 'danger'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '15 days' THEN 'danger'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '30 days' THEN 'warning'
        WHEN cd.validade_fim <= CURRENT_DATE + INTERVAL '60 days' THEN 'info'
        ELSE 'success'
    END as cor_alerta
FROM clientes c
INNER JOIN certificados_digitais cd ON c.cliente_id = cd.cliente_id
WHERE c.ativo = TRUE
    AND cd.ativo = TRUE 
    AND cd.validade_fim > CURRENT_DATE
    AND cd.validade_fim <= CURRENT_DATE + INTERVAL '60 days'
ORDER BY 
    dias_restantes ASC NULLS LAST,
    c.razao_social,
    cd.validade_fim
```

### Estrutura de Dados

```python
# Agrupamento por cliente
clientes_dict = {
    'cliente_id': {
        'cliente_id': int,
        'razao_social': str,
        'cnpj': str,
        'certificados': [
            {
                'certificado_id': int,
                'nome_arquivo': str,
                'fingerprint': str,
                'validade_inicio': datetime,
                'validade_fim': datetime,
                'ativo': bool,
                'dias_restantes': int,
                'status_vencimento': str,
                'cor_alerta': str
            }
        ]
    }
}

# Estatísticas
estatisticas = {
    'total': int,              # Total de certificados
    'vencidos': int,           # Certificados vencidos
    'criticos': int,           # ≤ 15 dias
    'urgentes': int,           # 16-30 dias
    'atencao': int,            # 31-60 dias
    'ok': int,                 # > 60 dias
    'total_clientes': int      # Clientes com certificados
}
```

## 📱 Interface do Usuário

### Template (relatorio_vencimento.html)

**Recursos visuais**:
- Cards coloridos para estatísticas
- Badges com cores semânticas (Bootstrap)
- Tabelas responsivas com hover
- Ícones FontAwesome
- Impressão otimizada (oculta filtros, mantém dados)

**JavaScript**:
- Auto-atualização a cada 5 minutos
- Filtros dinâmicos via GET
- Submissão automática ao alterar seleções

## 🖨️ Funcionalidade de Impressão

**Otimizações para impressão**:
```css
@media print {
    .no-print { display: none !important; }  /* Oculta filtros e botões */
    .print-only { display: block !important; } /* Exibe rodapé */
    .card { page-break-inside: avoid; }        /* Evita quebra dentro do card */
}
```

**Botão "Imprimir"**: Gera versão limpa sem filtros, pronta para impressão/PDF

## 📈 Casos de Uso

### Cenário 1: Verificação Diária
```
1. Acesse o relatório (padrão: 60 dias)
2. Verifique alertas vermelhos/amarelos no topo
3. Se houver alertas, identifique os clientes afetados
4. Entre em contato para providenciar renovação
```

### Cenário 2: Auditoria Mensal
```
1. Acesse com filtro "90 dias"
2. Gere impressão/PDF
3. Envie para equipe de suporte
4. Acompanhe renovações planejadas
```

### Cenário 3: Cliente Específico
```
1. Acesse "Todos os certificados ativos"
2. Use Ctrl+F para buscar razão social
3. Analise histórico de certificados do cliente
4. Planeje renovação com antecedência
```

### Cenário 4: Situação Crítica
```
ALERTA: "Existem 3 certificado(s) vencido(s)"
1. Identifique clientes afetados (cards com badge vermelho)
2. Contate clientes IMEDIATAMENTE
3. Oriente sobre impossibilidade de emitir NF-e
4. Providencie renovação urgente
5. Após renovação, verifique se alerta sumiu
```

## ⚙️ Configuração

### Parâmetros de URL

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `dias_alerta` | int | 60 | Antecedência do alerta em dias |
| `mostrar_todos` | bool | false | Exibir todos os certificados ativos |

**Exemplos**:
```
/admin/certificados/vencimento                              # Padrão (60 dias)
/admin/certificados/vencimento?dias_alerta=30               # Próximos 30 dias
/admin/certificados/vencimento?mostrar_todos=true           # Todos ativos
/admin/certificados/vencimento?dias_alerta=90&mostrar_todos=false  # Customizado
```

## 🎨 Personalização Visual

### Cores dos Status (Bootstrap)

```python
cor_alerta = {
    'VENCIDO': 'danger',     # bg-danger (vermelho)
    'CRÍTICO': 'danger',     # bg-danger (vermelho)
    'URGENTE': 'warning',    # bg-warning (amarelo)
    'ATENÇÃO': 'info',       # bg-info (azul claro)
    'OK': 'success'          # bg-success (verde)
}
```

### Cards de Estatísticas

```css
.card.border-left-primary { border-left: 4px solid #4e73df; }  /* Azul */
.card.border-left-danger { border-left: 4px solid #e74a3b; }   /* Vermelho */
.card.border-left-warning { border-left: 4px solid #f6c23e; }  /* Amarelo */
.card.border-left-info { border-left: 4px solid #36b9cc; }     /* Azul claro */
.card.border-left-success { border-left: 4px solid #1cc88a; }  /* Verde */
```

## ⚠️ Observações Importantes

1. **Certificados Inativos**: Não aparecem no relatório (filtro: `ativo = TRUE`)

2. **Cálculo de Dias**: Usa `EXTRACT(DAY FROM ...)` do PostgreSQL para precisão

3. **Auto-Atualização**: Página recarrega automaticamente a cada 5 minutos

4. **Performance**: Query otimizada com INNER JOIN (apenas clientes com certificados)

5. **Ordenação**: Certificados mais urgentes primeiro (dias_restantes ASC)

6. **Sem Certificados**: Exibe mensagem informativa se nenhum encontrado

## 🧪 Testes

### Checklist de Validação

- [ ] Relatório exibe certificados corretamente
- [ ] Estatísticas calculam valores corretos
- [ ] Filtro "dias_alerta" funciona (15, 30, 60, 90, 120)
- [ ] Filtro "mostrar_todos" exibe todos os ativos
- [ ] Alertas aparecem quando há vencidos/críticos
- [ ] Badges coloridas correspondem aos status
- [ ] Linhas da tabela colorem conforme criticidade
- [ ] Botão "Imprimir" gera versão limpa
- [ ] Auto-atualização funciona após 5 minutos
- [ ] Link no dashboard "Ver Relatório" funciona
- [ ] Menu "Sistema > Certificados Digitais" funciona
- [ ] Acesso restrito a admins (sem login redireciona)

## 📊 Integração com Dashboard

**Card "Certificado (dias)"** no Dashboard:
- **KPI**: Mostra dias até certificado mais próximo de expirar
- **Botão**: "Ver Relatório" abre este relatório
- **Cálculo**: `MIN(EXTRACT(DAY FROM (validade_fim - CURRENT_DATE)))`

**Relação**:
- Dashboard: Visão resumida (1 número)
- Relatório: Visão detalhada (todos os certificados por cliente)

## 📝 Histórico

- **2025-11-18**: Implementação inicial do relatório de certificados
- **Solicitação**: Listar certificados mais próximos ao vencimento por cliente
- **Objetivo**: Prevenir interrupção de emissão de NF-e por certificados expirados
- **Arquivos**:
  - `/routes/admin_routes.py` - Rota `relatorio_certificados_vencimento()`
  - `/templates/admin/certificados/relatorio_vencimento.html` - Template completo
  - `/templates/admin/dashboard.html` - Botão "Ver Relatório" adicionado
  - `/templates/base.html` - Menu "Certificados Digitais" adicionado

## 🔮 Melhorias Futuras

1. **Notificações por E-mail**: Enviar alertas automáticos para admins
2. **Dashboard Widget**: Mini-relatório no dashboard
3. **Exportação**: Gerar Excel/PDF via backend
4. **Histórico**: Rastrear renovações de certificados
5. **API REST**: Endpoint JSON para integrações
6. **Webhooks**: Notificar sistemas externos sobre vencimentos
7. **Filtro por Cliente**: Buscar certificados de cliente específico

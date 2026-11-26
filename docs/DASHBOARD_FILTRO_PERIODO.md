# Dashboard com Filtro de Período

## 📋 Resumo

Implementação de filtro de período no Dashboard do Super Admin para análise de dados em intervalos específicos.

## 🎯 Funcionalidades

### 1. Seletor de Período

**Localização**: Dashboard Super Admin (`/admin/dashboard`)

**Opções Disponíveis**:
- ⏰ **Hoje**: Dados do dia atual
- 📅 **Esta Semana**: De segunda-feira até hoje
- 📆 **Este Mês**: Do dia 1 até hoje
- 🗓️ **Último Trimestre**: Últimos 90 dias
- 📊 **Este Ano**: De 01/janeiro até hoje
- ♾️ **Todo Período**: Todos os dados históricos (padrão)
- 📝 **Período Customizado**: Selecione data inicial e final

### 2. KPIs Filtrados

Os seguintes KPIs são **filtrados pelo período selecionado**:

1. **Total de NF-e**: Quantidade de notas emitidas no período
2. **Valor Total**: Soma dos valores das NF-e no período
3. **Taxa de Sucesso**: % de NF-e autorizadas no período
4. **Sugestões IA Aceitas**: Quantidade de sugestões aceitas no período
5. **NF-e do Período**: Total de notas (mesmo que item 1)

### 3. KPIs NÃO Filtrados

Os seguintes KPIs **sempre mostram dados atuais** (não são filtrados):

1. **Certificados (Dias)**: Mostra **quantos dias faltam até o certificado digital mais próximo expirar**
   - Busca em `certificados_digitais` onde `ativo = TRUE`
   - Calcula: `MIN(validade_fim - CURRENT_DATE)`
   - **Importância**: Alerta crítico para renovação de certificados necessários para emissão de NF-e
   - Exibe 0 se não houver certificados ativos

2. **Total de Clientes**: Clientes ativos no sistema (snapshot atual)
3. **Total de Produtos**: Produtos cadastrados e ativos (snapshot atual)

### 4. Gráficos Filtrados

Todos os gráficos são atualizados dinamicamente conforme o período:

1. **NF-e por Mês**: Linha temporal do período selecionado
2. **Status das NF-e**: Distribuição de status no período (Pizza)
3. **Top 5 Clientes**: Clientes mais ativos no período (Barras)
4. **Top 5 Produtos**: Produtos mais utilizados (não filtrado - cadastros ativos)

## 🔧 Implementação Técnica

### Backend (routes/admin_routes.py)

```python
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Processar parâmetros de período
    periodo = request.args.get('periodo', 'tudo')
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    
    # Calcular datas baseadas no período
    if periodo == 'hoje':
        data_inicio = hoje.replace(hour=0, minute=0, second=0)
        data_fim = hoje.replace(hour=23, minute=59, second=59)
    elif periodo == 'semana':
        data_inicio = hoje - timedelta(days=hoje.weekday())
        data_fim = hoje
    # ... outros períodos
    
    # Aplicar filtros nas queries
    where_clause = "WHERE data_criacao BETWEEN :data_inicio AND :data_fim"
```

### Frontend (templates/admin/dashboard.html)

```html
<!-- Dropdown com opções de período -->
<div class="dropdown">
    <button class="btn btn-outline-info dropdown-toggle">
        <i class="fas fa-calendar-alt"></i> Período
    </button>
    <ul class="dropdown-menu">
        <li><a href="?periodo=hoje">Hoje</a></li>
        <li><a href="?periodo=semana">Esta Semana</a></li>
        <!-- ... -->
        <li>
            <form method="GET">
                <input type="date" name="data_inicio">
                <input type="date" name="data_fim">
                <button type="submit">Filtrar</button>
            </form>
        </li>
    </ul>
</div>
```

### JavaScript (AJAX com parâmetros)

```javascript
async function loadDashboardData() {
    // Obter parâmetros da URL atual
    const urlParams = new URLSearchParams(window.location.search);
    const apiUrl = new URL('/admin/dashboard/api/data', window.location.origin);
    
    // Repassar parâmetros para API
    if (urlParams.has('periodo')) {
        apiUrl.searchParams.set('periodo', urlParams.get('periodo'));
    }
    
    const response = await fetch(apiUrl.toString());
    const data = await response.json();
    
    // Atualizar gráficos com dados filtrados
}
```

## 📊 Queries SQL com Filtro

### Exemplo: Total de NF-e

```sql
-- Sem filtro
SELECT COUNT(*) FROM nfe_emitidas

-- Com filtro
SELECT COUNT(*) FROM nfe_emitidas
WHERE data_criacao BETWEEN :data_inicio AND :data_fim
```

### Exemplo: Certificados (NÃO filtrado)

```sql
-- Sempre mostra o certificado mais próximo de expirar
SELECT MIN(EXTRACT(DAY FROM (validade_fim - CURRENT_DATE)))
FROM certificados_digitais
WHERE ativo = TRUE AND validade_fim > CURRENT_DATE
```

## 🎨 Interface do Usuário

### Indicador de Filtro Ativo

Quando um filtro está aplicado, aparece um alerta informativo:

```
ℹ️ Filtro ativo: Este Mês
[Limpar Filtro]
```

### Atalhos Rápidos

- Dropdown com opções pré-definidas (1 clique)
- Formulário inline para período customizado
- Botão "Limpar Filtro" volta para visão completa

## 🔒 Permissões

- **Acesso**: Apenas Super Administradores
- **Validação**: Proteção em todas as rotas
- **Segurança**: Parâmetros validados no backend

## 📈 Casos de Uso

### Cenário 1: Análise Mensal
```
1. Acesse Dashboard
2. Clique em "Período" → "Este Mês"
3. Visualize KPIs e gráficos do mês atual
```

### Cenário 2: Comparação Customizada
```
1. Acesse Dashboard
2. Clique em "Período" → Formulário customizado
3. Selecione: 01/01/2024 até 31/03/2024
4. Clique "Filtrar"
5. Analise o primeiro trimestre de 2024
```

### Cenário 3: Monitoramento de Certificados
```
1. Acesse Dashboard (qualquer período)
2. Observe o KPI "Certificado (dias)"
3. Se mostrar valor baixo (ex: 30 dias), providenciar renovação
4. Este KPI NUNCA é filtrado - sempre mostra o mais urgente
```

## ⚠️ Observações Importantes

1. **Certificados**: O KPI de certificados SEMPRE mostra o mais próximo de expirar, independente do filtro
2. **Performance**: Filtros reduzem o volume de dados, melhorando o tempo de resposta
3. **Padrão**: Sem filtro, mostra "Todo Período" (comportamento original)
4. **Persistência**: Filtros permanecem ao clicar em "Atualizar"
5. **Gráficos**: Atualizados via AJAX com os mesmos parâmetros de filtro

## 🧪 Testes

### Checklist de Validação

- [ ] Dropdown "Período" aparece no dashboard
- [ ] Opções pré-definidas (Hoje, Semana, Mês, etc.) funcionam
- [ ] Período customizado aceita datas e filtra corretamente
- [ ] Alerta de "Filtro ativo" aparece quando filtro aplicado
- [ ] Botão "Limpar Filtro" remove todos os filtros
- [ ] KPIs são recalculados conforme período
- [ ] Gráficos são atualizados via AJAX
- [ ] Certificados (dias) permanece inalterado
- [ ] Botão "Atualizar" mantém filtro ativo
- [ ] Funciona apenas para Super Admins

## 📝 Histórico

- **2025-11**: Implementação inicial do filtro de período
- **Solicitação**: Adicionar seletor de período no dashboard
- **Objetivo**: Análise temporal de dados do sistema

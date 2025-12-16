# Sistema de Planos e Assinaturas para NFe

## Visão Geral

Sistema completo para gerenciar modalidades de cobrança por emissão de NFe, suportando:
- **Cobrança Avulsa**: Pagamento por NFe emitida
- **Pacotes Mensais**: Planos com quantidade fixa de NFes por mês
- **Controle de Consumo**: Monitoramento automático de NFes emitidas
- **Gestão de Vencimentos**: Controle de períodos de cobrança

## Estrutura do Banco de Dados

### Tabela: `planos_nfe`
Define os planos/pacotes disponíveis para contratação.

**Campos principais:**
- `plano_id`: ID único do plano
- `nome`: Nome do plano (ex: "Pacote Básico")
- `tipo_plano`: 'AVULSO' ou 'PACOTE'
- `quantidade_nfes`: Limite de NFes (NULL = ilimitado)
- `valor_mensal`: Valor fixo mensal
- `valor_por_nfe`: Valor unitário (para avulso ou excedente)
- `ativo`: Se o plano está disponível para contratação

### Tabela: `assinaturas_cliente`
Vincula clientes aos planos contratados.

**Campos principais:**
- `assinatura_id`: ID único da assinatura
- `cliente_id`: Cliente vinculado
- `plano_id`: Plano contratado
- `status`: 'ATIVA', 'SUSPENSA', 'CANCELADA'
- `nfes_consumidas`: Contador de NFes no período atual
- `periodo_ref_inicio/fim`: Período de cobrança atual
- `dia_vencimento`: Dia do mês para renovação

## Planos Padrão Criados

A migração cria 6 planos pré-configurados:

| Plano | Tipo | NFes/mês | Valor Mensal | Valor/NFe |
|-------|------|----------|--------------|-----------|
| Avulso | AVULSO | - | R$ 0,00 | R$ 0,50 |
| Básico | PACOTE | 50 | R$ 20,00 | R$ 0,60 |
| Intermediário | PACOTE | 100 | R$ 35,00 | R$ 0,55 |
| Profissional | PACOTE | 250 | R$ 80,00 | R$ 0,50 |
| Empresarial | PACOTE | 500 | R$ 140,00 | R$ 0,45 |
| Ilimitado | PACOTE | Ilimitado | R$ 300,00 | R$ 0,00 |

## Funções do Banco de Dados

### 1. `pode_emitir_nfe(cliente_id)`
Verifica se o cliente pode emitir NFe.

```sql
SELECT * FROM pode_emitir_nfe(123);
```

**Retorna:**
- `pode_emitir`: true/false
- `mensagem`: Motivo ou status
- `nfes_disponiveis`: Quantidade disponível
- `plano_nome`: Nome do plano ativo

### 2. `registrar_emissao_nfe(cliente_id)`
Incrementa o contador de NFes consumidas.

```sql
SELECT registrar_emissao_nfe(123);
```

### 3. `renovar_periodo_assinatura(assinatura_id)`
Renova o período de cobrança (zera contador).

```sql
SELECT renovar_periodo_assinatura(456);
```

## Uso no Código Python

### Verificar se Cliente Pode Emitir

```python
from sqlalchemy import text

# Verificar permissão antes de emitir
result = db.execute(
    text("SELECT * FROM pode_emitir_nfe(:cliente_id)"),
    {"cliente_id": cliente_id}
).fetchone()

if not result[0]:  # pode_emitir = False
    flash(f'Não é possível emitir NFe: {result[1]}', 'warning')
    return redirect(url_for('nfe.list_nfes'))
```

### Registrar Emissão de NFe

```python
# Após emitir NFe com sucesso
db.execute(
    text("SELECT registrar_emissao_nfe(:cliente_id)"),
    {"cliente_id": cliente_id}
)
db.commit()
```

### Usando os Modelos SQLAlchemy

```python
from database.models import AssinaturaCliente, PlanoNFe

# Buscar assinatura ativa do cliente
assinatura = db.query(AssinaturaCliente).filter(
    AssinaturaCliente.cliente_id == cliente_id,
    AssinaturaCliente.status == 'ATIVA'
).first()

# Verificar se pode emitir
pode, mensagem = assinatura.pode_emitir()
if not pode:
    flash(f'Limite atingido: {mensagem}', 'warning')
    return

# Registrar emissão
assinatura.registrar_emissao()
db.commit()
```

## Fluxo de Implementação

### 1. Executar Migração

```bash
psql -U postgres -d sjtnfe -f database/migrations/006_create_planos_assinaturas.sql
```

### 2. Criar Assinatura para Cliente

```python
from database.models import AssinaturaCliente
from datetime import date, timedelta

# Criar assinatura
nova_assinatura = AssinaturaCliente(
    cliente_id=123,
    plano_id=2,  # Pacote Básico (50 NFes)
    data_inicio=date.today(),
    status='ATIVA',
    dia_vencimento=10,
    periodo_ref_inicio=date.today(),
    periodo_ref_fim=date.today() + timedelta(days=30)
)

db.add(nova_assinatura)
db.commit()
```

### 3. Integrar na Emissão de NFe

No arquivo `routes/nfe_routes.py`, adicionar antes de emitir:

```python
# Verificar se cliente pode emitir
from sqlalchemy import text

result = db.execute(
    text("SELECT * FROM pode_emitir_nfe(:cliente_id)"),
    {"cliente_id": cliente_id}
).fetchone()

if not result[0]:  # pode_emitir = False
    flash(result[1], 'warning')  # Mostrar mensagem de erro
    return redirect(url_for('nfe.emitir_nfe', cliente_id=cliente_id))

# ... código de emissão da NFe ...

# Após emissão bem-sucedida
db.execute(
    text("SELECT registrar_emissao_nfe(:cliente_id)"),
    {"cliente_id": cliente_id}
)
db.commit()
```

## Interface de Administração

### Próximos Passos

1. **Tela de Gerenciamento de Planos**
   - Listar planos existentes
   - Criar/editar/desativar planos
   - Ajustar valores e limites

2. **Tela de Assinaturas por Cliente**
   - Visualizar assinatura atual
   - Alterar plano
   - Histórico de consumo
   - Renovação manual

3. **Dashboard de Consumo**
   - Total de NFes emitidas por cliente
   - Uso vs. limite do pacote
   - Alertas de limite próximo
   - Previsão de faturamento

4. **Relatórios Financeiros**
   - Faturamento por plano
   - Clientes por tipo de plano
   - Taxa de conversão avulso → pacote
   - Exportação para cobrança

## Consultas Úteis

### Listar Todos os Planos Ativos

```sql
SELECT 
    plano_id,
    nome,
    tipo_plano,
    quantidade_nfes,
    valor_mensal,
    valor_por_nfe
FROM planos_nfe
WHERE ativo = true
ORDER BY ordem_exibicao;
```

### Assinaturas Ativas com Consumo

```sql
SELECT 
    a.assinatura_id,
    c.razao_social,
    p.nome as plano,
    a.nfes_consumidas,
    p.quantidade_nfes,
    CASE 
        WHEN p.quantidade_nfes IS NULL THEN 'Ilimitado'
        ELSE CONCAT(
            ROUND((a.nfes_consumidas::numeric / p.quantidade_nfes) * 100, 1),
            '%'
        )
    END as percentual_uso
FROM assinaturas_cliente a
JOIN clientes c ON a.cliente_id = c.cliente_id
JOIN planos_nfe p ON a.plano_id = p.plano_id
WHERE a.status = 'ATIVA'
ORDER BY percentual_uso DESC;
```

### Clientes Próximos do Limite

```sql
SELECT 
    c.razao_social,
    p.nome as plano,
    a.nfes_consumidas,
    p.quantidade_nfes,
    p.quantidade_nfes - a.nfes_consumidas as restantes
FROM assinaturas_cliente a
JOIN clientes c ON a.cliente_id = c.cliente_id
JOIN planos_nfe p ON a.plano_id = p.plano_id
WHERE a.status = 'ATIVA'
  AND p.tipo_plano = 'PACOTE'
  AND p.quantidade_nfes IS NOT NULL
  AND a.nfes_consumidas >= (p.quantidade_nfes * 0.8)  -- 80% ou mais
ORDER BY restantes ASC;
```

### Faturamento Mensal Estimado

```sql
SELECT 
    p.nome as plano,
    COUNT(*) as total_assinaturas,
    p.valor_mensal,
    COUNT(*) * p.valor_mensal as faturamento_estimado
FROM assinaturas_cliente a
JOIN planos_nfe p ON a.plano_id = p.plano_id
WHERE a.status = 'ATIVA'
  AND p.tipo_plano = 'PACOTE'
GROUP BY p.plano_id, p.nome, p.valor_mensal
ORDER BY faturamento_estimado DESC;
```

## Segurança e Boas Práticas

1. **Validar sempre antes de emitir**: Use a função `pode_emitir_nfe()` em toda emissão
2. **Registrar emissões**: Chame `registrar_emissao_nfe()` após cada emissão bem-sucedida
3. **Renovar períodos**: Configure job mensal para renovar assinaturas
4. **Auditar mudanças**: Registre alterações de planos e valores
5. **Alertas automáticos**: Notifique clientes próximos do limite

## Próximas Melhorias

- [ ] Sistema de upgrade/downgrade de planos
- [ ] Cobrança automática por excedente
- [ ] Integração com gateway de pagamento
- [ ] Notificações por e-mail de limites
- [ ] Histórico de consumo mensal
- [ ] API REST para consulta de saldo
- [ ] Relatórios de faturamento detalhados
- [ ] Descontos e promoções
- [ ] Planos personalizados por cliente

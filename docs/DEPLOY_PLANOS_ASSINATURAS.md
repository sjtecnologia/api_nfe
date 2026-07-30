# Deploy do Sistema de Planos e Assinaturas

## 📋 Checklist de Arquivos

### Novos Arquivos Criados:
- ✅ `database/migrations/006_create_planos_assinaturas.sql`
- ✅ `routes/planos_routes.py`
- ✅ `templates/admin/planos/list.html`
- ✅ `templates/admin/planos/form.html`
- ✅ `templates/admin/planos/assinaturas_list.html`
- ✅ `templates/admin/planos/assinatura_form.html`
- ✅ `templates/admin/planos/relatorio_consumo.html`
- ✅ `docs/SISTEMA_PLANOS_ASSINATURAS.md`

### Arquivos Modificados:
- ✅ `database/models.py` - Adicionadas classes `PlanoNFe` e `AssinaturaCliente`
- ✅ `app.py` - Registrado blueprint `planos_bp`

## 🚀 Passos para Deploy

### 1. Copiar Arquivos para o Servidor

Copie todos os arquivos listados acima para o servidor Windows.

### 2. Executar Migração do Banco de Dados

Conecte no servidor e execute:

```bash
psql -U postgres -d sjtnfe -f database/migrations/006_create_planos_assinaturas.sql
```

**O que a migração faz:**
- Cria tabela `planos_nfe` com 6 planos pré-configurados
- Cria tabela `assinaturas_cliente`
- Cria funções SQL: `pode_emitir_nfe()`, `registrar_emissao_nfe()`, `renovar_periodo_assinatura()`
- Cria índices para performance

### 3. Reiniciar Serviço

No Windows Server:
1. Abra "Serviços" (services.msc)
2. Localize o serviço da API NFe
3. Clique com botão direito → "Reiniciar"

### 4. Verificar Instalação

Acesse no navegador:
```
http://seu-servidor:porta/admin/planos
```

Você deve ver a tela com os 6 planos pré-configurados.

## 📊 Planos Criados Automaticamente

A migração cria os seguintes planos:

| Plano | Tipo | NFes/mês | Valor Mensal | Valor/NFe |
|-------|------|----------|--------------|-----------|
| Avulso | AVULSO | - | R$ 0,00 | R$ 0,50 |
| Básico | PACOTE | 50 | R$ 20,00 | R$ 0,60 |
| Intermediário | PACOTE | 100 | R$ 35,00 | R$ 0,55 |
| Profissional | PACOTE | 250 | R$ 80,00 | R$ 0,50 |
| Empresarial | PACOTE | 500 | R$ 140,00 | R$ 0,45 |
| Ilimitado | PACOTE | ∞ | R$ 300,00 | R$ 0,00 |

**Você pode ajustar esses valores pela interface após o deploy.**

## 🔧 Próximos Passos - Integração com Emissão de NFe

### Adicionar Verificação na Emissão

No arquivo `routes/nfe_routes.py`, adicione **ANTES** de gerar a NFe:

```python
# VERIFICAR LIMITE DO PLANO
from sqlalchemy import text

result = db.execute(
    text("SELECT * FROM pode_emitir_nfe(:cliente_id)"),
    {"cliente_id": cliente_id}
).fetchone()

if not result[0]:  # pode_emitir = False
    flash(f'❌ {result[1]}', 'warning')
    return redirect(url_for('nfe.emitir_nfe', cliente_id=cliente_id))

# Continuar com emissão...
```

### Registrar Emissão Após Sucesso

**APÓS** a NFe ser emitida com sucesso:

```python
# REGISTRAR EMISSÃO NO CONTADOR
db.execute(
    text("SELECT registrar_emissao_nfe(:cliente_id)"),
    {"cliente_id": cliente_id}
)
db.commit()
```

## 🎯 URLs Disponíveis

Após o deploy, estas URLs estarão disponíveis:

- `/admin/planos` - Lista de planos
- `/admin/planos/criar` - Criar novo plano
- `/admin/planos/<id>/editar` - Editar plano
- `/admin/planos/assinaturas` - Lista de assinaturas
- `/admin/planos/assinaturas/criar` - Criar assinatura
- `/admin/planos/assinaturas/<id>/editar` - Editar assinatura
- `/admin/planos/relatorio/consumo` - Relatório de consumo
- `/admin/planos/api/verificar-limite/<cliente_id>` - API para verificar limite

## 📝 Tarefas Administrativas

### Criar Assinatura para Cliente

1. Acesse `/admin/planos/assinaturas`
2. Clique em "Nova Assinatura"
3. Selecione o cliente
4. Escolha o plano
5. Defina data de início e vencimento
6. Salve

### Monitorar Consumo

1. Acesse `/admin/planos/relatorio/consumo`
2. Visualize clientes próximos do limite
3. Entre em contato para upgrade quando necessário

### Renovar Período Mansal

Quando chegar o dia de renovação mensal:

1. Acesse a assinatura
2. Clique em "Renovar Período"
3. Isso zera o contador de NFes consumidas

**Ou via SQL:**
```sql
SELECT renovar_periodo_assinatura(assinatura_id);
```

## 🔍 Consultas SQL Úteis

### Ver Consumo de Todos os Clientes

```sql
SELECT 
    c.razao_social,
    p.nome as plano,
    a.nfes_consumidas,
    p.quantidade_nfes,
    ROUND((a.nfes_consumidas::numeric / NULLIF(p.quantidade_nfes, 0)) * 100, 1) as percentual
FROM assinaturas_cliente a
JOIN clientes c ON a.cliente_id = c.cliente_id
JOIN planos_nfe p ON a.plano_id = p.plano_id
WHERE a.status = 'ATIVA'
ORDER BY percentual DESC;
```

### Clientes Próximos do Limite (>80%)

```sql
SELECT 
    c.razao_social,
    a.nfes_consumidas,
    p.quantidade_nfes,
    p.quantidade_nfes - a.nfes_consumidas as restantes
FROM assinaturas_cliente a
JOIN clientes c ON a.cliente_id = c.cliente_id
JOIN planos_nfe p ON a.plano_id = p.plano_id
WHERE a.status = 'ATIVA'
  AND p.quantidade_nfes IS NOT NULL
  AND a.nfes_consumidas >= (p.quantidade_nfes * 0.8)
ORDER BY restantes ASC;
```

### Verificar se Cliente Específico Pode Emitir

```sql
SELECT * FROM pode_emitir_nfe(123); -- Substitua 123 pelo cliente_id
```

## ⚠️ Avisos Importantes

1. **Backup**: Faça backup do banco antes de executar a migração
2. **Teste**: Teste em homologação antes de produção
3. **Clientes Existentes**: Crie assinaturas para clientes já existentes
4. **Integração**: Não esqueça de adicionar as verificações na emissão de NFe
5. **Renovação**: Configure um job mensal para renovar automaticamente os períodos

## 🆘 Troubleshooting

### Erro: "relation planos_nfe does not exist"
- A migração não foi executada. Execute o arquivo SQL no banco.

### Erro: "cannot import name planos_bp"
- O arquivo `routes/planos_routes.py` não foi copiado corretamente.

### Templates não aparecem
- Verifique se a pasta `templates/admin/planos/` existe e tem todos os arquivos.

### Planos não aparecem
- Execute: `SELECT * FROM planos_nfe;` para verificar se foram criados.

## 📞 Suporte

Para dúvidas sobre o sistema, consulte:
- `docs/SISTEMA_PLANOS_ASSINATURAS.md` - Documentação completa
- Arquivos de exemplo nas rotas e templates

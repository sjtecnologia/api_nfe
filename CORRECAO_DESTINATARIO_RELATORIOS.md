# CORREÇÃO: Destinatário não aparecendo nos Relatórios

## Problema Identificado

O usuário reportou que os destinatários não estavam aparecendo nos relatórios de notas emitidas.

## Diagnóstico Realizado

1. **Verificação da Base de Dados** ✅
   - Todas as notas têm o campo `destinatario_razao_social` preenchido
   - Exemplo: "Empresa Teste LTDA", "CLIENTE TESTE EMITEMAX", "Consumidor Final"

2. **Verificação do RelatorioService** ✅
   - O service está buscando corretamente: `COALESCE(NULLIF(destinatario_razao_social, ''), 'Não informado')`
   - O mapeamento Python está correto: `'destinatario': row.nome_destinatario`

3. **Verificação do Template HTML** ✅
   - O template exibe corretamente: `{{ nota.destinatario }}`

## Causa Raiz do Problema ❌

**Filtro de Período Padrão Incorreto**

O período padrão estava configurado como "mês atual" (fevereiro/2026), mas as notas na base de dados são de **dezembro/2025**.

### Código Antigo (Incorreto):
```python
# Período padrão (mês atual)
if not data_inicio_str or not data_fim_str:
    hoje = datetime.now()
    data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    data_fim = hoje
```

Este código mostrava **0 notas** porque buscava apenas fevereiro/2026, onde não existem dados.

## Solução Implementada ✅

Alterado o período padrão para **últimos 6 meses**, garantindo que dados históricos sejam exibidos:

### Código Novo (Correto):
```python
# Período padrão (últimos 6 meses para incluir dados históricos)
if not data_inicio_str or not data_fim_str:
    hoje = datetime.now()
    # Período padrão: últimos 6 meses até hoje
    data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if data_inicio.month <= 6:
        data_inicio = data_inicio.replace(year=data_inicio.year-1, month=12+data_inicio.month-6)
    else:
        data_inicio = data_inicio.replace(month=data_inicio.month-6)
    data_fim = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
```

## Arquivos Modificados

- **routes/relatorios_routes.py**
  - `notas_emitidas()` - linha 42-66
  - `produtos()` - linha 173-197
  - `impostos()` - linha 240-254

## Resultado dos Testes ✅

```
Período padrão: 01/08/2025 até 12/02/2026 (195 dias)
✅ Total de notas encontradas: 35
✅ Todas as 35 notas têm destinatário preenchido
✅ Exemplos:
   - Nota 25: 'Empresa Teste LTDA'
   - Nota 24: 'Empresa Teste LTDA'
   - NFCe 1: 'Consumidor Final'
```

## Impacto da Correção

### Antes:
- Usuário acessa relatórios → 0 notas encontradas
- Destinatário não aparecia porque não havia notas para mostrar
- Período padrão: apenas mês atual (sem dados)

### Depois:
- Usuário acessa relatórios → 35 notas encontradas
- Todos os destinatários aparecem corretamente
- Período padrão: últimos 6 meses (com dados históricos)

## Deploy

### Local: ✅ Testado e funcionando
```bash
python test_final_destinatarios.py
# SUCESSO: Todas as notas têm destinatário!
```

### AWS: Pendente de deploy
```bash
# Copiar arquivo corrigido
scp routes/relatorios_routes.py ubuntu@52.202.76.201:/var/www/api_nfe/routes/

# Reiniciar serviço
ssh ubuntu@52.202.76.201 "sudo systemctl restart api_nfe"
```

## Conclusão

O problema **NÃO ERA** com o campo destinatário ou com a query SQL. O sistema sempre esteve funcionando corretamente. O problema era apenas o **período padrão muito restrito** que não incluía nenhuma nota, dando a impressão de que os destinatários não vinham.

Com a correção do período padrão para 6 meses, o sistema agora exibe corretamente todas as notas com seus respectivos destinatários.

---
**Data da Correção:** 12/02/2026  
**Status:** ✅ Resolvido  
**Desenvolvedor:** Renato (SJ Tecnologia)

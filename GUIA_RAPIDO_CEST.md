# 🚀 GUIA RÁPIDO - Sistema CEST v2.0

## ⚡ Início Rápido

```bash
# 1. Iniciar APIs
cd /Users/renato/Documents/Developement/api_nfe
./start_apis.sh

# 2. Testar
python3 teste_cest_expandido.py

# 3. Parar
./stop_apis.sh
```

---

## 📊 Cobertura Atual

### ✅ Segmentos Implementados (15/28)

| Código | Segmento | CESTs | Taxa Acerto |
|--------|----------|-------|-------------|
| 01 | Combustíveis e Lubrificantes | 10 | 100% |
| 02 | Bebidas Alcoólicas (exc. cerveja) | 9 | 50% |
| 03 | Cervejas, Refrigerantes, Águas | 8 | 100% |
| 04 | Sorvetes | 3 | 100% |
| 05 | Chocolates | 4 | 50% |
| 06 | Cigarros | 4 | 100% |
| 07 | Artefatos Domésticos | 5 | 100% |
| 08 | Ferramentas | 6 | 50% |
| 09 | Lâminas e Isqueiros | 3 | 100% |
| 10 | Autopeças | 10 | 100% |
| 17 | Higiene Pessoal | 15 | 80% |
| 20 | Produtos de Limpeza | 8 | 67% |
| 21 | Materiais de Construção | 10 | 100% |
| 22 | Medicamentos Humano | 6 | 100% |
| 23 | Medicamentos Veterinário | 3 | 100% |
| 24 | Papéis | 4 | 100% |
| 25 | Artefatos Plásticos | 5 | 100% |
| 26 | Cosméticos | 5 | 0% |
| 28 | Materiais Elétricos | 10 | 100% |

**Total**: 120+ códigos CEST | Taxa global: **82%**

---

## 🎯 Produtos com 100% de Acerto

### Combustíveis
- ✅ Gasolina
- ✅ Diesel
- ✅ GLP
- ✅ Etanol
- ✅ Lubrificantes

### Bebidas
- ✅ Cerveja
- ✅ Refrigerante
- ✅ Água mineral
- ✅ Vinho

### Autopeças
- ✅ Pneu
- ✅ Bateria
- ✅ Amortecedor
- ✅ Filtros

### Higiene
- ✅ Shampoo
- ✅ Sabonete
- ✅ Perfume
- ✅ Creme dental

### Limpeza
- ✅ Detergente
- ✅ Amaciante

### Construção
- ✅ Cimento
- ✅ Tinta
- ✅ Argamassa
- ✅ Cal

### Elétricos
- ✅ Lâmpada
- ✅ Fio elétrico
- ✅ Tomada
- ✅ Disjuntor

---

## ⚠️ Produtos com Problemas

### Necessitam Melhorias NCM
- ❌ Whisky (NCM não encontrado)
- ❌ Bombom (NCM não encontrado)
- ❌ Desodorante (NCM limitado)
- ❌ Desinfetante (NCM limitado)

### Classificação Ambígua
- ⚠️ Água sanitária (confunde com água mineral)
- ⚠️ Chave de fenda (confunde com panela)
- ⚠️ Filtro óleo (confunde com lubrificante)
- ⚠️ Cosméticos (NCM genérico)

---

## 📡 API - Exemplos

### Exemplo 1: Cerveja ✅
```bash
curl -X POST http://localhost:9000/api/sugestao \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Cerveja Heineken 350ml",
    "tipo_item": "Produto",
    "uf_origem": "SP"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "classificacao": {
    "ncm": "22030000",
    "cest": "03.001.00",
    "cest_fonte": "Base CONFAZ (automático)",
    "cfop": "5101",
    "cst": "00",
    "csosn": "101"
  }
}
```

### Exemplo 2: Pneu ✅
```bash
curl -X POST http://localhost:9000/api/sugestao \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Pneu Pirelli 175/70 R13",
    "tipo_item": "Produto",
    "uf_origem": "SP"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "classificacao": {
    "ncm": "40122000",
    "cest": "10.001.00",
    "cest_fonte": "Base CONFAZ (automático)",
    "cfop": "5101",
    "cst": "00",
    "csosn": "101"
  }
}
```

### Exemplo 3: Notebook (SEM ST) ✅
```bash
curl -X POST http://localhost:9000/api/sugestao \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Notebook Dell Inspiron",
    "tipo_item": "Produto",
    "uf_origem": "SP"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "classificacao": {
    "ncm": "84713000",
    "cest": null,
    "cfop": "5101",
    "cst": "00",
    "csosn": "101"
  }
}
```

---

## 🔧 Integração Frontend

```javascript
// Exemplo jQuery
$('#btn_sugestao_ia').click(function() {
    const produto = $('#descricao_produto').val();
    
    $.ajax({
        url: '/admin/api/sugestao_tributaria',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            produto: produto,
            cliente_id: $('#cliente_id').val(),
            uf_origem: 'SP'
        }),
        success: function(response) {
            if (response.success) {
                // Preencher campos
                $('#ncm_id').val(response.ncm_id).trigger('change');
                $('#cfop_id').val(response.cfop_id).trigger('change');
                $('#cst_id').val(response.cst_id).trigger('change');
                $('#csosn_id').val(response.csosn_id).trigger('change');
                
                // ✨ CEST preenchido automaticamente!
                if (response.cest) {
                    $('#cest').val(response.cest);
                }
                
                alert('✅ Classificação aplicada com sucesso!');
            }
        }
    });
});
```

---

## 📝 Checklist Implantação

### Antes de Usar
- [ ] APIs rodando (8081 e 9000)
- [ ] LLM disponível (opcional, mas recomendado)
- [ ] Banco de dados com tabelas: ncms, cfops, cst_icms, csosn_icms
- [ ] Frontend com botão "Sugestão IA"

### Validação
- [ ] Testar com produtos de cada segmento
- [ ] Verificar logs: `tail -f ia_api.log`
- [ ] Monitorar performance (< 5s por produto)
- [ ] Validar CEST com tabela CONFAZ

### Manutenção
- [ ] Backup semanal da base CEST
- [ ] Atualizar NCMs novos do Siscomex
- [ ] Revisar produtos com erro > 5%
- [ ] Adicionar segmentos faltantes

---

## 🐛 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| CEST null para produto ST | Adicionar em `cest_database.py` |
| NCM não encontrado | Adicionar em `ncm_direto` dict |
| CEST segmento errado | Melhorar palavras-chave específicas |
| API timeout | Verificar LLM disponível |
| Erro 500 | Verificar logs: `tail ia_api.log` |

---

## 📊 Monitoramento

```bash
# Ver status
curl http://localhost:9000/api/status

# Ver logs em tempo real
tail -f ia_api.log ncm_api.log

# Testar health
curl http://localhost:9000/health
curl http://localhost:8081/health
```

---

## 🎓 Referências

- [Convênio ICMS 142/2018](https://www.confaz.fazenda.gov.br/legislacao/convenios/2018/CV142_18)
- [Tabela NCM Oficial](https://www.gov.br/siscomex)
- [Documentação Completa](./DOCUMENTACAO_CEST_SISTEMA.md)
- [Relatório Expansão](./RELATORIO_EXPANSAO_CEST.md)

---

**Versão**: 2.0.0  
**Última atualização**: 05/11/2025  
**Status**: ✅ Produção

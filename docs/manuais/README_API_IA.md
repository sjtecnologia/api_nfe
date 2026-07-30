# 🤖 API IA Unificada - Sugestão Tributária

Sistema completo de classificação tributária automática usando NCM + LLM integrados.

## 📋 Arquitetura Simplificada

```
┌─────────────────────────────────────────────────────┐
│         API IA UNIFICADA (Porta 9000)               │
│  ✅ Sugestão Tributária Completa                    │
│  ✅ Busca NCM                                        │
│  ✅ Health Check                                     │
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
   ┌────▼──────┐    ┌────▼────────────────┐
   │  API NCM  │    │  LLM Llama-3.1-8B   │
   │ :8081     │    │  :1234 (LM Studio)  │
   │ 13.217    │    │  192.168.0.52       │
   │ códigos   │    │                     │
   └───────────┘    └─────────────────────┘
```

## 🚀 Como Usar

### Início Rápido (1 comando!)

```bash
./start_apis.sh
```

Este comando:
- ✅ Verifica dependências
- ✅ Inicia API NCM (porta 8081)
- ✅ Verifica LLM (porta 1234)
- ✅ Inicia API IA Unificada (porta 9000)
- ✅ Exibe resumo e testes

### Parar Serviços

```bash
./stop_apis.sh
```

## 📡 Endpoints Disponíveis

### 1. Sugestão Individual

```bash
curl -X POST http://localhost:9000/api/sugestao \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Smartphone Samsung Galaxy",
    "tipo_item": "Produto",
    "uf_origem": "SP",
    "regime_tributario": "Simples Nacional"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "timestamp": "2025-11-03T...",
  "produto": "Smartphone Samsung Galaxy",
  "classificacao": {
    "ncm": "85171231",
    "cfop": "5101",
    "cst": "00",
    "csosn": "101",
    "cest": null,
    "explicacao": "Classificação baseada em..."
  }
}
```

### 2. Sugestão em Lote

```bash
curl -X POST http://localhost:9000/api/sugestao/lote \
  -H "Content-Type: application/json" \
  -d '{
    "produtos": [
      {"descricao": "Smartphone", "tipo_item": "Produto"},
      {"descricao": "Notebook", "tipo_item": "Produto"},
      {"descricao": "Mouse wireless", "tipo_item": "Produto"}
    ],
    "uf_origem": "SP",
    "regime_tributario": "Simples Nacional"
  }'
```

### 3. Buscar NCM

```bash
curl "http://localhost:9000/api/ncm/search?q=smartphone&limit=5"
```

### 4. Health Check

```bash
curl http://localhost:9000/health
```

### 5. Status Detalhado

```bash
curl http://localhost:9000/api/status
```

### 6. Documentação Completa

```bash
curl http://localhost:9000/
```

## 🔧 Configuração

### Arquivos Necessários

- ✅ `api_ia_unificada.py` - API principal
- ✅ `api_ncm_standalone.py` - API NCM
- ✅ `servico_sugestao_ia.py` - Lógica de integração
- ✅ `Tabela_NCM_Vigente_20251029.json` - Base de dados NCM

### Dependências Python

```bash
source venv/bin/activate
pip install flask flask-cors requests
```

### Serviços Externos

1. **LLM Studio** - http://192.168.0.52:1234
   - Modelo: meta-llama-3.1-8b-instruct
   - Status: Opcional (tem fallback)

2. **API NCM** - http://localhost:8081
   - 13.217 códigos oficiais
   - Status: Obrigatório

## 📊 Monitoramento

### Ver Logs em Tempo Real

```bash
# API NCM
tail -f ncm_api.log

# API IA Unificada
tail -f ia_api.log
```

### Verificar Status

```bash
# Health check rápido
curl -s http://localhost:9000/health | jq

# Status detalhado
curl -s http://localhost:9000/api/status | jq
```

### Verificar Portas Ativas

```bash
lsof -i :8081  # API NCM
lsof -i :9000  # API IA
lsof -i :1234  # LLM
```

## 🧪 Testes

### Teste Completo do Sistema

```bash
# 1. Verificar health
curl http://localhost:9000/health

# 2. Testar sugestão
curl -X POST http://localhost:9000/api/sugestao \
  -H "Content-Type: application/json" \
  -d '{"descricao": "Smartphone", "tipo_item": "Produto", "uf_origem": "SP"}'

# 3. Testar busca NCM
curl "http://localhost:9000/api/ncm/search?q=smartphone"
```

### Teste de Performance

```bash
# Testar tempo de resposta
time curl -X POST http://localhost:9000/api/sugestao \
  -H "Content-Type: application/json" \
  -d '{"descricao": "Notebook Dell", "tipo_item": "Produto"}'
```

## ⚡ Performance

- **Tempo médio de resposta:** ~5 segundos
- **Taxa de sucesso:** 100% (com fallback)
- **Suporte a lote:** Até 10 produtos por requisição
- **Timeout LLM:** 5 segundos (fallback automático)

## 🛠️ Troubleshooting

### API NCM não inicia

```bash
# Verificar porta
lsof -i :8081

# Ver logs
cat ncm_api.log

# Verificar arquivo de dados
ls -lh Tabela_NCM_Vigente_20251029.json
```

### LLM não responde

```bash
# Verificar conectividade
curl http://192.168.0.52:1234/v1/models

# A API funcionará em modo fallback se LLM estiver offline
```

### API IA não inicia

```bash
# Verificar porta
lsof -i :9000

# Ver logs
cat ia_api.log

# Verificar dependências
source venv/bin/activate
python3 -c "import flask, requests; print('OK')"
```

## 📝 Estrutura de Arquivos

```
api_nfe/
├── api_ia_unificada.py           # API principal ⭐
├── api_ncm_standalone.py          # API NCM (porta 8081)
├── servico_sugestao_ia.py         # Lógica de integração
├── start_apis.sh                  # Iniciar tudo 🚀
├── stop_apis.sh                   # Parar tudo 🛑
├── Tabela_NCM_Vigente_20251029.json  # Base de dados
├── ncm_api.log                    # Logs API NCM
├── ia_api.log                     # Logs API IA
└── README_API_IA.md               # Este arquivo
```

## 🎯 Próximos Passos

1. **Integração com App Principal**
   ```python
   # No routes/admin_routes.py
   import requests
   
   resultado = requests.post(
       'http://localhost:9000/api/sugestao',
       json={'descricao': descricao, 'tipo_item': tipo_item}
   )
   ```

2. **Cache de Resultados**
   - Implementar cache Redis para produtos frequentes
   - Reduzir chamadas à LLM

3. **Monitoramento**
   - Dashboard de métricas
   - Alertas de disponibilidade

## 📞 Suporte

Em caso de problemas:

1. Verificar logs: `tail -f ia_api.log ncm_api.log`
2. Testar endpoints: `curl http://localhost:9000/health`
3. Reiniciar serviços: `./stop_apis.sh && ./start_apis.sh`

---

**Desenvolvido com ❤️ usando Flask + LLM + NCM oficial**

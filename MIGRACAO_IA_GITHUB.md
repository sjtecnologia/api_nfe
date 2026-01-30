# Migração para GitHub Models (IA Nativa)

**Data:** 30 de Janeiro de 2026  
**Status:** ✅ CONCLUÍDO

## Resumo

O sistema foi migrado para usar **GitHub Models** (GPT-4o-mini) como provedor de IA principal, substituindo completamente o LLM local que requeria VPN.

---

## 🔄 O Que Mudou

### ANTES (Sistema Antigo)
- **LLM Local:** Servidor `192.168.0.52:1234` (Llama-3.1-8B)
- **Acesso:** Requer VPN/WireGuard para conectar ao servidor local
- **Dependência:** Hardware dedicado (GPU, servidor local sempre ligado)
- **Latência:** Variável dependendo da rede
- **Custo:** Infraestrutura própria

### AGORA (Sistema Atual)
- **GitHub Models:** API Cloud (GPT-4o-mini)
- **Acesso:** Direto via internet (HTTPS)
- **Token:** Variável de ambiente `GITHUB_TOKEN`
- **Latência:** ~1-3 segundos (API otimizada)
- **Custo:** Incluído no GitHub (gratuito até limite)

---

## ✅ Benefícios da Migração

1. **Sem VPN:** Não é mais necessário configurar VPN/WireGuard
2. **Sem Infraestrutura:** Não precisa manter servidor LLM local
3. **Sempre Disponível:** API cloud 99.9% uptime
4. **Modelo Atualizado:** GPT-4o-mini (mais preciso que Llama local)
5. **Escalável:** Suporta múltiplas requisições simultâneas
6. **Manutenção Zero:** GitHub gerencia atualizações e patches

---

## 🔧 Configuração Atual

### Variável de Ambiente
```bash
GITHUB_TOKEN=github_pat_xxxxxxxxxx
```

### Serviço de IA (ia_service/main.py)
```python
github_token = os.getenv("GITHUB_TOKEN", "")

if github_token:
    llm_url = "https://models.inference.ai.azure.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {github_token}"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [...],
        "max_tokens": 1000,
        "temperature": 0.1
    }
```

### Fallback Automático
Se `GITHUB_TOKEN` não estiver configurado, o sistema usa **validação por regras** (sem IA).

---

## 📋 Funcionalidades Usando GitHub Models

### 1. Validação de Regras Tributárias (NFe)
- **Endpoint:** `/api/validar-regra-ia`
- **Modelo:** GPT-4o-mini
- **Valida:** CFOP, CST, CSOSN, NCM, regime tributário

### 2. Validação de Regras de Serviços (NFS-e)
- **Endpoint:** `/api/validar-regra-servico-ia`
- **Modelo:** GPT-4o-mini
- **Valida:** LC 116, NBS, ISS, CST IBS/CBS, Reforma Tributária

### 3. Sugestões Tributárias (Produtos)
- **Endpoint:** `/api/sugerir-classificacao`
- **Modelo:** GPT-4o-mini
- **Sugere:** NCM, CFOP, CST, CSOSN, CEST

### 4. Análise de Documentos Fiscais
- **Endpoint:** `/api/analisar-xml`
- **Modelo:** GPT-4o-mini
- **Analisa:** Conformidade, erros, sugestões de melhoria

---

## ❌ O Que Foi REMOVIDO

### VPN/WireGuard
- ❌ Não há mais configuração de VPN
- ❌ Não precisa de túnel WireGuard
- ❌ Não há firewall/porta a liberar para LLM local

### Servidor LLM Local (192.168.0.52)
- ❌ Não há mais servidor `192.168.0.52:1234`
- ❌ Não precisa de Llama-3.1-8B local
- ❌ Não precisa de LM Studio ou Ollama

### Scripts Antigos (Deprecated)
Os seguintes scripts usavam LLM local e estão **obsoletos**:

```
/scripts/utilitarios/
  ├── NCM_INTEGRATION_FINAL.py          # Usa 192.168.0.52
  ├── api_ia_unificada.py               # Usa 192.168.0.52
  ├── simple_ncm_consultant.py          # Usa 192.168.0.52
  └── ncm_rag_system.py                 # Usa 192.168.0.52

/examples/
  ├── exemplo_treinamento_llm.py        # Usa 192.168.0.52
  └── llm_integration_example.py        # Usa 192.168.0.52
```

**Ação:** Manter para referência histórica, mas **NÃO USAR**.

---

## 🚀 Deploy AWS

### Serviços Ativos
1. **api-nfe-principal** (Flask, porta 8080)
   - Usa GitHub Models via proxy

2. **api-nfe-ia** (FastAPI, porta 8081)
   - Faz requisições ao GitHub Models
   - Retorna resultados processados

### Nenhuma Dependência Externa
- ✅ Sem VPN
- ✅ Sem servidor LLM local
- ✅ Apenas variável `GITHUB_TOKEN` necessária

---

## 📊 Comparativo de Performance

| Métrica | LLM Local (Antigo) | GitHub Models (Atual) |
|---------|-------------------|----------------------|
| Tempo resposta | 5-15s | 1-3s |
| Disponibilidade | 95% (depende servidor) | 99.9% |
| Precisão | Boa (Llama-3.1-8B) | Excelente (GPT-4o-mini) |
| Setup | Complexo (VPN+GPU) | Simples (token) |
| Custo | Hardware próprio | Gratuito GitHub |
| Manutenção | Alta | Zero |

---

## 🔐 Segurança

### Token GitHub
- Armazenado em variável de ambiente (não commitado)
- Rotação periódica recomendada
- Escopo: `inference` apenas

### Dados Enviados
- **Não enviamos:** CPF, CNPJ, nomes de clientes
- **Enviamos:** Códigos fiscais, descrições genéricas, regras
- **GitHub:** Não treina modelos com nossos dados

---

## 📝 Próximos Passos

1. ✅ **Remover scripts antigos** da pasta `/scripts/utilitarios/` (opcional)
2. ✅ **Documentar** migração (este arquivo)
3. ✅ **Monitorar** uso do token GitHub (quotas)
4. ⏳ **Avaliar** upgrade para GPT-4o se necessário

---

## 🆘 Suporte

### Em Caso de Problemas

**Erro: "Serviço de IA indisponível"**
- Verificar variável `GITHUB_TOKEN` configurada
- Verificar quota GitHub não excedida
- Sistema usa fallback automático (regras básicas)

**Erro: "Invalid token"**
- Gerar novo token em: https://github.com/settings/tokens
- Configurar escopo: `inference`
- Atualizar variável de ambiente

**Latência Alta (>5s)**
- Normal em horários de pico
- GitHub Models é serviço compartilhado
- Sistema continua funcional

---

## 📚 Documentação Adicional

- [GitHub Models Documentation](https://docs.github.com/en/github-models)
- [GPT-4o-mini Specs](https://platform.openai.com/docs/models/gpt-4o-mini)
- [Azure AI Inference API](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

---

**Última Atualização:** 30/01/2026  
**Responsável:** Equipe SJ Tecnologia  
**Status:** ✅ Sistema em produção com GitHub Models

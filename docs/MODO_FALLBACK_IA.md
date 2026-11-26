# 🔄 Modo Fallback - Sistema de Sugestão IA

## 📋 Visão Geral

O sistema de sugestão tributária agora possui um **modo fallback** que permite funcionar mesmo quando as APIs externas (NCM e LLM) estão offline ou indisponíveis.

## 🔍 Como Funciona

### Verificação de APIs

O sistema verifica a disponibilidade de cada API independentemente:

```python
apis_status = {
    "ncm": False,  # API NCM em localhost:8081
    "llm": False   # LLM em 192.168.0.52:1234
}
```

### Cenários de Operação

#### ✅ Cenário 1: Todas APIs Online (Modo Normal)
- API NCM: busca códigos oficiais do Siscomex
- LLM: análise inteligente e classificação precisa
- CEST: sugestão automática baseada em CONFAZ

**Resultado:** Sugestões precisas e confiáveis

#### ⚠️ Cenário 2: Apenas LLM Offline
- API NCM: busca códigos oficiais
- **Fallback LLM**: usa regras heurísticas básicas
- CEST: funciona normalmente

**Resultado:** Sugestões baseadas em NCM real + regras

#### ⚠️ Cenário 3: Apenas API NCM Offline
- **Fallback NCM**: usa mapa de NCMs conhecidos
- LLM: indisponível sem dados NCM
- **Fallback Completo**: regras heurísticas

**Resultado:** Sugestões básicas funcionais

#### 🔴 Cenário 4: Ambas APIs Offline (Modo Fallback Total)
- **Fallback Completo**: usa apenas regras heurísticas
- NCM: mapeamento interno de produtos comuns
- CFOP: 5101 (padrão)
- CST/CSOSN: baseado em regime tributário

**Resultado:** Sugestões básicas que permitem continuar trabalhando

## 🗺️ Mapa de NCMs (Fallback)

O sistema possui um mapa interno de NCMs para produtos comuns:

| Produto | NCM | Descrição |
|---------|-----|-----------|
| Software/Sistema | 85234910 | Suportes com software |
| Mouse | 84716053 | Mouse óptico |
| Teclado | 84716052 | Teclados |
| Monitor | 85285900 | Monitores LCD |
| Computador | 84713000 | Computadores portáteis |
| Notebook | 84713010 | Notebooks |
| Impressora | 84433210 | Impressoras |
| Celular | 85171231 | Smartphones |
| Tablet | 85171270 | Tablets |

## 📊 Resposta Fallback

Quando em modo fallback, a resposta inclui um campo adicional:

```json
{
  "ncm": "84716053",
  "cfop": "5101",
  "cst": "00",
  "csosn": null,
  "cest": null,
  "explicacao": "Sugestão básica gerada por regras heurísticas (APIs offline). Verifique e ajuste conforme necessário.",
  "modo": "fallback"
}
```

**Atenção:** A presença do campo `"modo": "fallback"` indica que a sugestão foi gerada sem as APIs e deve ser revisada.

## 🚀 Como Iniciar as APIs

### API NCM (Porta 8081)

```bash
cd /Users/renato/Documents/Developement/api_nfe
source venv/bin/activate
python3 api_ncm_standalone.py
```

Verificação:
```bash
curl http://localhost:8081/health
```

### LLM Studio (Porta 1234)

1. Abra o LM Studio
2. Carregue o modelo Llama-3.1-8B
3. Inicie o servidor local
4. Verifique: `curl http://192.168.0.52:1234/v1/models`

### Script Automático

```bash
./start_apis.sh
```

## 🔔 Mensagens de Diagnóstico

O sistema exibe mensagens claras no console:

```
✅ API NCM disponível
✅ LLM disponível
📋 Gerando prompt...
🤖 Consultando IA...
✅ Sugestão gerada com sucesso!
```

Ou em caso de fallback:

```
⚠️ API NCM offline: Connection refused - usando fallback
⚠️ LLM offline: Connection refused - usando regras heurísticas
⚠️ Modo fallback total - gerando sugestão básica
⚙️ Usando regras heurísticas
✅ Sugestão gerada com sucesso!
```

## ⚙️ Configuração

As URLs das APIs podem ser configuradas na inicialização do serviço:

```python
from servico_sugestao_ia import ServicoSugestaoIA

# URLs padrão
servico = ServicoSugestaoIA()

# URLs customizadas
servico = ServicoSugestaoIA(
    ncm_api_url="http://servidor:8081",
    llm_url="http://servidor-llm:1234"
)
```

## 📝 Recomendações

### Para Produção
- **Sempre** tenha as APIs rodando
- Configure monitoramento de uptime
- Use o modo fallback apenas como backup

### Para Desenvolvimento
- Modo fallback permite trabalhar sem dependências
- Útil para testes de interface
- NCMs básicos suficientes para validação

### Para Demonstrações
- Modo fallback garante que o sistema sempre responde
- Melhor experiência do usuário
- Sem erros HTTP 500

## 🔧 Troubleshooting

### Erro: Connection refused (localhost:8081)
**Causa:** API NCM não está rodando  
**Solução:** `python3 api_ncm_standalone.py`

### Erro: Connection refused (192.168.0.52:1234)
**Causa:** LM Studio não está rodando  
**Solução:** Inicie o LM Studio e o servidor local

### Sugestões muito genéricas
**Causa:** Modo fallback ativo  
**Solução:** Inicie as APIs para sugestões precisas

### Timeout nas APIs
**Causa:** APIs lentas ou sobrecarregadas  
**Solução:** Sistema usa fallback automaticamente após 2s

## 📈 Benefícios

✅ **Alta disponibilidade**: Sistema sempre responde  
✅ **Graceful degradation**: Qualidade diminui, mas funciona  
✅ **Sem erros HTTP 500**: Sempre retorna sugestão  
✅ **Diagnóstico claro**: Mensagens indicam modo de operação  
✅ **Recuperação automática**: Volta ao modo normal quando APIs retornam  

## 🎯 Próximos Passos

1. Expandir mapa de NCMs fallback com mais produtos
2. Adicionar regras de CFOP baseadas em UF origem/destino
3. Melhorar heurísticas de CST baseado em tipo de produto
4. Implementar cache de sugestões anteriores
5. Adicionar indicador visual no frontend quando em modo fallback

---

**Atualizado:** 19/11/2025  
**Versão:** 1.0  
**Status:** ✅ Implementado e testado

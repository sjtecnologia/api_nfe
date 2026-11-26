# 🤖 Documentação da API NCM para LLM

## 📋 Visão Geral

Esta API fornece acesso completo à base de **NCMs (Nomenclatura Comum do Mercosul)** brasileira para integração com sua LLM. A base contém **13.217 códigos NCM** hierárquicos obtidos do Sistema Siscomex da Receita Federal.

**URL Base**: `http://192.168.0.52:1234` (porta da sua LLM)

## 🏗️ Estrutura de Dados NCM

### Hierarquia NCM
- **Capítulo** (2 dígitos): Ex: `01` - Animais vivos
- **Posição** (4 dígitos): Ex: `01.01` - Cavalos, asininos e muares, vivos
- **Subposição** (6 dígitos): Ex: `01.01.21` - Reprodutores de raça pura (categoria)
- **Item** (8 dígitos): Ex: `01.01.21.00` - Reprodutores de raça pura (específico)

### Tipos de NCM
- **Sintético**: Apenas para classificação hierárquica (não pode receber lançamentos)
- **Analítico**: Código final usado em Notas Fiscais Eletrônicas (pode receber lançamentos)

## 🚀 Endpoints da API

### 1. Exportar Base Completa para Treinamento
```http
GET /api/llm/ncms/export
```

**Uso**: Obtém TODA a base NCM estruturada para treinar sua LLM.

**Resposta**:
```json
{
  "success": true,
  "metadata": {
    "descricao": "Base completa de NCMs hierárquica",
    "fonte": "Sistema Siscomex - Receita Federal do Brasil",
    "estrutura": "Hierárquica: Capítulo (2d) > Posição (4d) > Subposição (6d) > Item (8d)",
    "uso": "NCMs analíticos (8 dígitos) são usados em NFe"
  },
  "estatisticas": {
    "total_ncms": 13217,
    "por_tipo": {
      "sinteticos": 2710,
      "analiticos": 10507
    }
  },
  "ncms": [
    {
      "id": 1,
      "codigo": "01012100",
      "codigo_formatado": "01.01.21.00",
      "descricao": "Reprodutores de raça pura",
      "tipo": "analitico",
      "nivel": {
        "nome": "Item",
        "digitos": 8,
        "posicao_hierarquia": 3
      },
      "hierarquia_pais": [
        {
          "codigo": "01",
          "nivel": "Capítulo",
          "descricao": "Animais vivos."
        }
      ],
      "pode_receber_lancamento": true,
      "contexto_completo": "Capítulo: 01 - Animais vivos. > Posição: 01.01 - Cavalos, asininos e muares, vivos. > NCM: 01.01.21.00 - Reprodutores de raça pura",
      "tags_busca": ["01012100", "01.01.21.00", "item", "reprodutores", "raça", "pura"]
    }
  ]
}
```

### 2. Buscar NCMs
```http
GET /api/llm/ncms/search?q={termo}&tipo={tipo}&nivel={nivel}&limit={limite}
```

**Parâmetros**:
- `q` (obrigatório): Termo de busca (código ou descrição)
- `tipo` (opcional): `sintetico`, `analitico` ou `todos` (padrão: `todos`)
- `nivel` (opcional): `capitulo`, `posicao`, `subposicao`, `item` ou `todos` (padrão: `todos`)
- `limit` (opcional): Máximo 200 resultados (padrão: 50)

**Exemplo**: `/api/llm/ncms/search?q=cavalos&tipo=analitico&limit=5`

### 3. Obter Hierarquia de NCM
```http
GET /api/llm/ncms/hierarquia/{codigo}
```

**Parâmetros**:
- `codigo`: Código NCM (com ou sem pontos)

**Exemplo**: `/api/llm/ncms/hierarquia/01.01.21.00`

**Resposta**:
```json
{
  "success": true,
  "ncm_solicitado": {
    "codigo": "01012100",
    "codigo_formatado": "01.01.21.00",
    "descricao": "Reprodutores de raça pura",
    "tipo": "analitico"
  },
  "hierarquia": {
    "pais": [
      {
        "codigo": "01",
        "codigo_formatado": "01",
        "descricao": "Animais vivos.",
        "tipo": "sintetico"
      }
    ],
    "filhos": [],
    "irmaos": []
  }
}
```

### 4. Estatísticas da Base
```http
GET /api/llm/ncms/stats
```

**Uso**: Obtenha estatísticas gerais e contexto da base NCM.

## 🎯 Como Usar na sua LLM

### 1. Treinamento Inicial
```python
import requests

# Baixar base completa
response = requests.get("http://192.168.0.52:1234/api/llm/ncms/export")
ncm_data = response.json()

# Use ncm_data["ncms"] para treinar sua LLM sobre:
# - Estrutura hierárquica de NCMs
# - Relações entre códigos
# - Descrições e contextos
# - Quais são analíticos vs sintéticos
```

### 2. Consultas em Tempo Real
```python
def find_ncm_for_product(product_description: str):
    """Encontra NCM para um produto"""
    params = {
        "q": product_description,
        "tipo": "analitico",  # Só NCMs usáveis em NFe
        "nivel": "item",      # Só códigos de 8 dígitos
        "limit": 5
    }
    
    response = requests.get(
        "http://192.168.0.52:8080/api/llm/ncms/search",
        params=params
    )
    
    return response.json()

# Exemplo
result = find_ncm_for_product("notebook computador portátil")
```

### 3. Explicação Contextual
```python
def explain_ncm(codigo: str):
    """Explica um NCM com contexto hierárquico"""
    response = requests.get(
        f"http://192.168.0.52:8080/api/llm/ncms/hierarquia/{codigo}"
    )
    
    data = response.json()
    if data["success"]:
        # Monta explicação hierárquica
        explanation = []
        for pai in data["hierarquia"]["pais"]:
            explanation.append(f"{pai['codigo_formatado']}: {pai['descricao']}")
        
        ncm = data["ncm_solicitado"]
        explanation.append(f"→ {ncm['codigo_formatado']}: {ncm['descricao']}")
        
        return " > ".join(explanation)
```

## 🧠 Contexto para LLM

### Regras Importantes
1. **NCMs Analíticos** (8 dígitos) são os únicos usados em NFe
2. **NCMs Sintéticos** são apenas para classificação hierárquica
3. **Hierarquia é obrigatória**: Sempre entender o contexto pai
4. **Precisão é crucial**: NCM errado pode causar problemas fiscais

### Casos de Uso Comuns
- **Classificação de produtos** para NFe
- **Consulta de alíquotas** de impostos
- **Verificação de regulamentações** específicas
- **Auditoria fiscal** e compliance

### Exemplos de Perguntas que sua LLM pode responder:

**Pergunta**: "Qual NCM para notebook?"
**Resposta LLM**:
```
Para notebooks/computadores portáteis, recomendo verificar:

🔍 Busquei por "notebook computador portátil" e encontrei:

**84.71.30.00** - Máquinas automáticas para processamento de dados, portáteis
📁 Hierarquia: 84 (Máquinas e aparelhos mecânicos) > 84.71 (Máquinas automáticas para processamento de dados) > 84.71.30 (Portáteis)
✅ NCM analítico - pode ser usado em NFe

Este é o NCM mais apropriado para notebooks e laptops.
```

**Pergunta**: "O que significa NCM 01.01.21.00?"
**Resposta LLM**:
```
📋 **NCM 01.01.21.00**: Reprodutores de raça pura

**Contexto Hierárquico**:
• 01: Animais vivos
  • 01.01: Cavalos, asininos e muares, vivos
    • **01.01.21.00**: Reprodutores de raça pura

✅ **Tipo**: Analítico (pode receber lançamentos em NFe)
🎯 **Uso**: Para cavalos, asininos e muares reprodutores de raça pura
📝 **Aplicação**: Importação/exportação de animais reprodutores certificados
```

## 🔧 Configuração no seu Servidor

1. **Instale dependências**:
```bash
pip install flask sqlalchemy psycopg2-binary
```

2. **Configure a URL** no seu script:
```python
API_BASE_URL = "http://192.168.0.52:1234"  # Porta da sua LLM
```

3. **Teste a conexão**:
```bash
curl http://192.168.0.52:1234/api/llm/ncms/stats
```

## ⚡ Performance e Limites

- **Base completa**: ~15MB JSON (13.217 NCMs)
- **Limite de busca**: 200 resultados por consulta
- **Timeout**: 30 segundos por requisição
- **Encoding**: UTF-8 (suporta acentos portugueses)

## 🛡️ Segurança

- API é **somente leitura** (GET requests)
- Não requer autenticação para endpoints LLM
- Dados são **públicos** (Receita Federal)
- **Rate limiting** recomendado se uso intensivo

## 📞 Suporte

Para dúvidas sobre a API ou estrutura de dados, consulte:
- Documentação oficial: [Sistema Siscomex](https://siscomex.gov.br)
- Base de dados: PostgreSQL local
- Código fonte: `/routes/llm_api_routes.py`

---
**✅ API pronta para integração com sua LLM em 192.168.0.52!**
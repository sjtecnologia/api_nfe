# � GUIA DEFINITIVO: TREINAR SUA LLM COM NCMs

## ✅ SITUAÇÃO ATUAL

**API NCM criada e testada com sucesso!** 

- ✅ **13.217 NCMs** carregados e funcionando
- ✅ **API independente** pronta para porta 1234
- ✅ **Todos os endpoints** testados e funcionais
- ✅ **Scripts de integração** criados

## 🚀 PRÓXIMOS PASSOS (3 Simples)

### 1️⃣ **COPIAR ARQUIVOS PARA SEU SERVIDOR**

Copie estes 2 arquivos para o servidor `192.168.0.52`:

```bash
# No seu computador:
scp api_ncm_standalone.py usuario@192.168.0.52:/caminho/destino/
scp ncms_training_data.json usuario@192.168.0.52:/caminho/destino/
```

### 2️⃣ **EXECUTAR NO SERVIDOR**

No servidor 192.168.0.52:

```bash
# Instalar dependência (se não tiver)
pip3 install flask

# Executar API
cd /caminho/destino/
python3 api_ncm_standalone.py
```

**Você verá:**
```
🤖 API NCM para LLM - Versão Independente
==================================================
✅ Carregados 13217 NCMs processados
🌐 Servidor será executado em: http://192.168.0.52:1234
🚀 Iniciando servidor...
```

### 3️⃣ **TESTAR SE FUNCIONOU**

Do seu computador:
```bash
curl http://192.168.0.52:1234/health
```

**Resposta esperada:**
```json
{
  "status": "UP",
  "ncms_loaded": true,
  "total_ncms": 13217
}
```

---

## 🤖 COMO INTEGRAR COM SUA LLM

### **Código para sua LLM:**

```python
import requests

class NCMExpert:
    def __init__(self):
        self.api_url = "http://192.168.0.52:1234"
    
    def buscar_ncm(self, produto):
        """Busca NCM para um produto"""
        response = requests.get(f"{self.api_url}/api/llm/ncms/search", 
                              params={"q": produto, "tipo": "analitico", "limit": 3})
        return response.json()
    
    def explicar_ncm(self, codigo):
        """Explica um NCM com contexto"""
        response = requests.get(f"{self.api_url}/api/llm/ncms/hierarquia/{codigo}")
        return response.json()
    
    def responder_pergunta(self, pergunta):
        """Responde perguntas sobre NCM"""
        
        # Extrai palavra-chave da pergunta
        palavras = pergunta.lower().split()
        termo = " ".join([p for p in palavras if len(p) > 3][:3])
        
        # Busca NCMs
        resultado = self.buscar_ncm(termo)
        
        if resultado.get("success") and resultado.get("resultados"):
            ncm = resultado["resultados"][0]
            
            # Busca contexto hierárquico
            hierarquia = self.explicar_ncm(ncm["codigo"])
            
            # Monta resposta
            resposta = f"""🔍 **NCM {ncm['codigo_formatado']}**: {ncm['descricao']}

📁 **Hierarquia**:"""
            
            if hierarquia.get("success"):
                for pai in hierarquia["hierarquia"]["pais"]:
                    resposta += f"\n• {pai['codigo_formatado']}: {pai['descricao']}"
                resposta += f"\n  • **{ncm['codigo_formatado']}**: **{ncm['descricao']}**"
            
            resposta += f"""

✅ **Tipo**: Analítico (adequado para NFe)
🎯 **Uso**: Recomendado para classificação fiscal deste produto"""
            
            return resposta
        else:
            return f"❌ Não encontrei NCMs relacionados a '{termo}'"

# Usar na sua LLM:
ncm_expert = NCMExpert()
resposta = ncm_expert.responder_pergunta("Qual NCM para cavalos reprodutores?")
print(resposta)
```

### **Exemplo de Resposta:**

**Pergunta**: "Qual NCM para cavalos reprodutores?"

**Sua LLM responderá:**
```
🔍 **NCM 01.01.21.00**: Reprodutores de raça pura

📁 **Hierarquia**:
• 01: Animais vivos.
  • 01.01: Cavalos, asininos e muares, vivos.
    • **01.01.21.00**: **Reprodutores de raça pura**

✅ **Tipo**: Analítico (adequado para NFe)
🎯 **Uso**: Recomendado para classificação fiscal deste produto
```

---

## 🎓 TREINAMENTO AVANÇADO DA LLM

### **1. Prompt do Sistema:**

```
Você é um especialista em NCMs (Nomenclatura Comum do Mercosul) brasileiros.

DADOS DISPONÍVEIS:
- 13.217 NCMs hierárquicos oficiais
- API em http://192.168.0.52:1234
- Base da Receita Federal (Siscomex)

REGRAS:
1. APENAS NCMs analíticos (8 dígitos) são usados em NFe
2. NCMs sintéticos são apenas para classificação
3. SEMPRE forneça contexto hierárquico completo
4. SEMPRE indique se é analítico ou sintético

Para consultas NCM, use a API disponível.
```

### **2. Exemplos de Treinamento:**

Use o arquivo `ncms_training_data.json` (17.8 MB) que contém:
- 13.217 exemplos estruturados
- Contexto hierárquico completo
- Classificação sintético/analítico
- Tags de busca otimizadas

### **3. Funções da LLM:**

Ensine sua LLM estas funções:

```python
# Função 1: Buscar por produto
def find_ncm_for_product(product_name):
    # Chama API de busca
    # Retorna melhores NCMs analíticos

# Função 2: Explicar NCM
def explain_ncm_code(ncm_code):
    # Chama API de hierarquia
    # Retorna contexto completo

# Função 3: Validar NCM
def validate_ncm(ncm_code):
    # Verifica se existe e é analítico
    # Retorna status de validade
```

## 🚀 ABORDAGEM 1: RAG (RECOMENDADA)

### Por que RAG é melhor?
- ✅ Não precisa retreinar o modelo
- ✅ Dados sempre atualizados
- ✅ Menor custo computacional
- ✅ Implementação mais rápida

### 1. Instalar dependências
```bash
pip install openai chromadb sentence-transformers requests
```

### 2. Script RAG completo
```python
#!/usr/bin/env python3
"""
Sistema RAG para consulta de NCMs
Integra base de dados NCM com sua LLM
"""

import requests
import json
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
import openai

class NCMRagSystem:
    def __init__(self, api_base_url: str = "http://192.168.0.52:8080"):
        self.api_url = api_base_url
        self.client = chromadb.PersistentClient(path="./ncm_vectordb")
        self.collection = None
        self.encoder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Configure sua LLM aqui (OpenAI, Ollama, etc.)
        # openai.api_key = "sua-api-key"
        # openai.api_base = "http://192.168.0.52:8000/v1"  # Se usando Ollama
    
    def load_ncm_data(self):
        """Carrega dados NCM da API e indexa no ChromaDB"""
        print("🔄 Carregando dados NCM...")
        
        response = requests.get(f"{self.api_url}/api/llm/ncms/export")
        if not response.ok:
            raise Exception(f"Erro ao carregar dados: {response.status_code}")
        
        data = response.json()
        ncms = data['ncms']
        
        print(f"📋 Carregados {len(ncms)} NCMs")
        
        # Cria ou obtém coleção
        try:
            self.collection = self.client.get_collection("ncms")
            print("✅ Usando coleção existente")
        except:
            self.collection = self.client.create_collection("ncms")
            print("🆕 Criada nova coleção")
            
            # Prepara documentos para indexação
            documents = []
            metadatas = []
            ids = []
            
            for ncm in ncms:
                # Texto para busca semântica
                text = f"""
                NCM {ncm['codigo_formatado']}: {ncm['descricao']}
                Tipo: {ncm['tipo']}
                Nível: {ncm['nivel']['nome']}
                Contexto: {ncm.get('contexto_completo', '')}
                Hierarquia: {' > '.join([p['descricao'] for p in ncm.get('hierarquia_pais', [])])}
                """
                
                documents.append(text.strip())
                metadatas.append({
                    'codigo': ncm['codigo'],
                    'codigo_formatado': ncm['codigo_formatado'],
                    'descricao': ncm['descricao'],
                    'tipo': ncm['tipo'],
                    'nivel': ncm['nivel']['nome'],
                    'pode_usar_nfe': ncm['pode_receber_lancamento']
                })
                ids.append(str(ncm['id']))
            
            # Indexa no ChromaDB
            print("🔄 Indexando no banco vetorial...")
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
                print(f"   Processados {min(i+batch_size, len(documents))}/{len(documents)}")
            
            print("✅ Indexação concluída!")
    
    def search_relevant_ncms(self, query: str, n_results: int = 5) -> List[Dict]:
        """Busca NCMs relevantes para a consulta"""
        if not self.collection:
            raise Exception("Dados não carregados. Execute load_ncm_data() primeiro.")
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        relevant_ncms = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            relevant_ncms.append({
                'document': doc,
                'metadata': metadata,
                'distance': results['distances'][0][i] if 'distances' in results else 0
            })
        
        return relevant_ncms
    
    def generate_response(self, user_question: str) -> str:
        """Gera resposta usando RAG"""
        # 1. Busca NCMs relevantes
        relevant_ncms = self.search_relevant_ncms(user_question, n_results=3)
        
        # 2. Constrói contexto
        context = "INFORMAÇÕES NCM RELEVANTES:\\n\\n"
        for i, ncm in enumerate(relevant_ncms, 1):
            meta = ncm['metadata']
            context += f"{i}. NCM {meta['codigo_formatado']}: {meta['descricao']}\\n"
            context += f"   Tipo: {meta['tipo']} | Nível: {meta['nivel']}\\n"
            context += f"   Pode usar em NFe: {'Sim' if meta['pode_usar_nfe'] else 'Não'}\\n\\n"
        
        # 3. Prompt para LLM
        prompt = f"""
Você é um especialista em NCM (Nomenclatura Comum do Mercosul) brasileiro.

{context}

PERGUNTA DO USUÁRIO: {user_question}

INSTRUÇÕES:
- Use apenas as informações NCM fornecidas acima
- Seja preciso e técnico
- Sempre mencione se o NCM é analítico (pode usar em NFe) ou sintético
- Forneça contexto hierárquico quando relevante
- Se não encontrar NCM adequado, diga claramente

RESPOSTA:"""

        # 4. Chama sua LLM (ajuste conforme seu modelo)
        try:
            # Exemplo para OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # ou seu modelo local
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )
            return response.choices[0].message.content
            
        except Exception as e:
            # Fallback simples se LLM não disponível
            return f"""
            Baseado nos dados NCM encontrados:
            
            {context}
            
            Para a pergunta: "{user_question}"
            
            Verifique os NCMs listados acima. NCMs analíticos (8 dígitos) podem ser usados em NFe.
            """
    
    def chat_interface(self):
        """Interface de chat simples"""
        print("\\n🤖 SISTEMA RAG NCM - Digite 'sair' para encerrar\\n")
        
        while True:
            question = input("❓ Sua pergunta sobre NCM: ").strip()
            
            if question.lower() in ['sair', 'exit', 'quit']:
                print("👋 Até logo!")
                break
            
            if not question:
                continue
            
            print("🔄 Processando...")
            try:
                response = self.generate_response(question)
                print(f"\\n🎯 **Resposta**:\\n{response}\\n")
                print("-" * 50)
            except Exception as e:
                print(f"❌ Erro: {e}")

def main():
    print("🚀 INICIANDO SISTEMA RAG NCM")
    
    # Inicializa sistema
    rag = NCMRagSystem("http://localhost:8080")  # Ajuste URL
    
    # Carrega dados (só precisa fazer uma vez)
    try:
        rag.load_ncm_data()
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return
    
    # Interface de chat
    rag.chat_interface()

if __name__ == "__main__":
    main()
```

### 3. Como usar o RAG
```bash
# Instala dependências
pip install chromadb sentence-transformers openai

# Executa sistema RAG
python3 ncm_rag_system.py
```

## 🔧 ABORDAGEM 2: FINE-TUNING

### Para modelos OpenAI
```python
import openai
import json

# 1. Prepare dados de treinamento
def prepare_training_data():
    """Converte dados NCM para formato OpenAI"""
    response = requests.get("http://192.168.0.52:8080/api/llm/ncms/export")
    data = response.json()
    
    training_examples = []
    
    for ncm in data['ncms'][:1000]:  # Limite para teste
        # Cria exemplos de pergunta-resposta
        examples = [
            {
                "messages": [
                    {"role": "user", "content": f"O que é NCM {ncm['codigo_formatado']}?"},
                    {"role": "assistant", "content": f"NCM {ncm['codigo_formatado']}: {ncm['descricao']}. É um código {ncm['tipo']} de nível {ncm['nivel']['nome']}. {'Pode ser usado em NFe.' if ncm['pode_receber_lancamento'] else 'Não pode ser usado em NFe (apenas classificação).'}"}
                ]
            },
            {
                "messages": [
                    {"role": "user", "content": f"Qual NCM para {ncm['descricao'].lower()}?"},
                    {"role": "assistant", "content": f"Para {ncm['descricao'].lower()}, use o NCM {ncm['codigo_formatado']}."}
                ]
            }
        ]
        training_examples.extend(examples)
    
    # Salva arquivo de treinamento
    with open('ncm_training.jsonl', 'w') as f:
        for example in training_examples:
            f.write(json.dumps(example) + '\\n')
    
    return 'ncm_training.jsonl'

# 2. Faz upload e fine-tuning
def fine_tune_model():
    # Upload arquivo
    file_response = openai.File.create(
        file=open('ncm_training.jsonl', 'rb'),
        purpose='fine-tune'
    )
    
    # Inicia fine-tuning
    fine_tune_response = openai.FineTune.create(
        training_file=file_response['id'],
        model='gpt-3.5-turbo'
    )
    
    print(f"Fine-tune iniciado: {fine_tune_response['id']}")
    return fine_tune_response['id']
```

## 🎯 ABORDAGEM 3: PROMPT ENGINEERING

### Sistema baseado em prompts
```python
import requests

class NCMPromptSystem:
    def __init__(self, api_url="http://192.168.0.52:8080"):
        self.api_url = api_url
        self.base_prompt = """
Você é um ESPECIALISTA em NCM (Nomenclatura Comum do Mercosul) brasileiro.

REGRAS:
1. NCMs analíticos (8 dígitos) são usados em NFe
2. NCMs sintéticos são apenas para classificação
3. Sempre forneça contexto hierárquico
4. Base oficial: 13.217 NCMs do Siscomex

"""
    
    def get_context_for_query(self, query: str) -> str:
        """Busca contexto relevante via API"""
        response = requests.get(
            f"{self.api_url}/api/llm/ncms/search",
            params={"q": query, "limit": 5}
        )
        
        if response.ok:
            data = response.json()
            context = "DADOS NCM RELEVANTES:\\n"
            
            for ncm in data.get('resultados', []):
                context += f"- {ncm['codigo_formatado']}: {ncm['descricao']} ({ncm['tipo']})\\n"
            
            return context
        
        return "Nenhum dado NCM encontrado."
    
    def generate_prompt(self, user_question: str) -> str:
        """Gera prompt completo com contexto"""
        context = self.get_context_for_query(user_question)
        
        return f"""
{self.base_prompt}

{context}

PERGUNTA: {user_question}

RESPOSTA (seja preciso e técnico):
"""
```

## 🏆 COMPARAÇÃO DAS ABORDAGENS

| Aspecto | RAG | Fine-tuning | Prompt Engineering |
|---------|-----|-------------|-------------------|
| **Facilidade** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Custo** | Baixo | Alto | Muito Baixo |
| **Atualização** | Automática | Manual | Automática |
| **Precisão** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Velocidade** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## 📋 ENDPOINTS DISPONÍVEIS

| Endpoint | Uso | Exemplo |
|----------|-----|---------|
| `/api/llm/ncms/stats` | Estatísticas gerais | Quantos NCMs existem? |
| `/api/llm/ncms/search?q={termo}` | Buscar NCMs | NCM para "notebook" |
| `/api/llm/ncms/hierarquia/{codigo}` | Contexto hierárquico | O que é NCM 01.01.21.00? |
| `/api/llm/ncms/export` | Base completa | Dados para treinamento |
| `/health` | Status da API | Verificar se funciona |

---

## 🧪 TESTES FINAIS

### **Teste 1: Conectividade**
```bash
curl http://192.168.0.52:1234/health
# Deve retornar: {"status": "UP", "total_ncms": 13217}
```

### **Teste 2: Busca**
```bash
curl "http://192.168.0.52:1234/api/llm/ncms/search?q=cavalos&tipo=analitico&limit=3"
# Deve retornar NCMs relacionados a cavalos
```

### **Teste 3: Hierarquia**
```bash
curl http://192.168.0.52:1234/api/llm/ncms/hierarquia/01.01.21.00
# Deve retornar contexto hierárquico completo
```

---

## ✅ CHECKLIST FINAL

- [ ] **Arquivo `api_ncm_standalone.py` copiado** para servidor
- [ ] **Arquivo `ncms_training_data.json` copiado** para servidor  
- [ ] **Flask instalado** no servidor (`pip3 install flask`)
- [ ] **API executando** na porta 1234
- [ ] **Testes passando** (curl funcionando)
- [ ] **LLM integrada** com código NCMExpert
- [ ] **Prompt de sistema** configurado
- [ ] **Funções de busca** implementadas

---

## 🎉 RESULTADO FINAL

**Sua LLM será capaz de:**

✅ **Classificar qualquer produto** com NCM correto  
✅ **Explicar códigos NCM** com contexto hierárquico  
✅ **Validar NCMs** para uso em NFe  
✅ **Responder perguntas fiscais** com precisão  
✅ **Fornecer orientação técnica** sobre classificação  

**Base de conhecimento:**
- 🎯 13.217 NCMs oficiais brasileiros
- 📊 10.507 NCMs analíticos (usáveis em NFe)
- 🏗️ Hierarquia completa de 4 níveis
- 🔄 Dados atualizados do Siscomex

---

## 📞 RESUMO EXECUTIVO

1. **Copie 2 arquivos** para 192.168.0.52
2. **Execute `python3 api_ncm_standalone.py`**
3. **Integre código NCMExpert** na sua LLM
4. **Configure prompt** especialista NCM
5. **Teste** com perguntas reais

**🚀 SUA LLM SERÁ A ESPECIALISTA NCM DEFINITIVA!**

Tempo estimado: **15 minutos** ⏱️  
Resultado: **LLM especialista em classificação fiscal brasileira** 🇧🇷
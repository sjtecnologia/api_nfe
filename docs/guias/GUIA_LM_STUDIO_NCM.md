# 🎯 GUIA: CODELLAMA + NCM PARA LM STUDIO

## 📊 **SUA CONFIGURAÇÃO ATUAL**

✅ **LLM**: CodeLlama-7B-Instruct em `http://192.168.0.52:1234`  
✅ **Gerenciador**: LM Studio 0.3.30  
✅ **API NCM**: Rodando em `http://localhost:8081`

---

## 🤔 **AVALIAÇÃO: CODELLAMA É ADEQUADO?**

### **✅ PODE FUNCIONAR:**
- ✅ Boa com instruções estruturadas
- ✅ Responde em português
- ✅ Já está configurado

### **⚠️ LIMITAÇÕES:**
- ⚠️ **Focado em código**, não dados fiscais
- ⚠️ **Contexto limitado** (4k tokens)
- ⚠️ **Sem conhecimento fiscal brasileiro**

### **🏆 MODELOS MELHORES (RECOMENDADOS):**

1. **Llama-3.1-8B-Instruct** ← **MELHOR OPÇÃO**
2. **Mistral-7B-Instruct-v0.3**
3. **Qwen2.5-7B-Instruct**

---

## 🚀 **SOLUÇÃO SIMPLES (FUNCIONA COM QUALQUER LLM)**

### **1️⃣ CONFIGURAR PROMPT NO LM STUDIO**

No LM Studio, configure este **System Message**:

```
Você é um especialista em NCM (Nomenclatura Comum do Mercosul) brasileiro.

DADOS DISPONÍVEIS:
- 13.217 códigos NCM oficiais do Siscomex
- Base hierárquica completa (4 níveis)
- Classificação: Analíticos (NFe) vs Sintéticos

REGRAS IMPORTANTES:
1. NCMs ANALÍTICOS (8 dígitos) = Usados em NFe
2. NCMs SINTÉTICOS = Apenas classificação hierárquica
3. Sempre forneça contexto hierárquico
4. Seja preciso: erro fiscal tem consequências

FORMATO DE RESPOSTA:
🎯 NCM: [código]
📝 Descrição: [descrição oficial]
✅ Tipo: Analítico/Sintético
📋 Uso em NFe: Sim/Não
💡 Observações: [detalhes importantes]
```

### **2️⃣ EXEMPLOS DE PERGUNTA/RESPOSTA**

**Pergunta**: "Qual NCM para notebook gamer?"

**Resposta da LLM**:
```
🎯 NCM: 84.71.30.29
📝 Descrição: Computadores portáteis com peso não superior a 10 kg
✅ Tipo: Analítico  
📋 Uso em NFe: Sim
💡 Observações: NCM específico para notebooks e laptops, incluindo equipamentos gamer
```

---

## 🛠️ **SCRIPT DE INTEGRAÇÃO SIMPLES**

Crie um arquivo `ncm_consultor.py`:

```python
#!/usr/bin/env python3
"""
Consultor NCM simples para LM Studio
Não precisa de API - funciona offline
"""

import json
import re
from typing import List, Dict

class NCMConsultorSimples:
    def __init__(self):
        self.ncms = []
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega dados NCM do arquivo JSON"""
        try:
            with open('ncms_training_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.ncms = data.get('ncms', [])
                print(f"✅ Carregados {len(self.ncms)} NCMs")
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
    
    def buscar_ncm(self, termo: str, limite: int = 5) -> List[Dict]:
        """Busca NCMs por termo"""
        termo_lower = termo.lower()
        resultados = []
        
        for ncm in self.ncms:
            descricao = ncm.get('descricao', '').lower()
            if termo_lower in descricao:
                score = descricao.count(termo_lower)
                resultados.append({
                    'codigo': ncm.get('codigo', ''),
                    'descricao': ncm.get('descricao', ''),
                    'tipo': ncm.get('tipo_ncm', ''),
                    'score': score
                })
        
        # Ordena por relevância
        resultados.sort(key=lambda x: x['score'], reverse=True)
        return resultados[:limite]
    
    def formatar_resposta(self, produto: str) -> str:
        """Gera resposta formatada para LM Studio"""
        resultados = self.buscar_ncm(produto, limite=3)
        
        if not resultados:
            return f"❌ Nenhum NCM encontrado para '{produto}'"
        
        melhor = resultados[0]
        
        resposta = f"""🎯 **NCM RECOMENDADO PARA "{produto.upper()}"**

📋 **Principal:**
• NCM: {melhor['codigo']}
• Descrição: {melhor['descricao']}
• Tipo: {melhor['tipo']}
• Uso em NFe: {'✅ Sim' if melhor['tipo'] == 'Analítico' else '❌ Não (apenas classificação)'}

"""
        
        if len(resultados) > 1:
            resposta += "🔍 **Alternativas:**\\n"
            for alt in resultados[1:]:
                resposta += f"• {alt['codigo']}: {alt['descricao'][:60]}...\\n"
        
        resposta += """
💡 **IMPORTANTE**: Verifique sempre se o NCM analítico é adequado ao seu produto específico."""
        
        return resposta
    
    def chat_interativo(self):
        """Chat simples para testes"""
        print("\\n🤖 CONSULTOR NCM - Digite 'sair' para encerrar\\n")
        
        while True:
            produto = input("🔍 Produto para classificar: ").strip()
            
            if produto.lower() in ['sair', 'exit']:
                break
            
            if produto:
                resposta = self.formatar_resposta(produto)
                print(f"\\n{resposta}\\n")
                print("-" * 60)

# Teste
if __name__ == "__main__":
    consultor = NCMConsultorSimples()
    consultor.chat_interativo()
```

### **3️⃣ USAR NO LM STUDIO**

1. **Salve o script** como `ncm_consultor.py`
2. **Execute**: `python3 ncm_consultor.py`
3. **Teste** com produtos reais
4. **Copie as respostas** para treinar sua LLM

---

## 📚 **COMO TREINAR O CODELLAMA**

### **Método 1: Exemplos no Chat**

Converse com sua LLM usando estes exemplos:

```
Usuário: Qual NCM para cavalos reprodutores?

Assistente: 🎯 NCM: 01.01.21.00
📝 Descrição: Reprodutores de raça pura
✅ Tipo: Analítico
📋 Uso em NFe: Sim
💡 Observações: NCM específico para cavalos de reprodução com certificado genealógico

Usuário: E para notebooks?

Assistente: 🎯 NCM: 84.71.30.29
📝 Descrição: Computadores portáteis com peso não superior a 10 kg
✅ Tipo: Analítico
📋 Uso em NFe: Sim
💡 Observações: Inclui laptops, notebooks e equipamentos portáteis similares
```

### **Método 2: Prompt com Contexto**

Sempre inclua contexto NCM nas suas perguntas:

```
Com base nestes NCMs:
- 01.01.21.00: Reprodutores de raça pura (Analítico)
- 84.71.30.29: Computadores portáteis ≤ 10kg (Analítico)
- 92.04.91.00: Papel fotográfico (Analítico)

Pergunta: Qual NCM para [seu produto]?
```

---

## 🎯 **SUGESTÃO: TROCAR POR LLAMA-3.1-8B**

### **Por que Llama-3.1-8B é melhor:**

1. **Português nativo** vs CodeLlama (inglês/código)
2. **Contexto 128k** vs CodeLlama (4k tokens)
3. **Raciocínio estruturado** vs CodeLlama (foco código)
4. **Conhecimento geral** vs CodeLlama (apenas programação)

### **Como trocar no LM Studio:**

1. **Procure**: "Meta-Llama-3.1-8B-Instruct"
2. **Baixe**: Versão GGUF Q4_K_M (±4.6GB)
3. **Carregue**: No lugar do CodeLlama
4. **Configure**: Mesmo system prompt

---

## ✅ **TESTE RÁPIDO**

Execute este teste no seu LM Studio:

**System Message**:
```
Você é especialista em NCM brasileiro. NCMs analíticos (8 dígitos) são usados em NFe. Sempre formate: NCM [código] - [descrição] - [Analítico/Sintético]
```

**User Message**:
```
Preciso classificar "papel fotográfico" para NFe. Qual NCM usar?
```

**Resposta esperada**:
```
NCM 92049100 - Papel fotográfico - Analítico
Este NCM pode ser usado em NFe por ser analítico (8 dígitos).
```

---

## 🎉 **RESULTADO FINAL**

Com essa configuração, sua LLM será capaz de:

✅ **Classificar produtos** com NCM correto  
✅ **Distinguir** NCMs analíticos vs sintéticos  
✅ **Orientar** sobre uso em NFe  
✅ **Fornecer contexto** fiscal adequado  

**🚀 EM 15 MINUTOS SUA LLM VIRA ESPECIALISTA NCM!**
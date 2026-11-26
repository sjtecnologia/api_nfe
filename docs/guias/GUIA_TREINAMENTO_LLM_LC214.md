# 🎓 Guia de Treinamento - LLM NCM com Lei Complementar 214/2025

## 📋 Objetivo

Treinar o modelo Llama-3.1-8B rodando em **192.168.0.52:1234** para responder consultas sobre classificação NCM com embasamento legal da **Lei Complementar 214/2025** (Reforma Tributária - IBS e CBS).

---

## 📁 Arquivos Criados

### 1. **dataset_treinamento_ncm_lc214_2025.jsonl**
Dataset de treinamento com 12 exemplos cobrindo:
- ✅ Produtos da Cesta Básica (redução 100%)
- ✅ Alimentos dietéticos para erros inatos do metabolismo
- ✅ Hortifrutigranjeiros
- ✅ Material ferroviário (suspensão)
- ✅ Perfumaria (restrições ZFM)
- ✅ Combustíveis (CIDE)
- ✅ Produtos comuns (tributação padrão)

---

## 🚀 Métodos de Treinamento

### **OPÇÃO 1: Fine-tuning via LM Studio (RECOMENDADO)**

#### Passo 1: Preparar Dataset
O arquivo `dataset_treinamento_ncm_lc214_2025.jsonl` já está no formato correto (JSONL com messages).

#### Passo 2: No LM Studio
1. Abra o **LM Studio**
2. Vá em **Fine-tuning** (ou Training)
3. Selecione o modelo base: **Llama-3.1-8B**
4. Carregue o dataset: `dataset_treinamento_ncm_lc214_2025.jsonl`
5. Configure:
   - **Learning Rate**: 2e-5 (padrão)
   - **Epochs**: 3-5 (comece com 3)
   - **Batch Size**: 4
   - **Max Tokens**: 1024
6. Clique em **Start Training**
7. Aguarde conclusão (pode levar 30min-2h dependendo do hardware)
8. Carregue o modelo treinado no servidor local

---

### **OPÇÃO 2: Fine-tuning via Python (Avançado)**

Se preferir fazer via código Python:

```bash
# 1. Instalar dependências
pip install torch transformers datasets peft accelerate bitsandbytes

# 2. Executar script de treinamento (criar o arquivo abaixo)
python treinar_llm_ncm_lc214.py
```

#### Script: `treinar_llm_ncm_lc214.py`

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import json

# Configurações
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"  # ou caminho local
OUTPUT_DIR = "./llm_ncm_lc214_trained"
DATASET_FILE = "dataset_treinamento_ncm_lc214_2025.jsonl"

# 1. Carregar modelo e tokenizer
print("🔄 Carregando modelo base...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    load_in_8bit=True,  # Quantização para economizar memória
    device_map="auto",
    torch_dtype=torch.float16
)

# 2. Configurar LoRA (Low-Rank Adaptation)
print("⚙️ Configurando LoRA...")
lora_config = LoraConfig(
    r=16,  # Rank
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, lora_config)

# 3. Carregar e processar dataset
print("📚 Carregando dataset...")
dataset = load_dataset("json", data_files=DATASET_FILE)

def format_dataset(example):
    """Formata os dados no formato de chat do Llama"""
    messages = example["messages"]
    text = tokenizer.apply_chat_template(messages, tokenize=False)
    return {"text": text}

tokenized_dataset = dataset.map(format_dataset)

# 4. Configurar treinamento
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-5,
    logging_steps=10,
    save_steps=50,
    warmup_steps=10,
    fp16=True,
    optim="paged_adamw_8bit"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    tokenizer=tokenizer
)

# 5. Treinar
print("🎓 Iniciando treinamento...")
trainer.train()

# 6. Salvar modelo treinado
print("💾 Salvando modelo...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("✅ Treinamento concluído!")
print(f"📁 Modelo salvo em: {OUTPUT_DIR}")
```

---

### **OPÇÃO 3: Prompt Engineering (SEM Fine-tuning)**

Se não quiser fazer fine-tuning, pode melhorar as respostas via **System Prompt aprimorado**:

```python
# Já implementado em servico_sugestao_ia.py
# O system prompt já contém informações da LC 214/2025
```

**Vantagens:**
- ✅ Não requer treinamento
- ✅ Mudanças imediatas
- ✅ Mais fácil de atualizar

**Desvantagens:**
- ⚠️ Menos preciso que fine-tuning
- ⚠️ Depende do tamanho do contexto

---

## 📊 Testar o Modelo Treinado

### Teste 1: Produto da Cesta Básica

```bash
curl -X POST http://192.168.0.52:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-ncm-lc214",
    "messages": [
      {
        "role": "system",
        "content": "Você é um especialista em classificação tributária NCM com conhecimento da LC 214/2025."
      },
      {
        "role": "user",
        "content": "Classifique: Café torrado em grãos. NCM disponível: 09.01.21.10. Forneça embasamento da LC 214/2025."
      }
    ],
    "max_tokens": 500,
    "temperature": 0.1
  }'
```

**Resposta Esperada:**
```json
{
  "ncm": "09012110",
  "cfop": "5101",
  "csosn": "101",
  "explicacao": "Café torrado em grão - NCM 09.01.21.10. EMBASAMENTO LEGAL LC 214/2025: Produto do Anexo I (Cesta Básica) com REDUÇÃO DE 100% das alíquotas do IBS e CBS..."
}
```

### Teste 2: Produto com Restrição

```bash
curl -X POST http://192.168.0.52:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-ncm-lc214",
    "messages": [
      {
        "role": "user",
        "content": "Classifique: Perfume importado. NCM: 33.03.00.10. Cite LC 214/2025."
      }
    ]
  }'
```

**Resposta Esperada:**
```json
{
  "ncm": "33030010",
  "explicacao": "...RESTRIÇÃO ESPECIAL para ZFM. Art. 381, alínea 'f': vedação à apropriação de créditos..."
}
```

---

## 🔧 Integração com o Sistema

O sistema já está preparado para usar a LLM treinada. No arquivo `servico_sugestao_ia.py`:

```python
# Linha 37-38
def __init__(self, 
             ncm_api_url: str = "http://localhost:8081",
             llm_url: str = "http://192.168.0.52:1234"):  # ← Já configurado
```

Após treinar, basta:
1. Carregar o modelo treinado no LM Studio
2. Iniciar o servidor local na porta 1234
3. O sistema usará automaticamente a LLM aprimorada

---

## 📈 Expandir o Treinamento

Para adicionar mais exemplos ao dataset:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Você é um especialista em classificação tributária NCM com conhecimento da LC 214/2025."
    },
    {
      "role": "user",
      "content": "Produto: [DESCRIÇÃO]\n\nDados NCM:\n**NCM XX.XX.XX.XX** - [Descrição]\n\nClassifique com embasamento LC 214/2025."
    },
    {
      "role": "assistant",
      "content": "{JSON com explicação detalhada e artigos da lei}"
    }
  ]
}
```

### Produtos Prioritários para Adicionar:

1. **Medicamentos** (Anexo IV - redução 60%)
2. **Dispositivos médicos** (Anexo V - redução 60%)
3. **Produtos de higiene** (Anexo VIII - redução 60%)
4. **Serviços de educação** (Anexo II - redução 60%)
5. **Serviços de saúde** (Anexo III - redução 60%)
6. **Combustíveis** (regime específico)
7. **Bebidas alcoólicas** (regime específico)
8. **Cigarros** (regime específico)

---

## ✅ Checklist de Implementação

- [x] Dataset de treinamento criado (12 exemplos)
- [x] System prompt atualizado com LC 214/2025
- [x] Integração com LLM configurada
- [ ] Fine-tuning executado (escolher OPÇÃO 1 ou 2)
- [ ] Testes de validação realizados
- [ ] Modelo em produção no servidor

---

## 📚 Referências Legais

- **Lei Complementar 214/2025**: Institui IBS e CBS
- **Resolução Gecex 272/2021**: NCM/SH vigente
- **Artigos-chave**:
  - Art. 2º: Princípio da neutralidade
  - Art. 8º e 9º: Imunidades e isenções
  - Art. 12-13: Base de cálculo
  - Art. 14-20: Alíquotas
  - Art. 119: Suspensão (material ferroviário)
  - Art. 381: Restrições ZFM
  - Art. 492: Nomenclatura NCM/SH
  - Anexos I, II, III, IV, V, VIII, XV: Benefícios fiscais

---

## 🎯 Próximos Passos

1. **Executar fine-tuning** usando LM Studio (mais fácil) ou Python script
2. **Testar modelo** com produtos reais
3. **Validar respostas** comparando com lei original
4. **Expandir dataset** com mais 50-100 exemplos
5. **Re-treinar** periodicamente quando houver atualizações na lei
6. **Monitorar acurácia** das classificações

---

**Criado em:** 19/11/2025  
**Versão:** 1.0  
**Status:** ✅ Pronto para treinamento

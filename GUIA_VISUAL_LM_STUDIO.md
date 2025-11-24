# 🎓 GUIA VISUAL - Treinamento no LM Studio

## 📍 Localização dos Arquivos

**Dataset pronto para uso:**
```
/Users/renato/Documents/Developement/api_nfe/dataset_treinamento_ncm_lc214_2025.jsonl
```

---

## 🚀 PASSO A PASSO NO LM STUDIO

### 1️⃣ Abrir a Aba de Fine-tuning

```
LM Studio (aplicativo aberto)
├── 🏠 Home
├── 🔍 Search
├── 💬 Chat
├── 🖥️ Local Server (você está aqui agora)
└── 🎓 Fine-tuning  ← CLIQUE AQUI
```

**O que fazer:**
- No menu lateral esquerdo do LM Studio
- Clique no ícone que parece um "certificado" ou "diploma"
- Pode estar escrito "Fine-tuning" ou "LoRA"

---

### 2️⃣ Selecionar o Modelo Base

**Tela: "Select Base Model"**

```
┌─────────────────────────────────────────┐
│ Base Model: [Select Model ▼]           │
└─────────────────────────────────────────┘
```

**O que fazer:**
- Clique no dropdown "Select Model"
- Procure por: `meta-llama-3.1-8b-instruct`
- Ou: `llama-3.1-8b-instruct`
- Ou: O modelo que você está usando no servidor (porta 1234)
- Selecione o modelo

**💡 Dica:** Use o MESMO modelo que está rodando no servidor!

---

### 3️⃣ Carregar o Dataset

**Tela: "Load Dataset"**

```
┌─────────────────────────────────────────┐
│ Dataset File: [Select File...] 📁      │
└─────────────────────────────────────────┘
```

**O que fazer:**
1. Clique em "Select File..." ou "Browse" ou ícone 📁
2. Navegue até: `/Users/renato/Documents/Developement/api_nfe/`
3. Selecione: `dataset_treinamento_ncm_lc214_2025.jsonl`
4. Clique "Open" ou "Abrir"

**✅ Confirmação:**
- O LM Studio deve mostrar: "12 examples loaded" ou similar
- Pode mostrar preview dos dados

---

### 4️⃣ Configurar Hiperparâmetros

**Tela: "Training Configuration"**

```
┌─────────────────────────────────────────┐
│ Learning Rate:    [0.00002        ]     │
│ Epochs:           [3              ]     │
│ Batch Size:       [4              ]     │
│ Max Length:       [1024           ]     │
│                                         │
│ Advanced Settings (opcional)            │
│ ├─ LoRA Rank (r):      [16]            │
│ ├─ LoRA Alpha:         [32]            │
│ └─ LoRA Dropout:       [0.05]          │
└─────────────────────────────────────────┘
```

**Configure assim:**

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| **Learning Rate** | `0.00002` ou `2e-5` | Taxa de aprendizado |
| **Epochs** | `3` | Quantas vezes treina todo dataset |
| **Batch Size** | `4` | Exemplos por iteração |
| **Max Length** | `1024` | Tamanho máximo do texto |
| **LoRA Rank (r)** | `16` | Tamanho da adaptação |
| **LoRA Alpha** | `32` | Escala da adaptação |
| **LoRA Dropout** | `0.05` | Regularização |

**💡 Dica:** Se o LM Studio travar ou ficar lento:
- Reduza Batch Size para `2`
- Reduza Max Length para `512`

---

### 5️⃣ Iniciar o Treinamento

**Botão grande:**

```
┌─────────────────────────────────────────┐
│                                         │
│      [🚀 Start Fine-tuning]            │
│                                         │
└─────────────────────────────────────────┘
```

**O que fazer:**
1. Revise as configurações
2. Clique no botão "Start Fine-tuning" ou "Train"
3. **Aguarde!**

**⏱️ Tempo estimado:**
- Mac M1/M2/M3: 30 minutos - 1 hora
- Mac Intel: 1-2 horas
- Depende da GPU/CPU disponível

---

### 6️⃣ Monitorar o Progresso

**Durante o treinamento, você verá:**

```
┌─────────────────────────────────────────┐
│ Training Progress                       │
│ ████████░░░░░░░░░░░░░ 40%              │
│                                         │
│ Epoch: 2/3                              │
│ Loss: 0.342                             │
│ Time Elapsed: 15m 23s                   │
│ Estimated Remaining: 23m 10s            │
│                                         │
│ [📊 Loss Graph]                         │
│     ╱╲                                  │
│    ╱  ╲                                 │
│   ╱    ╲___                             │
│  ╱         ╲___                         │
│ ╱              ╲___                     │
└─────────────────────────────────────────┘
```

**O que observar:**
- ✅ **Loss diminuindo:** Está aprendendo!
- ⚠️ **Loss aumentando:** Pode estar overfitting
- ❌ **Erro/Crash:** Tente reduzir batch size

**💡 Dica:** Deixe o Mac conectado na energia e não feche o LM Studio!

---

### 7️⃣ Treinamento Concluído

**Tela de sucesso:**

```
┌─────────────────────────────────────────┐
│ ✅ Training Complete!                   │
│                                         │
│ Model saved to:                         │
│ ~/LMStudio/models/fine-tuned/           │
│ llama-3.1-8b-lc214-2025/                │
│                                         │
│ Final Loss: 0.089                       │
│ Total Time: 45m 18s                     │
│                                         │
│ [Load in Chat] [Load in Server]        │
└─────────────────────────────────────────┘
```

**O que fazer:**
1. Clique em **"Load in Server"** (Carregar no Servidor)
2. Ou vá manualmente para a aba "Local Server"

---

### 8️⃣ Carregar Modelo Treinado no Servidor

**Aba: Local Server**

```
┌─────────────────────────────────────────┐
│ Select Model to Load:                   │
│                                         │
│ ( ) meta-llama-3.1-8b-instruct (base)  │
│ (•) llama-3.1-8b-lc214-2025 (fine-tuned) ← ESTE!
│                                         │
│ Port: [1234]                            │
│                                         │
│ [🚀 Start Server]                       │
└─────────────────────────────────────────┘
```

**O que fazer:**
1. Selecione o modelo **treinado** (fine-tuned)
2. Mantenha porta **1234**
3. Clique "Start Server"
4. Aguarde "Server Running" aparecer

---

### 9️⃣ Testar o Modelo Treinado

**No terminal:**

```bash
cd /Users/renato/Documents/Developement/api_nfe
source venv/bin/activate
python3 teste_rapido_llm.py
```

**Resultado esperado:**

```
🧪 TESTE RÁPIDO - Café (Cesta Básica)
============================================================

✅ RESPOSTA DA LLM:
------------------------------------------------------------
{
  "ncm": "09012110",
  "cfop": "5101",
  "csosn": "101",
  "explicacao": "Café torrado em grão - NCM 09.01.21.10. 
  
  EMBASAMENTO LEGAL LC 214/2025: 
  Produto enquadrado no Anexo I (Cesta Básica Nacional) com 
  REDUÇÃO DE 100% das alíquotas do IBS e CBS (Art. 8º - isenção). 
  
  A Posição 09.01 da NCM/SH é especificamente mencionada no 
  item 8 do Anexo I. A classificação NCM/SH está conforme 
  Resolução Gecex nº 272/2021 (Art. 492, LC 214/2025)."
}
------------------------------------------------------------

📊 ANÁLISE:
   ✅ NCM correto (09012110): SIM
   📚 Cita LC 214/2025: SIM
   📄 Cita artigos/anexos: SIM

🎉 LLM fornece embasamento legal completo!
```

---

## 🎯 COMPARAÇÃO: ANTES vs DEPOIS

### ❌ ANTES (Testamos às 07:46)
```json
{
  "ncm": "09012110",
  "beneficios_lc_214": false,  ← ERRADO!
  "artigos_aplicaveis": []     ← ERRADO!
}
```
"A Lei Complementar 214/2025 não menciona benefícios..." ← **INCORRETO**

### ✅ DEPOIS (Após treinamento)
```json
{
  "ncm": "09012110",
  "explicacao": "...EMBASAMENTO LEGAL LC 214/2025: 
  Produto enquadrado no Anexo I (Cesta Básica) com 
  REDUÇÃO DE 100%...Art. 8º...Posição 09.01..." ← **CORRETO!**
}
```

---

## 🎓 RESUMO DOS PASSOS

```
1. LM Studio → Aba "Fine-tuning"
2. Selecionar modelo: meta-llama-3.1-8b-instruct
3. Carregar dataset: dataset_treinamento_ncm_lc214_2025.jsonl
4. Configurar: LR=0.00002, Epochs=3, Batch=4
5. Clicar "Start Fine-tuning"
6. Aguardar 30min-2h
7. Carregar modelo treinado no servidor (porta 1234)
8. Testar: python3 teste_rapido_llm.py
9. Comparar resultados!
```

---

## ⚠️ TROUBLESHOOTING

### Problema: "Out of Memory"
**Solução:**
- Reduza Batch Size para `2`
- Reduza Max Length para `512`
- Feche outros aplicativos

### Problema: "Training muito lento"
**Solução:**
- Normal em CPU (pode levar 2h)
- Use Mac com GPU (M1/M2/M3 é mais rápido)
- Reduza Epochs para `2`

### Problema: "Loss não diminui"
**Solução:**
- Aumente Learning Rate para `0.0001`
- Ou aumente Epochs para `5`
- Dataset pode precisar de mais exemplos

### Problema: "Modelo não aparece após treino"
**Solução:**
- Verifique pasta: `~/LMStudio/models/fine-tuned/`
- Reinicie o LM Studio
- Recarregue a aba "Local Server"

---

## 📚 ARQUIVOS RELACIONADOS

- 📊 Dataset: `dataset_treinamento_ncm_lc214_2025.jsonl` (12 exemplos)
- 📖 Guia completo: `GUIA_TREINAMENTO_LLM_LC214.md`
- 🧪 Teste: `teste_rapido_llm.py`
- 📋 Lei: `lei_complementar_214_2025_dados_estruturados.json`
- 📈 Resultado antes: `RESULTADO_TESTE_ANTES_TREINAMENTO.md`

---

## ✅ CHECKLIST

- [ ] LM Studio aberto
- [ ] Aba Fine-tuning selecionada
- [ ] Modelo base carregado
- [ ] Dataset carregado (12 examples)
- [ ] Hiperparâmetros configurados
- [ ] Treinamento iniciado
- [ ] Aguardando conclusão (30min-2h)
- [ ] Modelo treinado carregado no servidor
- [ ] Teste executado
- [ ] Resultados comparados

---

**Pronto para começar! 🚀**

Qualquer dúvida durante o processo, me avise!

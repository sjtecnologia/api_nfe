# ⚠️ AVISO: Python 3.13 e PyTorch

## 🔴 Problema Identificado

**PyTorch ainda não tem suporte oficial para Python 3.13**

Seu ambiente:
- Python: 3.13.7
- PyTorch: Não disponível para esta versão

## ✅ SOLUÇÃO RECOMENDADA: Use LM Studio

O LM Studio é **MUITO MAIS FÁCIL** e não depende do Python:

### 📋 Passo a Passo - LM Studio

1. **Abra o LM Studio** (já está rodando o servidor)

2. **Vá na aba "Fine-tuning"**
   - No menu lateral esquerdo, clique em "Fine-tuning"

3. **Configure o treinamento:**
   - **Base Model:** Selecione `meta-llama-3.1-8b-instruct` (o modelo já carregado)
   - **Dataset:** Clique em "Select dataset file"
     - Navegue até: `/Users/renato/Documents/Developement/api_nfe/`
     - Selecione: `dataset_treinamento_ncm_lc214_2025.jsonl`

4. **Ajuste os parâmetros:**
   ```
   Learning Rate: 0.00002 (ou 2e-5)
   Epochs: 3
   Batch Size: 4
   Max Sequence Length: 1024
   LoRA Rank (r): 16
   LoRA Alpha: 32
   ```

5. **Inicie o treinamento:**
   - Clique em "Start Fine-tuning"
   - Aguarde 30min-2h (depende do hardware)
   - O LM Studio mostrará o progresso

6. **Teste o modelo treinado:**
   - Após o treinamento, vá em "Local Server"
   - Carregue o modelo treinado
   - Start Server (porta 1234)
   - Execute: `python3 teste_rapido_llm.py`

---

## 🔧 ALTERNATIVA: Instalar PyTorch Nightly (NÃO RECOMENDADO)

Se REALMENTE quiser usar o script Python:

```bash
# Instalar PyTorch nightly (versão de desenvolvimento)
source venv/bin/activate
pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu

# Instalar outras dependências
pip3 install transformers datasets peft accelerate bitsandbytes

# Executar treinamento
python3 treinar_llm_ncm_lc214.py
```

**⚠️ Avisos:**
- Versão nightly pode ser instável
- Requer download grande (~2GB)
- CPU training é 10-20x mais lento que GPU
- **LM Studio é MUITO mais fácil**

---

## 🎯 POR QUE LM STUDIO É MELHOR?

| Aspecto | LM Studio | Python Script |
|---------|-----------|---------------|
| **Instalação** | ✅ Já instalado | ❌ Depende PyTorch 3.13 |
| **Interface** | ✅ GUI amigável | ⚠️ Linha de comando |
| **Velocidade** | ✅ Otimizado | ⚠️ Depende do hardware |
| **Monitoramento** | ✅ Gráficos em tempo real | ⚠️ Apenas texto |
| **Facilidade** | ✅ Clique e pronto | ⚠️ Configuração manual |
| **Erros** | ✅ Menos problemas | ⚠️ Mais dependências |

---

## 📊 DEPOIS DO TREINAMENTO

Execute o teste para comparar:

```bash
# Antes (já testamos - 0% de embasamento legal)
python3 teste_rapido_llm.py

# Depois do treinamento (esperado: 80-100%)
python3 teste_rapido_llm.py
```

**Resultado esperado:**
```json
{
  "ncm": "09012110",
  "explicacao": "Café torrado em grão - NCM 09.01.21.10. 
  EMBASAMENTO LEGAL LC 214/2025: Produto enquadrado no Anexo I 
  (Cesta Básica Nacional) com REDUÇÃO DE 100% das alíquotas do 
  IBS e CBS (Art. 8º). Posição 09.01 da NCM/SH especificamente 
  mencionada no item 8 do Anexo I..."
}
```

---

## 🎓 DECISÃO FINAL

### ✅ RECOMENDADO: LM Studio
- Abra LM Studio → Fine-tuning
- Carregue `dataset_treinamento_ncm_lc214_2025.jsonl`
- Start Training
- **Pronto!**

### ⚠️ NÃO RECOMENDADO: Python Script
- Requer PyTorch nightly (instável)
- Mais complexo
- Mais lento em CPU
- Mais propenso a erros

---

## 📚 Arquivos Prontos

Todos os arquivos estão criados e prontos:
- ✅ `dataset_treinamento_ncm_lc214_2025.jsonl` - 12 exemplos
- ✅ `GUIA_TREINAMENTO_LLM_LC214.md` - Guia completo
- ✅ `treinar_llm_ncm_lc214.py` - Script Python (requer PyTorch)
- ✅ `teste_rapido_llm.py` - Teste antes/depois
- ✅ `RESULTADO_TESTE_ANTES_TREINAMENTO.md` - Análise do teste

**Tudo pronto para treinar via LM Studio! 🚀**

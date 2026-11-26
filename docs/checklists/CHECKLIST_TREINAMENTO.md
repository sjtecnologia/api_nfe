# 🔧 Checklist - Preparação para Treinamento

## ❌ PROBLEMA IDENTIFICADO

O servidor LLM em `http://192.168.0.52:1234` está **offline ou não respondendo**.

## ✅ PASSO A PASSO PARA RESOLVER

### 1️⃣ Verificar se LM Studio está rodando

```bash
# Teste de conectividade
curl http://192.168.0.52:1234/health

# Se falhar:
# ❌ Servidor offline
# ✅ Se funcionar: retorna algo como {"status": "ok"}
```

### 2️⃣ Iniciar LM Studio

**Opção A - LM Studio GUI:**
1. Abra o aplicativo LM Studio
2. Vá em "Local Server" (servidor local)
3. Carregue o modelo Llama-3.1-8B-Instruct
4. Clique em "Start Server"
5. Verifique se está na porta 1234

**Opção B - Linha de comando:**
```bash
# Se tiver lm-studio CLI instalado
lm-studio server start --port 1234
```

### 3️⃣ Testar Conexão

```bash
# Teste simples
python3 -c "
import requests
try:
    r = requests.post('http://192.168.0.52:1234/v1/chat/completions', 
                     json={'messages': [{'role': 'user', 'content': 'oi'}], 'max_tokens': 10},
                     timeout=10)
    print('✅ LLM respondendo!')
    print(r.json())
except Exception as e:
    print(f'❌ Erro: {e}')
"
```

### 4️⃣ Executar Teste Rápido

```bash
# Depois que LM Studio estiver rodando:
python3 teste_rapido_llm.py
```

### 5️⃣ Executar Treinamento

**Opção A - LM Studio (Recomendado):**
```
1. Abra LM Studio
2. Aba "Fine-tuning"
3. Selecione modelo base: Llama-3.1-8B-Instruct
4. Carregue: dataset_treinamento_ncm_lc214_2025.jsonl
5. Configure:
   - Epochs: 3
   - Learning rate: 0.00002
   - Batch size: 4
6. Clique "Start Training"
7. Aguarde 30min-2h
8. Carregue modelo treinado no servidor
```

**Opção B - Python Script:**
```bash
# Requer GPU com 8GB+ VRAM
python3 treinar_llm_ncm_lc214.py
```

## 📊 RESULTADO ESPERADO

### ANTES do Treinamento:
```json
{
  "ncm": "09012110",
  "cfop": "5101",
  "explicacao": "Café torrado em grãos. NCM 09.01.21.10."
}
```
❌ **SEM embasamento legal da LC 214/2025**

### DEPOIS do Treinamento:
```json
{
  "ncm": "09012110",
  "cfop": "5101",
  "csosn": "101",
  "explicacao": "Café torrado em grão - NCM 09.01.21.10. EMBASAMENTO LEGAL LC 214/2025: Produto enquadrado no Anexo I (Cesta Básica Nacional) com REDUÇÃO DE 100% das alíquotas do IBS e CBS (Art. 8º - isenção). Posição 09.01 da NCM/SH especificamente mencionada no item 8 do Anexo I. A classificação NCM/SH está conforme Resolução Gecex nº 272/2021 (Art. 492, LC 214/2025)."
}
```
✅ **COM embasamento legal completo**

## 🎯 PRÓXIMOS PASSOS

1. [ ] Iniciar LM Studio
2. [ ] Verificar servidor na porta 1234
3. [ ] Executar `python3 teste_rapido_llm.py`
4. [ ] Se teste OK → Executar treinamento
5. [ ] Testar novamente após treinamento
6. [ ] Comparar resultados

## 💡 IMPORTANTE

- **IP Correto?** Verifique se 192.168.0.52 é o IP do servidor LLM
- **Firewall?** Porta 1234 pode estar bloqueada
- **Modelo carregado?** LM Studio precisa ter um modelo ativo
- **Memória?** Llama-3.1-8B precisa de ~8GB RAM

## 🔍 TROUBLESHOOTING

### Erro: Connection Refused
- LM Studio não está rodando
- Porta 1234 não está aberta
- IP incorreto

### Erro: Timeout
- Modelo muito grande para o hardware
- Servidor sobrecarregado
- Aumente o timeout no script

### Erro: 404 Not Found
- Endpoint errado
- Verifique: `/v1/chat/completions`
- Modelo não carregado no servidor

## 📚 REFERÊNCIAS

- Dataset: `dataset_treinamento_ncm_lc214_2025.jsonl`
- Guia completo: `GUIA_TREINAMENTO_LLM_LC214.md`
- Script de treino: `treinar_llm_ncm_lc214.py`
- Lei: `lei_complementar_214_2025_dados_estruturados.json`

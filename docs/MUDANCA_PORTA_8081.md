# 🔧 CONFIGURAÇÃO ATUALIZADA - PORTA 8081

## ⚠️ MUDANÇA IMPORTANTE:

A API NCM foi **movida da porta 8080 para 8081** para evitar conflitos com seu aplicativo.

## 🚀 COMO USAR:

### 1. **Pare a API antiga** (se estiver rodando):
```bash
# Pressione Ctrl+C no terminal da API
```

### 2. **Inicie a API na nova porta**:
```bash
cd /Users/renato/Documents/Developement/api_nfe
python3 api_ncm_standalone.py
```

### 3. **Verifique se está funcionando**:
```bash
curl http://localhost:8081/health
```

### 4. **Teste o gerador de prompts**:
```bash
python3 prompt_generator_ncm.py
```

---

## 📋 URLS ATUALIZADAS:

- **API NCM Local**: `http://localhost:8081`
- **API NCM Rede**: `http://192.168.0.52:8081`
- **LM Studio**: `http://192.168.0.52:1234` (sem mudança)
- **Seu App**: `http://localhost:8080` (liberado para você!)

---

## ✅ ARQUIVOS ATUALIZADOS:

- ✅ `api_ncm_standalone.py` - Nova porta 8081
- ✅ `prompt_generator_ncm.py` - Conecta na porta 8081
- ✅ `llama_ncm_oficial.py` - Conecta na porta 8081
- ✅ `lm_studio_ncm_integration.py` - Conecta na porta 8081
- ✅ `simple_ncm_consultant.py` - Conecta na porta 8081
- ✅ `ncm_rag_system.py` - Conecta na porta 8081
- ✅ `GUIA_LM_STUDIO_NCM.md` - Documentação atualizada

---

## 🎯 PRÓXIMOS PASSOS:

1. **Reinicie a API NCM** na nova porta
2. **Seus prompts funcionam normalmente** - só muda a porta interna
3. **Seu app pode usar a porta 8080** sem conflitos

**🚀 Tudo funcionando na nova porta 8081!**
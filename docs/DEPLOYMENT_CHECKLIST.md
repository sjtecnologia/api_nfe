# 🚀 CHECKLIST DE DEPLOY - API NCM PARA LLM

## 📁 ARQUIVOS NECESSÁRIOS

### **1. Arquivo Principal**
- [x] `api_ncm_standalone.py` (API Flask completa)
  - **Tamanho:** ~8KB
  - **Função:** Servidor API especializado em NCMs
  - **Porta:** 1234 (configurada para sua LLM)

### **2. Base de Dados**  
- [x] `ncms_training_data.json` (Base NCM completa)
  - **Tamanho:** 17.8MB
  - **Registros:** 13.217 NCMs oficiais
  - **Formato:** JSON estruturado do Siscomex

---

## 🛠️ PRÉ-REQUISITOS NO SERVIDOR

```bash
# 1. Python 3.7+ instalado
python3 --version

# 2. Flask instalado
pip3 install flask

# 3. Porta 1234 disponível
netstat -an | grep :1234
```

---

## 📋 PASSO A PASSO

### **ETAPA 1: Copiar Arquivos**
```bash
# No servidor 192.168.0.52
mkdir -p /opt/ncm-api
cd /opt/ncm-api

# Copiar os 2 arquivos:
# - api_ncm_standalone.py
# - ncms_training_data.json
```

### **ETAPA 2: Executar API**
```bash
cd /opt/ncm-api
python3 api_ncm_standalone.py
```

### **ETAPA 3: Verificar Status**
```bash
# Teste de conectividade
curl http://localhost:1234/health

# Resposta esperada:
{
  "status": "UP",
  "ncms_loaded": true,
  "total_ncms": 13217,
  "memory_usage": "18.3MB"
}
```

---

## 🧪 TESTES DE VALIDAÇÃO

### **✅ Teste 1: Health Check**
```bash
curl http://192.168.0.52:1234/health
```
**Resultado esperado:** Status UP com 13.217 NCMs

### **✅ Teste 2: Busca Simples**
```bash
curl "http://192.168.0.52:1234/api/llm/ncms/search?q=notebook&limit=3"
```
**Resultado esperado:** Lista de NCMs para notebooks

### **✅ Teste 3: Hierarquia**
```bash
curl http://192.168.0.52:1234/api/llm/ncms/hierarquia/84.71.30.29
```
**Resultado esperado:** Contexto hierárquico completo

### **✅ Teste 4: Estatísticas**
```bash
curl http://192.168.0.52:1234/api/llm/ncms/stats
```
**Resultado esperado:** Resumo com totais por tipo

---

## 🔧 INTEGRAÇÃO COM SUA LLM

### **Código de Integração:**
```python
class NCMExpert:
    def __init__(self):
        self.api_base = "http://192.168.0.52:1234"
    
    def buscar_ncm(self, produto):
        """Busca NCM para produto"""
        response = requests.get(f"{self.api_base}/api/llm/ncms/search", 
                              params={"q": produto, "tipo": "analitico", "limit": 5})
        return response.json()
    
    def explicar_ncm(self, codigo):
        """Explica código NCM com contexto"""
        response = requests.get(f"{self.api_base}/api/llm/ncms/hierarquia/{codigo}")
        return response.json()
```

---

## 📊 STATUS DE IMPLEMENTAÇÃO

| Componente | Status | Detalhes |
|------------|---------|----------|
| 🎯 API Core | ✅ Completo | Todos endpoints funcionais |
| 📦 Base NCM | ✅ Completo | 13.217 códigos carregados |
| 🔍 Busca | ✅ Completo | Algoritmo otimizado |
| 🏗️ Hierarquia | ✅ Completo | 4 níveis estruturados |
| 🧪 Testes | ✅ Completo | Validação total |
| 📚 Docs | ✅ Completo | Guias detalhados |

---

## ⚡ PERFORMANCE ESPERADA

- **Startup:** 2-3 segundos (carregamento JSON)
- **Busca:** < 50ms por consulta
- **Memória:** ~20MB RAM
- **CPU:** Mínimo (idle 0.1%)
- **Rede:** Apenas requisições HTTP

---

## 🚨 SOLUÇÃO DE PROBLEMAS

### **Problema: Porta ocupada**
```bash
# Verificar processo usando porta 1234
lsof -i :1234

# Matar processo se necessário
kill -9 <PID>
```

### **Problema: JSON não carrega**
```bash
# Verificar tamanho do arquivo
ls -lh ncms_training_data.json

# Deve mostrar ~18MB
```

### **Problema: Import Error**
```bash
# Instalar Flask
pip3 install flask

# Ou usar pip se Python 3 for padrão
pip install flask
```

---

## 🎉 SUCESSO FINAL

**Se todos os testes passaram:**

✅ **API funcionando** na porta 1234  
✅ **13.217 NCMs** carregados  
✅ **Busca otimizada** operacional  
✅ **Hierarquia completa** disponível  
✅ **Pronto para integração** com sua LLM  

---

## 📞 PRÓXIMO PASSO

**INTEGRE com sua LLM usando:**
1. **Código NCMExpert** fornecido
2. **Prompt especialista** em classificação fiscal
3. **Funções de busca** nos endpoints da API
4. **Teste com perguntas reais** de classificação

**🚀 SUA LLM SERÁ A ESPECIALISTA NCM DEFINITIVA!**

**Tempo total de deploy:** 5-10 minutos ⏱️  
**Complexidade:** Baixa 🟢  
**Resultado:** LLM especialista fiscal 🇧🇷
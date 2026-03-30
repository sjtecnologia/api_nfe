# 🚀 GUIA DE IMPLANTAÇÃO: API NCM no Servidor da LLM

## 📋 Situação Atual

✅ **API criada** - Todos os endpoints NCM estão prontos  
✅ **Scripts de teste** - Configurados para porta 1234  
❌ **API não implantada** - Precisa ser configurada no servidor 192.168.0.52:1234  

## 🛠️ PASSOS PARA IMPLANTAR

### 1. Preparar Arquivos no Servidor

Copie estes arquivos para o servidor `192.168.0.52`:

```bash
# Arquivos essenciais da API NCM
routes/llm_api_routes.py           # ← API principal com endpoints
database/connection.py             # ← Conexão com PostgreSQL  
config/settings.py                 # ← Configurações
app.py                            # ← Aplicação Flask principal

# Dados NCM
ncms_training_data.json           # ← Base completa (17.8 MB)
Tabela_NCM_Vigente_20251029.json  # ← Dados originais Siscomex

# Scripts de teste
teste_api_llm.py                  # ← Para testar se funcionou
exemplo_treinamento_llm.py        # ← Exemplos para sua LLM
```

### 2. Instalar Dependências

No servidor da LLM:
```bash
# Instalar Python e dependências
pip install flask sqlalchemy psycopg2-binary requests

# Ou se tiver requirements.txt:
pip install -r requirements.txt
```

### 3. Configurar Banco de Dados

**Opção A: Usar PostgreSQL existente**
```python
# Em config/settings.py ajustar:
DATABASE_CONFIG = {
    'host': 'localhost',  # ou IP do seu PostgreSQL
    'database': 'sua_base_ncm',
    'user': 'seu_usuario',
    'password': 'sua_senha',
    'port': 5432
}
```

**Opção B: Criar base NCM separada**
```sql
-- Criar tabela NCM
CREATE TABLE ncms (
    ncm_id SERIAL PRIMARY KEY,
    codigo VARCHAR(8) NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    tipo VARCHAR(20) DEFAULT 'analitico',
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fonte_atualizacao VARCHAR(50) DEFAULT 'siscomex'
);
```

### 4. Carregar Dados NCM

Execute uma vez para carregar os 13.217 NCMs:

```python
# Script para carregar dados (execute uma vez)
import json
import psycopg2

def carregar_ncms():
    # Conectar no banco
    conn = psycopg2.connect(
        host="localhost",
        database="sua_base",
        user="usuario", 
        password="senha"
    )
    
    # Carregar dados do JSON
    with open('ncms_training_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Inserir NCMs
    cursor = conn.cursor()
    for ncm in data['ncms']:
        cursor.execute("""
            INSERT INTO ncms (codigo, descricao, tipo, fonte_atualizacao) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (codigo) DO NOTHING
        """, (ncm['codigo'], ncm['descricao'], ncm['tipo'], 'siscomex'))
    
    conn.commit()
    print(f"✅ Carregados {len(data['ncms'])} NCMs")

carregar_ncms()
```

### 5. Configurar Flask para Porta 1234

Ajustar `app.py` para rodar na porta 1234:

```python
# No final do app.py:
if __name__ == '__main__':
    app.run(
        debug=False,          # Produção
        host='0.0.0.0',       # Aceita conexões externas
        port=1234,            # ← PORTA DA SUA LLM
        threaded=True         # Performance
    )
```

### 6. Iniciar API NCM

```bash
# No servidor 192.168.0.52
cd /caminho/da/api
python3 app.py

# Ou em background:
nohup python3 app.py > api_ncm.log 2>&1 &
```

### 7. Testar se Funcionou

```bash
# Do seu computador, teste:
curl http://192.168.0.52:1234/api/llm/ncms/stats

# Ou execute o script de teste:
python3 teste_api_llm.py
```

## 🔧 ALTERNATIVA SIMPLES: API INDEPENDENTE

Se você não quer modificar seu servidor principal, crie uma **API NCM independente**:

### Arquivo: `api_ncm_standalone.py`
```python
#!/usr/bin/env python3
"""
API NCM independente para LLM
Roda na porta 1234 apenas com dados NCM
"""

from flask import Flask, jsonify, request
import json
import re
from typing import Dict, List

app = Flask(__name__)

# Carrega dados NCM na memória (mais rápido)
NCM_DATA = None

def load_ncm_data():
    """Carrega dados NCM do arquivo JSON"""
    global NCM_DATA
    try:
        with open('ncms_training_data.json', 'r', encoding='utf-8') as f:
            NCM_DATA = json.load(f)
        print(f"✅ Carregados {len(NCM_DATA['ncms'])} NCMs")
        return True
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return False

@app.route('/api/llm/ncms/stats', methods=['GET'])
def get_stats():
    """Estatísticas da base NCM"""
    if not NCM_DATA:
        return jsonify({"success": False, "error": "Dados não carregados"})
    
    return jsonify({
        "success": True,
        "estatisticas_gerais": NCM_DATA["estatisticas"],
        "contexto_para_llm": {
            "uso_principal": "NCMs analíticos (8 dígitos) são usados em NFe",
            "estrutura": "Hierárquica com 4 níveis",
            "fonte_oficial": "Sistema Siscomex da Receita Federal"
        }
    })

@app.route('/api/llm/ncms/search', methods=['GET'])
def search_ncms():
    """Busca NCMs por termo"""
    if not NCM_DATA:
        return jsonify({"success": False, "error": "Dados não carregados"})
    
    query = request.args.get('q', '').lower()
    tipo = request.args.get('tipo', 'todos').lower()
    limit = min(int(request.args.get('limit', 50)), 200)
    
    if not query:
        return jsonify({"success": False, "error": "Parâmetro q é obrigatório"})
    
    # Busca nos NCMs
    resultados = []
    for ncm in NCM_DATA['ncms']:
        # Verifica se corresponde à busca
        if (query in ncm['codigo'].lower() or 
            query in ncm['descricao'].lower()):
            
            # Filtra por tipo se especificado
            if tipo != 'todos' and ncm['tipo'] != tipo:
                continue
            
            resultados.append({
                "codigo": ncm['codigo'],
                "codigo_formatado": ncm['codigo_formatado'],
                "descricao": ncm['descricao'],
                "tipo": ncm['tipo'],
                "nivel": ncm['nivel'],
                "pode_receber_lancamento": ncm['pode_receber_lancamento']
            })
            
            if len(resultados) >= limit:
                break
    
    return jsonify({
        "success": True,
        "query": query,
        "total_encontrados": len(resultados),
        "resultados": resultados
    })

@app.route('/api/llm/ncms/hierarquia/<codigo>', methods=['GET'])
def get_hierarchy(codigo):
    """Hierarquia de um NCM específico"""
    if not NCM_DATA:
        return jsonify({"success": False, "error": "Dados não carregados"})
    
    # Remove pontos do código
    codigo_limpo = codigo.replace('.', '')
    
    # Busca o NCM
    ncm_encontrado = None
    for ncm in NCM_DATA['ncms']:
        if ncm['codigo'] == codigo_limpo:
            ncm_encontrado = ncm
            break
    
    if not ncm_encontrado:
        return jsonify({"success": False, "error": f"NCM {codigo} não encontrado"})
    
    return jsonify({
        "success": True,
        "ncm_solicitado": {
            "codigo": ncm_encontrado['codigo'],
            "codigo_formatado": ncm_encontrado['codigo_formatado'],
            "descricao": ncm_encontrado['descricao'],
            "tipo": ncm_encontrado['tipo']
        },
        "hierarquia": {
            "pais": ncm_encontrado.get('hierarquia_pais', []),
            "filhos": [],
            "irmaos": []
        }
    })

@app.route('/api/llm/ncms/export', methods=['GET'])
def export_all():
    """Exporta base completa"""
    if not NCM_DATA:
        return jsonify({"success": False, "error": "Dados não carregados"})
    
    return jsonify(NCM_DATA)

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "UP", "ncms_loaded": NCM_DATA is not None})

if __name__ == '__main__':
    print("🚀 Iniciando API NCM para LLM...")
    
    if load_ncm_data():
        print("🌐 API será executada em: http://0.0.0.0:1234")
        print("📋 Endpoints disponíveis:")
        print("   • /api/llm/ncms/stats")
        print("   • /api/llm/ncms/search")
        print("   • /api/llm/ncms/hierarquia/<codigo>")
        print("   • /api/llm/ncms/export")
        print("   • /health")
        
        app.run(
            debug=False,
            host='0.0.0.0',
            port=1234,
            threaded=True
        )
    else:
        print("❌ Falha ao carregar dados NCM")
```

### Para usar a API independente:

1. **Copie os arquivos** para o servidor:
   ```bash
   scp api_ncm_standalone.py usuario@192.168.0.52:/caminho/
   scp ncms_training_data.json usuario@192.168.0.52:/caminho/
   ```

2. **Execute no servidor**:
   ```bash
   cd /caminho/
   python3 api_ncm_standalone.py
   ```

3. **Teste**:
   ```bash
   curl http://192.168.0.52:1234/health
   ```

## ✅ RESULTADO ESPERADO

Após a implantação, sua LLM poderá:

```python
# Sua LLM fará consultas assim:
import requests

def consultar_ncm(produto):
    response = requests.get("http://192.168.0.52:1234/api/llm/ncms/search", 
                          params={"q": produto, "tipo": "analitico"})
    return response.json()

# Exemplo de uso
resultado = consultar_ncm("notebook")
print(f"NCM recomendado: {resultado['resultados'][0]['codigo_formatado']}")
```

---

## 📞 PRÓXIMOS PASSOS

1. ✅ **Escolha a abordagem** (integrar na API existente ou API independente)
2. ✅ **Copie os arquivos** para o servidor 192.168.0.52
3. ✅ **Execute a API** na porta 1234
4. ✅ **Teste** com `python3 teste_api_llm.py`
5. ✅ **Integre** com sua LLM

**Depois disso, sua LLM será especialista NCM! 🎯**
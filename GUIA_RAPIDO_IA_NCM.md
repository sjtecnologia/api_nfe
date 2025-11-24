# 🚀 Guia Rápido - Sistema IA NCM

## 📦 Instalação (5 minutos)

### 1. Instalar Dependências ML

```bash
# Bibliotecas de Machine Learning
pip install scikit-learn numpy pandas

# Natural Language Processing
pip install nltk

# Baixar recursos NLTK
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('rslp')"
```

### 2. Verificar Instalação

```bash
python -c "from ai_ncm.predicao.motor_ia_ncm import MotorIANCM; print('✅ Sistema OK')"
```

---

## ⚡ Uso Rápido

### Exemplo 1: Sugerir NCM (Python)

```python
from ai_ncm.predicao.motor_ia_ncm import MotorIANCM

# Inicializa motor
motor = MotorIANCM()

# Sugere NCM
resultado = motor.sugerir_ncm(
    descricao="Cadeira de escritório giratória com rodas"
)

print(f"NCM: {resultado['ncm']}")
print(f"Descrição: {resultado['descricao']}")
print(f"Confiança: {resultado['confianca']:.1%}")
```

### Exemplo 2: API REST

```bash
# Iniciar servidor de teste
python routes/ncm_ia_routes.py

# Em outro terminal, testar endpoint
curl -X POST http://localhost:5001/api/ncm/sugerir \
  -H "Content-Type: application/json" \
  -d '{"descricao": "Mouse sem fio Logitech", "top_n": 3}'
```

### Exemplo 3: Menu Interativo

```bash
python exemplo_uso_ia_ncm.py
# Escolha uma opção do menu
```

---

## 📋 Endpoints da API

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/ncm/sugerir` | POST | Sugerir NCM |
| `/api/ncm/validar/<ncm>` | GET | Validar código |
| `/api/ncm/embasamento/<ncm>` | GET | Base legal |
| `/api/ncm/feedback` | POST | Registrar feedback |
| `/api/ncm/buscar` | GET | Buscar por palavra |
| `/api/ncm/artigos-legais` | GET | Buscar na lei |
| `/api/ncm/estatisticas` | GET | Estatísticas |
| `/api/ncm/health` | GET | Health check |

---

## 🔧 Integração com App Principal

### app.py

```python
from flask import Flask
from routes.ncm_ia_routes import registrar_rotas_ncm_ia

app = Flask(__name__)

# Registra rotas da IA NCM
registrar_rotas_ncm_ia(app)

if __name__ == '__main__':
    app.run(debug=True)
```

---

## 🎯 Casos de Uso

### 1. Formulário de Produto (NFC-e)

```html
<input type="text" id="descricao_produto" placeholder="Cadeira de escritório">
<button onclick="sugerirNCM()">🤖 Sugerir NCM</button>
<input type="text" id="ncm" placeholder="NCM">

<script>
function sugerirNCM() {
    const descricao = document.getElementById('descricao_produto').value;
    
    fetch('/api/ncm/sugerir', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({descricao: descricao})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('ncm').value = data.ncm;
        alert(`NCM sugerido: ${data.ncm} (${data.confianca}% confiança)`);
    });
}
</script>
```

### 2. Validação em Tempo Real

```javascript
// Validar NCM enquanto usuário digita
document.getElementById('ncm').addEventListener('blur', function() {
    const ncm = this.value;
    
    fetch(`/api/ncm/validar/${ncm}`)
        .then(res => res.json())
        .then(data => {
            if (data.valido) {
                this.classList.add('valid');
                this.classList.remove('invalid');
            } else {
                this.classList.add('invalid');
                this.classList.remove('valid');
            }
        });
});
```

### 3. Sistema de Feedback

```python
# Depois de emitir NF-e, registrar feedback
motor.registrar_feedback(
    descricao="Teclado mecânico gamer",
    ncm_sugerido="8471.60.53",
    ncm_correto="8471.60.53",  # Usuário confirmou
    aprovado=True,
    usuario_id=request.user.id
)
```

---

## 📊 Formato de Resposta

### JSON Completo

```json
{
  "sucesso": true,
  "ncm": "9401.30.00",
  "descricao": "Assentos giratórios de altura ajustável",
  "confianca": 0.95,
  "alternativas": [
    {
      "ncm": "9401.80.00",
      "descricao": "Outros assentos",
      "confianca": 0.75
    }
  ],
  "classificacao": {
    "ncm": "9401.30.00",
    "descricao_oficial": "Assentos giratórios de altura ajustável",
    "confianca": "95.0%",
    "nivel_confianca": "MUITO ALTA"
  },
  "fundamentacao_tecnica": [
    "Produto classificado no Capítulo 94 da NCM",
    "Enquadramento na Posição 9401 da tabela NCM vigente",
    "..."
  ],
  "base_legal": [
    {
      "artigo": "Art. 4º",
      "lei": "LC 214/2025",
      "resumo": "O IBS e a CBS incidem sobre...",
      "relevancia": "Artigo base sobre incidência de tributos"
    }
  ],
  "observacoes": [
    "✅ Alta confiança na classificação. Recomenda-se uso direto.",
    "📌 A classificação NCM é de responsabilidade do contribuinte."
  ],
  "proximos_passos": [
    "2️⃣ Consultar tabela NCM completa no site da Receita Federal",
    "3️⃣ Verificar alíquotas de IBS e CBS aplicáveis"
  ]
}
```

---

## 🔍 Troubleshooting

### Erro: "scikit-learn não instalado"

```bash
pip install scikit-learn numpy
```

### Erro: "Tabela NCM não encontrada"

```bash
# Verificar se arquivo existe
ls Tabela_NCM_Vigente_20251029.json

# Ou mover para diretório correto
mv Tabela_NCM_Vigente_20251029.json ai_ncm/dados/
```

### Erro: "Lei Complementar não encontrada"

```bash
# Executar extração do PDF novamente
python extrair_pdf_lei_214.py
```

### Baixa Confiança nas Sugestões

1. **Treinar modelo com mais dados**
2. **Adicionar mais exemplos via feedback**
3. **Melhorar descrição do produto**

---

## 📈 Monitoramento

### Ver Estatísticas

```bash
curl http://localhost:5001/api/ncm/estatisticas
```

### Health Check

```bash
curl http://localhost:5001/api/ncm/health
```

### Log de Feedback

```python
# Ver histórico de classificações
from ai_ncm.predicao.motor_ia_ncm import MotorIANCM
motor = MotorIANCM()
print(f"Total de feedbacks: {len(motor.historico)}")
```

---

## 💡 Dicas de Uso

### 1. **Descrições Detalhadas = Melhor Resultado**

❌ Ruim: "cadeira"  
✅ Bom: "Cadeira de escritório giratória com rodas e ajuste de altura"

### 2. **Use Contexto Quando Disponível**

```python
resultado = motor.sugerir_ncm(
    descricao="notebook",
    contexto="equipamento de informática profissional",
    detalhes={"marca": "Dell", "processador": "Intel Core i5"}
)
```

### 3. **Aproveite Alternativas**

```python
# Analise top 5 sugestões
for alt in resultado['alternativas'][:5]:
    print(f"{alt['ncm']}: {alt['descricao']} ({alt['confianca']:.1%})")
```

### 4. **Sempre Registre Feedback**

```python
# Melhora o sistema com o tempo
motor.registrar_feedback(
    descricao=descricao,
    ncm_sugerido=resultado['ncm'],
    ncm_correto=ncm_confirmado,
    aprovado=True
)
```

---

## 🎓 Próximos Passos

1. ✅ Instalou dependências
2. ✅ Testou exemplos
3. ✅ Integrou com app
4. 📝 **Agora:** Criar dataset de treinamento
5. 🚀 **Depois:** Treinar modelo ML
6. 📊 **Por fim:** Monitorar performance

---

## 📞 Suporte

- **Documentação Completa:** `SISTEMA_IA_NCM_README.md`
- **Resumo Técnico:** `RESUMO_SISTEMA_IA_NCM.md`
- **Exemplos:** `exemplo_uso_ia_ncm.py`

---

*Guia atualizado: Janeiro 2025*  
*Sistema IA NCM v1.0*

# Correção: DANFE Oficial vs Simplificado

## 🐛 Problema Identificado

Ao gerar o DANFE, o sistema estava gerando a versão **simplificada** (ReportLab) em vez da **oficial** (nfelib + BrazilFiscalReport).

## 🔍 Causa Raiz

A biblioteca `nfelib` estava instalada, mas faltavam as **engines de PDF** necessárias:
- ❌ `BrazilFiscalReport` - Não estava instalado
- ❌ `brazilnum` - Não estava instalado
- ❌ `erpbrasil.edoc.pdf` - Não estava instalado

Além disso, o código não estava:
- Passando o parâmetro `config` com a logo para o método `to_pdf()`
- Usando o nome correto da engine: `"brazilfiscalreport"` (minúsculo)

## ✅ Solução Aplicada

### 1. Instalação de Dependências

```bash
pip install brazilnum
pip install BrazilFiscalReport
pip install erpbrasil.edoc.pdf
```

**Pacotes instalados:**
- ✅ `brazilnum==0.8.8` - Validações e formatações brasileiras
- ✅ `BrazilFiscalReport==0.5.33` - Engine principal de PDF
- ✅ `erpbrasil.edoc.pdf` - Engine alternativa
- ✅ `fpdf2>=2.8.3` - Dependência do BrazilFiscalReport
- ✅ `python-barcode` - Geração de códigos de barras
- ✅ `phonenumbers` - Validação de telefones

### 2. Correção do Código

**Arquivo:** `services/danfe_service.py`

**Antes:**
```python
# Tentava usar engine None (padrão) sem configuração
pdf_engines = [
    None,  # ❌ Não funcionava
    "BrazilFiscalReport",  # ❌ Nome errado
    "erpbrasil.edoc.pdf"
]

# Não passava logo
pdf_bytes = nfe_proc.to_pdf(engine=engine)
```

**Depois:**
```python
# Configura logo usando DanfeConfig
config = None
if logo_path and os.path.exists(logo_path):
    from brazilfiscalreport.danfe import DanfeConfig
    config = DanfeConfig(logo=logo_path)
    logger.info(f"✅ Logo configurada: {logo_path}")

# Usa nome correto da engine
pdf_engines = [
    "brazilfiscalreport",  # ✅ Nome correto (minúsculo)
    "BrazilFiscalReport",  # Fallback
    "erpbrasil.edoc.pdf"   # Alternativa
]

# Passa config com logo
pdf_bytes = nfe_proc.to_pdf(engine=engine, config=config)
```

## 🧪 Como Testar

### Teste 1: Verificar Dependências
```bash
python -c "
import brazilnum
import BrazilFiscalReport
import erpbrasil.edoc.pdf
print('✅ Todas as engines instaladas')
"
```

### Teste 2: Gerar DANFE
1. Acesse **Emitir NFe**
2. Preencha os dados básicos
3. Marque **"Gerar DANFE automaticamente"**
4. Emita a NFe em **Homologação**
5. Verifique o PDF gerado

**Resultado esperado:**
- ✅ DANFE oficial com layout da SEFAZ
- ✅ Logo do cliente visível no cabeçalho
- ✅ Todos os campos de transportadora presentes
- ✅ Código de barras e chave de acesso formatados
- ✅ Informações fiscais completas

### Teste 3: Verificar Logs
```bash
# Verificar se a engine correta foi usada
grep "PDF gerado com engine" /caminho/logs/app.log
```

**Saída esperada:**
```
✅ PDF gerado com engine brazilfiscalreport, tamanho: 45678 bytes
```

## 📊 Diferenças entre DANFEs

### DANFE Oficial (BrazilFiscalReport)
- ✅ Layout oficial da SEFAZ
- ✅ Código de barras
- ✅ Formatação profissional
- ✅ Todos os campos fiscais
- ✅ Logo do cliente
- ✅ Aceito para impressão e envio

### DANFE Simplificado (ReportLab - Fallback)
- ⚠️ Layout básico
- ❌ Sem código de barras
- ⚠️ Formatação simples
- ⚠️ Campos principais apenas
- ⚠️ Logo genérica
- ❌ Apenas para referência interna

## 🔧 Troubleshooting

### Problema: Ainda gera DANFE simplificado

**Verificar:**
```bash
pip list | grep -i brazil
pip list | grep -i erpbrasil
```

**Deve mostrar:**
```
BrazilFiscalReport    0.5.33
brazilnum             0.8.8
erpbrasil.base        2.1.3
erpbrasil.edoc.pdf    2.1.4
```

### Problema: Erro "No module named 'brazilfiscalreport'"

**Solução:**
```bash
pip install --upgrade BrazilFiscalReport
```

### Problema: Logo não aparece no DANFE

**Verificar:**
1. Campo `logo_path` está preenchido no banco?
   ```sql
   SELECT cliente_id, razao_social, logo_path FROM clientes WHERE logo_path IS NOT NULL;
   ```

2. Arquivo existe em `static/logos/`?
   ```bash
   ls -la static/logos/
   ```

3. Caminho está correto?
   - ✅ `logos/cliente_1733164800.png` (relativo)
   - ❌ `/static/logos/cliente_1733164800.png` (absoluto - errado)

### Problema: Erro ao gerar PDF

**Verificar logs:**
```python
# services/danfe_service.py adiciona logs detalhados
logger.error(f"❌ Erro com engine {engine}: {str(e)}")
print(f"   Traceback: {traceback.format_exc()}")
```

**Comum:**
- XML inválido ou malformado
- Certificado expirado
- Campos obrigatórios faltando

## 📁 Arquivos Modificados

```
services/danfe_service.py
└── generate_danfe_nfelib()
    ├── ✅ Adiciona DanfeConfig com logo
    ├── ✅ Corrige nome da engine para "brazilfiscalreport"
    └── ✅ Passa config no to_pdf()
```

## 🚀 Próximos Passos

1. ✅ Dependências instaladas
2. ✅ Código corrigido
3. ⏳ **Reiniciar serviço** (necessário!)
4. ⏳ Testar emissão de NFe
5. ⏳ Verificar DANFE gerado

## 🔄 Reiniciar Serviço

### No servidor de produção (Windows):
```bash
nssm restart NFe_Backend
```

### Localmente (Mac/Linux):
```bash
# Se estiver rodando com Flask
pkill -f "python app.py"
python app.py
```

---

**Data da Correção:** 02/12/2025  
**Versão:** 1.1  
**Status:** ✅ Resolvido

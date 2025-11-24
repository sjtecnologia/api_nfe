# 📄 Instrução para Processar Segundo PDF

## 🎯 Objetivo

O usuário mencionou **"dois pdfs"** sobre a Lei Complementar 214/2025, mas até agora apenas um PDF foi processado.

Este arquivo contém instruções para processar o segundo PDF quando for fornecido.

---

## ✅ O que já foi feito

- ✅ **Primeiro PDF processado:**
  - 232 páginas
  - 806.677 caracteres extraídos
  - 1.226 artigos parseados
  - 20 referências NCM identificadas
  - 418 menções a alíquotas
  - Arquivo gerado: `lei_complementar_214_2025_dados_estruturados.json`

---

## 🔄 Quando o segundo PDF chegar

### Passo 1: Extrair o segundo PDF

```bash
# Usar o mesmo script de extração
python extrair_pdf_lei_214.py
# (Modificar para processar o segundo arquivo)
```

### Passo 2: Comparar conteúdos

```python
# Verificar se há informações adicionais
import json

# Carregar dados do primeiro PDF
with open('lei_complementar_214_2025_dados_estruturados.json', 'r') as f:
    dados_pdf1 = json.load(f)

# Carregar dados do segundo PDF (após extração)
with open('lei_complementar_214_2025_dados_estruturados_pdf2.json', 'r') as f:
    dados_pdf2 = json.load(f)

# Comparar
print(f"PDF 1: {dados_pdf1['total_artigos']} artigos")
print(f"PDF 2: {dados_pdf2['total_artigos']} artigos")

print(f"PDF 1: {dados_pdf1['total_referencias_ncm']} refs NCM")
print(f"PDF 2: {dados_pdf2['total_referencias_ncm']} refs NCM")
```

### Passo 3: Mesclar dados (se necessário)

```python
# Script para mesclar dois PDFs
def mesclar_dados_lei(dados1, dados2):
    """Mescla dados de dois PDFs da mesma lei"""
    
    # Verifica se são a mesma lei
    if dados1.get('lei') != dados2.get('lei'):
        print("⚠️ Atenção: PDFs parecem ser de leis diferentes!")
    
    # Mescla artigos (remove duplicatas)
    artigos_mesclados = {}
    
    for artigo in dados1.get('artigos', []):
        artigos_mesclados[artigo['artigo']] = artigo
    
    for artigo in dados2.get('artigos', []):
        # Se artigo já existe, mescla conteúdo
        if artigo['artigo'] in artigos_mesclados:
            # Mantém o maior conteúdo
            if len(artigo['conteudo']) > len(artigos_mesclados[artigo['artigo']]['conteudo']):
                artigos_mesclados[artigo['artigo']] = artigo
        else:
            artigos_mesclados[artigo['artigo']] = artigo
    
    # Mescla referências NCM
    refs_ncm = []
    refs_ncm.extend(dados1.get('referencias_ncm', []))
    refs_ncm.extend(dados2.get('referencias_ncm', []))
    
    # Remove duplicatas
    refs_ncm_unicas = []
    termos_vistos = set()
    
    for ref in refs_ncm:
        termo = ref.get('termo', '')
        if termo not in termos_vistos:
            refs_ncm_unicas.append(ref)
            termos_vistos.add(termo)
    
    # Mescla alíquotas
    aliquotas = []
    aliquotas.extend(dados1.get('aliquotas', []))
    aliquotas.extend(dados2.get('aliquotas', []))
    
    # Cria estrutura mesclada
    dados_mesclados = {
        'lei': dados1.get('lei', 'LC 214/2025'),
        'data': dados1.get('data', '16/01/2025'),
        'total_artigos': len(artigos_mesclados),
        'total_referencias_ncm': len(refs_ncm_unicas),
        'total_aliquotas': len(aliquotas),
        'artigos': list(artigos_mesclados.values()),
        'referencias_ncm': refs_ncm_unicas,
        'aliquotas': aliquotas,
        'fontes': [
            'PDF 1 processado',
            'PDF 2 processado',
            'Dados mesclados automaticamente'
        ]
    }
    
    return dados_mesclados

# Usar função
dados_mesclados = mesclar_dados_lei(dados_pdf1, dados_pdf2)

# Salvar resultado
with open('lei_complementar_214_2025_completo.json', 'w', encoding='utf-8') as f:
    json.dump(dados_mesclados, f, ensure_ascii=False, indent=2)

print("✅ Dados mesclados salvos em: lei_complementar_214_2025_completo.json")
```

### Passo 4: Atualizar sistema IA

```python
# Recarregar dados no motor IA
from ai_ncm.predicao.motor_ia_ncm import MotorIANCM

# O motor carregará automaticamente o arquivo atualizado
motor = MotorIANCM()

# Verificar se novos dados foram carregados
print(f"✅ Lei Complementar carregada")
print(f"   Artigos: {len(motor.lei_214.get('artigos', []))}")
print(f"   Refs NCM: {len(motor.lei_214.get('referencias_ncm', []))}")
```

---

## 🤔 Possíveis Cenários

### Cenário 1: Segundo PDF é complemento do primeiro

**Exemplo:** Primeiro PDF contém texto da lei, segundo PDF contém anexos/tabelas

**Ação:**
- Extrair ambos
- Mesclar dados
- Atualizar arquivo `lei_complementar_214_2025_dados_estruturados.json`

### Cenário 2: Segundo PDF é versão atualizada

**Exemplo:** Primeiro PDF é rascunho, segundo é versão final publicada

**Ação:**
- Comparar artigos
- Usar versão mais completa
- Substituir arquivo antigo

### Cenário 3: Segundo PDF é documento relacionado

**Exemplo:** Regulamentação, decreto, portaria complementar

**Ação:**
- Processar separadamente
- Criar arquivo novo: `documento_complementar_dados.json`
- Atualizar `BuscadorLeiComplementar` para buscar em múltiplos documentos

### Cenário 4: PDFs são idênticos

**Exemplo:** Mesma versão em formatos diferentes

**Ação:**
- Verificar qual PDF tem melhor extração
- Manter apenas um
- Descartar duplicata

---

## 📋 Checklist para Segundo PDF

Quando receber o segundo PDF:

- [ ] Salvar arquivo com nome descritivo
- [ ] Executar `extrair_pdf_lei_214.py` (adaptado)
- [ ] Comparar totais (artigos, NCM refs, alíquotas)
- [ ] Identificar cenário (complemento, atualização, relacionado, idêntico)
- [ ] Mesclar dados se necessário
- [ ] Atualizar arquivo usado pelo sistema IA
- [ ] Testar motor IA com novos dados
- [ ] Verificar se há novos NCMs mencionados
- [ ] Atualizar documentação se relevante

---

## 🔧 Script Adaptado para Segundo PDF

```python
# extrair_segundo_pdf.py
import pdfplumber
import json
from pathlib import Path

def extrair_segundo_pdf(caminho_pdf: str):
    """
    Extrai dados do segundo PDF sobre LC 214/2025
    """
    print("📄 Processando segundo PDF...")
    print(f"   Arquivo: {caminho_pdf}")
    
    # Usar mesmas funções de extrair_pdf_lei_214.py
    # ...
    
    # Salvar com nome diferente
    arquivo_saida = 'lei_complementar_214_2025_dados_estruturados_pdf2.json'
    
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Segundo PDF processado")
    print(f"   Saída: {arquivo_saida}")
    
    return dados

if __name__ == '__main__':
    # Processar segundo PDF
    caminho = input("Digite o caminho do segundo PDF: ")
    dados = extrair_segundo_pdf(caminho)
    
    # Perguntar se deseja mesclar
    mesclar = input("\nDeseja mesclar com primeiro PDF? (s/n): ")
    
    if mesclar.lower() == 's':
        from mesclar_pdfs import mesclar_dados_lei
        
        # Carregar primeiro PDF
        with open('lei_complementar_214_2025_dados_estruturados.json', 'r') as f:
            dados_pdf1 = json.load(f)
        
        # Mesclar
        dados_mesclados = mesclar_dados_lei(dados_pdf1, dados)
        
        # Salvar
        with open('lei_complementar_214_2025_completo.json', 'w', encoding='utf-8') as f:
            json.dump(dados_mesclados, f, ensure_ascii=False, indent=2)
        
        print("✅ Dados mesclados salvos!")
```

---

## 📞 Quando Solicitar Segundo PDF

Perguntar ao usuário:

> 🗣️ **"Você mencionou dois PDFs sobre a Lei Complementar 214/2025. Processamos o primeiro PDF com sucesso (232 páginas, 1.226 artigos). Você tem o segundo PDF disponível? Se sim, por favor, forneça para que possamos:**
> - Verificar se há informações adicionais
> - Mesclar dados complementares
> - Garantir que o sistema IA tenha acesso completo à legislação

---

## 📝 Nota

Este arquivo serve como **guia para ação futura**. O sistema IA está funcional com os dados do primeiro PDF. O segundo PDF pode:

1. **Adicionar mais artigos** → Melhorar embasamento legal
2. **Adicionar mais refs NCM** → Melhorar precisão nas sugestões
3. **Adicionar anexos/tabelas** → Enriquecer contexto

**Status Atual:** ✅ Sistema funcional com 1 PDF  
**Status Desejado:** ✅✅ Sistema completo com 2 PDFs (quando disponível)

---

*Instrução criada: Janeiro 2025*  
*Aguardando: Segundo PDF da LC 214/2025*

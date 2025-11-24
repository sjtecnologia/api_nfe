#!/usr/bin/env python3
"""
Script para extrair texto da Lei Complementar 214/2025
e preparar dados para treinamento de IA para classificação NCM
"""

import pdfplumber
import json
import re
from pathlib import Path

def extrair_texto_pdf(caminho_pdf):
    """Extrai todo o texto do PDF"""
    print(f"📄 Extraindo texto de: {caminho_pdf}")
    
    texto_completo = []
    
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            print(f"📊 Total de páginas: {len(pdf.pages)}")
            
            for i, pagina in enumerate(pdf.pages, 1):
                print(f"  Processando página {i}/{len(pdf.pages)}...", end='\r')
                texto = pagina.extract_text()
                if texto:
                    texto_completo.append(texto)
            
            print(f"\n✅ Extração concluída!")
            
    except Exception as e:
        print(f"❌ Erro ao extrair PDF: {e}")
        return None
    
    return '\n\n'.join(texto_completo)


def extrair_artigos(texto):
    """Extrai artigos da lei com seus conteúdos"""
    print("\n📋 Extraindo artigos da lei...")
    
    # Padrão para identificar artigos
    padrao_artigo = r'Art\.\s*(\d+º?[A-Z]?)[\.º]?\s+(.*?)(?=Art\.\s*\d+|$)'
    
    artigos = []
    matches = re.finditer(padrao_artigo, texto, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        numero_artigo = match.group(1).strip()
        conteudo_artigo = match.group(2).strip()
        
        # Remove múltiplos espaços e quebras de linha
        conteudo_artigo = re.sub(r'\s+', ' ', conteudo_artigo)
        
        artigos.append({
            'artigo': numero_artigo,
            'conteudo': conteudo_artigo[:500]  # Primeiros 500 caracteres
        })
    
    print(f"✅ {len(artigos)} artigos extraídos")
    return artigos


def identificar_referencias_ncm(texto):
    """Identifica menções a NCM e classificação fiscal"""
    print("\n🔍 Identificando referências a NCM...")
    
    # Padrões para identificar NCM
    padroes_ncm = [
        r'NCM[\s-]?\d{4}\.?\d{2}\.?\d{2}',  # NCM 0000.00.00
        r'classificação fiscal',
        r'nomenclatura comum do mercosul',
        r'código ncm',
        r'tabela ncm',
        r'posição\s+\d{4}',  # Posição tarifária
    ]
    
    referencias = []
    
    for padrao in padroes_ncm:
        matches = re.finditer(padrao, texto, re.IGNORECASE)
        for match in matches:
            contexto_inicio = max(0, match.start() - 200)
            contexto_fim = min(len(texto), match.end() + 200)
            contexto = texto[contexto_inicio:contexto_fim]
            
            referencias.append({
                'termo': match.group(0),
                'contexto': contexto.strip()
            })
    
    print(f"✅ {len(referencias)} referências encontradas")
    return referencias


def extrair_tabelas_aliquotas(texto):
    """Tenta identificar tabelas de alíquotas IBS/CBS"""
    print("\n📊 Procurando tabelas de alíquotas...")
    
    # Padrões para identificar menções a alíquotas
    padroes_aliquota = [
        r'alíquota.*?(\d+[,.]?\d*)\s*%',
        r'IBS.*?(\d+[,.]?\d*)\s*%',
        r'CBS.*?(\d+[,.]?\d*)\s*%',
    ]
    
    aliquotas = []
    
    for padrao in padroes_aliquota:
        matches = re.finditer(padrao, texto, re.IGNORECASE | re.DOTALL)
        for match in matches:
            contexto_inicio = max(0, match.start() - 150)
            contexto_fim = min(len(texto), match.end() + 150)
            contexto = texto[contexto_inicio:contexto_fim]
            
            aliquotas.append({
                'match': match.group(0),
                'percentual': match.group(1) if (match.lastindex is not None and match.lastindex >= 1) else None,
                'contexto': contexto.strip()
            })
    
    print(f"✅ {len(aliquotas)} menções a alíquotas encontradas")
    return aliquotas


def salvar_dados_estruturados(dados, arquivo_saida):
    """Salva dados estruturados em JSON"""
    print(f"\n💾 Salvando dados estruturados em: {arquivo_saida}")
    
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    
    print("✅ Dados salvos com sucesso!")


def main():
    # Caminho do PDF
    pdf_path = Path("/Users/renato/Documents/Developement/api_nfe/Documentacao/LEI COMPLEMENTAR Nº 214, DE 16 DE JANEIRO DE 2025 - LEI COMPLEMENTAR Nº 214, DE 16 DE JANEIRO DE 2025 - DOU - Imprensa Nacional.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        return
    
    # 1. Extrair texto completo
    texto_completo = extrair_texto_pdf(str(pdf_path))
    
    if not texto_completo:
        print("❌ Não foi possível extrair texto do PDF")
        return
    
    # Salvar texto completo
    texto_path = Path("lei_complementar_214_2025_texto_completo.txt")
    with open(texto_path, 'w', encoding='utf-8') as f:
        f.write(texto_completo)
    print(f"\n💾 Texto completo salvo em: {texto_path}")
    
    # 2. Extrair artigos
    artigos = extrair_artigos(texto_completo)
    
    # 3. Identificar referências NCM
    referencias_ncm = identificar_referencias_ncm(texto_completo)
    
    # 4. Extrair tabelas de alíquotas
    aliquotas = extrair_tabelas_aliquotas(texto_completo)
    
    # 5. Estruturar dados para treinamento
    dados_estruturados = {
        'lei': 'LC 214/2025',
        'data': '16/01/2025',
        'total_artigos': len(artigos),
        'total_referencias_ncm': len(referencias_ncm),
        'total_aliquotas': len(aliquotas),
        'artigos': artigos[:50],  # Primeiros 50 artigos
        'referencias_ncm': referencias_ncm[:100],  # Primeiras 100 referências
        'aliquotas': aliquotas[:50],  # Primeiras 50 menções
    }
    
    # 6. Salvar dados estruturados
    json_path = Path("lei_complementar_214_2025_dados_estruturados.json")
    salvar_dados_estruturados(dados_estruturados, str(json_path))
    
    # 7. Exibir estatísticas
    print("\n" + "="*60)
    print("📊 RESUMO DA EXTRAÇÃO")
    print("="*60)
    print(f"📄 Texto completo: {len(texto_completo):,} caracteres")
    print(f"📋 Artigos extraídos: {len(artigos)}")
    print(f"🔍 Referências NCM: {len(referencias_ncm)}")
    print(f"💰 Menções a alíquotas: {len(aliquotas)}")
    print("="*60)
    
    # Amostra de dados
    if artigos:
        print(f"\n📝 Exemplo de artigo extraído:")
        print(f"   Art. {artigos[0]['artigo']}")
        print(f"   {artigos[0]['conteudo'][:200]}...")
    
    if referencias_ncm:
        print(f"\n🔍 Exemplo de referência NCM:")
        print(f"   {referencias_ncm[0]['termo']}")
        print(f"   Contexto: {referencias_ncm[0]['contexto'][:150]}...")


if __name__ == '__main__':
    main()

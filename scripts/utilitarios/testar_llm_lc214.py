"""
[?] Script de Teste - LLM NCM (Antes e Depois do Treinamento)
Testa a capacidade da LLM de fornecer embasamento legal da LC 214/2025
"""

import requests
import json
from typing import Dict, List

# Configurações
LLM_URL = "http://192.168.0.52:1234/v1/chat/completions"
TIMEOUT = 60

# ==================== CASOS DE TESTE ====================

TESTES = [
    {
        "nome": "Café (Cesta Básica - Redução 100%)",
        "produto": "Café torrado em grãos",
        "ncm_disponivel": "09.01.21.10 - Café torrado, não descafeinado, em grão",
        "esperado": {
            "ncm": "09012110",
            "beneficio": "Redução 100% IBS/CBS",
            "artigo": "Anexo I, item 8, LC 214/2025"
        }
    },
    {
        "nome": "Ovos (Redução 100%)",
        "produto": "Ovos frescos de galinha",
        "ncm_disponivel": "04.07.21.00 - Ovos frescos, de galinha",
        "esperado": {
            "ncm": "04072100",
            "beneficio": "Redução 100% IBS/CBS",
            "artigo": "Anexo XV, item 1, LC 214/2025"
        }
    },
    {
        "nome": "Farinha Dietética (Redução 100%)",
        "produto": "Farinha para fenilcetonúria - baixo teor de proteína",
        "ncm_disponivel": "19.01.90.90 - Outras preparações alimentícias",
        "esperado": {
            "ncm": "19019090",
            "beneficio": "Redução 100% IBS/CBS",
            "artigo": "Anexo I, item 24, LC 214/2025"
        }
    },
    {
        "nome": "Perfume (Restrição ZFM)",
        "produto": "Perfume importado - Eau de Parfum 100ml",
        "ncm_disponivel": "33.03.00.10 - Perfumes (extratos)",
        "esperado": {
            "ncm": "33030010",
            "restricao": "Vedação créditos ZFM",
            "artigo": "Art. 381, alínea f, LC 214/2025"
        }
    },
    {
        "nome": "Locomotiva (Suspensão)",
        "produto": "Locomotiva elétrica para transporte ferroviário",
        "ncm_disponivel": "86.01.10.00 - Locomotivas, de fonte externa de eletricidade",
        "esperado": {
            "ncm": "86011000",
            "beneficio": "Suspensão IBS/CBS",
            "artigo": "Art. 119, §1º, LC 214/2025"
        }
    }
]

# ==================== FUNÇÕES ====================

def criar_prompt(produto: str, ncm_disponivel: str) -> str:
    """Cria o prompt de teste"""
    return f"""Produto: {produto}

Dados NCM disponíveis:
**NCM {ncm_disponivel}**

Classifique este produto fornecendo:
1. NCM correto (8 dígitos)
2. CFOP
3. CST ou CSOSN
4. CEST (se aplicável)
5. EMBASAMENTO LEGAL da Lei Complementar 214/2025 (IBS/CBS)

IMPORTANTE: Cite artigos, parágrafos e anexos específicos da LC 214/2025 quando houver benefícios fiscais ou restrições."""

def testar_llm(teste: Dict) -> Dict:
    """Executa um teste na LLM"""
    print(f"\n{'='*60}")
    print(f"[?] Teste: {teste['nome']}")
    print(f"{'='*60}")
    print(f"Produto: {teste['produto']}")
    print(f"NCM: {teste['ncm_disponivel']}")
    
    # Preparar mensagens
    messages = [
        {
            "role": "system",
            "content": "Você é um especialista brasileiro em classificação tributária NCM com conhecimento profundo da Lei Complementar 214/2025 (Reforma Tributária - IBS e CBS). Analise produtos e retorne o NCM correto com embasamento legal preciso citando artigos específicos da lei."
        },
        {
            "role": "user",
            "content": criar_prompt(teste['produto'], teste['ncm_disponivel'])
        }
    ]
    
    # Chamar API
    try:
        print("\n[?] Consultando LLM...")
        response = requests.post(
            LLM_URL,
            json={
                "model": "meta-llama-3.1-8b-instruct",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.1
            },
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            resposta = data["choices"][0]["message"]["content"]
            
            print("\n[LIST] RESPOSTA DA LLM:")
            print("-" * 60)
            print(resposta)
            print("-" * 60)
            
            # Análise da resposta
            analise = analisar_resposta(resposta, teste['esperado'])
            print("\n[DATA] ANÁLISE:")
            print(f"   [OK] NCM Correto: {'Sim' if analise['ncm_correto'] else 'Não'}")
            print(f"   [?] Citou LC 214/2025: {'Sim' if analise['citou_lei'] else 'Não'}")
            print(f"   [?] Citou artigos específicos: {'Sim' if analise['citou_artigos'] else 'Não'}")
            
            if analise['observacoes']:
                print(f"   [!] Observações: {analise['observacoes']}")
            
            return {
                "sucesso": True,
                "resposta": resposta,
                "analise": analise
            }
        else:
            print(f"[X] Erro na API: {response.status_code}")
            print(response.text)
            return {"sucesso": False, "erro": response.text}
            
    except requests.exceptions.Timeout:
        print("⏰ Timeout - LLM não respondeu a tempo")
        return {"sucesso": False, "erro": "Timeout"}
    except Exception as e:
        print(f"[X] Erro: {e}")
        return {"sucesso": False, "erro": str(e)}

def analisar_resposta(resposta: str, esperado: Dict) -> Dict:
    """Analisa a qualidade da resposta"""
    resposta_lower = resposta.lower()
    
    # Verificar NCM
    ncm_esperado = esperado.get('ncm', '').replace('.', '')
    ncm_correto = ncm_esperado in resposta.replace('.', '').replace(' ', '')
    
    # Verificar citação da lei
    citou_lei = any([
        'lc 214' in resposta_lower,
        'lei complementar 214' in resposta_lower,
        '214/2025' in resposta_lower,
        'lc214' in resposta_lower
    ])
    
    # Verificar citação de artigos
    citou_artigos = any([
        'art.' in resposta_lower,
        'artigo' in resposta_lower,
        'anexo' in resposta_lower,
        '§' in resposta,
        'parágrafo' in resposta_lower
    ])
    
    # Verificar menção ao benefício/restrição
    beneficio = esperado.get('beneficio', '')
    restricao = esperado.get('restricao', '')
    
    mencionou_beneficio = False
    if beneficio:
        if 'redução 100%' in beneficio.lower():
            mencionou_beneficio = any([
                'redução de 100%' in resposta_lower,
                'redução 100%' in resposta_lower,
                'isenção' in resposta_lower,
                'isento' in resposta_lower
            ])
        elif 'suspensão' in beneficio.lower():
            mencionou_beneficio = 'suspensão' in resposta_lower
    
    if restricao:
        mencionou_beneficio = restricao.lower() in resposta_lower
    
    # Observações
    observacoes = []
    if not ncm_correto:
        observacoes.append(f"NCM esperado: {ncm_esperado}")
    if not citou_lei:
        observacoes.append("Não citou LC 214/2025")
    if not citou_artigos:
        observacoes.append("Não citou artigos específicos")
    if not mencionou_beneficio and (beneficio or restricao):
        observacoes.append(f"Não mencionou: {beneficio or restricao}")
    
    return {
        "ncm_correto": ncm_correto,
        "citou_lei": citou_lei,
        "citou_artigos": citou_artigos,
        "mencionou_beneficio": mencionou_beneficio,
        "observacoes": "; ".join(observacoes) if observacoes else None
    }

def executar_todos_testes():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("  [?] SUITE DE TESTES - LLM NCM com LC 214/2025")
    print("="*60)
    print(f"\n[?] Servidor LLM: {LLM_URL}")
    print(f"[DATA] Total de testes: {len(TESTES)}\n")
    
    resultados = []
    
    for i, teste in enumerate(TESTES, 1):
        print(f"\n[{i}/{len(TESTES)}]", end=" ")
        resultado = testar_llm(teste)
        resultados.append({
            "nome": teste['nome'],
            "resultado": resultado
        })
        
        # Aguardar um pouco entre testes
        if i < len(TESTES):
            import time
            time.sleep(2)
    
    # Resumo final
    print("\n" + "="*60)
    print("  [DATA] RESUMO DOS TESTES")
    print("="*60)
    
    sucessos = sum(1 for r in resultados if r['resultado'].get('sucesso'))
    ncm_corretos = sum(1 for r in resultados if r['resultado'].get('analise', {}).get('ncm_correto'))
    citou_lei = sum(1 for r in resultados if r['resultado'].get('analise', {}).get('citou_lei'))
    citou_artigos = sum(1 for r in resultados if r['resultado'].get('analise', {}).get('citou_artigos'))
    
    print(f"\n[OK] Testes executados com sucesso: {sucessos}/{len(TESTES)}")
    print(f"[?] NCMs corretos: {ncm_corretos}/{len(TESTES)}")
    print(f"[?] Citou LC 214/2025: {citou_lei}/{len(TESTES)}")
    print(f"[?] Citou artigos específicos: {citou_artigos}/{len(TESTES)}")
    
    porcentagem = (citou_artigos / len(TESTES)) * 100
    
    print(f"\n[?] Taxa de sucesso (com embasamento legal): {porcentagem:.1f}%")
    
    if porcentagem < 50:
        print("\n[!] RECOMENDAÇÃO: Execute o fine-tuning para melhorar os resultados!")
        print("   python treinar_llm_ncm_lc214.py")
    elif porcentagem < 80:
        print("\n[?] SUGESTÃO: Fine-tuning pode melhorar ainda mais os resultados")
    else:
        print("\n[?] Excelente! A LLM já fornece bom embasamento legal")

# ==================== MAIN ====================

if __name__ == "__main__":
    try:
        executar_todos_testes()
    except KeyboardInterrupt:
        print("\n\n[!] Testes interrompidos pelo usuário")
    except Exception as e:
        print(f"\n\n[X] Erro: {e}")
        import traceback
        traceback.print_exc()

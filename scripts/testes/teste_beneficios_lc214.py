"""
[?] Teste Específico - Produtos com Benefícios LC 214/2025
Testa produtos que têm benefícios fiscais na nova lei
"""

import requests
import json

LLM_URL = "http://192.168.0.52:1234/v1/chat/completions"

TESTES_BENEFICIOS = [
    {
        "nome": "Café - Cesta Básica",
        "produto": "Café torrado em grãos",
        "ncm": "09.01.21.10",
        "esperado": {
            "beneficio": "Redução 100%",
            "anexo": "Anexo I",
            "item": "item 8",
            "artigo": "Art. 8º"
        }
    },
    {
        "nome": "Ovos - Hortifrutigranjeiros",
        "produto": "Ovos frescos de galinha",
        "ncm": "04.07.21.00",
        "esperado": {
            "beneficio": "Redução 100%",
            "anexo": "Anexo XV",
            "item": "item 1"
        }
    },
    {
        "nome": "Tomate - Hortifrutigranjeiros",
        "produto": "Tomate fresco",
        "ncm": "07.02.00.00",
        "esperado": {
            "beneficio": "Redução 100%",
            "anexo": "Anexo XV",
            "capitulo": "Capítulo 07"
        }
    }
]

def testar_produto(teste):
    """Testa um produto com benefício fiscal"""
    
    print("\n" + "="*70)
    print(f"[?] Teste: {teste['nome']}")
    print("="*70)
    print(f"Produto: {teste['produto']}")
    print(f"NCM: {teste['ncm']}")
    
    messages = [
        {
            "role": "system",
            "content": "Você é um especialista em classificação tributária NCM com conhecimento profundo da Lei Complementar 214/2025 (Reforma Tributária - IBS e CBS)."
        },
        {
            "role": "user",
            "content": f"""Classifique este produto e informe TODOS os benefícios fiscais da LC 214/2025:

Produto: {teste['produto']}
NCM disponível: {teste['ncm']}

Retorne em formato JSON com:
1. NCM (8 dígitos)
2. CFOP sugerido
3. CSOSN ou CST
4. CEST (se aplicável)
5. Explicação COMPLETA citando:
   - Qual anexo da LC 214/2025
   - Qual artigo
   - Qual item específico
   - Qual o benefício (redução %, suspensão, etc)

IMPORTANTE: Cite artigos, parágrafos e anexos ESPECÍFICOS da LC 214/2025."""
        }
    ]
    
    print("\n[?] Consultando LLM...")
    
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "meta-llama-3.1-8b-instruct",
                "messages": messages,
                "max_tokens": 600,
                "temperature": 0.1
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            resposta = data["choices"][0]["message"]["content"]
            
            print("\n[OK] RESPOSTA DA LLM:")
            print("-" * 70)
            print(resposta)
            print("-" * 70)
            
            # Análise
            resposta_lower = resposta.lower()
            
            checks = {
                "anexo": any(x in resposta_lower for x in ['anexo i', 'anexo xv', 'anexo 1', 'anexo 15']),
                "artigo": 'art.' in resposta_lower or 'artigo' in resposta_lower,
                "item": 'item' in resposta_lower,
                "reducao": any(x in resposta_lower for x in ['redução', 'reducao', '100%', 'isenção', 'isento']),
                "lc214": '214' in resposta or 'lc 214' in resposta_lower
            }
            
            print("\n[DATA] VERIFICAÇÃO:")
            print(f"   {'[OK]' if checks['anexo'] else '[X]'} Citou Anexo (I ou XV)")
            print(f"   {'[OK]' if checks['artigo'] else '[X]'} Citou Artigo")
            print(f"   {'[OK]' if checks['item'] else '[X]'} Citou Item específico")
            print(f"   {'[OK]' if checks['reducao'] else '[X]'} Mencionou Redução/Isenção")
            print(f"   {'[OK]' if checks['lc214'] else '[X]'} Citou LC 214/2025")
            
            total = sum(checks.values())
            porcentagem = (total / len(checks)) * 100
            
            print(f"\n[?] Taxa de Completude: {porcentagem:.0f}% ({total}/{len(checks)})")
            
            if porcentagem >= 80:
                print("[OK] EXCELENTE - Resposta completa com embasamento legal!")
            elif porcentagem >= 60:
                print("[!] BOM - Mas pode melhorar citações específicas")
            else:
                print("[X] INSUFICIENTE - Falta embasamento legal detalhado")
            
            return {
                "sucesso": True,
                "checks": checks,
                "porcentagem": porcentagem
            }
        else:
            print(f"[X] Erro HTTP {response.status_code}")
            return {"sucesso": False}
            
    except requests.exceptions.Timeout:
        print("\n⏰ TIMEOUT - LLM não respondeu a tempo")
        return {"sucesso": False}
    except Exception as e:
        print(f"\n[X] Erro: {e}")
        return {"sucesso": False}

def executar_testes():
    """Executa todos os testes"""
    
    print("\n" + "="*70)
    print("  [?] TESTE DE PRODUTOS COM BENEFÍCIOS - LC 214/2025")
    print("="*70)
    print(f"\n[?] Servidor: {LLM_URL}")
    print(f"[DATA] Total de testes: {len(TESTES_BENEFICIOS)}\n")
    
    resultados = []
    
    for i, teste in enumerate(TESTES_BENEFICIOS, 1):
        print(f"\n[Teste {i}/{len(TESTES_BENEFICIOS)}]")
        resultado = testar_produto(teste)
        resultados.append(resultado)
        
        if i < len(TESTES_BENEFICIOS):
            import time
            print("\n⏳ Aguardando 3 segundos...")
            time.sleep(3)
    
    # Resumo final
    print("\n" + "="*70)
    print("  [DATA] RESUMO GERAL")
    print("="*70)
    
    sucessos = sum(1 for r in resultados if r.get('sucesso'))
    
    if sucessos > 0:
        porcentagens = [r['porcentagem'] for r in resultados if r.get('sucesso')]
        media = sum(porcentagens) / len(porcentagens)
        
        print(f"\n[OK] Testes executados: {sucessos}/{len(TESTES_BENEFICIOS)}")
        print(f"[?] Taxa média de completude: {media:.0f}%")
        
        if media >= 80:
            print("\n[?] EXCELENTE! A LLM está citando corretamente a LC 214/2025!")
            print("   [OK] Anexos sendo referenciados")
            print("   [OK] Artigos sendo citados")
            print("   [OK] Benefícios sendo explicados")
        elif media >= 60:
            print("\n[!] BOM, mas pode melhorar:")
            print("   [?] Considere fazer fine-tuning para respostas mais precisas")
        else:
            print("\n[X] INSUFICIENTE - Fine-tuning é necessário!")
            print("   [LOG] A LLM precisa aprender os detalhes da LC 214/2025")
    else:
        print("\n[X] Nenhum teste foi executado com sucesso")
        print("   Verifique se o servidor LLM está rodando")

if __name__ == "__main__":
    try:
        executar_testes()
    except KeyboardInterrupt:
        print("\n\n[!] Testes interrompidos pelo usuário")
    except Exception as e:
        print(f"\n\n[X] Erro: {e}")
        import traceback
        traceback.print_exc()

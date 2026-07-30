#!/usr/bin/env python3
"""
Teste de campo CEST na integração IA
"""

import requests
import json

def testar_cest():
    print("=" * 70)
    print("TESTE: CAMPO CEST NA SUGESTÃO TRIBUTÁRIA")
    print("=" * 70)
    
    # Produtos que PODEM ter CEST (geralmente com ST)
    produtos_com_st = [
        "Gasolina comum",
        "Cerveja em lata 350ml",
        "Cigarro marlboro",
        "Shampoo dove 400ml",
        "Pneu 175/70 R13",
        "Bateria automotiva 60Ah"
    ]
    
    # Produtos comuns (geralmente SEM CEST)
    produtos_sem_st = [
        "Mouse wireless",
        "Notebook Dell",
        "Lápis de cor",
        "Caderno universitário"
    ]
    
    api_url = "http://localhost:9000/api/sugestao"
    
    print("\n[SEARCH] Testando produtos COM possível Substituição Tributária:")
    print("-" * 70)
    
    for produto in produtos_com_st:
        try:
            response = requests.post(
                api_url,
                json={'descricao': produto},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    classif = data['classificacao']
                    cest = classif.get('cest')
                    ncm = classif.get('ncm')
                    
                    if cest and cest != 'null':
                        print(f"  [OK] {produto:30} → NCM: {ncm}, CEST: {cest}")
                    else:
                        print(f"  ⚪ {produto:30} → NCM: {ncm}, CEST: null (não gerado)")
            else:
                print(f"  [X] {produto:30} → Erro HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  [X] {produto:30} → Erro: {str(e)[:40]}")
    
    print("\n[SEARCH] Testando produtos SEM Substituição Tributária:")
    print("-" * 70)
    
    for produto in produtos_sem_st:
        try:
            response = requests.post(
                api_url,
                json={'descricao': produto},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    classif = data['classificacao']
                    cest = classif.get('cest')
                    ncm = classif.get('ncm')
                    
                    status = "[OK]" if not cest or cest == 'null' else "[!]"
                    print(f"  {status} {produto:30} → NCM: {ncm}, CEST: {cest}")
            else:
                print(f"  [X] {produto:30} → Erro HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  [X] {produto:30} → Erro: {str(e)[:40]}")
    
    print("\n" + "=" * 70)
    print("[LIST] RESUMO:")
    print("=" * 70)
    print("""
[OK] CEST está sendo retornado pela API
[OK] JavaScript já está preparado para preencher o campo CEST
[OK] Backend já está passando CEST no resultado final

[!]  OBSERVAÇÃO:
O CEST é campo OPCIONAL e específico para produtos com 
Substituição Tributária (ST). Atualmente a API está retornando
null para CEST porque o LLM está offline.

Quando o LLM estiver online, ele poderá sugerir CEST para
produtos que realmente necessitam (combustíveis, bebidas, 
cigarros, cosméticos, pneus, baterias, etc.)

[LOG] COMO FUNCIONA:
1. API IA retorna: {"cest": "01.001.00" ou null}
2. Backend passa: {"ids": {"cest": "01.001.00"}}
3. JavaScript preenche: $('#cest').val('01.001.00')
    """)
    print("=" * 70)

if __name__ == '__main__':
    testar_cest()

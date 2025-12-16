"""
[?] Teste SIMPLES - Café com Benefício LC 214/2025
"""

import requests

LLM_URL = "http://192.168.0.52:1234/v1/chat/completions"

print("="*70)
print("[?] TESTE: Café - Deve ter Redução 100% (Anexo I, Art. 8º)")
print("="*70)

messages = [
    {
        "role": "user",
        "content": "Classifique: Café torrado em grãos. NCM 09.01.21.10. Tem benefício na LC 214/2025? Responda brevemente."
    }
]

print("\n[?] Consultando LLM...")

try:
    response = requests.post(
        LLM_URL,
        json={
            "model": "meta-llama-3.1-8b-instruct",
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.1
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        resposta = data["choices"][0]["message"]["content"]
        
        print("\n[OK] RESPOSTA:")
        print("-" * 70)
        print(resposta)
        print("-" * 70)
        
        # Verificar palavras-chave
        r = resposta.lower()
        
        print("\n[DATA] ANÁLISE:")
        print(f"   {'[OK]' if 'anexo' in r else '[X]'} Mencionou Anexo")
        print(f"   {'[OK]' if '100' in r or 'cem' in r else '[X]'} Mencionou Redução 100%")
        print(f"   {'[OK]' if 'art' in r else '[X]'} Citou Artigo")
        print(f"   {'[OK]' if '214' in resposta else '[X]'} Citou LC 214/2025")
        
        tem_beneficio = 'anexo' in r and ('100' in r or 'redução' in r or 'isenção' in r)
        
        if tem_beneficio:
            print("\n[?] SUCESSO! LLM reconheceu o benefício fiscal!")
        else:
            print("\n[X] FALHA! LLM não identificou o benefício corretamente")
            
    else:
        print(f"[X] Erro HTTP {response.status_code}")
        
except requests.exceptions.Timeout:
    print("\n⏰ TIMEOUT - LLM demorou muito")
    print("   Tente aumentar o timeout ou reduzir max_tokens")
except Exception as e:
    print(f"\n[X] Erro: {e}")

"""
🧪 Teste Rápido - LLM com LC 214/2025
Testa um único caso para verificar se a LLM está respondendo
"""

import requests
import json

LLM_URL = "http://192.168.0.52:1234/v1/chat/completions"

def testar_cafe():
    """Testa classificação de café com LC 214/2025"""
    
    print("="*60)
    print("🧪 TESTE RÁPIDO - Café (Cesta Básica)")
    print("="*60)
    
    messages = [
        {
            "role": "system",
            "content": "Você é um especialista brasileiro em classificação tributária NCM com conhecimento da Lei Complementar 214/2025."
        },
        {
            "role": "user",
            "content": """Produto: Café torrado em grãos

NCM disponível: 09.01.21.10 - Café torrado, não descafeinado, em grão

Classifique este produto e informe:
1. NCM (8 dígitos)
2. Se há benefícios na LC 214/2025
3. Cite artigos específicos da lei se aplicável

Responda em formato JSON."""
        }
    ]
    
    print("\n🔄 Consultando LLM...")
    print(f"📡 URL: {LLM_URL}")
    
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "meta-llama-3.1-8b-instruct",
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.1
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            resposta = data["choices"][0]["message"]["content"]
            
            print("\n✅ RESPOSTA DA LLM:")
            print("-" * 60)
            print(resposta)
            print("-" * 60)
            
            # Análise
            tem_ncm = "09012110" in resposta or "0901.21.10" in resposta
            cita_lei = "214" in resposta or "LC 214" in resposta.upper()
            cita_artigo = "art" in resposta.lower() or "anexo" in resposta.lower()
            
            print("\n📊 ANÁLISE:")
            print(f"   ✅ NCM correto (09012110): {'SIM' if tem_ncm else 'NÃO'}")
            print(f"   📚 Cita LC 214/2025: {'SIM' if cita_lei else 'NÃO'}")
            print(f"   📄 Cita artigos/anexos: {'SIM' if cita_artigo else 'NÃO'}")
            
            if not cita_artigo:
                print("\n⚠️ RECOMENDAÇÃO: Execute o fine-tuning!")
                print("   python treinar_llm_ncm_lc214.py")
            else:
                print("\n🎉 LLM já fornece embasamento legal!")
            
        else:
            print(f"\n❌ Erro HTTP {response.status_code}")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("\n⏰ TIMEOUT - LLM não respondeu em 15 segundos")
        print("   Verifique se o servidor está rodando em 192.168.0.52:1234")
    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO DE CONEXÃO")
        print("   Servidor LLM não está acessível em 192.168.0.52:1234")
        print("\n💡 Verifique:")
        print("   1. LM Studio está aberto?")
        print("   2. Servidor está ativo na porta 1234?")
        print("   3. O IP 192.168.0.52 está correto?")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")

if __name__ == "__main__":
    try:
        testar_cafe()
    except KeyboardInterrupt:
        print("\n\n⚠️ Teste interrompido")

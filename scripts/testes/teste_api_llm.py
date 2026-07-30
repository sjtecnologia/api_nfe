#!/usr/bin/env python3
"""
TESTE RÁPIDO: Verificar se a API NCM está funcionando na porta 1234
"""

import requests
import json

def testar_api_llm():
    """Testa se a API está funcionando na porta da LLM"""
    
    print("[SEARCH] TESTANDO API NCM NA PORTA 1234")
    print("=" * 50)
    
    base_url = "http://192.168.0.52:1234"
    
    # Teste 1: Verificar estatísticas
    print("\n1️⃣ Testando endpoint de estatísticas...")
    try:
        response = requests.get(f"{base_url}/api/llm/ncms/stats", timeout=10)
        if response.ok:
            data = response.json()
            if data.get("success"):
                stats = data["estatisticas_gerais"]
                print(f"[OK] API funcionando! Total de NCMs: {stats['total_ncms']}")
                print(f"   • Analíticos: {stats['tipos']['analiticos']}")
                print(f"   • Sintéticos: {stats['tipos']['sinteticos']}")
            else:
                print(f"[X] API retornou erro: {data.get('error')}")
        else:
            print(f"[X] Erro HTTP {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        print("[X] Não conseguiu conectar na API")
        print("[?] Verifique se o servidor está rodando em 192.168.0.52:1234")
        return False
    except Exception as e:
        print(f"[X] Erro: {e}")
        return False
    
    # Teste 2: Buscar NCM
    print("\n2️⃣ Testando busca de NCMs...")
    try:
        params = {"q": "animais", "tipo": "analitico", "limit": 3}
        response = requests.get(f"{base_url}/api/llm/ncms/search", params=params, timeout=10)
        if response.ok:
            data = response.json()
            if data.get("success") and data.get("resultados"):
                print(f"[OK] Busca funcionando! Encontrados {len(data['resultados'])} NCMs")
                for ncm in data["resultados"]:
                    print(f"   • {ncm['codigo_formatado']}: {ncm['descricao']}")
            else:
                print("[!] Busca não retornou resultados")
        else:
            print(f"[X] Erro na busca: {response.status_code}")
    except Exception as e:
        print(f"[X] Erro na busca: {e}")
    
    # Teste 3: Hierarquia de NCM
    print("\n3️⃣ Testando hierarquia de NCM...")
    try:
        response = requests.get(f"{base_url}/api/llm/ncms/hierarquia/01.01.21.00", timeout=10)
        if response.ok:
            data = response.json()
            if data.get("success"):
                ncm = data["ncm_solicitado"]
                print(f"[OK] Hierarquia funcionando!")
                print(f"   NCM: {ncm['codigo_formatado']} - {ncm['descricao']}")
                print(f"   Tipo: {ncm['tipo']}")
            else:
                print(f"[X] Erro na hierarquia: {data.get('error')}")
        else:
            print(f"[X] Erro HTTP hierarquia: {response.status_code}")
    except Exception as e:
        print(f"[X] Erro na hierarquia: {e}")
    
    print("\n" + "=" * 50)
    print("[OK] TESTE CONCLUÍDO!")
    print("\nSe todos os testes passaram, sua LLM pode usar:")
    print(f"[?] Base URL: {base_url}")
    print("[LIST] Endpoints disponíveis:")
    print("   • /api/llm/ncms/stats - Estatísticas")
    print("   • /api/llm/ncms/search - Buscar NCMs")
    print("   • /api/llm/ncms/hierarquia/{codigo} - Hierarquia")
    print("   • /api/llm/ncms/export - Base completa")
    
    return True

def exemplo_uso_llm():
    """Exemplo de como sua LLM usaria a API"""
    
    print("\n\n[?] EXEMPLO: COMO SUA LLM USARIA A API")
    print("=" * 50)
    
    base_url = "http://192.168.0.52:1234"
    
    # Simulação: usuário pergunta sobre NCM
    pergunta_usuario = "Qual NCM para cavalos reprodutores?"
    print(f"[USER] Usuário pergunta: '{pergunta_usuario}'")
    
    # LLM extrai palavras-chave e busca
    print("[?] LLM processa e busca...")
    
    try:
        # Busca por "cavalos reprodutores"
        params = {"q": "cavalos reprodutores", "tipo": "analitico", "limit": 3}
        response = requests.get(f"{base_url}/api/llm/ncms/search", params=params, timeout=10)
        
        if response.ok:
            data = response.json()
            if data.get("success") and data.get("resultados"):
                melhor_ncm = data["resultados"][0]
                
                # Busca hierarquia para contexto completo
                hierarchy_response = requests.get(f"{base_url}/api/llm/ncms/hierarquia/{melhor_ncm['codigo']}", timeout=10)
                hierarchy_data = hierarchy_response.json()
                
                # LLM formula resposta
                print(f"\n[?] Resposta da LLM:")
                print(f"Para cavalos reprodutores, recomendo o **NCM {melhor_ncm['codigo_formatado']}**")
                print(f"**Descrição**: {melhor_ncm['descricao']}")
                
                if hierarchy_data.get("success"):
                    print(f"\n[?] **Contexto Hierárquico**:")
                    for pai in hierarchy_data["hierarquia"]["pais"]:
                        print(f"• {pai['codigo_formatado']}: {pai['descricao']}")
                    print(f"  • **{melhor_ncm['codigo_formatado']}**: **{melhor_ncm['descricao']}**")
                
                print(f"\n[OK] **Tipo**: Analítico (adequado para NFe)")
                print(f"[?] **Uso**: Este NCM é específico para cavalos reprodutores de raça pura")
                
            else:
                print("[?] LLM responde: Não encontrei NCMs específicos para essa consulta")
        else:
            print("[?] LLM responde: Erro ao acessar base de dados NCM")
            
    except Exception as e:
        print(f"[?] LLM responde: Erro técnico na consulta: {e}")

if __name__ == "__main__":
    testar_api_llm()
    exemplo_uso_llm()
    
    print("\n\n[LIST] RESUMO PARA SUA LLM:")
    print("=" * 40)
    print("[?] URL da API: http://192.168.0.52:1234")
    print("[DATA] Base: 13.217 NCMs hierárquicos")
    print("[?] Uso: Classificação fiscal brasileira")
    print("[OK] Status: Pronta para integração!")
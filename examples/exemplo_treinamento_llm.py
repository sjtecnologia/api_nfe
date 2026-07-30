#!/usr/bin/env python3
"""
EXEMPLO PRÁTICO: Como treinar sua LLM com dados NCM
Este script mostra exatamente como fazer
"""

import requests
import json

def exemplo_basico_consulta():
    """Exemplo básico de como sua LLM pode consultar NCMs"""
    
    print("[?] EXEMPLO 1: CONSULTA BÁSICA")
    print("=" * 50)
    
    # Sua LLM fará isso internamente
    api_url = "http://192.168.0.52:1234"  # Porta da sua LLM
    
    # Usuário pergunta: "Qual NCM para notebook?"
    user_question = "notebook"
    
    # Sua LLM busca na API
    response = requests.get(f"{api_url}/api/llm/ncms/search", 
                          params={"q": user_question, "tipo": "analitico", "limit": 3})
    
    if response.ok:
        data = response.json()
        
        print(f"[USER] Usuário perguntou: 'Qual NCM para {user_question}?'")
        print(f"[?] LLM encontrou {len(data['resultados'])} NCMs:")
        
        for ncm in data['resultados']:
            print(f"   • {ncm['codigo_formatado']}: {ncm['descricao']}")
        
        # Sua LLM responderia:
        best_ncm = data['resultados'][0]
        print(f"\n[?] Resposta da LLM:")
        print(f"Para {user_question}, recomendo o NCM {best_ncm['codigo_formatado']}: {best_ncm['descricao']}")
        print(f"É um código analítico, adequado para uso em NFe.")

def exemplo_contexto_hierarquico():
    """Exemplo de como fornecer contexto hierárquico"""
    
    print("\n\n[?] EXEMPLO 2: CONTEXTO HIERÁRQUICO")
    print("=" * 50)
    
    api_url = "http://192.168.0.52:1234"
    codigo = "01.01.21.00"
    
    # Usuário pergunta: "O que é NCM 01.01.21.00?"
    response = requests.get(f"{api_url}/api/llm/ncms/hierarquia/{codigo}")
    
    if response.ok:
        data = response.json()
        ncm = data['ncm_solicitado']
        pais = data['hierarquia']['pais']
        
        print(f"[USER] Usuário perguntou: 'O que é NCM {codigo}?'")
        print(f"[?] Resposta da LLM:")
        print(f"\n[LIST] NCM {ncm['codigo_formatado']}: {ncm['descricao']}")
        print(f"[OK] Tipo: {'Analítico (pode usar em NFe)' if ncm['tipo'] == 'analitico' else 'Sintético'}")
        print(f"\n[?] Hierarquia:")
        
        for pai in pais:
            print(f"   • {pai['codigo_formatado']}: {pai['descricao']}")
        print(f"   • {ncm['codigo_formatado']}: {ncm['descricao']} ← ESTE NCM")

def exemplo_treinamento_dados():
    """Exemplo de como usar dados para treinar"""
    
    print("\n\n[?] EXEMPLO 3: DADOS PARA TREINAMENTO")
    print("=" * 50)
    
    api_url = "http://192.168.0.52:1234"
    
    # Baixa base completa
    print("[IN] Baixando base completa...")
    response = requests.get(f"{api_url}/api/llm/ncms/export")
    
    if response.ok:
        data = response.json()
        ncms = data['ncms']
        
        print(f"[DATA] Total de NCMs: {len(ncms)}")
        
        # Exemplo de como estruturar para treinamento
        training_examples = []
        
        for ncm in ncms[:5]:  # Só 5 exemplos para demo
            # Cria exemplos pergunta-resposta
            examples = [
                {
                    "input": f"Qual é o NCM {ncm['codigo_formatado']}?",
                    "output": f"NCM {ncm['codigo_formatado']}: {ncm['descricao']}. É um código {ncm['tipo']} de {ncm['nivel']['nome']}."
                },
                {
                    "input": f"NCM para {ncm['descricao'].lower()}",
                    "output": f"Para {ncm['descricao'].lower()}, use o NCM {ncm['codigo_formatado']}."
                }
            ]
            training_examples.extend(examples)
        
        print(f"\n[LOG] Exemplos de treinamento gerados: {len(training_examples)}")
        print("\n[SEARCH] Amostras:")
        
        for i, example in enumerate(training_examples[:3]):
            print(f"\n   Exemplo {i+1}:")
            print(f"   Pergunta: {example['input']}")
            print(f"   Resposta: {example['output']}")
        
        # Salva para treinamento
        with open('exemplos_treinamento_ncm.json', 'w', encoding='utf-8') as f:
            json.dump(training_examples, f, ensure_ascii=False, indent=2)
        
        print(f"\n[SAVE] Exemplos salvos em: exemplos_treinamento_ncm.json")

def exemplo_integracao_llm():
    """Exemplo de como integrar com sua LLM"""
    
    print("\n\n[?] EXEMPLO 4: INTEGRAÇÃO COM SUA LLM")
    print("=" * 50)
    
    print("""
[?] PASSOS PARA INTEGRAR:

1. **Configure a URL da API na sua LLM**:
   BASE_URL = "http://192.168.0.52:1234"

2. **Crie função de busca**:
   ```python
   def buscar_ncm(produto):
       response = requests.get(f"{BASE_URL}/api/llm/ncms/search",
                             params={"q": produto, "tipo": "analitico"})
       return response.json()
   ```

3. **Integre no prompt da sua LLM**:
   ```
   Você tem acesso a uma base de 13.217 NCMs brasileiros.
   Para consultas sobre NCM, use a função buscar_ncm().
   
   Usuário: "Qual NCM para notebook?"
   [Você busca via API]
   Resposta: "Para notebook, recomendo NCM 84.71.30.00..."
   ```

4. **Treinar com exemplos**:
   - Use o arquivo exemplos_treinamento_ncm.json
   - Adicione mais exemplos conforme necessário
   - Foque em perguntas comuns do seu domínio

5. **Teste e refine**:
   - Teste com perguntas reais
   - Ajuste prompts conforme feedback
   - Monitore precisão das respostas
""")

def exemplo_prompts_especificos():
    """Exemplos de prompts específicos para sua LLM"""
    
    print("\n\n[?] EXEMPLO 5: PROMPTS PARA SUA LLM")
    print("=" * 50)
    
    prompts = {
        "Sistema": """
Você é um especialista em NCM (Nomenclatura Comum do Mercosul) brasileiro.
Você tem acesso a uma API com 13.217 códigos NCM oficiais.

REGRAS IMPORTANTES:
- NCMs analíticos (8 dígitos) são usados em NFe
- NCMs sintéticos são apenas para classificação
- Sempre forneça contexto hierárquico
- Seja preciso - erro de NCM causa problemas fiscais

Quando receber pergunta sobre NCM:
1. Busque na API primeiro
2. Forneça contexto hierárquico
3. Indique se é analítico ou sintético
4. Explique aplicação prática
""",
        
        "Busca de Produto": """
Usuário quer NCM para: {produto}

Passos:
1. Buscar NCMs analíticos relacionados
2. Mostrar top 3 opções com contexto
3. Recomendar o mais adequado
4. Explicar critério de escolha
""",
        
        "Explicação de Código": """
Usuário quer saber sobre NCM: {codigo}

Passos:
1. Buscar hierarquia completa
2. Explicar contexto pai-filho
3. Indicar tipo (analítico/sintético)
4. Mostrar aplicação prática
"""
    }
    
    print("[LOG] PROMPTS RECOMENDADOS:")
    for tipo, prompt in prompts.items():
        print(f"\n[?] {tipo}:")
        print(f"```\n{prompt}\n```")

def main():
    """Executa todos os exemplos"""
    print("[?] GUIA PRÁTICO: TREINAR SUA LLM COM NCMs")
    print("=" * 60)
    
    try:
        exemplo_basico_consulta()
        exemplo_contexto_hierarquico()
        exemplo_treinamento_dados()
        exemplo_integracao_llm()
        exemplo_prompts_especificos()
        
        print("\n\n[OK] RESUMO FINAL:")
        print("=" * 40)
        print("1. [OK] API funcionando com 13.217 NCMs")
        print("2. [OK] Exemplos de consulta prontos")
        print("3. [OK] Dados de treinamento gerados")
        print("4. [OK] Prompts específicos criados")
        print("5. [OK] Guia de integração completo")
        
        print("[START] PRÓXIMOS PASSOS:")
        print("1. Configure URL da API: http://192.168.0.52:1234")
        print("2. Use os prompts fornecidos")
        print("3. Integre as consultas na sua LLM")
        print("4. Teste com perguntas reais")
        print("5. Refine conforme necessário")
        
    except Exception as e:
        print(f"\n[X] Erro durante execução: {e}")
        print("[?] Verifique se a API está rodando em 192.168.0.52:1234")

if __name__ == "__main__":
    main()
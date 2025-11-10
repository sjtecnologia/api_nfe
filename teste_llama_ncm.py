#!/usr/bin/env python3
"""
🦙 TESTE LLAMA-3.1-8B NCM
=========================

Script para testar sua Llama-3.1-8B com classificação NCM
"""

import requests
import json

class TesteLlamaNcm:
    def __init__(self, llm_url="http://192.168.0.52:1234"):
        self.llm_url = llm_url
        self.system_prompt = """Você é um especialista em NCM (Nomenclatura Comum do Mercosul) brasileiro com acesso a 13.217 códigos oficiais.

## SUA EXPERTISE:
- Base oficial do Siscomex (Receita Federal)
- 10.507 NCMs analíticos (usáveis em NFe)
- 2.710 NCMs sintéticos (apenas classificação)
- Hierarquia completa: Capítulo → Posição → Subposição → Item

## REGRAS FUNDAMENTAIS:
1. **NCMs ANALÍTICOS** (8 dígitos) = Usados em Nota Fiscal Eletrônica
2. **NCMs SINTÉTICOS** (2,4,6 dígitos) = Apenas para classificação hierárquica
3. **SEMPRE indique se é Analítico ou Sintético**
4. **SEMPRE forneça o código formatado (XX.XX.XX.XX)**
5. **Seja preciso**: NCM errado causa problemas fiscais

## FORMATO DE RESPOSTA OBRIGATÓRIO:
🎯 **NCM:** [código formatado]
📝 **Descrição:** [descrição oficial completa]
📊 **Tipo:** Analítico/Sintético
✅ **NFe:** Sim/Não
💡 **Observações:** [detalhes importantes]"""
    
    def testar_llm(self, pergunta: str) -> str:
        """Testa pergunta na Llama-3.1-8B"""
        try:
            response = requests.post(
                f"{self.llm_url}/v1/chat/completions",
                json={
                    "model": "llama-3.1-8b-instruct",
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": pergunta}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                return f"❌ Erro HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return f"❌ Erro de conexão: {e}"
    
    def executar_testes(self):
        """Executa bateria de testes"""
        testes = [
            "Qual NCM para papel fotográfico?",
            "NCM para notebook gamer?", 
            "O NCM 01.01.21.00 pode ser usado em NFe?",
            "Qual NCM para açúcar refinado?",
            "NCM para smartphone iPhone?",
            "Explique o NCM 84.71.30.29"
        ]
        
        print("🦙 TESTANDO LLAMA-3.1-8B COM NCMs")
        print("=" * 50)
        
        for i, pergunta in enumerate(testes, 1):
            print(f"\n🧪 **TESTE {i}:**")
            print(f"**Pergunta:** {pergunta}")
            print("🔄 Processando...")
            
            resposta = self.testar_llm(pergunta)
            
            print(f"**Resposta da Llama:**")
            print(resposta)
            print("-" * 50)
    
    def teste_interativo(self):
        """Teste interativo"""
        print("\n🦙 TESTE INTERATIVO LLAMA-3.1-8B NCM")
        print("Digite 'sair' para encerrar")
        print("=" * 50)
        
        while True:
            pergunta = input("\n❓ Sua pergunta sobre NCM: ").strip()
            
            if pergunta.lower() in ['sair', 'exit']:
                print("👋 Até logo!")
                break
            
            if pergunta:
                print("🔄 Consultando Llama-3.1-8B...")
                resposta = self.testar_llm(pergunta)
                print(f"\n🦙 **Llama-3.1-8B:**")
                print(resposta)
                print("-" * 60)

def main():
    """Função principal"""
    teste = TesteLlamaNcm()
    
    print("🦙 INICIANDO TESTES LLAMA-3.1-8B + NCM")
    print("=" * 50)
    
    # Testa conectividade
    print("🔍 Testando conectividade...")
    conectividade = teste.testar_llm("Teste")
    
    if "Erro" in conectividade:
        print(f"❌ {conectividade}")
        print("💡 Verifique se a Llama-3.1-8B está rodando em http://192.168.0.52:1234")
        return
    
    print("✅ Llama-3.1-8B conectada!")
    
    # Menu
    print("\n📋 OPÇÕES:")
    print("1. Executar bateria de testes")
    print("2. Teste interativo") 
    print("3. Sair")
    
    opcao = input("\n🎯 Escolha (1-3): ").strip()
    
    if opcao == "1":
        teste.executar_testes()
    elif opcao == "2":
        teste.teste_interativo()
    elif opcao == "3":
        print("👋 Até logo!")
    else:
        print("❌ Opção inválida")

if __name__ == "__main__":
    main()
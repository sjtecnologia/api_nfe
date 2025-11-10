#!/usr/bin/env python3
"""
🦙 LLAMA-3.1-8B + API NCM OFICIAL
=================================

Conecta sua Llama-3.1-8B com a base oficial de 13.217 NCMs
Resultado: Classificação precisa com dados reais
"""

import requests
import json
from typing import Dict, List

class LlamaNcmExpert:
    def __init__(self, 
                 llm_url="http://192.168.0.52:1234",
                 ncm_api="http://localhost:8081"):
        self.llm_url = llm_url
        self.ncm_api = ncm_api
        
        # System prompt otimizado
        self.system_prompt = """Você é um especialista em NCM brasileiro. Você receberá dados NCM oficiais do Siscomex e deve responder baseado APENAS nestes dados.

FORMATO OBRIGATÓRIO:
🎯 **NCM:** [código exato fornecido]
📝 **Descrição:** [descrição exata fornecida]  
📊 **Tipo:** [Analítico/Sintético exato]
✅ **NFe:** [Sim se Analítico, Não se Sintético]
💡 **Observações:** [análise técnica do NCM]

REGRAS:
- Use APENAS os dados NCM fornecidos
- NÃO invente códigos ou descrições
- Analíticos (8 dígitos) = usam em NFe
- Sintéticos (2,4,6 dígitos) = apenas classificação"""
    
    def buscar_ncm_oficial(self, produto: str) -> List[Dict]:
        """Busca NCMs na base oficial"""
        try:
            response = requests.get(
                f"{self.ncm_api}/api/llm/ncms/search",
                params={"q": produto, "tipo": "analitico", "limit": 3},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("resultados", [])
        except:
            pass
        return []
    
    def obter_hierarquia_ncm(self, codigo: str) -> Dict:
        """Obtém hierarquia oficial do NCM"""
        try:
            response = requests.get(
                f"{self.ncm_api}/api/llm/ncms/hierarquia/{codigo}",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}
    
    def consultar_llm_com_dados(self, pergunta: str, contexto_ncm: str) -> str:
        """Consulta Llama com dados NCM oficiais"""
        prompt = f"""DADOS NCM OFICIAIS:
{contexto_ncm}

PERGUNTA DO USUÁRIO: {pergunta}

Responda baseado APENAS nos dados NCM fornecidos acima."""
        
        try:
            response = requests.post(
                f"{self.llm_url}/v1/chat/completions",
                json={
                    "model": "llama-3.1-8b-instruct",
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 400,
                    "temperature": 0.1,
                    "top_p": 0.9
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"❌ Erro na LLM: {e}"
        
        return "❌ Erro ao consultar LLM"
    
    def classificar_produto(self, produto: str) -> str:
        """Classificação completa com dados oficiais"""
        print(f"🔍 Buscando NCMs para: {produto}")
        
        # 1. Busca NCMs oficiais
        ncms = self.buscar_ncm_oficial(produto)
        
        if not ncms:
            return f"❌ Nenhum NCM oficial encontrado para '{produto}'"
        
        # 2. Monta contexto com dados oficiais
        contexto = f"NCMs OFICIAIS ENCONTRADOS PARA '{produto.upper()}':\\n\\n"
        
        for i, ncm in enumerate(ncms, 1):
            contexto += f"{i}. **NCM {ncm.get('codigo_formatado', 'N/A')}**\\n"
            contexto += f"   Descrição: {ncm.get('descricao', 'N/A')}\\n"
            contexto += f"   Tipo: {ncm.get('tipo', 'N/A').title()}\\n"
            contexto += f"   Relevância: {ncm.get('relevancia', 'N/A')}\\n\\n"
        
        # 3. Consulta Llama com dados reais
        pergunta = f"Com base nos NCMs oficiais fornecidos, qual o melhor NCM para classificar '{produto}' em uma NFe?"
        
        print("🦙 Consultando Llama-3.1-8B...")
        resposta = self.consultar_llm_com_dados(pergunta, contexto)
        
        return resposta
    
    def explicar_ncm_codigo(self, codigo: str) -> str:
        """Explica NCM específico com dados oficiais"""
        print(f"📋 Buscando dados oficiais do NCM: {codigo}")
        
        # 1. Busca hierarquia oficial
        hierarquia = self.obter_hierarquia_ncm(codigo)
        
        if not hierarquia:
            return f"❌ NCM {codigo} não encontrado na base oficial"
        
        # 2. Monta contexto hierárquico
        contexto = f"DADOS OFICIAIS DO NCM {codigo}:\\n\\n"
        
        ncm_info = hierarquia.get("ncm", {})
        contexto += f"**NCM:** {ncm_info.get('codigo_formatado', codigo)}\\n"
        contexto += f"**Descrição:** {ncm_info.get('descricao', 'N/A')}\\n"
        contexto += f"**Tipo:** {ncm_info.get('tipo', 'N/A').title()}\\n\\n"
        
        if "hierarquia" in hierarquia:
            contexto += "**HIERARQUIA OFICIAL:**\\n"
            for pai in hierarquia["hierarquia"].get("pais", []):
                contexto += f"- {pai.get('codigo_formatado', 'N/A')}: {pai.get('descricao', 'N/A')}\\n"
        
        # 3. Consulta Llama
        pergunta = f"Explique o NCM {codigo} e seu uso em NFe baseado nos dados oficiais fornecidos"
        
        print("🦙 Consultando Llama-3.1-8B...")
        resposta = self.consultar_llm_com_dados(pergunta, contexto)
        
        return resposta
    
    def chat_interativo(self):
        """Chat com classificação oficial"""
        print("\\n🦙 LLAMA-3.1-8B + BASE NCM OFICIAL")
        print("Comandos:")
        print("• classificar [produto] - Classifica com dados oficiais")
        print("• explicar [código] - Explica NCM com hierarquia oficial")
        print("• sair - Encerra")
        print("=" * 60)
        
        while True:
            try:
                entrada = input("\\n❓ Comando: ").strip()
                
                if entrada.lower() in ['sair', 'exit']:
                    print("👋 Até logo!")
                    break
                
                if entrada.startswith("classificar "):
                    produto = entrada[12:].strip()
                    if produto:
                        resposta = self.classificar_produto(produto)
                        print(f"\\n{resposta}\\n")
                        print("-" * 60)
                
                elif entrada.startswith("explicar "):
                    codigo = entrada[9:].strip()
                    if codigo:
                        resposta = self.explicar_ncm_codigo(codigo)
                        print(f"\\n{resposta}\\n")
                        print("-" * 60)
                
                else:
                    # Classificação direta
                    resposta = self.classificar_produto(entrada)
                    print(f"\\n{resposta}\\n")
                    print("-" * 60)
                    
            except KeyboardInterrupt:
                print("\\n👋 Interrompido")
                break

def main():
    """Função principal"""
    print("🦙 LLAMA-3.1-8B + API NCM OFICIAL")
    print("=" * 50)
    
    expert = LlamaNcmExpert()
    
    # Testa conectividade
    print("🔍 Testando conexões...")
    
    # Teste LLM
    try:
        response = requests.get(f"{expert.llm_url}/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ Llama-3.1-8B conectada")
        else:
            print("❌ Llama-3.1-8B não responde")
            return
    except:
        print("❌ Llama-3.1-8B não conectada")
        return
    
    # Teste API NCM
    try:
        response = requests.get(f"{expert.ncm_api}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API NCM conectada")
        else:
            print("❌ API NCM não responde")
            return
    except:
        print("❌ API NCM não conectada")
        print("💡 Execute: python3 api_ncm_standalone.py")
        return
    
    print("\\n🎉 TUDO CONECTADO! Sistema híbrido pronto!")
    
    # Teste rápido
    print("\\n🧪 TESTE RÁPIDO:")
    resultado = expert.classificar_produto("papel fotográfico")
    print(resultado)
    
    print("\\n" + "=" * 60)
    expert.chat_interativo()

if __name__ == "__main__":
    main()
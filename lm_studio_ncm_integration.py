"""
🎯 INTEGRAÇÃO NCM COM LM STUDIO
================================

Conecta sua LLM (CodeLlama ou outra) rodando no LM Studio
com a base de dados NCM oficial brasileira.

Configuração:
- LLM: http://192.168.0.52:1234 (LM Studio)
- API NCM: http://localhost:8081 (nossa API)
"""

import requests
import json
from typing import Dict, List

class NCMLMStudioIntegration:
    """Integração NCM otimizada para LM Studio"""
    
    def __init__(self, 
                 llm_url: str = "http://192.168.0.52:1234", 
                 ncm_api_url: str = "http://localhost:8081"):
        self.llm_url = llm_url
        self.ncm_api_url = ncm_api_url
        self.llm_available = self._check_llm()
        self.ncm_api_available = self._check_ncm_api()
    
    def _check_llm(self) -> bool:
        """Verifica se LLM está rodando"""
        try:
            # LM Studio geralmente responde em /v1/models
            response = requests.get(f"{self.llm_url}/v1/models", timeout=5)
            if response.status_code == 200:
                print("✅ LLM (LM Studio) conectada")
                return True
        except:
            pass
        
        # Tenta endpoint direto
        try:
            response = requests.post(
                f"{self.llm_url}/v1/chat/completions",
                json={
                    "model": "local-model",
                    "messages": [{"role": "user", "content": "teste"}],
                    "max_tokens": 10
                },
                timeout=5
            )
            print("✅ LLM (LM Studio) conectada")
            return True
        except Exception as e:
            print(f"❌ LLM não conectada: {e}")
            return False
    
    def _check_ncm_api(self) -> bool:
        """Verifica se API NCM está rodando"""
        try:
            response = requests.get(f"{self.ncm_api_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API NCM conectada")
                return True
        except Exception as e:
            print(f"❌ API NCM não conectada: {e}")
            return False
    
    def buscar_ncms(self, termo: str, limite: int = 3) -> List[Dict]:
        """Busca NCMs relacionados ao termo"""
        if not self.ncm_api_available:
            return []
        
        try:
            response = requests.get(
                f"{self.ncm_api_url}/api/llm/ncms/search",
                params={"q": termo, "tipo": "analitico", "limit": limite},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
        except Exception as e:
            print(f"Erro na busca NCM: {e}")
        
        return []
    
    def obter_hierarquia(self, codigo_ncm: str) -> Dict:
        """Obtém contexto hierárquico do NCM"""
        if not self.ncm_api_available:
            return {}
        
        try:
            response = requests.get(
                f"{self.ncm_api_url}/api/llm/ncms/hierarquia/{codigo_ncm}",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Erro ao obter hierarquia: {e}")
        
        return {}
    
    def consultar_llm(self, pergunta: str, contexto_ncm: str = "") -> str:
        """Consulta a LLM via LM Studio"""
        if not self.llm_available:
            return "❌ LLM não disponível"
        
        # Monta prompt otimizado para LM Studio
        prompt = f"""Você é um especialista em NCM (Nomenclatura Comum do Mercosul) brasileiro.

DADOS NCM DISPONÍVEIS:
{contexto_ncm}

PERGUNTA: {pergunta}

INSTRUÇÕES:
- Use APENAS os dados NCM fornecidos acima
- Seja preciso e direto
- NCMs analíticos (8 dígitos) podem ser usados em NFe
- NCMs sintéticos são apenas para classificação
- Sempre mencione o código NCM recomendado

RESPOSTA:"""

        try:
            # Formato compatível com LM Studio
            response = requests.post(
                f"{self.llm_url}/v1/chat/completions",
                json={
                    "model": "local-model",  # LM Studio aceita qualquer nome
                    "messages": [
                        {
                            "role": "system", 
                            "content": "Você é um especialista em classificação fiscal brasileira (NCM)."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                return f"❌ Erro LLM: {response.status_code}"
                
        except Exception as e:
            return f"❌ Erro ao consultar LLM: {e}"
    
    def classificar_produto(self, produto: str) -> str:
        """Classifica produto usando NCM + LLM"""
        print(f"🔍 Classificando: {produto}")
        
        # 1. Busca NCMs relacionados
        ncms = self.buscar_ncms(produto, limite=3)
        
        if not ncms:
            return f"❌ Nenhum NCM encontrado para '{produto}'"
        
        # 2. Monta contexto
        contexto = "NCMs RELEVANTES:\n"
        for i, ncm in enumerate(ncms, 1):
            contexto += f"{i}. NCM {ncm.get('codigo_ncm', 'N/A')}: {ncm.get('descricao', 'N/A')}\n"
            contexto += f"   Tipo: {ncm.get('tipo_ncm', 'N/A')} | Score: {ncm.get('score', 0):.2f}\n\n"
        
        # 3. Consulta LLM
        pergunta = f"Qual o melhor NCM para classificar '{produto}' em uma NFe?"
        resposta = self.consultar_llm(pergunta, contexto)
        
        return resposta
    
    def explicar_ncm(self, codigo_ncm: str) -> str:
        """Explica um código NCM específico"""
        print(f"📋 Explicando NCM: {codigo_ncm}")
        
        # 1. Busca hierarquia
        hierarquia = self.obter_hierarquia(codigo_ncm)
        
        if not hierarquia:
            return f"❌ NCM {codigo_ncm} não encontrado"
        
        # 2. Monta contexto hierárquico
        contexto = f"INFORMAÇÕES DO NCM {codigo_ncm}:\n"
        
        ncm_info = hierarquia.get("ncm", {})
        contexto += f"Descrição: {ncm_info.get('descricao', 'N/A')}\n"
        contexto += f"Tipo: {ncm_info.get('tipo_ncm', 'N/A')}\n\n"
        
        if "hierarquia" in hierarquia:
            contexto += "HIERARQUIA:\n"
            for pai in hierarquia["hierarquia"].get("pais", []):
                contexto += f"- {pai.get('codigo', 'N/A')}: {pai.get('descricao', 'N/A')}\n"
        
        # 3. Consulta LLM
        pergunta = f"Explique o NCM {codigo_ncm} e seu uso em NFe"
        resposta = self.consultar_llm(pergunta, contexto)
        
        return resposta
    
    def chat_interativo(self):
        """Interface de chat simples"""
        print("\n🤖 CHAT NCM - Digite 'sair' para encerrar")
        print("Comandos:")
        print("- classificar [produto]: Classifica um produto")  
        print("- explicar [código]: Explica um NCM")
        print("- ou faça uma pergunta livre\n")
        
        while True:
            try:
                pergunta = input("❓ Você: ").strip()
                
                if pergunta.lower() in ['sair', 'exit', 'quit']:
                    print("👋 Até logo!")
                    break
                
                if not pergunta:
                    continue
                
                print("🤔 Processando...")
                
                # Comandos específicos
                if pergunta.startswith("classificar "):
                    produto = pergunta[12:].strip()
                    resposta = self.classificar_produto(produto)
                
                elif pergunta.startswith("explicar "):
                    codigo = pergunta[9:].strip()
                    resposta = self.explicar_ncm(codigo)
                
                else:
                    # Pergunta livre - tenta extrair contexto
                    palavras = pergunta.lower().split()
                    termos = [p for p in palavras if len(p) > 3][:3]
                    termo_busca = " ".join(termos)
                    
                    ncms = self.buscar_ncms(termo_busca, limite=2)
                    contexto = ""
                    
                    if ncms:
                        contexto = "NCMs RELACIONADOS:\n"
                        for ncm in ncms:
                            contexto += f"- NCM {ncm.get('codigo_ncm', 'N/A')}: {ncm.get('descricao', 'N/A')}\n"
                    
                    resposta = self.consultar_llm(pergunta, contexto)
                
                print(f"\n🎯 NCM Expert: {resposta}\n")
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\n👋 Interrompido pelo usuário")
                break
            except Exception as e:
                print(f"❌ Erro: {e}")

def main():
    """Função principal"""
    print("🚀 INICIANDO INTEGRAÇÃO NCM + LM STUDIO")
    print("=" * 50)
    
    # Inicializa integração
    integration = NCMLMStudioIntegration()
    
    if not integration.llm_available:
        print("\n❌ LLM não está rodando em http://192.168.0.52:1234")
        print("💡 Verifique se o LM Studio está ativo")
        return
    
    if not integration.ncm_api_available:
        print("\n❌ API NCM não está rodando")
        print("💡 Execute: python3 api_ncm_standalone.py")
        return
    
    print("\n✅ Tudo conectado! Iniciando chat...")
    
    # Testa integração
    print("\n🧪 TESTE RÁPIDO:")
    resultado = integration.classificar_produto("notebook gamer")
    print(f"Teste: {resultado[:100]}...")
    
    # Inicia chat
    integration.chat_interativo()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Sistema Simples de Consulta NCM para LLM
Usa apenas a API existente - sem dependências externas
"""

import requests
import json
import re
from typing import List, Dict, Any

class SimpleNCMConsultant:
    """Consultor NCM simples usando apenas requests"""
    
    def __init__(self, api_base_url: str = "http://192.168.0.52:8081"):
        self.api_base_url = api_base_url
        self.test_connection()
    
    def test_connection(self):
        """Testa conexão com a API"""
        try:
            response = requests.get(f"{self.api_base_url}/api/llm/ncms/stats", timeout=10)
            if response.ok:
                data = response.json()
                total = data.get('estatisticas_gerais', {}).get('total_ncms', 0)
                print(f"[OK] Conectado à API - {total} NCMs disponíveis")
            else:
                print(f"[!] API respondeu com status {response.status_code}")
        except Exception as e:
            print(f"[X] Erro de conexão: {e}")
            print(f"[?] Verifique se a API está rodando em {self.api_base_url}")
    
    def search_ncm(self, query: str, tipo: str = "todos", limit: int = 5) -> Dict:
        """Busca NCMs via API"""
        try:
            params = {
                "q": query,
                "tipo": tipo,
                "limit": limit
            }
            
            response = requests.get(
                f"{self.api_base_url}/api/llm/ncms/search",
                params=params,
                timeout=15
            )
            
            if response.ok:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}",
                    "resultados": []
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "resultados": []
            }
    
    def get_hierarchy(self, codigo: str) -> Dict:
        """Obtém hierarquia de um NCM"""
        try:
            response = requests.get(
                f"{self.api_base_url}/api/llm/ncms/hierarquia/{codigo}",
                timeout=10
            )
            
            if response.ok:
                return response.json()
            else:
                return {"success": False, "error": f"Status {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_stats(self) -> Dict:
        """Obtém estatísticas da base"""
        try:
            response = requests.get(f"{self.api_base_url}/api/llm/ncms/stats", timeout=10)
            if response.ok:
                return response.json()
            else:
                return {"success": False}
        except:
            return {"success": False}
    
    def explain_ncm(self, codigo: str) -> str:
        """Explica um NCM específico com contexto"""
        hierarchy = self.get_hierarchy(codigo)
        
        if not hierarchy.get("success"):
            return f"[X] NCM {codigo} não encontrado ou erro na consulta."
        
        ncm = hierarchy["ncm_solicitado"]
        pais = hierarchy["hierarquia"]["pais"]
        
        explanation = []
        explanation.append(f"[LIST] **NCM {ncm['codigo_formatado']}**: {ncm['descricao']}")
        
        # Tipo
        if ncm['tipo'] == 'analitico':
            explanation.append("   [OK] **Tipo**: Analítico (pode receber lançamentos em NFe)")
        else:
            explanation.append("   [?] **Tipo**: Sintético (apenas para classificação hierárquica)")
        
        # Hierarquia
        if pais:
            explanation.append("   [?] **Hierarquia**:")
            for pai in pais:
                explanation.append(f"      • {pai['codigo_formatado']}: {pai['descricao']}")
            explanation.append(f"      • **{ncm['codigo_formatado']}**: **{ncm['descricao']}**")
        
        return "\\n".join(explanation)
    
    def find_best_ncm_for_product(self, product_description: str) -> str:
        """Encontra melhor NCM para um produto"""
        # Busca apenas NCMs analíticos (usáveis em NFe)
        result = self.search_ncm(product_description, tipo="analitico", limit=3)
        
        if not result.get("success") or not result.get("resultados"):
            return f"""
[X] **Nenhum NCM analítico encontrado** para: "{product_description}"

[?] **Sugestões**:
- Tente palavras-chave mais específicas
- Use termos técnicos do produto
- Consulte a nomenclatura oficial do produto

[SEARCH] **Exemplo**: Em vez de "notebook", tente "computador portátil" ou "máquina processamento dados"
"""
        
        response_parts = []
        response_parts.append(f"[SEARCH] **Melhores NCMs para**: {product_description}")
        response_parts.append("")
        
        # Mostra os 3 melhores resultados
        for i, ncm in enumerate(result["resultados"], 1):
            response_parts.append(f"**{i}. NCM {ncm['codigo_formatado']}**: {ncm['descricao']}")
            
            # Adiciona contexto hierárquico se disponível
            hierarchy = self.get_hierarchy(ncm['codigo'])
            if hierarchy.get("success") and hierarchy["hierarquia"]["pais"]:
                response_parts.append("   [?] **Contexto**:")
                for pai in hierarchy["hierarquia"]["pais"]:
                    response_parts.append(f"      • {pai['codigo_formatado']}: {pai['descricao']}")
            
            response_parts.append(f"   [?] **Relevância**: {ncm.get('relevancia', 'N/A')}")
            response_parts.append("")
        
        # Recomendação
        best_ncm = result["resultados"][0]
        response_parts.append(f"[?] **Recomendação**: Use o NCM **{best_ncm['codigo_formatado']}** para operações em NFe.")
        
        return "\\n".join(response_parts)
    
    def intelligent_response(self, user_question: str) -> str:
        """Resposta inteligente baseada no tipo de pergunta"""
        question_lower = user_question.lower().strip()
        
        # Detecta tipo de pergunta
        
        # 1. Pergunta sobre NCM específico
        ncm_pattern = r'ncm\\s+([0-9.]+)'
        ncm_match = re.search(ncm_pattern, question_lower)
        if ncm_match:
            codigo = ncm_match.group(1)
            return self.explain_ncm(codigo)
        
        # 2. Pergunta "qual NCM para..."
        if any(word in question_lower for word in ['qual ncm', 'que ncm', 'ncm para']):
            # Extract product description
            product_terms = re.sub(r'qual\\s+ncm\\s+para\\s*', '', question_lower)
            product_terms = re.sub(r'que\\s+ncm\\s+.*?para\\s*', '', product_terms)
            product_terms = product_terms.strip('?.,!').strip()
            
            if product_terms:
                return self.find_best_ncm_for_product(product_terms)
        
        # 3. Pergunta sobre diferenças ou conceitos
        if any(word in question_lower for word in ['diferença', 'diferenca', 'o que é', 'conceito']):
            if 'sintetico' in question_lower and 'analitico' in question_lower:
                return """
[?] **Diferença entre NCM Sintético e Analítico**:

[?] **NCM SINTÉTICO**:
• **Função**: Apenas classificação hierárquica
• **Estrutura**: 2, 4 ou 6 dígitos
• **Uso em NFe**: [X] NÃO pode ser usado
• **Exemplo**: `84.71` (Máquinas para processamento de dados)
• **Quantidade**: 2.710 códigos na base

[OK] **NCM ANALÍTICO**:
• **Função**: Classificação final para operações comerciais
• **Estrutura**: Sempre 8 dígitos
• **Uso em NFe**: [OK] DEVE ser usado
• **Exemplo**: `84.71.30.00` (Máquinas portáteis para processamento)
• **Quantidade**: 10.507 códigos na base

[?] **Regra Prática**: 
- Se tem 8 dígitos = Analítico (use em NFe)
- Se tem menos de 8 dígitos = Sintético (não use em NFe)

[!] **Importante**: Usar NCM sintético em NFe é erro fiscal!
"""
        
        # 4. Busca geral
        return self.find_best_ncm_for_product(user_question)
    
    def interactive_chat(self):
        """Chat interativo"""
        print("\\n" + "=" * 60)
        print("[?] CONSULTOR NCM INTELIGENTE")
        print("=" * 60)
        print("[?] Faça perguntas sobre NCMs ou digite 'sair' para encerrar")
        print("[LIST] Exemplos:")
        print("   • 'Qual NCM para notebook?'")
        print("   • 'O que é NCM 84.71.30.00?'")
        print("   • 'Diferença entre sintético e analítico'")
        print()
        
        while True:
            try:
                question = input("❓ Sua pergunta: ").strip()
                
                if question.lower() in ['sair', 'exit', 'quit', 'q']:
                    print("[?] Até logo!")
                    break
                
                if not question:
                    continue
                
                print("\\n[?] Consultando base NCM...")
                response = self.intelligent_response(question)
                print(f"\\n{response}")
                print("\\n" + "-" * 60 + "\\n")
                
            except KeyboardInterrupt:
                print("\\n\\n[?] Interrompido. Até logo!")
                break
            except Exception as e:
                print(f"\\n[X] Erro: {e}")
    
    def demo_queries(self):
        """Demonstra consultas comuns"""
        demo_questions = [
            "Qual NCM para notebook?",
            "O que é NCM 01.01.21.00?",
            "NCM 84.71.30.00",
            "Diferença entre sintético e analítico",
            "Qual NCM para cavalos reprodutores?",
            "computador portátil"
        ]
        
        print("[?] DEMONSTRAÇÃO - CONSULTAS COMUNS")
        print("=" * 50)
        
        for question in demo_questions:
            print(f"\\n❓ **Pergunta**: {question}")
            print("-" * 40)
            
            response = self.intelligent_response(question)
            print(response)
            
            print("\\n" + "=" * 50)
            
            # Pausa para leitura
            input("Pressione Enter para continuar...")

def main():
    print("[START] SISTEMA SIMPLES DE CONSULTA NCM")
    print("[?] Usa apenas requests - sem dependências complexas")
    
    # URL da API
    api_url = input("\\n[?] URL da API (Enter para localhost:8081): ").strip()
    if not api_url:
        api_url = "http://localhost:8081"
    
    # Inicializa consultor
    consultant = SimpleNCMConsultant(api_url)
    
    # Menu
    while True:
        print("\\n" + "=" * 40)
        print("[LIST] MENU")
        print("=" * 40)
        print("1. [?] Chat interativo")
        print("2. [?] Demonstração")
        print("3. [DATA] Estatísticas da base")
        print("4. [?] Sair")
        
        choice = input("\\n[?] Escolha: ").strip()
        
        if choice == "1":
            consultant.interactive_chat()
        
        elif choice == "2":
            consultant.demo_queries()
        
        elif choice == "3":
            stats = consultant.get_stats()
            if stats.get("success"):
                s = stats["estatisticas_gerais"]
                print(f"\\n[DATA] **Estatísticas da Base NCM**:")
                print(f"   • Total: {s['total_ncms']} NCMs")
                print(f"   • Analíticos: {s['tipos']['analiticos']}")
                print(f"   • Sintéticos: {s['tipos']['sinteticos']}")
                print(f"   • Capítulos: {s['capitulos_unicos']}")
            else:
                print("[X] Erro ao obter estatísticas")
        
        elif choice == "4":
            print("[?] Até logo!")
            break
        
        else:
            print("[X] Opção inválida!")

if __name__ == "__main__":
    main()
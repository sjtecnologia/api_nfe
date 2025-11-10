#!/usr/bin/env python3
"""
Script de exemplo para integração da LLM com a API de NCMs
Demonstra como sua LLM pode consultar e utilizar a base de NCMs

Servidor da API: 192.168.0.52 (substitua pela porta correta)
"""

import requests
import json
from typing import Dict, List, Any, Optional
import sys

class NCMQueryClient:
    """Cliente para consulta da API de NCMs para LLM"""
    
    def __init__(self, api_base_url: str = "http://192.168.0.52:1234"):
        self.base_url = api_base_url
        self.api_prefix = "/api/llm"
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Faz requisição para a API"""
        try:
            url = f"{self.base_url}{self.api_prefix}{endpoint}"
            response = requests.get(url, params=params or {}, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def get_all_ncms_for_training(self) -> Dict[str, Any]:
        """
        Exporta TODA a base de NCMs para treinamento da LLM
        
        Retorna estrutura completa com:
        - Hierarquia de todos os NCMs
        - Contexto completo de cada código
        - Metadados para classificação
        - Estatísticas da base
        """
        print("🔄 Carregando base completa de NCMs...")
        return self._make_request("/ncms/export")
    
    def search_ncms(self, query: str, tipo: str = "todos", nivel: str = "todos", limit: int = 10) -> Dict[str, Any]:
        """
        Busca NCMs por termo
        
        Args:
            query: Termo de busca (podem ser códigos ou descrições)
            tipo: 'sintetico', 'analitico' ou 'todos'
            nivel: 'capitulo', 'posicao', 'subposicao', 'item' ou 'todos'
            limit: Máximo de resultados (até 200)
        """
        params = {
            "q": query,
            "tipo": tipo,
            "nivel": nivel,
            "limit": limit
        }
        return self._make_request("/ncms/search", params)
    
    def get_ncm_hierarchy(self, codigo: str) -> Dict[str, Any]:
        """
        Obtém hierarquia completa de um NCM específico
        
        Args:
            codigo: Código NCM (com ou sem pontos)
        """
        return self._make_request(f"/ncms/hierarquia/{codigo}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas da base NCM"""
        return self._make_request("/ncms/stats")
    
    def find_best_ncm_for_product(self, product_description: str, limit: int = 5) -> Dict[str, Any]:
        """
        Encontra os melhores NCMs para um produto baseado na descrição
        
        Args:
            product_description: Descrição do produto
            limit: Número máximo de sugestões
        """
        # Busca apenas NCMs analíticos (que podem receber lançamentos)
        result = self.search_ncms(
            query=product_description,
            tipo="analitico",
            nivel="item",  # Apenas itens (8 dígitos)
            limit=limit
        )
        
        if result.get("success"):
            # Adiciona contexto hierárquico para cada sugestão
            for ncm in result.get("resultados", []):
                hierarchy = self.get_ncm_hierarchy(ncm["codigo"])
                if hierarchy.get("success"):
                    ncm["contexto_hierarquico"] = hierarchy["hierarquia"]["pais"]
        
        return result
    
    def explain_ncm_code(self, codigo: str) -> str:
        """
        Explica um código NCM de forma didática para a LLM
        
        Args:
            codigo: Código NCM a ser explicado
        """
        result = self.get_ncm_hierarchy(codigo)
        
        if not result.get("success"):
            return f"❌ Erro ao buscar NCM {codigo}: {result.get('error', 'Desconhecido')}"
        
        ncm = result["ncm_solicitado"]
        hierarquia = result["hierarquia"]
        
        explanation = []
        explanation.append(f"📋 **NCM {ncm['codigo_formatado']}**: {ncm['descricao']}")
        explanation.append(f"   **Tipo**: {'✅ Analítico (pode receber lançamentos)' if ncm['tipo'] == 'analitico' else '📁 Sintético (apenas classificação)'}")
        
        if hierarquia["pais"]:
            explanation.append("   **Hierarquia**:")
            for i, pai in enumerate(hierarquia["pais"]):
                indent = "   " + "  " * (i + 1)
                explanation.append(f"{indent}• {pai['codigo_formatado']}: {pai['descricao']}")
            
            # Adiciona o próprio NCM no final da hierarquia
            indent = "   " + "  " * (len(hierarquia["pais"]) + 1)
            explanation.append(f"{indent}• **{ncm['codigo_formatado']}**: **{ncm['descricao']}**")
        
        return "\n".join(explanation)

def demonstrate_llm_integration():
    """Demonstra como a LLM pode usar a API"""
    
    print("=" * 60)
    print("🤖 DEMONSTRAÇÃO: INTEGRAÇÃO LLM COM API DE NCMs")
    print("=" * 60)
    
    # Inicializa cliente (ajuste a URL conforme necessário)
    client = NCMQueryClient("http://192.168.0.52:1234")  # Porta da sua LLM
    
    print("\n1️⃣ **OBTENDO ESTATÍSTICAS DA BASE**")
    print("-" * 40)
    
    stats = client.get_statistics()
    if stats.get("success"):
        s = stats["estatisticas_gerais"]
        print(f"📊 Total de NCMs: {s['total_ncms']}")
        print(f"   • Analíticos (usáveis em NFe): {s['tipos']['analiticos']}")
        print(f"   • Sintéticos (classificação): {s['tipos']['sinteticos']}")
        print(f"   • Capítulos únicos: {s['capitulos_unicos']}")
        
        print("\n🏆 Top 3 capítulos com mais NCMs:")
        for cap in stats["top_capitulos"][:3]:
            print(f"   • Cap. {cap['codigo']}: {cap['ncms_analiticos']} NCMs analíticos")
            print(f"     {cap['descricao'][:70]}...")
    
    print("\n2️⃣ **EXPLICANDO UM NCM ESPECÍFICO**")
    print("-" * 40)
    
    explanation = client.explain_ncm_code("01.01.21.00")
    print(explanation)
    
    print("\n3️⃣ **BUSCANDO NCMS POR PRODUTO**")
    print("-" * 40)
    
    # Exemplo: empresa quer classificar "notebook"
    product = "notebook"
    print(f"🔍 Buscando NCMs para: '{product}'")
    
    suggestions = client.find_best_ncm_for_product(product, limit=3)
    if suggestions.get("success"):
        print(f"   Encontradas {suggestions['total_encontrados']} sugestões:")
        
        for i, ncm in enumerate(suggestions["resultados"], 1):
            print(f"\n   {i}. **{ncm['codigo_formatado']}**: {ncm['descricao']}")
            
            # Mostra contexto hierárquico se disponível
            if "contexto_hierarquico" in ncm:
                for pai in ncm["contexto_hierarquico"]:
                    print(f"      ↳ {pai['codigo_formatado']}: {pai['descricao']}")
    
    print("\n4️⃣ **EXEMPLO DE CONSULTA INTELIGENTE**")
    print("-" * 40)
    
    # Simula como a LLM responderia uma pergunta
    user_question = "Qual NCM usar para importar cavalos reprodutores?"
    print(f"❓ Pergunta: {user_question}")
    
    # LLM busca por palavras-chave
    search_result = client.search_ncms("cavalos reprodutores", tipo="analitico", limit=3)
    
    if search_result.get("success") and search_result["resultados"]:
        best_ncm = search_result["resultados"][0]
        explanation = client.explain_ncm_code(best_ncm["codigo"])
        
        print(f"\n🎯 **Resposta da LLM:**")
        print(f"Para importar cavalos reprodutores, recomendo o NCM:")
        print(explanation)
        print(f"\n✅ Este é um NCM analítico, adequado para uso em NFe.")
    
    print("\n" + "=" * 60)
    print("✅ DEMONSTRAÇÃO CONCLUÍDA")
    print("=" * 60)

def export_training_data():
    """Exporta dados para treinamento da LLM"""
    print("🔄 Exportando base completa para treinamento da LLM...")
    
    client = NCMQueryClient("http://192.168.0.52:1234")  # Porta da sua LLM
    data = client.get_all_ncms_for_training()
    
    if data.get("success"):
        # Salva em arquivo JSON para treinamento
        filename = "ncms_training_data.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Dados exportados para: {filename}")
        print(f"📊 Total de NCMs: {len(data['ncms'])}")
        print(f"📄 Tamanho do arquivo: {len(json.dumps(data)) / 1024 / 1024:.1f} MB")
        
        return filename
    else:
        print(f"❌ Erro na exportação: {data.get('error')}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        # Modo exportação para treinamento
        export_training_data()
    else:
        # Modo demonstração
        demonstrate_llm_integration()
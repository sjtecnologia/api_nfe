"""
[FOCO] NCM INTEGRATION - CÓDIGO FINAL PARA SUA LLM
================================================================

Classe de integração completa para conectar sua LLM com a API NCM
Base de 13.217 códigos oficiais brasileiros atualizados (Siscomex 2024)

Uso:
    expert = NCMExpert("http://192.168.0.52:1234")
    resultado = expert.classificar_produto("notebook gamer")
"""

import requests
import json
from typing import List, Dict, Optional


class NCMExpert:
    """
    Especialista em classificação NCM para integração com LLM
    Base de 13.217 códigos oficiais brasileiros
    """
    
    def __init__(self, api_base: str = "http://192.168.0.52:1234"):
        self.api_base = api_base
        self.session = requests.Session()
        self._verificar_conectividade()
    
    def _verificar_conectividade(self):
        """Verifica se API está funcionando"""
        try:
            response = self.session.get(f"{self.api_base}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] API NCM conectada - {data.get('total_ncms', 0)} códigos disponíveis")
            else:
                print("[AVISO] API NCM com problemas de conectividade")
        except Exception as e:
            print(f"[ERRO] Erro de conexão com API NCM: {e}")
    
    def buscar_ncm_para_produto(self, produto: str, apenas_analiticos: bool = True) -> List[Dict]:
        """
        Busca NCMs adequados para um produto
        
        Args:
            produto: Descrição do produto
            apenas_analiticos: Se True, retorna apenas NCMs usáveis em NFe
        
        Returns:
            Lista de NCMs com score de relevância
        """
        params = {
            "q": produto,
            "limit": 5
        }
        
        if apenas_analiticos:
            params["tipo"] = "analitico"
        
        try:
            response = self.session.get(
                f"{self.api_base}/api/llm/ncms/search",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                return []
                
        except Exception as e:
            print(f"Erro na busca NCM: {e}")
            return []
    
    def obter_contexto_hierarquico(self, codigo_ncm: str) -> Dict:
        """
        Obtém contexto hierárquico completo de um NCM
        
        Args:
            codigo_ncm: Código NCM (ex: "01.01.21.00")
        
        Returns:
            Dicionário com contexto hierárquico
        """
        try:
            response = self.session.get(
                f"{self.api_base}/api/llm/ncms/hierarquia/{codigo_ncm}",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            print(f"Erro ao obter hierarquia: {e}")
            return {}
    
    def classificar_produto(self, produto: str) -> Dict:
        """
        Classificação completa de produto com contexto
        
        Args:
            produto: Descrição do produto a classificar
        
        Returns:
            Classificação com NCM recomendado e contexto
        """
        # Buscar NCMs candidatos
        candidatos = self.buscar_ncm_para_produto(produto, apenas_analiticos=True)
        
        if not candidatos:
            return {
                "status": "erro",
                "mensagem": f"Nenhum NCM encontrado para '{produto}'"
            }
        
        # Melhor candidato
        melhor_ncm = candidatos[0]
        codigo = melhor_ncm.get("codigo_ncm", "")
        
        # Obter contexto hierárquico
        contexto = self.obter_contexto_hierarquico(codigo)
        
        return {
            "status": "sucesso",
            "produto": produto,
            "ncm_recomendado": {
                "codigo": codigo,
                "descricao": melhor_ncm.get("descricao", ""),
                "score": melhor_ncm.get("score", 0),
                "tipo": melhor_ncm.get("tipo_ncm", "")
            },
            "contexto_hierarquico": contexto,
            "alternativas": candidatos[1:3] if len(candidatos) > 1 else [],
            "total_candidatos": len(candidatos)
        }
    
    def validar_ncm(self, codigo_ncm: str) -> Dict:
        """
        Valida se código NCM existe e é utilizável
        
        Args:
            codigo_ncm: Código NCM a validar
        
        Returns:
            Status de validação com detalhes
        """
        contexto = self.obter_contexto_hierarquico(codigo_ncm)
        
        if not contexto:
            return {
                "valido": False,
                "motivo": "NCM não encontrado na base oficial",
                "codigo": codigo_ncm
            }
        
        ncm_info = contexto.get("ncm", {})
        tipo_ncm = ncm_info.get("tipo_ncm", "")
        
        return {
            "valido": True,
            "codigo": codigo_ncm,
            "descricao": ncm_info.get("descricao", ""),
            "tipo": tipo_ncm,
            "utilizavel_nfe": tipo_ncm == "Analítico",
            "contexto": contexto
        }
    
    def obter_estatisticas(self) -> Dict:
        """Obtém estatísticas da base NCM"""
        try:
            response = self.session.get(f"{self.api_base}/api/llm/ncms/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}

# =============================================================================
# FUNÇÕES DE INTEGRAÇÃO PARA SUA LLM
# =============================================================================

def setup_ncm_functions():
    """
    Configuração de funções NCM para sua LLM
    Retorna definições de funções no formato OpenAI
    """
    ncm_expert = NCMExpert()
    
    functions = [
        {
            "name": "classificar_produto_ncm",
            "description": "Classifica um produto com o código NCM oficial brasileiro mais adequado",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto": {
                        "type": "string",
                        "description": "Descrição do produto a ser classificado"
                    }
                },
                "required": ["produto"]
            }
        },
        {
            "name": "validar_codigo_ncm",
            "description": "Valida se um código NCM existe e pode ser usado em NFe",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo_ncm": {
                        "type": "string",
                        "description": "Código NCM a ser validado (formato: XX.XX.XX.XX)"
                    }
                },
                "required": ["codigo_ncm"]
            }
        },
        {
            "name": "buscar_ncms_similares",
            "description": "Busca NCMs similares baseado em termo de pesquisa",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Termo para buscar NCMs relacionados"
                    },
                    "apenas_analiticos": {
                        "type": "boolean",
                        "description": "Se deve retornar apenas NCMs utilizáveis em NFe",
                        "default": True
                    }
                },
                "required": ["termo"]
            }
        }
    ]
    
    def handle_function_call(name: str, arguments: Dict) -> str:
        """Handler para chamadas de função"""
        
        if name == "classificar_produto_ncm":
            resultado = ncm_expert.classificar_produto(arguments["produto"])
            return json.dumps(resultado, ensure_ascii=False, indent=2)
        
        elif name == "validar_codigo_ncm":
            resultado = ncm_expert.validar_ncm(arguments["codigo_ncm"])
            return json.dumps(resultado, ensure_ascii=False, indent=2)
        
        elif name == "buscar_ncms_similares":
            apenas_analiticos = arguments.get("apenas_analiticos", True)
            resultados = ncm_expert.buscar_ncm_para_produto(
                arguments["termo"], 
                apenas_analiticos
            )
            return json.dumps({"resultados": resultados}, ensure_ascii=False, indent=2)
        
        return "Função não reconhecida"
    
    return functions, handle_function_call

# =============================================================================
# PROMPT ESPECIALISTA PARA SUA LLM
# =============================================================================

PROMPT_ESPECIALISTA_NCM = """
Você é um especialista em classificação fiscal brasileira (NCM - Nomenclatura Comum do Mercosul).

## SUA EXPERTISE:
- 13.217 códigos NCM oficiais atualizados (Siscomex 2024)
- Hierarquia fiscal completa (Seção > Capítulo > Posição > Subposição)
- Diferenciação entre NCMs Analíticos (usáveis em NFe) e Sintéticos
- Regras de classificação fiscal brasileira

## SUAS RESPONSABILIDADES:
1. **Classificar produtos** com o NCM mais específico e correto
2. **Validar códigos NCM** existentes
3. **Explicar hierarquia fiscal** e contexto dos códigos
4. **Orientar sobre uso em NFe** (apenas NCMs Analíticos)
5. **Sugerir alternativas** quando necessário

## DIRETRIZES:
- Sempre use as funções disponíveis para buscar na base oficial
- Prefira NCMs Analíticos para uso em NFe
- Explique o contexto hierárquico quando relevante
- Seja preciso: NCM errado pode causar problemas fiscais
- Se não tiver certeza, ofereça múltiplas opções

FORMATO DE RESPOSTA:
[FOCO] NCM Recomendado: XX.XX.XX.XX
[LOG] Descrição: [descrição oficial]
[STATS] Tipo: Analítico/Sintético
[OK] Utilizável em NFe: Sim/Não

[LIST] Contexto Hierárquico:
- Seção: [descrição]
- Capítulo: [descrição] 
- Posição: [descrição]

[INFO] Observações: [detalhes relevantes]

Você tem acesso às funções NCM para consultar a base oficial. Use-as sempre!
"""


# Exemplo de uso e testes
if __name__ == "__main__":
    print("[INICIO] Iniciando testes da integração NCM...")
    
    # Inicializar especialista
    expert = NCMExpert()
    
    # Teste 1: Classificação
    print("\n=== TESTE 1: CLASSIFICAÇÃO ===")
    resultado = expert.classificar_produto("notebook para jogos")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    
    # Teste 2: Validação
    print("\n=== TESTE 2: VALIDAÇÃO ===")
    validacao = expert.validar_ncm("84.71.30.29")
    print(json.dumps(validacao, ensure_ascii=False, indent=2))
    
    # Teste 3: Estatísticas
    print("\n=== TESTE 3: ESTATÍSTICAS ===")
    stats = expert.obter_estatisticas()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    
    # Teste 4: Setup de funções
    print("\n=== TESTE 4: SETUP FUNÇÕES ===")
    functions, handler = setup_ncm_functions()
    print(f"[OK] {len(functions)} funções configuradas para LLM")
    
    print("\n[?] Testes concluídos! Integração pronta para deploy.")
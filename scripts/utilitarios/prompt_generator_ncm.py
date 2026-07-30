#!/usr/bin/env python3
"""
[?] CONSULTOR NCM SIMPLES PARA LLAMA-3.1-8B
===========================================

Sistema simplificado que gera prompts prontos para sua Llama-3.1-8B
Você copia e cola no LM Studio
"""

import requests
import json

class NCMPromptGenerator:
    """Gera prompts com dados NCM oficiais para usar no LM Studio"""
    
    def __init__(self, ncm_api="http://localhost:8081"):
        """
        Inicializa o gerador de prompts
        
        Args:
            ncm_api: URL da API NCM
        """
        self.ncm_api = ncm_api
    
    def buscar_ncm_oficial(self, produto: str, limite: int = 3) -> list:
        """Busca NCMs na base oficial"""
        try:
            response = requests.get(
                f"{self.ncm_api}/api/llm/ncms/search",
                params={"q": produto, "tipo": "analitico", "limit": limite},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("resultados", [])
        except Exception as e:
            print(f"Erro na API: {e}")
        return []
    
    def gerar_prompt_classificacao(self, produto: str) -> str:
        """Gera prompt completo para classificar produto"""
        print(f"[SEARCH] Buscando NCMs oficiais para: {produto}")
        
        ncms = self.buscar_ncm_oficial(produto)
        
        if not ncms:
            return f"""[X] Nenhum NCM encontrado para '{produto}' na base oficial.
            
[?] Tente termos mais genéricos como:
- Para "smartphone iPhone" → "telefone"
- Para "notebook gamer" → "computador portátil"  
- Para "açúcar refinado especial" → "açúcar"
"""
        
        # Monta prompt com dados reais
        prompt = f"""Você é especialista em NCM brasileiro. Baseado nos dados OFICIAIS abaixo, classifique "{produto}":

**DADOS NCM OFICIAIS ENCONTRADOS:**
"""
        
        for i, ncm in enumerate(ncms, 1):
            prompt += f"""
{i}. **NCM {ncm.get('codigo_formatado', 'N/A')}**
   Descrição: {ncm.get('descricao', 'N/A')}
   Tipo: {ncm.get('tipo', 'N/A').title()}
   Status NFe: {'[OK] Pode usar' if ncm.get('pode_receber_lancamento') else '[X] Não pode usar'}
"""

        prompt += f"""
**PERGUNTA:** Qual o melhor NCM para classificar "{produto}" em uma Nota Fiscal Eletrônica?

**INSTRUÇÕES:**
- Use APENAS os NCMs listados acima
- Escolha o mais específico e adequado
- Formate a resposta assim:

[?] **NCM:** [código do NCM escolhido]
[LOG] **Descrição:** [descrição oficial exata]
[DATA] **Tipo:** Analítico
[OK] **NFe:** Sim
[?] **Observações:** [por que este NCM é o mais adequado]

**SUA RESPOSTA:**"""
        
        return prompt
    
    def gerar_prompt_explicacao(self, codigo_ncm: str) -> str:
        """Gera prompt para explicar NCM específico"""
        try:
            response = requests.get(
                f"{self.ncm_api}/api/llm/ncms/hierarquia/{codigo_ncm}",
                timeout=10
            )
            
            if response.status_code != 200:
                return f"[X] NCM {codigo_ncm} não encontrado na base oficial"
            
            data = response.json()
            ncm_info = data.get("ncm", {})
            hierarquia = data.get("hierarquia", {})
            
            prompt = f"""Você é especialista em NCM brasileiro. Explique o NCM baseado nos dados OFICIAIS:

**DADOS OFICIAIS DO NCM {codigo_ncm}:**

**NCM:** {ncm_info.get('codigo_formatado', codigo_ncm)}
**Descrição:** {ncm_info.get('descricao', 'N/A')}
**Tipo:** {ncm_info.get('tipo', 'N/A').title()}
**Uso em NFe:** {'[OK] Sim' if ncm_info.get('pode_receber_lancamento') else '[X] Não'}

**HIERARQUIA OFICIAL:**"""
            
            for pai in hierarquia.get("pais", []):
                prompt += f"""
- {pai.get('codigo_formatado', 'N/A')}: {pai.get('descricao', 'N/A')}"""
            
            prompt += f"""

**PERGUNTA:** Explique o NCM {codigo_ncm} e seu uso em NFe.

**INSTRUÇÕES:**
- Use APENAS os dados oficiais fornecidos
- Explique a hierarquia e classificação
- Indique se pode ser usado em NFe

**FORMATO DE RESPOSTA:**
[?] **NCM:** {codigo_ncm}
[LOG] **Descrição:** [descrição oficial]
[DATA] **Tipo:** [Analítico/Sintético]
[OK] **NFe:** [Sim/Não]
[LIST] **Hierarquia:** [explicar níveis]
[?] **Observações:** [detalhes importantes]

**SUA RESPOSTA:**"""
            
            return prompt
            
        except Exception as e:
            return f"[X] Erro ao buscar dados: {e}"
    
    def menu_interativo(self):
        """Menu para gerar prompts"""
        print("\n[?] GERADOR DE PROMPTS NCM PARA LLAMA-3.1-8B")
        print("=" * 60)
        print("Este sistema gera prompts prontos para usar no LM Studio")
        print("Copie o prompt gerado e cole no chat da sua Llama-3.1-8B")
        print("=" * 60)
        
        while True:
            print("\n[LIST] OPÇÕES:")
            print("1. Gerar prompt para classificar produto")
            print("2. Gerar prompt para explicar NCM")
            print("3. Sair")
            
            opcao = input("\n[?] Escolha (1-3): ").strip()
            
            if opcao == "1":
                produto = input("[?] Nome do produto: ").strip()
                if produto:
                    print("\n" + "="*60)
                    print("[?] GERANDO PROMPT...")
                    prompt = self.gerar_prompt_classificacao(produto)
                    print("\n[OK] PROMPT GERADO! Copie tudo abaixo:")
                    print("="*60)
                    print(prompt)
                    print("="*60)
                    print("[?] Copie este prompt e cole no LM Studio")
            
            elif opcao == "2":
                codigo = input("[?] Código NCM (ex: 84.71.30.29): ").strip()
                if codigo:
                    print("\n" + "="*60)
                    print("[?] GERANDO PROMPT...")
                    prompt = self.gerar_prompt_explicacao(codigo)
                    print("\n[OK] PROMPT GERADO! Copie tudo abaixo:")
                    print("="*60)
                    print(prompt)
                    print("="*60)
                    print("[?] Copie este prompt e cole no LM Studio")
            
            elif opcao == "3":
                print("[?] Até logo!")
                break
            
            else:
                print("[X] Opção inválida")

def main():
    """Função principal"""
    generator = NCMPromptGenerator()
    
    # Testa API
    try:
        response = requests.get("http://localhost:8081/health", timeout=5)
        if response.status_code == 200:
            print("[OK] API NCM conectada")
            return True
    except:
        pass
    
    print("[X] API NCM não encontrada em localhost:8081")
    print("[?] Execute: python3 api_ncm_standalone.py")
    return False
    
    # Demonstração rápida
    print("\n[?] DEMONSTRAÇÃO:")
    prompt_demo = generator.gerar_prompt_classificacao("papel fotográfico")
    print(prompt_demo[:300] + "...")
    
    generator.menu_interativo()

if __name__ == "__main__":
    main()
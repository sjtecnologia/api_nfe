#!/usr/bin/env python3
"""
[?] Consultor NCM Simples para LM Studio
========================================

Funciona OFFLINE - não precisa de API
Ideal para treinar sua LLM com exemplos reais
"""

import json
import re
from typing import List, Dict

class NCMConsultorSimples:
    def __init__(self):
        self.ncms = []
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega dados NCM do arquivo JSON"""
        try:
            with open('ncms_training_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.ncms = data.get('ncms', [])
                print(f"[OK] Carregados {len(self.ncms)} NCMs")
                print(f"[DATA] Analíticos: {sum(1 for n in self.ncms if n.get('tipo') == 'analitico')}")
                print(f"[DATA] Sintéticos: {sum(1 for n in self.ncms if n.get('tipo') == 'sintetico')}")
        except FileNotFoundError:
            print("[X] Arquivo 'ncms_training_data.json' não encontrado")
            print("[?] Certifique-se de ter o arquivo no mesmo diretório")
        except Exception as e:
            print(f"[X] Erro ao carregar dados: {e}")
    
    def buscar_ncm(self, termo: str, limite: int = 5, apenas_analiticos: bool = True) -> List[Dict]:
        """Busca NCMs por termo"""
        if not self.ncms:
            return []
        
        termo_lower = termo.lower().strip()
        resultados = []
        
        for ncm in self.ncms:
            # Filtro por tipo se solicitado
            if apenas_analiticos and ncm.get('tipo') != 'analitico':
                continue
            
            descricao = ncm.get('descricao', '').lower()
            
            # Calcula score de relevância
            score = 0
            
            # Termo exato na descrição
            if termo_lower in descricao:
                score += descricao.count(termo_lower) * 10
            
            # Palavras individuais
            palavras_termo = termo_lower.split()
            for palavra in palavras_termo:
                if len(palavra) > 2 and palavra in descricao:
                    score += 5
            
            if score > 0:
                resultados.append({
                    'codigo': ncm.get('codigo', ''),
                    'codigo_formatado': ncm.get('codigo_formatado', ''),
                    'descricao': ncm.get('descricao', ''),
                    'tipo': ncm.get('tipo', '').title(),
                    'score': score
                })
        
        # Ordena por relevância
        resultados.sort(key=lambda x: x['score'], reverse=True)
        return resultados[:limite]
    
    def formatar_resposta_llm(self, produto: str) -> str:
        """Gera resposta formatada para usar no LM Studio"""
        resultados = self.buscar_ncm(produto, limite=3, apenas_analiticos=True)
        
        if not resultados:
            return f"""[X] **NENHUM NCM ENCONTRADO PARA "{produto.upper()}"**

[?] **Sugestões:**
- Tente termos mais genéricos (ex: "computador" em vez de "notebook gamer")
- Verifique a grafia
- Use palavras-chave principais do produto"""
        
        melhor = resultados[0]
        
        resposta = f"""[?] **NCM RECOMENDADO PARA "{produto.upper()}"**

**[LIST] CLASSIFICAÇÃO PRINCIPAL:**
• **NCM:** {melhor['codigo_formatado']}
• **Descrição:** {melhor['descricao']}
• **Tipo:** {melhor['tipo']}
• **Uso em NFe:** [OK] SIM (NCM Analítico)
• **Score:** {melhor['score']} pontos

"""
        
        if len(resultados) > 1:
            resposta += "**[SEARCH] ALTERNATIVAS:**\n"
            for i, alt in enumerate(resultados[1:], 2):
                resposta += f"{i}. {alt['codigo_formatado']}: {alt['descricao']}\n"
            resposta += "\n"
        
        resposta += """**[?] OBSERVAÇÕES IMPORTANTES:**
- [OK] NCM Analítico pode ser usado em Nota Fiscal Eletrônica
- [LIST] Sempre confirme se a descrição corresponde exatamente ao seu produto
- ⚖️ Em caso de dúvida, consulte a Receita Federal ou contador
- [?] Use sempre o código mais específico possível"""
        
        return resposta
    
    def gerar_exemplo_treinamento(self, produto: str) -> str:
        """Gera exemplo no formato ideal para treinar LLM"""
        resultados = self.buscar_ncm(produto, limite=1, apenas_analiticos=True)
        
        if not resultados:
            return ""
        
        ncm = resultados[0]
        
        exemplo = f"""**Exemplo de Classificação NCM:**

**Usuário:** Qual NCM para {produto}?

**Assistente:** [?] NCM: {ncm['codigo_formatado']}
[LOG] Descrição: {ncm['descricao']}
[OK] Tipo: {ncm['tipo']}
[LIST] Uso em NFe: Sim
[?] Observações: NCM analítico adequado para uso em Nota Fiscal Eletrônica

---"""
        
        return exemplo
    
    def chat_interativo(self):
        """Interface de chat para testes"""
        if not self.ncms:
            print("[X] Não foi possível carregar os dados NCM")
            return
        
        print("\n[?] CONSULTOR NCM SIMPLES")
        print("=" * 50)
        print("Comandos:")
        print("• classificar [produto] - Busca NCM para produto")
        print("• exemplo [produto] - Gera exemplo para treinar LLM")
        print("• sair - Encerra o programa")
        print("=" * 50)
        
        while True:
            try:
                entrada = input("\n[SEARCH] Digite seu comando: ").strip()
                
                if entrada.lower() in ['sair', 'exit', 'quit']:
                    print("[?] Até logo!")
                    break
                
                if not entrada:
                    continue
                
                if entrada.startswith("classificar "):
                    produto = entrada[12:].strip()
                    if produto:
                        print("\n[?] Buscando...")
                        resposta = self.formatar_resposta_llm(produto)
                        print(f"\n{resposta}\n")
                        print("-" * 60)
                
                elif entrada.startswith("exemplo "):
                    produto = entrada[8:].strip()
                    if produto:
                        print("\n[?] Gerando exemplo...")
                        exemplo = self.gerar_exemplo_treinamento(produto)
                        if exemplo:
                            print(f"\n{exemplo}\n")
                            print("[SAVE] Copie este exemplo para treinar sua LLM no LM Studio")
                        else:
                            print("[X] Nenhum exemplo gerado")
                        print("-" * 60)
                
                else:
                    # Classificação direta
                    print("\n[?] Buscando...")
                    resposta = self.formatar_resposta_llm(entrada)
                    print(f"\n{resposta}\n")
                    print("-" * 60)
                    
            except KeyboardInterrupt:
                print("\n[?] Interrompido pelo usuário")
                break
            except Exception as e:
                print(f"[X] Erro: {e}")
    
    def gerar_dataset_treinamento(self, produtos: List[str], arquivo_saida: str = "exemplos_ncm_treinamento.txt"):
        """Gera dataset de exemplos para treinamento"""
        exemplos = []
        
        print(f"[?] Gerando exemplos de treinamento para {len(produtos)} produtos...")
        
        for produto in produtos:
            exemplo = self.gerar_exemplo_treinamento(produto)
            if exemplo:
                exemplos.append(exemplo)
        
        # Salva em arquivo
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("# EXEMPLOS DE TREINAMENTO NCM PARA LLM\n")
            f.write("# " + "=" * 50 + "\n\n")
            for exemplo in exemplos:
                f.write(exemplo + "\n\n")
        
        print(f"[OK] {len(exemplos)} exemplos salvos em '{arquivo_saida}'")
        print("[?] Use este arquivo para treinar sua LLM no LM Studio")

def main():
    """Função principal"""
    print("[START] INICIANDO CONSULTOR NCM SIMPLES")
    print("=" * 50)
    
    consultor = NCMConsultorSimples()
    
    if not consultor.ncms:
        print("\n[X] Não foi possível inicializar o consultor")
        print("[?] Verifique se o arquivo 'ncms_training_data.json' existe")
        return
    
    print("\n[OK] Consultor inicializado com sucesso!")
    
    # Teste rápido
    print("\n[?] TESTE RÁPIDO:")
    teste = consultor.formatar_resposta_llm("papel fotográfico")
    print(teste[:200] + "..." if len(teste) > 200 else teste)
    
    # Menu de opções
    print("\n[LIST] OPÇÕES:")
    print("1. Chat interativo")
    print("2. Gerar dataset de treinamento")
    print("3. Sair")
    
    try:
        opcao = input("\n[?] Escolha uma opção (1-3): ").strip()
        
        if opcao == "1":
            consultor.chat_interativo()
        
        elif opcao == "2":
            produtos_exemplo = [
                "papel fotográfico", "notebook", "cavalos reprodutores", 
                "automóvel", "açúcar", "café", "computador desktop",
                "smartphone", "impressora", "televisor", "geladeira"
            ]
            consultor.gerar_dataset_treinamento(produtos_exemplo)
        
        elif opcao == "3":
            print("[?] Até logo!")
        
        else:
            print("[X] Opção inválida")
            
    except KeyboardInterrupt:
        print("\n[?] Programa interrompido")

if __name__ == "__main__":
    main()
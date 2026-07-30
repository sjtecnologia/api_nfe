#!/usr/bin/env python3
"""
Sistema RAG (Retrieval Augmented Generation) para NCMs
Integra base de dados NCM com LLM usando busca semântica
"""

import requests
import json
import os
from typing import List, Dict, Any, Optional
import sqlite3
from datetime import datetime
import re

class SimpleNCMRag:
    """Sistema RAG simples sem dependências externas complexas"""
    
    def __init__(self, api_base_url: str = "http://192.168.0.52:8081"):
        self.api_base_url = api_base_url
        self.db_path = "ncm_rag.db"
        self.ncm_data = []
        self._init_database()
    
    def _init_database(self):
        """Inicializa banco SQLite para cache local"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ncms (
                id INTEGER PRIMARY KEY,
                codigo TEXT UNIQUE,
                codigo_formatado TEXT,
                descricao TEXT,
                tipo TEXT,
                nivel_nome TEXT,
                pode_usar_nfe BOOLEAN,
                contexto_completo TEXT,
                hierarquia_pais TEXT,
                data_cache TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_descricao ON ncms(descricao);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_codigo ON ncms(codigo);
        """)
        
        conn.commit()
        conn.close()
    
    def load_and_cache_ncm_data(self, force_reload: bool = False):
        """Carrega dados NCM da API e armazena localmente"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verifica se já tem dados em cache
        if not force_reload:
            cursor.execute("SELECT COUNT(*) FROM ncms WHERE date(data_cache) = date('now')")
            count = cursor.fetchone()[0]
            
            if count > 10000:  # Se tem dados recentes
                print(f"[OK] Usando cache local ({count} NCMs)")
                cursor.execute("SELECT * FROM ncms")
                rows = cursor.fetchall()
                
                self.ncm_data = []
                for row in rows:
                    self.ncm_data.append({
                        'id': row[0],
                        'codigo': row[1],
                        'codigo_formatado': row[2],
                        'descricao': row[3],
                        'tipo': row[4],
                        'nivel_nome': row[5],
                        'pode_usar_nfe': bool(row[6]),
                        'contexto_completo': row[7],
                        'hierarquia_pais': json.loads(row[8]) if row[8] else []
                    })
                
                conn.close()
                return
        
        print("[?] Carregando dados NCM da API...")
        
        try:
            response = requests.get(f"{self.api_base_url}/api/llm/ncms/export", timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success'):
                raise Exception(f"API retornou erro: {data.get('message', 'Desconhecido')}")
            
            ncms = data['ncms']
            print(f"[LIST] Carregados {len(ncms)} NCMs da API")
            
            # Limpa cache antigo
            cursor.execute("DELETE FROM ncms")
            
            # Insere novos dados
            for ncm in ncms:
                cursor.execute("""
                    INSERT OR REPLACE INTO ncms 
                    (id, codigo, codigo_formatado, descricao, tipo, nivel_nome, 
                     pode_usar_nfe, contexto_completo, hierarquia_pais)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ncm['id'],
                    ncm['codigo'],
                    ncm['codigo_formatado'],
                    ncm['descricao'],
                    ncm['tipo'],
                    ncm['nivel']['nome'],
                    ncm['pode_receber_lancamento'],
                    ncm.get('contexto_completo', ''),
                    json.dumps(ncm.get('hierarquia_pais', []))
                ))
            
            conn.commit()
            self.ncm_data = ncms
            print("[OK] Dados armazenados em cache local")
            
        except Exception as e:
            print(f"[X] Erro ao carregar dados: {e}")
            print("[?] Verifique se a API está rodando e acessível")
            
        finally:
            conn.close()
    
    def search_ncms(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca NCMs usando busca textual simples"""
        if not self.ncm_data:
            print("[!] Dados não carregados. Executando load_and_cache_ncm_data()...")
            self.load_and_cache_ncm_data()
        
        query_lower = query.lower().strip()
        query_words = re.findall(r'\w+', query_lower)
        
        # Busca por relevância
        results = []
        
        for ncm in self.ncm_data:
            score = 0
            descricao_lower = ncm['descricao'].lower()
            codigo = ncm['codigo']
            
            # Pontuação por correspondência exata de código
            if query_lower.replace('.', '').replace(' ', '') in codigo:
                score += 100
            
            # Pontuação por palavras na descrição
            for word in query_words:
                if len(word) > 2:  # Ignora palavras muito pequenas
                    if word in descricao_lower:
                        score += len(word) * 2
                    
                    # Pontuação parcial para palavras similares
                    for desc_word in descricao_lower.split():
                        if word in desc_word or desc_word in word:
                            score += 1
            
            # Bonificação para NCMs analíticos
            if ncm['pode_receber_lancamento']:
                score += 5
            
            if score > 0:
                results.append({
                    'ncm': ncm,
                    'score': score,
                    'relevancia': 'alta' if score > 50 else 'media' if score > 10 else 'baixa'
                })
        
        # Ordena por pontuação e limita resultados
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def get_ncm_hierarchy(self, codigo: str) -> Optional[Dict]:
        """Obtém hierarquia de um NCM específico"""
        try:
            response = requests.get(f"{self.api_base_url}/api/llm/ncms/hierarquia/{codigo}")
            if response.ok:
                return response.json()
        except:
            pass
        return None
    
    def generate_response(self, user_question: str) -> str:
        """Gera resposta baseada em busca e contexto"""
        # 1. Busca NCMs relevantes
        search_results = self.search_ncms(user_question, limit=3)
        
        if not search_results:
            return f"""
[X] **Nenhum NCM encontrado** para: "{user_question}"

[?] **Sugestões**:
- Tente termos mais específicos
- Use palavras-chave do produto
- Inclua características técnicas
- Exemplo: "computador portátil" em vez de "notebook"
"""
        
        # 2. Constrói resposta estruturada
        response_parts = []
        response_parts.append(f"[SEARCH] **Consultando NCMs para**: {user_question}")
        response_parts.append("")
        
        for i, result in enumerate(search_results, 1):
            ncm = result['ncm']
            
            response_parts.append(f"**{i}. NCM {ncm['codigo_formatado']}**: {ncm['descricao']}")
            
            # Tipo e uso
            tipo_icon = "[OK]" if ncm['pode_receber_lancamento'] else "[?]"
            tipo_text = "Analítico (pode usar em NFe)" if ncm['pode_receber_lancamento'] else "Sintético (apenas classificação)"
            response_parts.append(f"   {tipo_icon} **Tipo**: {tipo_text}")
            
            # Hierarquia se disponível
            if ncm.get('hierarquia_pais'):
                response_parts.append(f"   [?] **Hierarquia**:")
                for pai in ncm['hierarquia_pais']:
                    response_parts.append(f"      • {pai.get('codigo', 'N/A')}: {pai.get('descricao', 'N/A')}")
            
            response_parts.append(f"   [?] **Relevância**: {result['relevancia']}")
            response_parts.append("")
        
        # 3. Recomendação principal
        best_ncm = search_results[0]['ncm']
        if best_ncm['pode_receber_lancamento']:
            response_parts.append("[?] **Recomendação**: Use o primeiro NCM analítico listado para operações em NFe.")
        else:
            # Procura primeiro analítico
            for result in search_results:
                if result['ncm']['pode_receber_lancamento']:
                    response_parts.append(f"[?] **Recomendação**: Para NFe, use o NCM {result['ncm']['codigo_formatado']} (analítico).")
                    break
            else:
                response_parts.append("[!] **Atenção**: Nenhum NCM analítico encontrado. Refine a busca.")
        
        return "\n".join(response_parts)
    
    def interactive_chat(self):
        """Interface de chat interativa"""
        print("=" * 60)
        print("[?] SISTEMA RAG NCM - CONSULTA INTELIGENTE")
        print("=" * 60)
        print("[?] Digite sua pergunta sobre NCM ou 'sair' para encerrar")
        print("[LIST] Exemplos: 'notebook', 'reprodutores cavalos', 'NCM 84.71.30.00'")
        print()
        
        while True:
            try:
                question = input("❓ Sua pergunta: ").strip()
                
                if question.lower() in ['sair', 'exit', 'quit', 'q']:
                    print("[?] Até logo!")
                    break
                
                if not question:
                    continue
                
                print("\n[?] Processando...")
                response = self.generate_response(question)
                print(f"\n{response}")
                print("\n" + "-" * 60 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n[?] Interrompido pelo usuário. Até logo!")
                break
            except Exception as e:
                print(f"\n[X] Erro: {e}")
                print("Tente novamente...\n")
    
    def batch_test(self):
        """Testa sistema com perguntas comuns"""
        test_questions = [
            "notebook",
            "cavalos reprodutores",
            "NCM 84.71.30.00",
            "computador portátil",
            "produtos químicos",
            "máquinas agrícolas"
        ]
        
        print("[?] TESTE EM LOTE - PERGUNTAS COMUNS")
        print("=" * 50)
        
        for question in test_questions:
            print(f"\n[LIST] TESTE: {question}")
            print("-" * 30)
            
            response = self.generate_response(question)
            print(response)
            
            print("\n" + "=" * 50)

def main():
    print("[START] INICIANDO SISTEMA RAG NCM")
    print("[?] Configuração: Busca textual simples + Cache SQLite")
    print()
    
    # Configuração da URL da API
    api_url = input("[?] URL da API (Enter para localhost:8081): ").strip()
    if not api_url:
        api_url = "http://localhost:8081"
    
    # Inicializa sistema RAG
    rag = SimpleNCMRag(api_url)
    
    # Menu principal
    while True:
        print("\n" + "=" * 40)
        print("[LIST] MENU PRINCIPAL")
        print("=" * 40)
        print("1. [SAVE] Carregar dados NCM")
        print("2. [?] Chat interativo")
        print("3. [?] Teste em lote")
        print("4. [?] Recarregar dados")
        print("5. [?] Sair")
        
        choice = input("\n[?] Escolha uma opção: ").strip()
        
        if choice == "1":
            rag.load_and_cache_ncm_data()
        
        elif choice == "2":
            if not rag.ncm_data:
                print("[!] Carregando dados primeiro...")
                rag.load_and_cache_ncm_data()
            rag.interactive_chat()
        
        elif choice == "3":
            if not rag.ncm_data:
                print("[!] Carregando dados primeiro...")
                rag.load_and_cache_ncm_data()
            rag.batch_test()
        
        elif choice == "4":
            rag.load_and_cache_ncm_data(force_reload=True)
        
        elif choice == "5":
            print("[?] Até logo!")
            break
        
        else:
            print("[X] Opção inválida!")

if __name__ == "__main__":
    main()
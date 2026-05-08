"""
Motor de IA para Sugestão de Classificação NCM
Utiliza Machine Learning para sugerir códigos NCM baseados em descrições de produtos
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import unicodedata

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.ensemble import RandomForestClassifier  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
    import numpy as np  # type: ignore
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    TfidfVectorizer = None  # type: ignore
    RandomForestClassifier = None  # type: ignore
    cosine_similarity = None  # type: ignore
    np = None  # type: ignore
    print("[!]  scikit-learn não instalado. Funcionalidade de IA limitada.")


class MotorIANCM:
    """
    Motor de Inteligência Artificial para sugestão de códigos NCM
    """
    
    def __init__(self, caminho_dados: Optional[str] = None):
        """
        Inicializa o motor de IA NCM
        
        Args:
            caminho_dados: Caminho para o diretório de dados (opcional)
        """
        if caminho_dados is None:
            caminho_dados = str(Path(__file__).parent.parent / 'dados')
        
        self.caminho_dados = Path(caminho_dados)
        self.tabela_ncm = self._carregar_tabela_ncm()
        self.lei_214 = self._carregar_lei_complementar()
        self.historico = self._carregar_historico_classificacoes()
        
        if SKLEARN_AVAILABLE and TfidfVectorizer:
            self.vectorizer = TfidfVectorizer(  # type: ignore
                max_features=500,
                ngram_range=(1, 3),
                stop_words=self._get_stopwords()
            )
            self.modelo: Optional[RandomForestClassifier] = None  # type: ignore
            self._inicializar_modelo()
        else:
            print("[!]  Modelo de IA não disponível. Use 'pip install scikit-learn'")
    
    def _carregar_tabela_ncm(self) -> Dict:
        """Carrega tabela NCM vigente"""
        arquivo_ncm = self.caminho_dados / 'Tabela_NCM_Vigente_20251029.json'
        
        # Tenta carregar do arquivo principal
        if arquivo_ncm.exists():
            with open(arquivo_ncm, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Arquivo alternativo na raiz do projeto
        arquivo_ncm_raiz = self.caminho_dados.parent / 'Tabela_NCM_Vigente_20251029.json'
        if arquivo_ncm_raiz.exists():
            with open(arquivo_ncm_raiz, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        print("[!]  Tabela NCM não encontrada. Usando dados de exemplo.")
        return self._gerar_ncm_exemplo()
    
    def _carregar_lei_complementar(self) -> Dict:
        """Carrega dados estruturados da LC 214/2025"""
        arquivo_lei = self.caminho_dados.parent / 'lei_complementar_214_2025_dados_estruturados.json'
        
        if arquivo_lei.exists():
            with open(arquivo_lei, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        print("[!]  Lei Complementar 214/2025 não encontrada.")
        return {}
    
    def _carregar_historico_classificacoes(self) -> List[Dict]:
        """Carrega histórico de classificações anteriores para aprendizado"""
        arquivo_historico = self.caminho_dados / 'historico_classificacoes.json'
        
        if arquivo_historico.exists():
            with open(arquivo_historico, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return []
    
    def _gerar_ncm_exemplo(self) -> Dict:
        """Gera alguns exemplos de NCM para testes"""
        return {
            "ncm": [
                {
                    "codigo": "9401.30.00",
                    "descricao": "Assentos giratórios de altura ajustável",
                    "capitulo": "94",
                    "posicao": "9401"
                },
                {
                    "codigo": "8471.30.12",
                    "descricao": "Computadores portáteis de peso inferior a 3,5 kg",
                    "capitulo": "84",
                    "posicao": "8471"
                },
                {
                    "codigo": "8471.60.52",
                    "descricao": "Mouses e trackballs",
                    "capitulo": "84",
                    "posicao": "8471"
                }
            ]
        }
    
    def _get_stopwords(self) -> List[str]:
        """Retorna lista de stop words em português"""
        return [
            'a', 'o', 'e', 'é', 'de', 'da', 'do', 'em', 'um', 'uma', 'os', 'as',
            'para', 'com', 'por', 'ao', 'dos', 'das', 'no', 'na', 'nos', 'nas',
            'ou', 'se', 'que', 'mais', 'menos', 'muito', 'pouco'
        ]
    
    def _inicializar_modelo(self):
        """Inicializa e treina modelo básico se houver histórico"""
        if not SKLEARN_AVAILABLE:
            return
        
        if len(self.historico) >= 10:  # Mínimo de 10 exemplos
            print("[?] Treinando modelo com histórico de classificações...")
            descricoes = [item['descricao'] for item in self.historico]
            ncms = [item['ncm'] for item in self.historico]
            
            X = self.vectorizer.fit_transform(descricoes)
            if RandomForestClassifier is not None:
                self.modelo = RandomForestClassifier(n_estimators=100, random_state=42)
                self.modelo.fit(X, ncms)
                print(f"[OK] Modelo treinado com {len(self.historico)} exemplos")
            else:
                self.modelo = None
        else:
            print("ℹ️  Histórico insuficiente para treinar modelo. Usando busca por similaridade.")
    
    def _normalizar_texto(self, texto: str) -> str:
        """
        Normaliza texto removendo acentos e convertendo para minúsculas
        """
        # Remove acentos
        texto = unicodedata.normalize('NFKD', texto)
        texto = texto.encode('ASCII', 'ignore').decode('ASCII')
        
        # Converte para minúsculas
        texto = texto.lower()
        
        # Remove caracteres especiais, mantém apenas letras, números e espaços
        texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
        
        # Remove espaços múltiplos
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto
    
    def _calcular_similaridade_texto(self, texto1: str, texto2: str) -> float:
        """
        Calcula similaridade entre dois textos usando TF-IDF e cosine similarity
        """
        if not SKLEARN_AVAILABLE:
            # Fallback simples: palavras em comum
            palavras1 = set(self._normalizar_texto(texto1).split())
            palavras2 = set(self._normalizar_texto(texto2).split())
            
            if not palavras1 or not palavras2:
                return 0.0
            
            intersecao = palavras1.intersection(palavras2)
            uniao = palavras1.union(palavras2)
            
            return len(intersecao) / len(uniao) if uniao else 0.0
        
        # Usando TF-IDF e cosine similarity
        try:
            vectors = self.vectorizer.fit_transform([texto1, texto2])
            if cosine_similarity is not None:
                similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
                return float(similarity)
            else:
                return 0.0
        except:
            return 0.0
    
    def sugerir_ncm(
        self,
        descricao: str,
        contexto: Optional[str] = None,
        detalhes_adicionais: Optional[str] = None,
        top_n: int = 3
    ) -> Dict:
        """
        Sugere códigos NCM baseado na descrição do produto
        
        Args:
            descricao: Descrição do produto
            contexto: Contexto adicional (categoria, setor, etc.)
            detalhes_adicionais: Detalhes técnicos do produto
            top_n: Número de sugestões a retornar
        
        Returns:
            Dicionário com sugestões e embasamento legal
        """
        # Combina todas as informações
        texto_completo = descricao
        if contexto:
            texto_completo += f" {contexto}"
        if detalhes_adicionais:
            texto_completo += f" {detalhes_adicionais}"
        
        texto_normalizado = self._normalizar_texto(texto_completo)
        
        # Busca por similaridade na tabela NCM
        sugestoes = self._buscar_ncm_por_similaridade(texto_normalizado, top_n * 2)
        
        # Se houver modelo treinado, usa predição
        if SKLEARN_AVAILABLE and self.modelo is not None:
            predicoes_ml = self._prever_com_modelo(texto_normalizado, top_n)
            # Combina resultados
            sugestoes = self._combinar_resultados(sugestoes, predicoes_ml)
        
        # Limita ao top_n
        sugestoes = sugestoes[:top_n]
        
        # Obtém embasamento legal
        if sugestoes:
            ncm_principal = sugestoes[0]
            embasamento = self._obter_embasamento_legal(ncm_principal['codigo'])
        else:
            embasamento = {}
        
        return {
            'sucesso': len(sugestoes) > 0,
            'ncm_sugerido': sugestoes[0] if sugestoes else None,
            'alternativas': sugestoes[1:] if len(sugestoes) > 1 else [],
            'embasamento_legal': embasamento,
            'timestamp': datetime.now().isoformat(),
            'metodo': 'modelo_ml' if (SKLEARN_AVAILABLE and self.modelo) else 'similaridade_textual'
        }
    
    def _buscar_ncm_por_similaridade(self, texto: str, top_n: int = 5) -> List[Dict]:
        """Busca NCMs por similaridade textual"""
        resultados = []
        
        # Verifica estrutura da tabela NCM
        if 'ncm' in self.tabela_ncm:
            lista_ncm = self.tabela_ncm['ncm']
        elif isinstance(self.tabela_ncm, list):
            lista_ncm = self.tabela_ncm
        else:
            print("[!]  Estrutura de tabela NCM não reconhecida")
            return []
        
        for item_ncm in lista_ncm:
            descricao_ncm = item_ncm.get('descricao', '')
            
            # Calcula similaridade
            score = self._calcular_similaridade_texto(texto, descricao_ncm)
            
            if score > 0.1:  # Threshold mínimo
                resultados.append({
                    'codigo': item_ncm.get('codigo', ''),
                    'descricao': descricao_ncm,
                    'confianca': float(score),
                    'capitulo': item_ncm.get('capitulo', ''),
                    'posicao': item_ncm.get('posicao', '')
                })
        
        # Ordena por score
        resultados.sort(key=lambda x: x['confianca'], reverse=True)
        
        return resultados[:top_n]
    
    def _prever_com_modelo(self, texto: str, top_n: int = 3) -> List[Dict]:
        """Faz predição usando modelo treinado"""
        if not SKLEARN_AVAILABLE or self.modelo is None:
            return []
        
        try:
            X = self.vectorizer.transform([texto])
            probabilidades = self.modelo.predict_proba(X)[0]
            classes = self.modelo.classes_
            
            # Pega top_n predições
            indices_top = np.argsort(probabilidades)[-top_n:][::-1]
            
            resultados = []
            for idx in indices_top:
                ncm_codigo = classes[idx]
                confianca = probabilidades[idx]
                
                # Busca informações completas do NCM
                info_ncm = self._buscar_info_ncm(ncm_codigo)
                
                if info_ncm:
                    resultados.append({
                        'codigo': ncm_codigo,
                        'descricao': info_ncm.get('descricao', ''),
                        'confianca': float(confianca),
                        'capitulo': info_ncm.get('capitulo', ''),
                        'posicao': info_ncm.get('posicao', '')
                    })
            
            return resultados
        except Exception as e:
            print(f"[!]  Erro na predição: {e}")
            return []
    
    def _buscar_info_ncm(self, codigo_ncm: str) -> Optional[Dict]:
        """Busca informações completas de um código NCM"""
        lista_ncm = self.tabela_ncm.get('ncm', []) if isinstance(self.tabela_ncm, dict) else self.tabela_ncm
        
        for item in lista_ncm:
            if item.get('codigo', '').replace('.', '') == codigo_ncm.replace('.', ''):
                return item
        
        return None
    
    def _combinar_resultados(self, resultados1: List[Dict], resultados2: List[Dict]) -> List[Dict]:
        """Combina e deduplica resultados de diferentes métodos"""
        combinados = {}
        
        for res in resultados1 + resultados2:
            codigo = res['codigo']
            if codigo not in combinados:
                combinados[codigo] = res
            else:
                # Mantém a maior confiança
                if res['confianca'] > combinados[codigo]['confianca']:
                    combinados[codigo] = res
        
        # Converte de volta para lista e ordena
        lista_final = list(combinados.values())
        lista_final.sort(key=lambda x: x['confianca'], reverse=True)
        
        return lista_final
    
    def _buscar_ncm_por_codigo(self, ncm_codigo: str) -> Optional[Dict]:
        """
        Busca um NCM específico pelo código
        
        Args:
            ncm_codigo: Código NCM (8 dígitos)
        
        Returns:
            Dicionário com informações do NCM ou None
        """
        ncm_normalizado = ncm_codigo.replace('.', '').replace('-', '')
        
        # A tabela NCM é um dicionário, itera pelos itens
        for codigo, info in self.tabela_ncm.items():
            codigo_db = codigo.replace('.', '').replace('-', '')
            if codigo_db == ncm_normalizado:
                return {'codigo': codigo, **info}
        
        return None
    
    def _obter_embasamento_legal(self, ncm_codigo: str) -> Dict:
        """
        Obtém embasamento legal da LC 214/2025 para o NCM
        """
        embasamento = {
            'lei': 'LC 214/2025',
            'artigos_relacionados': [],
            'aliquota_ibs_cbs': {
                'ibs': '26.5%',
                'cbs': '8.5%',
                'total': '35.0%',
                'observacao': 'Alíquota padrão conforme estimativa baseada na LC 214/2025'
            },
            'fundamentacao': []
        }
        
        # Busca artigos relevantes
        if self.lei_214 and 'artigos' in self.lei_214:
            # Artigos gerais sobre tributação
            artigos_chave = ['4º', '47º', '195']
            
            for artigo in self.lei_214['artigos']:
                if artigo['artigo'] in artigos_chave:
                    embasamento['artigos_relacionados'].append({
                        'numero': f"Art. {artigo['artigo']}",
                        'texto': artigo['conteudo'][:300] + '...',
                        'relevancia': 'Artigo base sobre incidência de IBS/CBS'
                    })
        
        # Busca referências específicas ao NCM
        if self.lei_214 and 'referencias_ncm' in self.lei_214:
            for ref in self.lei_214['referencias_ncm']:
                if ncm_codigo in ref.get('termo', ''):
                    embasamento['referencias_ncm_especificas'] = {
                        'encontrada': True,
                        'contexto': ref.get('contexto', '')[:200]
                    }
                    break
        
        # Fundamentação genérica
        info_ncm = self._buscar_info_ncm(ncm_codigo)
        if info_ncm:
            capitulo = info_ncm.get('capitulo', '')
            posicao = info_ncm.get('posicao', '')
            
            embasamento['fundamentacao'] = [
                f"Produto classificado no Capítulo {capitulo} da Nomenclatura Comum do Mercosul (NCM)",
                f"Posição tarifária {posicao} conforme tabela NCM vigente",
                f"Subposição {ncm_codigo} corresponde à descrição: {info_ncm.get('descricao', '')}",
                "Sujeito à incidência de IBS e CBS conforme LC 214/2025, Art. 4º",
                "Classificação passível de verificação junto à Receita Federal do Brasil"
            ]
        
        return embasamento
    
    def registrar_feedback(
        self,
        descricao: str,
        ncm_sugerido: str,
        ncm_confirmado: str,
        usuario_id: Optional[int] = None,
        aprovado: bool = True
    ):
        """
        Registra feedback de classificação para aprendizado contínuo
        
        Args:
            descricao: Descrição do produto
            ncm_sugerido: NCM que foi sugerido pela IA
            ncm_confirmado: NCM confirmado/correto
            usuario_id: ID do usuário que forneceu feedback
            aprovado: Se a sugestão foi aprovada
        """
        feedback = {
            'descricao': descricao,
            'ncm_sugerido': ncm_sugerido,
            'ncm_confirmado': ncm_confirmado,
            'aprovado': aprovado,
            'usuario_id': usuario_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Adiciona ao histórico
        self.historico.append({
            'descricao': descricao,
            'ncm': ncm_confirmado
        })
        
        # Salva histórico atualizado
        arquivo_historico = self.caminho_dados / 'historico_classificacoes.json'
        with open(arquivo_historico, 'w', encoding='utf-8') as f:
            json.dump(self.historico, f, ensure_ascii=False, indent=2)
        
        # Se acumulou exemplos suficientes, retreina modelo
        if len(self.historico) % 50 == 0 and SKLEARN_AVAILABLE:
            print(f"[?] Retreinando modelo com {len(self.historico)} exemplos...")
            self._inicializar_modelo()
        
        print(f"[OK] Feedback registrado: {'Aprovado' if aprovado else 'Corrigido'}")


# Exemplo de uso
if __name__ == '__main__':
    motor = MotorIANCM()
    
    # Teste 1: Cadeira de escritório
    resultado1 = motor.sugerir_ncm(
        descricao="Cadeira de escritório giratória com rodas",
        contexto="móveis de escritório"
    )
    
    print("\n" + "="*60)
    print("[?] Teste: Cadeira de Escritório")
    print("="*60)
    if resultado1['sucesso']:
        print(f"NCM Sugerido: {resultado1['ncm_sugerido']['codigo']}")
        print(f"Descrição: {resultado1['ncm_sugerido']['descricao']}")
        print(f"Confiança: {resultado1['ncm_sugerido']['confianca']:.2%}")
    
    # Teste 2: Notebook
    resultado2 = motor.sugerir_ncm(
        descricao="Notebook Dell Inspiron 15 3000",
        contexto="eletrônicos",
        detalhes_adicionais="8GB RAM, 256GB SSD, tela 15.6 polegadas"
    )
    
    print("\n" + "="*60)
    print("[?] Teste: Notebook")
    print("="*60)
    if resultado2['sucesso']:
        print(f"NCM Sugerido: {resultado2['ncm_sugerido']['codigo']}")
        print(f"Descrição: {resultado2['ncm_sugerido']['descricao']}")
        print(f"Confiança: {resultado2['ncm_sugerido']['confianca']:.2%}")

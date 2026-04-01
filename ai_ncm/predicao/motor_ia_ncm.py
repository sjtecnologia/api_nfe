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
    
    def _construir_descricao_hierarquica(self, codigo_ncm: str, descricao_base: str, lista_ncm: List[Dict]) -> str:
        """
        Constrói descrição completa incluindo hierarquia de NCMs pais.
        Ex: '0901.21.00' -> 'Café torrado não descafeinado'
        """
        # Remove pontos para facilitar comparação
        codigo_limpo = codigo_ncm.replace('.', '')
        
        # Se já é um capítulo/posição genérico (2-4 dígitos), retorna direto
        if len(codigo_limpo) <= 4:
            return descricao_base
        
        # Busca NCMs pais (prefixos progressivos)
        descricoes = []
        
        # Capítulo (2 dígitos): 09
        if len(codigo_limpo) >= 2:
            codigo_cap = f"{codigo_limpo[:2]}.{codigo_limpo[2:4]}"
            ncm_cap = next((n for n in lista_ncm if n.get('Codigo', '') == codigo_cap), None)
            if ncm_cap:
                desc = ncm_cap.get('Descricao', '').strip('- ')
                if desc and not desc.startswith('-'):
                    descricoes.append(desc)
        
        # Posição (4 dígitos): 0901
        if len(codigo_limpo) >= 4:
            for prefixo in [f"{codigo_limpo[:4]}.{codigo_limpo[4:5]}", codigo_limpo[:4]]:
                ncm_pos = next((n for n in lista_ncm if n.get('Codigo', '').replace('.', '') == prefixo.replace('.', '')), None)
                if ncm_pos:
                    desc = ncm_pos.get('Descricao', '').strip('- ')
                    if desc and desc not in descricoes:
                        descricoes.append(desc)
                    break
        
        # Adiciona descrição do próprio NCM
        desc_propria = descricao_base.strip('- ').lower()
        if desc_propria and not desc_propria.startswith('--'):
            descricoes.append(descricao_base.strip('- '))
        
        # Concatena hierarquia
        return ' '.join(descricoes) if descricoes else descricao_base
    
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
            # Fallback com pesos para palavras importantes
            palavras1 = set(self._normalizar_texto(texto1).split())
            palavras2 = set(self._normalizar_texto(texto2).split())
            
            if not palavras1 or not palavras2:
                return 0.0
            
            # Palavras-chave importantes recebem peso maior
            palavras_chave_importantes = {
                'torrado', 'descafeinado', 'grao', 'cafe', 'moido', 'soluvel',
                'verde', 'cru', 'tostado', 'descascado', 'beneficiado'
            }
            
            intersecao = palavras1.intersection(palavras2)
            
            # Calcula score base (Jaccard)
            uniao = palavras1.union(palavras2)
            score_base = len(intersecao) / len(uniao) if uniao else 0.0
            
            # Bônus se palavras-chave importantes coincidem
            palavras_importantes_comuns = intersecao.intersection(palavras_chave_importantes)
            bonus = len(palavras_importantes_comuns) * 0.2  # 20% de bônus por palavra importante
            
            return min(1.0, score_base + bonus)
        
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
        if 'Nomenclaturas' in self.tabela_ncm:
            lista_ncm = self.tabela_ncm['Nomenclaturas']
        elif 'ncm' in self.tabela_ncm:
            lista_ncm = self.tabela_ncm['ncm']
        elif isinstance(self.tabela_ncm, list):
            lista_ncm = self.tabela_ncm
        else:
            print("[!]  Estrutura de tabela NCM não reconhecida")
            return []
        
        for item_ncm in lista_ncm:
            # Normaliza campos PascalCase para lowercase
            item_normalizado = {
                'codigo': item_ncm.get('Codigo', item_ncm.get('codigo', '')),
                'descricao': item_ncm.get('Descricao', item_ncm.get('descricao', '')),
                'data_inicio': item_ncm.get('Data_Inicio', item_ncm.get('data_inicio', '')),
                'data_fim': item_ncm.get('Data_Fim', item_ncm.get('data_fim', '')),
                'capitulo': item_ncm.get('Capitulo', item_ncm.get('capitulo', '')),
                'posicao': item_ncm.get('Posicao', item_ncm.get('posicao', ''))
            }
            
            # ✅ CORREÇÃO 4.1: Filtrar NCMs descontinuados por data_fim
            data_fim = item_normalizado.get('data_fim')
            if data_fim:
                try:
                    # Aceita formatos: YYYY-MM-DD, DD/MM/YYYY, YYYY-MM-DD HH:MM:SS, ou datetime object
                    if isinstance(data_fim, str):
                        from datetime import datetime
                        # Remove timestamp se houver (YYYY-MM-DD HH:MM:SS -> YYYY-MM-DD)
                        data_fim_clean = data_fim.split()[0] if ' ' in data_fim else data_fim
                        
                        # Tenta formato brasileiro DD/MM/YYYY
                        if '/' in data_fim_clean:
                            data_fim_dt = datetime.strptime(data_fim_clean, '%d/%m/%Y')
                        else:
                            # Formato ISO YYYY-MM-DD
                            data_fim_dt = datetime.strptime(data_fim_clean, '%Y-%m-%d')
                        
                        # Ignora datas muito distantes no futuro (9999 = vigente)
                        if data_fim_dt.year < 9999 and data_fim_dt < datetime.now():
                            # NCM descontinuado - pula
                            continue
                    elif hasattr(data_fim, 'year'):  # datetime object
                        from datetime import datetime
                        if data_fim.year < 9999 and data_fim < datetime.now():
                            continue
                except Exception as e:
                    # Se falhar ao parsear data, permite (assume vigente)
                    pass
            
            descricao_ncm = item_normalizado.get('descricao', '')
            codigo_ncm = item_normalizado.get('codigo', '')
            
            # ✅ Constrói descrição hierárquica completa (ex: "Café torrado não descafeinado")
            descricao_completa = self._construir_descricao_hierarquica(codigo_ncm, descricao_ncm, lista_ncm)
            
            # Penaliza se buscamos "torrado" mas a descrição tem "não torrado"
            penalidade = 0.0
            texto_busca_lower = texto.lower()
            descricao_lower = descricao_completa.lower()
            
            # Normaliza acentos para detecção de negação
            descricao_normalizada = descricao_lower.replace('ã', 'a').replace('á', 'a').replace('â', 'a')
            texto_normalizado = texto_busca_lower.replace('ã', 'a').replace('á', 'a').replace('â', 'a')
            
            # Detecta conflitos de negação
            if 'torrado' in texto_normalizado:
                # Se a descrição tem "não torrado" ou "nao torrado", aplica penalidade alta
                if 'nao torrado' in descricao_normalizada or 'não torrado' in descricao_lower:
                    penalidade += 0.5  # Aumentado de 0.3 para 0.5
            
            if 'descafeinado' in texto_normalizado:
                # Se a descrição tem "não descafeinado" ou "nao descafeinado", aplica penalidade alta  
                if 'nao descafeinado' in descricao_normalizada or 'não descafeinado' in descricao_lower:
                    penalidade += 0.5
            
            # Calcula similaridade com descrição hierárquica
            score = self._calcular_similaridade_texto(texto, descricao_completa)
            score = max(0.0, score - penalidade)  # Aplica penalidade
            
            # Bônus para matches positivos exatos (evita confusão com negações)
            if 'torrado' in texto_normalizado and 'torrado' in descricao_normalizada:
                # Se tem "torrado" mas NÃO tem "não torrado", dá bônus
                if 'nao torrado' not in descricao_normalizada and 'não torrado' not in descricao_lower:
                    score *= 1.3  # Bônus de 30% para match positivo
            
            # Bônus para NCMs mais específicos (8 dígitos completos)
            digitos_ncm = len(codigo_ncm.replace('.', '').replace('-', ''))
            if digitos_ncm >= 8:  # NCM completo (ex: 0901.21.00)
                score *= 1.3  # Aumentado de 1.2 para 1.3
            elif digitos_ncm >= 6:  # NCM de 6 dígitos (ex: 0901.21)
                score *= 1.15  # Aumentado de 1.1 para 1.15
            # NCMs com 2-4 dígitos (capítulos/posições) não recebem bônus
            
            if score > 0.1:  # Threshold mínimo
                resultados.append({
                    'codigo': codigo_ncm,
                    'descricao': descricao_completa,  # Retorna descrição completa
                    'confianca': float(score),
                    'capitulo': item_normalizado.get('capitulo', ''),
                    'posicao': item_normalizado.get('posicao', '')
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
        if 'Nomenclaturas' in self.tabela_ncm:
            lista_ncm = self.tabela_ncm['Nomenclaturas']
        elif 'ncm' in self.tabela_ncm:
            lista_ncm = self.tabela_ncm.get('ncm', [])
        elif isinstance(self.tabela_ncm, list):
            lista_ncm = self.tabela_ncm
        else:
            return None
        
        for item in lista_ncm:
            codigo_item = item.get('Codigo', item.get('codigo', '')).replace('.', '')
            if codigo_item == codigo_ncm.replace('.', ''):
                return {
                    'codigo': item.get('Codigo', item.get('codigo', '')),
                    'descricao': item.get('Descricao', item.get('descricao', '')),
                    'capitulo': item.get('Capitulo', item.get('capitulo', '')),
                    'posicao': item.get('Posicao', item.get('posicao', ''))
                }
        
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

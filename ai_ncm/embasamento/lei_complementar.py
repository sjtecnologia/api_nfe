"""
Buscador de Artigos e Referências na Lei Complementar 214/2025
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from difflib import SequenceMatcher


class BuscadorLeiComplementar:
    """
    Busca e recupera artigos, alíquotas e referências da LC 214/2025
    """
    
    def __init__(self, caminho_dados: Optional[str] = None):
        """
        Inicializa o buscador
        
        Args:
            caminho_dados: Caminho para o arquivo de dados estruturados da lei
        """
        if caminho_dados is None:
            caminho_dados = str(Path(__file__).parent.parent.parent / 'lei_complementar_214_2025_dados_estruturados.json')
        
        self.caminho_dados = Path(caminho_dados)
        self.dados_lei = self._carregar_lei()
    
    def _carregar_lei(self) -> Dict:
        """Carrega dados estruturados da LC 214/2025"""
        if self.caminho_dados.exists():
            with open(self.caminho_dados, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"[!]  Arquivo não encontrado: {self.caminho_dados}")
            return {}
    
    def buscar_artigo(self, numero_artigo: str) -> Optional[Dict]:
        """
        Busca um artigo específico pelo número
        
        Args:
            numero_artigo: Número do artigo (ex: "4º", "47", "195")
        
        Returns:
            Dicionário com informações do artigo ou None
        """
        if not self.dados_lei or 'artigos' not in self.dados_lei:
            return None
        
        # Normaliza número do artigo
        numero_normalizado = numero_artigo.replace('º', '').replace('°', '').strip()
        
        for artigo in self.dados_lei['artigos']:
            artigo_num = artigo.get('artigo', '').replace('º', '').replace('°', '').strip()
            if artigo_num == numero_normalizado:
                return {
                    'numero': f"Art. {artigo['artigo']}",
                    'conteudo': artigo['conteudo'],
                    'lei': 'LC 214/2025',
                    'data': '16/01/2025'
                }
        
        return None
    
    def buscar_por_palavra_chave(self, palavra_chave: str, max_resultados: int = 10) -> List[Dict]:
        """
        Busca artigos que contenham determinada palavra-chave
        
        Args:
            palavra_chave: Termo a buscar
            max_resultados: Número máximo de resultados
        
        Returns:
            Lista de artigos encontrados
        """
        if not self.dados_lei or 'artigos' not in self.dados_lei:
            return []
        
        resultados = []
        palavra_lower = palavra_chave.lower()
        
        for artigo in self.dados_lei['artigos']:
            conteudo = artigo.get('conteudo', '').lower()
            
            if palavra_lower in conteudo:
                # Extrai contexto ao redor da palavra-chave
                pos = conteudo.find(palavra_lower)
                inicio = max(0, pos - 100)
                fim = min(len(conteudo), pos + len(palavra_chave) + 100)
                contexto = conteudo[inicio:fim]
                
                resultados.append({
                    'numero': f"Art. {artigo['artigo']}",
                    'conteudo_completo': artigo['conteudo'],
                    'contexto': f"...{contexto}...",
                    'relevancia': conteudo.count(palavra_lower)
                })
        
        # Ordena por relevância
        resultados.sort(key=lambda x: x['relevancia'], reverse=True)
        
        return resultados[:max_resultados]
    
    def buscar_referencias_ncm(self) -> List[Dict]:
        """
        Retorna todas as referências a NCM encontradas na lei
        
        Returns:
            Lista com referências a códigos NCM
        """
        if not self.dados_lei or 'referencias_ncm' not in self.dados_lei:
            return []
        
        return self.dados_lei['referencias_ncm']
    
    def buscar_aliquotas(self, tipo: Optional[str] = None) -> List[Dict]:
        """
        Busca menções a alíquotas na lei
        
        Args:
            tipo: Tipo de alíquota ('IBS', 'CBS') ou None para todas
        
        Returns:
            Lista com referências a alíquotas
        """
        if not self.dados_lei or 'aliquotas' not in self.dados_lei:
            return []
        
        aliquotas = self.dados_lei['aliquotas']
        
        if tipo:
            tipo_upper = tipo.upper()
            return [
                aliq for aliq in aliquotas
                if tipo_upper in aliq.get('match', '').upper()
            ]
        
        return aliquotas
    
    def obter_estatisticas(self) -> Dict:
        """
        Retorna estatísticas sobre a lei
        
        Returns:
            Dicionário com estatísticas
        """
        if not self.dados_lei:
            return {}
        
        return {
            'lei': self.dados_lei.get('lei', 'LC 214/2025'),
            'data': self.dados_lei.get('data', '16/01/2025'),
            'total_artigos': self.dados_lei.get('total_artigos', 0),
            'total_referencias_ncm': self.dados_lei.get('total_referencias_ncm', 0),
            'total_aliquotas': self.dados_lei.get('total_aliquotas', 0)
        }
    
    def buscar_artigos_sobre_ncm(self) -> List[Dict]:
        """
        Busca artigos que tratam especificamente sobre NCM ou classificação fiscal
        
        Returns:
            Lista de artigos relevantes
        """
        palavras_chave = [
            'ncm',
            'nomenclatura comum do mercosul',
            'classificação fiscal',
            'código ncm',
            'posição tarifária'
        ]
        
        resultados_combinados = []
        artigos_vistos = set()
        
        for palavra in palavras_chave:
            resultados = self.buscar_por_palavra_chave(palavra, max_resultados=5)
            
            for res in resultados:
                numero = res['numero']
                if numero not in artigos_vistos:
                    artigos_vistos.add(numero)
                    resultados_combinados.append(res)
        
        return resultados_combinados
    
    def buscar_aliquotas_por_ncm(self, ncm_codigo: str) -> Dict:
        """
        Busca alíquotas específicas para um código NCM (se disponível)
        
        Args:
            ncm_codigo: Código NCM (ex: "9401.30.00")
        
        Returns:
            Dicionário com informações de alíquota
        """
        # Busca referências NCM que mencionam o código
        referencias = self.buscar_referencias_ncm()
        
        for ref in referencias:
            if ncm_codigo in ref.get('termo', ''):
                # Busca alíquotas no contexto
                contexto = ref.get('contexto', '')
                
                # Tenta extrair percentuais
                percentuais = re.findall(r'(\d+[,.]?\d*)\s*%', contexto)
                
                return {
                    'ncm': ncm_codigo,
                    'encontrado': True,
                    'contexto': contexto,
                    'percentuais_mencionados': percentuais
                }
        
        # Retorna alíquota padrão estimada
        return {
            'ncm': ncm_codigo,
            'encontrado': False,
            'ibs': '26.5%',
            'cbs': '8.5%',
            'total': '35.0%',
            'observacao': 'Alíquota padrão estimada (não específica para este NCM)'
        }
    
    def gerar_relatorio_completo(self, ncm_codigo: Optional[str] = None) -> Dict:
        """
        Gera relatório completo sobre a lei, opcionalmente focado em um NCM
        
        Args:
            ncm_codigo: Código NCM para focar o relatório (opcional)
        
        Returns:
            Dicionário com relatório completo
        """
        relatorio = {
            'estatisticas': self.obter_estatisticas(),
            'artigos_chave': [],
            'referencias_ncm': [],
            'aliquotas': []
        }
        
        # Artigos fundamentais
        artigos_importantes = ['1º', '4º', '47º', '195']
        for num_art in artigos_importantes:
            artigo = self.buscar_artigo(num_art)
            if artigo:
                relatorio['artigos_chave'].append(artigo)
        
        # Referências NCM
        relatorio['referencias_ncm'] = self.buscar_referencias_ncm()[:20]
        
        # Alíquotas
        relatorio['aliquotas'] = {
            'ibs': self.buscar_aliquotas('IBS')[:10],
            'cbs': self.buscar_aliquotas('CBS')[:10]
        }
        
        # Se NCM específico fornecido
        if ncm_codigo:
            relatorio['ncm_especifico'] = {
                'codigo': ncm_codigo,
                'aliquotas': self.buscar_aliquotas_por_ncm(ncm_codigo),
                'artigos_relacionados': self.buscar_artigos_sobre_ncm()[:5]
            }
        
        return relatorio


# Exemplo de uso
if __name__ == '__main__':
    buscador = BuscadorLeiComplementar()
    
    print("\n" + "="*60)
    print("[DATA] ESTATÍSTICAS DA LEI COMPLEMENTAR 214/2025")
    print("="*60)
    stats = buscador.obter_estatisticas()
    for chave, valor in stats.items():
        print(f"{chave}: {valor}")
    
    print("\n" + "="*60)
    print("[LIST] ARTIGO 4º - INCIDÊNCIA")
    print("="*60)
    artigo_4 = buscador.buscar_artigo('4º')
    if artigo_4:
        print(f"{artigo_4['numero']}")
        print(f"{artigo_4['conteudo'][:300]}...")
    
    print("\n" + "="*60)
    print("[SEARCH] REFERÊNCIAS A NCM NA LEI")
    print("="*60)
    refs_ncm = buscador.buscar_referencias_ncm()
    print(f"Total de referências encontradas: {len(refs_ncm)}")
    if refs_ncm:
        print(f"\nPrimeira referência:")
        print(f"Termo: {refs_ncm[0]['termo']}")
        print(f"Contexto: {refs_ncm[0]['contexto'][:150]}...")
    
    print("\n" + "="*60)
    print("[?] BUSCA DE ALÍQUOTAS - IBS")
    print("="*60)
    aliq_ibs = buscador.buscar_aliquotas('IBS')
    print(f"Menções encontradas: {len(aliq_ibs)}")
    if aliq_ibs:
        print(f"\nPrimeira menção:")
        print(f"Match: {aliq_ibs[0]['match']}")
        print(f"Percentual: {aliq_ibs[0].get('percentual', 'N/A')}")
    
    print("\n" + "="*60)
    print("[SEARCH] BUSCA POR PALAVRA-CHAVE: 'tributação'")
    print("="*60)
    resultados = buscador.buscar_por_palavra_chave('tributação', max_resultados=3)
    print(f"Artigos encontrados: {len(resultados)}")
    for i, res in enumerate(resultados, 1):
        print(f"\n{i}. {res['numero']}")
        print(f"   Relevância: {res['relevancia']} menções")
        print(f"   Contexto: {res['contexto'][:100]}...")

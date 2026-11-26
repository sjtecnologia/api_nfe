"""
Gerador de Justificativas Legais para Classificação NCM
"""

from typing import Dict, List, Optional
from datetime import datetime
import re


class GeradorJustificativa:
    """
    Gera justificativas legais formatadas para classificações NCM
    """
    
    def gerar_justificativa_completa(
        self,
        ncm_codigo: str,
        ncm_descricao: str,
        descricao_produto: str,
        artigos_relacionados: List[Dict],
        confianca: float
    ) -> Dict:
        """
        Gera justificativa completa para uma classificação NCM
        
        Args:
            ncm_codigo: Código NCM sugerido
            ncm_descricao: Descrição oficial do NCM
            descricao_produto: Descrição do produto fornecida
            artigos_relacionados: Lista de artigos da LC 214/2025
            confianca: Score de confiança da classificação
        
        Returns:
            Dicionário com justificativa estruturada
        """
        # Extrai componentes do NCM
        capitulo = ncm_codigo[:2] if len(ncm_codigo) >= 2 else ''
        posicao = ncm_codigo[:4].replace('.', '') if len(ncm_codigo) >= 4 else ''
        
        # Monta justificativa
        justificativa = {
            'classificacao': {
                'ncm': ncm_codigo,
                'descricao_oficial': ncm_descricao,
                'confianca': f"{confianca:.1%}",
                'nivel_confianca': self._classificar_confianca(confianca)
            },
            'fundamentacao_tecnica': self._gerar_fundamentacao_tecnica(
                ncm_codigo, ncm_descricao, descricao_produto, capitulo, posicao
            ),
            'base_legal': self._formatar_base_legal(artigos_relacionados),
            'observacoes': self._gerar_observacoes(confianca),
            'proximos_passos': self._gerar_proximos_passos(confianca),
            'gerado_em': datetime.now().isoformat()
        }
        
        return justificativa
    
    def _classificar_confianca(self, score: float) -> str:
        """Classifica nível de confiança em categorias"""
        if score >= 0.9:
            return 'MUITO ALTA'
        elif score >= 0.75:
            return 'ALTA'
        elif score >= 0.5:
            return 'MÉDIA'
        elif score >= 0.3:
            return 'BAIXA'
        else:
            return 'MUITO BAIXA'
    
    def _gerar_fundamentacao_tecnica(
        self,
        ncm_codigo: str,
        ncm_descricao: str,
        descricao_produto: str,
        capitulo: str,
        posicao: str
    ) -> List[str]:
        """Gera lista de pontos de fundamentação técnica"""
        fundamentacao = []
        
        # 1. Classificação na estrutura NCM
        if capitulo:
            fundamentacao.append(
                f"1. Produto classificado no **Capítulo {capitulo}** da Nomenclatura Comum do Mercosul (NCM)"
            )
        
        if posicao:
            fundamentacao.append(
                f"2. Enquadramento na **Posição {posicao}** da tabela NCM vigente"
            )
        
        fundamentacao.append(
            f"3. **Subposição {ncm_codigo}** corresponde à descrição oficial: \"{ncm_descricao}\""
        )
        
        # 2. Correspondência com descrição do produto
        palavras_chave = self._extrair_palavras_chave_relevantes(descricao_produto, ncm_descricao)
        
        if palavras_chave:
            fundamentacao.append(
                f"4. Correspondência identificada entre descrição do produto e NCM: "
                f"{', '.join(palavras_chave)}"
            )
        
        # 3. Base legal
        fundamentacao.append(
            "5. Classificação sujeita à incidência de IBS e CBS conforme Lei Complementar 214/2025, Art. 4º"
        )
        
        # 4. Verificação
        fundamentacao.append(
            "6. Classificação passível de verificação junto à Receita Federal do Brasil (RFB) "
            "e consulta à tabela TIPI/NCM atualizada"
        )
        
        return fundamentacao
    
    def _extrair_palavras_chave_relevantes(
        self,
        descricao_produto: str,
        ncm_descricao: str
    ) -> List[str]:
        """
        Extrai palavras-chave que aparecem tanto na descrição do produto
        quanto na descrição oficial do NCM
        """
        # Normaliza textos
        produto_words = set(re.findall(r'\b\w{4,}\b', descricao_produto.lower()))
        ncm_words = set(re.findall(r'\b\w{4,}\b', ncm_descricao.lower()))
        
        # Stop words para remover
        stop_words = {
            'para', 'com', 'sem', 'outro', 'outros', 'outras', 'demais',
            'todos', 'todas', 'qualquer', 'quaisquer', 'sobre', 'entre'
        }
        
        # Palavras em comum
        palavras_comuns = (produto_words & ncm_words) - stop_words
        
        # Retorna as mais relevantes (limitado a 5)
        return list(palavras_comuns)[:5]
    
    def _formatar_base_legal(self, artigos: List[Dict]) -> List[Dict]:
        """Formata artigos legais de forma estruturada"""
        base_legal = []
        
        for artigo in artigos:
            base_legal.append({
                'artigo': artigo.get('numero', ''),
                'lei': artigo.get('lei', 'LC 214/2025'),
                'resumo': self._resumir_artigo(artigo.get('texto', artigo.get('conteudo', ''))),
                'relevancia': artigo.get('relevancia', 'Artigo relacionado à classificação fiscal')
            })
        
        return base_legal
    
    def _resumir_artigo(self, texto: str, max_caracteres: int = 200) -> str:
        """Cria resumo de um artigo"""
        if len(texto) <= max_caracteres:
            return texto
        
        # Pega primeiras frases até atingir limite
        texto_resumido = texto[:max_caracteres]
        
        # Tenta terminar em frase completa
        ultimo_ponto = texto_resumido.rfind('.')
        if ultimo_ponto > max_caracteres * 0.7:
            texto_resumido = texto_resumido[:ultimo_ponto + 1]
        else:
            texto_resumido = texto_resumido.rsplit(' ', 1)[0] + '...'
        
        return texto_resumido
    
    def _gerar_observacoes(self, confianca: float) -> List[str]:
        """Gera observações baseadas no nível de confiança"""
        observacoes = []
        
        if confianca >= 0.9:
            observacoes.append(
                "[OK] Alta confiança na classificação. Recomenda-se uso direto."
            )
        elif confianca >= 0.75:
            observacoes.append(
                "[!]  Boa confiança na classificação. Recomenda-se validação com contador."
            )
        elif confianca >= 0.5:
            observacoes.append(
                "[!]  Confiança média. **Validação obrigatória** com contador ou consultor fiscal."
            )
        else:
            observacoes.append(
                "[X] Baixa confiança na classificação. **Consulta à RFB recomendada**."
            )
        
        # Observação geral
        observacoes.append(
            "[?] A classificação NCM é de responsabilidade do contribuinte. "
            "Em caso de dúvida, consulte a Receita Federal ou um despachante aduaneiro."
        )
        
        observacoes.append(
            "[?] Esta sugestão foi gerada por inteligência artificial com base na "
            "Lei Complementar 214/2025 e na tabela NCM vigente."
        )
        
        return observacoes
    
    def _gerar_proximos_passos(self, confianca: float) -> List[str]:
        """Gera sugestões de próximos passos baseado na confiança"""
        passos = []
        
        if confianca < 0.75:
            passos.append(
                "1️⃣ **Validar classificação** com contador ou consultor fiscal especializado"
            )
        
        passos.append(
            "2️⃣ **Consultar tabela NCM** completa e atualizada no site da Receita Federal"
        )
        
        passos.append(
            "3️⃣ **Verificar alíquotas** de IBS e CBS aplicáveis ao produto"
        )
        
        if confianca < 0.5:
            passos.append(
                "4️⃣ **Considerar consulta formal** à RFB através de Solução de Consulta"
            )
        
        passos.append(
            f"5️⃣ **Documentar** a classificação escolhida e sua fundamentação"
        )
        
        return passos
    
    def formatar_para_exibicao(self, justificativa: Dict) -> str:
        """
        Formata justificativa como texto legível para exibição
        
        Args:
            justificativa: Dicionário com justificativa completa
        
        Returns:
            String formatada em Markdown
        """
        output = []
        
        # Cabeçalho
        classificacao = justificativa.get('classificacao', {})
        output.append("# [LIST] JUSTIFICATIVA DE CLASSIFICAÇÃO NCM\n")
        output.append(f"**NCM:** {classificacao.get('ncm', 'N/A')}")
        output.append(f"**Descrição:** {classificacao.get('descricao_oficial', 'N/A')}")
        output.append(f"**Confiança:** {classificacao.get('confianca', 'N/A')} ({classificacao.get('nivel_confianca', 'N/A')})")
        output.append("")
        
        # Fundamentação Técnica
        output.append("## [SEARCH] Fundamentação Técnica\n")
        for item in justificativa.get('fundamentacao_tecnica', []):
            output.append(item)
        output.append("")
        
        # Base Legal
        output.append("## ⚖️ Base Legal\n")
        for artigo in justificativa.get('base_legal', []):
            output.append(f"### {artigo.get('artigo', '')} - {artigo.get('lei', '')}")
            output.append(f"{artigo.get('resumo', '')}")
            output.append(f"*{artigo.get('relevancia', '')}*\n")
        
        # Observações
        output.append("## [!]  Observações Importantes\n")
        for obs in justificativa.get('observacoes', []):
            output.append(obs)
        output.append("")
        
        # Próximos Passos
        output.append("## [?] Próximos Passos Recomendados\n")
        for passo in justificativa.get('proximos_passos', []):
            output.append(passo)
        output.append("")
        
        # Rodapé
        output.append("---")
        output.append(f"*Gerado em: {justificativa.get('gerado_em', 'N/A')}*")
        output.append("*Sistema de IA NCM - Lei Complementar 214/2025*")
        
        return '\n'.join(output)


# Exemplo de uso
if __name__ == '__main__':
    gerador = GeradorJustificativa()
    
    # Dados de exemplo
    justificativa = gerador.gerar_justificativa_completa(
        ncm_codigo='9401.30.00',
        ncm_descricao='Assentos giratórios de altura ajustável',
        descricao_produto='Cadeira de escritório giratória com rodas',
        artigos_relacionados=[
            {
                'numero': 'Art. 4º',
                'lei': 'LC 214/2025',
                'texto': 'O IBS e a CBS incidem sobre operações onerosas com bens ou com serviços.',
                'relevancia': 'Artigo base sobre incidência de tributos'
            }
        ],
        confianca=0.95
    )
    
    # Exibe justificativa formatada
    print(gerador.formatar_para_exibicao(justificativa))

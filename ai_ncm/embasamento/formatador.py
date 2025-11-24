"""
Formatador de Respostas - Converte dados em diferentes formatos
"""

from typing import Dict, List, Optional
from datetime import datetime
import json


class FormatadorResposta:
    """
    Formata respostas da IA NCM em diferentes formatos (JSON, HTML, PDF, TXT)
    """
    
    def formatar_json(self, dados: Dict, pretty: bool = True) -> str:
        """
        Formata resposta como JSON
        
        Args:
            dados: Dicionário com dados da classificação
            pretty: Se deve indentar o JSON
        
        Returns:
            String JSON formatada
        """
        if pretty:
            return json.dumps(dados, ensure_ascii=False, indent=2)
        return json.dumps(dados, ensure_ascii=False)
    
    def formatar_html(self, dados: Dict) -> str:
        """
        Formata resposta como HTML
        
        Args:
            dados: Dicionário com dados da classificação
        
        Returns:
            String HTML formatada
        """
        html = ['<!DOCTYPE html>', '<html lang="pt-BR">', '<head>']
        html.append('<meta charset="UTF-8">')
        html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html.append('<title>Classificação NCM</title>')
        html.append('<style>')
        html.append(self._get_css_styles())
        html.append('</style>')
        html.append('</head>')
        html.append('<body>')
        
        # Container principal
        html.append('<div class="container">')
        
        # Cabeçalho
        html.append(self._gerar_cabecalho_html(dados))
        
        # Classificação Principal
        html.append(self._gerar_classificacao_html(dados.get('classificacao', {})))
        
        # Alternativas
        alternativas = dados.get('alternativas', [])
        if alternativas:
            html.append(self._gerar_alternativas_html(alternativas))
        
        # Fundamentação Técnica
        fundamentacao = dados.get('fundamentacao_tecnica', [])
        if fundamentacao:
            html.append(self._gerar_fundamentacao_html(fundamentacao))
        
        # Base Legal
        base_legal = dados.get('base_legal', [])
        if base_legal:
            html.append(self._gerar_base_legal_html(base_legal))
        
        # Observações
        observacoes = dados.get('observacoes', [])
        if observacoes:
            html.append(self._gerar_observacoes_html(observacoes))
        
        # Próximos Passos
        proximos_passos = dados.get('proximos_passos', [])
        if proximos_passos:
            html.append(self._gerar_proximos_passos_html(proximos_passos))
        
        # Rodapé
        html.append(self._gerar_rodape_html(dados))
        
        html.append('</div>')  # Fecha container
        html.append('</body>')
        html.append('</html>')
        
        return '\n'.join(html)
    
    def _get_css_styles(self) -> str:
        """Retorna estilos CSS para HTML"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; background: #f4f4f4; }
        .container { max-width: 900px; margin: 20px auto; background: white; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }
        h2 { color: #34495e; margin-top: 30px; margin-bottom: 15px; font-size: 1.5em; }
        h3 { color: #555; margin-top: 20px; margin-bottom: 10px; }
        .classificacao { background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .ncm-code { font-size: 2em; color: #2980b9; font-weight: bold; }
        .confianca { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .confianca.alta { background: #2ecc71; color: white; }
        .confianca.media { background: #f39c12; color: white; }
        .confianca.baixa { background: #e74c3c; color: white; }
        .alternativa { background: #fff; border-left: 4px solid #3498db; padding: 15px; margin: 10px 0; }
        .alternativa-ncm { font-weight: bold; color: #2980b9; font-size: 1.2em; }
        .fundamentacao { counter-reset: item; }
        .fundamentacao li { list-style: none; padding: 10px; margin: 10px 0; background: #f8f9fa; border-left: 3px solid #3498db; }
        .fundamentacao li::before { content: counter(item) ". "; counter-increment: item; font-weight: bold; color: #3498db; }
        .artigo { background: #fafafa; border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; }
        .observacao { padding: 10px; margin: 10px 0; border-left: 4px solid #f39c12; background: #fff3cd; }
        .passo { padding: 10px; margin: 10px 0; border-left: 4px solid #28a745; background: #d4edda; }
        .rodape { margin-top: 40px; padding-top: 20px; border-top: 2px solid #ecf0f1; text-align: center; color: #7f8c8d; font-size: 0.9em; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        table th, table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        table th { background: #34495e; color: white; }
        table tr:hover { background: #f5f5f5; }
        """
    
    def _gerar_cabecalho_html(self, dados: Dict) -> str:
        """Gera cabeçalho HTML"""
        return '<h1>📋 Classificação NCM - Inteligência Artificial</h1>'
    
    def _gerar_classificacao_html(self, classificacao: Dict) -> str:
        """Gera seção de classificação principal"""
        ncm = classificacao.get('ncm', 'N/A')
        descricao = classificacao.get('descricao_oficial', 'N/A')
        confianca = classificacao.get('confianca', '0%')
        nivel = classificacao.get('nivel_confianca', 'BAIXA')
        
        # Determina classe CSS da confiança
        confianca_class = 'baixa'
        if 'ALTA' in nivel:
            confianca_class = 'alta'
        elif 'MÉDIA' in nivel:
            confianca_class = 'media'
        
        html = ['<div class="classificacao">']
        html.append('<h2>🎯 Classificação Recomendada</h2>')
        html.append(f'<div class="ncm-code">{ncm}</div>')
        html.append(f'<p><strong>Descrição:</strong> {descricao}</p>')
        html.append(f'<p><strong>Confiança:</strong> <span class="confianca {confianca_class}">{confianca} - {nivel}</span></p>')
        html.append('</div>')
        
        return '\n'.join(html)
    
    def _gerar_alternativas_html(self, alternativas: List[Dict]) -> str:
        """Gera seção de classificações alternativas"""
        html = ['<h2>🔄 Classificações Alternativas</h2>']
        
        for alt in alternativas[:5]:  # Máximo 5 alternativas
            ncm = alt.get('ncm', 'N/A')
            descricao = alt.get('descricao', 'N/A')
            confianca = alt.get('confianca', 0)
            
            html.append('<div class="alternativa">')
            html.append(f'<div class="alternativa-ncm">{ncm}</div>')
            html.append(f'<p>{descricao}</p>')
            html.append(f'<p><small>Confiança: {confianca:.1%}</small></p>')
            html.append('</div>')
        
        return '\n'.join(html)
    
    def _gerar_fundamentacao_html(self, fundamentacao: List[str]) -> str:
        """Gera seção de fundamentação técnica"""
        html = ['<h2>🔍 Fundamentação Técnica</h2>']
        html.append('<ul class="fundamentacao">')
        
        for item in fundamentacao:
            # Remove numeração se já existir
            texto = item.split('.', 1)[-1].strip() if '. ' in item else item
            html.append(f'<li>{texto}</li>')
        
        html.append('</ul>')
        return '\n'.join(html)
    
    def _gerar_base_legal_html(self, base_legal: List[Dict]) -> str:
        """Gera seção de base legal"""
        html = ['<h2>⚖️ Base Legal</h2>']
        
        for artigo in base_legal:
            numero = artigo.get('artigo', 'N/A')
            lei = artigo.get('lei', 'LC 214/2025')
            resumo = artigo.get('resumo', '')
            relevancia = artigo.get('relevancia', '')
            
            html.append('<div class="artigo">')
            html.append(f'<h3>{numero} - {lei}</h3>')
            html.append(f'<p>{resumo}</p>')
            html.append(f'<p><em>{relevancia}</em></p>')
            html.append('</div>')
        
        return '\n'.join(html)
    
    def _gerar_observacoes_html(self, observacoes: List[str]) -> str:
        """Gera seção de observações"""
        html = ['<h2>⚠️ Observações Importantes</h2>']
        
        for obs in observacoes:
            html.append(f'<div class="observacao">{obs}</div>')
        
        return '\n'.join(html)
    
    def _gerar_proximos_passos_html(self, proximos_passos: List[str]) -> str:
        """Gera seção de próximos passos"""
        html = ['<h2>🎯 Próximos Passos Recomendados</h2>']
        
        for passo in proximos_passos:
            html.append(f'<div class="passo">{passo}</div>')
        
        return '\n'.join(html)
    
    def _gerar_rodape_html(self, dados: Dict) -> str:
        """Gera rodapé HTML"""
        gerado_em = dados.get('gerado_em', datetime.now().isoformat())
        
        html = ['<div class="rodape">']
        html.append(f'<p>Gerado em: {gerado_em}</p>')
        html.append('<p>Sistema de IA NCM - Lei Complementar 214/2025</p>')
        html.append('<p><em>Esta classificação é uma sugestão. A responsabilidade final é do contribuinte.</em></p>')
        html.append('</div>')
        
        return '\n'.join(html)
    
    def formatar_texto_simples(self, dados: Dict) -> str:
        """
        Formata resposta como texto simples
        
        Args:
            dados: Dicionário com dados da classificação
        
        Returns:
            String de texto formatada
        """
        linhas = []
        
        # Cabeçalho
        linhas.append('=' * 80)
        linhas.append('CLASSIFICAÇÃO NCM - INTELIGÊNCIA ARTIFICIAL')
        linhas.append('=' * 80)
        linhas.append('')
        
        # Classificação
        classificacao = dados.get('classificacao', {})
        linhas.append('CLASSIFICAÇÃO RECOMENDADA:')
        linhas.append('-' * 80)
        linhas.append(f"NCM: {classificacao.get('ncm', 'N/A')}")
        linhas.append(f"Descrição: {classificacao.get('descricao_oficial', 'N/A')}")
        linhas.append(f"Confiança: {classificacao.get('confianca', 'N/A')} ({classificacao.get('nivel_confianca', 'N/A')})")
        linhas.append('')
        
        # Alternativas
        alternativas = dados.get('alternativas', [])
        if alternativas:
            linhas.append('CLASSIFICAÇÕES ALTERNATIVAS:')
            linhas.append('-' * 80)
            for i, alt in enumerate(alternativas[:5], 1):
                linhas.append(f"{i}. {alt.get('ncm', 'N/A')} - {alt.get('descricao', 'N/A')}")
                linhas.append(f"   Confiança: {alt.get('confianca', 0):.1%}")
            linhas.append('')
        
        # Fundamentação
        fundamentacao = dados.get('fundamentacao_tecnica', [])
        if fundamentacao:
            linhas.append('FUNDAMENTAÇÃO TÉCNICA:')
            linhas.append('-' * 80)
            for item in fundamentacao:
                linhas.append(f"• {item}")
            linhas.append('')
        
        # Base Legal
        base_legal = dados.get('base_legal', [])
        if base_legal:
            linhas.append('BASE LEGAL:')
            linhas.append('-' * 80)
            for artigo in base_legal:
                linhas.append(f"{artigo.get('artigo', 'N/A')} - {artigo.get('lei', 'LC 214/2025')}")
                linhas.append(f"{artigo.get('resumo', '')}")
                linhas.append(f"({artigo.get('relevancia', '')})")
                linhas.append('')
        
        # Observações
        observacoes = dados.get('observacoes', [])
        if observacoes:
            linhas.append('OBSERVAÇÕES IMPORTANTES:')
            linhas.append('-' * 80)
            for obs in observacoes:
                linhas.append(f"⚠️  {obs}")
            linhas.append('')
        
        # Próximos Passos
        proximos_passos = dados.get('proximos_passos', [])
        if proximos_passos:
            linhas.append('PRÓXIMOS PASSOS RECOMENDADOS:')
            linhas.append('-' * 80)
            for passo in proximos_passos:
                linhas.append(f"➤ {passo}")
            linhas.append('')
        
        # Rodapé
        linhas.append('=' * 80)
        linhas.append(f"Gerado em: {dados.get('gerado_em', 'N/A')}")
        linhas.append('Sistema de IA NCM - Lei Complementar 214/2025')
        linhas.append('Esta classificação é uma sugestão. A responsabilidade final é do contribuinte.')
        linhas.append('=' * 80)
        
        return '\n'.join(linhas)


# Exemplo de uso
if __name__ == '__main__':
    formatador = FormatadorResposta()
    
    # Dados de exemplo
    dados_exemplo = {
        'classificacao': {
            'ncm': '9401.30.00',
            'descricao_oficial': 'Assentos giratórios de altura ajustável',
            'confianca': '95.0%',
            'nivel_confianca': 'MUITO ALTA'
        },
        'alternativas': [
            {'ncm': '9401.80.00', 'descricao': 'Outros assentos', 'confianca': 0.75},
            {'ncm': '9403.70.00', 'descricao': 'Móveis de plástico', 'confianca': 0.60}
        ],
        'fundamentacao_tecnica': [
            'Produto classificado no Capítulo 94 da NCM',
            'Enquadramento na Posição 9401 da tabela NCM vigente',
            'Correspondência com características: giratória, ajustável, rodas'
        ],
        'base_legal': [
            {
                'artigo': 'Art. 4º',
                'lei': 'LC 214/2025',
                'resumo': 'O IBS e a CBS incidem sobre operações onerosas com bens ou com serviços.',
                'relevancia': 'Artigo base sobre incidência de tributos'
            }
        ],
        'observacoes': [
            '✅ Alta confiança na classificação. Recomenda-se uso direto.',
            '📌 A classificação NCM é de responsabilidade do contribuinte.'
        ],
        'proximos_passos': [
            '2️⃣ Consultar tabela NCM completa no site da Receita Federal',
            '3️⃣ Verificar alíquotas de IBS e CBS aplicáveis'
        ],
        'gerado_em': datetime.now().isoformat()
    }
    
    # Teste de formatação JSON
    print("=== FORMATO JSON ===")
    print(formatador.formatar_json(dados_exemplo))
    print("\n")
    
    # Teste de formatação texto simples
    print("=== FORMATO TEXTO ===")
    print(formatador.formatar_texto_simples(dados_exemplo))
    print("\n")
    
    # HTML seria muito longo para exibir, mas pode ser salvo em arquivo
    html_output = formatador.formatar_html(dados_exemplo)
    print("=== FORMATO HTML (primeiras linhas) ===")
    print('\n'.join(html_output.split('\n')[:20]))
    print("...")

"""
Rotas API para Sugestões NCM com IA
"""

from flask import Blueprint, request, jsonify
from typing import Dict, List
import sys
from pathlib import Path

# Adiciona diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_ncm.predicao.motor_ia_ncm import MotorIANCM
from ai_ncm.embasamento.lei_complementar import BuscadorLeiComplementar
from ai_ncm.embasamento.justificativa import GeradorJustificativa
from ai_ncm.embasamento.formatador import FormatadorResposta


# Cria blueprint
ncm_ia_bp = Blueprint('ncm_ia', __name__, url_prefix='/api/ncm')

# Inicializa componentes (singleton)
motor_ia = None
buscador_legal = None
gerador_justificativa = None
formatador = None


def inicializar_componentes():
    """Inicializa componentes da IA (lazy loading)"""
    global motor_ia, buscador_legal, gerador_justificativa, formatador
    
    if motor_ia is None:
        try:
            motor_ia = MotorIANCM()
            buscador_legal = BuscadorLeiComplementar()
            gerador_justificativa = GeradorJustificativa()
            formatador = FormatadorResposta()
            print("[OK] Componentes da IA NCM inicializados com sucesso")
        except Exception as e:
            print(f"[X] Erro ao inicializar componentes da IA: {e}")
            raise


@ncm_ia_bp.route('/sugerir', methods=['POST'])
def sugerir_ncm():
    """
    POST /api/ncm/sugerir
    
    Sugere classificações NCM baseado na descrição do produto
    
    Body (JSON):
    {
        "descricao": "Cadeira de escritório giratória",
        "contexto": "Para revenda",
        "detalhes": {
            "material": "couro sintético",
            "caracteristicas": ["giratória", "rodas", "ajuste de altura"]
        },
        "top_n": 5,
        "formato": "json"  # json, html, texto
    }
    
    Returns:
        JSON com sugestões de NCM e embasamento legal
    """
    inicializar_componentes()
    
    try:
        # Extrai dados da requisição
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                'sucesso': False,
                'erro': 'Body JSON não fornecido'
            }), 400
        
        descricao = dados.get('descricao', '').strip()
        if not descricao:
            return jsonify({
                'sucesso': False,
                'erro': 'Campo "descricao" é obrigatório'
            }), 400
        
        contexto = dados.get('contexto', '')
        detalhes = dados.get('detalhes', {})
        top_n = dados.get('top_n', 5)
        formato = dados.get('formato', 'json').lower()
        
        # Faz sugestão
        resultado = motor_ia.sugerir_ncm(
            descricao=descricao,
            contexto=contexto,
            top_n=top_n
        )
        
        if not resultado.get('sucesso'):
            return jsonify(resultado), 404
        
        # Gera justificativa completa
        justificativa = gerador_justificativa.gerar_justificativa_completa(
            ncm_codigo=resultado['ncm'],
            ncm_descricao=resultado['descricao'],
            descricao_produto=descricao,
            artigos_relacionados=resultado.get('base_legal', []),
            confianca=resultado['confianca']
        )
        
        # Mescla resultado com justificativa
        resposta_completa = {
            **resultado,
            **justificativa
        }
        
        # Formata resposta conforme solicitado
        if formato == 'html':
            html = formatador.formatar_html(resposta_completa)
            return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
        elif formato == 'texto' or formato == 'txt':
            texto = formatador.formatar_texto_simples(resposta_completa)
            return texto, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
        else:  # json (padrão)
            return jsonify(resposta_completa), 200
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': f'Erro ao processar sugestão: {str(e)}'
        }), 500


@ncm_ia_bp.route('/validar/<ncm>', methods=['GET'])
def validar_ncm(ncm: str):
    """
    GET /api/ncm/validar/<ncm>
    
    Valida se um código NCM existe e está vigente
    
    Args:
        ncm: Código NCM (ex: 9401.30.00 ou 94013000)
    
    Returns:
        JSON com informações sobre o NCM
    """
    inicializar_componentes()
    
    try:
        # Normaliza NCM
        ncm_normalizado = ncm.replace('.', '').replace('-', '')
        
        # Busca no banco de dados NCM
        ncm_info = motor_ia._buscar_ncm_por_codigo(ncm_normalizado)
        
        if ncm_info:
            return jsonify({
                'sucesso': True,
                'valido': True,
                'ncm': ncm_info.get('codigo'),
                'descricao': ncm_info.get('descricao'),
                'vigente': ncm_info.get('vigente', True)
            }), 200
        else:
            return jsonify({
                'sucesso': True,
                'valido': False,
                'mensagem': f'NCM {ncm} não encontrado na tabela vigente'
            }), 404
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': f'Erro ao validar NCM: {str(e)}'
        }), 500


@ncm_ia_bp.route('/embasamento/<ncm>', methods=['GET'])
def obter_embasamento(ncm: str):
    """
    GET /api/ncm/embasamento/<ncm>
    
    Retorna embasamento legal para um NCM específico
    
    Args:
        ncm: Código NCM (ex: 9401.30.00)
    
    Query params:
        formato: json, html, texto
    
    Returns:
        Embasamento legal formatado
    """
    inicializar_componentes()
    
    try:
        formato = request.args.get('formato', 'json').lower()
        
        # Busca informações do NCM
        ncm_normalizado = ncm.replace('.', '').replace('-', '')
        ncm_info = motor_ia._buscar_ncm_por_codigo(ncm_normalizado)
        
        if not ncm_info:
            return jsonify({
                'sucesso': False,
                'erro': f'NCM {ncm} não encontrado'
            }), 404
        
        # Busca embasamento legal
        embasamento = motor_ia._obter_embasamento_legal(ncm)
        # Garante que embasamento seja uma lista de dicionários
        if isinstance(embasamento, dict):
            embasamento = [embasamento]
        
        # Gera justificativa completa
        justificativa = gerador_justificativa.gerar_justificativa_completa(
            ncm_codigo=ncm,
            ncm_descricao=ncm_info.get('descricao', ''),
            descricao_produto='',  # Não disponível nesta rota
            artigos_relacionados=embasamento,
            confianca=1.0  # Embasamento direto, sem predição
        )
        
        # Formata conforme solicitado
        if formato == 'html':
            html = formatador.formatar_html(justificativa)
            return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
        elif formato == 'texto' or formato == 'txt':
            texto = gerador_justificativa.formatar_para_exibicao(justificativa)
            return texto, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
        else:  # json
            return jsonify({
                'sucesso': True,
                'ncm': ncm,
                'descricao': ncm_info.get('descricao', ''),
                'embasamento': embasamento,
                'justificativa': justificativa
            }), 200
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': f'Erro ao obter embasamento: {str(e)}'
        }), 500


@ncm_ia_bp.route('/feedback', methods=['POST'])
def registrar_feedback():
    """
    POST /api/ncm/feedback
    
    Registra feedback do usuário sobre uma classificação
    (usado para aprendizado contínuo)
    
    Body (JSON):
    {
        "descricao": "Cadeira de escritório",
        "ncm_sugerido": "9401.30.00",
        "ncm_correto": "9401.30.00",
        "aprovado": true,
        "usuario_id": 123
    }
    
    Returns:
        Confirmação de registro
    """
    inicializar_componentes()
    
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                'sucesso': False,
                'erro': 'Body JSON não fornecido'
            }), 400
        
        # Valida campos obrigatórios
        campos_obrigatorios = ['descricao', 'ncm_sugerido', 'ncm_correto', 'aprovado']
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({
                    'sucesso': False,
                    'erro': f'Campo "{campo}" é obrigatório'
                }), 400
        
        # Registra feedback
        motor_ia.registrar_feedback(
            descricao=dados['descricao'],
            ncm_sugerido=dados['ncm_sugerido'],
            ncm_confirmado=dados['ncm_correto'],
            aprovado=dados['aprovado'],
            usuario_id=dados.get('usuario_id')
        )
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Feedback registrado com sucesso',
            'aprendizado_continuo': 'O sistema será retreinado automaticamente quando atingir 50 feedbacks'
        }), 201
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': f'Erro ao registrar feedback: {str(e)}'
        }), 500


@ncm_ia_bp.route('/buscar', methods=['GET'])
def buscar_ncm():
    """
    GET /api/ncm/buscar?query=cadeira&limit=10
    
    Busca códigos NCM por palavra-chave
    
    Query params:
        query: Termo de busca
        limit: Quantidade de resultados (padrão: 10)
    
    Returns:
        Lista de NCMs encontrados
    """
    inicializar_componentes()
    
    try:
        query = request.args.get('query', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({
                'sucesso': False,
                'erro': 'Parâmetro "query" é obrigatório'
            }), 400
        
        # Busca por similaridade
        resultados = motor_ia._buscar_ncm_por_similaridade(query, top_n=limit)
        
        return jsonify({
            'sucesso': True,
            'total': len(resultados),
            'resultados': resultados
        }), 200
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': f'Erro ao buscar NCM: {str(e)}'
        }), 500


@ncm_ia_bp.route('/artigos-legais', methods=['GET'])
def buscar_artigos_legais():
    """
    GET /api/ncm/artigos-legais?palavra=tributacao&max=5
    
    Busca artigos da LC 214/2025 por palavra-chave
    
    Query params:
        palavra: Termo de busca
        max: Máximo de resultados (padrão: 10)
    
    Returns:
        Artigos encontrados
    """
    inicializar_componentes()
    
    try:
        palavra = request.args.get('palavra', '').strip()
        max_resultados = int(request.args.get('max', 10))
        
        if not palavra:
            return jsonify({
                'sucesso': False,
                'erro': 'Parâmetro "palavra" é obrigatório'
            }), 400
        
        # Busca na lei
        resultados = buscador_legal.buscar_por_palavra_chave(
            palavra_chave=palavra,
            max_resultados=max_resultados
        )
        
        return jsonify({
            'sucesso': True,
            'palavra_buscada': palavra,
            'total': len(resultados),
            'artigos': resultados
        }), 200
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': f'Erro ao buscar artigos: {str(e)}'
        }), 500


@ncm_ia_bp.route('/estatisticas', methods=['GET'])
def obter_estatisticas():
    """
    GET /api/ncm/estatisticas
    
    Retorna estatísticas do sistema IA NCM
    
    Returns:
        Estatísticas gerais
    """
    inicializar_componentes()
    
    try:
        # Estatísticas da Lei
        stats_lei = buscador_legal.obter_estatisticas()
        
        # Estatísticas do motor (se disponível)
        stats_motor = {
            # Ajuste aqui para o atributo correto, por exemplo, motor_ia.ncm_lista ou motor_ia.ncms_list, ou defina como 0 se não houver equivalente
            'ncm_cadastrados': len(motor_ia.ncm_lista) if hasattr(motor_ia, 'ncm_lista') else 0,
            'modelo_treinado': hasattr(motor_ia, 'modelo') and motor_ia.modelo is not None,
            'historico_classificacoes': len(motor_ia.historico) if hasattr(motor_ia, 'historico') else 0
        }
        
        return jsonify({
            'sucesso': True,
            'lei_complementar': stats_lei,
            'motor_ia': stats_motor
        }), 200
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': f'Erro ao obter estatísticas: {str(e)}'
        }), 500


@ncm_ia_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET /api/ncm/health
    
    Verifica saúde do sistema
    
    Returns:
        Status dos componentes
    """
    try:
        inicializar_componentes()
        
        status = {
            'sucesso': True,
            'status': 'healthy',
            'componentes': {
                'motor_ia': motor_ia is not None,
                'buscador_legal': buscador_legal is not None,
                'gerador_justificativa': gerador_justificativa is not None,
                'formatador': formatador is not None
            }
        }
        
        return jsonify(status), 200
    
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'status': 'unhealthy',
            'erro': str(e)
        }), 500


# Função auxiliar para registrar rotas no app principal
def registrar_rotas_ncm_ia(app):
    """
    Registra blueprint das rotas NCM IA no app Flask
    
    Args:
        app: Instância do Flask app
    """
    app.register_blueprint(ncm_ia_bp)
    print("[OK] Rotas da IA NCM registradas: /api/ncm/*")


# Para teste standalone
if __name__ == '__main__':
    from flask import Flask
    
    app = Flask(__name__)
    registrar_rotas_ncm_ia(app)
    
    print("\n[START] Servidor de teste iniciado")
    print("[?] Rotas disponíveis:")
    print("   POST /api/ncm/sugerir - Sugerir NCM")
    print("   GET  /api/ncm/validar/<ncm> - Validar NCM")
    print("   GET  /api/ncm/embasamento/<ncm> - Obter embasamento")
    print("   POST /api/ncm/feedback - Registrar feedback")
    print("   GET  /api/ncm/buscar - Buscar NCM por palavra-chave")
    print("   GET  /api/ncm/artigos-legais - Buscar artigos LC 214/2025")
    print("   GET  /api/ncm/estatisticas - Ver estatísticas")
    print("   GET  /api/ncm/health - Health check")
    print("\n")
    
    app.run(debug=True, port=5001)

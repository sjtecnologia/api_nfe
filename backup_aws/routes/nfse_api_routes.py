"""
Rotas de API para NFS-e - Busca de NBS e validações
Data: 09/02/2026
Referência: NT007 v1.03.00
"""

from flask import Blueprint, jsonify, request
from database.connection import get_db
from services.nfse_validation_service import buscar_nbs_por_termo, validar_e_obter_dados_nbs

# Criar blueprint
nfse_api_bp = Blueprint('nfse_api', __name__, url_prefix='/api/nfse')


@nfse_api_bp.route('/nbs/search', methods=['GET'])
def buscar_nbs():
    """
    Busca códigos NBS para autocomplete/select2
    
    Query Parameters:
        q: Termo de busca (código, descrição ou palavras-chave)
        page: Número da página (default: 1)
        per_page: Resultados por página (default: 20, max: 50)
    
    Returns:
        JSON: {
            'results': [
                {
                    'id': 'codigo_nbs',
                    'text': 'codigo - descricao',
                    'codigo_nbs': 'codigo',
                    'descricao': 'descricao',
                    'codigo_lc116': 'codigo_lc116',
                    'categoria': 'categoria'
                },
                ...
            ],
            'pagination': {
                'more': bool
            }
        }
    """
    try:
        # Parâmetros
        termo = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 50)
        
        # Validar termo
        if not termo or len(termo) < 2:
            return jsonify({
                'results': [],
                'pagination': {'more': False},
                'message': 'Digite pelo menos 2 caracteres para buscar'
            })
        
        # Buscar
        db = next(get_db())
        resultados = buscar_nbs_por_termo(termo, db, limite=per_page + 1)  # +1 para saber se há mais
        
        # Verificar se há mais resultados
        has_more = len(resultados) > per_page
        if has_more:
            resultados = resultados[:per_page]
        
        # Formatar para select2
        results_formatted = []
        for nbs in resultados:
            results_formatted.append({
                'id': nbs['codigo_nbs'],
                'text': nbs['descricao_completa'],
                'codigo_nbs': nbs['codigo_nbs'],
                'descricao': nbs['descricao'],
                'codigo_lc116': nbs['codigo_lc116'],
                'categoria': nbs['categoria'],
                'subcategoria': nbs['subcategoria']
            })
        
        return jsonify({
            'results': results_formatted,
            'pagination': {
                'more': has_more
            }
        })
        
    except Exception as e:
        return jsonify({
            'results': [],
            'pagination': {'more': False},
            'error': str(e)
        }), 500


@nfse_api_bp.route('/nbs/<codigo>', methods=['GET'])
def obter_nbs(codigo):
    """
    Obtém detalhes de um código NBS específico
    
    Args:
        codigo: Código NBS (9 dígitos)
    
    Returns:
        JSON: {
            'sucesso': bool,
            'mensagem': str,
            'dados': {
                'codigo_nbs': str,
                'descricao': str,
                'codigo_lc116': str,
                'categoria': str,
                'subcategoria': str
            }
        }
    """
    try:
        db = next(get_db())
        resultado = validar_e_obter_dados_nbs(codigo, db)
        
        if resultado['sucesso']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 404
            
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao buscar NBS: {str(e)}',
            'dados': None
        }), 500


@nfse_api_bp.route('/validar', methods=['POST'])
def validar_campos_nfse():
    """
    Valida campos da Reforma Tributária de uma NFS-e
    
    Request Body (JSON):
        {
            'codigo_nbs': str,
            'codigo_indicador_operacao': str,
            'cst_ibs_cbs': str,
            'codigo_classificacao_tributaria': str,
            'codigo_localidade_incidencia': str,
            'percentual_redutor': float,
            'percentual_total_tributos_federais': float,
            'percentual_total_tributos_estaduais': float,
            'percentual_total_tributos_municipais': float
        }
    
    Returns:
        JSON: {
            'valido': bool,
            'erros': list,
            'avisos': list,
            'dados_validados': dict
        }
    """
    try:
        from services.nfse_validation_service import NFSeValidationService
        
        dados = request.get_json()
        if not dados:
            return jsonify({
                'valido': False,
                'erros': ['Dados não fornecidos'],
                'avisos': [],
                'dados_validados': {}
            }), 400
        
        db = next(get_db())
        resultado = NFSeValidationService.validar_nfse_completa(dados, db)
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            'valido': False,
            'erros': [f'Erro na validação: {str(e)}'],
            'avisos': [],
            'dados_validados': {}
        }), 500


@nfse_api_bp.route('/indicadores-operacao', methods=['GET'])
def listar_indicadores_operacao():
    """
    Lista indicadores de operação disponíveis (AnexoVII)
    
    Query Parameters:
        tipo: Filtrar por tipo (Interna, Interestadual, Exterior)
    
    Returns:
        JSON: {
            'indicadores': [
                {
                    'codigo': str,
                    'descricao': str,
                    'tipo_operacao': str,
                    'categoria': str
                },
                ...
            ]
        }
    """
    try:
        from database.models import IndicadorOperacaoIBSCBS
        
        db = next(get_db())
        query = db.query(IndicadorOperacaoIBSCBS).filter_by(ativo=True)
        
        # Filtrar por tipo se fornecido
        tipo = request.args.get('tipo')
        if tipo:
            query = query.filter_by(tipo_operacao=tipo)
        
        indicadores = query.order_by(IndicadorOperacaoIBSCBS.codigo_indicador).all()
        
        return jsonify({
            'indicadores': [ind.to_dict() for ind in indicadores]
        })
        
    except Exception as e:
        return jsonify({
            'indicadores': [],
            'error': str(e)
        }), 500


@nfse_api_bp.route('/classificacoes', methods=['GET'])
def listar_classificacoes():
    """
    Lista classificações tributárias disponíveis
    
    Returns:
        JSON: {
            'classificacoes': [
                {
                    'codigo': str,
                    'descricao': str,
                    'categoria': str,
                    'aliquota_sugerida_ibs': float,
                    'aliquota_sugerida_cbs': float
                },
                ...
            ]
        }
    """
    try:
        from database.models import ClassificacaoTributariaNFSe
        
        db = next(get_db())
        classificacoes = db.query(ClassificacaoTributariaNFSe).filter_by(
            ativo=True
        ).order_by(
            ClassificacaoTributariaNFSe.codigo_classificacao
        ).all()
        
        return jsonify({
            'classificacoes': [c.to_dict() for c in classificacoes]
        })
        
    except Exception as e:
        return jsonify({
            'classificacoes': [],
            'error': str(e)
        }), 500


@nfse_api_bp.route('/cst', methods=['GET'])
def listar_cst():
    """
    Lista códigos CST IBS/CBS disponíveis
    
    Returns:
        JSON: {
            'cst_list': [
                {
                    'codigo': str,
                    'descricao': str,
                    'categoria': str,
                    'permite_credito': bool,
                    'calcula_ibs': bool,
                    'calcula_cbs': bool
                },
                ...
            ]
        }
    """
    try:
        from database.models import CSTIBSCBS
        
        db = next(get_db())
        cst_list = db.query(CSTIBSCBS).filter_by(
            ativo=True
        ).order_by(
            CSTIBSCBS.codigo_cst
        ).all()
        
        return jsonify({
            'cst_list': [cst.to_dict() for cst in cst_list]
        })
        
    except Exception as e:
        return jsonify({
            'cst_list': [],
            'error': str(e)
        }), 500

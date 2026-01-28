"""
API Routes específicas para integração com LLM
Fornece dados estruturados da base de NCMs para treinamento/consulta
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from database.connection import get_db
import json
from typing import Dict, List, Any
from datetime import datetime

# Blueprint para API da LLM
llm_api_bp = Blueprint('llm_api', __name__, url_prefix='/api/llm')

def _get_db():
    """Helper para obter conexão com banco"""
    return next(get_db())

@llm_api_bp.route('/ncms/export', methods=['GET'])
def export_ncms_for_training():
    """
    Exporta toda a base de NCMs estruturada hierarquicamente para treinamento da LLM
    
    Formato otimizado para LLM entender:
    - Estrutura hierárquica completa
    - Contexto de cada nível
    - Relacionamentos pai-filho
    - Metadados para classificação
    """
    try:
        db = _get_db()
        
        # Busca todos os NCMs com ordenação hierárquica
        rows = db.execute(text("""
            SELECT 
                ncm_id, codigo, descricao, tipo,
                data_atualizacao, fonte_atualizacao,
                LENGTH(codigo) as nivel_digitos,
                CASE 
                    WHEN LENGTH(codigo) = 2 THEN 'Capítulo'
                    WHEN LENGTH(codigo) = 4 THEN 'Posição'
                    WHEN LENGTH(codigo) = 6 THEN 'Subposição'
                    WHEN LENGTH(codigo) = 8 THEN 'Item'
                    ELSE 'Indefinido'
                END as nivel_nome
            FROM ncms
            WHERE fonte_atualizacao IN ('siscomex', 'dados_iniciais')
            ORDER BY 
                SUBSTRING(codigo, 1, 2),  -- Capítulo
                SUBSTRING(codigo, 3, 2),  -- Posição  
                SUBSTRING(codigo, 5, 2),  -- Subposição
                SUBSTRING(codigo, 7, 2)   -- Item
        """)).fetchall()
        
        # Estrutura os dados para a LLM
        ncms_estruturados = []
        hierarquia_cache = {}  # Cache para relacionamentos
        
        for row in rows:
            codigo = row.codigo
            descricao = row.descricao
            tipo = row.tipo
            nivel_digitos = row.nivel_digitos
            nivel_nome = row.nivel_nome
            
            # Formata código com pontos
            if len(codigo) >= 8:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}.{codigo[6:8]}"
            elif len(codigo) >= 6:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}"
            elif len(codigo) >= 4:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}"
            else:
                codigo_formatado = codigo
            
            # Determina hierarquia (códigos pais)
            pais = []
            if len(codigo) >= 4:  # Tem capítulo pai
                capitulo = codigo[:2]
                pais.append({
                    'codigo': capitulo,
                    'nivel': 'Capítulo',
                    'descricao': hierarquia_cache.get(capitulo, 'N/A')
                })
            
            if len(codigo) >= 6:  # Tem posição pai
                posicao = codigo[:4]
                pais.append({
                    'codigo': posicao[:2] + '.' + posicao[2:4],
                    'nivel': 'Posição',
                    'descricao': hierarquia_cache.get(posicao, 'N/A')
                })
            
            if len(codigo) >= 8:  # Tem subposição pai
                subposicao = codigo[:6]
                pais.append({
                    'codigo': subposicao[:2] + '.' + subposicao[2:4] + '.' + subposicao[4:6],
                    'nivel': 'Subposição',
                    'descricao': hierarquia_cache.get(subposicao, 'N/A')
                })
            
            # Armazena no cache para próximas consultas
            hierarquia_cache[codigo] = descricao
            
            # Estrutura final para LLM
            ncm_estruturado = {
                'id': row.ncm_id,
                'codigo': codigo,
                'codigo_formatado': codigo_formatado,
                'descricao': descricao,
                'tipo': tipo,  # 'sintetico' ou 'analitico'
                'nivel': {
                    'nome': nivel_nome,
                    'digitos': nivel_digitos,
                    'posicao_hierarquia': (nivel_digitos // 2) - 1
                },
                'hierarquia_pais': pais,
                'pode_receber_lancamento': tipo == 'analitico',
                'contexto_completo': _gerar_contexto_completo(codigo, descricao, pais),
                'tags_busca': _gerar_tags_busca(codigo, descricao, nivel_nome),
                'atualizado_em': row.data_atualizacao.isoformat() if row.data_atualizacao else None,
                'fonte': row.fonte_atualizacao
            }
            
            ncms_estruturados.append(ncm_estruturado)
        
        # Estatísticas para contexto da LLM
        stats = {
            'total_ncms': len(ncms_estruturados),
            'por_tipo': {
                'sinteticos': len([n for n in ncms_estruturados if n['tipo'] == 'sintetico']),
                'analiticos': len([n for n in ncms_estruturados if n['tipo'] == 'analitico'])
            },
            'por_nivel': {
                'capitulos': len([n for n in ncms_estruturados if n['nivel']['nome'] == 'Capítulo']),
                'posicoes': len([n for n in ncms_estruturados if n['nivel']['nome'] == 'Posição']),
                'subposicoes': len([n for n in ncms_estruturados if n['nivel']['nome'] == 'Subposição']),
                'itens': len([n for n in ncms_estruturados if n['nivel']['nome'] == 'Item'])
            }
        }
        
        # Resposta completa para LLM
        resposta = {
            'success': True,
            'metadata': {
                'descricao': 'Base completa de NCMs (Nomenclatura Comum do Mercosul) hierárquica',
                'fonte': 'Sistema Siscomex - Receita Federal do Brasil',
                'estrutura': 'Hierárquica: Capítulo (2d) > Posição (4d) > Subposição (6d) > Item (8d)',
                'uso': 'NCMs analíticos (8 dígitos) são usados em NFe. Sintéticos são apenas classificação.',
                'formato_codigo': 'XX.XX.XX.XX onde cada par representa um nível hierárquico',
                'exportado_em': datetime.now().isoformat()
            },
            'estatisticas': stats,
            'ncms': ncms_estruturados
        }
        
        db.close()
        return jsonify(resposta)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao exportar NCMs para LLM'
        }), 500

@llm_api_bp.route('/ncms/search', methods=['GET'])
def search_ncms_for_llm():
    """
    Busca NCMs específicos para consultas da LLM
    
    Parâmetros:
    - q: termo de busca
    - tipo: 'sintetico', 'analitico' ou 'todos'
    - nivel: 'capitulo', 'posicao', 'subposicao', 'item' ou 'todos'
    - limit: limite de resultados (padrão 50)
    """
    try:
        query = request.args.get('q', '').strip()
        tipo_filtro = request.args.get('tipo', 'todos').lower()
        nivel_filtro = request.args.get('nivel', 'todos').lower()
        limit = min(int(request.args.get('limit', 50)), 200)  # Máximo 200
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Parâmetro q (busca) é obrigatório'
            }), 400
        
        db = _get_db()
        
        # Constrói filtros SQL
        filtros = ["(codigo ILIKE :query OR descricao ILIKE :query)"]
        params = {'query': f'%{query}%', 'limit': limit}
        
        if tipo_filtro in ['sintetico', 'analitico']:
            filtros.append("tipo = :tipo")
            params['tipo'] = tipo_filtro
        
        if nivel_filtro != 'todos':
            nivel_digitos_map = {
                'capitulo': 2,
                'posicao': 4,
                'subposicao': 6,
                'item': 8
            }
            if nivel_filtro in nivel_digitos_map:
                filtros.append("LENGTH(codigo) = :nivel_digitos")
                params['nivel_digitos'] = nivel_digitos_map[nivel_filtro]
        
        where_clause = " AND ".join(filtros)
        
        rows = db.execute(text(f"""
            SELECT 
                ncm_id, codigo, descricao, tipo,
                LENGTH(codigo) as nivel_digitos,
                CASE 
                    WHEN LENGTH(codigo) = 2 THEN 'Capítulo'
                    WHEN LENGTH(codigo) = 4 THEN 'Posição'
                    WHEN LENGTH(codigo) = 6 THEN 'Subposição'
                    WHEN LENGTH(codigo) = 8 THEN 'Item'
                    ELSE 'Indefinido'
                END as nivel_nome
            FROM ncms
            WHERE {where_clause}
            ORDER BY 
                CASE WHEN codigo ILIKE :query THEN 1 ELSE 2 END,
                codigo
            LIMIT :limit
        """), params).fetchall()
        
        # Formata resultados para LLM
        resultados = []
        for row in rows:
            codigo = row.codigo
            
            # Formata código
            if len(codigo) >= 8:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}.{codigo[6:8]}"
            elif len(codigo) >= 6:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}"
            elif len(codigo) >= 4:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}"
            else:
                codigo_formatado = codigo
            
            resultado = {
                'id': row.ncm_id,
                'codigo': codigo,
                'codigo_formatado': codigo_formatado,
                'descricao': row.descricao,
                'tipo': row.tipo,
                'nivel': {
                    'nome': row.nivel_nome,
                    'digitos': row.nivel_digitos
                },
                'pode_receber_lancamento': row.tipo == 'analitico',
                'relevancia': 'alta' if codigo.lower().startswith(query.lower()) else 'media'
            }
            
            resultados.append(resultado)
        
        resposta = {
            'success': True,
            'query': query,
            'filtros': {
                'tipo': tipo_filtro,
                'nivel': nivel_filtro
            },
            'total_encontrados': len(resultados),
            'resultados': resultados
        }
        
        db.close()
        return jsonify(resposta)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro na busca de NCMs'
        }), 500

@llm_api_bp.route('/ncms/hierarquia/<codigo>', methods=['GET'])
def get_hierarquia_ncm(codigo: str):
    """
    Retorna a hierarquia completa de um NCM específico
    Útil para LLM entender o contexto completo
    """
    try:
        # Remove pontos do código
        codigo_limpo = codigo.replace('.', '')
        
        if not codigo_limpo.isdigit() or len(codigo_limpo) not in [2, 4, 6, 8]:
            return jsonify({
                'success': False,
                'message': 'Código NCM deve ter 2, 4, 6 ou 8 dígitos'
            }), 400
        
        db = _get_db()
        
        # Busca o NCM específico
        ncm_row = db.execute(text("""
            SELECT ncm_id, codigo, descricao, tipo
            FROM ncms
            WHERE codigo = :codigo
        """), {'codigo': codigo_limpo}).fetchone()
        
        if not ncm_row:
            return jsonify({
                'success': False,
                'message': f'NCM {codigo} não encontrado'
            }), 404
        
        # Busca toda a hierarquia (pais e filhos)
        hierarquia_completa = _buscar_hierarquia_completa(db, codigo_limpo)
        
        resposta = {
            'success': True,
            'ncm_solicitado': {
                'codigo': codigo_limpo,
                'codigo_formatado': _formatar_codigo(codigo_limpo),
                'descricao': ncm_row.descricao,
                'tipo': ncm_row.tipo
            },
            'hierarquia': hierarquia_completa
        }
        
        db.close()
        return jsonify(resposta)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao buscar hierarquia do NCM'
        }), 500

@llm_api_bp.route('/ncms/stats', methods=['GET'])
def get_ncm_statistics():
    """
    Retorna estatísticas da base NCM para contexto da LLM
    """
    try:
        db = _get_db()
        
        # Estatísticas gerais
        stats = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN tipo = 'sintetico' THEN 1 END) as sinteticos,
                COUNT(CASE WHEN tipo = 'analitico' THEN 1 END) as analiticos,
                COUNT(CASE WHEN LENGTH(codigo) = 2 THEN 1 END) as capitulos,
                COUNT(CASE WHEN LENGTH(codigo) = 4 THEN 1 END) as posicoes,
                COUNT(CASE WHEN LENGTH(codigo) = 6 THEN 1 END) as subposicoes,
                COUNT(CASE WHEN LENGTH(codigo) = 8 THEN 1 END) as itens,
                COUNT(DISTINCT SUBSTRING(codigo, 1, 2)) as capitulos_unicos
            FROM ncms 
            WHERE fonte_atualizacao IN ('siscomex', 'dados_iniciais')
        """)).fetchone()
        
        if not stats:
            db.close()
            return jsonify({
                'success': False,
                'message': 'Nenhuma estatística disponível'
            }), 404
        
        # Top 10 capítulos com mais NCMs
        top_capitulos = db.execute(text("""
            SELECT 
                SUBSTRING(codigo, 1, 2) as capitulo,
                MAX(CASE WHEN LENGTH(codigo) = 2 THEN descricao END) as descricao_capitulo,
                COUNT(*) as total_ncms,
                COUNT(CASE WHEN tipo = 'analitico' THEN 1 END) as analiticos
            FROM ncms 
            WHERE fonte_atualizacao IN ('siscomex', 'dados_iniciais')
            GROUP BY SUBSTRING(codigo, 1, 2)
            ORDER BY total_ncms DESC
            LIMIT 10
        """)).fetchall()
        
        resposta = {
            'success': True,
            'estatisticas_gerais': {
                'total_ncms': stats.total,
                'tipos': {
                    'sinteticos': stats.sinteticos,
                    'analiticos': stats.analiticos
                },
                'niveis': {
                    'capitulos': stats.capitulos,
                    'posicoes': stats.posicoes,
                    'subposicoes': stats.subposicoes,
                    'itens': stats.itens
                },
                'capitulos_unicos': stats.capitulos_unicos
            },
            'top_capitulos': [
                {
                    'codigo': cap.capitulo,
                    'descricao': cap.descricao_capitulo,
                    'total_ncms': cap.total_ncms,
                    'ncms_analiticos': cap.analiticos
                }
                for cap in top_capitulos
            ],
            'contexto_para_llm': {
                'uso_principal': 'NCMs analíticos (8 dígitos) são usados em Notas Fiscais Eletrônicas',
                'estrutura': 'Hierárquica com 4 níveis: Capítulo → Posição → Subposição → Item',
                'fonte_oficial': 'Sistema Siscomex da Receita Federal do Brasil',
                'atualizacao': 'Base sincronizada com dados oficiais'
            }
        }
        
        db.close()
        return jsonify(resposta)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao obter estatísticas'
        }), 500

# Funções auxiliares
def _gerar_contexto_completo(codigo: str, descricao: str, pais: List[Dict]) -> str:
    """Gera contexto completo para a LLM entender o NCM"""
    contexto_parts = []
    
    # Adiciona contexto dos pais
    for pai in pais:
        contexto_parts.append(f"{pai['nivel']}: {pai['codigo']} - {pai['descricao']}")
    
    # Adiciona o próprio NCM
    codigo_formatado = _formatar_codigo(codigo)
    contexto_parts.append(f"NCM: {codigo_formatado} - {descricao}")
    
    return " > ".join(contexto_parts)

def _gerar_tags_busca(codigo: str, descricao: str, nivel: str) -> List[str]:
    """Gera tags para facilitar busca da LLM"""
    tags = [
        codigo,
        _formatar_codigo(codigo),
        nivel.lower(),
        descricao.lower()
    ]
    
    # Adiciona palavras-chave da descrição
    palavras = descricao.lower().split()
    tags.extend([p for p in palavras if len(p) > 3])
    
    return list(set(tags))  # Remove duplicatas

def _formatar_codigo(codigo: str) -> str:
    """Formata código NCM com pontos"""
    if len(codigo) >= 8:
        return f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}.{codigo[6:8]}"
    elif len(codigo) >= 6:
        return f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}"
    elif len(codigo) >= 4:
        return f"{codigo[:2]}.{codigo[2:4]}"
    else:
        return codigo

def _buscar_hierarquia_completa(db, codigo: str) -> Dict[str, Any]:
    """Busca hierarquia completa (pais e filhos) de um NCM"""
    hierarquia = {
        'pais': [],
        'filhos': [],
        'irmaos': []
    }
    
    # Busca pais (códigos menores)
    if len(codigo) > 2:
        pais_codes = []
        if len(codigo) >= 4:
            pais_codes.append(codigo[:2])  # Capítulo
        if len(codigo) >= 6:
            pais_codes.append(codigo[:4])  # Posição
        if len(codigo) >= 8:
            pais_codes.append(codigo[:6])  # Subposição
        
        if pais_codes:
            pais_rows = db.execute(text("""
                SELECT codigo, descricao, tipo
                FROM ncms 
                WHERE codigo = ANY(:codes)
                ORDER BY LENGTH(codigo)
            """), {'codes': pais_codes}).fetchall()
            
            hierarquia['pais'] = [
                {
                    'codigo': p.codigo,
                    'codigo_formatado': _formatar_codigo(p.codigo),
                    'descricao': p.descricao,
                    'tipo': p.tipo
                }
                for p in pais_rows
            ]
    
    # Busca filhos (códigos que começam com este)
    if len(codigo) < 8:
        filhos_rows = db.execute(text("""
            SELECT codigo, descricao, tipo
            FROM ncms 
            WHERE codigo LIKE :pattern AND LENGTH(codigo) > :current_len
            ORDER BY codigo
            LIMIT 20
        """), {
            'pattern': f'{codigo}%',
            'current_len': len(codigo)
        }).fetchall()
        
        hierarquia['filhos'] = [
            {
                'codigo': f.codigo,
                'codigo_formatado': _formatar_codigo(f.codigo),
                'descricao': f.descricao,
                'tipo': f.tipo
            }
            for f in filhos_rows
        ]
    
    return hierarquia


# ========== VALIDAÇÃO NFe COM IA ==========
@llm_api_bp.route('/validar-nfe', methods=['POST'])
def validar_nfe_com_ia():
    """
    Endpoint para validar dados da NFe usando IA antes da emissão.
    Chama o serviço ia_service FastAPI.
    """
    import requests
    import os
    
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                'sucesso': False,
                'validacao_ok': False,
                'erros_criticos': [{'campo': 'dados', 'erro': 'Nenhum dado recebido', 'solucao': 'Preencha o formulário'}],
                'alertas': [],
                'sugestoes_melhoria': [],
                'score_confianca': 0,
                'resumo': 'Dados não recebidos'
            })
        
        # URL do serviço de IA (FastAPI rodando na porta 8081)
        ia_service_url = os.getenv('IA_SERVICE_URL', 'http://localhost:8081')
        
        # Chamar serviço de IA
        response = requests.post(
            f'{ia_service_url}/valida/nfe-pre-emissao',
            json=dados,
            timeout=60
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'sucesso': False,
                'validacao_ok': True,
                'erros_criticos': [],
                'alertas': [{'alerta': f'Serviço IA retornou código {response.status_code}'}],
                'sugestoes_melhoria': [],
                'score_confianca': 0,
                'resumo': 'Serviço IA indisponível'
            })
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            'sucesso': False,
            'validacao_ok': True,
            'erros_criticos': [],
            'alertas': [{'alerta': 'Serviço de IA não está rodando. Verifique se o ia_service está ativo.'}],
            'sugestoes_melhoria': [],
            'score_confianca': 0,
            'resumo': 'Serviço IA offline'
        })
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'validacao_ok': True,
            'erros_criticos': [],
            'alertas': [{'alerta': f'Erro: {str(e)}'}],
            'sugestoes_melhoria': [],
            'score_confianca': 0,
            'resumo': f'Erro: {str(e)}'
        })
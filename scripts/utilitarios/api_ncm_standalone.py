#!/usr/bin/env python3
"""
API NCM INDEPENDENTE para LLM
Versão standalone que roda na porta 1234 usando apenas o arquivo JSON
Não precisa de banco de dados - carrega tudo na memória
"""

from flask import Flask, jsonify, request
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

app = Flask(__name__)

# Dados NCM globais (carregados na memória)
NCM_DATA: Optional[Dict[str, Any]] = None

def load_ncm_data():
    """Carrega dados NCM do arquivo JSON na memória"""
    global NCM_DATA
    
    json_files = [
        'ncms_training_data.json',
        'Tabela_NCM_Vigente_20251029.json',
        '../ncms_training_data.json'  # Caso esteja em subpasta
    ]
    
    for json_file in json_files:
        try:
            if os.path.exists(json_file):
                print(f"[IN] Carregando {json_file}...")
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Se é o arquivo de treinamento (já processado)
                if 'ncms' in data and 'estatisticas' in data:
                    NCM_DATA = data
                    print(f"[OK] Carregados {len(data.get('ncms') or [])} NCMs processados")
                    return True
                
                # Se é o arquivo original do Siscomex
                elif 'nomenclaturas' in data:
                    print("[?] Processando dados do Siscomex...")
                    NCM_DATA = processar_dados_siscomex(data)
                    if NCM_DATA:
                        print(f"[OK] Processados {len((NCM_DATA or {}).get('ncms') or [])} NCMs do Siscomex")
                        return True
                        
        except Exception as e:
            print(f"[!] Erro ao carregar {json_file}: {e}")
            continue
    
    print("[X] Nenhum arquivo de dados NCM encontrado")
    print("[?] Certifique-se de ter um destes arquivos:")
    for f in json_files:
        print(f"   • {f}")
    return False

def processar_dados_siscomex(data):
    """Processa dados originais do Siscomex para formato da API"""
    try:
        ncms_processados = []
        nomenclaturas = data.get('nomenclaturas', [])
        
        for item in nomenclaturas:
            codigo = item.get('codigo', '').strip()
            descricao = item.get('descricao', '').strip()
            
            if not codigo or not descricao:
                continue
            
            # Determina tipo baseado no tamanho
            tipo = 'analitico' if len(codigo) == 8 else 'sintetico'
            
            # Determina nível
            nivel_map = {2: 'Capítulo', 4: 'Posição', 6: 'Subposição', 8: 'Item'}
            nivel_nome = nivel_map.get(len(codigo), 'Indefinido')
            
            # Formata código com pontos
            if len(codigo) >= 8:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}.{codigo[6:8]}"
            elif len(codigo) >= 6:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}"
            elif len(codigo) >= 4:
                codigo_formatado = f"{codigo[:2]}.{codigo[2:4]}"
            else:
                codigo_formatado = codigo
            
            # Gera hierarquia pais
            pais = []
            if len(codigo) >= 4:
                cap_code = codigo[:2]
                pais.append({"codigo": cap_code, "nivel": "Capítulo", "descricao": "N/A"})
            if len(codigo) >= 6:
                pos_code = codigo[:4]
                pais.append({"codigo": pos_code, "nivel": "Posição", "descricao": "N/A"})
            if len(codigo) >= 8:
                sub_code = codigo[:6]
                pais.append({"codigo": sub_code, "nivel": "Subposição", "descricao": "N/A"})
            
            ncm_processado = {
                "id": len(ncms_processados) + 1,
                "codigo": codigo,
                "codigo_formatado": codigo_formatado,
                "descricao": descricao,
                "tipo": tipo,
                "nivel": {
                    "nome": nivel_nome,
                    "digitos": len(codigo)
                },
                "hierarquia_pais": pais,
                "pode_receber_lancamento": tipo == 'analitico',
                "contexto_completo": f"{codigo_formatado} - {descricao}",
                "tags_busca": [codigo, codigo_formatado, descricao.lower()]
            }
            
            ncms_processados.append(ncm_processado)
        
        # Calcula estatísticas
        total = len(ncms_processados)
        analiticos = len([n for n in ncms_processados if n['tipo'] == 'analitico'])
        sinteticos = total - analiticos
        
        return {
            "success": True,
            "metadata": {
                "descricao": "Base de NCMs processada do Siscomex",
                "fonte": "Sistema Siscomex - Receita Federal do Brasil",
                "estrutura": "Hierárquica: Capítulo (2d) > Posição (4d) > Subposição (6d) > Item (8d)",
                "processado_em": datetime.now().isoformat()
            },
            "estatisticas": {
                "total_ncms": total,
                "por_tipo": {
                    "analiticos": analiticos,
                    "sinteticos": sinteticos
                },
                "por_nivel": {
                    "capitulos": len([n for n in ncms_processados if n['nivel']['digitos'] == 2]),
                    "posicoes": len([n for n in ncms_processados if n['nivel']['digitos'] == 4]),
                    "subposicoes": len([n for n in ncms_processados if n['nivel']['digitos'] == 6]),
                    "itens": len([n for n in ncms_processados if n['nivel']['digitos'] == 8])
                }
            },
            "ncms": ncms_processados
        }
        
    except Exception as e:
        print(f"[X] Erro ao processar dados Siscomex: {e}")
        return None

@app.route('/api/llm/ncms/stats', methods=['GET'])
def get_ncm_statistics():
    """Retorna estatísticas da base NCM"""
    if not NCM_DATA:
        return jsonify({
            "success": False,
            "error": "Dados NCM não carregados. Verifique se o arquivo JSON existe."
        }), 500
    
    stats = NCM_DATA.get("estatisticas", {})
    
    return jsonify({
        "success": True,
        "estatisticas_gerais": stats,
        "contexto_para_llm": {
            "uso_principal": "NCMs analíticos (8 dígitos) são usados em Notas Fiscais Eletrônicas",
            "estrutura": "Hierárquica com 4 níveis: Capítulo → Posição → Subposição → Item",
            "fonte_oficial": "Sistema Siscomex da Receita Federal do Brasil",
            "atualizacao": "Base sincronizada com dados oficiais"
        }
    })

@app.route('/api/llm/ncms/search', methods=['GET'])
def search_ncms_for_llm():
    """Busca NCMs por termo para LLM"""
    if not NCM_DATA:
        return jsonify({
            "success": False,
            "error": "Dados NCM não carregados"
        }), 500
    
    query = request.args.get('q', '').strip().lower()
    tipo_filtro = request.args.get('tipo', 'todos').lower()
    nivel_filtro = request.args.get('nivel', 'todos').lower()
    limit = min(int(request.args.get('limit', 50)), 200)
    
    if not query:
        return jsonify({
            "success": False,
            "message": "Parâmetro q (busca) é obrigatório"
        }), 400
    
    resultados = []
    
    for ncm in NCM_DATA.get('ncms', []):
        # Verifica se corresponde à busca
        match = False
        if (query in ncm['codigo'].lower() or 
            query in ncm['descricao'].lower() or
            any(query in tag for tag in ncm.get('tags_busca', []))):
            match = True
        
        if not match:
            continue
        
        # Filtra por tipo
        if tipo_filtro != 'todos' and ncm['tipo'] != tipo_filtro:
            continue
        
        # Filtra por nível
        if nivel_filtro != 'todos':
            nivel_digitos_map = {
                'capitulo': 2, 'posicao': 4, 'subposicao': 6, 'item': 8
            }
            if nivel_filtro in nivel_digitos_map:
                if ncm['nivel']['digitos'] != nivel_digitos_map[nivel_filtro]:
                    continue
        
        # Calcula relevância
        relevancia = 'alta' if ncm['codigo'].lower().startswith(query) else 'media'
        
        resultado = {
            "id": ncm.get('id', 0),
            "codigo": ncm['codigo'],
            "codigo_formatado": ncm['codigo_formatado'],
            "descricao": ncm['descricao'],
            "tipo": ncm['tipo'],
            "nivel": ncm['nivel'],
            "pode_receber_lancamento": ncm['pode_receber_lancamento'],
            "relevancia": relevancia
        }
        
        resultados.append(resultado)
        
        if len(resultados) >= limit:
            break
    
    # Ordena por relevância
    resultados.sort(key=lambda x: (x['relevancia'] == 'alta', x['codigo']))
    
    return jsonify({
        "success": True,
        "query": query,
        "filtros": {
            "tipo": tipo_filtro,
            "nivel": nivel_filtro
        },
        "total_encontrados": len(resultados),
        "resultados": resultados
    })

@app.route('/api/llm/ncms/hierarquia/<codigo>', methods=['GET'])
def get_hierarquia_ncm(codigo: str):
    """Retorna hierarquia completa de um NCM"""
    if not NCM_DATA:
        return jsonify({
            "success": False,
            "error": "Dados NCM não carregados"
        }), 500
    
    # Remove pontos do código
    codigo_limpo = codigo.replace('.', '').strip()
    
    if not codigo_limpo.isdigit() or len(codigo_limpo) not in [2, 4, 6, 8]:
        return jsonify({
            "success": False,
            "message": "Código NCM deve ter 2, 4, 6 ou 8 dígitos"
        }), 400
    
    # Busca o NCM específico
    ncm_encontrado = None
    for ncm in NCM_DATA.get('ncms', []):
        if ncm['codigo'] == codigo_limpo:
            ncm_encontrado = ncm
            break
    
    if not ncm_encontrado:
        return jsonify({
            "success": False,
            "message": f"NCM {codigo} não encontrado"
        }), 404
    
    # Busca pais na hierarquia
    pais = []
    for ncm in NCM_DATA.get('ncms', []):
        # Verifica se é pai (código menor e início igual)
        if (len(ncm['codigo']) < len(codigo_limpo) and 
            codigo_limpo.startswith(ncm['codigo'])):
            pai = {
                "codigo": ncm['codigo'],
                "codigo_formatado": ncm['codigo_formatado'],
                "descricao": ncm['descricao'],
                "tipo": ncm['tipo']
            }
            pais.append(pai)
    
    # Ordena pais por tamanho (capítulo → posição → subposição)
    pais.sort(key=lambda x: len(x['codigo']))
    
    return jsonify({
        "success": True,
        "ncm_solicitado": {
            "codigo": ncm_encontrado['codigo'],
            "codigo_formatado": ncm_encontrado['codigo_formatado'],
            "descricao": ncm_encontrado['descricao'],
            "tipo": ncm_encontrado['tipo']
        },
        "hierarquia": {
            "pais": pais,
            "filhos": [],  # Não implementado para simplicidade
            "irmaos": []   # Não implementado para simplicidade
        }
    })

@app.route('/api/llm/ncms/export', methods=['GET'])
def export_ncms_for_training():
    """Exporta base completa para treinamento da LLM"""
    if not NCM_DATA:
        return jsonify({
            "success": False,
            "error": "Dados NCM não carregados"
        }), 500
    
    return jsonify(NCM_DATA)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check da API"""
    return jsonify({
        "status": "UP",
        "timestamp": datetime.now().isoformat(),
        "ncms_loaded": NCM_DATA is not None,
        "total_ncms": len(NCM_DATA.get('ncms', [])) if NCM_DATA else 0
    })

@app.route('/', methods=['GET'])
def home():
    """Página inicial da API"""
    if not NCM_DATA:
        return jsonify({
            "api": "NCM API para LLM",
            "status": "[X] Dados não carregados",
            "message": "Verifique se os arquivos JSON estão disponíveis"
        })
    
    stats = NCM_DATA.get('estatisticas', {})
    
    return jsonify({
        "api": "NCM API para LLM",
        "status": "[OK] Funcionando",
        "versao": "1.0",
        "total_ncms": stats.get('total_ncms', 0),
        "endpoints": [
            "/api/llm/ncms/stats",
            "/api/llm/ncms/search?q={termo}",
            "/api/llm/ncms/hierarquia/{codigo}",
            "/api/llm/ncms/export",
            "/health"
        ],
        "exemplo_uso": "curl http://192.168.0.52:1234/api/llm/ncms/search?q=animais&tipo=analitico"
    })

if __name__ == '__main__':
    print("[?] API NCM para LLM - Versão Independente")
    print("=" * 50)
    
    # Tenta carregar os dados
    if load_ncm_data() and NCM_DATA:
        stats = NCM_DATA.get('estatisticas', {})
        
        print("[OK] API pronta para usar!")
        print(f"[DATA] Total de NCMs: {stats.get('total_ncms', 0)}")
        print(f"   • Analíticos: {stats.get('por_tipo', {}).get('analiticos', 0)}")
        print(f"   • Sintéticos: {stats.get('por_tipo', {}).get('sinteticos', 0)}")
        print()
        print("[?] Servidor será executado em:")
        print("   http://0.0.0.0:8081")
        print("   http://192.168.0.52:8081")
        print()
        print("[LIST] Endpoints disponíveis:")
        print("   • GET /api/llm/ncms/stats")
        print("   • GET /api/llm/ncms/search?q={termo}")
        print("   • GET /api/llm/ncms/hierarquia/{codigo}")
        print("   • GET /api/llm/ncms/export")
        print("   • GET /health")
        print()
        print("[?] Teste rápido:")
        print("   curl http://192.168.0.52:8081/health")
        print()
        print("[?] IMPORTANTE: Sua LLM está em http://192.168.0.52:1234")
        print("[?] Esta API NCM está em http://192.168.0.52:8081")
        print()
        print("[START] Iniciando servidor...")
        
        app.run(
            debug=False,
            host='0.0.0.0',      # Aceita conexões de qualquer IP
            port=8081,           # Porta diferente da LLM (1234)
            threaded=True        # Suporte a múltiplas requisições
        )
    else:
        print("[X] Falha ao carregar dados NCM")
        print()
        print("[?] Para resolver:")
        print("1. Certifique-se de ter um destes arquivos no mesmo diretório:")
        print("   • ncms_training_data.json")
        print("   • Tabela_NCM_Vigente_20251029.json")
        print()
        print("2. Execute novamente:")
        print("   python3 api_ncm_standalone.py")
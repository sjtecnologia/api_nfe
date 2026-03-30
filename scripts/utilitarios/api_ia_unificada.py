#!/usr/bin/env python3
"""
[?] API IA UNIFICADA - NCM + LLM Integrados
Consolida todos os serviços de IA em uma única API
Porta 9000 - Serviço completo de sugestão tributária
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio
import json
from datetime import datetime
from servico_sugestao_ia import servico_sugestao, SugestaoRequest

app = Flask(__name__)
CORS(app)  # Permite requisições do frontend

# ============================================================================
# ROTAS PRINCIPAIS - SUGESTÃO TRIBUTÁRIA
# ============================================================================

@app.route('/api/sugestao', methods=['POST'])
def sugestao_tributaria():
    """
    Endpoint principal para sugestão tributária usando IA
    
    Body JSON:
    {
        "descricao": "Smartphone Samsung Galaxy",
        "tipo_item": "Produto",
        "uf_origem": "SP",
        "regime_tributario": "Simples Nacional",
        "cliente_id": 1
    }
    """
    try:
        data = request.get_json()
        
        # Validação básica
        if not data or not data.get('descricao'):
            return jsonify({
                "success": False,
                "erro": "Campo 'descricao' é obrigatório"
            }), 400
        
        # Criar request
        req = SugestaoRequest(
            descricao=data.get('descricao'),
            tipo_item=data.get('tipo_item', 'Produto'),
            cliente_id=data.get('cliente_id'),
            uf_origem=data.get('uf_origem'),
            regime_tributario=data.get('regime_tributario'),
            unidade_comercial=data.get('unidade_comercial', 'UN'),
            codigo_interno=data.get('codigo_interno')
        )
        
        # Executar sugestão de forma síncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resultado = loop.run_until_complete(servico_sugestao.gerar_sugestao(req))
        loop.close()
        
        # Retornar resultado
        if "erro" in resultado:
            return jsonify({
                "success": False,
                **resultado
            }), 500
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "produto": data.get('descricao'),
            "classificacao": resultado
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "erro": f"Erro ao processar sugestão: {str(e)}"
        }), 500

@app.route('/api/sugestao/lote', methods=['POST'])
def sugestao_lote():
    """
    Processar múltiplas sugestões em lote
    
    Body JSON:
    {
        "produtos": [
            {"descricao": "Smartphone", "tipo_item": "Produto"},
            {"descricao": "Notebook", "tipo_item": "Produto"}
        ],
        "uf_origem": "SP",
        "regime_tributario": "Simples Nacional"
    }
    """
    try:
        data = request.get_json()
        produtos = data.get('produtos', [])
        
        if not produtos:
            return jsonify({
                "success": False,
                "erro": "Lista 'produtos' é obrigatória"
            }), 400
        
        resultados = []
        
        for produto in produtos[:10]:  # Limite de 10 por requisição
            req = SugestaoRequest(
                descricao=produto.get('descricao'),
                tipo_item=produto.get('tipo_item', 'Produto'),
                uf_origem=data.get('uf_origem'),
                regime_tributario=data.get('regime_tributario')
            )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resultado = loop.run_until_complete(servico_sugestao.gerar_sugestao(req))
            loop.close()
            
            resultados.append({
                "produto": produto.get('descricao'),
                "classificacao": resultado
            })
        
        return jsonify({
            "success": True,
            "total_processados": len(resultados),
            "resultados": resultados
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "erro": f"Erro ao processar lote: {str(e)}"
        }), 500

# ============================================================================
# ROTAS DE BUSCA NCM
# ============================================================================

@app.route('/api/ncm/search', methods=['GET'])
def buscar_ncm():
    """
    Busca NCMs na base oficial
    Query params: q (termo de busca), limit (opcional)
    """
    try:
        termo = request.args.get('q', '').strip()
        limite = int(request.args.get('limit', 10))
        
        if not termo:
            return jsonify({
                "success": False,
                "erro": "Parâmetro 'q' é obrigatório"
            }), 400
        
        ncms = servico_sugestao.buscar_ncm_oficial(termo, limite)
        
        return jsonify({
            "success": True,
            "termo_busca": termo,
            "total_encontrados": len(ncms),
            "resultados": ncms
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "erro": f"Erro ao buscar NCM: {str(e)}"
        }), 500

# ============================================================================
# ROTAS DE STATUS E HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check da API"""
    # Verificar APIs dependentes
    apis_status = servico_sugestao._verificar_apis()
    
    return jsonify({
        "status": "UP" if apis_status else "DEGRADED",
        "timestamp": datetime.now().isoformat(),
        "servicos": {
            "api_ncm": "UP" if apis_status else "DOWN",
            "llm": "UP" if apis_status else "DOWN"
        },
        "configuracao": {
            "ncm_api": servico_sugestao.ncm_api_url,
            "llm_url": servico_sugestao.llm_url
        }
    })

@app.route('/api/status', methods=['GET'])
def status_detalhado():
    """Status detalhado do sistema"""
    import requests
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "servicos": {}
    }
    
    # Status API NCM
    try:
        ncm_response = requests.get(f"{servico_sugestao.ncm_api_url}/health", timeout=5)
        if ncm_response.status_code == 200:
            ncm_data = ncm_response.json()
            status["servicos"]["api_ncm"] = {
                "status": "UP",
                "total_ncms": ncm_data.get("total_ncms", 0)
            }
        else:
            status["servicos"]["api_ncm"] = {"status": "DOWN"}
    except:
        status["servicos"]["api_ncm"] = {"status": "DOWN"}
    
    # Status LLM
    try:
        llm_response = requests.get(f"{servico_sugestao.llm_url}/v1/models", timeout=5)
        if llm_response.status_code == 200:
            llm_data = llm_response.json()
            models = llm_data.get("data", [])
            status["servicos"]["llm"] = {
                "status": "UP",
                "modelo": models[0].get("id") if models else "N/A"
            }
        else:
            status["servicos"]["llm"] = {"status": "DOWN"}
    except:
        status["servicos"]["llm"] = {"status": "DOWN"}
    
    return jsonify(status)

@app.route('/', methods=['GET'])
def home():
    """Página inicial da API"""
    return jsonify({
        "api": "[?] API IA Unificada - Sugestão Tributária",
        "versao": "1.0",
        "status": "[OK] Funcionando",
        "documentacao": {
            "sugestao_individual": {
                "endpoint": "POST /api/sugestao",
                "exemplo": {
                    "descricao": "Smartphone Samsung Galaxy",
                    "tipo_item": "Produto",
                    "uf_origem": "SP",
                    "regime_tributario": "Simples Nacional"
                }
            },
            "sugestao_lote": {
                "endpoint": "POST /api/sugestao/lote",
                "exemplo": {
                    "produtos": [
                        {"descricao": "Smartphone", "tipo_item": "Produto"},
                        {"descricao": "Notebook", "tipo_item": "Produto"}
                    ],
                    "uf_origem": "SP"
                }
            },
            "busca_ncm": {
                "endpoint": "GET /api/ncm/search?q={termo}",
                "exemplo": "GET /api/ncm/search?q=smartphone&limit=5"
            },
            "health": {
                "endpoint": "GET /health"
            },
            "status": {
                "endpoint": "GET /api/status"
            }
        },
        "exemplos_curl": {
            "sugestao": 'curl -X POST http://localhost:9000/api/sugestao -H "Content-Type: application/json" -d \'{"descricao": "Smartphone", "tipo_item": "Produto", "uf_origem": "SP"}\'',
            "busca_ncm": 'curl http://localhost:9000/api/ncm/search?q=smartphone',
            "health": 'curl http://localhost:9000/health'
        }
    })

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("[?] API IA UNIFICADA - Sugestão Tributária com NCM + LLM")
    print("=" * 70)
    print()
    print("[LIST] SERVIÇOS INTEGRADOS:")
    print("   [OK] API NCM (13.217 códigos oficiais)")
    print("   [OK] LLM Llama-3.1-8B-Instruct")
    print("   [OK] Gerador de Prompts Otimizado")
    print("   [OK] Fallback Automático")
    print()
    print("[?] SERVIDOR:")
    print("   • URL: http://localhost:9000")
    print("   • Porta: 9000")
    print()
    print("[?] DEPENDÊNCIAS:")
    print(f"   • API NCM: {servico_sugestao.ncm_api_url}")
    print(f"   • LLM: {servico_sugestao.llm_url}")
    print()
    print("[?] ENDPOINTS DISPONÍVEIS:")
    print("   • POST /api/sugestao - Sugestão individual")
    print("   • POST /api/sugestao/lote - Sugestão em lote")
    print("   • GET /api/ncm/search?q={termo} - Buscar NCM")
    print("   • GET /health - Health check")
    print("   • GET /api/status - Status detalhado")
    print("   • GET / - Documentação")
    print()
    print("[?] TESTE RÁPIDO:")
    print('   curl -X POST http://localhost:9000/api/sugestao \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"descricao": "Smartphone Samsung", "tipo_item": "Produto", "uf_origem": "SP"}\'')
    print()
    print("[INFO] IMPORTANTE:")
    print("   • API NCM deve estar rodando na porta 8081")
    print("   • LLM deve estar rodando no IP 192.168.0.52:1234")
    print()
    print("[INICIO] Iniciando servidor na porta 9000...")
    print("=" * 70)
    print()
    
    app.run(
        debug=False,
        host='0.0.0.0',
        port=9000,
        threaded=True
    )

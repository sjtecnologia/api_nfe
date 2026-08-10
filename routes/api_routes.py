from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, text, func
from database.connection import get_db
from database.models import (
    Cfop, Ncm, Produto, Cliente, CertificadoDigital, NFeEmitidas,
    RegimeTributario, RegraTributacao, Csosnicms, Csticms, OrigemMercadoria
)
from auth.permissions import get_accessible_client_ids

api_bp = Blueprint('api', __name__)


def _get_cache():
    return current_app.extensions.get('cache')


@api_bp.route('/cfops', methods=['GET'])
@login_required
def get_cfops():
    """Retorna lista de CFOPs com paginação e cache."""
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(500, request.args.get('per_page', 100, type=int))
    cache_key = f'cfops_p{page}_pp{per_page}'
    cache = _get_cache()
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    db = next(get_db())
    try:
        total = db.query(func.count(Cfop.cfop_id)).scalar()
        cfops = db.query(Cfop).order_by(Cfop.cfop).offset((page - 1) * per_page).limit(per_page).all()
        cfop_list = [{"cfop_id": c.cfop_id, "cfop": c.cfop, "descricao": c.descricao} for c in cfops]
        resp = jsonify(cfop_list)
        resp.headers['X-Total-Count'] = str(total)
        if cache:
            cache.set(cache_key, resp, timeout=3600)
        return resp, 200
    finally:
        db.close()


@api_bp.route('/ncms', methods=['GET'])
@login_required
def get_ncms():
    """Retorna lista de NCMs com paginação e cache."""
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(500, request.args.get('per_page', 100, type=int))
    q = request.args.get('q', '').strip()
    cache_key = f'ncms_p{page}_pp{per_page}_q{q}'
    cache = _get_cache()
    if cache and not q:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    db = next(get_db())
    try:
        query = db.query(Ncm)
        if q:
            query = query.filter(or_(Ncm.codigo.ilike(f'%{q}%'), Ncm.descricao.ilike(f'%{q}%')))
        total = query.count()
        ncms = query.order_by(Ncm.codigo).offset((page - 1) * per_page).limit(per_page).all()
        ncm_list = [{"ncm_id": n.ncm_id, "codigo": n.codigo, "descricao": n.descricao} for n in ncms]
        resp = jsonify(ncm_list)
        resp.headers['X-Total-Count'] = str(total)
        if cache and not q:
            cache.set(cache_key, resp, timeout=3600)
        return resp, 200
    finally:
        db.close()

@api_bp.route('/produtos/cliente/<int:cliente_id>', methods=['GET'])
@login_required
def get_produtos_cliente(cliente_id):
    """Retorna produtos de um cliente específico"""
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    if cliente_id not in accessible_client_ids:
        return jsonify({"error": "Acesso negado para este cliente."}), 403
    
    produtos = db.query(Produto).filter_by(cliente_id=cliente_id, ativo=True).all()
    produto_list = []
    
    for p in produtos:
        produto_list.append({
            "produto_id": p.produto_id,
            "codigo_interno": p.codigo_interno,
            "descricao": p.descricao,
            "preco_unitario_padrao": float(getattr(p, "preco_unitario_padrao", 0) or 0),
            "unidade_comercial": p.unidade_comercial,
            "ncm_codigo": p.ncm.codigo if p.ncm else None,
            "cfop": p.cfop.cfop if p.cfop else None
        })
    
    return jsonify(produto_list), 200

@api_bp.route('/regras_tributacao/buscar', methods=['POST'])
@login_required
def buscar_regra_tributacao():
    """Busca regra de tributação baseada nos critérios fornecidos"""
    try:
        db = next(get_db())
        data = request.get_json()
        
        print(f"\n{'='*80}")
        print(f"[BUSCA REGRA] Requisição recebida")
        print(f"{'='*80}")
        
        if not data:
            return jsonify({"error": "Dados JSON não fornecidos."}), 400
        
        cliente_id = data.get('cliente_id')
        regime_tributario_id = data.get('regime_tributario_id')
        cfop_codigo = data.get('cfop_codigo')
        ncm_codigo = data.get('ncm_codigo')
        uf_origem = data.get('uf_origem')
        uf_destino = data.get('uf_destino')
        tipo_item = data.get('tipo_item')
        
        print(f"[PARAMS] Cliente ID: {cliente_id}")
        print(f"[PARAMS] Regime Tributário ID: {regime_tributario_id}")
        print(f"[PARAMS] CFOP: {cfop_codigo}")
        print(f"[PARAMS] NCM: {ncm_codigo}")
        print(f"[PARAMS] UF Origem: {uf_origem} | UF Destino: {uf_destino}")
        print(f"[PARAMS] Tipo Item: {tipo_item}")
        
        # Normalizar tipo_item para o formato do banco (primeira letra maiúscula)
        # Aceita: "PRODUTO", "produto", "Produto" → converte para "Produto"
        if tipo_item:
            tipo_item = tipo_item.capitalize()  # "PRODUTO" → "Produto", "produto" → "Produto"
            print(f"[PARAMS] Tipo Item normalizado: {tipo_item}")
        
        # Validar acesso ao cliente
        accessible_client_ids = get_accessible_client_ids(db)
        print(f"[ACCESS] IDs acessíveis: {accessible_client_ids}")
        
        if cliente_id and int(cliente_id) not in accessible_client_ids:
            print(f"[ERROR] Acesso negado ao cliente {cliente_id}")
            return jsonify({"error": "Acesso negado para este cliente."}), 403
        
        # Contar total de regras ativas no banco
        total_regras = db.query(RegraTributacao).filter(RegraTributacao.ativo == True).count()
        print(f"[INFO] Total de regras ativas no banco: {total_regras}")
        
        if total_regras == 0:
            print(f"[WARNING] ⚠️ NENHUMA REGRA TRIBUTÁRIA CADASTRADA NO BANCO!")
            return jsonify({"sucesso": False, "message": "Nenhuma regra tributária cadastrada. Cadastre regras em Admin > Regras de Tributação."}), 404
        
        # --- pré-calcular subqueries de CFOP e NCM (reusadas nos níveis) ---
        cfop_variantes = set()
        cfop_subquery = None
        if cfop_codigo:
            cfop_variantes = {cfop_codigo}
            if len(cfop_codigo) >= 4:
                if cfop_codigo[0] == '5':
                    cfop_variantes.add('6' + cfop_codigo[1:])
                elif cfop_codigo[0] == '6':
                    cfop_variantes.add('5' + cfop_codigo[1:])
            cfop_subquery = db.query(Cfop.cfop_id).filter(Cfop.cfop.in_(cfop_variantes))
            cfop_ids = [c.cfop_id for c in cfop_subquery.all()]
            print(f"[SEARCH] CFOP '{cfop_codigo}' (variantes: {cfop_variantes}) -> IDs: {cfop_ids}")

        ncm_subquery = None
        if ncm_codigo:
            ncm_subquery = db.query(Ncm.ncm_id).filter(Ncm.codigo == ncm_codigo)
            ncm_ids = [n.ncm_id for n in ncm_subquery.all()]
            print(f"[SEARCH] NCM '{ncm_codigo}' -> IDs: {ncm_ids}")

        opts = [
            joinedload(RegraTributacao.regime_tributario),
            joinedload(RegraTributacao.cfop),
            joinedload(RegraTributacao.ncm),
            joinedload(RegraTributacao.cst_icms_obj),
            joinedload(RegraTributacao.csosn_icms_obj),
            joinedload(RegraTributacao.motivo_desoneracao),
        ]
        order = [RegraTributacao.cliente_id.desc(), RegraTributacao.prioridade.desc()]

        def _base_query():
            q = db.query(RegraTributacao).options(*opts).filter(RegraTributacao.ativo == True)
            if cliente_id:
                q = q.filter(or_(RegraTributacao.cliente_id == cliente_id, RegraTributacao.cliente_id.is_(None)))
            else:
                q = q.filter(RegraTributacao.cliente_id.is_(None))
            if regime_tributario_id:
                q = q.filter(RegraTributacao.regime_tributario_id == regime_tributario_id)
            if tipo_item:
                q = q.filter(or_(RegraTributacao.tipo_item == tipo_item, RegraTributacao.tipo_item.is_(None)))
            return q

        def _aplicar_ncm_cfop_uf(q, usar_cfop, usar_ncm, usar_uf):
            if usar_cfop and cfop_subquery is not None:
                q = q.filter(or_(RegraTributacao.cfop_id.in_(cfop_subquery), RegraTributacao.cfop_id.is_(None)))
            if usar_ncm and ncm_subquery is not None:
                q = q.filter(or_(RegraTributacao.ncm_id.in_(ncm_subquery), RegraTributacao.ncm_id.is_(None)))
            if usar_uf:
                if uf_origem:
                    q = q.filter(or_(RegraTributacao.uf_origem == uf_origem, RegraTributacao.uf_origem.is_(None)))
                if uf_destino:
                    q = q.filter(or_(RegraTributacao.uf_destino == uf_destino, RegraTributacao.uf_destino.is_(None)))
            return q.order_by(*order)

        # Busca em cascata: do mais específico ao mais genérico
        niveis = [
            ("NCM+CFOP+UF",  True,  True,  True),   # nível 1 – match completo
            ("NCM+CFOP",     True,  True,  False),   # nível 2 – ignora UF
            ("NCM",          False, True,  False),   # nível 3 – ignora CFOP e UF
            ("genérico",     False, False, False),   # nível 4 – só cliente+regime
        ]

        regra_encontrada = None
        nivel_usado = None
        for descricao_nivel, usar_cfop, usar_ncm, usar_uf in niveis:
            q = _aplicar_ncm_cfop_uf(_base_query(), usar_cfop, usar_ncm, usar_uf)
            regra_encontrada = q.first()
            if regra_encontrada:
                nivel_usado = descricao_nivel
                print(f"[OK] Regra encontrada no nível '{descricao_nivel}' (ID {regra_encontrada.regra_tributacao_id})")
                break
            print(f"[CASCATA] Nível '{descricao_nivel}' sem resultado, tentando mais genérico...")

        if regra_encontrada:
            regra_dict = regra_encontrada.to_dict()
            print(f"   Descrição: {regra_dict.get('descricao_regra')}")

            # Normalizar campos None
            for campo, padrao in [('descricao_regra', 'Regra tributária automática'),
                                   ('aliquota_icms', 0.0), ('aliquota_pis', 0.0),
                                   ('aliquota_cofins', 0.0), ('aliquota_ipi', 0.0)]:
                if regra_dict.get(campo) is None:
                    regra_dict[campo] = padrao

            regra_dict['nivel_match'] = nivel_usado
            return jsonify({'sucesso': True, 'regra': regra_dict}), 200
        else:
            print(f"[!] Nenhuma regra encontrada em nenhum nível para cliente={cliente_id}, regime={regime_tributario_id}, NCM={ncm_codigo}, CFOP={cfop_codigo}")
            return jsonify({"sucesso": False, "message": "Nenhuma regra de tributação encontrada para os critérios fornecidos."}), 404
    
    except Exception as e:
        print(f"[X] ERRO ao buscar regra tributária: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erro ao buscar regra tributária: {str(e)}"}), 500

@api_bp.route('/clientes', methods=['GET'])
@login_required
def get_clientes():
    """Retorna lista de clientes que o usuário tem acesso"""
    db = next(get_db())
    accessible_client_ids = get_accessible_client_ids(db)
    
    clientes = db.query(Cliente).filter(Cliente.cliente_id.in_(accessible_client_ids)).all()
    cliente_list = []
    
    for c in clientes:
        cliente_list.append({
            "cliente_id": c.cliente_id,
            "razao_social": c.razao_social,
            "cnpj": c.cnpj,
            "uf": c.uf,
            "ativo": c.ativo
        })
    
    return jsonify(cliente_list), 200


@api_bp.route('/nfe/proximo-numero', methods=['GET'])
@login_required
def get_proximo_numero_nfe():
    """Busca o próximo número disponível de NFe para um cliente"""
    try:
        cliente_id = request.args.get('cliente_id', type=int)
        modelo = request.args.get('modelo', '55')
        serie = request.args.get('serie', 1, type=int)
        
        if not cliente_id:
            return jsonify({"success": False, "error": "cliente_id obrigatório"}), 400
        
        db = next(get_db())
        accessible_client_ids = get_accessible_client_ids(db)
        
        if cliente_id not in accessible_client_ids:
            return jsonify({"success": False, "error": "Acesso negado"}), 403
        
        # Tentar usar a função do banco de dados
        try:
            result = db.execute(
                text("SELECT get_proximo_numero_nfe(:cliente_id, :modelo, :serie)"),
                {"cliente_id": cliente_id, "modelo": modelo, "serie": serie}
            ).scalar()
            proximo_numero = result if result else 1
        except Exception as e:
            # Fallback: buscar MAX + 1
            print(f"[WARN] Função get_proximo_numero_nfe não encontrada, usando fallback: {e}")
            result = db.execute(
                text("""
                    SELECT COALESCE(MAX(numero), 0) + 1 
                    FROM nfe_emitidas 
                    WHERE cliente_id = :cliente_id 
                      AND modelo = :modelo 
                      AND serie = :serie
                """),
                {"cliente_id": cliente_id, "modelo": modelo, "serie": serie}
            ).scalar()
            proximo_numero = result if result else 1
        
        return jsonify({
            "success": True,
            "proximo_numero": proximo_numero,
            "cliente_id": cliente_id,
            "modelo": modelo,
            "serie": serie
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Erro ao buscar próximo número: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/validar-regra-ia', methods=['POST'])
@login_required
def validar_regra_ia():
    """
    Proxy para validação de regra tributária com IA.
    Evita problemas de CORS ao fazer requisição server-side.
    """
    import requests
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        print(f"[IA VALIDAÇÃO] Proxy recebeu dados: {data}")
        
        # Chamar serviço de IA internamente (server-side)
        response = requests.post(
            'http://localhost:8081/valida/regra',
            json=data,
            timeout=20
        )
        
        print(f"[IA VALIDAÇÃO] Status: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            print(f"[IA VALIDAÇÃO] Resultado: {resultado}")
            return jsonify(resultado), 200
        else:
            print(f"[IA VALIDAÇÃO] Erro: {response.text}")
            return jsonify({
                "error": "Erro ao validar com IA",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.Timeout:
        print(f"[IA VALIDAÇÃO] Timeout ao conectar serviço IA")
        return jsonify({
            "error": "Timeout ao validar com IA",
            "details": "Serviço demorou mais de 20 segundos"
        }), 504
        
    except requests.exceptions.ConnectionError:
        print(f"[IA VALIDAÇÃO] Erro de conexão com serviço IA")
        return jsonify({
            "error": "Serviço de IA indisponível",
            "details": "Não foi possível conectar ao serviço de IA na porta 8081"
        }), 503
        
    except Exception as e:
        print(f"[IA VALIDAÇÃO] Erro inesperado: {e}")
        return jsonify({
            "error": "Erro inesperado",
            "details": str(e)
        }), 500

@api_bp.route('/sugestao-produto-ia', methods=['POST'])
@login_required
def sugestao_produto_ia():
    """
    Sugestão de tributação de produto com IA com resolução de IDs locais.
    Usa o mesmo serviço do fluxo admin para mapear NCM/CFOP/CST/CSOSN.
    """
    from services.product_classification_service import (
        ProductClassificationError,
        ProductClassificationService,
        ProductClassificationUnavailable,
    )
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        db = next(get_db())
        try:
            svc = ProductClassificationService(db)
            resultado = svc.classify(
                descricao=data.get('descricao', ''),
                cliente_id=data.get('cliente_id'),
                tipo_item=data.get('tipo_item', 'Produto'),
                unidade_comercial=data.get('unidade_comercial', 'UN'),
                codigo_interno=data.get('codigo_interno', ''),
                user_id=getattr(current_user, 'id', None),
            )
            return jsonify(resultado), 200
        finally:
            db.close()

    except ProductClassificationUnavailable as e:
        return jsonify({
            "error": str(e),
            "details": "Serviço de IA indisponível na porta 8081"
        }), 503

    except ProductClassificationError as e:
        return jsonify({
            "error": str(e),
            "details": "Falha ao processar resposta de classificação"
        }), 500
        
    except Exception as e:
        print(f"[IA SUGESTÃO] Erro inesperado: {e}")
        return jsonify({
            "error": "Erro inesperado",
            "details": str(e)
        }), 500

@api_bp.route('/validar-produto-ia', methods=['POST'])
@login_required
def validar_produto_ia():
    """
    Proxy para validação final de produto com IA antes de salvar.
    Valida todos os campos tributários estão corretos.
    """
    import requests
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        print(f"[IA VALIDAÇÃO PRODUTO] Proxy recebeu dados: {data}")
        
        # Chamar serviço de IA para validar produto (usa o endpoint de validação de regra)
        response = requests.post(
            'http://localhost:8081/valida/regra',
            json=data,
            timeout=20
        )
        
        print(f"[IA VALIDAÇÃO PRODUTO] Status: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            print(f"[IA VALIDAÇÃO PRODUTO] Resultado: {resultado}")
            return jsonify(resultado), 200
        else:
            print(f"[IA VALIDAÇÃO PRODUTO] Erro: {response.text}")
            return jsonify({
                "error": "Erro ao validar com IA",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.Timeout:
        print(f"[IA VALIDAÇÃO PRODUTO] Timeout")
        return jsonify({
            "error": "Timeout ao validar com IA",
            "details": "Serviço demorou mais de 20 segundos"
        }), 504
        
    except requests.exceptions.ConnectionError:
        print(f"[IA VALIDAÇÃO PRODUTO] Erro de conexão")
        return jsonify({
            "error": "Serviço de IA indisponível",
            "details": "Não foi possível conectar ao serviço de IA na porta 8081"
        }), 503
        
    except Exception as e:
        print(f"[IA VALIDAÇÃO PRODUTO] Erro inesperado: {e}")
        return jsonify({
            "error": "Erro inesperado",
            "details": str(e)
        }), 500

@api_bp.route('/validar-regra-servico-ia', methods=['POST'])
@login_required
def validar_regra_servico_ia():
    """
    Proxy para validação de regra tributária de serviço (NFS-e) com IA.
    Evita problemas de CORS ao fazer requisição server-side.
    """
    import requests
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        print(f"[IA VALIDAÇÃO SERVIÇO] Proxy recebeu dados: {data}")
        
        # Chamar serviço de IA internamente (server-side)
        response = requests.post(
            'http://localhost:8081/valida/regra-servico',
            json=data,
            timeout=20
        )
        
        print(f"[IA VALIDAÇÃO SERVIÇO] Status: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            print(f"[IA VALIDAÇÃO SERVIÇO] Resultado: {resultado}")
            return jsonify(resultado), 200
        else:
            print(f"[IA VALIDAÇÃO SERVIÇO] Erro: {response.text}")
            return jsonify({
                "error": "Erro ao validar com IA",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.Timeout:
        print(f"[IA VALIDAÇÃO SERVIÇO] Timeout ao conectar serviço IA")
        return jsonify({
            "error": "Timeout ao validar com IA",
            "details": "Serviço demorou mais de 20 segundos"
        }), 504
        
    except requests.exceptions.ConnectionError:
        print(f"[IA VALIDAÇÃO SERVIÇO] Erro de conexão com serviço IA")
        return jsonify({
            "error": "Serviço de IA indisponível",
            "details": "Não foi possível conectar ao serviço de IA na porta 8081"
        }), 503
        
    except Exception as e:
        print(f"[IA VALIDAÇÃO SERVIÇO] Erro inesperado: {e}")
        return jsonify({
            "error": "Erro inesperado",
            "details": str(e)
        }), 500


@api_bp.route('/assistente-ia', methods=['POST'])
@login_required
def assistente_ia():
    """
    🤖 Assistente IA EmiteMax - Responde perguntas sobre emissão de NFe
    """
    try:
        data = request.get_json()
        pergunta = data.get('pergunta', '').strip()
        contexto = data.get('contexto', {})
        
        if not pergunta:
            return jsonify({"success": False, "error": "Pergunta não fornecida"}), 400
        
        # Extrair contexto da empresa e NFe
        empresa = contexto.get('empresa', {})
        nfe_info = contexto.get('nfe', {})
        
        crt = empresa.get('crt', 1)
        uf = empresa.get('uf', 'SP')
        regime = empresa.get('regime', 'Simples Nacional')
        
        print(f"[ASSISTENTE IA] Pergunta: {pergunta}")
        print(f"[ASSISTENTE IA] Contexto: CRT={crt}, UF={uf}, Regime={regime}")
        
        # Base de conhecimento estruturada por tipo de pergunta
        respostas = gerar_resposta_assistente(pergunta, crt, uf, regime, nfe_info)
        
        return jsonify({
            "success": True,
            "resposta": respostas
        }), 200
        
    except Exception as e:
        print(f"[ASSISTENTE IA] Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Erro ao processar pergunta",
            "details": str(e)
        }), 500


def gerar_resposta_assistente(pergunta, crt, uf, regime, nfe_info):
    """
    Gera resposta baseada em base de conhecimento estruturada
    """
    pergunta_lower = pergunta.lower()
    
    # 📦 Perguntas sobre emissão/venda dentro ou fora do estado
    if ('emitir' in pergunta_lower or 'venda' in pergunta_lower or 'vender' in pergunta_lower) and ('dentro' in pergunta_lower or 'mesmo estado' in pergunta_lower):
        return f"""✅ <strong>Como emitir venda dentro de {uf} (mesmo estado):</strong><br><br>
<strong>1. CFOP a usar:</strong><br>
• <strong>5102</strong> - Venda de mercadoria adquirida de terceiros<br>
• <strong>5405</strong> - Venda com mercadoria sujeita ao ST<br><br>
<strong>2. Para Simples Nacional (seu caso):</strong><br>
• CSOSN: <strong>102</strong> (mais comum)<br>
• Origem: <strong>0</strong> (Nacional)<br>
• Não precisa calcular ICMS manualmente!<br><br>
<strong>3. Passo a passo:</strong><br>
1. Selecione o destinatário (mesmo UF que você)<br>
2. Adicione o produto<br>
3. CFOP: <strong>5102</strong><br>
4. CSOSN: <strong>102</strong><br>
5. Sistema calcula automaticamente<br><br>
💡 O número <strong>5</strong> inicial indica operação <strong>dentro</strong> do estado."""
    
    if ('emitir' in pergunta_lower or 'venda' in pergunta_lower or 'vender' in pergunta_lower) and ('fora' in pergunta_lower or 'outro estado' in pergunta_lower or 'interestadual' in pergunta_lower):
        return f"""✅ <strong>Como emitir venda para outro estado (interestadual):</strong><br><br>
<strong>1. CFOP a usar:</strong><br>
• <strong>6102</strong> - Venda de mercadoria para outro estado<br>
• <strong>6405</strong> - Venda com mercadoria sujeita ao ST<br><br>
<strong>2. Para Simples Nacional (seu caso):</strong><br>
• CSOSN: <strong>102</strong> ou <strong>103</strong><br>
• Origem: <strong>0</strong> (Nacional)<br>
• Sistema calcula DIFAL automaticamente para consumidor final<br><br>
<strong>3. Passo a passo:</strong><br>
1. Selecione destinatário em <strong>outro UF</strong><br>
2. Adicione o produto<br>
3. CFOP: <strong>6102</strong><br>
4. CSOSN: <strong>102</strong><br>
5. Se for consumidor final, marque "Consumidor Final"<br><br>
💡 O número <strong>6</strong> inicial indica operação <strong>interestadual</strong>.<br>
⚠️ Para consumidor final, há DIFAL (diferencial de alíquota)."""
    
    # 📦 CFOP - Perguntas sobre CFOP
    if 'cfop' in pergunta_lower:
        if 'dentro' in pergunta_lower or 'mesmo estado' in pergunta_lower:
            return f"""✅ <strong>CFOP para venda dentro de {uf}:</strong><br><br>
<strong>5102</strong> - Venda de mercadoria adquirida de terceiros<br>
<strong>5405</strong> - Venda de mercadoria adquirida de terceiros em operação com mercadoria sujeita ao regime de substituição tributária<br><br>
📋 <strong>Como preencher:</strong><br>
1. No campo CFOP do produto, selecione <strong>5102</strong><br>
2. Para produtos com ST, use <strong>5405</strong><br><br>
💡 O número <strong>5</strong> inicial indica operação dentro do estado."""
        
        elif 'fora' in pergunta_lower or 'outro estado' in pergunta_lower or 'interestadual' in pergunta_lower:
            return f"""✅ <strong>CFOP para venda interestadual (fora de {uf}):</strong><br><br>
<strong>6102</strong> - Venda de mercadoria adquirida de terceiros<br>
<strong>6405</strong> - Venda com mercadoria sujeita ao regime de ST<br><br>
📋 <strong>Como preencher:</strong><br>
1. No campo CFOP do produto, selecione <strong>6102</strong><br>
2. Para produtos com ST, use <strong>6405</strong><br><br>
💡 O número <strong>6</strong> inicial indica operação interestadual.<br>
⚠️ <strong>ATENÇÃO:</strong> Operações interestaduais exigem cálculo de DIFAL (Diferencial de Alíquota) para consumidor final."""
        
        elif 'diferença' in pergunta_lower or '5102' in pergunta_lower or '6102' in pergunta_lower:
            return """✅ <strong>Diferença entre CFOP 5102 e 6102:</strong><br><br>
<strong>5102</strong> = Venda <strong>DENTRO</strong> do estado (Ex: SP → SP)<br>
<strong>6102</strong> = Venda para <strong>OUTRO</strong> estado (Ex: SP → RJ)<br><br>
📌 <strong>Regra simples:</strong><br>
• Se cliente no mesmo estado que você → Use <strong>5xxx</strong><br>
• Se cliente em outro estado → Use <strong>6xxx</strong><br><br>
💡 O sistema detecta automaticamente baseado no UF do destinatário!"""
    
    # 🧮 CSOSN - Simples Nacional
    if ('csosn' in pergunta_lower or 'simples nacional' in pergunta_lower) and crt == 1:
        if 'qual' in pergunta_lower or 'usar' in pergunta_lower or 'número' in pergunta_lower:
            return """✅ <strong>CSOSN mais comuns no Simples Nacional:</strong><br><br>
<strong>102</strong> - Tributada pelo Simples Nacional sem permissão de crédito<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Mais usado! Para maioria das vendas normais<br><br>
<strong>103</strong> - Isenção do ICMS para faixa de receita bruta<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Empresas com receita menor<br><br>
<strong>500</strong> - ICMS cobrado anteriormente por ST<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Quando já foi pago ICMS por substituição<br><br>
<strong>900</strong> - Outros (operações especiais)<br><br>
📋 <strong>Como preencher:</strong><br>
1. Campo "CSOSN ICMS": selecione <strong>102</strong> (padrão)<br>
2. O sistema calcula automaticamente<br><br>
💡 <strong>Dica:</strong> No Simples Nacional, você NÃO precisa calcular ICMS manualmente!"""
        
        return f"""✅ <strong>CSOSN - Código de Situação da Operação no Simples Nacional</strong><br><br>
Empresas do <strong>Simples Nacional (CRT=1)</strong> usam CSOSN ao invés de CST.<br><br>
<strong>Códigos principais:</strong><br>
• <strong>102</strong> - Tributada sem crédito (mais comum)<br>
• <strong>103</strong> - Isenção<br>
• <strong>400</strong> - Não tributada<br>
• <strong>500</strong> - ICMS ST<br><br>
💡 Seu regime atual: <strong>{regime}</strong>"""
    
    # 🏷️ CST - Regime Normal
    if ('cst' in pergunta_lower or 'regime normal' in pergunta_lower) and crt == 3:
        if '00' in pergunta_lower or '20' in pergunta_lower or '40' in pergunta_lower:
            return """✅ <strong>CST - Código de Situação Tributária (Regime Normal):</strong><br><br>
<strong>00</strong> - Tributada integralmente<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Venda normal com ICMS cheio (12%, 18%, etc)<br><br>
<strong>20</strong> - Com redução de base de cálculo<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Quando há benefício fiscal (ex: redução de 60%)<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚠️ <strong>Requer código de benefício (cBenef)</strong><br><br>
<strong>40</strong> - Isenta<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Operação isenta de ICMS por lei<br><br>
<strong>41</strong> - Não tributada<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Operação que não incide ICMS<br><br>
<strong>50</strong> - Suspensão<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 ICMS suspenso por decisão judicial/lei<br><br>
<strong>60</strong> - ICMS cobrado anteriormente por ST<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Produto já teve ICMS retido<br><br>
<strong>70</strong> - Com redução de BC e cobrança do ICMS por ST<br>
&nbsp;&nbsp;&nbsp;&nbsp;📌 Casos específicos de ST com redução<br><br>
📋 <strong>Como preencher:</strong><br>
1. Campo "CST ICMS": selecione conforme operação<br>
2. Se CST 20, 30, 40, 50, 70 → preencha também o <strong>cBenef</strong>"""
        
        return """✅ <strong>CST no Regime Normal (CRT=3):</strong><br><br>
O CST indica a situação tributária do ICMS:<br><br>
• <strong>00</strong> = Tributado normalmente<br>
• <strong>20</strong> = Tributado com redução<br>
• <strong>40</strong> = Isento<br>
• <strong>60</strong> = ICMS ST<br><br>
📌 Escolha conforme a operação fiscal do produto."""
    
    # 💰 ICMS - Cálculos
    if 'icms' in pergunta_lower and ('calcular' in pergunta_lower or 'como' in pergunta_lower):
        if 'interestadual' in pergunta_lower or 'outro estado' in pergunta_lower:
            return f"""✅ <strong>Cálculo de ICMS Interestadual:</strong><br><br>
<strong>Operação de {uf} para outro estado:</strong><br><br>
<strong>1. ICMS Origem (seu estado):</strong><br>
&nbsp;&nbsp;&nbsp;&nbsp;Alíquota interestadual (geralmente 12% ou 7%)<br><br>
<strong>2. DIFAL (Diferencial de Alíquota):</strong><br>
&nbsp;&nbsp;&nbsp;&nbsp;Diferença entre alíquota interna do destino e origem<br>
&nbsp;&nbsp;&nbsp;&nbsp;Parte para Estado de destino<br>
&nbsp;&nbsp;&nbsp;&nbsp;Parte para Estado de origem<br><br>
📋 <strong>O sistema calcula automaticamente!</strong><br><br>
💡 <strong>Exemplo:</strong><br>
Venda SP → RJ de R$ 100,00<br>
• ICMS interestadual (12%): R$ 12,00<br>
• Alíquota interna RJ (20%): R$ 20,00<br>
• DIFAL: R$ 8,00 (20% - 12%)<br><br>
⚠️ DIFAL só para <strong>consumidor final</strong> (indFinal=1)"""
        
        if regime == "Simples Nacional":
            return """✅ <strong>ICMS no Simples Nacional:</strong><br><br>
<strong>Boa notícia!</strong> No Simples Nacional você NÃO precisa calcular ICMS manualmente! 🎉<br><br>
📌 <strong>Como funciona:</strong><br>
1. Você paga ICMS junto com DAS (guia única)<br>
2. Na NFe, apenas informe o CSOSN correto<br>
3. O sistema preenche automaticamente<br><br>
<strong>Campos a preencher:</strong><br>
• CSOSN: Geralmente <strong>102</strong> ou <strong>103</strong><br>
• Origem: <strong>0</strong> (Nacional)<br>
• Pronto! ✅<br><br>
💡 Muito mais simples que Regime Normal!"""
        
        return """✅ <strong>Cálculo de ICMS (Regime Normal):</strong><br><br>
<strong>Fórmula básica:</strong><br>
ICMS = Valor do Produto × Alíquota ICMS<br><br>
<strong>Alíquotas comuns:</strong><br>
• 18% - Padrão SP<br>
• 12% - Operações interestaduais<br>
• 7% - Operações interestaduais (Sul/Sudeste)<br><br>
📋 <strong>O sistema calcula automaticamente</strong> baseado no UF de destino!<br><br>
⚠️ Com CST 20 (redução), aplica-se % de redução antes."""
    
    # 🎁 cBenef - Código de Benefício Fiscal
    if 'cbenef' in pergunta_lower or 'beneficio' in pergunta_lower or 'benefício' in pergunta_lower:
        return """✅ <strong>cBenef - Código de Benefício Fiscal:</strong><br><br>
Obrigatório quando usar CST que indica benefício fiscal:<br>
• CST <strong>20</strong> (redução de BC)<br>
• CST <strong>30</strong> (isenta ou não tributada com ST)<br>
• CST <strong>40</strong> (isenta)<br>
• CST <strong>41</strong> (não tributada)<br>
• CST <strong>50</strong> (suspensão)<br>
• CST <strong>70</strong> (redução com ST)<br><br>
📋 <strong>Como preencher:</strong><br>
1. Preencha o CST correspondente<br>
2. No campo "Cód. Benef. Fiscal", informe o código<br><br>
📌 <strong>Exemplo de códigos SP:</strong><br>
• SP000001 a SP999999<br><br>
⚠️ <strong>Onde encontrar seu código?</strong><br>
• Consulte RICMS-SP Anexo II Art. 77<br>
• Pergunte ao seu contador<br>
• Site da SEFAZ-SP<br><br>
💡 <strong>Campo já está disponível no formulário!</strong>"""
    
    # 👤 Consumidor Final
    if 'consumidor final' in pergunta_lower or 'cpf' in pergunta_lower or 'pessoa fisica' in pergunta_lower or 'pessoa física' in pergunta_lower:
        return """✅ <strong>Emissão para Consumidor Final (CPF):</strong><br><br>
📋 <strong>Passo a passo:</strong><br><br>
<strong>1. Dados do Destinatário:</strong><br>
• CPF (não CNPJ)<br>
• Nome completo<br>
• Endereço completo<br><br>
<strong>2. Indicador de Consumidor Final:</strong><br>
• Marque <strong>SIM</strong> no campo "Consumidor Final"<br>
• Isso define indFinal = 1<br><br>
<strong>3. Indicador de Presença:</strong><br>
• <strong>1</strong> - Operação presencial<br>
• <strong>2</strong> - Internet<br>
• <strong>3</strong> - Telefone<br>
• <strong>9</strong> - Outros<br><br>
<strong>4. CFOP:</strong><br>
• Dentro do estado: <strong>5102</strong><br>
• Fora do estado: <strong>6102</strong><br><br>
⚠️ <strong>ATENÇÃO venda interestadual:</strong><br>
Sistema calcula automaticamente DIFAL (diferencial de alíquota)!"""
    
    # 🚚 Tipo de operação (entrada/saída)
    if 'entrada' in pergunta_lower or 'saída' in pergunta_lower or 'saida' in pergunta_lower:
        return """✅ <strong>Tipo de Operação - Entrada vs Saída:</strong><br><br>
<strong>0 - Entrada:</strong><br>
📥 Você está RECEBENDO mercadoria<br>
• Compra de fornecedor<br>
• Devolução de cliente<br>
• Transferência recebida<br><br>
<strong>1 - Saída:</strong><br>
📤 Você está ENVIANDO mercadoria<br>
• Venda para cliente<br>
• Devolução para fornecedor<br>
• Transferência enviada<br><br>
💡 <strong>Na maioria dos casos:</strong><br>
Você vai usar <strong>SAÍDA (1)</strong> para vendas!<br><br>
📋 Este campo fica em "Identificação da NFe"."""
    
    # 📦 Produtos
    if 'produto' in pergunta_lower and ('adicionar' in pergunta_lower or 'preencher' in pergunta_lower):
        return """✅ <strong>Como adicionar produtos na NFe:</strong><br><br>
📋 <strong>Passo a passo:</strong><br><br>
<strong>1. Clique em "Adicionar Produto"</strong><br><br>
<strong>2. Preencha os campos obrigatórios:</strong><br>
• Código do produto<br>
• Descrição<br>
• NCM (8 dígitos)<br>
• CFOP<br>
• Quantidade<br>
• Valor unitário<br><br>
<strong>3. Campos tributários:</strong><br>
• Origem da mercadoria (geralmente 0)<br>
• CSOSN ou CST (conforme seu regime)<br>
• Alíquota ICMS (se aplicável)<br><br>
<strong>4. Clique em "Salvar Item"</strong><br><br>
💡 <strong>Dica:</strong> Você pode cadastrar produtos previamente no menu "Produtos" para não precisar preencher toda vez!"""
    
    # 💳 Pagamento
    if 'pagamento' in pergunta_lower or 'valor' in pergunta_lower and 'pagar' in pergunta_lower:
        return """✅ <strong>Como preencher dados de pagamento:</strong><br><br>
📋 <strong>Campos importantes:</strong><br><br>
<strong>1. Forma de Pagamento:</strong><br>
• Dinheiro<br>
• Cartão de Crédito<br>
• Cartão de Débito<br>
• PIX<br>
• Boleto<br>
• Transferência<br><br>
<strong>2. Valor do Pagamento:</strong><br>
⚡ <strong>Atualiza automaticamente!</strong><br>
Sistema soma produtos + frete - desconto<br><br>
<strong>3. Indicador de Pagamento:</strong><br>
• <strong>0</strong> - À vista<br>
• <strong>1</strong> - À prazo<br>
• <strong>2</strong> - Outros<br><br>
💡 <strong>O valor é calculado automaticamente!</strong><br>
Você só precisa escolher a forma de pagamento."""
    
    # 🚚 Transporte e Frete
    if 'frete' in pergunta_lower or 'transporte' in pergunta_lower:
        return """✅ <strong>Modalidade de Frete:</strong><br><br>
<strong>0 - Por conta do Emitente (CIF)</strong><br>
📦 VOCÊ paga o frete<br>
Valor do frete entra na NFe<br><br>
<strong>1 - Por conta do Destinatário (FOB)</strong><br>
📦 CLIENTE paga o frete<br>
Cliente paga frete direto à transportadora<br><br>
<strong>2 - Por conta de Terceiros</strong><br>
📦 Outra empresa paga<br><br>
<strong>9 - Sem Frete</strong><br>
📦 Não há transporte<br>
Ex: Retirada no local, venda digital<br><br>
📋 <strong>Como preencher:</strong><br>
1. Selecione modalidade<br>
2. Se houver valor de frete, preencha<br>
3. Dados da transportadora (opcional)<br><br>
💡 O valor do frete entra no total da NFe automaticamente!"""
    
    # ❓ Pergunta genérica
    return f"""🤖 <strong>Assistente EmiteMax</strong><br><br>
Desculpe, não encontrei uma resposta específica para sua pergunta.<br><br>
📌 <strong>Informações do seu contexto:</strong><br>
• Regime: <strong>{regime}</strong><br>
• UF: <strong>{uf}</strong><br>
• CRT: <strong>{crt}</strong><br><br>
💡 <strong>Tente perguntas como:</strong><br>
• "Como emitir venda dentro do estado?"<br>
• "Qual CFOP usar?"<br>
• "O que é CSOSN?"<br>
• "Como calcular ICMS?"<br>
• "Como preencher para consumidor final?"<br><br>
⚠️ Para dúvidas complexas, consulte seu contador!"""

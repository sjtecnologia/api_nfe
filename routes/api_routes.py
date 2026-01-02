from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, text
from database.connection import get_db
from database.models import (
    Cfop, Ncm, Produto, Cliente, CertificadoDigital, NFeEmitidas,
    RegimeTributario, RegraTributacao, Csosnicms, Csticms, OrigemMercadoria
)
from auth.permissions import get_accessible_client_ids

api_bp = Blueprint('api', __name__)

@api_bp.route('/cfops', methods=['GET'])
@login_required
def get_cfops():
    """Retorna lista de CFOPs"""
    db = next(get_db())
    cfops = db.query(Cfop).all()
    cfop_list = [{"cfop_id": c.cfop_id, "cfop": c.cfop, "descricao": c.descricao} for c in cfops]
    return jsonify(cfop_list), 200

@api_bp.route('/ncms', methods=['GET'])
@login_required
def get_ncms():
    """Retorna lista de NCMs"""
    db = next(get_db())
    ncms = db.query(Ncm).all()
    ncm_list = [{"ncm_id": n.ncm_id, "codigo": n.codigo, "descricao": n.descricao} for n in ncms]
    return jsonify(ncm_list), 200

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
        
        query = db.query(RegraTributacao).options(
        joinedload(RegraTributacao.regime_tributario),
        joinedload(RegraTributacao.cfop),
        joinedload(RegraTributacao.ncm),
        joinedload(RegraTributacao.cst_icms_obj),
        joinedload(RegraTributacao.csosn_icms_obj),
        joinedload(RegraTributacao.motivo_desoneracao)
        ).filter(RegraTributacao.ativo == True)
        
        # Filtros obrigatórios
        if cliente_id:
            query = query.filter(or_(RegraTributacao.cliente_id == cliente_id, RegraTributacao.cliente_id.is_(None)))
        else:
            query = query.filter(RegraTributacao.cliente_id.is_(None))
        
        if regime_tributario_id:
            query = query.filter(RegraTributacao.regime_tributario_id == regime_tributario_id)
        
        # Filtros condicionais
        if cfop_codigo:
            cfop_subquery = db.query(Cfop.cfop_id).filter(Cfop.cfop == cfop_codigo)
            cfop_ids = [c.cfop_id for c in cfop_subquery.all()]
            print(f"[SEARCH] CFOP '{cfop_codigo}' -> IDs encontrados: {cfop_ids}")
            query = query.filter(or_(RegraTributacao.cfop_id.in_(cfop_subquery), RegraTributacao.cfop_id.is_(None)))
        
        if ncm_codigo:
            ncm_subquery = db.query(Ncm.ncm_id).filter(Ncm.codigo == ncm_codigo)
            ncm_ids = [n.ncm_id for n in ncm_subquery.all()]
            print(f"[SEARCH] NCM '{ncm_codigo}' -> IDs encontrados: {ncm_ids}")
            query = query.filter(or_(RegraTributacao.ncm_id.in_(ncm_subquery), RegraTributacao.ncm_id.is_(None)))
            
        if uf_origem:
            query = query.filter(or_(RegraTributacao.uf_origem == uf_origem, RegraTributacao.uf_origem.is_(None)))
        if uf_destino:
            query = query.filter(or_(RegraTributacao.uf_destino == uf_destino, RegraTributacao.uf_destino.is_(None)))
        if tipo_item:
            # tipo_item já foi normalizado (capitalize) no início da função
            query = query.filter(or_(RegraTributacao.tipo_item == tipo_item, RegraTributacao.tipo_item.is_(None)))
        
        # Ordenar por prioridade
        query = query.order_by(
            RegraTributacao.cliente_id.desc(),
            RegraTributacao.prioridade.desc()
        )
        
        # Debug: contar quantas regras passaram nos filtros
        count_filtradas = query.count()
        print(f"[QUERY] Regras após filtros: {count_filtradas}")
        
        if count_filtradas == 0:
            print(f"[WARNING] ⚠️ Nenhuma regra passou nos filtros!")
            print(f"[HINT] Verifique se existe regra com:")
            print(f"   - Cliente ID: {cliente_id} (ou NULL para regra global)")
            print(f"   - Regime: {regime_tributario_id}")
            print(f"   - CFOP: {cfop_codigo} (ou NULL)")
            print(f"   - NCM: {ncm_codigo} (ou NULL)")
            print(f"   - UF Origem: {uf_origem} (ou NULL)")
            print(f"   - UF Destino: {uf_destino} (ou NULL)")
            print(f"   - Tipo: {tipo_item} (ou NULL)")
        
        regra_encontrada = query.first()
        if regra_encontrada:
            regra_dict = regra_encontrada.to_dict()
            print(f"[OK] Regra encontrada ID {regra_encontrada.regra_tributacao_id}:")
            print(f"   Descrição: {regra_dict.get('descricao_regra')}")
            print(f"   ICMS: {regra_dict.get('aliquota_icms')}% | CSOSN: {regra_dict.get('csosn_icms')} | CST: {regra_dict.get('cst_icms')}")
            print(f"   PIS: {regra_dict.get('aliquota_pis')}% | CST: {regra_dict.get('cst_pis')}")
            print(f"   COFINS: {regra_dict.get('aliquota_cofins')}% | CST: {regra_dict.get('cst_cofins')}")
            print(f"   IPI: {regra_dict.get('aliquota_ipi')}% | CST: {regra_dict.get('cst_ipi')}")
            
            # Normalizar campos None para valores padrão (evitar problemas no frontend)
            if regra_dict.get('descricao_regra') is None:
                regra_dict['descricao_regra'] = 'Regra tributária automática'
            if regra_dict.get('aliquota_icms') is None:
                regra_dict['aliquota_icms'] = 0.0
            if regra_dict.get('aliquota_pis') is None:
                regra_dict['aliquota_pis'] = 0.0
            if regra_dict.get('aliquota_cofins') is None:
                regra_dict['aliquota_cofins'] = 0.0
            if regra_dict.get('aliquota_ipi') is None:
                regra_dict['aliquota_ipi'] = 0.0
            # CST pode ser None quando não aplicável (não forçamos valor)
            
            return jsonify({'sucesso': True, 'regra': regra_dict}), 200
        else:
            print(f"[!] Nenhuma regra encontrada para:")
            print(f"   Cliente: {cliente_id}, Regime: {regime_tributario_id}")
            print(f"   NCM: {ncm_codigo}, CFOP: {cfop_codigo}")
            print(f"   UF Origem: {uf_origem}, UF Destino: {uf_destino}")
            print(f"   Tipo: {tipo_item}")
            
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
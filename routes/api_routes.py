from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
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
    db = next(get_db())
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Dados JSON não fornecidos."}), 400
    
    cliente_id = data.get('cliente_id')
    regime_tributario_id = data.get('regime_tributario_id')
    cfop_codigo = data.get('cfop_codigo')
    ncm_codigo = data.get('ncm_codigo')
    uf_origem = data.get('uf_origem')
    uf_destino = data.get('uf_destino')
    tipo_item = data.get('tipo_item')
    
    # Validar acesso ao cliente
    accessible_client_ids = get_accessible_client_ids(db)
    if cliente_id and int(cliente_id) not in accessible_client_ids:
        return jsonify({"error": "Acesso negado para este cliente."}), 403
    
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
        query = query.filter(RegraTributacao.cfop_id.in_(cfop_subquery))
    
    if ncm_codigo:
        ncm_subquery = db.query(Ncm.ncm_id).filter(Ncm.codigo == ncm_codigo)
        query = query.filter(RegraTributacao.ncm_id.in_(ncm_subquery))
        
    if uf_origem:
        query = query.filter(RegraTributacao.uf_origem == uf_origem)
    if uf_destino:
        query = query.filter(RegraTributacao.uf_destino == uf_destino)
    if tipo_item:
        query = query.filter(RegraTributacao.tipo_item == tipo_item)
    
    # Ordenar por prioridade
    query = query.order_by(
        RegraTributacao.cliente_id.desc(),
        RegraTributacao.prioridade.desc()
    )
    
    regra_encontrada = query.first()
    if regra_encontrada:
        regra_dict = regra_encontrada.to_dict()
        print(f"✅ Regra encontrada ID {regra_encontrada.regra_tributacao_id}:")
        print(f"   Descrição: {regra_dict.get('descricao_regra')}")
        print(f"   ICMS: {regra_dict.get('aliquota_icms')}% | CSOSN: {regra_dict.get('csosn_icms')} | CST: {regra_dict.get('cst_icms')}")
        print(f"   PIS: {regra_dict.get('aliquota_pis')}% | CST: {regra_dict.get('cst_pis')}")
        print(f"   COFINS: {regra_dict.get('aliquota_cofins')}% | CST: {regra_dict.get('cst_cofins')}")
        print(f"   IPI: {regra_dict.get('aliquota_ipi')}% | CST: {regra_dict.get('cst_ipi')}")
        
        return jsonify({'sucesso': True, 'regra': regra_dict}), 200
    else:
        print(f"⚠️ Nenhuma regra encontrada para:")
        print(f"   Cliente: {cliente_id}, Regime: {regime_tributario_id}")
        print(f"   NCM: {ncm_codigo}, CFOP: {cfop_codigo}")
        print(f"   UF Origem: {uf_origem}, UF Destino: {uf_destino}")
        print(f"   Tipo: {tipo_item}")
        
        return jsonify({"sucesso": False, "message": "Nenhuma regra de tributação encontrada para os critérios fornecidos."}), 404

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
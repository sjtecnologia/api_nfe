from auth.decorators import permission_required, admin_required
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from database.connection import get_db
from sqlalchemy import text
from sqlalchemy.engine import Result
from typing import Optional, Any


admin_bp = Blueprint('admin', __name__)

# ========== DASHBOARD ==========
@admin_bp.route('/')
@login_required  
def admin_home():
    """Dashboard administrativo"""
    db = None
    try:
        db = next(get_db())
        
        # Estatísticas gerais da plataforma
        stats = {}
        
        # Total de clientes
        clientes_result = db.execute(text("SELECT COUNT(*) as total FROM clientes WHERE ativo = true"))
        clientes_row = clientes_result.first()
        stats['total_clientes'] = clientes_row.total if clientes_row else 0
        
        # Total de NFes (todos os clientes)
        nfes_result = db.execute(text("SELECT COUNT(*) as total FROM nfe_emitidas"))
        nfes_row = nfes_result.first()
        stats['total_nfes'] = nfes_row.total if nfes_row else 0
        
        # NFes no ano atual
        nfes_ano_result = db.execute(text("""
            SELECT COUNT(*) as total FROM nfe_emitidas 
            WHERE EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE)
        """))
        nfes_ano_row = nfes_ano_result.first()
        stats['nfes_ano'] = nfes_ano_row.total if nfes_ano_row else 0
        
        # NFes no mês atual
        nfes_mes_result = db.execute(text("""
            SELECT COUNT(*) as total FROM nfe_emitidas 
            WHERE EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND EXTRACT(MONTH FROM data_criacao) = EXTRACT(MONTH FROM CURRENT_DATE)
        """))
        nfes_mes_row = nfes_mes_result.first()
        stats['nfes_mes'] = nfes_mes_row.total if nfes_mes_row else 0
        
        # Últimos clientes cadastrados
        ultimos_clientes = db.execute(text("""
            SELECT cliente_id, razao_social, nome_fantasia, cnpj, data_cadastro
            FROM clientes 
            WHERE ativo = true
            ORDER BY data_cadastro DESC 
            
        """))
        
        return render_template('admin/dashboard.html', 
                             stats=stats,
                             ultimos_clientes=[dict(row._mapping) for row in ultimos_clientes])
                             
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return render_template('admin/dashboard.html', 
                             stats={'total_clientes': 0, 'total_nfes': 0, 'nfes_ano': 0, 'nfes_mes': 0},
                             ultimos_clientes=[])
    finally:
        if db:
            db.close()

# ========== PRODUTOS ==========

@admin_bp.route('/produtos')
@login_required
@admin_required()
def list_produtos():
    """Listar produtos"""
    db = None
    cliente_id: int = int(request.args.get('cliente_id', 5))
    
    try:
        db = next(get_db())
        
        print(f"🔍 DEBUG list_produtos:")
        print(f"  • Cliente ID recebido: {cliente_id}")
        
        # Query dos produtos
        produtos_result = db.execute(text("""
            SELECT p.produto_id, p.codigo_interno, p.descricao, 
                   p.unidade_comercial, p.preco_unitario_padrao,
                   p.ativo, n.codigo as ncm_codigo
            FROM produtos p
            LEFT JOIN ncms n ON p.ncm_id = n.ncm_id
            WHERE p.cliente_id = :cliente_id
            ORDER BY p.descricao
        """), {"cliente_id": cliente_id})
        
        produtos = [dict(row._mapping) for row in produtos_result]
        
        # Buscar nome do cliente
        cliente_result = db.execute(text("""
            SELECT razao_social FROM clientes WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        
        cliente_data = cliente_result.first()
        cliente_nome = cliente_data.razao_social if cliente_data else f"Cliente {cliente_id}"
        
        return render_template('admin/produtos/list.html', 
                             produtos=produtos,
                             cliente_id=cliente_id,
                             cliente_nome=cliente_nome)
        
    except Exception as e:
        print(f"❌ Erro ao listar produtos: {e}")
        flash('Erro ao carregar produtos.', 'error')
        return render_template('admin/produtos/list.html', 
                             produtos=[], 
                             cliente_id=cliente_id,
                             cliente_nome=f"Cliente {cliente_id}")
    finally:
        if db:
            db.close()

# ✅ ROTA DE CRIAÇÃO TAMBÉM PRECISA SER CORRIGIDA
@admin_bp.route('/produtos/add')
@login_required
@admin_required()
def create_produto():
    """Formulário para criar novo produto"""
    db = None
    cliente_id: int = int(request.args.get('cliente_id', 5))
    
    try:
        db = next(get_db())
        
        print(f"🔍 DEBUG create_produto:")
        print(f"  • Cliente ID recebido: {cliente_id}")
        
        # ✅ BUSCAR TODOS OS DADOS PARA OS SELECTS
        # NCMs
        ncms_result = db.execute(text("""
            SELECT ncm_id, codigo, descricao 
            FROM ncms 
            ORDER BY codigo 
            
        """))
        ncms = [dict(row._mapping) for row in ncms_result]
        
        # CFOPs
        cfops_result = db.execute(text("""
            SELECT cfop_id, cfop as codigo, descricao 
            FROM cfops 
            ORDER BY 
                CASE 
                    WHEN cfop ~ '^[0-9]+$' THEN CAST(cfop AS INTEGER)
                    ELSE 9999
                END,
                cfop
        """))
        cfops = [dict(row._mapping) for row in cfops_result]
        
        # ✅ CSTs ICMS (CORRIGIDO)
        csts_result = db.execute(text("""
            SELECT cst_id, codigo, descricao 
            FROM cst_icms 
            ORDER BY codigo
        """))
        csts = [dict(row._mapping) for row in csts_result]
        
        # ✅ CSOSNs (CORRIGIDO)
        csosns_result = db.execute(text("""
            SELECT csosn_id, codigo, descricao 
            FROM csosn_icms 
            ORDER BY codigo
        """))
        csosns = [dict(row._mapping) for row in csosns_result]
        
        # Origens Mercadoria
        origens_result = db.execute(text("""
            SELECT codigo, descricao 
            FROM origens_mercadoria 
            ORDER BY codigo
        """))
        origens_mercadoria = [dict(row._mapping) for row in origens_result]
        
        print(f"📋 Dados carregados para formulário:")
        print(f"  • NCMs: {len(ncms)}")
        print(f"  • CFOPs: {len(cfops)}")
        print(f"  • CSTs ICMS: {len(csts)}")
        print(f"  • CSOSNs: {len(csosns)}")
        print(f"  • Origens: {len(origens_mercadoria)}")
        
        return render_template('admin/produtos/form.html',
                             ncms=ncms,
                             cfops=cfops,
                             csts=csts,      # ✅ Agora sendo passado
                             csosns=csosns,  # ✅ Agora sendo passado
                             origens_mercadoria=origens_mercadoria,
                             cliente_id=cliente_id)
        
    except Exception as e:
        print(f"❌ Erro ao carregar dados para criação: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar formulário.', 'error')
        return redirect(url_for('admin.list_produtos'))
    finally:
        if db:
            db.close()

@admin_bp.route('/produtos/<int:produto_id>/edit')
@login_required
@admin_required()
def edit_produto(produto_id: int):
    """Formulário para editar produto existente"""
    db = None
    
    try:
        db = next(get_db())
        
        print(f"🔍 DEBUG edit_produto:")
        print(f"  • Produto ID recebido: {produto_id}")
        
        # ✅ BUSCAR O PRODUTO COM TODOS OS DADOS
        produto_result = db.execute(text("""
            SELECT p.produto_id, p.codigo_interno, p.descricao, 
                   p.unidade_comercial, p.preco_unitario_padrao,
                   p.ncm_id, p.cest, p.origem_mercadoria, p.tipo_item, 
                   p.ativo, p.cliente_id, p.cfop_id, p.cst_id, p.csosn_id
            FROM produtos p
            WHERE p.produto_id = :produto_id
        """), {"produto_id": produto_id})
        
        produto_data = produto_result.first()
        
        if not produto_data:
            print(f"❌ Produto {produto_id} não encontrado!")
            flash('Produto não encontrado!', 'error')
            return redirect(url_for('admin.list_produtos'))
        
        produto = dict(produto_data._mapping)
        cliente_id = produto['cliente_id']
        
        print(f"✅ Produto encontrado: {produto['descricao']}")
        
        # ✅ CONVERTER ORIGEM PARA STRING PARA COMPATIBILIDADE COM TEMPLATE
        if produto['origem_mercadoria'] is not None:
            produto['origem_mercadoria'] = str(produto['origem_mercadoria'])
            print(f"🔧 Origem convertida para string: '{produto['origem_mercadoria']}'")
        
        print(f"🔍 DEBUG - Origem da Mercadoria no produto:")
        print(f"  • Valor no banco: '{produto['origem_mercadoria']}'")
        print(f"  • Tipo do valor: {type(produto['origem_mercadoria'])}")
        print(f"  • Repr do valor: {repr(produto['origem_mercadoria'])}")
        print(f"  • É None? {produto['origem_mercadoria'] is None}")
        print(f"  • É string vazia? {produto['origem_mercadoria'] == ''}")
        
        # ✅ BUSCAR NCMs
        ncms_result = db.execute(text("""
            SELECT ncm_id, codigo, descricao 
            FROM ncms 
            ORDER BY codigo 
        """))
        ncms = [dict(row._mapping) for row in ncms_result]
        
        # ✅ BUSCAR CFOPs
        cfops_result = db.execute(text("""
            SELECT cfop_id, cfop as codigo, descricao 
            FROM cfops 
            ORDER BY cfop
        """))
        cfops = [dict(row._mapping) for row in cfops_result]
        
        # ✅ BUSCAR CSTs ICMS (CORRIGIDO)
        csts_result = db.execute(text("""
            SELECT cst_id, codigo, descricao 
            FROM cst_icms 
            ORDER BY codigo
        """))
        csts = [dict(row._mapping) for row in csts_result]
        
        # ✅ BUSCAR CSOSNs (CORRIGIDO)
        csosns_result = db.execute(text("""
            SELECT csosn_id, codigo, descricao 
            FROM csosn_icms 
            ORDER BY codigo
        """))
        csosns = [dict(row._mapping) for row in csosns_result]
        
        # ✅ BUSCAR ORIGENS MERCADORIA
        origens_result = db.execute(text("""
            SELECT codigo, descricao 
            FROM origens_mercadoria 
            ORDER BY codigo
        """))
        origens_mercadoria = [dict(row._mapping) for row in origens_result]
        
        print(f"📋 Dados carregados para formulário:")
        print(f"  • NCMs: {len(ncms)}")
        print(f"  • CFOPs: {len(cfops)}")
        print(f"  • CSTs ICMS: {len(csts)}")
        print(f"  • CSOSNs: {len(csosns)}")
        print(f"  • Origens: {len(origens_mercadoria)}")
        
        # ✅ DEBUG ESPECÍFICO DAS ORIGENS DISPONÍVEIS
        print(f"🔍 Origens de Mercadoria disponíveis:")
        for i, origem in enumerate(origens_mercadoria):
            print(f"    • [{i}] Código: '{origem['codigo']}' (tipo: {type(origem['codigo'])}) - {origem['descricao']}")
            # Verificar se é igual ao valor do produto
            if produto['origem_mercadoria'] is not None:
                iguais_str = str(produto['origem_mercadoria']) == str(origem['codigo'])
                iguais_int = produto['origem_mercadoria'] == origem['codigo']  
                print(f"      → Igual ao produto (str)? {iguais_str}")
                print(f"      → Igual ao produto (valor)? {iguais_int}")
            if i >= 4:  # Mostrar apenas os primeiros 5
                break
        
        # ✅ DEBUG DOS CSTs E CSOSNs
        print(f"🔍 CSTs encontrados:")
        for cst in csts[:5]:  # Mostra apenas os primeiros 5
            print(f"    • ID: {cst['cst_id']}, Código: {cst['codigo']}, Descrição: {cst['descricao']}")
        
        print(f"🔍 CSOSNs encontrados:")
        for csosn in csosns[:5]:  # Mostra apenas os primeiros 5
            print(f"    • ID: {csosn['csosn_id']}, Código: {csosn['codigo']}, Descrição: {csosn['descricao']}")
        
        return render_template('admin/produtos/form.html',
                             produto=produto,
                             ncms=ncms,
                             cfops=cfops,
                             csts=csts,      # ✅ Agora sendo passado
                             csosns=csosns,  # ✅ Agora sendo passado
                             origens_mercadoria=origens_mercadoria,
                             cliente_id=cliente_id)
        
    except Exception as e:
        print(f"❌ Erro ao carregar produto para edição: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar produto.', 'error')
        return redirect(url_for('admin.list_produtos'))
    finally:
        if db:
            db.close()

# ✅ NOVA ROTA - SALVAR PRODUTO (POST)
@admin_bp.route('/produtos/add', methods=['POST'])
@login_required
@admin_required()
def store_produto():
    """Salvar novo produto"""
    db = None
    cliente_id: Optional[str] = None
    
    try:
        db = next(get_db())
        
        # Dados do formulário
        cliente_id = request.form.get('cliente_id')
        codigo_interno = request.form.get('codigo_interno')
        descricao = request.form.get('descricao')
        ncm_id = request.form.get('ncm_id')
        cest = request.form.get('cest')
        unidade_comercial = request.form.get('unidade_comercial')
        preco_unitario_padrao = request.form.get('preco_unitario_padrao') or '0'
        origem_mercadoria = request.form.get('origem_mercadoria')
        tipo_item = request.form.get('tipo_item')
        ativo = 'ativo' in request.form
        cfop_id = request.form.get('cfop_id')
        cst_id = request.form.get('cst_id')
        csosn_id = request.form.get('csosn_id')
        
        print(f"💾 CRIANDO NOVO PRODUTO:")
        print(f"  • Cliente ID: {cliente_id}")
        print(f"  • Descrição: {descricao}")
        print(f"  • NCM ID: {ncm_id}")
        print(f"  • CFOP ID: {cfop_id}")
        
        # Validação básica
        if not all([cliente_id, codigo_interno, descricao, ncm_id, origem_mercadoria, tipo_item, cfop_id]):
            flash('Preencha todos os campos obrigatórios', 'error')
            return redirect(url_for('admin.create_produto', cliente_id=cliente_id or 5))
        
        # Converter tipos com validação
        cliente_id_int = int(cliente_id) if cliente_id else 5
        ncm_id_int = int(ncm_id) if ncm_id else 0
        cfop_id_int = int(cfop_id) if cfop_id else 0
        origem_mercadoria_int = int(origem_mercadoria) if origem_mercadoria else 0
        preco_float = float(preco_unitario_padrao) if preco_unitario_padrao else 0.0
        cst_id_int = int(cst_id) if cst_id and cst_id.strip() else None
        csosn_id_int = int(csosn_id) if csosn_id and csosn_id.strip() else None
        
        # Inserir produto
        db.execute(text("""
            INSERT INTO produtos (
                cliente_id, codigo_interno, descricao, ncm_id, cest,
                unidade_comercial, preco_unitario_padrao, origem_mercadoria,
                tipo_item, ativo, created_by_user_id, cfop_id, cst_id, csosn_id
            ) VALUES (
                :cliente_id, :codigo_interno, :descricao, :ncm_id, :cest,
                :unidade_comercial, :preco_unitario_padrao, :origem_mercadoria,
                :tipo_item, :ativo, :user_id, :cfop_id, :cst_id, :csosn_id
            )
        """), {
            'cliente_id': cliente_id_int,
            'codigo_interno': codigo_interno,
            'descricao': descricao,
            'ncm_id': ncm_id_int,
            'cest': cest,
            'unidade_comercial': unidade_comercial,
            'preco_unitario_padrao': preco_float,
            'origem_mercadoria': origem_mercadoria_int,
            'tipo_item': tipo_item,
            'ativo': ativo,
            'user_id': current_user.id,
            'cfop_id': cfop_id_int,
            'cst_id': cst_id_int,
            'csosn_id': csosn_id_int
        })
        
        db.commit()
        flash('Produto criado com sucesso!', 'success')
        print(f"✅ Produto criado com sucesso!")
        
        return redirect(url_for('admin.list_produtos', cliente_id=cliente_id_int))
        
    except Exception as e:
        print(f"❌ Erro ao criar produto: {e}")
        import traceback
        traceback.print_exc()
        if db:
            db.rollback()
        flash('Erro ao criar produto.', 'error')
        return redirect(url_for('admin.create_produto', cliente_id=cliente_id or 5))
    finally:
        if db:
            db.close()

# ✅ NOVA ROTA - ATUALIZAR PRODUTO (POST)
@admin_bp.route('/produtos/<int:produto_id>/edit', methods=['POST'])
@login_required
@admin_required()
def update_produto(produto_id: int):
    """Atualizar produto existente"""
    db = None
    
    try:
        db = next(get_db())
        
        # Dados do formulário
        codigo_interno = request.form.get('codigo_interno')
        descricao = request.form.get('descricao')
        ncm_id = request.form.get('ncm_id')
        cest = request.form.get('cest')
        unidade_comercial = request.form.get('unidade_comercial')
        preco_unitario_padrao = request.form.get('preco_unitario_padrao') or '0'
        origem_mercadoria = request.form.get('origem_mercadoria')
        tipo_item = request.form.get('tipo_item')
        ativo = 'ativo' in request.form
        cfop_id = request.form.get('cfop_id')
        cst_id = request.form.get('cst_id')
        csosn_id = request.form.get('csosn_id')
        
        print(f"📝 ATUALIZANDO PRODUTO ID {produto_id}:")
        print(f"  • Descrição: {descricao}")
        
        # Converter tipos com validação
        ncm_id_int = int(ncm_id) if ncm_id else 0
        cfop_id_int = int(cfop_id) if cfop_id else 0
        origem_mercadoria_int = int(origem_mercadoria) if origem_mercadoria else 0
        preco_float = float(preco_unitario_padrao) if preco_unitario_padrao else 0.0
        cst_id_int = int(cst_id) if cst_id and cst_id.strip() else None
        csosn_id_int = int(csosn_id) if csosn_id and csosn_id.strip() else None
        
        # Atualizar produto
        result: Result[Any] = db.execute(text("""
            UPDATE produtos SET
                codigo_interno = :codigo_interno,
                descricao = :descricao,
                ncm_id = :ncm_id,
                cest = :cest,
                unidade_comercial = :unidade_comercial,
                preco_unitario_padrao = :preco_unitario_padrao,
                origem_mercadoria = :origem_mercadoria,
                tipo_item = :tipo_item,
                ativo = :ativo,
                cfop_id = :cfop_id,
                cst_id = :cst_id,
                csosn_id = :csosn_id
            WHERE produto_id = :produto_id
        """), {
            'produto_id': produto_id,
            'codigo_interno': codigo_interno,
            'descricao': descricao,
            'ncm_id': ncm_id_int,
            'cest': cest,
            'unidade_comercial': unidade_comercial,
            'preco_unitario_padrao': preco_float,
            'origem_mercadoria': origem_mercadoria_int,
            'tipo_item': tipo_item,
            'ativo': ativo,
            'cfop_id': cfop_id_int,
            'cst_id': cst_id_int,
            'csosn_id': csosn_id_int
        })
        
        # ✅ CORREÇÃO: Usar getattr ao invés de hasattr para evitar erro do Pylance
        rowcount = getattr(result, 'rowcount', None)
        if rowcount is not None and rowcount == 0:
            flash('Produto não encontrado!', 'error')
            return redirect(url_for('admin.list_produtos'))
        
        db.commit()
        flash('Produto atualizado com sucesso!', 'success')
        print(f"✅ Produto {produto_id} atualizado com sucesso!")
        
        # Buscar cliente_id para redirect
        cliente_result = db.execute(text("""
            SELECT cliente_id FROM produtos WHERE produto_id = :produto_id
        """), {"produto_id": produto_id})
        cliente_data = cliente_result.first()
        cliente_id = cliente_data.cliente_id if cliente_data else 5
        
        return redirect(url_for('admin.list_produtos', cliente_id=cliente_id))
        
    except Exception as e:
        print(f"❌ Erro ao atualizar produto: {e}")
        import traceback
        traceback.print_exc()
        if db:
            db.rollback()
        flash('Erro ao atualizar produto.', 'error')
        return redirect(url_for('admin.edit_produto', produto_id=produto_id))
    finally:
        if db:
            db.close()

@admin_bp.route('/produtos/alterar-status', methods=['POST'])
@login_required
@admin_required()
def alterar_status_produto():
    """Alterar status ativo/inativo do produto"""
    db = None
    
    try:
        db = next(get_db())
        
        produto_id = request.form.get('produto_id')
        ativo = request.form.get('ativo') == 'true'
        cliente_id = request.form.get('cliente_id')
        
        if not produto_id:
            return jsonify({'success': False, 'message': 'ID do produto não informado'}), 400
        
        # Atualizar status
        result: Result[Any] = db.execute(text("""
            UPDATE produtos 
            SET ativo = :ativo 
            WHERE produto_id = :produto_id
        """), {
            'produto_id': int(produto_id),
            'ativo': ativo
        })
        
        # ✅ CORREÇÃO: Usar getattr ao invés de hasattr para evitar erro do Pylance
        rowcount = getattr(result, 'rowcount', None)
        if rowcount is not None and rowcount == 0:
            return jsonify({'success': False, 'message': 'Produto não encontrado'}), 404
        
        db.commit()
        
        status_texto = "ativado" if ativo else "desativado"
        
        return jsonify({
            'success': True,
            'message': f'Produto {status_texto} com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro ao alterar status: {e}")
        if db:
            db.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500
    finally:
        if db:
            db.close()

@admin_bp.route('/destinatarios')
@login_required
@permission_required('destinatarios_nfe.read')
def list_destinatarios():
    connection = None
    try:
        cliente_id = request.args.get('cliente_id')
        
        if not cliente_id and not current_user.is_admin():
            cliente_id = session.get('current_client_id')
        
        if not cliente_id:
            flash('Cliente não especificado.', 'error')
            return redirect(url_for('home.home'))
        
        connection = next(get_db())
        
        # ✅ INCLUIR NOVOS CAMPOS NA CONSULTA
        query = text("""
            SELECT 
                d.destinatario_id,
                d.cpf_cnpj,
                d.nome_razao_social,
                d.tipo_pessoa,
                d.ie,
                d.email,
                d.telefone,
                d.logradouro,
                d.numero,
                d.complemento,
                d.bairro,
                d.cep,
                d.nome_municipio,
                d.codigo_municipio,
                d.uf,
                d.codigo_uf
            FROM destinatarios_nfe d
            WHERE d.cliente_id = :cliente_id
            ORDER BY d.nome_razao_social
        """)
        
        result = connection.execute(query, {'cliente_id': cliente_id})
        destinatarios = [dict(row._mapping) for row in result]
        
        print(f"✅ Destinatários encontrados: {len(destinatarios)}")
        
        # Buscar nome do cliente  
        cliente_result = connection.execute(text("""
            SELECT razao_social FROM clientes WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        
        cliente_data = cliente_result.first()
        cliente_nome = cliente_data.razao_social if cliente_data else f"Cliente {cliente_id}"
        
        return render_template('admin/destinatarios/list.html', 
                             destinatarios=destinatarios,
                             cliente_id=cliente_id,
                             cliente_nome=cliente_nome)
        
    except Exception as e:
        print(f"❌ Erro ao listar destinatários: {e}")
        flash(f'Erro ao carregar destinatários: {str(e)}', 'error')
        return render_template('admin/destinatarios/list.html', 
                             destinatarios=[],
                             cliente_id=cliente_id if 'cliente_id' in locals() else None,
                             cliente_nome=f"Cliente {cliente_id}" if 'cliente_id' in locals() else "Cliente")
    finally:
        if connection:
            connection.close()

# ✅ ADICIONAR A ROTA QUE ESTAVA FALTANDO
@admin_bp.route('/destinatarios/novo')
@login_required  
@permission_required('destinatarios_nfe.create')
def novo_destinatario():
    try:
        cliente_id = request.args.get('cliente_id')
        
        if not cliente_id and not current_user.is_admin():
            cliente_id = session.get('current_client_id')
        
        if not cliente_id:
            flash('Cliente não especificado.', 'error')
            return redirect(url_for('home.home'))
        
        print(f"✅ Abrindo formulário de novo destinatário para cliente {cliente_id}")
        
        return render_template('admin/destinatarios/form.html', 
                             destinatario=None,
                             cliente_id=cliente_id)
        
    except Exception as e:
        print(f"❌ Erro ao abrir formulário de destinatário: {e}")
        flash(f'Erro ao abrir formulário: {str(e)}', 'error')
        return redirect(url_for('admin.list_destinatarios', cliente_id=cliente_id))

# ...existing code...

@admin_bp.route('/destinatarios/salvar', methods=['POST'])
@login_required
@permission_required('destinatarios_nfe.create') 
def salvar_destinatario():
    connection = None
    try:
        cliente_id = request.form.get('cliente_id')
        destinatario_id = request.form.get('destinatario_id')
        
        print(f"💾 Salvando destinatário - Cliente: {cliente_id}, ID: {destinatario_id}")
        
        # ✅ MAPEAMENTO UF → CÓDIGO IBGE
        UF_CODES = {
            'AC': 12, 'AL': 17, 'AP': 16, 'AM': 13, 'BA': 29,
            'CE': 23, 'DF': 53, 'ES': 32, 'GO': 52, 'MA': 21,
            'MT': 51, 'MS': 50, 'MG': 31, 'PA': 15, 'PB': 25,
            'PR': 41, 'PE': 26, 'PI': 22, 'RJ': 33, 'RN': 24,
            'RS': 43, 'RO': 11, 'RR': 14, 'SC': 42, 'SP': 35,
            'SE': 28, 'TO': 27
        }
        
        # ✅ LIMPAR E VALIDAR DADOS ANTES DE SALVAR
        cpf_cnpj = request.form.get('cpf_cnpj', '').replace('.', '').replace('-', '').replace('/', '')
        cep = request.form.get('cep', '').replace('-', '')
        telefone = request.form.get('telefone', '').replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
        
        # ✅ OBTER UF E CÓDIGO UF
        uf = request.form.get('uf', 'SP')
        codigo_uf = UF_CODES.get(uf, 35)  # Default SP = 35
        
        # Validar tamanhos
        if len(cep) > 8:
            flash(f'CEP muito longo: {cep}. Máximo 8 caracteres.', 'error')
            return redirect(url_for('admin.novo_destinatario', cliente_id=cliente_id))
        
        if len(cpf_cnpj) > 14:
            flash(f'CPF/CNPJ muito longo: {cpf_cnpj}. Máximo 14 caracteres.', 'error')
            return redirect(url_for('admin.novo_destinatario', cliente_id=cliente_id))
        
        print(f"🔧 Dados limpos - CEP: '{cep}', CPF/CNPJ: '{cpf_cnpj}', UF: '{uf}', Código UF: {codigo_uf}")
        
        connection = next(get_db())
        
        if destinatario_id:
            # ✅ EDITAR - INCLUIR UF E CODIGO_UF
            query = text("""
                UPDATE destinatarios_nfe SET
                    cpf_cnpj = :cpf_cnpj,
                    nome_razao_social = :nome_razao_social,
                    tipo_pessoa = :tipo_pessoa,
                    ie = :ie,
                    ie_indicador_nfe = :ie_indicador_nfe,
                    email = :email,
                    telefone = :telefone,
                    logradouro = :logradouro,
                    numero = :numero,
                    complemento = :complemento,
                    bairro = :bairro,
                    cep = :cep,
                    codigo_municipio = :codigo_municipio,
                    nome_municipio = :nome_municipio,
                    uf = :uf,
                    codigo_uf = :codigo_uf
                WHERE destinatario_id = :destinatario_id AND cliente_id = :cliente_id
            """)
            
            connection.execute(query, {
                'cpf_cnpj': cpf_cnpj,
                'nome_razao_social': request.form.get('nome_razao_social'),
                'tipo_pessoa': request.form.get('tipo_pessoa', 'J'),
                'ie': request.form.get('ie'),
                'ie_indicador_nfe': request.form.get('ie_indicador_nfe', 'C'),
                'email': request.form.get('email'),
                'telefone': telefone,
                'logradouro': request.form.get('logradouro'),
                'numero': request.form.get('numero'),
                'complemento': request.form.get('complemento'),
                'bairro': request.form.get('bairro'),
                'cep': cep,
                'codigo_municipio': request.form.get('codigo_municipio'),
                'nome_municipio': request.form.get('nome_municipio'),
                'uf': uf,
                'codigo_uf': codigo_uf,
                'destinatario_id': destinatario_id,
                'cliente_id': cliente_id
            })
            
            flash('Destinatário atualizado com sucesso!', 'success')
        else:
            # ✅ CRIAR NOVO - INCLUIR UF E CODIGO_UF
            query = text("""
                INSERT INTO destinatarios_nfe (
                    cliente_id, cpf_cnpj, nome_razao_social, tipo_pessoa,
                    ie, ie_indicador_nfe, email, telefone,
                    logradouro, numero, complemento, bairro, cep,
                    codigo_municipio, nome_municipio, uf, codigo_uf
                ) VALUES (
                    :cliente_id, :cpf_cnpj, :nome_razao_social, :tipo_pessoa,
                    :ie, :ie_indicador_nfe, :email, :telefone,
                    :logradouro, :numero, :complemento, :bairro, :cep,
                    :codigo_municipio, :nome_municipio, :uf, :codigo_uf
                )
            """)
            
            connection.execute(query, {
                'cliente_id': cliente_id,
                'cpf_cnpj': cpf_cnpj,
                'nome_razao_social': request.form.get('nome_razao_social'),
                'tipo_pessoa': request.form.get('tipo_pessoa', 'J'),
                'ie': request.form.get('ie'),
                'ie_indicador_nfe': request.form.get('ie_indicador_nfe', 'C'),
                'email': request.form.get('email'),
                'telefone': telefone,
                'logradouro': request.form.get('logradouro'),
                'numero': request.form.get('numero'),
                'complemento': request.form.get('complemento'),
                'bairro': request.form.get('bairro'),
                'cep': cep,
                'codigo_municipio': request.form.get('codigo_municipio'),
                'nome_municipio': request.form.get('nome_municipio'),
                'uf': uf,
                'codigo_uf': codigo_uf
            })
            
            flash('Destinatário criado com sucesso!', 'success')
        
        connection.commit()
        return redirect(url_for('admin.list_destinatarios', cliente_id=cliente_id))
        
    except Exception as e:
        print(f"❌ Erro ao salvar destinatário: {e}")
        if connection:
            connection.rollback()
        flash(f'Erro ao salvar destinatário: {str(e)}', 'error')
        return redirect(url_for('admin.list_destinatarios', cliente_id=cliente_id))
    finally:
        if connection:
            connection.close()

# ✅ ATUALIZAR API BUSCAR CEP PARA INCLUIR CODIGO_UF
@admin_bp.route('/api/buscar-cep/<cep>')
@login_required
def buscar_cep(cep):
    """Busca informações do CEP na API dos Correios"""
    try:
        import requests
        
        # ✅ MAPEAMENTO UF → CÓDIGO IBGE (MESMO DO BACKEND)
        UF_CODES = {
            'AC': 12, 'AL': 17, 'AP': 16, 'AM': 13, 'BA': 29,
            'CE': 23, 'DF': 53, 'ES': 32, 'GO': 52, 'MA': 21,
            'MT': 51, 'MS': 50, 'MG': 31, 'PA': 15, 'PB': 25,
            'PR': 41, 'PE': 26, 'PI': 22, 'RJ': 33, 'RN': 24,
            'RS': 43, 'RO': 11, 'RR': 14, 'SC': 42, 'SP': 35,
            'SE': 28, 'TO': 27
        }
        
        # Limpar CEP
        cep_limpo = cep.replace('-', '').replace('.', '')
        
        if len(cep_limpo) != 8:
            return jsonify({'error': 'CEP deve ter 8 dígitos'}), 400
        
        # Buscar na API do ViaCEP
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'erro' in data:
                return jsonify({'error': 'CEP não encontrado'}), 404
            
            # Buscar código IBGE do município
            codigo_municipio = data.get('ibge', '')
            uf = data.get('uf', 'SP')
            codigo_uf = UF_CODES.get(uf, 35)
            
            return jsonify({
                'success': True,
                'logradouro': data.get('logradouro', ''),
                'bairro': data.get('bairro', ''),
                'nome_municipio': data.get('localidade', ''),
                'uf': uf,
                'codigo_uf': codigo_uf,
                'codigo_municipio': codigo_municipio,
                'cep': cep_limpo
            })
        else:
            return jsonify({'error': 'Erro ao consultar CEP'}), 500
            
    except Exception as e:
        print(f"❌ Erro ao buscar CEP {cep}: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# ...existing code...


@admin_bp.route('/destinatarios/<int:destinatario_id>/edit')
@login_required
@permission_required('destinatarios_nfe.update')
def edit_destinatario(destinatario_id):
    connection = None
    try:
        print(f"✏️ Editando destinatário ID: {destinatario_id}")
        
        connection = next(get_db())
        
        # ✅ INCLUIR NOVOS CAMPOS NA CONSULTA DE EDIÇÃO
        query = text("""
            SELECT d.*, c.razao_social as cliente_nome
            FROM destinatarios_nfe d
            JOIN clientes c ON d.cliente_id = c.cliente_id
            WHERE d.destinatario_id = :destinatario_id
        """)
        
        result = connection.execute(query, {'destinatario_id': destinatario_id})
        destinatario = result.first()
        
        if not destinatario:
            flash('Destinatário não encontrado!', 'error')
            return redirect(url_for('admin.list_destinatarios'))
        
        destinatario_dict = dict(destinatario._mapping)
        
        return render_template('admin/destinatarios/form.html', 
                             destinatario=destinatario_dict,
                             cliente_id=destinatario_dict['cliente_id'])
        
    except Exception as e:
        print(f"❌ Erro ao carregar destinatário: {e}")
        flash(f'Erro ao carregar destinatário: {str(e)}', 'error')
        return redirect(url_for('admin.list_destinatarios'))
    finally:
        if connection:
            connection.close()
# ========== CERTIFICADOS ==========
# ...existing code...

@admin_bp.route('/certificados')
@login_required
@permission_required('certificados_nfe.read')
def list_certificados():
    connection = None
    try:
        print(f"✅ Acesso admin autorizado para {current_user.username} com roles: {[r.nome for r in current_user.roles]}")
        
        cliente_id = request.args.get('cliente_id')
        
        if not cliente_id and not current_user.is_admin():
            cliente_id = session.get('current_client_id')
        
        if not cliente_id:
            flash('Cliente não especificado.', 'error')
            return redirect(url_for('home.home'))
        
        print(f"🔍 DEBUG list_certificados:")
        print(f"  • Cliente ID recebido: {cliente_id}")
        
        connection = next(get_db())
        
        # ✅ QUERY CORRETA COM CAMPOS REAIS
        query = text("""
            SELECT 
                c.certificado_digital_id,
                c.fingerprint,
                c.nome_arquivo_original,
                c.validade_inicio,
                c.validade_fim,
                c.ativo,
                c.data_upload,
                c.created_by_user_id
            FROM certificados_digitais c
            WHERE c.cliente_id = :cliente_id
            ORDER BY c.data_upload DESC NULLS LAST, c.certificado_digital_id DESC
        """)
        
        result = connection.execute(query, {'cliente_id': cliente_id})
        certificados = [dict(row._mapping) for row in result]
        
        print(f"✅ Certificados encontrados: {len(certificados)}")
        
        # Buscar nome do cliente
        cliente_result = connection.execute(text("""
            SELECT razao_social FROM clientes WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        
        cliente_data = cliente_result.first()
        cliente_nome = cliente_data.razao_social if cliente_data else f"Cliente {cliente_id}"
        
        return render_template('admin/certificados/list.html',
                             certificados=certificados,
                             cliente_id=cliente_id,
                             cliente_nome=cliente_nome)
        
    except Exception as e:
        print(f"❌ Erro ao listar certificados: {e}")
        flash(f'Erro ao carregar certificados: {str(e)}', 'error')
        try:
            return render_template('admin/certificados/list.html',
                                 certificados=[],
                                 cliente_id=cliente_id if 'cliente_id' in locals() else None,
                                 cliente_nome=f"Cliente {cliente_id}" if 'cliente_id' in locals() else "Cliente")
        except Exception as template_error:
            print(f"❌ Erro no template: {template_error}")
            return f"<h1>Certificados Digitais</h1><p>Erro: {str(e)}</p><a href='/admin/certificados/novo?cliente_id={cliente_id}'>Novo Certificado</a>"
    finally:
        if connection:
            connection.close()

@admin_bp.route('/certificados/novo')
@login_required
@permission_required('certificados_nfe.create')
def novo_certificado():
    try:
        cliente_id = request.args.get('cliente_id')
        
        if not cliente_id and not current_user.is_admin():
            cliente_id = session.get('current_client_id')
        
        if not cliente_id:
            flash('Cliente não especificado.', 'error')
            return redirect(url_for('home.home'))
        
        print(f"✅ Abrindo formulário de novo certificado para cliente {cliente_id}")
        
        return render_template('admin/certificados/form.html', 
                             certificado=None,
                             cliente_id=cliente_id)
        
    except Exception as e:
        print(f"❌ Erro ao abrir formulário de certificado: {e}")
        flash(f'Erro ao abrir formulário: {str(e)}', 'error')
        return redirect(url_for('admin.list_certificados', cliente_id=cliente_id))

@admin_bp.route('/certificados/salvar', methods=['POST'])
@login_required
@permission_required('certificados_nfe.create')
def salvar_certificado():
    connection = None
    try:
        cliente_id = request.form.get('cliente_id')
        
        print(f"💾 Salvando certificado para cliente: {cliente_id}")
        
        # Verificar se foi enviado arquivo
        if 'arquivo_certificado' not in request.files:
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(url_for('admin.novo_certificado', cliente_id=cliente_id))
        
        arquivo = request.files['arquivo_certificado']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(url_for('admin.novo_certificado', cliente_id=cliente_id))
        
        # Validar extensão
        if not arquivo.filename.lower().endswith(('.pfx', '.p12')):
            flash('Arquivo deve ser .pfx ou .p12', 'error')
            return redirect(url_for('admin.novo_certificado', cliente_id=cliente_id))
        
        # ✅ GERAR FINGERPRINT E VALIDAR CERTIFICADO
        import hashlib
        import base64
        from datetime import datetime
        
        # Ler conteúdo do arquivo
        conteudo_arquivo = arquivo.read()
        senha = request.form.get('senha_certificado', '')
        nome_arquivo = arquivo.filename
        
        # Gerar fingerprint (hash do conteúdo)
        fingerprint = hashlib.sha256(conteudo_arquivo).hexdigest()
        
        # Converter para base64 para armazenamento
        conteudo_base64 = base64.b64encode(conteudo_arquivo).decode('utf-8')
        
        # TODO: Aqui você pode adicionar validação do certificado
        # Para extrair validade_inicio e validade_fim usando cryptography
        validade_inicio = datetime.now()  # Placeholder
        validade_fim = datetime.now().replace(year=datetime.now().year + 1)  # Placeholder
        
        connection = next(get_db())
        
        # ✅ VERIFICAR SE JÁ EXISTE CERTIFICADO COM MESMO FINGERPRINT
        check_query = text("""
            SELECT certificado_digital_id FROM certificados_digitais 
            WHERE fingerprint = :fingerprint AND cliente_id = :cliente_id
        """)
        
        existing = connection.execute(check_query, {
            'fingerprint': fingerprint,
            'cliente_id': cliente_id
        }).first()
        
        if existing:
            flash('Este certificado já foi cadastrado para este cliente.', 'warning')
            return redirect(url_for('admin.list_certificados', cliente_id=cliente_id))
        
        # ✅ DESCOBRIR O ATRIBUTO CORRETO DO USER_ID
        user_id = None
        try:
            # Tentar várias possibilidades de atributos
            if hasattr(current_user, 'user_id'):
                user_id = current_user.user_id
            elif hasattr(current_user, 'id'):
                user_id = current_user.id
            elif hasattr(current_user, 'usuario_id'):
                user_id = current_user.usuario_id
            else:
                print(f"🔍 DEBUG: Atributos do current_user: {dir(current_user)}")
                user_id = 1  # Fallback para admin
        except Exception as e:
            print(f"❌ Erro ao obter user_id: {e}")
            user_id = 1  # Fallback
        
        print(f"🔍 DEBUG: user_id determinado: {user_id}")
        
        # ✅ INSERT COM CAMPOS CORRETOS
        query = text("""
            INSERT INTO certificados_digitais (
                cliente_id, 
                fingerprint, 
                conteudo_certificado, 
                senha_certificado, 
                validade_inicio, 
                validade_fim, 
                ativo, 
                data_upload, 
                nome_arquivo_original,
                created_by_user_id
            ) VALUES (
                :cliente_id, 
                :fingerprint, 
                :conteudo_certificado,
                :senha_certificado, 
                :validade_inicio, 
                :validade_fim, 
                :ativo, 
                NOW(), 
                :nome_arquivo_original,
                :created_by_user_id
            )
        """)
        
        connection.execute(query, {
            'cliente_id': cliente_id,
            'fingerprint': fingerprint,
            'conteudo_certificado': conteudo_base64,
            'senha_certificado': senha,
            'validade_inicio': validade_inicio,
            'validade_fim': validade_fim,
            'ativo': True,
            'nome_arquivo_original': nome_arquivo,
            'created_by_user_id': user_id
        })
        
        connection.commit()
        
        print(f"✅ Certificado salvo com fingerprint: {fingerprint[:16]}...")
        flash('Certificado enviado com sucesso!', 'success')
        return redirect(url_for('admin.list_certificados', cliente_id=cliente_id))
        
    except Exception as e:
        print(f"❌ Erro ao salvar certificado: {e}")
        import traceback
        traceback.print_exc()
        
        if connection:
            connection.rollback()
        flash(f'Erro ao salvar certificado: {str(e)}', 'error')
        return redirect(url_for('admin.list_certificados', cliente_id=cliente_id))
    finally:
        if connection:
            connection.close()

# ✅ ROTA PARA ATIVAR/DESATIVAR CERTIFICADO
@admin_bp.route('/certificados/<int:certificado_id>/toggle-status', methods=['POST'])
@login_required
@permission_required('certificados_nfe.update')
def toggle_certificado_status(certificado_id):
    connection = None
    try:
        cliente_id = request.form.get('cliente_id')
        
        connection = next(get_db())
        
        # Buscar certificado atual
        query = text("""
            SELECT ativo FROM certificados_digitais 
            WHERE certificado_digital_id = :certificado_id AND cliente_id = :cliente_id
        """)
        
        result = connection.execute(query, {
            'certificado_id': certificado_id,
            'cliente_id': cliente_id
        }).first()
        
        if not result:
            flash('Certificado não encontrado.', 'error')
            return redirect(url_for('admin.list_certificados', cliente_id=cliente_id))
        
        # Alternar status
        novo_status = not result.ativo
        
        update_query = text("""
            UPDATE certificados_digitais 
            SET ativo = :novo_status
            WHERE certificado_digital_id = :certificado_id AND cliente_id = :cliente_id
        """)
        
        connection.execute(update_query, {
            'novo_status': novo_status,
            'certificado_id': certificado_id,
            'cliente_id': cliente_id
        })
        
        connection.commit()
        
        status_text = "ativado" if novo_status else "desativado"
        flash(f'Certificado {status_text} com sucesso!', 'success')
        
        return redirect(url_for('admin.list_certificados', cliente_id=cliente_id))
        
    except Exception as e:
        print(f"❌ Erro ao alterar status do certificado: {e}")
        if connection:
            connection.rollback()
        flash(f'Erro ao alterar status: {str(e)}', 'error')
        return redirect(url_for('admin.list_certificados', cliente_id=cliente_id))
    finally:
        if connection:
            connection.close()

# ...existing code...

# ========== REGRAS DE TRIBUTAÇÃO ==========
@admin_bp.route('/regras-tributacao')
@login_required
@permission_required('regras_tributacao.read')
def list_regras_tributacao():
    connection = None
    try:
        print(f"✅ Acesso admin autorizado para {current_user.username} com roles: {[r.nome for r in current_user.roles]}")
        
        cliente_id = request.args.get('cliente_id')
        
        if not cliente_id and not current_user.is_admin():
            cliente_id = session.get('current_client_id')
        
        if not cliente_id:
            flash('Cliente não especificado.', 'error')
            return redirect(url_for('home.home'))
        
        print(f"🔍 DEBUG list_regras_tributacao:")
        print(f"  • Cliente ID recebido: {cliente_id}")
        
        connection = next(get_db())
        
        # ✅ QUERY CORRETA COM CAMPOS REAIS DA TABELA
        query = text("""
            SELECT 
                rt.regra_tributacao_id,
                rt.cliente_id,
                rt.regime_tributario_id,
                rt.cfop_id,
                rt.ncm_id,
                rt.uf_origem,
                rt.uf_destino,
                rt.tipo_item,
                rt.prioridade,
                rt.cst_icms,
                rt.csosn_icms,
                rt.aliquota_icms,
                rt.reducao_base_icms,
                rt.modalidade_bc_icms,
                rt.motivo_desoneracao_icms,
                rt.cst_pis,
                rt.aliquota_pis,
                c.cfop as cfop_codigo,
                c.descricao as cfop_descricao,
                n.codigo as ncm_codigo,
                n.descricao as ncm_descricao
            FROM regras_tributacao rt
            LEFT JOIN cfops c ON rt.cfop_id = c.cfop_id
            LEFT JOIN ncms n ON rt.ncm_id = n.ncm_id
            WHERE rt.cliente_id = :cliente_id
            ORDER BY rt.prioridade ASC, rt.regra_tributacao_id DESC
        """)
        
        result = connection.execute(query, {'cliente_id': cliente_id})
        regras = [dict(row._mapping) for row in result]
        
        print(f"✅ Regras de tributação encontradas: {len(regras)}")
        
        # 🔍 DEBUG: Imprimir primeira regra se existir
        if regras:
            print(f"📋 Primeira regra: {regras[0]}")
        
        # Buscar nome do cliente
        cliente_result = connection.execute(text("""
            SELECT razao_social FROM clientes WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        
        cliente_data = cliente_result.first()
        cliente_nome = cliente_data.razao_social if cliente_data else f"Cliente {cliente_id}"
        
        return render_template('admin/regras_tributacao/list.html',
                             regras=regras,
                             cliente_id=cliente_id,
                             cliente_nome=cliente_nome)
        
    except Exception as e:
        print(f"❌ Erro ao listar regras de tributação: {e}")
        import traceback
        traceback.print_exc()
        
        flash(f'Erro ao carregar regras de tributação: {str(e)}', 'error')
        try:
            return render_template('admin/regras_tributacao/list.html',
                                 regras=[],
                                 cliente_id=cliente_id if 'cliente_id' in locals() else None,
                                 cliente_nome=f"Cliente {cliente_id}" if 'cliente_id' in locals() else "Cliente")
        except Exception as template_error:
            print(f"❌ Erro no template: {template_error}")
            return f"""
            <h1>Regras de Tributação - Cliente {cliente_id if 'cliente_id' in locals() else 'N/A'}</h1>
            <p>Erro: {str(e)}</p>
            <a href='/admin/regras-tributacao/nova?cliente_id={cliente_id if 'cliente_id' in locals() else 5}' class='btn btn-primary'>Nova Regra</a>
            """
    finally:
        if connection:
            connection.close()

@admin_bp.route('/regras-tributacao/nova')
@login_required
@permission_required('regras_tributacao.create')
def nova_regra_tributacao():
    connection = None
    try:
        cliente_id = request.args.get('cliente_id')
        
        if not cliente_id and not current_user.is_admin():
            cliente_id = session.get('current_client_id')
        
        if not cliente_id:
            flash('Cliente não especificado.', 'error')
            return redirect(url_for('home.home'))
        
        print(f"✅ Abrindo formulário de nova regra de tributação para cliente {cliente_id}")
        
        connection = next(get_db())
        
        # ✅ CORREÇÃO: Query correta baseada na estrutura real
        cfops_result = connection.execute(text("""
            SELECT cfop_id, cfop, descricao FROM cfops ORDER BY cfop
        """))
        cfops = [dict(row._mapping) for row in cfops_result]
        
        # ✅ CORREÇÃO: Query para NCMs (assumindo estrutura similar)
        ncms_result = connection.execute(text("""
            SELECT ncm_id, codigo, descricao FROM ncms ORDER BY codigo 
        """))
        ncms = [dict(row._mapping) for row in ncms_result]
        
        return render_template('admin/regras_tributacao/form.html', 
                             regra=None,
                             cliente_id=cliente_id,
                             cfops=cfops,
                             ncms=ncms)
        
    except Exception as e:
        print(f"❌ Erro ao abrir formulário de regra de tributação: {e}")
        flash(f'Erro ao abrir formulário: {str(e)}', 'error')
        return redirect(url_for('admin.list_regras_tributacao', cliente_id=cliente_id))
    finally:
        if connection:
            connection.close()

@admin_bp.route('/regras-tributacao/editar/<int:regra_id>')
@login_required
@permission_required('regras_tributacao.update')
def editar_regra_tributacao(regra_id):
    connection = None
    try:
        connection = next(get_db())
        
        # Buscar regra existente
        regra_query = text("""
            SELECT * FROM regras_tributacao 
            WHERE regra_tributacao_id = :regra_id
        """)
        
        regra_result = connection.execute(regra_query, {'regra_id': regra_id})
        regra = regra_result.first()
        
        if not regra:
            flash('Regra de tributação não encontrada.', 'error')
            return redirect(url_for('admin.list_regras_tributacao'))
        
        regra_dict = dict(regra._mapping)
        cliente_id = regra_dict['cliente_id']
        
        print(f"✅ Editando regra de tributação {regra_id} para cliente {cliente_id}")
        
        # ✅ CORREÇÃO: Query correta para CFOPs
        cfops_result = connection.execute(text("""
            SELECT cfop_id, cfop, descricao FROM cfops ORDER BY cfop
        """))
        cfops = [dict(row._mapping) for row in cfops_result]
        
        # ✅ CORREÇÃO: Query correta para NCMs
        ncms_result = connection.execute(text("""
            SELECT ncm_id, codigo, descricao FROM ncms ORDER BY codigo
        """))
        ncms = [dict(row._mapping) for row in ncms_result]
        
        print(f"📋 CFOPs encontrados: {len(cfops)}")
        print(f"📋 NCMs encontrados: {len(ncms)}")
        
        return render_template('admin/regras_tributacao/form.html', 
                             regra=regra_dict,
                             cliente_id=cliente_id,
                             cfops=cfops,
                             ncms=ncms)
        
    except Exception as e:
        print(f"❌ Erro ao editar regra de tributação: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao carregar regra: {str(e)}', 'error')
        return redirect(url_for('admin.list_regras_tributacao'))
    finally:
        if connection:
            connection.close()

# Atualizar a rota salvar para suportar edição
@admin_bp.route('/regras-tributacao/salvar', methods=['POST'])
@login_required
@permission_required('regras_tributacao.create')
def salvar_regra_tributacao():
    connection = None
    try:
        cliente_id = request.form.get('cliente_id')
        regra_id = request.form.get('regra_tributacao_id')  # Para edição
        
        print(f"💾 Salvando regra de tributação para cliente: {cliente_id}, ID: {regra_id}")
        
        connection = next(get_db())
        
        # Converter valores vazios para None
        def safe_int(value):
            return int(value) if value and value.strip() else None
        
        def safe_float(value):
            return float(value) if value and value.strip() else None
        
        def safe_str(value):
            return value.strip() if value and value.strip() else None
        
        dados = {
            'cliente_id': cliente_id,
            'regime_tributario_id': safe_int(request.form.get('regime_tributario_id')) or 1,  # Default
            'cfop_id': safe_int(request.form.get('cfop_id')),
            'ncm_id': safe_int(request.form.get('ncm_id')),
            'uf_origem': safe_str(request.form.get('uf_origem')),
            'uf_destino': safe_str(request.form.get('uf_destino')),
            'tipo_item': safe_str(request.form.get('tipo_item')),
            'prioridade': safe_int(request.form.get('prioridade')) or 100,
            'cst_icms': safe_str(request.form.get('cst_icms')),
            'csosn_icms': safe_str(request.form.get('csosn_icms')),
            'aliquota_icms': safe_float(request.form.get('aliquota_icms')),
            'reducao_base_icms': safe_float(request.form.get('reducao_base_icms')),
            'modalidade_bc_icms': safe_int(request.form.get('modalidade_bc_icms')),
            'motivo_desoneracao_icms': safe_int(request.form.get('motivo_desoneracao_icms')),
            'cst_pis': safe_str(request.form.get('cst_pis')),
            'aliquota_pis': safe_float(request.form.get('aliquota_pis')),
            'aliquota_cofins': safe_float(request.form.get('aliquota_cofins'))
        }
        
        if regra_id:
            # UPDATE - Edição
            query = text("""
                UPDATE regras_tributacao SET
                    regime_tributario_id = :regime_tributario_id,
                    cfop_id = :cfop_id,
                    ncm_id = :ncm_id,
                    uf_origem = :uf_origem,
                    uf_destino = :uf_destino,
                    tipo_item = :tipo_item,
                    prioridade = :prioridade,
                    cst_icms = :cst_icms,
                    csosn_icms = :csosn_icms,
                    aliquota_icms = :aliquota_icms,
                    reducao_base_icms = :reducao_base_icms,
                    modalidade_bc_icms = :modalidade_bc_icms,
                    motivo_desoneracao_icms = :motivo_desoneracao_icms,
                    cst_pis = :cst_pis,
                    aliquota_pis = :aliquota_pis,
                    aliquota_cofins = :aliquota_cofins
                WHERE regra_tributacao_id = :regra_id
            """)
            dados['regra_id'] = regra_id
            flash('Regra de tributação atualizada com sucesso!', 'success')
        else:
            # INSERT - Nova regra
            query = text("""
                INSERT INTO regras_tributacao (
                    cliente_id,
                    regime_tributario_id,
                    cfop_id,
                    ncm_id,
                    uf_origem,
                    uf_destino,
                    tipo_item,
                    prioridade,
                    cst_icms,
                    csosn_icms,
                    aliquota_icms,
                    reducao_base_icms,
                    modalidade_bc_icms,
                    motivo_desoneracao_icms,
                    cst_pis,
                    aliquota_pis,
                    aliquota_cofins
                ) VALUES (
                    :cliente_id,
                    :regime_tributario_id,
                    :cfop_id,
                    :ncm_id,
                    :uf_origem,
                    :uf_destino,
                    :tipo_item,
                    :prioridade,
                    :cst_icms,
                    :csosn_icms,
                    :aliquota_icms,
                    :reducao_base_icms,
                    :modalidade_bc_icms,
                    :motivo_desoneracao_icms,
                    :cst_pis,
                    :aliquota_pis,
                    :aliquota_cofins
                )
            """)
            flash('Regra de tributação criada com sucesso!', 'success')
        
        connection.execute(query, dados)
        connection.commit()
        
        return redirect(url_for('admin.list_regras_tributacao', cliente_id=cliente_id))
        
    except Exception as e:
        print(f"❌ Erro ao salvar regra de tributação: {e}")
        import traceback
        traceback.print_exc()
        
        if connection:
            connection.rollback()
        flash(f'Erro ao salvar regra: {str(e)}', 'error')
        return redirect(url_for('admin.list_regras_tributacao', cliente_id=cliente_id))
    finally:
        if connection:
            connection.close()

# Adicionar ao admin_routes.py:
@admin_bp.route('/regras-tributacao/excluir/<int:regra_id>', methods=['POST'])
@login_required
@permission_required('regras_tributacao.delete')
def excluir_regra_tributacao(regra_id):
    connection = None
    try:
        cliente_id = request.form.get('cliente_id')
        connection = next(get_db())
        
        query = text("DELETE FROM regras_tributacao WHERE regra_tributacao_id = :regra_id")
        connection.execute(query, {'regra_id': regra_id})
        connection.commit()
        
        flash('Regra de tributação excluída com sucesso!', 'success')
        return redirect(url_for('admin.list_regras_tributacao', cliente_id=cliente_id))
        
    except Exception as e:
        if connection:
            connection.rollback()
        flash(f'Erro ao excluir regra: {str(e)}', 'error')
        return redirect(url_for('admin.list_regras_tributacao', cliente_id=cliente_id))
    finally:
        if connection:
            connection.close()

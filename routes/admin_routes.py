from typing import Optional, Dict, Any, List, Generator
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app

# Definição do Blueprint admin_bp
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
import os
import sys
import importlib
import json
from werkzeug.utils import secure_filename
import requests
from flask_login import login_required, current_user
from sqlalchemy import text
from sqlalchemy.engine import Result
from datetime import datetime
from pathlib import Path
import asyncio
from auth.decorators import admin_required  # Importar decorator de admin

# Definição do Blueprint admin_bp

# Defina o decorator permission_required (stub ou real)
try:
    from ..core.permissions import permission_required  # type: ignore
except Exception:
    def permission_required(permission):
        def decorator(f):
            return f
        return decorator

# Inicializa get_db na primeira chamada
from database.connection import get_db

# -------------------------------------------------------------------
# PRODUTOS (CADASTRO, EDIÇÃO, LISTAGEM)
# -------------------------------------------------------------------

@admin_bp.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('produtos.edit')
def editar_produto(produto_id):
    db = _get_db()
    try:
        # Initialize cliente_id at the beginning
        cliente_id = None
        
        if request.method == 'POST':
            # Atualiza produto
            data = {
                'produto_id': produto_id,
                'codigo_interno': request.form.get('codigo_interno'),
                'descricao': request.form.get('descricao'),
                'unidade_comercial': request.form.get('unidade_comercial','UN'),
                'preco_unitario_padrao': request.form.get('preco_unitario_padrao') or 0,
                'ncm_id': request.form.get('ncm_id'),
                'cfop_id': request.form.get('cfop_id'),
                'cest': request.form.get('cest'),
                'csosn_id': request.form.get('csosn_id'),
            }
            db.execute(text("""
                UPDATE produtos
                SET codigo_interno=:codigo_interno,
                    descricao=:descricao,
                    unidade_comercial=:unidade_comercial,
                    preco_unitario_padrao=:preco_unitario_padrao,
                    ncm_id=:ncm_id,
                    cfop_id=:cfop_id,
                    cest=:cest,
                    csosn_id=:csosn_id
                WHERE produto_id=:produto_id
            """), data)
            db.commit()
            flash('Produto atualizado', 'success')
            # Buscar cliente_id do produto atualizado
            row = db.execute(text("SELECT cliente_id FROM produtos WHERE produto_id = :pid"), {'pid': produto_id}).fetchone()
            cliente_id = row[0] if row else None
            if cliente_id:
                return redirect(url_for('admin.edit_cliente', cliente_id=cliente_id) + '#produtos')
            return redirect(url_for('admin.list_produtos'))
        else:
            # Exibe form de edição
            row = db.execute(text("SELECT * FROM produtos WHERE produto_id = :pid"), {'pid': produto_id}).fetchone()
            produto = dict(row._mapping) if row else None
            print(f"🔍 Produto encontrado: {produto is not None}")
            if produto:
                print(f"🔍 Produto ID: {produto.get('produto_id')}, Descrição: {produto.get('descricao')}")
                for key, value in produto.items():
                    print(f"🔍 {key}: {value}")
            if produto and 'cliente_id' in produto and produto['cliente_id']:
                cliente_id = produto['cliente_id']
            else:
                cliente_id = request.args.get('cliente_id') or session.get('active_cliente_id')
            try:
                cliente_id = int(cliente_id) if cliente_id is not None else None
            except (TypeError, ValueError):
                cliente_id = None
            print("🔍 Buscando NCMs...")
            ncm_list = db.execute(text("SELECT ncm_id, codigo, descricao FROM ncms ORDER BY codigo")).fetchall()
            print(f"🔍 NCMs encontrados: {len(ncm_list)}")
            
            print("🔍 Buscando CFOPs...")
            cfop_list = db.execute(text("SELECT cfop_id, cfop, descricao FROM cfops ORDER BY cfop")).fetchall()
            print(f"🔍 CFOPs encontrados: {len(cfop_list)}")
            
            print("🔍 Buscando CSTs...")
            cst_list = db.execute(text("SELECT cst_id, codigo, descricao FROM cst_icms ORDER BY codigo")).fetchall()
            print(f"🔍 CSTs encontrados: {len(cst_list)}")
            
            print("🔍 Buscando CSOSNs...")
            csosn_list = db.execute(text("SELECT csosn_id, codigo, descricao FROM csosn_icms ORDER BY codigo")).fetchall()
            print(f"🔍 CSOSNs encontrados: {len(csosn_list)}")
            
            print("🔍 Buscando Origens de Mercadoria...")
            origens_list = db.execute(text("SELECT origem_id, codigo, descricao FROM origens_mercadoria ORDER BY codigo")).fetchall()
            print(f"🔍 Origens encontradas: {len(origens_list)}")
            
            print("🔍 Tentando renderizar template...")
            try:
                return render_template(
                    'admin/produtos/form.html',
                    produto=produto,
                    cliente_id=cliente_id,
                    ncms=[dict(n._mapping) for n in ncm_list],
                    cfops=[dict(c._mapping) for c in cfop_list],
                    csts=[dict(c._mapping) for c in cst_list],
                    csosns=[dict(c._mapping) for c in csosn_list],
                    origens_mercadoria=[dict(o._mapping) for o in origens_list]
                )
            except Exception as template_error:
                print(f"❌ Erro ao renderizar template: {template_error}")
                raise template_error
    except Exception as e:
        db.rollback()
        print(f"❌ Erro na função editar_produto: {e}")
        print(f"❌ Tipo do erro: {type(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao editar produto: {e}', 'danger')
        return redirect(url_for('admin.list_produtos'))
    finally:
        db.close()

def _get_db():
    return next(get_db())

# Rota para upload de NCM CSV e envio para IA
@admin_bp.route('/ncms/upload-csv', methods=['GET', 'POST'])
@login_required
def upload_ncm_csv():
    if request.method == 'POST':
        file = request.files.get('file')
        filename = file.filename if file and hasattr(file, 'filename') else None
        if not file or not filename or not isinstance(filename, str) or not filename.lower().endswith('.csv'):
            flash('Selecione um arquivo CSV válido.', 'danger')
            return redirect(request.url)
        safe_filename = secure_filename(filename)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        os.makedirs(upload_folder, exist_ok=True)
        upload_path = os.path.join(upload_folder, safe_filename)
        file.save(upload_path)
        # Enviar para microserviço IA (ajuste a URL conforme necessário)
        ia_url = current_app.config.get('IA_NCM_UPLOAD_URL', 'http://localhost:8000/ncm/dados')
        try:
            with open(upload_path, 'rb') as f:
                response = requests.post(ia_url, files={'file': f}, timeout=60)
            if response.status_code == 200:
                flash('Arquivo enviado para IA com sucesso!', 'success')
            else:
                flash(f'Falha ao enviar para IA: {response.text}', 'danger')
        except Exception as e:
            flash(f'Erro ao enviar para IA: {e}', 'danger')
        return redirect(url_for('admin.list_ncms'))
    return render_template('admin/ncms/upload_csv.html')

# Defina o decorator permission_required (stub ou real)
try:
    from ..core.permissions import permission_required  # type: ignore
except Exception:
    def permission_required(permission):
        def decorator(f):
            return f
        return decorator

# Inicializa get_db na primeira chamada
from database.connection import get_db



## A duplicata da função edit_produto foi removida. Mantenha apenas uma definição correta no arquivo.


## As funções create_produto e edit_produto duplicadas foram removidas. Mantenha apenas uma definição de cada no arquivo, preferencialmente a versão mais recente e correta (com passagem de cliente_id para o template).

# Rota para editar NCM
@admin_bp.route('/ncms/editar/<int:ncm_id>', methods=['GET', 'POST'])
@login_required
# @permission_required('ncms.edit')  # Descomente se desejar controle de permissão
def edit_ncm(ncm_id):
    db = _get_db()
    try:
        if request.method == 'POST':
            codigo = request.form.get('codigo')
            descricao = request.form.get('descricao')
            # Adicione outros campos conforme necessário
            db.execute(text("""
                UPDATE ncms SET codigo = :codigo, descricao = :descricao WHERE ncm_id = :ncm_id
            """), {'codigo': codigo, 'descricao': descricao, 'ncm_id': ncm_id})
            db.commit()
            flash('NCM atualizado com sucesso!', 'success')
            return redirect(url_for('admin.list_ncms'))
        row = db.execute(text("SELECT ncm_id, codigo, descricao FROM ncms WHERE ncm_id = :id"), {'id': ncm_id}).fetchone()
        ncm = dict(row._mapping) if row else None
        return render_template('admin/ncms/form.html', ncm=ncm)
    except Exception as e:
        db.rollback()
        flash(f'Erro ao editar NCM: {e}', 'danger')
        return redirect(url_for('admin.list_ncms'))
    finally:
        db.close()




# Defina o decorator permission_required (stub ou real)
try:
    # Tente importar o real
    from ..core.permissions import permission_required  # type: ignore
except Exception:
    def permission_required(permission):
        def decorator(f):
            return f
        return decorator

# ...existing code...
@admin_bp.route('/produtos/<int:produto_id>/duplicar', methods=['POST'])
@login_required
@permission_required('produtos.create')
def duplicar_produto(produto_id: int):
    db = _get_db()
    try:
        # Buscar produto original
        row = db.execute(text("""
            SELECT cliente_id, codigo_interno, descricao, unidade_comercial, tipo_item, preco_unitario_padrao,
                   ncm_id, cfop_id, origem_mercadoria, cest, cst_id, csosn_id, ativo
            FROM produtos WHERE produto_id = :pid
        """), {'pid': produto_id}).fetchone()
        if not row:
            flash('Produto original não encontrado para duplicação.', 'error')
            return redirect(request.referrer or url_for('admin.list_produtos'))
        prod = dict(row._mapping)
        # Ajustar campos para novo produto
        prod['codigo_interno'] = (prod['codigo_interno'] or '') + '_COPIA'
        prod['descricao'] = (prod['descricao'] or '') + ' (Cópia)'
        prod['created_by_user_id'] = current_user.id
        # Insert novo produto
        result = db.execute(text("""
            INSERT INTO produtos (cliente_id, codigo_interno, descricao, unidade_comercial, tipo_item, preco_unitario_padrao,
                      ncm_id, cfop_id, origem_mercadoria, cest, cst_id, csosn_id, created_by_user_id, ativo)
            VALUES (:cliente_id, :codigo_interno, :descricao, :unidade_comercial, :tipo_item, :preco_unitario_padrao,
                :ncm_id, :cfop_id, :origem_mercadoria, :cest, :cst_id, :csosn_id, :created_by_user_id, :ativo)
            RETURNING produto_id
        """), prod)
        db.commit()
        row_result = result.fetchone()
        new_id = row_result[0] if row_result else None
        if new_id:
            flash('Produto duplicado com sucesso! Faça os ajustes necessários.', 'success')
            return redirect(url_for('admin.editar_produto', produto_id=new_id))
        else:
            flash('Erro ao duplicar produto: ID não retornado.', 'error')
            return redirect(request.referrer or url_for('admin.list_produtos'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao duplicar produto: {e}")
        flash('Erro ao duplicar produto', 'error')
        return redirect(request.referrer or url_for('admin.list_produtos'))
    finally:
        db.close()

# Importe o decorator permission_required
try:
    import sys
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parent.parent
    core_dir = BASE_DIR / "core"
    if str(BASE_DIR) not in sys.path:
        sys.path.append(str(BASE_DIR))
    if str(core_dir) not in sys.path:
        sys.path.append(str(core_dir))
    # Certifique-se que core/permissions.py existe e core tem __init__.py
    # Se o erro persistir, tente importar via caminho relativo:
    try:
        # Tente importar via caminho relativo se estiver dentro de um pacote
        try:
            from ..core.permissions import permission_required  # type: ignore
        except ImportError:
            # Fallback: tente importar absoluto se sys.path estiver correto
            try:
                from ..core.permissions import permission_required  # type: ignore
            except ImportError:
                # Defina um stub para evitar erro de importação (ajuste conforme sua implementação real)
                def permission_required(permission):
                    def decorator(f):
                        return f
                    return decorator
    except ImportError:
        try:
            from ..core.permissions import permission_required  # type: ignore
        except ImportError:
            # Defina um stub para evitar erro de importação (ajuste conforme sua implementação real)
            def permission_required(permission):
                def decorator(f):
                    return f
                return decorator
except ImportError:
    # Defina um stub para evitar erro de importação (ajuste conforme sua implementação real)
    def permission_required(permission):
        def decorator(f):
            return f
        return decorator

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

def _locate_get_db():
    """
    Tenta localizar função get_db em módulos comuns.
    Retorna a função (generator factory) ou lança RuntimeError.
    """
    candidate_modules = [
        'db',
        'database',
        'core.db',
        'core.database',
        'app.db',
        'app.database'
    ]
    
    # Primeiro tenta importar do diretório pai (raiz do projeto)
    try:
        sys.path.insert(0, str(BASE_DIR))
        root_db = importlib.import_module('core.db')
        if hasattr(root_db, 'get_db'):
            return root_db.get_db
    except ImportError as e:
        print(f"❌ Não conseguiu importar db do diretório raiz: {e}")
        pass
    
    # Tenta outros módulos candidatos
    for mod_name in candidate_modules:
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, 'get_db'):
                print(f"✅ Encontrou get_db em {mod_name}")
                return getattr(mod, 'get_db')
        except ImportError:
            continue
    
    # Tenta relative (caso pacote tenha __init__.py no root)
    try:
        from .. import db as rel_db  # type: ignore
        if hasattr(rel_db, 'get_db'):
            return rel_db.get_db
    except Exception:
        pass
    
    # Fallback engine em config
    def _fallback():
        engine = current_app.config.get('SQLALCHEMY_ENGINE')
        if engine is None:
            print("❌ SQLALCHEMY_ENGINE não encontrado em current_app.config")
            print("❌ Estrutura de diretórios:")
            print(f"   BASE_DIR: {BASE_DIR}")
            print(f"   sys.path inclui: {BASE_DIR in sys.path}")
            raise RuntimeError("get_db não encontrado. Ajuste caminhos ou verifique se módulo db.py existe.")
        conn = engine.connect()
        try:
            yield conn
        finally:
            conn.close()
    return _fallback


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def _safe_row_to_dict(row, columns: Optional[List[str]] = None) -> Dict[str, Any]:
    if not row:
        return {}
    if hasattr(row, '_mapping'):
        return dict(row._mapping)
    if hasattr(row, '_asdict'):
        return row._asdict()
    if columns:
        return {col: (row[i] if i < len(row) else None) for i, col in enumerate(columns)}
    try:
        return dict(row)
    except Exception:
        return {}

def resolve_cliente_id(param_name: str = 'cliente_id', required: bool = False) -> Optional[int]:
    cid = request.args.get(param_name) or request.form.get(param_name) or session.get('active_cliente_id')
    if cid is None:
        return None
    try:
        return int(cid)
    except (TypeError, ValueError):
        if required:
            raise
        return None

# Inicializa get_db na primeira chamada
from database.connection import get_db
# get_db = _locate_get_db()



# -------------------------------------------------------------------
# DASHBOARD ADMIN
# -------------------------------------------------------------------

@admin_bp.route('/')
@login_required
def admin_home():
    """Redireciona para o novo dashboard analytics"""
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/nfes')
@login_required
@permission_required('nfes.view')
def list_nfes():
    db = _get_db()
    q = request.args.get('q', '').strip()
    cliente_id = request.args.get('cliente_id')
    filtro = []
    params = {}
    from flask_login import current_user
    # Se não for super_admin, filtra por cliente_id ou pelos clientes acessíveis
    if not current_user.is_super_admin():
        accessible_ids = [c.get('cliente_id') for c in current_user.get_accessible_clients()] if hasattr(current_user, 'get_accessible_clients') else []
        if cliente_id:
            filtro.append("n.cliente_id = :cliente_id")
            params['cliente_id'] = int(cliente_id)
        elif accessible_ids:
            filtro.append("n.cliente_id IN :ids")
            params['ids'] = tuple(accessible_ids)
        else:
            filtro.append("1=0")  # Nenhum cliente acessível
    elif cliente_id:
        filtro.append("n.cliente_id = :cliente_id")
        params['cliente_id'] = int(cliente_id)
    # Filtro de busca
    if q:
        filtro.append("(" +
            "n.destinatario_razao_social ILIKE :q OR "
            "n.destinatario_cnpj_cpf ILIKE :q OR "
            "c.razao_social ILIKE :q OR "
            "c.cnpj ILIKE :q"
            ")")
        params['q'] = f'%{q}%'
    where_clause = ""
    if filtro:
        where_clause = "WHERE " + " AND ".join(filtro)
    rows = db.execute(text(f"""
        SELECT n.nfe_emitida_id, n.cliente_id, n.chave_acesso, n.data_criacao, n.status,
               n.destinatario_razao_social, n.destinatario_cnpj_cpf,
               n.tipo_nfe, n.finalidade_emissao,
               c.razao_social, c.cnpj
        FROM nfe_emitidas n
        JOIN clientes c ON c.cliente_id = n.cliente_id
        {where_clause}
        ORDER BY n.data_criacao DESC
        LIMIT 100
    """), params).fetchall()
    nfes = [dict(row._mapping) for row in rows]

    # Monta o cliente_map para o filtro e exibição
    clientes = db.execute(text("SELECT cliente_id, razao_social FROM clientes ORDER BY razao_social")).fetchall()
    cliente_map = {row.cliente_id: row.razao_social for row in clientes}

    return render_template(
        'admin/nfes/list.html',
        nfes=nfes,
        q=q,
        cliente_map=cliente_map,
        cliente_id=cliente_id
    )

def _calculate_ncm_hierarchy_level(codigo):
    """
    Calcula o nível hierárquico de um código NCM baseado na estrutura:
    - Capítulo (2 dígitos): 01, 02, etc. - Nível 0
    - Posição (4 dígitos): 0101, 0102, etc. - Nível 1  
    - Subposição (6 dígitos): 010101, 010102, etc. - Nível 2
    - Item (8 dígitos): 01010101, 01010102, etc. - Nível 3
    """
    if not codigo or not codigo.isdigit():
        return 0
    
    codigo_len = len(codigo)
    if codigo_len <= 2:
        return 0  # Capítulo
    elif codigo_len <= 4:
        return 1  # Posição
    elif codigo_len <= 6:
        return 2  # Subposição
    else:
        return 3  # Item (8 dígitos)

def _add_ncm_hierarchy_data(ncms):
    """
    Adiciona dados de hierarquia aos NCMs para exibição indentada
    """
    for ncm in ncms:
        codigo = ncm.get('codigo', '')
        ncm['hierarchy_level'] = _calculate_ncm_hierarchy_level(codigo)
        
        # Define tipo de elemento baseado no nível
        level_names = ['Capítulo', 'Posição', 'Subposição', 'Item']
        ncm['hierarchy_type'] = level_names[min(ncm['hierarchy_level'], 3)]
        
        # Calcula indentação (20px por nível)
        ncm['indent_px'] = ncm['hierarchy_level'] * 20
        
        # Formata código com pontos para melhor visualização
        if len(codigo) >= 8:
            ncm['codigo_formatado'] = f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}.{codigo[6:8]}"
        elif len(codigo) >= 6:
            ncm['codigo_formatado'] = f"{codigo[:2]}.{codigo[2:4]}.{codigo[4:6]}"
        elif len(codigo) >= 4:
            ncm['codigo_formatado'] = f"{codigo[:2]}.{codigo[2:4]}"
        else:
            ncm['codigo_formatado'] = codigo
    
    return ncms

@admin_bp.route('/ncms')
@login_required
def list_ncms():
    from services.ncm_service import ncm_service
    
    db = _get_db()
    q = request.args.get('q', '').strip()
    
    # Usa o serviço híbrido para busca
    if q:
        ncms = ncm_service.search_ncm_hybrid(q, limit=100)
        # Converte para formato esperado pelo template se necessário
        if ncms and not isinstance(ncms[0].get('ncm_id'), (int, type(None))):
            # Se vem da busca online, cria formato compatível
            ncms = [{'ncm_id': i+1, 'codigo': ncm.get('codigo', ''), 'descricao': ncm.get('descricao', ''), 
                    'data_atualizacao': ncm.get('data_atualizacao'), 'fonte_atualizacao': 'online'} 
                   for i, ncm in enumerate(ncms)]
    else:
        # Lista padrão do banco local com ordenação hierárquica
        rows = db.execute(text("""
            SELECT ncm_id, codigo, descricao, tipo, data_inicio, data_fim, tipo_ato, numero_ato, ano_ato,
                   data_atualizacao, fonte_atualizacao
            FROM ncms
            ORDER BY 
                SUBSTRING(codigo, 1, 2),  -- Capítulo
                SUBSTRING(codigo, 3, 2),  -- Posição  
                SUBSTRING(codigo, 5, 2),  -- Subposição
                SUBSTRING(codigo, 7, 2)   -- Item
        """)).fetchall()
        ncms = [dict(row._mapping) for row in rows]
    
    # Adiciona dados de hierarquia para exibição indentada
    ncms = _add_ncm_hierarchy_data(ncms)
    
    db.close()
    
    return render_template('admin/ncms/list.html', ncms=ncms)



@admin_bp.route('/ncms/upload-siscomex', methods=['GET', 'POST'])
@login_required
@permission_required('ncms.sync')
def upload_siscomex_json():
    """
    Upload manual de arquivo JSON baixado do Siscomex após resolver captcha
    """
    if request.method == 'POST':
        file = request.files.get('siscomex_file')
        
        if not file or not file.filename:
            flash('Por favor, selecione um arquivo JSON do Siscomex.', 'warning')
            return redirect(request.url)
        
        if not file.filename.lower().endswith(('.json', '.txt')):
            flash('Arquivo deve ser JSON baixado do Siscomex (.json ou .txt).', 'warning')
            return redirect(request.url)
        
        try:
            # Lê o conteúdo do arquivo
            content = file.read().decode('utf-8').strip()
            
            if not content:
                flash('Arquivo parece estar vazio.', 'warning')
                return redirect(request.url)
            
            # Verifica se é JSON válido básico
            if not (content.startswith('{') or content.startswith('[')):
                flash('Arquivo não parece ser um JSON válido. Deve começar com { ou [', 'warning')
                return redirect(request.url)
            
            # Processa o JSON do Siscomex
            from services.ncm_service import ncm_service
            result = ncm_service.process_siscomex_json(content)
            
            if result['success']:
                flash(f"✅ {result['message']}", 'success')
            else:
                flash(f"⚠️ {result['message']}", 'warning')
                
        except UnicodeDecodeError:
            flash('Erro de codificação do arquivo. Certifique-se que está em UTF-8.', 'error')
        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'error')
        
        return redirect(url_for('admin.list_ncms'))
    
    # GET - Mostra formulário de upload
    return render_template('admin/ncms/upload_siscomex.html')





# API para busca de NCM híbrida (para Select2)
@admin_bp.route('/api/ncms/search', methods=['GET'])
@login_required
def api_search_ncms():
    from services.ncm_service import ncm_service
    
    q = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 50)), 100)
    
    # Se não houver busca, retorna NCMs mais comuns
    if len(q) < 2:
        db = _get_db()
        try:
            # Retorna os 50 primeiros NCMs ordenados por código
            result = db.execute(text("""
                SELECT ncm_id, codigo, descricao 
                FROM ncms 
                WHERE tipo = 'analitico'
                ORDER BY codigo 
                LIMIT :limit
            """), {'limit': limit})
            
            results = []
            for row in result:
                results.append({
                    'id': row.ncm_id,
                    'text': f"{row.codigo} - {row.descricao}",
                    'codigo': row.codigo,
                    'descricao': row.descricao
                })
            
            return jsonify({'results': results})
        finally:
            db.close()
    
    try:
        ncms = ncm_service.search_ncm_hybrid(q, limit)
        
        # Formato para Select2
        results = []
        for ncm in ncms:
            results.append({
                'id': ncm.get('ncm_id', ''),
                'text': f"{ncm.get('codigo', '')} - {ncm.get('descricao', '')}",
                'codigo': ncm.get('codigo', ''),
                'descricao': ncm.get('descricao', '')
            })
        
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'results': [], 'error': str(e)})

# Rota para cadastro de novo NCM
@admin_bp.route('/ncms/novo', methods=['GET', 'POST'])
@login_required
# @permission_required('ncms.create')  # Descomente se desejar controle de permissão
def create_ncm():
    db = _get_db()
    try:
        if request.method == 'POST':
            codigo = request.form.get('codigo')
            descricao = request.form.get('descricao')
            # Adicione outros campos conforme necessário
            db.execute(text("""
                INSERT INTO ncms (codigo, descricao) VALUES (:codigo, :descricao)
            """), {'codigo': codigo, 'descricao': descricao})
            db.commit()
            flash('NCM cadastrado com sucesso!', 'success')
            return redirect(url_for('admin.list_ncms'))
        return render_template('admin/ncms/form.html', ncm=None)
    except Exception as e:
        db.rollback()
        flash(f'Erro ao cadastrar NCM: {e}', 'danger')
        return redirect(url_for('admin.list_ncms'))
    finally:
        db.close()

# Rota para excluir NCM
@admin_bp.route('/ncms/excluir/<int:ncm_id>', methods=['POST'])
@login_required
@permission_required('ncms.delete')
def delete_ncm(ncm_id):
    db = _get_db()
    try:
        # Verifica se o NCM está sendo usado por algum produto
        produtos_usando = db.execute(text("""
            SELECT COUNT(*) as total FROM produtos WHERE ncm_id = :ncm_id
        """), {'ncm_id': ncm_id}).fetchone()
        
        if produtos_usando and produtos_usando.total > 0:
            flash(f'Não é possível excluir este NCM pois está sendo usado por {produtos_usando.total} produto(s).', 'warning')
            return redirect(url_for('admin.list_ncms'))
        
        # Se não está sendo usado, pode excluir
        result: Result[Any] = db.execute(text("DELETE FROM ncms WHERE ncm_id = :ncm_id"), {'ncm_id': ncm_id})
        
        # Para SQLAlchemy, usamos result.rowcount para verificar quantas linhas foram afetadas
        rows_affected = getattr(result, 'rowcount', 0)
        
        if rows_affected > 0:
            db.commit()
            flash('NCM excluído com sucesso!', 'success')
        else:
            flash('NCM não encontrado.', 'warning')
            
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_ncm: {e}")
        flash(f'Erro ao excluir NCM: {str(e)}', 'error')
    finally:
        db.close()
    
    return redirect(url_for('admin.list_ncms'))

## Rotas de roles e permissions incompletas removidas para evitar erro de sintaxe.

@admin_bp.route('/cst')
@login_required
@permission_required('cst.view')
def list_cst():
    db = _get_db()
    try:
        q = request.args.get('q', '').strip()
        if q:
            rows = db.execute(text("""
                SELECT cst_id, codigo, descricao
                FROM cst_icms
                WHERE codigo ILIKE :q OR descricao ILIKE :q
                ORDER BY codigo
            """), {'q': f'%{q}%'}).fetchall()
        else:
            rows = db.execute(text("""
                SELECT cst_id, codigo, descricao
                FROM cst_icms
                ORDER BY codigo
            """)).fetchall()
        csts = [dict(row._mapping) for row in rows]
        return render_template('admin/cst/list.html', csts=csts)
    except Exception as e:
        print(f"❌ Erro list_cst: {e}")
        flash('Erro ao carregar CSTs', 'error')
        return render_template('admin/cst/list.html', csts=[])
    finally:
        db.close()

@admin_bp.route('/cst/novo')
@login_required
@permission_required('cst.create')
def create_cst():
    return render_template('admin/cst/form.html', cst=None)

@admin_bp.route('/cst/editar/<int:cst_id>', methods=['GET', 'POST'])
@login_required
@permission_required('cst.edit')
def edit_cst(cst_id):
    db = _get_db()
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        try:
            db.execute(text("""
                UPDATE cst_icms SET
                    codigo = :codigo,
                    descricao = :descricao
                WHERE cst_id = :cst_id
            """), {
                'codigo': codigo,
                'descricao': descricao,
                'cst_id': cst_id
            })
            db.commit()
            flash('CST atualizado com sucesso!', 'success')
            return redirect(url_for('admin.list_cst'))
        except Exception as e:
            db.rollback()
            flash('Erro ao atualizar CST', 'danger')
    row = db.execute(text("SELECT cst_id, codigo, descricao FROM cst_icms WHERE cst_id = :id"), {'id': cst_id}).fetchone()
    cst = dict(row._mapping) if row else None
    return render_template('admin/cst/form.html', cst=cst)

@admin_bp.route('/cst/excluir/<int:cst_id>', methods=['POST'])
@login_required
@permission_required('cst.delete')
def delete_cst(cst_id):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM cst_icms WHERE cst_id = :id"), {'id': cst_id})
        db.commit()
        flash('CST excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_cst: {e}")
        flash('Erro ao excluir CST', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_cst'))

@admin_bp.route('/cst/pis-cofins')
@login_required
def list_cst_pis_cofins():
    """
    Caso o template venha a referenciar admin.list_cst_pis_cofins no futuro.
    """
    flash('Lista de CST PIS/COFINS (stub).', 'info')
    return redirect(url_for('admin.admin_home'))


@admin_bp.route('/cfops')
@login_required
def list_cfops():
    db = _get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(text("""
            SELECT cfop_id, cfop, descricao, observacao, tipooperacao, identificadordestinooperacao
            FROM cfops
            WHERE cfop::text ILIKE :q
               OR descricao ILIKE :q
               OR observacao ILIKE :q
               OR tipooperacao ILIKE :q
               OR identificadordestinooperacao ILIKE :q
            ORDER BY cfop
        """), {'q': f'%{q}%'}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT cfop_id, cfop, descricao, observacao, tipooperacao, identificadordestinooperacao
            FROM cfops
            ORDER BY cfop
        """)).fetchall()
    cfops = [dict(row._mapping) for row in rows]
    return render_template('admin/cfops/list.html', cfops=cfops)

@admin_bp.route('/cfops/novo')
@login_required
def create_cfop():
    return render_template('admin/cfops/form.html', cfop=None)

@admin_bp.route('/cfops/salvar', methods=['POST'])
@login_required
def save_cfop():
    db = _get_db()
    try:
        data = {
            'cfop': request.form.get('cfop'),
            'descricao': request.form.get('descricao'),
            'observacao': request.form.get('observacao'),
            'tipooperacao': request.form.get('tipooperacao'),
            'identificadordestinooperacao': request.form.get('identificadordestinooperacao')
        }
        
        cfop_id = request.form.get('cfop_id')
        if cfop_id:  # Editar
            data['cfop_id'] = cfop_id
            db.execute(text("""
                UPDATE cfops SET cfop=:cfop, descricao=:descricao, observacao=:observacao,
                tipooperacao=:tipooperacao, identificadordestinooperacao=:identificadordestinooperacao
                WHERE cfop_id=:cfop_id
            """), data)
            flash('CFOP atualizado', 'success')
        else:  # Criar
            db.execute(text("""
                INSERT INTO cfops (cfop, descricao, observacao, tipooperacao, identificadordestinooperacao)
                VALUES (:cfop, :descricao, :observacao, :tipooperacao, :identificadordestinooperacao)
            """), data)
            flash('CFOP criado', 'success')
        
        db.commit()
        return redirect(url_for('admin.list_cfops'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro save_cfop: {e}")
        flash('Erro ao salvar CFOP', 'error')
        return redirect(url_for('admin.list_cfops'))
    finally:
        db.close()

@admin_bp.route('/cfops/editar/<int:cfop_id>')
@login_required
def edit_cfop(cfop_id):
    db = _get_db()
    try:
        row = db.execute(text("SELECT * FROM cfops WHERE cfop_id = :id"), {'id': cfop_id}).fetchone()
        if not row:
            flash('CFOP não encontrado', 'error')
            return redirect(url_for('admin.list_cfops'))
        
        cfop = _safe_row_to_dict(row, [
            'cfop_id','cfop','descricao','observacao','tipooperacao','identificadordestinooperacao'
        ])
        return render_template('admin/cfops/form.html', cfop=cfop)
    except Exception as e:
        print(f"❌ Erro edit_cfop: {e}")
        flash('Erro ao carregar CFOP', 'error')
        return redirect(url_for('admin.list_cfops'))
    finally:
        db.close()

@admin_bp.route('/cfops/excluir/<int:cfop_id>', methods=['POST'])
@login_required
def delete_cfop(cfop_id):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM cfops WHERE cfop_id = :id"), {'id': cfop_id})
        db.commit()
        flash('CFOP excluído', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_cfop: {e}")
        flash('Erro ao excluir CFOP', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_cfops'))

@admin_bp.route('/usuarios')
@login_required
@permission_required('usuarios.view')
def list_usuarios():
    db = _get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(text("""
            SELECT id, username, email, _is_active, created_at
            FROM users
            WHERE username ILIKE :q OR email ILIKE :q
            ORDER BY username
        """), {'q': f'%{q}%'}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT id, username, email, _is_active, created_at
            FROM users
            ORDER BY username
        """)).fetchall()
    usuarios = []
    for row in rows:
        usuario = dict(row._mapping)
        # Buscar roles do usuário
        roles_data = db.execute(text("""
            SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = :user_id
        """), {'user_id': usuario['id']}).fetchall()
        usuario['roles'] = [{'name': r.name} for r in roles_data]
        usuarios.append(usuario)
    return render_template('admin/usuarios/list.html', usuarios=usuarios)

from werkzeug.security import generate_password_hash

@admin_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
@permission_required('usuarios.create')
def create_usuario():
    db = _get_db()
    roles = db.execute(text("SELECT id, name FROM roles ORDER BY name")).fetchall()
    clientes = db.execute(text("SELECT cliente_id, razao_social FROM clientes ORDER BY razao_social")).fetchall()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password_hash')
        is_active = request.form.get('is_active') == 'on'
        selected_roles = request.form.getlist('roles')
        selected_clientes = request.form.getlist('clientes')
        try:
            password_hash = generate_password_hash(password) if password else None
            result = db.execute(text("""
                INSERT INTO users (username, email, password_hash, _is_active)
                VALUES (:username, :email, :password_hash, :is_active)
                RETURNING id
            """), {
                'username': username,
                'email': email,
                'password_hash': password_hash,
                'is_active': is_active
            })
            user_id = result.scalar()
            for role_id in selected_roles:
                db.execute(text("""
                    INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)
                """), {'user_id': user_id, 'role_id': role_id})
            for cliente_id in selected_clientes:
                db.execute(text("""
                    INSERT INTO user_clients (user_id, client_id) VALUES (:user_id, :cliente_id)
                """), {'user_id': user_id, 'cliente_id': cliente_id})
            db.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('admin.list_usuarios'))
        except Exception as e:
            db.rollback()
            if 'duplicate key value violates unique constraint' in str(e):
                flash('Já existe um usuário com esse nome ou email.', 'warning')
            else:
                flash('Erro ao cadastrar usuário.', 'danger')
    return render_template('admin/usuarios/form.html', usuario=None, roles=roles, clientes=clientes)

@admin_bp.route('/usuarios/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
@permission_required('usuarios.edit')
def edit_usuario(usuario_id):
    db = _get_db()
    roles = db.execute(text("SELECT id, name FROM roles ORDER BY name")).fetchall()
    clientes = db.execute(text("SELECT cliente_id, razao_social FROM clientes ORDER BY razao_social")).fetchall()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password_hash')
        is_active = request.form.get('is_active') == 'on'
        selected_roles = request.form.getlist('roles')
        selected_clientes = request.form.getlist('clientes')
        try:
            if password:
                password_hash = generate_password_hash(password)
                db.execute(text("""
                    UPDATE users SET
                        username = :username,
                        email = :email,
                        password_hash = :password_hash,
                        _is_active = :is_active
                    WHERE id = :usuario_id
                """), {
                    'username': username,
                    'email': email,
                    'password_hash': password_hash,
                    'is_active': is_active,
                    'usuario_id': usuario_id
                })
            else:
                db.execute(text("""
                    UPDATE users SET
                        username = :username,
                        email = :email,
                        _is_active = :is_active
                    WHERE id = :usuario_id
                """), {
                    'username': username,
                    'email': email,
                    'is_active': is_active,
                    'usuario_id': usuario_id
                })
            db.execute(text("DELETE FROM user_roles WHERE user_id = :user_id"), {'user_id': usuario_id})
            for role_id in selected_roles:
                db.execute(text("""
                    INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)
                """), {'user_id': usuario_id, 'role_id': role_id})
            db.execute(text("DELETE FROM user_clients WHERE user_id = :user_id"), {'user_id': usuario_id})
            for cliente_id in selected_clientes:
                db.execute(text("""
                    INSERT INTO user_clients (user_id, client_id) VALUES (:user_id, :cliente_id)
                """), {'user_id': usuario_id, 'cliente_id': cliente_id})
            db.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin.list_usuarios'))
        except Exception as e:
            db.rollback()
            if 'duplicate key value violates unique constraint' in str(e):
                flash('Já existe um usuário com esse nome ou email.', 'warning')
            else:
                flash('Erro ao atualizar usuário.', 'danger')
    row = db.execute(text("SELECT id, username, email, password_hash, _is_active FROM users WHERE id = :id"), {'id': usuario_id}).fetchone()
    usuario = dict(row._mapping) if row else {}
    usuario_roles = [r[0] for r in db.execute(text("SELECT role_id FROM user_roles WHERE user_id = :id"), {'id': usuario_id}).fetchall()]
    usuario_clientes = [c[0] for c in db.execute(text("SELECT client_id FROM user_clients WHERE user_id = :id"), {'id': usuario_id}).fetchall()]
    usuario['roles'] = usuario_roles
    usuario['clientes'] = usuario_clientes
    return render_template('admin/usuarios/form.html', usuario=usuario, roles=roles, clientes=clientes)

@admin_bp.route('/usuarios/excluir/<int:usuario_id>', methods=['POST'])
@login_required
@permission_required('usuarios.delete')
def delete_usuario(usuario_id):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM users WHERE id = :id"), {'id': usuario_id})
        db.commit()
        flash('Usuário excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_usuario: {e}")
        flash('Erro ao excluir usuário', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_usuarios'))

@admin_bp.route('/clientes/<int:cliente_id>/visualizar')
@login_required
@permission_required('clientes.view')
def visualizar_cliente(cliente_id: int):
    db = _get_db()
    try:
        row = db.execute(text("""
            SELECT cliente_id, razao_social, nome_fantasia, cnpj, inscricao_estadual, inscricao_municipal,
                   regime_tributario_id, cnae, cep, logradouro, numero, complemento, bairro,
                   nome_municipio, codigo_municipio, uf, email_contato, telefone_contato, ativo, data_cadastro
            FROM clientes
            WHERE cliente_id = :cid
        """), {'cid': cliente_id}).fetchone()
        cliente = dict(row._mapping) if row else None

        # Busca regime tributário
        regime = None
        if cliente and cliente.get('regime_tributario_id'):
            regime_row = db.execute(text("""
                SELECT nome FROM regimes_tributarios WHERE regime_tributario_id = :rid
            """), {'rid': cliente['regime_tributario_id']}).fetchone()
            regime = regime_row[0] if regime_row else None

        # Busca produtos do cliente
        produtos = db.execute(text("""
            SELECT produto_id, descricao, codigo_interno, ativo
            FROM produtos
            WHERE cliente_id = :cid
            ORDER BY descricao
        """), {'cid': cliente_id}).fetchall()
        produtos = [dict(p._mapping) for p in produtos]

        # Busca destinatários do cliente
        destinatarios = db.execute(text("""
            SELECT destinatario_id, nome_razao_social, cpf_cnpj, email
            FROM destinatarios_nfe
            WHERE cliente_id = :cid
            ORDER BY nome_razao_social
        """), {'cid': cliente_id}).fetchall()
        destinatarios = [dict(d._mapping) for d in destinatarios]

        return render_template(
            'admin/clientes/detalhes.html',
            cliente=cliente,
            regime=regime,
            produtos=produtos,
            destinatarios=destinatarios
        )
    except Exception as e:
        print(f"❌ Erro visualizar_cliente: {e}")
        flash('Erro ao carregar detalhes do cliente', 'error')
        return redirect(url_for('admin.list_clientes'))
    finally:
        db.close()

@admin_bp.route('/csosn')
@login_required
@permission_required('csosn.view')
def list_csosn():
    db = _get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(text("""
            SELECT csosn_id, codigo, descricao
            FROM csosn_icms
            WHERE codigo ILIKE :q
               OR descricao ILIKE :q
            ORDER BY codigo
        """), {'q': f'%{q}%'}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT csosn_id, codigo, descricao
            FROM csosn_icms
            ORDER BY codigo
        """)).fetchall()
    csosns = [dict(row._mapping) for row in rows]
    return render_template('admin/csosn/list.html', csosns=csosns)

@admin_bp.route('/csosn/novo')
@login_required
@permission_required('csosn.create')
def create_csosn():
    return render_template('admin/csosn/form.html', csosn=None)

@admin_bp.route('/csosn/editar/<int:csosn_id>', methods=['GET', 'POST'])
@login_required
@permission_required('csosn.edit')
def edit_csosn(csosn_id):
    db = _get_db()
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        try:
            db.execute(text("""
                UPDATE csosn_icms SET
                    codigo = :codigo,
                    descricao = :descricao
                WHERE csosn_id = :csosn_id
            """), {
                'codigo': codigo,
                'descricao': descricao,
                'csosn_id': csosn_id
            })
            db.commit()
            flash('CSOSN atualizado com sucesso!', 'success')
            return redirect(url_for('admin.list_csosn'))
        except Exception as e:
            db.rollback()
            flash('Erro ao atualizar CSOSN', 'danger')
    row = db.execute(text("SELECT csosn_id, codigo, descricao FROM csosn_icms WHERE csosn_id = :id"), {'id': csosn_id}).fetchone()
    csosn = dict(row._mapping) if row else None
    return render_template('admin/csosn/form.html', csosn=csosn)

@admin_bp.route('/csosn/excluir/<int:csosn_id>', methods=['POST'])
@login_required
@permission_required('csosn.delete')
def delete_csosn(csosn_id):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM csosn_icms WHERE csosn_id = :id"), {'id': csosn_id})
        db.commit()
        flash('CSOSN excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_csosn: {e}")
        flash('Erro ao excluir CSOSN', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_csosn'))


@admin_bp.route('/regimes-tributarios')
@login_required
@permission_required('regimes_tributarios.view')
def list_regimes_tributarios():
    """Lista regimes tributários"""
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT regime_tributario_id, nome, descricao
            FROM regimes_tributarios
            ORDER BY nome
        """)).fetchall()
        regimes = [_safe_row_to_dict(r, [
            'regime_tributario_id','nome','descricao'
        ]) for r in rows]
        return render_template('admin/regimes_tributarios/list.html', regimes=regimes)
    except Exception as e:
        print(f"❌ Erro list_regimes_tributarios: {e}")
        flash('Erro ao carregar regimes tributários', 'error')
        return render_template('admin/regimes_tributarios/list.html', regimes=[])
    finally:
        db.close()

@admin_bp.route('/regimes-tributarios/novo', defaults={'regime_tributario_id': None})
@admin_bp.route('/regimes-tributarios/<int:regime_tributario_id>/editar')
@login_required
@permission_required('regimes_tributarios.create')
def novo_regime_tributario(regime_tributario_id):
    regime = None
    if regime_tributario_id:
        db = _get_db()
        row = db.execute(text("""
            SELECT regime_tributario_id, nome, descricao
            FROM regimes_tributarios
            WHERE regime_tributario_id = :rid
        """), {'rid': regime_tributario_id}).first()
        if row:
            regime = _safe_row_to_dict(row, ['regime_tributario_id', 'nome', 'descricao'])
        db.close()
    return render_template('admin/regimes_tributarios/form.html', regime=regime)

@admin_bp.route('/regimes-tributarios/salvar', methods=['POST'])
@login_required
@permission_required('regimes_tributarios.create')
def salvar_regime_tributario():
    db = _get_db()
    regime_tributario_id = request.form.get('regime_tributario_id')
    nome = request.form.get('nome')
    descricao = request.form.get('descricao')
    try:
        if regime_tributario_id:
            db.execute(text("""
                UPDATE regimes_tributarios
                SET nome = :nome, descricao = :descricao
                WHERE regime_tributario_id = :rid
            """), {'nome': nome, 'descricao': descricao, 'rid': regime_tributario_id})
            flash('Regime tributário atualizado com sucesso!', 'success')
        else:
            db.execute(text("""
                INSERT INTO regimes_tributarios (nome, descricao)
                VALUES (:nome, :descricao)
            """), {'nome': nome, 'descricao': descricao})
            flash('Regime tributário cadastrado com sucesso!', 'success')
        db.commit()
    except Exception as e:
        db.rollback()
        if 'duplicate key value violates unique constraint' in str(e):
            flash('Já existe um regime tributário com esse nome.', 'warning')
        else:
            flash('Erro ao salvar regime tributário.', 'danger')
    finally:
        db.close()
    return redirect(url_for('admin.list_regimes_tributarios'))

@admin_bp.route('/regimes-tributarios/<int:regime_tributario_id>/delete', methods=['POST'])
@login_required
@permission_required('regimes_tributarios.delete')
def delete_regime_tributario(regime_tributario_id: int):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM regimes_tributarios WHERE regime_tributario_id = :rid"),
                   {'rid': regime_tributario_id})
        db.commit()
        flash('Regime tributário excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_regime_tributario: {e}")
        flash('Erro ao excluir regime tributário', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_regimes_tributarios'))

@admin_bp.route('/roles')
@login_required
@permission_required('roles.view')
def list_roles():
    db = _get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(text("""
            SELECT id, name, description
            FROM roles
            WHERE name ILIKE :q OR description ILIKE :q
            ORDER BY name
        """), {'q': f'%{q}%'}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT id, name, description
            FROM roles
            ORDER BY name
        """)).fetchall()
    roles = [dict(row._mapping) for row in rows]
    return render_template('admin/roles/list.html', roles=roles)

@admin_bp.route('/roles/novo', methods=['GET', 'POST'])
@login_required
@permission_required('roles.create')
def create_role():
    db = _get_db()
    permissions = db.execute(text("SELECT id, name, description FROM permissions ORDER BY name")).fetchall()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        selected_permissions = request.form.getlist('permissions')
        try:
            result = db.execute(text("""
                INSERT INTO roles (name, description)
                VALUES (:name, :description)
                RETURNING id
            """), {'name': name, 'description': description})
            role_id = result.scalar()
            for perm_id in selected_permissions:
                db.execute(text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :perm_id)
                """), {'role_id': role_id, 'perm_id': perm_id})
            db.commit()
            flash('Role cadastrada com sucesso!', 'success')
            return redirect(url_for('admin.list_roles'))
        except Exception as e:
            db.rollback()
            flash('Erro ao cadastrar role', 'danger')
    return render_template('admin/roles/form.html', role=None, permissions=permissions)

@admin_bp.route('/roles/editar/<int:role_id>', methods=['GET', 'POST'])
@login_required
@permission_required('roles.edit')
def edit_role(role_id):
    db = _get_db()
    permissions = db.execute(text("SELECT id, name, description FROM permissions ORDER BY name")).fetchall()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        selected_permissions = request.form.getlist('permissions')
        try:
            db.execute(text("""
                UPDATE roles SET
                    name = :name,
                    description = :description
                WHERE id = :role_id
            """), {'name': name, 'description': description, 'role_id': role_id})
            db.execute(text("DELETE FROM role_permissions WHERE role_id = :role_id"), {'role_id': role_id})
            for perm_id in selected_permissions:
                db.execute(text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :perm_id)
                """), {'role_id': role_id, 'perm_id': perm_id})
            db.commit()
            flash('Role atualizada com sucesso!', 'success')
            return redirect(url_for('admin.list_roles'))
        except Exception as e:
            db.rollback()
            flash('Erro ao atualizar role', 'danger')
    row = db.execute(text("SELECT id, name, description FROM roles WHERE id = :id"), {'id': role_id}).fetchone()
    role = dict(row._mapping) if row else {}
    role_permissions = [p[0] for p in db.execute(text("SELECT permission_id FROM role_permissions WHERE role_id = :id"), {'id': role_id}).fetchall()]
    role['permissions'] = role_permissions
    return render_template('admin/roles/form.html', role=role, permissions=permissions)

@admin_bp.route('/roles/excluir/<int:role_id>', methods=['POST'])
@login_required
@permission_required('roles.delete')
def delete_role(role_id):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM role_permissions WHERE role_id = :id"), {'id': role_id})
        db.execute(text("DELETE FROM roles WHERE id = :id"), {'id': role_id})
        db.commit()
        flash('Role excluída com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_role: {e}")
        flash('Erro ao excluir role', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_roles'))

@admin_bp.route('/permissions')
@login_required
@permission_required('permissions.view')
def list_permissions():
    db = _get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(text("""
            SELECT id, name, description
            FROM permissions
            WHERE name ILIKE :q OR description ILIKE :q
            ORDER BY name
        """), {'q': f'%{q}%'}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT id, name, description
            FROM permissions
            ORDER BY name
        """)).fetchall()
    permissions = [dict(row._mapping) for row in rows]
    return render_template('admin/permissions/list.html', permissions=permissions)

@admin_bp.route('/permissions/novo')
@login_required
@permission_required('permissions.create')
def create_permission():
    return render_template('admin/permissions/form.html', permission=None)

@admin_bp.route('/permissions/editar/<int:permission_id>', methods=['GET', 'POST'])
@login_required
@permission_required('permissions.edit')
def edit_permission(permission_id):
    db = _get_db()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        try:
            db.execute(text("""
                UPDATE permissions SET
                    name = :name,
                    description = :description
                WHERE id = :permission_id
            """), {
                'name': name,
                'description': description,
                'permission_id': permission_id
            })
            db.commit()
            flash('Permissão atualizada com sucesso!', 'success')
            return redirect(url_for('admin.list_permissions'))
        except Exception as e:
            db.rollback()
            flash('Erro ao atualizar permissão', 'danger')
    row = db.execute(text("SELECT id, name, description FROM permissions WHERE id = :id"), {'id': permission_id}).fetchone()
    permission = dict(row._mapping) if row else None
    return render_template('admin/permissions/form.html', permission=permission)

@admin_bp.route('/permissions/excluir/<int:permission_id>', methods=['POST'])
@login_required
@permission_required('permissions.delete')
def delete_permission(permission_id):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM permissions WHERE id = :id"), {'id': permission_id})
        db.commit()
        flash('Permissão excluída com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_permission: {e}")
        flash('Erro ao excluir permissão', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_permissions'))

@admin_bp.route('/user-permissions')
@login_required
def list_user_permissions():
    """
    Stub para evitar BuildError de url_for('admin.list_user_permissions') usado em base.html.
    Gestão de permissões por usuário.
    """
    flash('Lista de Permissões de Usuário (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

@admin_bp.route('/logs')
@login_required
def list_logs():
    """
    Stub para evitar BuildError de url_for('admin.list_logs') usado em base.html.
    Logs do sistema.
    """
    flash('Lista de Logs (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

@admin_bp.route('/configuracoes')
@login_required
def configuracoes():
    """
    Stub para evitar BuildError de url_for('admin.configuracoes') usado em base.html.
    Configurações do sistema.
    """
    flash('Configurações do Sistema (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

# REMOVIDO: Stub antigo da rota /auditoria (implementação completa está na linha ~3719)
# A função list_auditoria() substitui este stub

@admin_bp.route('/backups')
@login_required
@permission_required('backups.view')
def list_backups():
    """
    Lista todos os backups disponíveis com informações detalhadas.
    """
    from config.settings import BACKUP_DIR, BACKUP_LOG_DIR
    import glob
    
    try:
        # Criar diretório de backups se não existir
        backup_path = Path(BACKUP_DIR)
        backup_path.mkdir(exist_ok=True)
        
        # Buscar todos os arquivos de backup
        backup_files = glob.glob(os.path.join(BACKUP_DIR, 'backup_*.sql.gz'))
        
        backups = []
        for filepath in backup_files:
            stat = os.stat(filepath)
            backups.append({
                'filename': os.path.basename(filepath),
                'filepath': filepath,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created_at': datetime.fromtimestamp(stat.st_mtime),
                'age_days': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
            })
        
        # Ordenar por data de criação (mais recente primeiro)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Buscar logs de backup
        log_files = glob.glob(os.path.join(BACKUP_LOG_DIR, 'backup_*.log'))
        last_backup_log = None
        if log_files:
            log_files.sort(key=os.path.getmtime, reverse=True)
            log_path = log_files[0]
            with open(log_path, 'r') as f:
                last_backup_log = f.read()
        
        return render_template('admin/backups.html', 
                             backups=backups,
                             backup_dir=BACKUP_DIR,
                             last_log=last_backup_log)
    except Exception as e:
        flash(f'Erro ao listar backups: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/backups/executar', methods=['POST'])
@login_required
@permission_required('backups.create')
def executar_backup_manual():
    """
    Executa backup manual do banco de dados.
    """
    from config.settings import BACKUP_DIR, BACKUP_RETENTION_DAYS
    import subprocess
    
    try:
        # Construir comando de backup
        script_path = os.path.join(os.getcwd(), 'backup_database.sh')
        
        if not os.path.exists(script_path):
            flash('Script de backup não encontrado!', 'danger')
            return redirect(url_for('admin.list_backups'))
        
        # Executar script de backup
        result = subprocess.run(
            [script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos timeout
        )
        
        if result.returncode == 0:
            flash('Backup executado com sucesso!', 'success')
        else:
            flash(f'Erro ao executar backup: {result.stderr}', 'danger')
            
    except subprocess.TimeoutExpired:
        flash('Timeout ao executar backup (> 5 minutos)', 'danger')
    except Exception as e:
        flash(f'Erro ao executar backup: {str(e)}', 'danger')
    
    return redirect(url_for('admin.list_backups'))

@admin_bp.route('/backups/download/<filename>')
@login_required
@permission_required('backups.download')
def download_backup(filename):
    """
    Faz download de um arquivo de backup específico.
    """
    from config.settings import BACKUP_DIR
    from flask import send_file
    
    try:
        # Validar filename para prevenir directory traversal
        secure_name = secure_filename(filename)
        if not secure_name.startswith('backup_') or not secure_name.endswith('.sql.gz'):
            flash('Nome de arquivo inválido!', 'danger')
            return redirect(url_for('admin.list_backups'))
        
        filepath = os.path.join(BACKUP_DIR, secure_name)
        
        if not os.path.exists(filepath):
            flash('Arquivo de backup não encontrado!', 'danger')
            return redirect(url_for('admin.list_backups'))
        
        return send_file(filepath, as_attachment=True)
        
    except Exception as e:
        flash(f'Erro ao baixar backup: {str(e)}', 'danger')
        return redirect(url_for('admin.list_backups'))

@admin_bp.route('/backups/delete/<filename>', methods=['POST'])
@login_required
@permission_required('backups.delete')
def delete_backup(filename):
    """
    Remove um arquivo de backup específico.
    """
    from config.settings import BACKUP_DIR
    
    try:
        # Validar filename
        secure_name = secure_filename(filename)
        if not secure_name.startswith('backup_') or not secure_name.endswith('.sql.gz'):
            flash('Nome de arquivo inválido!', 'danger')
            return redirect(url_for('admin.list_backups'))
        
        filepath = os.path.join(BACKUP_DIR, secure_name)
        
        if not os.path.exists(filepath):
            flash('Arquivo de backup não encontrado!', 'danger')
            return redirect(url_for('admin.list_backups'))
        
        os.remove(filepath)
        flash(f'Backup {secure_name} removido com sucesso!', 'success')
        
    except Exception as e:
        flash(f'Erro ao remover backup: {str(e)}', 'danger')
    
    return redirect(url_for('admin.list_backups'))

@admin_bp.route('/backup')
@login_required
def backup():
    """
    Redireciona para a lista de backups (mantém compatibilidade).
    """
    return redirect(url_for('admin.list_backups'))

# -------------------------------------------------------------------
# DASHBOARD ANALYTICS
# -------------------------------------------------------------------

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard principal com analytics, gráficos e KPIs do sistema.
    """
    db = _get_db()
    try:
        from datetime import datetime, timedelta
        
        # KPIs principais
        kpis = {}
        
        # 1. Total de NFes emitidas
        kpis['total_nfes'] = db.execute(text("""
            SELECT COUNT(*) FROM nfe_emitidas
        """)).scalar() or 0
        
        # 2. Valor total de NFes (extraindo do JSON)
        kpis['valor_total'] = db.execute(text("""
            SELECT COALESCE(SUM(
                (json_nfe->>'valor_total')::numeric
            ), 0) FROM nfe_emitidas
            WHERE json_nfe IS NOT NULL AND json_nfe->>'valor_total' IS NOT NULL
        """)).scalar() or 0
        
        # 3. Taxa de sucesso (autorizadas vs total)
        total = kpis['total_nfes']
        autorizadas = db.execute(text("""
            SELECT COUNT(*) FROM nfe_emitidas WHERE status = 'Autorizada'
        """)).scalar() or 0
        kpis['taxa_sucesso'] = round((autorizadas / total * 100) if total > 0 else 0, 1)
        
        # 4. Dias até vencimento do certificado mais próximo
        kpis['dias_certificado'] = db.execute(text("""
            SELECT MIN(EXTRACT(DAY FROM (validade_fim - CURRENT_DATE)))
            FROM certificados_digitais
            WHERE ativo = TRUE AND validade_fim > CURRENT_DATE
        """)).scalar()
        if kpis['dias_certificado'] is None:
            kpis['dias_certificado'] = 0
        else:
            kpis['dias_certificado'] = int(kpis['dias_certificado'])
        
        # 5. Total de clientes ativos
        kpis['total_clientes'] = db.execute(text("""
            SELECT COUNT(*) FROM clientes WHERE ativo = TRUE
        """)).scalar() or 0
        
        # 6. Total de produtos cadastrados
        kpis['total_produtos'] = db.execute(text("""
            SELECT COUNT(*) FROM produtos WHERE ativo = TRUE
        """)).scalar() or 0
        
        # 7. Sugestões IA aceitas (se houver dados)
        kpis['sugestoes_ia_aceitas'] = db.execute(text("""
            SELECT COUNT(*) FROM sugestoes_ia WHERE sugestao_aceita = TRUE
        """)).scalar() or 0
        
        # 8. NFes do mês atual
        kpis['nfes_mes'] = db.execute(text("""
            SELECT COUNT(*) 
            FROM nfe_emitidas 
            WHERE EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND EXTRACT(MONTH FROM data_criacao) = EXTRACT(MONTH FROM CURRENT_DATE)
        """)).scalar() or 0
        
        return render_template('admin/dashboard.html', kpis=kpis)
        
    except Exception as e:
        print(f"❌ Erro dashboard: {e}")
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/dashboard/api/data')
@login_required
def dashboard_api_data():
    """
    API JSON para dados do dashboard (gráficos e métricas).
    """
    db = _get_db()
    try:
        from datetime import datetime, timedelta
        from calendar import month_name
        
        data = {}
        
        # Gráfico 1: NFes por mês (últimos 12 meses)
        nfes_por_mes = db.execute(text("""
            SELECT 
                TO_CHAR(data_criacao, 'YYYY-MM') as mes,
                COUNT(*) as total,
                COALESCE(SUM(
                    (json_nfe->>'valor_total')::numeric
                ), 0) as valor
            FROM nfe_emitidas
            WHERE data_criacao >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY TO_CHAR(data_criacao, 'YYYY-MM')
            ORDER BY mes
        """)).fetchall()
        
        data['nfes_por_mes'] = {
            'labels': [row[0] for row in nfes_por_mes],
            'totais': [int(row[1]) for row in nfes_por_mes],
            'valores': [float(row[2]) for row in nfes_por_mes]
        }
        
        # Gráfico 2: Top 5 produtos cadastrados
        top_produtos = db.execute(text("""
            SELECT 
                descricao,
                produto_id
            FROM produtos
            WHERE ativo = TRUE AND descricao IS NOT NULL
            ORDER BY produto_id DESC
            LIMIT 5
        """)).fetchall()
        
        data['top_produtos'] = {
            'labels': [row[0][:30] if row[0] else 'Sem descrição' for row in top_produtos],
            'valores': [idx + 1 for idx in range(len(top_produtos))]  # Sequencial para demonstração
        }
        
        # Gráfico 3: Status das NFes (pizza)
        status_nfes = db.execute(text("""
            SELECT 
                COALESCE(status, 'Sem Status') as status,
                COUNT(*) as total
            FROM nfe_emitidas
            GROUP BY status
            ORDER BY total DESC
        """)).fetchall()
        
        data['status_nfes'] = {
            'labels': [row[0] for row in status_nfes],
            'valores': [int(row[1]) for row in status_nfes]
        }
        
        # Gráfico 4: Clientes mais ativos (top 5)
        top_clientes = db.execute(text("""
            SELECT 
                c.razao_social,
                COUNT(n.nfe_emitida_id) as total_nfes
            FROM clientes c
            LEFT JOIN nfe_emitidas n ON c.cliente_id = n.cliente_id
            WHERE c.ativo = TRUE
            GROUP BY c.razao_social
            HAVING COUNT(n.nfe_emitida_id) > 0
            ORDER BY total_nfes DESC
            LIMIT 5
        """)).fetchall()
        
        data['top_clientes'] = {
            'labels': [row[0][:30] for row in top_clientes],
            'valores': [int(row[1]) for row in top_clientes]
        }
        
        return jsonify(data)
        
    except Exception as e:
        print(f"❌ Erro dashboard API: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/motivos-desoneracao')
@login_required
@permission_required('motivos_desoneracao.view')
def list_motivos_desoneracao():
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT motivo_id, codigo, descricao
            FROM motivos_desoneracao_icms
            ORDER BY codigo
        """)).fetchall()
        motivos = [dict(row._mapping) for row in rows]
        return render_template('admin/motivos_desoneracao/list.html', motivos=motivos)
    except Exception as e:
        print(f"❌ Erro list_motivos_desoneracao: {e}")
        flash('Erro ao carregar motivos de desoneração', 'error')
        return render_template('admin/motivos_desoneracao/list.html', motivos=[])
    finally:
        db.close()

@admin_bp.route('/motivos-desoneracao/novo', defaults={'motivo_id': None})
@admin_bp.route('/motivos-desoneracao/<int:motivo_id>/editar')
@login_required
@permission_required('motivos_desoneracao.create')
def novo_motivo_desoneracao(motivo_id):
    motivo = None
    if motivo_id:
        db = _get_db()
        row = db.execute(text("""
            SELECT motivo_id, codigo, descricao
            FROM motivos_desoneracao_icms
            WHERE motivo_id = :mid
        """), {'mid': motivo_id}).first()
        if row:
            motivo = dict(row._mapping)
        db.close()
    return render_template('admin/motivos_desoneracao/form.html', motivo=motivo)

@admin_bp.route('/motivos-desoneracao/salvar', methods=['POST'])
@login_required
@permission_required('motivos_desoneracao.create')
def salvar_motivo_desoneracao():
    db = _get_db()
    motivo_id = request.form.get('motivo_id')
    codigo = request.form.get('codigo')
    descricao = request.form.get('descricao')
    try:
        if motivo_id:
            db.execute(text("""
                UPDATE motivos_desoneracao_icms
                SET codigo = :codigo, descricao = :descricao
                WHERE motivo_id = :mid
            """), {'codigo': codigo, 'descricao': descricao, 'mid': motivo_id})
            flash('Motivo de desoneração atualizado com sucesso!', 'success')
        else:
            db.execute(text("""
                INSERT INTO motivos_desoneracao_icms (codigo, descricao)
                VALUES (:codigo, :descricao)
            """), {'codigo': codigo, 'descricao': descricao})
            flash('Motivo de desoneração cadastrado com sucesso!', 'success')
        db.commit()
    except Exception as e:
        db.rollback()
        if 'duplicate key value violates unique constraint' in str(e):
            flash('Já existe um motivo de desoneração com esse código.', 'warning')
        else:
            flash('Erro ao salvar motivo de desoneração.', 'danger')
    finally:
        db.close()
    return redirect(url_for('admin.list_motivos_desoneracao'))

@admin_bp.route('/motivos-desoneracao/<int:motivo_id>/delete', methods=['POST'])
@login_required
@permission_required('motivos_desoneracao.delete')
def delete_motivo_desoneracao(motivo_id: int):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM motivos_desoneracao_icms WHERE motivo_id = :mid"),
                   {'mid': motivo_id})
        db.commit()
        flash('Motivo de desoneração excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_motivo_desoneracao: {e}")
        flash('Erro ao excluir motivo de desoneração', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_motivos_desoneracao'))

@admin_bp.route('/origens-mercadoria')
@login_required
@permission_required('origens_mercadoria.view')
def list_origens_mercadoria():
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT origem_id, codigo, descricao
            FROM origens_mercadoria
            ORDER BY codigo
        """)).fetchall()
        origens = [dict(row._mapping) for row in rows]
        return render_template('admin/origens_mercadoria/list.html', origens=origens)
    except Exception as e:
        flash(f'Erro ao listar origens de mercadoria: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_home'))

@admin_bp.route('/origens-mercadoria/novo', methods=['GET', 'POST'])
@login_required
@permission_required('origens_mercadoria.create')
def create_origem_mercadoria():
    db = _get_db()
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        try:
            db.execute(text("""
                INSERT INTO origens_mercadoria (codigo, descricao)
                VALUES (:codigo, :descricao)
            """), {
                'codigo': codigo,
                'descricao': descricao
            })
            db.commit()
            flash('Origem de Mercadoria criada com sucesso!', 'success')
            return redirect(url_for('admin.list_origens_mercadoria'))
        except Exception as e:
            db.rollback()
            flash(f'Erro ao criar Origem de Mercadoria: {str(e)}', 'danger')
    return render_template('admin/origens_mercadoria/form.html', origem=None)

@admin_bp.route('/origens-mercadoria/editar/<int:origem_id>', methods=['GET', 'POST'])
@login_required
@permission_required('origens_mercadoria.edit')
def edit_origem_mercadoria(origem_id):
    db = _get_db()
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        try:
            db.execute(text("""
                UPDATE origens_mercadoria SET
                    codigo = :codigo,
                    descricao = :descricao
                WHERE origem_id = :origem_id
            """), {
                'codigo': codigo,
                'descricao': descricao,
                'origem_id': origem_id
            })
            db.commit()
            flash('Origem de Mercadoria atualizada com sucesso!', 'success')
            return redirect(url_for('admin.list_origens_mercadoria'))
        except Exception as e:
            db.rollback()
            flash('Erro ao atualizar Origem de Mercadoria', 'danger')
    row = db.execute(text("SELECT origem_id, codigo, descricao FROM origens_mercadoria WHERE origem_id = :id"), {'id': origem_id}).fetchone()
    origem = dict(row._mapping) if row else None
    return render_template('admin/origens_mercadoria/form.html', origem=origem)

@admin_bp.route('/origens-mercadoria/excluir/<int:origem_id>', methods=['POST'])
@login_required
@permission_required('origens_mercadoria.delete')
def delete_origem_mercadoria(origem_id):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM origens_mercadoria WHERE origem_id = :id"), {'id': origem_id})
        db.commit()
        flash('Origem de Mercadoria excluída com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_origem_mercadoria: {e}")
        flash('Erro ao excluir Origem de Mercadoria', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_origens_mercadoria'))

# Opcional: função utilitária para checar endpoints (pode usar em templates se desejar)
def has_endpoint(name: str) -> bool:
    return name in current_app.view_functions

# Registra no Jinja (coloque isto após criação do blueprint se quiser usar em templates)
@admin_bp.record_once
def _register_template_utils(setup_state):
    setup_state.app.jinja_env.globals['has_endpoint'] = has_endpoint

# -------------------------------------------------------------------
# CLIENTES
# -------------------------------------------------------------------

@admin_bp.route('/clientes', methods=['GET'])
@login_required
@permission_required('clientes.view')
def list_clientes():
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT cliente_id, razao_social, cnpj, ativo, data_cadastro, email_contato, telefone_contato
            FROM clientes
            ORDER BY razao_social
        """)).fetchall()
        clientes = [_safe_row_to_dict(r, [
            'cliente_id','razao_social','cnpj','ativo','data_cadastro','email_contato','telefone_contato'
        ]) for r in rows]
        return render_template('admin/clientes/list.html', clientes=clientes)
    except Exception as e:
        print(f"❌ Erro list_clientes: {e}")
        flash('Erro ao carregar clientes', 'error')
        return render_template('admin/clientes/list.html', clientes=[])
    finally:
        db.close()


from services.certificate_service import  _encrypt_password
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import hashes
import base64
@admin_bp.route('/clientes/novo', methods=['GET', 'POST'])
@login_required
@permission_required('clientes.create')
def create_cliente():
    db = _get_db()
    try:
        # Carrega regimes tributários para o select
        regimes_rows = db.execute(text("SELECT regime_tributario_id, nome FROM regimes_tributarios")).fetchall()
        regimes_tributarios = [_safe_row_to_dict(r, ['regime_tributario_id', 'nome']) for r in regimes_rows]

        if request.method == 'POST':
            # Limpar CEP (remover formatação)
            cep_raw = request.form.get('cep', '')
            cep_limpo = ''.join(filter(str.isdigit, cep_raw))
            
            # Limpar CNPJ (remover formatação)
            cnpj_raw = request.form.get('cnpj', '')
            cnpj_limpo = ''.join(filter(str.isdigit, cnpj_raw))
            
            # Dados do cliente
            data = {
                'razao_social': request.form.get('razao_social'),
                'nome_fantasia': request.form.get('nome_fantasia'),
                'cnpj': cnpj_limpo,  # Limpo
                'inscricao_estadual': request.form.get('inscricao_estadual'),
                'inscricao_municipal': request.form.get('inscricao_municipal'),
                'regime_tributario_id': request.form.get('regime_tributario_id'),
                'cnae': request.form.get('cnae'),
                'cep': cep_limpo,  # Limpo
                'logradouro': request.form.get('logradouro'),
                'numero': request.form.get('numero'),
                'complemento': request.form.get('complemento'),
                'bairro': request.form.get('bairro'),
                'nome_municipio': request.form.get('nome_municipio'),
                'codigo_municipio': request.form.get('codigo_municipio'),
                'uf': request.form.get('uf'),
                'email_contato': request.form.get('email_contato'),
                'telefone_contato': request.form.get('telefone_contato'),
                'ativo': request.form.get('ativo') == 'on',
                'data_cadastro': datetime.now(),
                'created_by_user_id': current_user.id
            }
            try:
                # Salva cliente e recupera o cliente_id
                result = db.execute(text("""
                    INSERT INTO clientes (
                        razao_social, nome_fantasia, cnpj, inscricao_estadual, inscricao_municipal,
                        regime_tributario_id, cnae, cep, logradouro, numero, complemento, bairro,
                        nome_municipio, codigo_municipio, uf, email_contato, telefone_contato, ativo, data_cadastro, created_by_user_id
                    ) VALUES (
                        :razao_social, :nome_fantasia, :cnpj, :inscricao_estadual, :inscricao_municipal,
                        :regime_tributario_id, :cnae, :cep, :logradouro, :numero, :complemento, :bairro,
                        :nome_municipio, :codigo_municipio, :uf, :email_contato, :telefone_contato, :ativo, :data_cadastro, :created_by_user_id
                    ) RETURNING cliente_id
                """), data)
                row = result.fetchone()
                if row:
                    cliente_id = row[0]
                else:
                    # Nenhum id retornado: desfaz e retorna o formulário com erro
                    db.rollback()
                    flash('Erro ao inserir cliente: nenhum id retornado pelo banco.', 'danger')
                    return render_template(
                        'admin/clientes/form.html',
                        cliente=None,
                        form_data=data,
                        regimes_tributarios=regimes_tributarios
                    )

                # Salva certificado digital se foi enviado
                cert_file = request.files.get('conteudo_certificado_file')
                cert_senha = request.form.get('cert_senha_certificado')
                cert_ativo = request.form.get('cert_ativo') == 'on'
                cert_nome_arquivo = request.form.get('cert_nome_arquivo_original', 'Upload Inicial')

                if cert_file and cert_file.filename:
                    conteudo_certificado = cert_file.read()
                    senha_criptografada = _encrypt_password(cert_senha) if cert_senha else None
                    nome_arquivo_original = cert_file.filename

                    # Extrair fingerprint, validade_inicio e validade_fim
                    try:
                        # Carregar PKCS#12
                        password_bytes = cert_senha.encode('utf-8') if cert_senha is not None else None
                        private_key, cert_x509_obj, additional_certificates = pkcs12.load_key_and_certificates(
                            conteudo_certificado,
                            password_bytes
                        )
                        cert_obj = cert_x509_obj
                        if cert_obj is None and additional_certificates:
                            cert_obj = additional_certificates[0]
                        if cert_obj is None:
                            raise Exception("Certificado X.509 não encontrado dentro do PKCS#12")
                        fingerprint = cert_obj.fingerprint(hashes.SHA256()).hex()
                        validade_inicio = getattr(cert_obj, "not_valid_before_utc", None)
                        validade_fim = getattr(cert_obj, "not_valid_before_utc", None)
                    except Exception as e:
                        print(f"❌ Erro ao extrair dados do certificado: {e}")
                        fingerprint = None
                        validade_inicio = None
                        validade_fim = None

                    # Se quiser salvar o conteúdo em base64 (compatível com seu service)
                    conteudo_certificado_b64 = base64.b64encode(conteudo_certificado).decode('utf-8')

                    db.execute(text("""
                        INSERT INTO certificados_digitais (
                            cliente_id, conteudo_certificado, senha_certificado, ativo, data_upload,
                            nome_arquivo_original, created_by_user_id, fingerprint, validade_inicio, validade_fim
                        ) VALUES (
                            :cliente_id, :conteudo_certificado, :senha_certificado, :ativo, NOW(),
                            :nome_arquivo_original, :created_by_user_id, :fingerprint, :validade_inicio, :validade_fim
                        )
                    """), {
                        'cliente_id': cliente_id,
                        'conteudo_certificado': conteudo_certificado_b64,
                        'senha_certificado': senha_criptografada,
                        'ativo': cert_ativo,
                        'nome_arquivo_original': nome_arquivo_original,
                        'created_by_user_id': current_user.id,
                        'fingerprint': fingerprint,
                        'validade_inicio': validade_inicio,
                        'validade_fim': validade_fim
                    })

                db.commit()
                flash('Cliente cadastrado com sucesso!', 'success')
                return redirect(url_for('admin.list_clientes'))
            except Exception as e:
                db.rollback()
                print(f"❌ Erro ao salvar cliente/certificado: {e}")
                flash('Erro ao salvar cliente ou certificado', 'danger')
                form_data = data
                return render_template(
                    'admin/clientes/form.html',
                    cliente=None,
                    form_data=form_data,
                    regimes_tributarios=regimes_tributarios
                )

        # GET: exibe formulário vazio
        form_data = {
            'razao_social': '',
            'nome_fantasia': '',
            'cnpj': '',
            'inscricao_estadual': '',
            'inscricao_municipal': '',
            'regime_tributario_id': '',
            'cnae': '',
            'cep': '',
            'logradouro': '',
            'numero': '',
            'complemento': '',
            'bairro': '',
            'nome_municipio': '',
            'codigo_municipio': '',
            'uf': '',
            'email_contato': '',
            'telefone_contato': '',
            'ativo': True,
        }
        return render_template(
            'admin/clientes/form.html',
            cliente=None,
            form_data=form_data,
            regimes_tributarios=regimes_tributarios
        )
    except Exception as e:
        print(f"❌ Erro create_cliente: {e}")
        flash('Erro ao carregar formulário de cliente', 'error')
        return redirect(url_for('admin.list_clientes'))
    finally:
        db.close()


def _cliente_to_form_data(cliente_row):
    """Converte o resultado do banco para o dict esperado pelo form_data do template."""
    return {
        'razao_social': cliente_row.get('razao_social', ''),
        'nome_fantasia': cliente_row.get('nome_fantasia', ''),
        'cnpj': cliente_row.get('cnpj', ''),
        'inscricao_estadual': cliente_row.get('inscricao_estadual', ''),
        'inscricao_municipal': cliente_row.get('inscricao_municipal', ''),
        'regime_tributario_id': cliente_row.get('regime_tributario_id', ''),
        'cnae': cliente_row.get('cnae', ''),
        'cep': cliente_row.get('cep', ''),
        'logradouro': cliente_row.get('logradouro', ''),
        'numero': cliente_row.get('numero', ''),
        'complemento': cliente_row.get('complemento', ''),
        'bairro': cliente_row.get('bairro', ''),
        'nome_municipio': cliente_row.get('nome_municipio', ''),
        'codigo_municipio': cliente_row.get('codigo_municipio', ''),
        'uf': cliente_row.get('uf', ''),
        'email_contato': cliente_row.get('email_contato', ''),
        'telefone_contato': cliente_row.get('telefone_contato', ''),
        'ativo': cliente_row.get('ativo', True),
    }

@admin_bp.route('/clientes/<int:cliente_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('clientes.edit')
def edit_cliente(cliente_id: int):
    db = _get_db()
    try:
        row = db.execute(text("SELECT * FROM clientes WHERE cliente_id = :cid"), {'cid': cliente_id}).fetchone()
        
        if not row:
            flash('Cliente não encontrado', 'warning')
            return redirect(url_for('admin.list_clientes'))
        cliente = dict(row._mapping)

        if not cliente:
            flash('Cliente não encontrado', 'warning')
            return redirect(url_for('admin.list_clientes'))

        # Processar POST - atualização dos dados do cliente
        if request.method == 'POST':
            try:
                # Limpar CEP (remover formatação)
                cep_raw = request.form.get('cep', '')
                cep_limpo = ''.join(filter(str.isdigit, cep_raw))
                
                # Limpar CNPJ (remover formatação)
                cnpj_raw = request.form.get('cnpj', '')
                cnpj_limpo = ''.join(filter(str.isdigit, cnpj_raw))
                
                data = {
                    'razao_social': request.form.get('razao_social'),
                    'nome_fantasia': request.form.get('nome_fantasia'),
                    'cnpj': cnpj_limpo,  # Limpo
                    'inscricao_estadual': request.form.get('inscricao_estadual'),
                    'inscricao_municipal': request.form.get('inscricao_municipal'),
                    'regime_tributario_id': request.form.get('regime_tributario_id'),
                    'cnae': request.form.get('cnae'),
                    'cep': cep_limpo,  # Limpo
                    'logradouro': request.form.get('logradouro'),
                    'numero': request.form.get('numero'),
                    'complemento': request.form.get('complemento'),
                    'bairro': request.form.get('bairro'),
                    'nome_municipio': request.form.get('nome_municipio'),
                    'codigo_municipio': request.form.get('codigo_municipio'),
                    'uf': request.form.get('uf'),
                    'email_contato': request.form.get('email_contato'),
                    'telefone_contato': request.form.get('telefone_contato'),
                    'ativo': request.form.get('ativo') == 'on',
                    'cliente_id': cliente_id
                }

                db.execute(text("""
                    UPDATE clientes SET
                        razao_social = :razao_social,
                        nome_fantasia = :nome_fantasia,
                        cnpj = :cnpj,
                        inscricao_estadual = :inscricao_estadual,
                        inscricao_municipal = :inscricao_municipal,
                        regime_tributario_id = :regime_tributario_id,
                        cnae = :cnae,
                        cep = :cep,
                        logradouro = :logradouro,
                        numero = :numero,
                        complemento = :complemento,
                        bairro = :bairro,
                        nome_municipio = :nome_municipio,
                        codigo_municipio = :codigo_municipio,
                        uf = :uf,
                        email_contato = :email_contato,
                        telefone_contato = :telefone_contato,
                        ativo = :ativo
                    WHERE cliente_id = :cliente_id
                """), data)
                
                db.commit()
                flash('Cliente atualizado com sucesso!', 'success')
                return redirect(url_for('admin.list_clientes'))
            except Exception as e:
                db.rollback()
                print(f"❌ Erro ao atualizar cliente: {e}")
                flash('Erro ao atualizar cliente', 'danger')
                # Continua para renderizar o formulário com os dados atuais

        form_data = _cliente_to_form_data(cliente)
        certificados_result = db.execute(text("""
            SELECT * FROM certificados_digitais WHERE cliente_id = :cid
        """), {'cid': cliente_id}).fetchall()
        certificados_existentes = certificados_result if certificados_result else []
        
        
        # Consultar produtos cadastrados para o cliente
        prod_rows = db.execute(text("""
            SELECT *
            FROM produtos
            WHERE cliente_id = :cid
            ORDER BY descricao
        """), {'cid': cliente_id}).fetchall()
        produtos_existentes = []
        if prod_rows:
            produtos_existentes = [dict(row._mapping) for row in prod_rows]
         
            
        
        # Consultar regras tributárias para o cliente
        regras_rows = db.execute(text("""
            SELECT * FROM regras_tributacao WHERE cliente_id = :cid
        """), {'cid': cliente_id}).fetchall()
        regras_existentes = []
        if regras_rows:
            regras_existentes = [dict(row._mapping) for row in regras_rows]
            
        # Consultar destinatários para o cliente
        destinatarios_rows = db.execute(text("""
            SELECT * FROM destinatarios_nfe WHERE cliente_id = :cid
        """), {'cid': cliente_id}).fetchall()
        destinatarios = []
        if destinatarios_rows:
            destinatarios = [dict(row._mapping) for row in destinatarios_rows]
            
        regimes_rows = db.execute(text("SELECT regime_tributario_id, nome FROM regimes_tributarios")).fetchall()
        regimes_tributarios = []
        if regimes_rows:
            regimes_tributarios = [dict(r._mapping) for r in regimes_rows if r]


        certificados_existentes = [dict(row._mapping) for row in certificados_existentes if row]
       
        return render_template(
            'admin/clientes/form.html',
            cliente=cliente,
            cliente_id=cliente.get('cliente_id'),
            form_data=form_data,
            regimes_tributarios=regimes_tributarios,
            certificados_existentes=certificados_existentes,
            produtos_existentes=produtos_existentes,
            regras_existentes=regras_existentes,
            destinatarios=destinatarios
        )
    except Exception as e:
        import traceback
        print(f"❌ Erro edit_cliente: {e}")
        traceback.print_exc()
        flash('Erro ao carregar cliente', 'error')
        return redirect(url_for('admin.list_clientes'))
    finally:
        db.close()

@admin_bp.route('/clientes/<int:cliente_id>/delete', methods=['POST'])
@login_required
@permission_required('clientes.delete')
def delete_cliente(cliente_id: int):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM clientes WHERE cliente_id = :cid"), {'cid': cliente_id})
        db.commit()
        flash('Cliente excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_cliente: {e}")
        flash('Erro ao excluir cliente', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_clientes'))

@admin_bp.route('/certificados/novo/<int:cliente_id>')
@login_required
@permission_required('certificados.create')
def create_certificado(cliente_id: int):
    modal = request.args.get('modal', False)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Se for modal/AJAX, retorna apenas o conteúdo do formulário
    if modal or is_ajax:
        return render_template(
            'admin/certificados/form_content.html',
            certificado=None,
            cliente_id=cliente_id,
            modal=True
        )
    
    # Senão, retorna página completa
    return render_template(
        'admin/certificados/form.html',
        certificado=None,
        cliente_id=cliente_id,
        modal=False
    )

@admin_bp.route('/certificados/<int:certificado_digital_id>/edit/<int:cliente_id>', methods=['GET'])
@login_required
@permission_required('certificados.edit')
def edit_certificado(certificado_digital_id: int, cliente_id: int):
    db = _get_db()
    try:
        row = db.execute(text("""
            SELECT * FROM certificados_digitais WHERE certificado_digital_id = :cid
        """), {'cid': certificado_digital_id}).fetchone()
        certificado = dict(row._mapping) if row else None
        if not certificado:
            flash('Certificado não encontrado', 'warning')
            return redirect(url_for('admin.list_certificados'))
        return render_template(
            'admin/certificados/form.html',
            certificado=certificado,
            cliente_id=cliente_id
        )
    except Exception as e:
        print(f"❌ Erro edit_certificado: {e}")
        flash('Erro ao carregar certificado', 'error')
        return redirect(url_for('admin.list_certificados'))
    finally:
        db.close()

@admin_bp.route('/certificados/<int:certificado_digital_id>/delete', methods=['POST'])
@login_required
@permission_required('certificados.delete')
def delete_certificado(certificado_digital_id: int):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM certificados_digitais WHERE certificado_digital_id = :cid"),
                   {'cid': certificado_digital_id})
        db.commit()
        flash('Certificado excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_certificado: {e}")
        flash('Erro ao excluir certificado', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_certificados'))

@admin_bp.route('/regras-tributacao/nova/<int:cliente_id>')
@login_required
@permission_required('regras_tributacao.create')
def create_regra_tributacao(cliente_id: int):
    modal = request.args.get('modal', False)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or modal
    template = 'admin/regras_tributacao/form.html'
    db = _get_db()
    try:
        # Buscar todos os CFOPs
        cfop_rows = db.execute(text("""
            SELECT cfop_id, cfop, descricao FROM cfops ORDER BY cfop
        """)).fetchall()
        cfops = [dict(row._mapping) for row in cfop_rows]
        # Buscar todos os NCMs
        ncm_rows = db.execute(text("""
            SELECT ncm_id, codigo, descricao FROM ncms ORDER BY codigo
        """)).fetchall()
        ncms = [dict(row._mapping) for row in ncm_rows]
        if is_ajax:
            template = 'admin/regras_tributacao/form_partial.html'
        return render_template(
            template,
            regra=None,
            cliente_id=cliente_id,
            modal=modal,
            cfops=cfops,
            ncms=ncms
        )
    finally:
        db.close()

@admin_bp.route('/regras-tributacao/<int:regra_tributacao_id>/edit', methods=['GET'])
@login_required
@permission_required('regras_tributacao.edit')
def edit_regra_tributacao(regra_tributacao_id: int):
    db = _get_db()
    try:
        row = db.execute(text("""
            SELECT * FROM regras_tributacao WHERE regra_tributacao_id = :rid
        """), {'rid': regra_tributacao_id}).fetchone()
        regra = dict(row._mapping) if row else None
        if not regra:
            flash('Regra de tributação não encontrada', 'warning')
            return redirect(url_for('admin.list_regras_tributacao'))
        
        # Buscar todos os CFOPs
        cfop_rows = db.execute(text("""
            SELECT cfop_id, cfop, descricao FROM cfops ORDER BY cfop
        """)).fetchall()
        cfops = [dict(row._mapping) for row in cfop_rows]
        
        # Buscar todos os NCMs
        ncm_rows = db.execute(text("""
            SELECT ncm_id, codigo, descricao FROM ncms ORDER BY codigo
        """)).fetchall()
        ncms = [dict(row._mapping) for row in ncm_rows]
        
        return render_template('admin/regras_tributacao/form.html', 
                             regra=regra, 
                             cfops=cfops, 
                             ncms=ncms)
    except Exception as e:
        print(f"❌ Erro edit_regra_tributacao: {e}")
        flash('Erro ao carregar regra', 'error')
        return redirect(url_for('admin.list_regras_tributacao'))
    finally:
        db.close()

@admin_bp.route('/regras-tributacao/<int:regra_tributacao_id>/delete', methods=['POST'])
@login_required
@permission_required('regras_tributacao.delete')
def delete_regra_tributacao(regra_tributacao_id: int):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM regras_tributacao WHERE regra_tributacao_id=:rid"),
                   {'rid': regra_tributacao_id})
        db.commit()
        flash('Regra excluída com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_regra_tributacao: {e}")
        flash('Erro ao excluir regra', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_regras_tributacao'))

@admin_bp.route('/destinatarios/add/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
@permission_required('destinatarios_nfe.create')
def admin_destinatarios_nfe_add(cliente_id: int):
    if request.method == 'POST':
        db = _get_db()
        try:
            # Limpar CEP (remover formatação)
            cep_raw = request.form.get('cep', '')
            cep_limpo = ''.join(filter(str.isdigit, cep_raw))
            
            # Limpar CPF/CNPJ (remover formatação)
            cpf_cnpj_raw = request.form.get('cpf_cnpj', '')
            cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj_raw))
            
            # Garantir codigo_uf (campo obrigatório)
            codigo_uf = request.form.get('codigo_uf')
            if not codigo_uf or codigo_uf == 'None':
                # Mapeamento de fallback UF -> Código IBGE
                uf = request.form.get('uf', '')
                uf_map = {
                    'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29',
                    'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
                    'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
                    'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
                    'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
                    'SE': '28', 'TO': '17'
                }
                codigo_uf = uf_map.get(uf, '99')
                print(f"⚠️ codigo_uf não fornecido, usando mapeamento: {uf} = {codigo_uf}")
            
            data = {
                'cliente_id': cliente_id,
                'tipo_pessoa': request.form.get('tipo_pessoa'),  # Adicionado
                'nome_razao_social': request.form.get('nome_razao_social'),  # Adicionado
                'cpf_cnpj': cpf_cnpj_limpo,  # Limpo
                'ie': request.form.get('ie'),  # Adicionado
                'ie_indicador_nfe': request.form.get('ie_indicador_nfe', 'C'),  # Adicionado
                'email': request.form.get('email'),  # Adicionado
                'telefone': request.form.get('telefone'),  # Adicionado
                'logradouro': request.form.get('logradouro'),
                'numero': request.form.get('numero'),
                'complemento': request.form.get('complemento'),  # Adicionado
                'bairro': request.form.get('bairro'),
                'cep': cep_limpo,  # Limpo
                'codigo_municipio': request.form.get('codigo_municipio'),
                'nome_municipio': request.form.get('nome_municipio'),
                'uf': request.form.get('uf'),
                'codigo_uf': codigo_uf,  # Garantido
                'codigo_pais': request.form.get('codigo_pais', '1058'),  # Adicionado
                'nome_pais': request.form.get('nome_pais', 'Brasil'),  # Adicionado
                'data_cadastro': datetime.now(),  # Adicionado
                'created_by_user_id': current_user.id
            }
            db.execute(text("""
                INSERT INTO destinatarios_nfe (cliente_id, tipo_pessoa, nome_razao_social, cpf_cnpj, ie,
                                                ie_indicador_nfe, email, telefone, logradouro, numero,
                                                complemento, bairro, cep, codigo_municipio, nome_municipio,
                                                uf, codigo_uf, codigo_pais, nome_pais, data_cadastro, created_by_user_id)
                VALUES (:cliente_id, :tipo_pessoa, :nome_razao_social, :cpf_cnpj, :ie,
                        :ie_indicador_nfe, :email, :telefone, :logradouro, :numero,
                        :complemento, :bairro, :cep, :codigo_municipio, :nome_municipio,
                        :uf, :codigo_uf, :codigo_pais, :nome_pais, :data_cadastro, :created_by_user_id)
            """), data)
            db.commit()
            flash('Destinatário adicionado com sucesso', 'success')
            return redirect(url_for('admin.list_destinatarios', cliente_id=cliente_id))
        except Exception as e:
            db.rollback()
            print(f"❌ Erro admin_destinatarios_nfe_add: {e}")
            flash('Erro ao adicionar destinatário', 'error')
            return redirect(url_for('admin.list_destinatarios', cliente_id=cliente_id))
        finally:
            db.close()
    else:
        return render_template('admin/destinatarios/form.html', destinatario=None, cliente_id=cliente_id)



@admin_bp.route('/destinatarios/<int:destinatario_id>/delete', methods=['POST'])
@login_required
@permission_required('destinatarios_nfe.delete')
def delete_destinatario(destinatario_id: int):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM destinatarios_nfe WHERE destinatario_id = :cid"),
                   {'cid': destinatario_id})
        db.commit()
        flash('Destinatário excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_destinatario: {e}")
        flash('Erro ao excluir destinatário', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_destinatarios'))
# -------------------------------------------------------------------
# PRODUTOS
# -------------------------------------------------------------------

@admin_bp.route('/produtos')
@login_required
@permission_required('produtos.view')
def list_produtos():
    db = _get_db()
    try:
        from flask import session
        cliente_id = session.get('current_client_id')
        if not cliente_id:
            flash('Nenhum cliente selecionado.', 'error')
            return render_template('admin/produtos/list.html', produtos=[])
        rows = db.execute(text("""
            SELECT produto_id, codigo_interno, descricao, unidade_comercial, preco_unitario_padrao,
                   ncm_id, cfop_id, ativo
            FROM produtos
            WHERE cliente_id = :cliente_id
            ORDER BY descricao
        """), {'cliente_id': cliente_id}).fetchall()
        produtos = [_safe_row_to_dict(r, [
            'produto_id','codigo_interno','descricao','unidade_comercial',
            'preco_unitario_padrao','ncm_id','cfop_id','ativo'
        ]) for r in rows]
        return render_template('admin/produtos/list.html', produtos=produtos, cliente_id=cliente_id)
    except Exception as e:
        print(f"❌ Erro list_produtos: {e}")
        flash('Erro ao carregar produtos', 'error')
        return render_template('admin/produtos/list.html', produtos=[])
    finally:
        db.close()


@admin_bp.route('/produtos/importar', methods=['GET', 'POST'])
@login_required
@permission_required('produtos.create')
def importar_produtos():
    """
    GET: Exibe formulário de importação em lote
    POST: Processa arquivo CSV/XLSX e importa produtos
    """
    from flask import session, request
    from werkzeug.utils import secure_filename
    import os
    import pandas as pd
    from datetime import datetime
    
    cliente_id = session.get('current_client_id')
    if not cliente_id:
        flash('Selecione um cliente antes de importar produtos.', 'error')
        return redirect(url_for('admin.list_clientes'))
    
    if request.method == 'GET':
        return render_template('admin/produtos/importar.html', cliente_id=cliente_id)
    
    # POST: Processar upload
    db = _get_db()
    try:
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(url_for('admin.importar_produtos'))
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(url_for('admin.importar_produtos'))
        
        # Validar extensão
        if not arquivo.filename:
            flash('Nome do arquivo inválido', 'error')
            return redirect(url_for('admin.importar_produtos'))
        
        filename = secure_filename(arquivo.filename)
        extensao = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if extensao not in ['csv', 'xlsx', 'xls']:
            flash('Formato inválido. Use CSV ou XLSX', 'error')
            return redirect(url_for('admin.importar_produtos'))
        
        # Ler arquivo com pandas
        try:
            if extensao == 'csv':
                df = pd.read_csv(arquivo.stream, encoding='utf-8')
            else:
                df = pd.read_excel(arquivo.stream, engine='openpyxl')
        except Exception as e:
            flash(f'Erro ao ler arquivo: {str(e)}', 'error')
            return redirect(url_for('admin.importar_produtos'))
        
        # Validar colunas obrigatórias
        colunas_obrigatorias = ['codigo', 'descricao', 'unidade', 'valor']
        colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]
        
        if colunas_faltando:
            flash(f'Colunas obrigatórias faltando: {", ".join(colunas_faltando)}', 'error')
            return redirect(url_for('admin.importar_produtos'))
        
        # Processar importação
        sucessos = 0
        erros = []
        
        for idx, row in df.iterrows():
            # Ensure idx is converted to int properly - pandas index can be various types
            linha = int(str(idx)) + 2 if idx is not None else 2  # +2 porque pandas começa em 0 e tem header
            
            try:
                # Validações básicas
                if pd.isna(row['descricao']) or str(row['descricao']).strip() == '':
                    erros.append(f"Linha {linha}: Descrição obrigatória")
                    continue
                
                if pd.isna(row['valor']) or float(row['valor']) <= 0:
                    erros.append(f"Linha {linha}: Valor deve ser maior que zero")
                    continue
                
                # Buscar NCM se fornecido
                ncm_id = None
                if 'ncm_codigo' in row and not pd.isna(row['ncm_codigo']):
                    ncm_codigo = str(row['ncm_codigo']).strip()
                    ncm_row = db.execute(text("""
                        SELECT ncm_id FROM ncms WHERE codigo = :codigo LIMIT 1
                    """), {'codigo': ncm_codigo}).fetchone()
                    if ncm_row:
                        ncm_id = ncm_row[0]
                
                # Buscar CFOP se fornecido
                cfop_id = None
                if 'cfop_codigo' in row and not pd.isna(row['cfop_codigo']):
                    cfop_codigo = str(row['cfop_codigo']).strip()
                    cfop_row = db.execute(text("""
                        SELECT cfop_id FROM cfops WHERE cfop = :cfop LIMIT 1
                    """), {'cfop': cfop_codigo}).fetchone()
                    if cfop_row:
                        cfop_id = cfop_row[0]
                
                # Inserir produto
                db.execute(text("""
                    INSERT INTO produtos (
                        cliente_id, codigo_interno, descricao, unidade_comercial,
                        preco_unitario_padrao, ncm_id, cfop_id, ativo,
                        created_by_user_id, data_cadastro
                    ) VALUES (
                        :cliente_id, :codigo, :descricao, :unidade,
                        :valor, :ncm_id, :cfop_id, :ativo,
                        :user_id, :data
                    )
                """), {
                    'cliente_id': cliente_id,
                    'codigo': str(row['codigo']).strip() if not pd.isna(row['codigo']) else None,
                    'descricao': str(row['descricao']).strip(),
                    'unidade': str(row['unidade']).strip() if not pd.isna(row['unidade']) else 'UN',
                    'valor': float(row['valor']),
                    'ncm_id': ncm_id,
                    'cfop_id': cfop_id,
                    'ativo': bool(row.get('ativo', True)) if 'ativo' in row else True,
                    'user_id': current_user.id,
                    'data': datetime.now()
                })
                
                sucessos += 1
                
            except Exception as e:
                erros.append(f"Linha {linha}: {str(e)}")
                continue
        
        # Commit se houver sucessos
        if sucessos > 0:
            db.commit()
            flash(f'✅ Importação concluída: {sucessos} produto(s) importado(s)', 'success')
        
        if erros:
            flash(f'⚠️ {len(erros)} erro(s) encontrado(s)', 'warning')
        
        return render_template('admin/produtos/importar_resultado.html',
                             sucessos=sucessos,
                             erros=erros,
                             total_linhas=len(df),
                             cliente_id=cliente_id)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro importar_produtos: {e}")
        flash(f'Erro ao importar produtos: {str(e)}', 'error')
        return redirect(url_for('admin.importar_produtos'))
    finally:
        db.close()


@admin_bp.route('/produtos/template-csv')
@login_required
@permission_required('produtos.view')
def download_template_csv():
    """Download de template CSV para importação de produtos"""
    from flask import make_response
    import io
    
    # CSV com headers e exemplo
    csv_content = """codigo,descricao,unidade,valor,ncm_codigo,cfop_codigo,ativo
PROD001,Produto Exemplo 1,UN,10.50,84719000,5102,true
PROD002,Produto Exemplo 2,PC,25.00,85171290,5405,true
PROD003,Produto Exemplo 3,KG,5.75,39269090,5102,true"""
    
    output = io.StringIO()
    output.write(csv_content)
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=template_produtos.csv'
    
    return response


@admin_bp.route('/produtos/template-xlsx')
@login_required
@permission_required('produtos.view')
def download_template_xlsx():
    """Download de template XLSX para importação de produtos"""
    from flask import send_file
    import pandas as pd
    import io
    
    # Criar DataFrame com exemplo
    df = pd.DataFrame({
        'codigo': ['PROD001', 'PROD002', 'PROD003'],
        'descricao': ['Produto Exemplo 1', 'Produto Exemplo 2', 'Produto Exemplo 3'],
        'unidade': ['UN', 'PC', 'KG'],
        'valor': [10.50, 25.00, 5.75],
        'ncm_codigo': ['84719000', '85171290', '39269090'],
        'cfop_codigo': ['5102', '5405', '5102'],
        'ativo': [True, True, True]
    })
    
    # Criar arquivo Excel em memória
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Produtos', index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='template_produtos.xlsx'
    )


@admin_bp.route('/produtos/add', methods=['GET'])
@login_required
@permission_required('produtos.create')
def create_produto():
    from flask import session, request
    # Permite cliente_id via query string (prioridade)
    cliente_id = request.args.get('cliente_id') or session.get('current_client_id')
    # Sanitiza para garantir que não seja string 'None' ou vazio
    if not cliente_id or str(cliente_id).lower() == 'none':
        flash('Selecione um cliente antes de cadastrar produtos.', 'error')
        return redirect(url_for('admin.list_clientes'))
    cliente_id = str(cliente_id)
    db = _get_db()
    try:
        # Busca listas para selects (NCM, CFOP, etc)
        ncm_lista = db.execute(text("SELECT ncm_id, codigo, descricao FROM ncms")).fetchall()
        cfop_lista = db.execute(text("SELECT cfop_id, cfop ,descricao FROM cfops")).fetchall()
        origens_list = db.execute(text("SELECT origem_id, codigo, descricao FROM origens_mercadoria")).fetchall()
        csts_list = db.execute(text("SELECT cst_id, codigo, descricao FROM cst_icms")).fetchall()
        csosns_list = db.execute(text("SELECT csosn_id, codigo, descricao FROM csosn_icms")).fetchall()

        return render_template(
            'admin/produtos/form.html',
            produto=None,
            ncms=[dict(ncm._mapping) for ncm in ncm_lista],
            cfops=[dict(cfop._mapping) for cfop in cfop_lista],
            origens_mercadoria = [dict(origens._mapping) for origens in origens_list],
            csts = [dict(csts._mapping) for csts in csts_list],
            csosns = [dict(csosns._mapping) for csosns in csosns_list],
            cliente_id=cliente_id
        )
    except Exception as e:
        print(f"❌ Erro create_produto: {e}")
        flash('Erro ao carregar formulário de produto', 'error')
        return redirect(url_for('admin.list_produtos'))
    finally:
        db.close()

@admin_bp.route('/produtos/add', methods=['POST'])
@login_required
@permission_required('produtos.create')
def store_produto():
    db = _get_db()
    try:
        # Busca o cliente_id do form ou da sessão
        cliente_id = request.form.get('cliente_id') or session.get('current_client_id')
        # Corrige caso venha string 'None' ou valor vazio
        if not cliente_id or cliente_id == 'None':
            flash('Cliente não selecionado.', 'error')
            return redirect(url_for('admin.list_produtos'))
        cst_id = request.form.get('cst_id')
        csosn_id = request.form.get('csosn_id')
        data = {
            'cliente_id': int(cliente_id),
            'codigo_interno': request.form.get('codigo_interno'),
            'descricao': request.form.get('descricao'),
            'unidade_comercial': request.form.get('unidade_comercial','UN'),
            'tipo_item': request.form.get('tipo_item'),
            'preco_unitario_padrao': request.form.get('preco_unitario_padrao') or 0,
            'ncm_id': request.form.get('ncm_id'),
            'cfop_id': request.form.get('cfop_id'),
            'origem_mercadoria': request.form.get('origem_mercadoria'),
            'cest': request.form.get('cest'),
            'cst_id': int(cst_id) if cst_id else None,
            'csosn_id': int(csosn_id) if csosn_id else None,
            'created_by_user_id': current_user.id,
            'ativo': True
        }
        db.execute(text("""
            INSERT INTO produtos (cliente_id, codigo_interno, descricao, unidade_comercial, tipo_item, preco_unitario_padrao,
                      ncm_id, cfop_id, origem_mercadoria, cest, cst_id, csosn_id, created_by_user_id, ativo)
            VALUES (:cliente_id, :codigo_interno, :descricao, :unidade_comercial, :tipo_item, :preco_unitario_padrao,
                :ncm_id, :cfop_id, :origem_mercadoria, :cest, :cst_id, :csosn_id, :created_by_user_id, :ativo)
        """), data)
        db.commit()
        flash('Produto criado', 'success')
        # Redireciona para edição do cliente, aba produtos
        return redirect(url_for('admin.edit_cliente', cliente_id=cliente_id) + '#produtos')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro store_produto: {e}")
        flash('Erro ao criar produto', 'error')
        return redirect(url_for('admin.create_produto'))
    finally:
        db.close()


@admin_bp.route('/produtos/alterar-status', methods=['POST'])
@login_required
@permission_required('produtos.edit')
def alterar_status_produto():
    db = _get_db()
    try:
        produto_id = request.form.get('produto_id')
        ativo = request.form.get('ativo') == 'true'
        db.execute(text("""
            UPDATE produtos SET ativo = :ativo WHERE produto_id = :pid
        """), {'ativo': ativo, 'pid': produto_id})
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        print(f"❌ Erro alterar_status_produto: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@admin_bp.route('/produtos/<int:produto_id>/delete', methods=['POST'])
@login_required
@permission_required('produtos.delete')
def delete_produto(produto_id: int):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM produtos WHERE produto_id = :pid"), {'pid': produto_id})
        db.commit()
        flash('Produto excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_produto: {e}")
        flash('Erro ao excluir produto', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_produtos'))        

# -------------------------------------------------------------------
# DESTINATÁRIOS
# -------------------------------------------------------------------

@admin_bp.route('/destinatarios/<int:cliente_id>')
@login_required
@permission_required('destinatarios_nfe.view')
def list_destinatarios(cliente_id: int):
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT *
            FROM destinatarios_nfe
            WHERE cliente_id = :cid
            ORDER BY nome_razao_social
        """), {'cid': cliente_id}).fetchall()
        destinatarios = [_safe_row_to_dict(r, [
            'cliente_id','nome_razao_social','cpf_cnpj','uf','nome_municipio'
        ]) for r in rows]
        # Buscar nome do cliente
        cliente_row = db.execute(text("SELECT razao_social FROM clientes WHERE cliente_id = :cid"), {'cid': cliente_id}).fetchone()
        cliente_nome = cliente_row[0] if cliente_row else f"ID {cliente_id}"
        return render_template('admin/destinatarios/list.html', destinatarios=destinatarios, cliente_id=cliente_id, cliente_nome=cliente_nome)
    except Exception as e:
        print(f"❌ Erro list_destinatarios: {e}")
        flash('Erro ao carregar destinatários', 'error')
        # Buscar nome do cliente para erro também
        cliente_row = db.execute(text("SELECT razao_social FROM clientes WHERE cliente_id = :cid"), {'cid': cliente_id}).fetchone()
        cliente_nome = cliente_row[0] if cliente_row else f"ID {cliente_id}"
        return render_template('admin/destinatarios/list.html', destinatarios=[], cliente_id=cliente_id, cliente_nome=cliente_nome)
    finally:
        db.close()



@admin_bp.route('/destinatarios/salvar', methods=['POST'])
@login_required
@permission_required('destinatarios_nfe.create')
def salvar_destinatario():
    db = _get_db()
    try:
        # Limpar CEP (remover formatação)
        cep_raw = request.form.get('cep', '')
        cep_limpo = ''.join(filter(str.isdigit, cep_raw))
        
        # Limpar CPF/CNPJ (remover formatação)
        cpf_cnpj_raw = request.form.get('cpf_cnpj', '')
        cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj_raw))
        
        # Garantir codigo_uf (campo obrigatório)
        codigo_uf = request.form.get('codigo_uf')
        if not codigo_uf or codigo_uf == 'None':
            # Mapeamento de fallback UF -> Código IBGE
            uf = request.form.get('uf', '')
            uf_map = {
                'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29',
                'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
                'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
                'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
                'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
                'SE': '28', 'TO': '17'
            }
            codigo_uf = uf_map.get(uf, '99')
            print(f"⚠️ codigo_uf não fornecido, usando mapeamento: {uf} = {codigo_uf}")
        
        data = {
            'cliente_id': request.form.get('cliente_id'),
            'tipo_pessoa': request.form.get('tipo_pessoa'),
            'nome_razao_social': request.form.get('nome_razao_social'),
            'cpf_cnpj': cpf_cnpj_limpo,  # Limpo
            'ie': request.form.get('ie'),
            'ie_indicador_nfe': request.form.get('ie_indicador_nfe'),
            'email': request.form.get('email'),
            'telefone': request.form.get('telefone'),
            'logradouro': request.form.get('logradouro'),
            'numero': request.form.get('numero'),
            'complemento': request.form.get('complemento'),
            'bairro': request.form.get('bairro'),
            'cep': cep_limpo,  # Limpo
            'nome_municipio': request.form.get('nome_municipio'),
            'codigo_municipio': request.form.get('codigo_municipio'),
            'uf': request.form.get('uf'),
            'codigo_uf': codigo_uf,  # Garantido
            'codigo_pais': request.form.get('codigo_pais'),
            'nome_pais': request.form.get('nome_pais'),
            'data_cadastro': datetime.now(),
            'data_atualizacao': datetime.now(),
            'created_by_user_id': current_user.id
        }
        db.execute(text("""
            INSERT INTO destinatarios_nfe (cliente_id,tipo_pessoa,nome_razao_social, cpf_cnpj, ie,
                        ie_indicador_nfe, email,telefone,logradouro, numero,complemento, bairro,
                                  cep, codigo_municipio, nome_municipio, uf, codigo_uf, codigo_pais, nome_pais, data_cadastro,
                        data_atualizacao,created_by_user_id)
            VALUES (:cliente_id, :tipo_pessoa, :nome_razao_social, :cpf_cnpj, :ie,
                        :ie_indicador_nfe, :email, :telefone, :logradouro, :numero,
                        :complemento, :bairro, :cep, :codigo_municipio, :nome_municipio,
                        :uf, :codigo_uf, :codigo_pais, :nome_pais, :data_cadastro, :data_atualizacao, created_by_user_id)
                        
                        
        """), data)
        db.commit()
        flash('Destinatário salvo', 'success')
        cliente_id = request.form.get('cliente_id')
        return redirect(url_for('admin.list_destinatarios', cliente_id=cliente_id))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro salvar_destinatario: {e}")
        flash('Erro ao salvar destinatário', 'error')
        cliente_id = request.form.get('cliente_id')
        return redirect(url_for('admin.list_destinatarios', cliente_id=cliente_id))
    finally:
        db.close()

@admin_bp.route('/destinatarios/<int:destinatario_id>/edit')
@login_required
@permission_required('destinatarios_nfe.edit')
def edit_destinatario(destinatario_id: int):
    db = _get_db()
    try:
        row = db.execute(text("""
            SELECT cliente_id, nome_razao_social, cpf_cnpj, ie, ie_indicador_nfe
                              email, telefone, logradouro, numero, complemento, bairro,
                   cep, codigo_municipio, nome_municipio, uf, codigo_uf, codigo_pais, nome_pais,
                              data_cadastro, data_atualizacao, created_by_user_id
            FROM destinatarios_nfe
            WHERE destinatario_id = :cid
        """), {'cid': destinatario_id}).fetchone()
        destinatario = _safe_row_to_dict(row, [
            'cliente_id', 'nome_razao_social', 'cpf_cnpj', 'ie', 'ie_indicador_nfe'
                              'email', 'telefone', 'logradouro', 'numero', 'complemento', 'bairro',
                   'cep', 'codigo_municipio', 'nome_municipio', 'uf', 'codigo_uf', 'codigo_pais', 'nome_pais',
                              'data_cadastro', 'data_atualizacao', 'created_by_user_id'
        ])
        if not destinatario:
            flash('Destinatário não encontrado', 'warning')
            return redirect(url_for('admin.list_destinatarios'))
        return render_template('admin/destinatarios/form.html', destinatario=destinatario)
    except Exception as e:
        print(f"❌ Erro edit_destinatario: {e}")
        flash('Erro ao carregar destinatário', 'error')
        return redirect(url_for('admin.list_destinatarios'))
    finally:
        db.close()

# -------------------------------------------------------------------
# CERTIFICADOS
# -------------------------------------------------------------------

@admin_bp.route('/certificados')
@login_required
@permission_required('certificados.view')
def list_certificados():
    db = _get_db()
    cliente_id = request.args.get('cliente_id') or session.get('current_client_id') or session.get('active_cliente_id')
    cliente_nome = None
    try:
        if not cliente_id:
            flash('Selecione um cliente para visualizar os certificados.', 'warning')
            return render_template('admin/certificados/list.html', certificados=[], cliente_id=None, cliente_nome=None)
        row_cliente = db.execute(text("SELECT razao_social FROM clientes WHERE cliente_id = :cid"), {'cid': cliente_id}).fetchone()
        cliente_nome = row_cliente[0] if row_cliente else 'Cliente'
        rows = db.execute(text("""
            SELECT certificado_digital_id, fingerprint, conteudo_certificado, validade_fim, ativo, nome_arquivo_original, data_upload
            FROM certificados_digitais
            WHERE cliente_id = :cid
            ORDER BY certificado_digital_id DESC
        """), {'cid': cliente_id}).fetchall()
        certificados = [_safe_row_to_dict(r, [
            'certificado_digital_id','fingerprint','conteudo_certificado','validade_fim','ativo','nome_arquivo_original','data_upload'
        ]) for r in rows]
        return render_template('admin/certificados/list.html', certificados=certificados, cliente_id=cliente_id, cliente_nome=cliente_nome)
    except Exception as e:
        print(f"❌ Erro list_certificados: {e}")
        flash('Erro ao carregar certificados', 'error')
        return render_template('admin/certificados/list.html', certificados=[], cliente_id=cliente_id, cliente_nome=cliente_nome)
    finally:
        db.close()

@admin_bp.route('/certificados/salvar', methods=['POST'])
@login_required
@permission_required('certificados.create')
def salvar_certificado():
    db = _get_db()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    cliente_id = None  # Initialize to avoid "possibly unbound" error
    
    try:
        # Debug: imprimir todos os dados recebidos
        print(f"[DEBUG] Form data: {dict(request.form)}")
        print(f"[DEBUG] Files: {dict(request.files)}")
        print(f"[DEBUG] Referrer: {request.referrer}")
        
        # Obter cliente_id do form, args ou referrer
        cliente_id = request.form.get('cliente_id')
        if not cliente_id or cliente_id == '':
            # Tentar pegar do referrer URL (ex: /admin/clientes/11/edit)
            if request.referrer:
                import re
                match = re.search(r'/clientes/(\d+)/', request.referrer)
                if match:
                    cliente_id = match.group(1)
                    print(f"[DEBUG] Cliente ID extraído do referrer: {cliente_id}")
        
        if not cliente_id or cliente_id == '':
            raise Exception(f"Cliente ID não fornecido. Form keys: {list(request.form.keys())}, Referrer: {request.referrer}")
        
        # Convert to int to validate
        try:
            cliente_id = int(cliente_id)
        except (ValueError, TypeError):
            raise Exception(f"Cliente ID inválido: '{cliente_id}'")
            
        # Suporta ambos os formatos de formulário (antigo e novo)
        cert_file = request.files.get('conteudo_certificado_file') or request.files.get('arquivo_certificado')
        cert_senha = request.form.get('cert_senha_certificado') or request.form.get('senha_certificado')
        cert_ativo = request.form.get('cert_ativo') == 'on'
        cert_nome_arquivo = request.form.get('cert_nome_arquivo_original', 'Upload via Modal')
        
        if not cert_file or not cert_file.filename:
            raise Exception("Arquivo de certificado não fornecido")
        
        # Ler conteúdo do arquivo
        conteudo_certificado = cert_file.read()
        senha_criptografada = _encrypt_password(cert_senha) if cert_senha else None
        nome_arquivo_original = cert_file.filename
        
        # Extrair fingerprint e validades do certificado
        fingerprint = None
        validade_inicio = None
        validade_fim = None
        
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography.hazmat.primitives import hashes
            
            # Carregar PKCS#12
            password_bytes = cert_senha.encode('utf-8') if cert_senha else None
            private_key, cert_x509_obj, additional_certificates = pkcs12.load_key_and_certificates(
                conteudo_certificado,
                password_bytes
            )
            
            cert_obj = cert_x509_obj
            if cert_obj is None and additional_certificates:
                cert_obj = additional_certificates[0]
            if cert_obj is None:
                raise Exception("Certificado X.509 não encontrado dentro do PKCS#12")
                
            fingerprint = cert_obj.fingerprint(hashes.SHA256()).hex()
            validade_inicio = getattr(cert_obj, "not_valid_before_utc", None)
            validade_fim = getattr(cert_obj, "not_valid_after_utc", None)
            
        except Exception as e:
            print(f"⚠️ Aviso ao extrair dados do certificado: {e}")
            # Continua mesmo sem extrair os dados (melhor do que falhar)
        
        # Converter conteúdo para base64
        import base64
        conteudo_certificado_b64 = base64.b64encode(conteudo_certificado).decode('utf-8')
        
        # Inserir no banco
        db.execute(text("""
            INSERT INTO certificados_digitais (
                cliente_id, conteudo_certificado, senha_certificado, ativo, data_upload,
                nome_arquivo_original, created_by_user_id, fingerprint, validade_inicio, validade_fim
            ) VALUES (
                :cliente_id, :conteudo_certificado, :senha_certificado, :ativo, NOW(),
                :nome_arquivo_original, :created_by_user_id, :fingerprint, :validade_inicio, :validade_fim
            )
        """), {
            'cliente_id': cliente_id,
            'conteudo_certificado': conteudo_certificado_b64,
            'senha_certificado': senha_criptografada,
            'ativo': cert_ativo,
            'nome_arquivo_original': nome_arquivo_original,
            'created_by_user_id': current_user.id,
            'fingerprint': fingerprint,
            'validade_inicio': validade_inicio,
            'validade_fim': validade_fim
        })
        db.commit()
        
        # Se for requisição AJAX, retorna JSON
        if is_ajax:
            return jsonify({
                'success': True,
                'message': 'Certificado salvo com sucesso!',
                'redirect_url': url_for('admin.edit_cliente', cliente_id=cliente_id) + '#certificados'
            })
        
        # Senão, redirect tradicional
        flash('Certificado salvo com sucesso!', 'success')
        return redirect(url_for('admin.edit_cliente', cliente_id=cliente_id))
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro salvar_certificado: {e}")
        import traceback
        traceback.print_exc()
        
        # Se for requisição AJAX, retorna JSON com erro
        if is_ajax:
            return jsonify({
                'success': False,
                'message': f'Erro ao salvar certificado: {str(e)}'
            }), 500
        
        # Senão, redirect com flash
        flash(f'Erro ao salvar certificado: {str(e)}', 'error')
        # Se cliente_id foi obtido, redireciona para o cliente, senão para lista
        if cliente_id:
            return redirect(url_for('admin.edit_cliente', cliente_id=cliente_id))
        else:
            return redirect(url_for('admin.list_clientes'))
        
    finally:
        db.close()

@admin_bp.route('/certificados/<int:certificado_id>/toggle-status', methods=['POST'])
@login_required
@permission_required('certificados.edit')
def toggle_certificado_status(certificado_id: int):
    db = _get_db()
    try:
        row = db.execute(text("SELECT ativo FROM certificados WHERE certificado_id=:cid"),
                         {'cid': certificado_id}).fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Não encontrado'}), 404
        ativo_atual = row[0]
        db.execute(text("""
            UPDATE certificados SET ativo = :novo WHERE certificado_id=:cid
        """), {'novo': not ativo_atual, 'cid': certificado_id})
        db.commit()
        return jsonify({'success': True, 'ativo': not ativo_atual})
    except Exception as e:
        db.rollback()
        print(f"❌ Erro toggle_certificado_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

# -------------------------------------------------------------------
# REGRAS TRIBUTAÇÃO
# -------------------------------------------------------------------

@admin_bp.route('/regras-tributacao')
@login_required
@permission_required('regras_tributacao.view')
def list_regras_tributacao():
    db = _get_db()
    cliente_id = request.args.get('cliente_id') or session.get('current_client_id') or session.get('active_cliente_id')
    try:
        if not cliente_id:
            flash('Selecione um cliente para visualizar as regras tributárias.', 'warning')
            return render_template('admin/regras_tributacao/list.html', regras=[], cliente_id=None)
        
        # Query com JOIN para trazer dados completos de CFOP e NCM
        rows = db.execute(text("""
            SELECT 
                rt.regra_tributacao_id, rt.cliente_id, rt.cfop_id, rt.ncm_id, 
                rt.uf_origem, rt.uf_destino, rt.tipo_item, rt.prioridade, 
                rt.cst_icms, rt.csosn_icms, rt.aliquota_icms, rt.reducao_base_icms, 
                rt.modalidade_bc_icms, rt.motivo_desoneracao_icms, 
                rt.cst_pis, rt.aliquota_pis, rt.cst_cofins, rt.aliquota_cofins, 
                rt.cst_ipi, rt.aliquota_ipi, rt.descricao_regra, rt.data_criacao, rt.ativo,
                cf.cfop as cfop_codigo, cf.descricao as cfop_descricao,
                nc.codigo as ncm_codigo, nc.descricao as ncm_descricao
            FROM regras_tributacao rt
            LEFT JOIN cfops cf ON rt.cfop_id = cf.cfop_id
            LEFT JOIN ncms nc ON rt.ncm_id = nc.ncm_id
            WHERE rt.cliente_id = :cid
            ORDER BY rt.regra_tributacao_id DESC            
        """), {'cid': cliente_id}).fetchall()
        
        regras = [dict(r._mapping) for r in rows]
        return render_template('admin/regras_tributacao/list.html', regras=regras, cliente_id=cliente_id)
    except Exception as e:
        print(f"❌ Erro list_regras_tributacao: {e}")
        flash('Erro ao carregar regras', 'error')
        return render_template('admin/regras_tributacao/list.html', regras=[])
    finally:
        db.close()

@admin_bp.route('/regras-tributacao/nova')
@login_required
@permission_required('regras_tributacao.create')
def nova_regra_tributacao():
    db = _get_db()
    try:
        # Buscar todos os CFOPs
        cfop_rows = db.execute(text("""
            SELECT cfop_id, cfop, descricao FROM cfops ORDER BY cfop
        """)).fetchall()
        cfops = [dict(row._mapping) for row in cfop_rows]
        
        # Buscar todos os NCMs
        ncm_rows = db.execute(text("""
            SELECT ncm_id, codigo, descricao FROM ncms ORDER BY codigo
        """)).fetchall()
        ncms = [dict(row._mapping) for row in ncm_rows]
        
        cliente_id = request.args.get('cliente_id') or session.get('current_client_id') or session.get('active_cliente_id')
        
        return render_template('admin/regras_tributacao/form.html', 
                             regra=None, 
                             cfops=cfops, 
                             ncms=ncms,
                             cliente_id=cliente_id)
    finally:
        db.close()

@admin_bp.route('/regras-tributacao/salvar', methods=['POST'])
@login_required
@permission_required('regras_tributacao.create')
def salvar_regra_tributacao():
    db = _get_db()
    try:
        regra_id = request.form.get('regra_tributacao_id')
        cliente_id = request.form.get('cliente_id')
        
        # Função auxiliar para converter valores vazios em None
        def get_or_none(field, convert_to=None):
            val = request.form.get(field)
            if val is None or val == '':
                return None
            try:
                if convert_to == int:
                    return int(val)
                elif convert_to == float:
                    return float(val)
                elif convert_to == str:
                    return str(val)
                return str(val)
            except:
                return None
        
        # Montar dados
        data = {
            'cliente_id': cliente_id,
            'regime_tributario_id': get_or_none('regime_tributario_id', int) or 1,  # Default: Simples Nacional
            'cfop_id': get_or_none('cfop_id', int),
            'ncm_id': get_or_none('ncm_id', int),
            'uf_origem': get_or_none('uf_origem', str),
            'uf_destino': get_or_none('uf_destino', str),
            'tipo_item': get_or_none('tipo_item', str),
            'prioridade': get_or_none('prioridade', int) or 100,
            'cst_icms': get_or_none('cst_icms', str),
            'csosn_icms': get_or_none('csosn_icms', str),
            'aliquota_icms': get_or_none('aliquota_icms', float),
            'reducao_base_icms': get_or_none('reducao_base_icms', float),
            'modalidade_bc_icms': get_or_none('modalidade_bc_icms', int),
            'motivo_desoneracao_icms': get_or_none('motivo_desoneracao_icms', int),
            'cst_pis': get_or_none('cst_pis', str),
            'aliquota_pis': get_or_none('aliquota_pis', float),
            'cst_cofins': get_or_none('cst_cofins', str),
            'aliquota_cofins': get_or_none('aliquota_cofins', float),
            'cst_ipi': get_or_none('cst_ipi', str),
            'aliquota_ipi': get_or_none('aliquota_ipi', float),
            'descricao_regra': get_or_none('descricao_regra', str),
            'ativo': True
        }
        
        if regra_id:
            # Atualização
            data['regra_id'] = int(regra_id)
            db.execute(text("""
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
                    cst_cofins = :cst_cofins,
                    aliquota_cofins = :aliquota_cofins,
                    cst_ipi = :cst_ipi,
                    aliquota_ipi = :aliquota_ipi,
                    descricao_regra = :descricao_regra,
                    ativo = :ativo
                WHERE regra_tributacao_id = :regra_id
            """), data)
            flash('Regra atualizada com sucesso!', 'success')
        else:
            # Inserção
            db.execute(text("""
                INSERT INTO regras_tributacao (
                    cliente_id, regime_tributario_id, cfop_id, ncm_id, uf_origem, uf_destino, 
                    tipo_item, prioridade, cst_icms, csosn_icms, aliquota_icms, 
                    reducao_base_icms, modalidade_bc_icms, motivo_desoneracao_icms,
                    cst_pis, aliquota_pis, cst_cofins, aliquota_cofins, 
                    cst_ipi, aliquota_ipi, descricao_regra, ativo
                ) VALUES (
                    :cliente_id, :regime_tributario_id, :cfop_id, :ncm_id, :uf_origem, :uf_destino,
                    :tipo_item, :prioridade, :cst_icms, :csosn_icms, :aliquota_icms,
                    :reducao_base_icms, :modalidade_bc_icms, :motivo_desoneracao_icms,
                    :cst_pis, :aliquota_pis, :cst_cofins, :aliquota_cofins,
                    :cst_ipi, :aliquota_ipi, :descricao_regra, :ativo
                )
            """), data)
            flash('Regra criada com sucesso!', 'success')
        
        db.commit()
        return redirect(url_for('admin.list_regras_tributacao', cliente_id=cliente_id))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro salvar_regra_tributacao: {e}")
        flash('Erro ao salvar regra de tributação', 'error')
        return redirect(url_for('admin.nova_regra_tributacao'))
    finally:
        db.close()

@admin_bp.route('/regras-tributacao/excluir/<int:regra_id>', methods=['POST'])
@login_required
@permission_required('regras_tributacao.delete')
def excluir_regra_tributacao(regra_id: int):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM regras_tributacao WHERE regra_tributacao_id=:rid"),
                   {'rid': regra_id})
        db.commit()
        flash('Regra excluída', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro excluir_regra_tributacao: {e}")
        flash('Erro ao excluir regra', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_regras_tributacao'))

@admin_bp.route('/perfil')
@login_required
def perfil():
    db = _get_db()
    try:
        # Busca dados do usuário logado
        row = db.execute(text("""
            SELECT id, username, email, _is_active, created_at
            FROM users
            WHERE id = :id
        """), {'id': current_user.id}).fetchone()
        usuario = dict(row._mapping) if row else None

        # Busca roles do usuário
        roles = db.execute(text("""
            SELECT r.name
            FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = :id
        """), {'id': current_user.id}).fetchall()
        usuario_roles = [r[0] for r in roles]

        # Busca clientes do usuário
        clientes = db.execute(text("""
            SELECT c.cliente_id, c.razao_social
            FROM clientes c
            JOIN user_clients uc ON uc.client_id = c.cliente_id
            WHERE uc.user_id = :id
        """), {'id': current_user.id}).fetchall()
        usuario_clientes = [dict(row._mapping) for row in clientes]

        return render_template(
            'admin/perfil.html',
            usuario=usuario,
            usuario_roles=usuario_roles,
            usuario_clientes=usuario_clientes
        )
    except Exception as e:
        print(f"❌ Erro perfil: {e}")
        flash('Erro ao carregar perfil', 'error')
        return render_template('admin/perfil.html', usuario=None, usuario_roles=[], usuario_clientes=[])
    finally:
        db.close()

# -------------------------------------------------------------------
# BUSCAR CEP
# -------------------------------------------------------------------

@admin_bp.route('/api/buscar-cep/<cep>')
@login_required
def buscar_cep(cep: str):
    """Busca informações de endereço via API ViaCEP"""
    import requests
    from os import environ
    
    try:
        # Remove caracteres não numéricos
        cep_limpo = ''.join(filter(str.isdigit, cep))
        
        if len(cep_limpo) != 8:
            return jsonify({
                'success': False,
                'error': 'CEP inválido. Deve conter 8 dígitos.'
            }), 400
        
        # Consulta API ViaCEP
        print(f"🔍 Buscando CEP: {cep_limpo}")
        print(f"🌐 Tentando conectar em: https://viacep.com.br/ws/{cep_limpo}/json/")
        
        try:
            response = requests.get(
                f'https://viacep.com.br/ws/{cep_limpo}/json/', 
                timeout=10,  # Aumentado para 10 segundos
                headers={'User-Agent': 'Mozilla/5.0'}  # Alguns servidores exigem User-Agent
            )
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Erro de conexão específico: {e}")
            
            # Modo fallback: tentar usar CEPs de teste
            try:
                from config.cep_config import get_cep_teste
                dados_teste = get_cep_teste(cep_limpo)
                
                if dados_teste:
                    print(f"⚠️ MODO OFFLINE: Usando CEP de teste para {cep_limpo}")
                    # Continua o fluxo normal com dados de teste
                    dados = dados_teste
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Sem conexão com internet e CEP não está nos dados de teste.',
                        'details': f'CEPs de teste disponíveis: 01310-100, 20040-020, 30130-100, 40020-000, 80010-000'
                    }), 503
            except ImportError:
                return jsonify({
                    'success': False,
                    'error': 'Não foi possível conectar ao serviço ViaCEP. Verifique sua conexão com a internet.',
                    'details': 'ConnectionError - Verifique se você está conectado à internet e se não há firewall bloqueando.'
                }), 503
        else:
            # Conexão bem-sucedida com ViaCEP
            if response.status_code != 200:
                print(f"⚠️ Status HTTP: {response.status_code}")
                return jsonify({
                    'success': False,
                    'error': f'Erro ao consultar CEP (HTTP {response.status_code}). Tente novamente.'
                }), 500
            
            dados = response.json()
            
            # ViaCEP retorna {"erro": true} quando CEP não existe
            if dados.get('erro'):
                return jsonify({
                    'success': False,
                    'error': 'CEP não encontrado.'
                }), 404
        
        # Buscar código IBGE do município no banco de dados
        db = _get_db()
        try:
            municipio_query = text("""
                SELECT codigo_municipio, nome_municipio, uf
                FROM municipios
                WHERE UPPER(nome_municipio) = UPPER(:nome)
                AND uf = :uf
                LIMIT 1
            """)
            
            municipio_row = db.execute(municipio_query, {
                'nome': dados.get('localidade', ''),
                'uf': dados.get('uf', '')
            }).fetchone()
            
            if municipio_row:
                codigo_municipio = municipio_row[0]
                nome_municipio = municipio_row[1]
            else:
                # Fallback: tentar buscar apenas por nome
                municipio_query_fallback = text("""
                    SELECT codigo_municipio, nome_municipio, uf
                    FROM municipios
                    WHERE UPPER(nome_municipio) LIKE UPPER(:nome)
                    AND uf = :uf
                    LIMIT 1
                """)
                
                municipio_row = db.execute(municipio_query_fallback, {
                    'nome': f"%{dados.get('localidade', '')}%",
                    'uf': dados.get('uf', '')
                }).fetchone()
                
                if municipio_row:
                    codigo_municipio = municipio_row[0]
                    nome_municipio = municipio_row[1]
                else:
                    # Se não encontrar, usar dados do ViaCEP mesmo
                    codigo_municipio = dados.get('ibge', '')
                    nome_municipio = dados.get('localidade', '')
                    print(f"⚠️ Município não encontrado no BD: {nome_municipio}/{dados.get('uf')}")
            
            # Buscar código UF
            codigo_uf = None
            try:
                uf_query = text("SELECT codigo_uf FROM estados WHERE uf = :uf LIMIT 1")
                uf_row = db.execute(uf_query, {'uf': dados.get('uf', '')}).fetchone()
                if uf_row:
                    codigo_uf = uf_row[0]
            except Exception as e_uf:
                print(f"⚠️ Erro ao buscar código UF no BD: {e_uf}")
            
            # Fallback: Mapeamento manual de UF para código IBGE
            if not codigo_uf:
                uf_map = {
                    'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29',
                    'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
                    'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
                    'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
                    'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
                    'SE': '28', 'TO': '17'
                }
                codigo_uf = uf_map.get(dados.get('uf', ''))
                if codigo_uf:
                    print(f"ℹ️ Usando código UF do mapeamento: {dados.get('uf')} = {codigo_uf}")
            
        except Exception as e:
            print(f"⚠️ Erro ao buscar município no BD: {e}")
            codigo_municipio = dados.get('ibge', '')
            nome_municipio = dados.get('localidade', '')
            # Fallback final para código UF
            uf_map = {
                'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29',
                'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
                'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
                'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
                'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
                'SE': '28', 'TO': '17'
            }
            codigo_uf = uf_map.get(dados.get('uf', ''))
        finally:
            db.close()
        
        print(f"✅ CEP encontrado: {dados.get('logradouro')}, {nome_municipio}/{dados.get('uf')}")
        
        # Garantir que codigo_uf não seja None (campo obrigatório no banco)
        if not codigo_uf:
            print(f"⚠️ AVISO: codigo_uf não encontrado para UF={dados.get('uf')}. Usando código padrão '99'")
            codigo_uf = '99'  # Código genérico de fallback
        
        # Retornar dados formatados
        return jsonify({
            'success': True,
            'cep': cep_limpo,
            'logradouro': dados.get('logradouro', ''),
            'complemento': dados.get('complemento', ''),
            'bairro': dados.get('bairro', ''),
            'nome_municipio': nome_municipio,
            'codigo_municipio': codigo_municipio,
            'uf': dados.get('uf', ''),
            'codigo_uf': codigo_uf,
            'ddd': dados.get('ddd', '')
        }), 200
        
    except requests.Timeout:
        print(f"⏱️ Timeout ao buscar CEP: {cep}")
        return jsonify({
            'success': False,
            'error': 'Tempo esgotado ao consultar CEP (10 segundos). O serviço pode estar lento.',
            'details': 'Timeout - Tente novamente em alguns instantes.'
        }), 504
        
    except requests.RequestException as e:
        print(f"❌ Erro de conexão ao buscar CEP: {e}")
        print(f"❌ Tipo de erro: {type(e).__name__}")
        
        # Mensagem detalhada baseada no tipo de erro
        error_msg = 'Erro de conexão com o serviço de CEP.'
        details = str(e)
        
        if 'ConnectionError' in str(type(e).__name__):
            error_msg = 'Sem conexão com a internet ou serviço ViaCEP indisponível.'
            details = 'Verifique: 1) Conexão Wi-Fi/Ethernet, 2) Firewall, 3) Status do ViaCEP'
        elif 'SSLError' in str(type(e).__name__):
            error_msg = 'Erro de certificado SSL ao conectar com ViaCEP.'
            details = 'Problema de segurança na conexão. Verifique certificados do sistema.'
        
        return jsonify({
            'success': False,
            'error': error_msg,
            'details': details
        }), 503
        
    except Exception as e:
        print(f"❌ Erro inesperado ao buscar CEP: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Erro ao buscar CEP: {str(e)}',
            'details': 'Erro interno do servidor. Verifique os logs.'
        }), 500

# -------------------------------------------------------------------
# HEALTH
# -------------------------------------------------------------------

@admin_bp.route('/health')
def admin_health():
    return jsonify({'status': 'ok', 'role': getattr(current_user, 'role', None)})

# Endpoint para sugestão IA integrada (NCM + LLM) - USA API UNIFICADA
@admin_bp.route('/api/sugestao_tributaria', methods=['POST'])
@login_required
def api_sugestao_tributaria():
    """
    Endpoint que chama a API IA Unificada (porta 9000) e converte
    códigos para IDs do banco de dados para preenchimento automático
    """
    import requests as req_lib
    
    # Recebe dados do formulário via JSON
    dados = request.get_json()
    print(f"[IA] 🎯 Nova solicitação de sugestão: {dados.get('descricao', 'N/A')}")
    
    # Validação básica
    if not dados.get('descricao'):
        return jsonify({'erro': 'Descrição do produto é obrigatória'}), 400
    
    db = _get_db()
    
    try:
        # Enriquece dados com informações do cliente se disponível
        cliente_id = dados.get('cliente_id')
        if cliente_id:
            # Busca informações do cliente
            cliente_row = db.execute(text("""
                SELECT c.uf, c.regime_tributario_id, rt.nome as regime_nome
                FROM clientes c
                LEFT JOIN regimes_tributarios rt ON c.regime_tributario_id = rt.regime_tributario_id
                WHERE c.cliente_id = :cliente_id
            """), {'cliente_id': cliente_id}).fetchone()
            
            if cliente_row:
                cliente = dict(cliente_row._mapping)
                dados['uf_origem'] = cliente.get('uf')
                dados['regime_tributario'] = cliente.get('regime_nome')
                print(f"[IA] 📍 Contexto cliente: UF={cliente.get('uf')}, Regime={cliente.get('regime_nome')}")
        
        # Chama API IA Unificada (porta 9000)
        print(f"[IA] 🤖 Chamando API IA Unificada...")
        api_response = req_lib.post(
            'http://localhost:9000/api/sugestao',
            json={
                'descricao': dados.get('descricao'),
                'tipo_item': dados.get('tipo_item', 'Produto'),
                'uf_origem': dados.get('uf_origem'),
                'regime_tributario': dados.get('regime_tributario'),
                'unidade_comercial': dados.get('unidade_comercial', 'UN'),
                'codigo_interno': dados.get('codigo_interno'),
                'cliente_id': cliente_id
            },
            timeout=30
        )
        
        if api_response.status_code != 200:
            print(f"[IA] ❌ Erro na API: {api_response.status_code}")
            return jsonify({'erro': 'Erro ao consultar API de IA'}), 500
        
        resultado_api = api_response.json()
        
        if not resultado_api.get('success'):
            print(f"[IA] ❌ API retornou erro: {resultado_api.get('erro')}")
            return jsonify(resultado_api), 500
        
        classificacao = resultado_api.get('classificacao', {})
        print(f"[IA] ✅ Classificação recebida: NCM={classificacao.get('ncm')}")
        
        # Converte códigos para IDs do banco de dados
        resultado_final = {
            'sucesso': True,
            'classificacao': classificacao,
            'ids': {}  # IDs para preencher os selects
        }
        
        # Busca NCM_ID pelo código
        if classificacao.get('ncm'):
            ncm_codigo = classificacao['ncm'].replace('.', '')  # Remove pontos
            ncm_row = db.execute(text("""
                SELECT ncm_id, codigo, descricao 
                FROM ncms 
                WHERE REPLACE(codigo, '.', '') = :codigo
                LIMIT 1
            """), {'codigo': ncm_codigo}).fetchone()
            
            if ncm_row:
                ncm = dict(ncm_row._mapping)
                resultado_final['ids']['ncm_id'] = ncm['ncm_id']
                resultado_final['ncm_descricao'] = ncm['descricao']
                print(f"[IA] ✅ NCM encontrado: {ncm['codigo']} (ID: {ncm['ncm_id']})")
            else:
                print(f"[IA] ⚠️ NCM {ncm_codigo} não encontrado no banco")
        
        # Busca CFOP_ID pelo código
        if classificacao.get('cfop'):
            cfop_codigo = classificacao['cfop']
            # Tenta com e sem pontos (ex: "5101" ou "5.101")
            cfop_row = db.execute(text("""
                SELECT cfop_id, cfop, descricao 
                FROM cfops 
                WHERE REPLACE(cfop, '.', '') = :cfop OR cfop = :cfop
                LIMIT 1
            """), {'cfop': cfop_codigo}).fetchone()
            
            if cfop_row:
                cfop = dict(cfop_row._mapping)
                resultado_final['ids']['cfop_id'] = cfop['cfop_id']
                resultado_final['cfop_descricao'] = cfop['descricao']
                print(f"[IA] ✅ CFOP encontrado: {cfop['cfop']} (ID: {cfop['cfop_id']})")
            else:
                print(f"[IA] ⚠️ CFOP {cfop_codigo} não encontrado no banco")
        
        # Busca CST_ID pelo código (se aplicável)
        if classificacao.get('cst'):
            cst_codigo = classificacao['cst']
            cst_row = db.execute(text("""
                SELECT cst_id, codigo, descricao 
                FROM cst_icms 
                WHERE codigo = :cst
                LIMIT 1
            """), {'cst': cst_codigo}).fetchone()
            
            if cst_row:
                cst = dict(cst_row._mapping)
                resultado_final['ids']['cst_id'] = cst['cst_id']
                resultado_final['cst_descricao'] = cst['descricao']
                print(f"[IA] ✅ CST encontrado: {cst['codigo']} (ID: {cst['cst_id']})")
        
        # Busca CSOSN_ID pelo código (se aplicável)
        if classificacao.get('csosn'):
            csosn_codigo = classificacao['csosn']
            csosn_row = db.execute(text("""
                SELECT csosn_id, codigo, descricao 
                FROM csosn_icms 
                WHERE codigo = :csosn
                LIMIT 1
            """), {'csosn': csosn_codigo}).fetchone()
            
            if csosn_row:
                csosn = dict(csosn_row._mapping)
                resultado_final['ids']['csosn_id'] = csosn['csosn_id']
                resultado_final['csosn_descricao'] = csosn['descricao']
                print(f"[IA] ✅ CSOSN encontrado: {csosn['codigo']} (ID: {csosn['csosn_id']})")
        
        # CEST é campo texto livre (não tem tabela de IDs)
        if classificacao.get('cest'):
            resultado_final['ids']['cest'] = classificacao['cest']
            print(f"[IA] ✅ CEST recebido: {classificacao['cest']}")
        else:
            print(f"[IA] ℹ️  CEST não informado (opcional)")
        
        print(f"[IA] 🎉 Resultado final preparado com IDs do banco")
        return jsonify(resultado_final)
        
    except req_lib.exceptions.RequestException as e:
        print(f"[IA] ❌ Erro ao conectar com API IA: {e}")
        return jsonify({
            'erro': 'API de IA não está disponível. Certifique-se de que está rodando na porta 9000.',
            'detalhes': str(e)
        }), 503
        
    except Exception as e:
        print(f"[IA] ❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro no processamento: {str(e)}'}), 500
        
    finally:
        db.close()

# Endpoint para obter informações do cliente (regime tributário, etc.)
@admin_bp.route('/api/cliente/<int:cliente_id>/info', methods=['GET'])
@login_required
def api_cliente_info(cliente_id):
    """Retorna informações do cliente para ajustar interface dinamicamente"""
    db = _get_db()
    try:
        # Busca informações do cliente
        cliente_row = db.execute(text("""
            SELECT c.cliente_id, c.razao_social, c.uf, c.regime_tributario_id, 
                   rt.nome as regime_nome
            FROM clientes c
            LEFT JOIN regimes_tributarios rt ON c.regime_tributario_id = rt.regime_tributario_id
            WHERE c.cliente_id = :cliente_id
        """), {'cliente_id': cliente_id}).fetchone()
        
        if not cliente_row:
            return jsonify({'erro': 'Cliente não encontrado'}), 404
            
        cliente = dict(cliente_row._mapping)
        
        # Determina se é Simples Nacional
        regime_nome = cliente.get('regime_nome', '').lower()
        is_simples_nacional = 'simples' in regime_nome
        
        return jsonify({
            'cliente_id': cliente['cliente_id'],
            'razao_social': cliente['razao_social'],
            'uf': cliente['uf'],
            'regime_tributario_id': cliente['regime_tributario_id'],
            'regime_nome': cliente['regime_nome'],
            'is_simples_nacional': is_simples_nacional,
            'mostrar_cst': not is_simples_nacional,
            'mostrar_csosn': is_simples_nacional
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar dados do cliente: {e}")
        return jsonify({'erro': 'Erro interno do servidor'}), 500
    finally:
        db.close()

# Rota de teste para preenchimento automático
@admin_bp.route('/teste-preenchimento-ia')
@login_required
def teste_preenchimento_ia():
    """Página de teste para verificar preenchimento automático dos campos"""
    return render_template('teste_preenchimento_ia.html')

# Rota de teste para Select NCM
@admin_bp.route('/teste-select-ncm')
@login_required
def teste_select_ncm():
    """Página de teste para verificar funcionamento do Select2 de NCMs"""
    return render_template('teste_select_ncm.html')


# -------------------------------------------------------------------
# AUDITORIA E LOGS (FASE 4)
# -------------------------------------------------------------------

@admin_bp.route('/auditoria')
@login_required
@permission_required('admin.view')
def list_auditoria():
    """Lista logs de auditoria com filtros"""
    from services.auditoria_service import AuditoriaService
    
    try:
        # Parâmetros de filtro
        user_id = request.args.get('user_id', type=int)
        acao = request.args.get('acao', type=str)
        tabela_afetada = request.args.get('tabela', type=str)
        data_inicio_str = request.args.get('data_inicio')
        data_fim_str = request.args.get('data_fim')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Converte datas
        data_inicio = None
        data_fim = None
        if data_inicio_str:
            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            except ValueError:
                flash('Data inicial inválida', 'warning')
        
        if data_fim_str:
            try:
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d')
                # Adiciona 23:59:59 para incluir todo o dia
                from datetime import timedelta
                data_fim = data_fim + timedelta(hours=23, minutes=59, seconds=59)
            except ValueError:
                flash('Data final inválida', 'warning')
        
        # Busca logs
        offset = (page - 1) * per_page
        logs, total = AuditoriaService.obter_logs(
            user_id=user_id,
            acao=acao,
            tabela_afetada=tabela_afetada,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=per_page,
            offset=offset
        )
        
        # Calcula paginação
        total_pages = (total + per_page - 1) // per_page
        
        # Busca lista de usuários para o filtro
        db = _get_db()
        try:
            query_users = text("""
                SELECT id, username
                FROM users
                ORDER BY username
            """)
            usuarios = [{'id': row[0], 'username': row[1]} for row in db.execute(query_users)]
        finally:
            db.close()
        
        # Lista de ações disponíveis
        acoes_disponiveis = ['LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGOUT', 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 'ACCESS']
        
        # Lista de tabelas disponíveis
        tabelas_disponiveis = ['produtos', 'nfe_emitidas', 'clientes', 'users', 'certificados', 'destinatarios', 'regras_tributacao']
        
        return render_template('admin/auditoria/list.html',
                             logs=logs,
                             total=total,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             usuarios=usuarios,
                             acoes_disponiveis=acoes_disponiveis,
                             tabelas_disponiveis=tabelas_disponiveis,
                             filtros={
                                 'user_id': user_id,
                                 'acao': acao,
                                 'tabela': tabela_afetada,
                                 'data_inicio': data_inicio_str,
                                 'data_fim': data_fim_str
                             })
    
    except Exception as e:
        print(f"❌ Erro ao listar auditoria: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar logs de auditoria', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/auditoria/estatisticas')
@login_required
@permission_required('admin.view')
def estatisticas_auditoria():
    """Exibe estatísticas de auditoria"""
    from services.auditoria_service import AuditoriaService
    
    try:
        dias = request.args.get('dias', 30, type=int)
        stats = AuditoriaService.obter_estatisticas_auditoria(dias=dias)
        
        return render_template('admin/auditoria/estatisticas.html',
                             stats=stats,
                             dias=dias)
    
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar estatísticas', 'danger')
        return redirect(url_for('admin.list_auditoria'))


@admin_bp.route('/auditoria/export')
@login_required
@permission_required('admin.view')
def export_auditoria():
    """Exporta logs de auditoria para CSV ou XLSX"""
    from services.auditoria_service import AuditoriaService
    from io import BytesIO, StringIO
    from flask import make_response, send_file
    import csv
    
    try:
        # Parâmetros
        formato = request.args.get('formato', 'csv')  # csv ou xlsx
        user_id = request.args.get('user_id', type=int)
        acao = request.args.get('acao', type=str)
        tabela_afetada = request.args.get('tabela', type=str)
        data_inicio_str = request.args.get('data_inicio')
        data_fim_str = request.args.get('data_fim')
        
        # Converte datas
        data_inicio = None
        data_fim = None
        if data_inicio_str:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
        if data_fim_str:
            from datetime import timedelta
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d')
            data_fim = data_fim + timedelta(hours=23, minutes=59, seconds=59)
        
        # Busca todos os logs (sem limite)
        logs, total = AuditoriaService.obter_logs(
            user_id=user_id,
            acao=acao,
            tabela_afetada=tabela_afetada,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=10000,  # Limite máximo
            offset=0
        )
        
        if formato == 'csv':
            # Exporta como CSV
            si = StringIO()
            writer = csv.writer(si)
            
            # Cabeçalhos
            writer.writerow(['ID', 'Data/Hora', 'Usuário', 'Ação', 'Tabela', 'Registro ID', 'IP', 'Descrição'])
            
            # Dados
            for log in logs:
                writer.writerow([
                    log['auditoria_id'],
                    log['timestamp'].strftime('%d/%m/%Y %H:%M:%S') if log['timestamp'] else '',
                    log['username'],
                    log['acao'],
                    log['tabela_afetada'] or '',
                    log['registro_id'] or '',
                    log['ip_address'] or '',
                    log['descricao'] or ''
                ])
            
            output = make_response(si.getvalue())
            output.headers["Content-Disposition"] = f"attachment; filename=auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            output.headers["Content-type"] = "text/csv; charset=utf-8"
            return output
        
        elif formato == 'xlsx':
            # Exporta como XLSX
            try:
                import openpyxl
                from openpyxl import Workbook
                from openpyxl.styles import Font, PatternFill
            except ImportError:
                flash('Biblioteca openpyxl não instalada. Use formato CSV.', 'warning')
                return redirect(url_for('admin.list_auditoria'))
            
            wb = Workbook()
            ws = wb.active
            
            # Type guard para worksheet
            if ws is None:
                flash('Erro ao criar planilha XLSX.', 'error')
                return redirect(url_for('admin.list_auditoria'))
                
            ws.title = "Auditoria"
            
            # Cabeçalhos com estilo
            headers = ['ID', 'Data/Hora', 'Usuário', 'Ação', 'Tabela', 'Registro ID', 'IP', 'Descrição']
            ws.append(headers)
            
            # Estiliza cabeçalho (verifica se há linhas)
            try:
                for cell in ws[1]:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            except (IndexError, TypeError):
                pass  # Ignora se não houver linhas
            
            # Dados
            for log in logs:
                ws.append([
                    log['auditoria_id'],
                    log['timestamp'].strftime('%d/%m/%Y %H:%M:%S') if log['timestamp'] else '',
                    log['username'],
                    log['acao'],
                    log['tabela_afetada'] or '',
                    log['registro_id'] or '',
                    log['ip_address'] or '',
                    log['descricao'] or ''
                ])
            
            # Ajusta largura das colunas (type-safe)
            if hasattr(ws, 'column_dimensions'):
                ws.column_dimensions['A'].width = 8
                ws.column_dimensions['B'].width = 20
                ws.column_dimensions['C'].width = 15
                ws.column_dimensions['D'].width = 15
                ws.column_dimensions['E'].width = 20
                ws.column_dimensions['F'].width = 12
                ws.column_dimensions['G'].width = 15
                ws.column_dimensions['H'].width = 50
            
            # Salva em BytesIO
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'auditoria_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            )
        
        else:
            flash('Formato de exportação inválido', 'danger')
            return redirect(url_for('admin.list_auditoria'))
    
    except Exception as e:
        print(f"❌ Erro ao exportar auditoria: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao exportar logs', 'danger')
        return redirect(url_for('admin.list_auditoria'))


@admin_bp.route('/auditoria/<int:auditoria_id>')
@login_required
@permission_required('admin.view')
def view_auditoria(auditoria_id):
    """Visualiza detalhes de um log específico"""
    db = _get_db()
    try:
        query = text("""
            SELECT 
                a.auditoria_id,
                a.user_id,
                u.username,
                a.acao,
                a.tabela_afetada,
                a.registro_id,
                a.timestamp,
                a.dados_antes,
                a.dados_depois,
                a.ip_address,
                a.user_agent,
                a.descricao
            FROM auditoria a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.auditoria_id = :auditoria_id
        """)
        
        result = db.execute(query, {'auditoria_id': auditoria_id}).fetchone()
        
        if not result:
            flash('Log de auditoria não encontrado', 'warning')
            return redirect(url_for('admin.list_auditoria'))
        
        log = {
            'auditoria_id': result[0],
            'user_id': result[1],
            'username': result[2] or 'Sistema',
            'acao': result[3],
            'tabela_afetada': result[4],
            'registro_id': result[5],
            'timestamp': result[6],
            'dados_antes': result[7],
            'dados_depois': result[8],
            'ip_address': result[9],
            'user_agent': result[10],
            'descricao': result[11]
        }
        
        return render_template('admin/auditoria/view.html', log=log)
    
    except Exception as e:
        print(f"❌ Erro ao visualizar auditoria: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar detalhes do log', 'danger')
        return redirect(url_for('admin.list_auditoria'))
    finally:
        db.close()


@admin_bp.route('/auditoria/limpar', methods=['POST'])
@login_required
@permission_required('admin.manage')
def limpar_auditoria():
    """Limpa logs antigos de auditoria"""
    from services.auditoria_service import AuditoriaService
    
    try:
        dias = request.form.get('dias', 365, type=int)
        
        if dias < 90:
            flash('Não é permitido limpar logs com menos de 90 dias', 'warning')
            return redirect(url_for('admin.list_auditoria'))
        
        deletados = AuditoriaService.limpar_logs_antigos(dias=dias)
        
        flash(f'✅ {deletados} registros de auditoria removidos (mais de {dias} dias)', 'success')
        
        # Registra a ação de limpeza
        AuditoriaService.registrar_acao(
            user_id=current_user.id,
            acao='CLEANUP',
            tabela_afetada='auditoria',
            descricao=f'Limpeza de logs com mais de {dias} dias - {deletados} registros removidos'
        )
        
        return redirect(url_for('admin.list_auditoria'))
    
    except Exception as e:
        print(f"❌ Erro ao limpar auditoria: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao limpar logs antigos', 'danger')
        return redirect(url_for('admin.list_auditoria'))

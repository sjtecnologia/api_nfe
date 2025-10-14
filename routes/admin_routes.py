from __future__ import annotations
from typing import Optional, Dict, Any, List, Generator
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, session, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import text
from datetime import datetime
import sys
from pathlib import Path
import importlib

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

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

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

def _get_db():
    return next(get_db())

# -------------------------------------------------------------------
# DASHBOARD ADMIN
# -------------------------------------------------------------------

@admin_bp.route('/')
@login_required
def admin_home():
    db = None
    stats = {
        'total_clientes': 0,
        'total_nfes': 0,
        'nfes_ano': 0,
        'nfes_mes': 0
    }
    ultimas_nfes: List[Dict[str, Any]] = []
    ultimos_clientes: List[Dict[str, Any]] = []
    try:
        db = _get_db()

        # Total clientes (excluindo destinatários, ajuste se necessário)
        stats['total_clientes'] = db.execute(text("""
            SELECT COUNT(*) FROM clientes WHERE ativo = TRUE
        """)).scalar() or 0

        # Total NFes
        stats['total_nfes'] = db.execute(text("SELECT COUNT(*) FROM nfe_emitidas")).scalar() or 0

        ano_atual = datetime.now().year
        mes_atual = datetime.now().month

        stats['nfes_ano'] = db.execute(text("""
            SELECT COUNT(*) FROM nfe_emitidas
            WHERE EXTRACT(YEAR FROM data_criacao) = :ano
        """), {'ano': ano_atual}).scalar() or 0

        stats['nfes_mes'] = db.execute(text("""
            SELECT COUNT(*) FROM nfe_emitidas
            WHERE EXTRACT(YEAR FROM data_criacao) = :ano
              AND EXTRACT(MONTH FROM data_criacao) = :mes
        """), {'ano': ano_atual, 'mes': mes_atual}).scalar() or 0

        # Últimas NFes
        rows_nfe = db.execute(text("""
            SELECT nfe_emitida_id, status, data_criacao
            FROM nfe_emitidas
            ORDER BY nfe_emitida_id DESC
            LIMIT 10
        """)).fetchall()
        for r in rows_nfe:
            ultimas_nfes.append(_safe_row_to_dict(r, [
                'nfe_emitida_id','status','data_criacao'
            ]))

        # Últimos clientes
        rows_cli = db.execute(text("""
            SELECT cliente_id,
                   razao_social,
                   nome_fantasia,
                   cnpj AS cnpj,
                   data_cadastro AS data_cadastro
            FROM clientes
            WHERE ativo = TRUE
            ORDER BY cliente_id DESC
            LIMIT 8
        """)).fetchall()
        for r in rows_cli:
            ultimos_clientes.append(_safe_row_to_dict(r, [
                'cliente_id','razao_social','nome_fantasia','cnpj','data_cadastro'
            ]))

        return render_template('admin/dashboard.html',
                               stats=stats,
                               ultimas_nfes=ultimas_nfes,
                               ultimos_clientes=ultimos_clientes)
    except Exception as e:
        print(f"❌ Erro dashboard admin: {e}")
        flash('Erro ao carregar dashboard', 'error')
        return render_template('admin/dashboard.html',
                               stats=stats,
                               ultimas_nfes=ultimas_nfes,
                               ultimos_clientes=ultimos_clientes)
    finally:
        if db:
            db.close()

@admin_bp.route('/nfes')
@login_required
@permission_required('nfes.view')
def list_nfes():
    db = _get_db()
    q = request.args.get('q', '').strip()
    filtro = ""
    params = {}
    if q:
        filtro = """
            WHERE n.chave_acesso ILIKE :q
               OR n.destinatario_razao_social ILIKE :q
               OR n.destinatario_cnpj_cpf ILIKE :q
               OR c.razao_social ILIKE :q
               OR c.cnpj ILIKE :q
        """
        params['q'] = f'%{q}%'
    rows = db.execute(text(f"""
        SELECT n.nfe_emitida_id, n.cliente_id, n.chave_acesso, n.data_criacao, n.status,
               n.destinatario_razao_social, n.destinatario_cnpj_cpf,
               n.tipo_nfe, n.finalidade_emissao,
               c.razao_social, c.cnpj
        FROM nfe_emitidas n
        JOIN clientes c ON c.cliente_id = n.cliente_id
        {filtro}
        ORDER BY n.data_criacao DESC
        LIMIT 100
    """), params).fetchall()
    nfes = [dict(row._mapping) for row in rows]

    # Monta o cliente_map para o filtro e exibição
    clientes = db.execute(text("SELECT cliente_id, razao_social FROM clientes ORDER BY razao_social")).fetchall()
    cliente_map = {row.cliente_id: row.razao_social for row in clientes}

    cliente_id = request.args.get('cliente_id')

    return render_template(
        'admin/nfes/list.html',
        nfes=nfes,
        q=q,
        cliente_map=cliente_map,
        cliente_id=cliente_id
    )

@admin_bp.route('/ncms')
@login_required
def list_ncms():
    db = _get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(text("""
            SELECT ncm_id, codigo, descricao, data_inicio, data_fim, tipo_ato, numero_ato, ano_ato
            FROM ncms
            WHERE codigo ILIKE :q
               OR descricao ILIKE :q
               OR tipo_ato ILIKE :q
               OR numero_ato::text ILIKE :q
               OR ano_ato::text ILIKE :q
            ORDER BY codigo
        """), {'q': f'%{q}%'}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT ncm_id, codigo, descricao, data_inicio, data_fim, tipo_ato, numero_ato, ano_ato
            FROM ncms
            ORDER BY codigo
        """)).fetchall()
    ncms = [dict(row._mapping) for row in rows]
    return render_template('admin/ncms/list.html', ncms=ncms)

@admin_bp.route('/ncms/novo')
@login_required
@permission_required('ncms.create')
def create_ncm():
    return render_template('admin/ncms/form.html', ncm=None)

@admin_bp.route('/ncms/editar/<int:ncm_id>', methods=['GET', 'POST'])
@login_required
@permission_required('ncms.edit')
def edit_ncm(ncm_id):
    db = _get_db()
    if request.method == 'POST':
        # Recebe dados do formulário
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        data_inicio = request.form.get('data_inicio') or None
        data_fim = request.form.get('data_fim') or None
        tipo_ato = request.form.get('tipo_ato')
        numero_ato = request.form.get('numero_ato')
        ano_ato = request.form.get('ano_ato')
        try:
            db.execute(text("""
                UPDATE ncms SET
                    codigo = :codigo,
                    descricao = :descricao,
                    data_inicio = :data_inicio,
                    data_fim = :data_fim,
                    tipo_ato = :tipo_ato,
                    numero_ato = :numero_ato,
                    ano_ato = :ano_ato
                WHERE ncm_id = :ncm_id
            """), {
                'codigo': codigo,
                'descricao': descricao,
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'tipo_ato': tipo_ato,
                'numero_ato': numero_ato,
                'ano_ato': ano_ato,
                'ncm_id': ncm_id
            })
            db.commit()
            flash('NCM atualizado com sucesso!', 'success')
            return redirect(url_for('admin.list_ncms'))
        except Exception as e:
            db.rollback()
            flash('Erro ao atualizar NCM', 'danger')
    row = db.execute(text("SELECT ncm_id, codigo, descricao, data_inicio, data_fim, tipo_ato, numero_ato, ano_ato FROM ncms WHERE ncm_id = :id"), {'id': ncm_id}).fetchone()
    ncm = dict(row._mapping) if row else None
    return render_template('admin/ncms/form.html', ncm=ncm)

@admin_bp.route('/ncms/excluir/<int:ncm_id>', methods=['POST'])
@login_required
@permission_required('ncms.delete')
def delete_ncm(ncm_id):
    db = _get_db()
    try:
        db.execute(text("DELETE FROM ncms WHERE ncm_id = :id"), {'id': ncm_id})
        db.commit()
        flash('NCM excluído com sucesso', 'success')
    except Exception as e:
        db.rollback()
        print(f"❌ Erro delete_ncm: {e}")
        flash('Erro ao excluir NCM', 'error')
    finally:
        db.close()
    return redirect(url_for('admin.list_ncms'))        

@admin_bp.route('/cst')
@login_required
@permission_required('cst.view')
def list_cst():
    db = _get_db()
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(text("""
            SELECT cst_id, codigo, descricao
            FROM cst_icms
            WHERE codigo ILIKE :q
               OR descricao ILIKE :q
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
    usuarios = [dict(row._mapping) for row in rows]
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

@admin_bp.route('/auditoria')
@login_required
def auditoria():
    """
    Stub para evitar BuildError de url_for('admin.auditoria') usado em base.html.
    Auditoria do sistema.
    """
    flash('Auditoria (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

@admin_bp.route('/backup')
@login_required
def backup():
    """
    Stub para evitar BuildError de url_for('admin.backup') usado em base.html.
    Sistema de backup.
    """
    flash('Sistema de Backup (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

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
    q = request.args.get('q', '').strip()
    if q:
        rows = db.execute(text("""
            SELECT origem_id, codigo, descricao
            FROM origens_mercadoria
            WHERE codigo ILIKE :q
               OR descricao ILIKE :q
            ORDER BY codigo
        """), {'q': f'%{q}%'}).fetchall()
    else:
        rows = db.execute(text("""
            SELECT origem_id, codigo, descricao
            FROM origens_mercadoria
            ORDER BY codigo
        """)).fetchall()
    origens = [dict(row._mapping) for row in rows]
    return render_template('admin/origens_mercadoria/list.html', origens=origens)

@admin_bp.route('/origens-mercadoria/novo')
@login_required
@permission_required('origens_mercadoria.create')
def create_origem_mercadoria():
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



@admin_bp.route('/clientes/novo')
@login_required
@permission_required('clientes.create')
def create_cliente():
    db = _get_db()
    try:
        # Monta form_data vazio
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
        # Carrega regimes tributários para o select
        regimes_rows = db.execute(text("SELECT regime_tributario_id, nome FROM regimes_tributarios")).fetchall()
        regimes_tributarios = [_safe_row_to_dict(r, ['regime_tributario_id', 'nome']) for r in regimes_rows]
        
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
        if row:
            cliente = dict(row._mapping)
        else:
            cliente = None

        if not cliente:
            flash('Cliente não encontrado', 'warning')
            return redirect(url_for('admin.list_clientes'))

        form_data = _cliente_to_form_data(cliente)
        certificados_existentes = db.execute(text("""
            SELECT * FROM certificados_digitais WHERE cliente_id = :cid
        """), {'cid': cliente_id}).fetchall()
        
        # Consultar produtos cadastrados para o cliente
        prod_rows = db.execute(text("""
            SELECT *
            FROM produtos
            WHERE cliente_id = :cid
            ORDER BY descricao
        """), {'cid': cliente_id}).fetchall()
        produtos_existentes = [dict(row._mapping) for row in prod_rows]
        
        # Consultar regras tributárias para o cliente
        regras_rows = db.execute(text("""
            SELECT * FROM regras_tributacao WHERE cliente_id = :cid
        """), {'cid': cliente_id}).fetchall()
        regras_existentes = [dict(row._mapping) for row in regras_rows]

        # Consultar destinatários para o cliente
        destinatarios_rows = db.execute(text("""
            SELECT * FROM destinatarios_nfe WHERE cliente_id = :cid
        """), {'cid': cliente_id}).fetchall()
        destinatarios = [dict(row._mapping) for row in destinatarios_rows]

        regimes_rows = db.execute(text("SELECT regime_tributario_id, nome FROM regimes_tributarios")).fetchall()
        regimes_tributarios = [_safe_row_to_dict(r, ['regime_tributario_id', 'nome']) for r in regimes_rows]
        certificados_existentes = [dict(row._mapping) for row in certificados_existentes]
       
        return render_template(
            'admin/clientes/form.html',
            cliente=cliente,
            form_data=form_data,
            regimes_tributarios=regimes_tributarios,
            certificados_existentes=certificados_existentes,
            produtos_existentes=produtos_existentes,
            regras_existentes=regras_existentes,
            destinatarios=destinatarios
        )
    except Exception as e:
        print(f"❌ Erro edit_cliente: {e}")
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
    return render_template(
        'admin/certificados/form.html',
        certificado=None,
        cliente_id=cliente_id,
        modal=modal
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
    return render_template(
        'admin/regras_tributacao/form.html',
        regra=None,
        cliente_id=cliente_id,
        modal=modal
    )

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
        return render_template('admin/regras_tributacao/form.html', regra=regra)
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
            data = {
                'cliente_id': cliente_id,
                'tipo_pessoa': request.form.get('tipo_pessoa'),  # Adicionado
                'nome_razao_social': request.form.get('nome_razao_social'),  # Adicionado
                'cpf_cnpj': request.form.get('cpf_cnpj'),
                'ie': request.form.get('ie'),  # Adicionado
                'ie_indicador_nfe': request.form.get('ie_indicador_nfe', 'C'),  # Adicionado
                'email': request.form.get('email'),  # Adicionado
                'telefone': request.form.get('telefone'),  # Adicionado
                'logradouro': request.form.get('logradouro'),
                'numero': request.form.get('numero'),
                'complemento': request.form.get('complemento'),  # Adicionado
                'bairro': request.form.get('bairro'),
                'cep': request.form.get('cep'),
                'codigo_municipio': request.form.get('codigo_municipio'),
                'nome_municipio': request.form.get('nome_municipio'),
                'uf': request.form.get('uf'),
                'codigo_uf': request.form.get('codigo_uf'),  # Adicionado
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
            return redirect(url_for('admin.list_destinatarios'))
        except Exception as e:
            db.rollback()
            print(f"❌ Erro admin_destinatarios_nfe_add: {e}")
            flash('Erro ao adicionar destinatário', 'error')
            return redirect(url_for('admin.list_destinatarios'))
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
        rows = db.execute(text("""
            SELECT produto_id, codigo_interno, descricao, unidade_comercial, preco_unitario_padrao,
                   ncm_id, cfop_id, ativo
            FROM produtos
            ORDER BY descricao
        """)).fetchall()
        produtos = [_safe_row_to_dict(r, [
            'produto_id','codigo_interno','descricao','unidade_comercial',
            'preco_unitario_padrao','ncm_id','cfop_id','ativo'
        ]) for r in rows]
        return render_template('admin/produtos/list.html', produtos=produtos)
    except Exception as e:
        print(f"❌ Erro list_produtos: {e}")
        flash('Erro ao carregar produtos', 'error')
        return render_template('admin/produtos/list.html', produtos=[])
    finally:
        db.close()

@admin_bp.route('/produtos/add', methods=['GET'])
@login_required
@permission_required('produtos.create')
def create_produto():
    return render_template('admin/produtos/form.html', produto=None)

@admin_bp.route('/produtos/add', methods=['POST'])
@login_required
@permission_required('produtos.create')
def store_produto():
    db = _get_db()
    try:
        data = {
            'codigo_interno': request.form.get('codigo_interno'),
            'descricao': request.form.get('descricao'),
            'unidade_comercial': request.form.get('unidade_comercial','UN'),
            'preco_unitario_padrao': request.form.get('preco_unitario_padrao') or 0,
            'ncm_id': request.form.get('ncm_id'),
            'cfop_id': request.form.get('cfop_id'),
            'ativo': True
        }
        db.execute(text("""
            INSERT INTO produtos (codigo_interno, descricao, unidade_comercial, preco_unitario_padrao,
                                  ncm_id, cfop_id, ativo)
            VALUES (:codigo_interno, :descricao, :unidade_comercial, :preco_unitario_padrao,
                    :ncm_id, :cfop_id, :ativo)
        """), data)
        db.commit()
        flash('Produto criado', 'success')
        return redirect(url_for('admin.list_produtos'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro store_produto: {e}")
        flash('Erro ao criar produto', 'error')
        return redirect(url_for('admin.create_produto'))
    finally:
        db.close()

@admin_bp.route('/produtos/<int:produto_id>/edit', methods=['GET'])
@login_required
@permission_required('produtos.edit')
def edit_produto(produto_id: int):
    origem = request.args.get('origem', 'list')
    db = _get_db()
    try:
        row = db.execute(text("""
            SELECT produto_id, codigo_interno, descricao, unidade_comercial, preco_unitario_padrao,
                   tipo_item, ncm_id, cest, cfop_id, origem_mercadoria,
                   cst_id, csosn_id, ativo
            FROM produtos
            WHERE produto_id = :pid
        """), {'pid': produto_id}).fetchone()
        produto = dict(row._mapping) if row else None

        if not produto:
            flash('Produto não encontrado', 'warning')
            return redirect(url_for('admin.list_produtos'))

        # Se precisar de listas para selects (NCM, CFOP, etc), busque aqui:
        ncm_lista = db.execute(text("SELECT ncm_id, codigo, descricao FROM ncms")).fetchall()
        cfop_lista = db.execute(text("SELECT cfop_id, cfop ,descricao FROM cfops")).fetchall()
        origens_list = db.execute(text("SELECT origem_id, codigo, descricao FROM origens_mercadoria")).fetchall()
        csts_list = db.execute(text("SELECT cst_id, codigo, descricao FROM cst_icms")).fetchall()
        csosns_list = db.execute(text("SELECT csosn_id, codigo, descricao FROM csosn_icms")).fetchall()

        # ... outros selects ...

        return render_template(
            'admin/produtos/form.html',
            produto=produto,
            ncms=[dict(ncm._mapping) for ncm in ncm_lista],
            cfops=[dict(cfop._mapping) for cfop in cfop_lista],
            origens_mercadoria = [dict(origens._mapping) for origens in origens_list],
            csts = [dict(csts._mapping) for csts in csts_list],
            csosns = [dict(csosns._mapping) for csosns in csosns_list],
            voltar_para=origem

            # ... outros contextos ...
        )
    except Exception as e:
        print(f"❌ Erro edit_produto: {e}")
        flash('Erro ao carregar produto', 'error')
        return redirect(url_for('admin.list_produtos'))
    finally:
        db.close()

@admin_bp.route('/produtos/<int:produto_id>/edit', methods=['POST'])
@login_required
@permission_required('produtos.edit')
def update_produto(produto_id: int):
    db = _get_db()
    try:
        data = {
            'produto_id': produto_id,
            'codigo_interno': request.form.get('codigo_interno'),
            'descricao': request.form.get('descricao'),
            'unidade_comercial': request.form.get('unidade_comercial','UN'),
            'preco_unitario_padrao': request.form.get('preco_unitario_padrao') or 0,
            'ncm_id': request.form.get('ncm_id'),
            'cfop_id': request.form.get('cfcfop_idop_padrao'),
        }
        db.execute(text("""
            UPDATE produtos
            SET codigo_interno=:codigo_interno,
                descricao=:descricao,
                unidade_comercial=:unidade_comercial,
                preco_unitario_padrao=:preco_unitario_padrao,
                ncm_id=:ncm_id,
                cfop_id=:cfop_id
            WHERE produto_id=:produto_id
        """), data)
        db.commit()
        flash('Produto atualizado', 'success')
        return redirect(url_for('admin.list_produtos'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro update_produto: {e}")
        flash('Erro ao atualizar produto', 'error')
        return redirect(url_for('admin.edit_produto', produto_id=produto_id))
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
        return render_template('admin/destinatarios/list.html', destinatarios=destinatarios, cliente_id=cliente_id)
    except Exception as e:
        print(f"❌ Erro list_destinatarios: {e}")
        flash('Erro ao carregar destinatários', 'error')
        return render_template('admin/destinatarios/list.html', destinatarios=[], cliente_id=cliente_id)
    finally:
        db.close()



@admin_bp.route('/destinatarios/salvar', methods=['POST'])
@login_required
@permission_required('destinatarios_nfe.create')
def salvar_destinatario():
    db = _get_db()
    try:
        data = {
            'cliente_id': request.form.get('cliente_id'),
            'tipo_pessoa': request.form.get('tipo_pessoa'),
            'nome_razao_social': request.form.get('nome_razao_social'),
            'cpf_cnpj': request.form.get('cpf_cnpj'),
            'ie': request.form.get('ie'),
            'ie_indicador_nfe': request.form.get('ie_indicador_nfe'),
            'email': request.form.get('email'),
            'telefone': request.form.get('telefone'),
            'logradouro': request.form.get('logradouro'),
            'numero': request.form.get('numero'),
            'complemento': request.form.get('complemento'),
            'bairro': request.form.get('bairro'),
            'cep': request.form.get('cep'),
            'nome_municipio': request.form.get('nome_municipio'),
            'codigo_municipio': request.form.get('codigo_municipio'),
            'uf': request.form.get('uf'),
            'codigo_uf': request.form.get('codigo_uf'),
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
        return redirect(url_for('admin.list_destinatarios'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro salvar_destinatario: {e}")
        flash('Erro ao salvar destinatário', 'error')
        cliente_id = request.form.get('cliente_id')
        return redirect(url_for('admin.list_destinatarios'))
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
    try:
        rows = db.execute(text("""
            SELECT certificado_digital_id, fingerprint, conteudo_certificado, validade_fim, ativo
            FROM certificados_digitais
            ORDER BY certicertificado_digital_idficado_id DESC
        """)).fetchall()
        certificados = [_safe_row_to_dict(r, [
            'certificado_digital_id','fingerprint','conteudo_certificado','validade_fim','ativo'
        ]) for r in rows]
        return render_template('admin/certificados/list.html', certificados=certificados)
    except Exception as e:
        print(f"❌ Erro list_certificados: {e}")
        flash('Erro ao carregar certificados', 'error')
        return render_template('admin/certificados/list.html', certificados=[])
    finally:
        db.close()

@admin_bp.route('/certificados/novo')
@login_required
@permission_required('certificados.create')
def novo_certificado():
    return render_template('admin/certificados/form.html', certificado=None)

@admin_bp.route('/certificados/salvar', methods=['POST'])
@login_required
@permission_required('certificados.create')
def salvar_certificado():
    db = _get_db()
    try:
        
        valido_ate = request.form.get('validade_fim')
        db.execute(text("""
            INSERT INTO certificados_digitais (cliente_id, fingerprint, conteudo_certificado, senha_ceritificado,
                        validade_inicio, validade_fim, ativo, data_upload, nome_arquivo_original, created_by_user_id)
            VALUES (:cliente_id, :fingerprint, :conteudo_certificado,:senha_ceritificado,:validade_inicio
                        :validade_fim, TRUE, NOW(),:nome_arquivo_original,current_user.id)
        """), {
            
            'valido_ate': valido_ate
        })
        db.commit()
        flash('Certificado salvo', 'success')
        return redirect(url_for('admin.list_certificados'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro salvar_certificado: {e}")
        flash('Erro ao salvar certificado', 'error')
        return redirect(url_for('admin.novo_certificado'))
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
    try:
        rows = db.execute(text("""
            SELECT regra_tributacao_id, produto_id, cliente_id, cfop, origem, cst_icms,
                   aliquota_icms
            FROM regras_tributacao
            ORDER BY regra_tributacao_id DESC            
        """)).fetchall()
        regras = [_safe_row_to_dict(r, [
            'regra_tributacao_id','produto_id','cliente_id','cfop','origem',
            'cst_icms','aliquota_icms'
        ]) for r in rows]
        return render_template('admin/regras_tributacao/list.html', regras=regras)
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
    return render_template('admin/regras_tributacao/form.html', regra=None)

@admin_bp.route('/regras-tributacao/salvar', methods=['POST'])
@login_required
@permission_required('regras_tributacao.create')
def salvar_regra_tributacao():
    db = _get_db()
    try:
        data = {
            'produto_id': request.form.get('produto_id'),
            'cliente_id': request.form.get('cliente_id'),
            'cfop': request.form.get('cfop'),
            'origem': request.form.get('origem','0'),
            'cst_icms': request.form.get('cst_icms','00'),
            'aliquota_icms': request.form.get('aliquota_icms') or 0
        }
        db.execute(text("""
            INSERT INTO regras_tributacao (produto_id, cliente_id, cfop, origem, cst_icms, aliquota_icmst)
            VALUES (:produto_id, :cliente_id, :cfop, :origem, :cst_icms, :aliquota_icms)
        """), data)
        db.commit()
        flash('Regra salva', 'success')
        return redirect(url_for('admin.list_regras_tributacao'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro salvar_regra_tributacao: {e}")
        flash('Erro ao salvar regra', 'error')
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
        return redirect(url_for('admin.list_regras_tributacao'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro excluir_regra_tributacao: {e}")
        flash('Erro ao excluir regra', 'error')
        return redirect(url_for('admin.list_regras_tributacao'))
    finally:
        db.close()


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
# BUSCAR CEP (mock)
# -------------------------------------------------------------------

@admin_bp.route('/api/buscar-cep/<cep>')
@login_required
def buscar_cep(cep: str):
    return jsonify({
        'cep': cep,
        'logradouro': 'Rua Exemplo',
        'bairro': 'Centro',
        'uf': 'SP',
        'nome_municipio': 'São Paulo',
        'codigo_municipio': '3550308'
    })

# -------------------------------------------------------------------
# HEALTH
# -------------------------------------------------------------------

@admin_bp.route('/health')
def admin_health():
    return jsonify({'status': 'ok', 'role': getattr(current_user, 'role', None)})
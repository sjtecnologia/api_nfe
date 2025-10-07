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
def list_nfes():
    flash('Lista de NFes (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

@admin_bp.route('/ncms')
@login_required
def list_ncms():
    """
    Stub para evitar BuildError em base.html.
    Ajuste futuramente para exibir lista real (ou consumir /api/ncms).
    """
    flash('Lista de NCMs (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

@admin_bp.route('/cst')
@login_required
def list_cst():
    """
    Stub para evitar BuildError de url_for('admin.list_cst') usado em base.html.
    Substitua depois por listagem real de códigos CST ICMS.
    """
    flash('Lista de CST (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

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
    """Lista CFOPs"""
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT cfop_id, cfop, descricao, observacao, tipooperacao, identificadordestinooperacao, created_at
            FROM cfops
            ORDER BY cfop
        """)).fetchall()
        cfops = [_safe_row_to_dict(r, [
            'cfop_id','cfop','descricao','observacao','tipooperacao','identificadordestinooperacao','created_at'
        ]) for r in rows]
        return render_template('admin/cfops/list.html', cfops=cfops)
    except Exception as e:
        print(f"❌ Erro list_cfops: {e}")
        flash('Erro ao carregar CFOPs', 'error')
        return render_template('admin/cfops/list.html', cfops=[])
    finally:
        db.close()

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
                INSERT INTO cfops (cfop, descricao, observacao, tipooperacao, identificadordestinooperacao, created_at)
                VALUES (:cfop, :descricao, :observacao, :tipooperacao, :identificadordestinooperacao, NOW())
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
            'cfop_id','cfop','descricao','observacao','tipooperacao','identificadordestinooperacao','created_at'
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
def list_users():
    flash('Gestão de usuários (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

@admin_bp.route('/clientes/<int:cliente_id>')
@login_required
def view_cliente(cliente_id: int):
    flash(f'Visualização do cliente {cliente_id} (stub).', 'info')
    return redirect(url_for('admin.list_clientes'))

@admin_bp.route('/csosn')
@login_required
def list_csosn():
    """
    Stub para evitar BuildError de url_for('admin.list_csosn') usado em base.html.
    CSOSN = Código de Situação da Operação do Simples Nacional.
    """
    flash('Lista de CSOSN (stub).', 'info')
    return redirect(url_for('admin.admin_home'))


@admin_bp.route('/regimes-tributarios')
@login_required
@permission_required('regimes_tributarios.view')
def list_regimes_tributarios():
    """Lista regimes tributários"""
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT regime_tributario_id, nome, descricao, ativo, created_at
            FROM regimes_tributarios
            ORDER BY nome
        """)).fetchall()
        regimes = [_safe_row_to_dict(r, [
            'regime_tributario_id','nome','descricao','ativo','created_at'
        ]) for r in rows]
        return render_template('admin/regimes_tributarios/list.html', regimes=regimes)
    except Exception as e:
        print(f"❌ Erro list_regimes_tributarios: {e}")
        flash('Erro ao carregar regimes tributários', 'error')
        return render_template('admin/regimes_tributarios/list.html', regimes=[])
    finally:
        db.close()

@admin_bp.route('/regimes-tributarios/novo')
@login_required
@permission_required('regimes_tributarios.create')
def novo_regime_tributario():
    return render_template('admin/regimes_tributarios/form.html', regime=None)

@admin_bp.route('/regimes-tributarios/salvar', methods=['POST'])
@login_required
@permission_required('regimes_tributarios.create')
def salvar_regime_tributario():
    db = _get_db()
    try:
        data = {
            'nome': request.form.get('nome'),
            'descricao': request.form.get('descricao'),
            'ativo': True
        }
        db.execute(text("""
            INSERT INTO regimes_tributarios (nome, descricao, ativo, created_at)
            VALUES (:nome, :descricao, :ativo, NOW())
        """), data)
        db.commit()
        flash('Regime tributário salvo', 'success')
        return redirect(url_for('admin.list_regimes_tributarios'))
    except Exception as e:
        db.rollback()
        print(f"❌ Erro salvar_regime_tributario: {e}")
        flash('Erro ao salvar regime tributário', 'error')
        return redirect(url_for('admin.novo_regime_tributario'))
    finally:
        db.close()

@admin_bp.route('/roles')
@login_required
def list_roles():
    """
    Stub para evitar BuildError de url_for('admin.list_roles') usado em base.html.
    Gestão de roles/papéis de usuários no sistema.
    """
    flash('Lista de Roles (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

@admin_bp.route('/permissions')
@login_required
def list_permissions():
    """
    Stub para evitar BuildError de url_for('admin.list_permissions') usado em base.html.
    Gestão de permissões do sistema.
    """
    flash('Lista de Permissões (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

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
def list_motivos_desoneracao():
    """
    Stub para evitar BuildError de url_for('admin.list_motivos_desoneracao') usado em base.html.
    Motivos de desoneração do ICMS (códigos 1-16 conforme tabela SEFAZ).
    """
    flash('Lista de Motivos de Desoneração (stub).', 'info')
    return redirect(url_for('admin.admin_home'))

@admin_bp.route('/origens-mercadoria')
@login_required
def list_origens_mercadoria():
    """
    Stub para evitar BuildError de url_for('admin.list_origens_mercadoria') usado em base.html.
    Origens de mercadoria para NFe (0=Nacional, 1=Estrangeira-Importação direta, etc).
    """
    flash('Lista de Origens de Mercadoria (stub).', 'info')
    return redirect(url_for('admin.admin_home'))
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
            SELECT cliente_id, razao_social, cnpj, ativo, data_cadastro
            FROM clientes
            ORDER BY razao_social
        """)).fetchall()
        clientes = [_safe_row_to_dict(r, [
            'cliente_id','razao_social','cnpj','ativo','data_cadastro'
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
            SELECT produto_id, descricao, codigo_interno, ncm_id, cfop_id, unidade_comercial
            FROM produtos
            WHERE cliente_id = :cid
            ORDER BY descricao
        """), {'cid': cliente_id}).fetchall()
        produtos = [dict(row._mapping) for row in prod_rows]
        
        # Consultar regras tributárias para o cliente
        regras_rows = db.execute(text("""
            SELECT * FROM regras_tributacao WHERE cliente_id = :cid
        """), {'cid': cliente_id}).fetchall()
        regras_tributarias = [dict(row._mapping) for row in regras_rows]

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
            produtos=produtos,
            regras_tributarias=regras_tributarias,
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
    db = _get_db()
    try:
        row = db.execute(text("""
            SELECT produto_id, codigo_interno, descricao, unidade_comercial, preco_unitario_padrao,
                   ncm_id, cfop_id, ativo
            FROM produtos
            WHERE produto_id = :pid
        """), {'pid': produto_id}).fetchone()
        produto = _safe_row_to_dict(row, [
            'produto_id','codigo_interno','descricao','unidade_comercial','preco_unitario_padrao',
            'ncm_id','cfop_id','ativo'
        ])
        if not produto:
            flash('Produto não encontrado', 'warning')
            return redirect(url_for('admin.list_produtos'))
        return render_template('admin/produtos/form.html', produto=produto)
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

# -------------------------------------------------------------------
# DESTINATÁRIOS
# -------------------------------------------------------------------

@admin_bp.route('/destinatarios')
@login_required
@permission_required('destinatarios_nfe.view')
def list_destinatarios():
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT *
            FROM destinatarios_nfe
            WHERE tipo = 'DEST' OR tipo IS NULL
            ORDER BY razao_social
        """)).fetchall()
        destinatarios = [_safe_row_to_dict(r, [
            'cliente_id','nome_razao_social','cpf_cnpj','uf','nome_municipio'
        ]) for r in rows]
        return render_template('admin/destinatarios/list.html', destinatarios=destinatarios)
    except Exception as e:
        print(f"❌ Erro list_destinatarios: {e}")
        flash('Erro ao carregar destinatários', 'error')
        return render_template('admin/destinatarios/list.html', destinatarios=[])
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
        return redirect(url_for('admin.novo_destinatario', cliente_id=cliente_id))
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
            SELECT certificado_id, apelido, tipo, valido_ate, ativo, created_at
            FROM certificados
            ORDER BY certificado_id DESC
        """)).fetchall()
        certificados = [_safe_row_to_dict(r, [
            'certificado_id','apelido','tipo','valido_ate','ativo','created_at'
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
        apelido = request.form.get('apelido')
        tipo = request.form.get('tipo','A1')
        valido_ate = request.form.get('valido_ate')
        db.execute(text("""
            INSERT INTO certificados (apelido, tipo, valido_ate, ativo, created_at)
            VALUES (:apelido, :tipo, :valido_ate, TRUE, NOW())
        """), {
            'apelido': apelido,
            'tipo': tipo,
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
                   aliquota_icms, created_at
            FROM regras_tributacao
            ORDER BY regra_tributacao_id DESC
            LIMIT 100
        """)).fetchall()
        regras = [_safe_row_to_dict(r, [
            'regra_tributacao_id','produto_id','cliente_id','cfop','origem',
            'cst_icms','aliquota_icms','created_at'
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
            INSERT INTO regras_tributacao (produto_id, cliente_id, cfop, origem, cst_icms, aliquota_icms, created_at)
            VALUES (:produto_id, :cliente_id, :cfop, :origem, :cst_icms, :aliquota_icms, NOW())
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
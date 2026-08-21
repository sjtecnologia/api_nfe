"""
routes/admin_api_routes.py

Blueprint com as rotas de API JSON do módulo admin.
Extrai as rotas puramente JSON (sem render_template) de admin_routes.py,
mantendo as URLs inalteradas (/admin/api/...).

Registrado em app.py com url_prefix='/admin'.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, Response, jsonify, request, session
from flask_login import login_required, current_user
from auth.decorators import admin_required
import requests
import io
from sqlalchemy import text
from database.connection import get_db
from services.intelligence.cash_flow_data_aggregator import CashFlowDataAggregator
from services.intelligence.customer_data_aggregator import CustomerDataAggregator
from services.intelligence.data_types import PeriodoAnalise
from services.intelligence.inventory_data_aggregator import InventoryDataAggregator
from services.intelligence.sales_data_aggregator import SalesDataAggregator
from services.intelligence.sales_analysis_service import SalesAnalysisService
from services.intelligence.business_diagnostic_service import BusinessDiagnosticService
from services.product_description_service import (
    ProductDescriptionError,
    ProductDescriptionService,
    ProductDescriptionUnavailable,
)
try:
    from database.models import AiConversation, AiFeedback, AiMessage, AiUsageLog
except ImportError:
    AiConversation = None
    AiFeedback = None
    AiMessage = None
    AiUsageLog = None

try:
    from services.ai_service import AIService, AITenantAccessError, AIUsageLimitExceeded
except ImportError:
    AIService = None

    class AITenantAccessError(RuntimeError):
        pass

    class AIUsageLimitExceeded(RuntimeError):
        pass

try:
    from services.ai_providers import AIProviderError
except ImportError:
    class AIProviderError(RuntimeError):
        pass

try:
    from services.product_classification_service import (
        ProductClassificationError,
        ProductClassificationService,
        ProductClassificationUnavailable,
    )
except ImportError:
    ProductClassificationService = None

    class ProductClassificationError(RuntimeError):
        pass

    class ProductClassificationUnavailable(RuntimeError):
        pass

try:
    from services.consultor_vendas_service import gerar_resumo_consultor_vendas
except ImportError:
    gerar_resumo_consultor_vendas = None

logger = logging.getLogger(__name__)

admin_api_bp = Blueprint('admin_api', __name__)


def _ensure_estoque_caixa_tables(db):
    """Cria as tabelas de estoque/caixa caso a migração ainda não tenha sido aplicada."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
            movimentacao_id BIGSERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
            produto_id INTEGER,
            tipo_movimentacao VARCHAR(10) NOT NULL CHECK (tipo_movimentacao IN ('ENTRADA', 'SAIDA')),
            quantidade NUMERIC(15, 3) NOT NULL CHECK (quantidade > 0),
            valor_unitario NUMERIC(15, 2),
            observacao TEXT,
            data_movimentacao TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
            created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
        )
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_estoque_mov_cliente_data
        ON estoque_movimentacoes (cliente_id, data_movimentacao DESC)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_estoque_mov_produto
        ON estoque_movimentacoes (produto_id)
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS fluxo_caixa_lancamentos (
            lancamento_id BIGSERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
            tipo_lancamento VARCHAR(10) NOT NULL CHECK (tipo_lancamento IN ('RECEITA', 'DESPESA')),
            categoria VARCHAR(100) NOT NULL,
            descricao TEXT NOT NULL,
            valor NUMERIC(15, 2) NOT NULL CHECK (valor > 0),
            forma_pagamento VARCHAR(50),
            observacao TEXT,
            data_lancamento TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
            created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
        )
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_fluxo_caixa_cliente_data
        ON fluxo_caixa_lancamentos (cliente_id, data_lancamento DESC)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_fluxo_caixa_tipo
        ON fluxo_caixa_lancamentos (tipo_lancamento)
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS fluxo_caixa_categorias (
            categoria_id BIGSERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
            nome VARCHAR(100) NOT NULL,
            tipo_lancamento VARCHAR(10) NOT NULL DEFAULT 'DESPESA' CHECK (tipo_lancamento IN ('RECEITA', 'DESPESA')),
            descricao TEXT,
            ativo BOOLEAN NOT NULL DEFAULT true,
            created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
        )
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_fluxo_cat_cliente_nome
        ON fluxo_caixa_categorias (cliente_id, nome)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_fluxo_cat_cliente_tipo_nome
        ON fluxo_caixa_categorias (cliente_id, tipo_lancamento, nome)
    """))


def _parse_periodo_datas():
    """Resolve período por data explícita ou por atalho (7/15/30/90/mes)."""
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    periodo = (request.args.get('periodo') or '30').strip().lower()

    if data_inicio_str and data_fim_str:
        inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        return inicio, fim

    hoje = datetime.now().date()
    if periodo == 'mes':
        return hoje.replace(day=1), hoje

    try:
        dias = int(periodo)
    except ValueError:
        dias = 30

    dias = max(1, min(dias, 365))
    return hoje - timedelta(days=dias - 1), hoje


def _resolve_cliente_id_admin_api() -> int:
    """Resolve cliente_id respeitando isolamento por tenant e empresa ativa na sessão."""
    raw_cliente_id = request.args.get('cliente_id')
    body = request.get_json(silent=True) or {}
    session_cliente_id = session.get('current_client_id') or session.get('active_cliente_id')

    if raw_cliente_id in (None, ''):
        raw_cliente_id = body.get('cliente_id')

    accessible_ids = []
    if current_user.is_super_admin():
        if session_cliente_id not in (None, ''):
            return int(session_cliente_id)
        if raw_cliente_id not in (None, ''):
            return int(raw_cliente_id)
        raise ValueError('Selecione uma empresa para continuar')

    if hasattr(current_user, 'get_accessible_clients'):
        for c in current_user.get_accessible_clients() or []:
            cid = c.get('cliente_id')
            if cid is not None:
                accessible_ids.append(int(cid))

    if not accessible_ids:
        raise PermissionError('Usuário não possui clientes vinculados')

    if session_cliente_id in (None, ''):
        raise ValueError('Selecione uma empresa para continuar')

    cliente_id = int(session_cliente_id)
    if cliente_id not in accessible_ids:
        raise PermissionError('Acesso negado ao cliente ativo')
    return cliente_id


def _periodo_inteligencia() -> PeriodoAnalise:
    inicio, fim = _parse_periodo_datas()
    return PeriodoAnalise(inicio=inicio, fim=fim)


def _executar_agregador_inteligencia(aggregator_class):
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        periodo = _periodo_inteligencia()
        dados = aggregator_class(db).aggregate(cliente_id=cliente_id, periodo=periodo)
        return jsonify({'success': True, 'data': dados})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro no agregador de inteligência %s: %s', aggregator_class.__name__, exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro ao calcular dados de inteligência'}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Classificações IBS/CBS
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/classificacoes-ibs-cbs', methods=['GET'])
@login_required
def api_classificacoes_ibs_cbs():
    """Lista classificações IBS/CBS ativas — usado em formulários de emissão (CRT=3)."""
    from database.models import ClassificacaoIBSCBS

    db = next(get_db())
    try:
        rows = db.query(ClassificacaoIBSCBS).filter_by(ativo=True).all()
        resultado = [
            {
                'id':               c.classificacao_id,
                'codigo':           c.codigo,
                'descricao':        c.descricao,
                'aliquota_ibs_uf':  float(c.aliquota_ibs_uf),
                'aliquota_ibs_mun': float(c.aliquota_ibs_mun),
                'aliquota_cbs':     float(c.aliquota_cbs),
            }
            for c in rows
        ]
        return jsonify({'success': True, 'data': resultado})

    except Exception as e:
        logger.error('Erro ao buscar classificações IBS/CBS: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Regime tributário do cliente
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/regime-tributario/<int:cliente_id>', methods=['GET'])
@login_required
def api_regime_tributario_cliente(cliente_id):
    """
    Retorna CRT do regime tributário do cliente.
    Usado nos formulários de emissão para controlar exibição de campos IBS/CBS.
    """
    from database.models import Cliente

    db = next(get_db())
    try:
        cliente = db.query(Cliente).filter_by(cliente_id=cliente_id).first()
        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente não encontrado'}), 404

        crt         = cliente.regime_tributario.crt  if cliente.regime_tributario else 1
        regime_nome = cliente.regime_tributario.nome if cliente.regime_tributario else 'Simples Nacional'

        return jsonify({
            'success':       True,
            'crt':           crt,
            'regime_nome':   regime_nome,
            'requer_ibs_cbs': crt == 3,
        })

    except Exception as e:
        logger.error('Erro ao buscar regime tributário cliente %s: %s', cliente_id, e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Informações do cliente
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/cliente/<int:cliente_id>/info', methods=['GET'])
@login_required
def api_cliente_info(cliente_id):
    """
    Retorna informações do cliente para ajustar interface dinamicamente
    (regime tributário, UF, Simples Nacional vs Regime Normal).
    """
    from sqlalchemy import text

    db = next(get_db())
    try:
        row = db.execute(text("""
            SELECT c.cliente_id, c.razao_social, c.uf,
                   c.regime_tributario_id,
                   rt.nome AS regime_nome
            FROM clientes c
            LEFT JOIN regimes_tributarios rt
                   ON c.regime_tributario_id = rt.regime_tributario_id
            WHERE c.cliente_id = :cid
        """), {'cid': cliente_id}).fetchone()

        if not row:
            return jsonify({'erro': 'Cliente não encontrado'}), 404

        d = dict(row._mapping)
        regime_nome       = (d.get('regime_nome') or '').lower()
        is_simples        = 'simples' in regime_nome

        return jsonify({
            'cliente_id':           d['cliente_id'],
            'razao_social':         d['razao_social'],
            'uf':                   d['uf'],
            'regime_tributario_id': d['regime_tributario_id'],
            'regime_nome':          d.get('regime_nome'),
            'is_simples_nacional':  is_simples,
            'mostrar_cst':          not is_simples,
            'mostrar_csosn':        is_simples,
        })

    except Exception as e:
        logger.error('Erro ao buscar dados do cliente %s: %s', cliente_id, e, exc_info=True)
        return jsonify({'erro': 'Erro interno do servidor'}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/ia/produtos/gerar-descricao', methods=['POST'])
@login_required
def api_ia_produto_gerar_descricao():
    """Gera sugestão comercial estruturada sem alterar o produto automaticamente."""
    db = next(get_db())
    try:
        if not current_user.is_admin():
            return jsonify({'success': False, 'error': 'Permissão insuficiente para utilizar a IA no cadastro de produtos'}), 403

        cliente_id = _resolve_cliente_id_admin_api()
        payload = request.get_json(silent=True) or {}
        produto_id = payload.get('produto_id')
        additional_info = (payload.get('informacoes_adicionais') or '').strip()
        if len(additional_info) > ProductDescriptionService.MAX_ADDITIONAL_INFO:
            raise ProductDescriptionError(
                f'Informações adicionais devem ter no máximo {ProductDescriptionService.MAX_ADDITIONAL_INFO} caracteres.'
            )

        product_data = {}
        if produto_id not in (None, ''):
            try:
                produto_id = int(produto_id)
            except (TypeError, ValueError) as exc:
                raise ProductDescriptionError('produto_id inválido') from exc

            row = db.execute(text("""
                SELECT
                    p.produto_id, p.cliente_id, p.codigo_interno, p.descricao,
                    p.unidade_comercial, p.tipo_item, p.preco_unitario_padrao,
                    p.cest, n.codigo AS ncm_codigo, n.descricao AS ncm_descricao,
                    c.cfop AS cfop_codigo, c.descricao AS cfop_descricao
                FROM produtos p
                LEFT JOIN ncms n ON n.ncm_id = p.ncm_id
                LEFT JOIN cfops c ON c.cfop_id = p.cfop_id
                WHERE p.produto_id = :produto_id
                LIMIT 1
            """), {'produto_id': produto_id}).fetchone()
            if not row:
                return jsonify({'success': False, 'error': 'Produto não encontrado'}), 404
            if int(row.cliente_id) != cliente_id:
                return jsonify({'success': False, 'error': 'Acesso negado ao produto informado'}), 403
            product_data = dict(row._mapping)
        else:
            product_data = {
                key: payload.get(key)
                for key in (
                    'codigo_interno', 'descricao', 'unidade_comercial', 'tipo_item',
                    'preco_unitario_padrao', 'cest', 'ncm_codigo', 'ncm_descricao',
                    'cfop_codigo', 'cfop_descricao',
                )
            }

        if not (product_data.get('descricao') or '').strip():
            raise ProductDescriptionError('Descrição do produto é obrigatória')

        service = ProductDescriptionService(db)
        result = service.generate(
            product_data=product_data,
            additional_info=additional_info,
            cliente_id=cliente_id,
            user_id=getattr(current_user, 'id', None),
        )
        return jsonify({'success': True, 'data': result})
    except PermissionError as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ProductDescriptionError as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400
    except ProductDescriptionUnavailable as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 503
    except AIUsageLimitExceeded as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc), 'code': 'AI_USAGE_LIMIT'}), 429
    except Exception as exc:
        db.rollback()
        logger.error('Erro ao gerar descrição comercial do produto: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Não foi possível gerar a descrição neste momento.'}), 500
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Dados estruturados para futura inteligência empresarial
# -----------------------------------------------------------------------------

@admin_api_bp.route('/api/inteligencia/dados/vendas', methods=['GET'])
@login_required
def api_inteligencia_dados_vendas():
    """Retorna métricas comerciais agregadas da empresa ativa, sem chamar IA."""
    return _executar_agregador_inteligencia(SalesDataAggregator)


@admin_api_bp.route('/api/inteligencia/dados/estoque', methods=['GET'])
@login_required
def api_inteligencia_dados_estoque():
    """Retorna métricas agregadas de estoque da empresa ativa, sem chamar IA."""
    return _executar_agregador_inteligencia(InventoryDataAggregator)


@admin_api_bp.route('/api/inteligencia/dados/caixa', methods=['GET'])
@login_required
def api_inteligencia_dados_caixa():
    """Retorna análise histórica agregada do caixa, sem previsão e sem IA."""
    return _executar_agregador_inteligencia(CashFlowDataAggregator)


@admin_api_bp.route('/api/inteligencia/dados/clientes', methods=['GET'])
@login_required
def api_inteligencia_dados_clientes():
    """Retorna métricas agregadas de relacionamento da empresa ativa."""
    return _executar_agregador_inteligencia(CustomerDataAggregator)


@admin_api_bp.route('/api/inteligencia/analises/vendas', methods=['GET'])
@login_required
@admin_required()
def api_inteligencia_analise_vendas():
    """Calcula análise histórica determinística de vendas sem chamar IA."""
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        periodo = _periodo_inteligencia()
        resultado = SalesAnalysisService(db).analyze(cliente_id, periodo)
        return jsonify({'success': True, 'data': resultado})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro na análise de vendas: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro ao calcular análise de vendas'}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/inteligencia/analises/vendas/explicar', methods=['POST'])
@login_required
@admin_required()
def api_inteligencia_analise_vendas_explicar():
    """Gera narrativa sob demanda usando somente análise calculada no backend."""
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        periodo = _periodo_inteligencia()
        service = SalesAnalysisService(db)
        analysis = service.analyze(cliente_id, periodo)
        explanation = service.explain(analysis, cliente_id, getattr(current_user, 'id', None))
        analysis['narrativa'] = explanation.get('narrativa')
        if explanation.get('error'):
            analysis['qualidade_dados']['avisos'].append(
                'A análise foi calculada, mas não foi possível gerar a explicação por IA neste momento.'
            )
            return jsonify({'success': True, 'data': analysis, 'warning': explanation['error']})
        return jsonify({'success': True, 'data': analysis})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao explicar análise de vendas: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Não foi possível explicar a análise neste momento'}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/inteligencia/diagnostico', methods=['GET'])
@login_required
@admin_required()
def api_inteligencia_diagnostico():
    """Calcula diagnóstico executivo determinístico para a empresa ativa."""
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        periodo = _periodo_inteligencia()
        data = BusinessDiagnosticService(db).diagnose(cliente_id, periodo)
        return jsonify({'success': True, 'data': data})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro no diagnóstico empresarial: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro ao calcular diagnóstico empresarial'}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/inteligencia/diagnostico/resumir', methods=['POST'])
@login_required
@admin_required()
def api_inteligencia_diagnostico_resumir():
    """Gera resumo IA opcional a partir de diagnóstico calculado no backend."""
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        periodo = _periodo_inteligencia()
        service = BusinessDiagnosticService(db)
        data = service.diagnose(cliente_id, periodo)
        explanation = service.summarize_with_ai(data, cliente_id, getattr(current_user, 'id', None))
        data['narrative'] = explanation.get('narrative')
        if explanation.get('error'):
            return jsonify({'success': True, 'data': data, 'warning': 'Não foi possível gerar o resumo por IA neste momento.'})
        return jsonify({'success': True, 'data': data})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao resumir diagnóstico empresarial: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Não foi possível resumir o diagnóstico neste momento'}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/inteligencia/clientes', methods=['GET'])
@login_required
@admin_required()
def api_inteligencia_clientes():
    """Lista clientes encontrados no período da empresa ativa."""
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        periodo = _periodo_inteligencia()
        tipo = (request.args.get('tipo') or 'todos').strip().lower()
        if tipo not in {'todos', 'sem_compra', 'recorrentes'}:
            return jsonify({'success': False, 'error': 'Tipo de listagem inválido'}), 400
        data = CustomerDataAggregator(db).identified_customers(cliente_id, periodo, tipo)
        return jsonify({'success': True, 'data': {'periodo': periodo.to_dict(), 'tipo': tipo, 'clientes': data}})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao listar clientes identificados: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro ao carregar clientes identificados'}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Infraestrutura de IA
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/ia/prompts', methods=['GET'])
@login_required
def api_ia_prompts():
    """Lista os prompts ativos da IA centralizada."""
    if AIService is None:
        return jsonify({'success': False, 'error': 'Infraestrutura de IA indisponivel neste ambiente'}), 503

    service = AIService()
    return jsonify({
        'success': True,
        'data': service.list_prompts(),
    })


@admin_api_bp.route('/api/ia/prompts/<string:prompt_name>/preview', methods=['POST'])
@login_required
def api_ia_prompt_preview(prompt_name):
    """Renderiza um prompt com variáveis informadas, sem chamar o provider."""
    if AIService is None:
        return jsonify({'success': False, 'error': 'Infraestrutura de IA indisponivel neste ambiente'}), 503

    service = AIService()
    payload = request.get_json(silent=True) or {}
    try:
        rendered = service.render_prompt(prompt_name, payload.get('variables') or {})
    except KeyError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404

    return jsonify({
        'success': True,
        'data': {
            'prompt_name': prompt_name,
            'rendered_prompt': rendered,
            'variables': payload.get('variables') or {},
        },
    })


@admin_api_bp.route('/api/ia/status', methods=['GET'])
@login_required
def api_ia_status():
    """Retorna um resumo da configuração atual da IA."""
    if AIService is None:
        return jsonify({
            'success': True,
            'data': {
                'provider_model': '',
                'provider_url_configured': False,
                'default_temperature': 0,
                'default_max_tokens': 0,
                'default_monthly_limit': 0,
                'default_daily_limit': 0,
                'prompt_count': 0,
                'feedback_count': 0,
                'feedback_positive_count': 0,
                'feedback_negative_count': 0,
                'feedback_positive_rate': 0,
            },
            'warning': 'Infraestrutura de IA indisponivel neste ambiente',
        })

    service = AIService()
    config = service.config
    feedback_count = 0
    feedback_positive_count = 0
    feedback_negative_count = 0

    if AiFeedback is not None:
        db = next(get_db())
        try:
            feedback_count = db.query(AiFeedback).count()
            feedback_positive_count = db.query(AiFeedback).filter(AiFeedback.feedback == 'POSITIVO').count()
            feedback_negative_count = db.query(AiFeedback).filter(AiFeedback.feedback == 'NEGATIVO').count()
        except Exception as exc:
            logger.error('Erro ao buscar métricas de feedback da IA: %s', exc, exc_info=True)
        finally:
            db.close()

    feedback_positive_rate = round((feedback_positive_count / feedback_count) * 100, 1) if feedback_count else 0
    return jsonify({
        'success': True,
        'data': {
            'provider_model': config.provider_model,
            'provider_url_configured': bool(config.provider_url),
            'default_temperature': config.default_temperature,
            'default_max_tokens': config.default_max_tokens,
            'default_monthly_limit': config.default_monthly_limit,
            'default_daily_limit': config.default_daily_limit,
            'prompt_count': len(service.list_prompts()),
            'feedback_count': feedback_count,
            'feedback_positive_count': feedback_positive_count,
            'feedback_negative_count': feedback_negative_count,
            'feedback_positive_rate': feedback_positive_rate,
        },
    })


@admin_api_bp.route('/api/ia/health', methods=['GET'])
@login_required
def api_ia_health():
    """Checa rapidamente a disponibilidade operacional da IA legado (8081)."""
    checks = []
    base_url = 'http://127.0.0.1:8081'

    payloads = [
        (
            'openapi',
            'GET',
            f'{base_url}/openapi.json',
            None,
        ),
        (
            'valida_basica',
            'POST',
            f'{base_url}/valida',
            {
                'descricao': 'Produto teste healthcheck',
                'tipo_item': 'Produto',
            },
        ),
    ]

    for name, method, url, payload in payloads:
        try:
            if method == 'GET':
                resp = requests.get(url, timeout=5)
            else:
                resp = requests.post(url, json=payload, timeout=8)
            checks.append({
                'name': name,
                'method': method,
                'url': url,
                'status_code': resp.status_code,
                'ok': resp.status_code == 200,
            })
        except Exception as exc:
            checks.append({
                'name': name,
                'method': method,
                'url': url,
                'status_code': None,
                'ok': False,
                'error': str(exc),
            })

    operational = all(item.get('ok') for item in checks)
    return jsonify({
        'success': True,
        'data': {
            'operational': operational,
            'checks': checks,
        },
    })


@admin_api_bp.route('/api/ia/logs', methods=['GET'])
@login_required
def api_ia_logs():
    """Retorna os usos recentes da IA para auditoria rápida."""
    if AiUsageLog is None:
        return jsonify({
            'success': True,
            'data': [],
            'warning': 'Modelo AiUsageLog indisponivel neste ambiente',
        })

    raw_limit = request.args.get('limit', 10)
    try:
        limit = max(1, min(int(raw_limit), 50))
    except (TypeError, ValueError):
        limit = 10

    db = next(get_db())
    try:
        rows = (
            db.query(AiUsageLog)
            .order_by(AiUsageLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify({
            'success': True,
            'data': [row.to_dict() for row in rows],
        })
    except Exception as exc:
        logger.error('Erro ao buscar logs da IA: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/ia/feedbacks', methods=['GET'])
@login_required
def api_ia_feedbacks():
    """Retorna os feedbacks recentes da IA para acompanhamento de qualidade."""
    if AiFeedback is None:
        return jsonify({
            'success': True,
            'data': [],
            'warning': 'Modelo AiFeedback indisponivel neste ambiente',
        })

    raw_limit = request.args.get('limit', 10)
    try:
        limit = max(1, min(int(raw_limit), 50))
    except (TypeError, ValueError):
        limit = 10

    db = next(get_db())
    try:
        rows = (
            db.query(AiFeedback)
            .order_by(AiFeedback.created_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify({
            'success': True,
            'data': [row.to_dict() for row in rows],
        })
    except Exception as exc:
        logger.error('Erro ao buscar feedbacks da IA: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/ia/analytics', methods=['GET'])
@login_required
def api_ia_analytics():
    """Retorna métricas consolidadas da IA para dashboard administrativo."""
    raw_days = request.args.get('days', 14)
    try:
        days = max(1, min(int(raw_days), 90))
    except (TypeError, ValueError):
        days = 14

    raw_cliente_id = request.args.get('cliente_id')
    raw_funcionalidade = (request.args.get('funcionalidade') or '').strip()

    cliente_id = None
    if raw_cliente_id not in (None, ''):
        try:
            cliente_id = int(raw_cliente_id)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Parâmetro cliente_id inválido'}), 400

    funcionalidade = raw_funcionalidade or None

    start_date = datetime.now() - timedelta(days=days - 1)

    def _base_payload():
        return {
            'period_days': days,
            'applied_filters': {
                'cliente_id': cliente_id,
                'funcionalidade': funcionalidade,
            },
            'summary': {
                'total_requests': 0,
                'success_requests': 0,
                'error_requests': 0,
                'success_rate': 0,
                'avg_response_time_ms': 0,
                'total_tokens': 0,
                'total_cost': 0,
                'feedback_total': 0,
                'feedback_positive': 0,
                'feedback_negative': 0,
                'feedback_positive_rate': 0,
                'confidence_score': 0,
            },
            'daily_history': [],
            'by_functionality': [],
            'top_errors': [],
        }

    if AiUsageLog is None:
        return jsonify({'success': True, 'data': _base_payload(), 'warning': 'Modelo AiUsageLog indisponivel neste ambiente'})

    db = next(get_db())
    try:
        logs_query = db.query(AiUsageLog).filter(AiUsageLog.created_at >= start_date)
        if cliente_id is not None:
            logs_query = logs_query.filter(AiUsageLog.cliente_id == cliente_id)
        if funcionalidade:
            logs_query = logs_query.filter(AiUsageLog.funcionalidade == funcionalidade)
        logs = logs_query.all()

        feedbacks = []
        if AiFeedback is not None:
            feedback_query = db.query(AiFeedback).filter(AiFeedback.created_at >= start_date)
            if cliente_id is not None:
                feedback_query = feedback_query.filter(AiFeedback.cliente_id == cliente_id)
            if funcionalidade:
                feedback_query = feedback_query.filter(AiFeedback.funcionalidade == funcionalidade)
            feedbacks = feedback_query.all()

        total_requests = len(logs)
        success_requests = sum(1 for row in logs if (row.status or '').upper() == 'SUCCESS')
        error_requests = max(total_requests - success_requests, 0)
        total_tokens = int(sum(int(row.total_tokens or 0) for row in logs))
        total_cost = float(sum(float(row.cost_estimated or 0) for row in logs))
        total_response_time = int(sum(int(row.response_time_ms or 0) for row in logs))

        success_rate = round((success_requests / total_requests) * 100, 1) if total_requests else 0
        avg_response_time_ms = round(total_response_time / total_requests, 1) if total_requests else 0

        feedback_total = len(feedbacks)
        feedback_positive = sum(1 for row in feedbacks if (row.feedback or '').upper() == 'POSITIVO')
        feedback_negative = sum(1 for row in feedbacks if (row.feedback or '').upper() == 'NEGATIVO')
        feedback_positive_rate = round((feedback_positive / feedback_total) * 100, 1) if feedback_total else 0

        # Score composto para leitura executiva rápida.
        confidence_score = round((success_rate * 0.6) + (feedback_positive_rate * 0.4), 1)

        by_functionality = {}
        for row in logs:
            key = row.funcionalidade or 'sem_funcionalidade'
            item = by_functionality.setdefault(key, {
                'funcionalidade': key,
                'requests': 0,
                'success': 0,
                'errors': 0,
                'tokens': 0,
                'cost': 0.0,
                'response_time_total_ms': 0,
            })
            item['requests'] += 1
            if (row.status or '').upper() == 'SUCCESS':
                item['success'] += 1
            else:
                item['errors'] += 1
            item['tokens'] += int(row.total_tokens or 0)
            item['cost'] += float(row.cost_estimated or 0)
            item['response_time_total_ms'] += int(row.response_time_ms or 0)

        by_functionality_rows = []
        for value in by_functionality.values():
            requests_count = value['requests']
            by_functionality_rows.append({
                'funcionalidade': value['funcionalidade'],
                'requests': requests_count,
                'success': value['success'],
                'errors': value['errors'],
                'success_rate': round((value['success'] / requests_count) * 100, 1) if requests_count else 0,
                'tokens': value['tokens'],
                'cost': round(value['cost'], 6),
                'avg_response_time_ms': round(value['response_time_total_ms'] / requests_count, 1) if requests_count else 0,
            })

        by_functionality_rows.sort(key=lambda row: row['requests'], reverse=True)

        error_counter = {}
        for row in logs:
            if (row.status or '').upper() == 'SUCCESS':
                continue
            msg = (getattr(row, 'error_message', None) or '').strip() or 'Erro não informado'
            error_counter[msg] = error_counter.get(msg, 0) + 1

        top_errors = [
            {'message': message, 'count': count}
            for message, count in sorted(error_counter.items(), key=lambda item: item[1], reverse=True)[:5]
        ]

        daily_index = {}
        for offset in range(days):
            day = (start_date + timedelta(days=offset)).date()
            day_key = day.isoformat()
            daily_index[day_key] = {
                'date': day_key,
                'requests': 0,
                'success': 0,
                'errors': 0,
                'feedback_positive': 0,
                'feedback_negative': 0,
            }

        for row in logs:
            if not row.created_at:
                continue
            day_key = row.created_at.date().isoformat()
            if day_key not in daily_index:
                continue
            daily_index[day_key]['requests'] += 1
            if (row.status or '').upper() == 'SUCCESS':
                daily_index[day_key]['success'] += 1
            else:
                daily_index[day_key]['errors'] += 1

        for row in feedbacks:
            if not row.created_at:
                continue
            day_key = row.created_at.date().isoformat()
            if day_key not in daily_index:
                continue
            if (row.feedback or '').upper() == 'POSITIVO':
                daily_index[day_key]['feedback_positive'] += 1
            elif (row.feedback or '').upper() == 'NEGATIVO':
                daily_index[day_key]['feedback_negative'] += 1

        daily_history = [daily_index[key] for key in sorted(daily_index.keys())]

        data = _base_payload()
        data['summary'] = {
            'total_requests': total_requests,
            'success_requests': success_requests,
            'error_requests': error_requests,
            'success_rate': success_rate,
            'avg_response_time_ms': avg_response_time_ms,
            'total_tokens': total_tokens,
            'total_cost': round(total_cost, 6),
            'feedback_total': feedback_total,
            'feedback_positive': feedback_positive,
            'feedback_negative': feedback_negative,
            'feedback_positive_rate': feedback_positive_rate,
            'confidence_score': confidence_score,
        }
        data['daily_history'] = daily_history
        data['by_functionality'] = by_functionality_rows
        data['top_errors'] = top_errors

        return jsonify({'success': True, 'data': data})
    except Exception as exc:
        logger.error('Erro ao gerar analytics da IA: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/ia/feedback', methods=['POST'])
@login_required
def api_ia_feedback():
    """Registra feedback manual para acompanhamento da qualidade da IA."""
    if AIService is None:
        return jsonify({'success': False, 'error': 'Infraestrutura de IA indisponivel neste ambiente'}), 503

    payload = request.get_json(silent=True) or {}
    funcionalidade = (payload.get('funcionalidade') or '').strip()
    feedback = (payload.get('feedback') or '').strip()

    if not funcionalidade:
        return jsonify({'success': False, 'error': 'Campo funcionalidade é obrigatório'}), 400
    if feedback not in {'POSITIVO', 'NEGATIVO'}:
        return jsonify({'success': False, 'error': 'Campo feedback deve ser POSITIVO ou NEGATIVO'}), 400

    cliente_id = payload.get('cliente_id')
    if cliente_id is None:
        return jsonify({'success': False, 'error': 'Campo cliente_id é obrigatório'}), 400

    try:
        cliente_id = int(cliente_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Campo cliente_id inválido'}), 400

    service = AIService()
    try:
        resultado = service.register_feedback(
            cliente_id=cliente_id,
            user_id=getattr(current_user, 'id', None),
            funcionalidade=funcionalidade,
            feedback=feedback,
            comentario=(payload.get('comentario') or '').strip() or None,
            conversation_id=payload.get('conversation_id'),
            message_id=payload.get('message_id'),
        )
        return jsonify({'success': True, 'data': resultado})
    except Exception as exc:
        logger.error('Erro ao registrar feedback da IA: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro interno ao registrar feedback'}), 500


@admin_api_bp.route('/api/ia/assistente-fiscal/perguntar', methods=['POST'])
@login_required
def api_ia_assistente_fiscal_perguntar():
    """Executa uma pergunta no Assistente Fiscal com persistência de conversa e mensagens."""
    if AIService is None:
        return jsonify({'success': False, 'error': 'Infraestrutura de IA indisponivel neste ambiente'}), 503
    if AiConversation is None or AiMessage is None:
        return jsonify({'success': False, 'error': 'Modelos de conversa de IA indisponíveis'}), 503

    payload = request.get_json(silent=True) or {}
    pergunta = (payload.get('pergunta') or '').strip()
    if not pergunta:
        return jsonify({'success': False, 'error': 'Campo pergunta é obrigatório'}), 400

    cliente_id = payload.get('cliente_id')
    if cliente_id is None:
        return jsonify({'success': False, 'error': 'Campo cliente_id é obrigatório'}), 400

    try:
        cliente_id = int(cliente_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Campo cliente_id inválido'}), 400

    raw_conversation_id = payload.get('conversation_id')
    conversation_id = None
    if raw_conversation_id not in (None, ''):
        try:
            conversation_id = int(raw_conversation_id)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Campo conversation_id inválido'}), 400

    user_id = getattr(current_user, 'id', None)
    service = AIService()
    warnings = []

    try:
        if conversation_id is None:
            try:
                conversation = service.start_conversation(
                    cliente_id=cliente_id,
                    user_id=user_id,
                    funcionalidade='assistente_fiscal',
                    titulo=(pergunta[:80] + '...') if len(pergunta) > 80 else pergunta,
                    contexto=payload.get('contexto') if isinstance(payload.get('contexto'), dict) else None,
                )
                conversation_id = conversation.get('conversation_id')
            except Exception as exc:
                logger.warning('Assistente fiscal sem persistência de conversa: %s', exc)
                warnings.append('Não foi possível iniciar persistência da conversa; resposta gerada sem histórico completo.')

        user_message = None
        if conversation_id is not None:
            try:
                user_message = service.append_message(
                    conversation_id=conversation_id,
                    cliente_id=cliente_id,
                    user_id=user_id,
                    funcionalidade='assistente_fiscal',
                    role='user',
                    content=pergunta,
                )
            except Exception as exc:
                logger.warning('Falha ao persistir pergunta do assistente fiscal: %s', exc)
                warnings.append('Não foi possível persistir a pergunta no histórico.')

        resposta = service.chat(
            prompt_name='assistant_fiscal',
            user_message=pergunta,
            cliente_id=cliente_id,
            user_id=user_id,
            functionality='assistente_fiscal',
            conversation_id=conversation_id,
            tools_scope='fiscal',
            record=True,
        )

        conteudo = (resposta.get('content') or '').strip()
        aviso_legal = 'Aviso: esta orientação é informativa e pode depender da legislação local. Valide com seu contador antes de decisão fiscal definitiva.'
        if aviso_legal not in conteudo:
            conteudo = f"{conteudo}\n\n{aviso_legal}" if conteudo else aviso_legal

        usage = resposta.get('usage') or {}
        assistant_message = None
        if conversation_id is not None:
            try:
                assistant_message = service.append_message(
                    conversation_id=conversation_id,
                    cliente_id=cliente_id,
                    user_id=user_id,
                    funcionalidade='assistente_fiscal',
                    role='assistant',
                    content=conteudo,
                    model=resposta.get('model'),
                    prompt_tokens=int(usage.get('prompt_tokens') or 0),
                    completion_tokens=int(usage.get('completion_tokens') or 0),
                    total_tokens=int(usage.get('total_tokens') or 0),
                    cost_estimated=float(usage.get('cost_estimated') or 0),
                )
            except Exception as exc:
                logger.warning('Falha ao persistir resposta do assistente fiscal: %s', exc)
                warnings.append('Não foi possível persistir a resposta no histórico.')

        return jsonify({
            'success': True,
            'data': {
                'conversation_id': conversation_id,
                'user_message': user_message,
                'assistant_message': assistant_message,
                'answer': conteudo,
                'usage': usage,
                'warnings': warnings,
            },
        })
    except AIUsageLimitExceeded as exc:
        return jsonify({'success': False, 'error': str(exc)}), 429
    except AITenantAccessError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except AIProviderError as exc:
        return jsonify({
            'success': False,
            'error': 'Provedor de IA indisponível no ambiente local. Configure AI_PROVIDER_URL para testar respostas reais.',
            'details': str(exc),
        }), 503
    except Exception as exc:
        logger.error('Erro no assistente fiscal: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': f'Erro interno no Assistente Fiscal: {exc}'}), 500


@admin_api_bp.route('/api/ia/assistente-fiscal/conversas', methods=['GET'])
@login_required
def api_ia_assistente_fiscal_conversas():
    """Lista conversas recentes do Assistente Fiscal para inspeção no painel admin."""
    if AiConversation is None:
        return jsonify({'success': True, 'data': []})

    raw_limit = request.args.get('limit', 10)
    try:
        limit = max(1, min(int(raw_limit), 50))
    except (TypeError, ValueError):
        limit = 10

    raw_cliente_id = request.args.get('cliente_id')
    cliente_id = None
    if raw_cliente_id not in (None, ''):
        try:
            cliente_id = int(raw_cliente_id)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Parâmetro cliente_id inválido'}), 400

    db = next(get_db())
    try:
        query = (
            db.query(AiConversation)
            .filter(AiConversation.funcionalidade == 'assistente_fiscal')
            .order_by(AiConversation.last_message_at.desc(), AiConversation.updated_at.desc())
        )
        if cliente_id is not None:
            query = query.filter(AiConversation.cliente_id == cliente_id)

        rows = query.limit(limit).all()
        resultado = []
        for row in rows:
            last_msg = None
            if AiMessage is not None:
                last_msg = (
                    db.query(AiMessage)
                    .filter(AiMessage.conversation_id == row.conversation_id)
                    .order_by(AiMessage.created_at.desc())
                    .first()
                )
            item = row.to_dict()
            item['last_message'] = {
                'role': getattr(last_msg, 'role', None),
                'content': (getattr(last_msg, 'content', '') or '')[:280],
                'created_at': getattr(last_msg, 'created_at', None),
            } if last_msg else None
            resultado.append(item)

        return jsonify({'success': True, 'data': resultado})
    except Exception as exc:
        logger.error('Erro ao listar conversas do assistente fiscal: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro interno ao listar conversas'}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/ia/assistente-fiscal/mensagens', methods=['GET'])
@login_required
def api_ia_assistente_fiscal_mensagens():
    """Retorna todas as mensagens de uma conversa específica do Assistente Fiscal."""
    if AiConversation is None or AiMessage is None:
        return jsonify({'success': True, 'data': []})

    raw_conversation_id = request.args.get('conversation_id')
    if not raw_conversation_id:
        return jsonify({'success': False, 'error': 'Parâmetro conversation_id obrigatório'}), 400
    try:
        conversation_id = int(raw_conversation_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Parâmetro conversation_id inválido'}), 400

    db = next(get_db())
    try:
        conversa = db.query(AiConversation).filter(
            AiConversation.conversation_id == conversation_id,
            AiConversation.funcionalidade == 'assistente_fiscal',
        ).first()
        if conversa is None:
            return jsonify({'success': False, 'error': 'Conversa não encontrada'}), 404

        mensagens = (
            db.query(AiMessage)
            .filter(AiMessage.conversation_id == conversation_id)
            .order_by(AiMessage.created_at.asc())
            .all()
        )
        return jsonify({
            'success': True,
            'data': {
                'conversation_id': conversation_id,
                'titulo': conversa.titulo,
                'mensagens': [
                    {'role': m.role, 'content': m.content, 'created_at': str(m.created_at)}
                    for m in mensagens
                ],
            },
        })
    except Exception as exc:
        logger.error('Erro ao carregar mensagens da conversa %s: %s', conversation_id, exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro interno ao carregar mensagens'}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/ia/consultor-vendas/insights', methods=['GET'])
@login_required
def api_ia_consultor_vendas_insights():
    """Consultor de Vendas com comparativo de períodos e narrativa opcional por IA."""
    if gerar_resumo_consultor_vendas is None:
        return jsonify({'success': False, 'error': 'Consultor de vendas indisponível neste ambiente'}), 503

    raw_cliente_id = request.args.get('cliente_id')
    cliente_id = None
    if raw_cliente_id not in (None, ''):
        try:
            cliente_id = int(raw_cliente_id)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Parâmetro cliente_id inválido'}), 400

    if cliente_id is None:
        db = None
        try:
            from database.models import UserClient

            db = next(get_db())
            user_id = getattr(current_user, 'id', None)
            if user_id is None:
                return jsonify({'success': False, 'error': 'Usuário sem identificação'}), 400

            user_client_row = (
                db.query(UserClient)
                .filter(UserClient.user_id == user_id)
                .order_by(UserClient.client_id.asc())
                .first()
            )
            if user_client_row is None:
                return jsonify({'success': False, 'error': 'Nenhum cliente vinculado ao usuário'}), 400

            cliente_id = int(user_client_row.client_id)
        except Exception as exc:
            logger.warning('Consultor de vendas: não foi possível resolver cliente padrão para o usuário %s: %s', getattr(current_user, 'id', None), exc)
            return jsonify({'success': False, 'error': 'Nenhum cliente vinculado ao usuário ou cliente indisponível'}), 400
        finally:
            if db is not None:
                db.close()

    raw_days = request.args.get('days', 30)
    try:
        days = max(7, min(int(raw_days), 365))
    except (TypeError, ValueError):
        days = 30
    include_ai = request.args.get('include_ai', '1').strip().lower() not in {'0', 'false', 'no'}

    try:
        data = gerar_resumo_consultor_vendas(
            cliente_id=cliente_id,
            days=days,
            user_id=getattr(current_user, 'id', None),
            incluir_narrativa_ia=include_ai,
        )
        return jsonify({'success': True, 'data': data})
    except Exception as exc:
        logger.error('Erro ao gerar insights do consultor de vendas: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro interno ao gerar insights do consultor de vendas'}), 500


@admin_api_bp.route('/api/ia/classificar-produto', methods=['POST'])
@login_required
def api_ia_classificar_produto():
    """Classifica um produto usando o fluxo fiscal de IA já existente."""
    if ProductClassificationService is None:
        return jsonify({'success': False, 'error': 'Classificacao de IA indisponivel neste ambiente'}), 503

    payload = request.get_json(silent=True) or {}
    descricao = (payload.get('descricao') or '').strip()
    if not descricao:
        return jsonify({'success': False, 'error': 'Campo descricao é obrigatório'}), 400

    db = next(get_db())
    try:
        service = ProductClassificationService(db)
        resultado = service.classify(
            descricao=descricao,
            cliente_id=payload.get('cliente_id'),
            tipo_item=payload.get('tipo_item', 'Produto'),
            unidade_comercial=payload.get('unidade_comercial', 'UN'),
            codigo_interno=payload.get('codigo_interno', ''),
            user_id=getattr(current_user, 'id', None),
        )
        return jsonify({'success': True, 'data': resultado})
    except ProductClassificationUnavailable as exc:
        return jsonify({'success': False, 'error': str(exc)}), 503
    except ProductClassificationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500
    except Exception as exc:
        logger.error('Erro ao classificar produto via IA: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro interno ao classificar produto'}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/ia/gerador-anuncios', methods=['POST'])
@login_required
def api_ia_gerador_anuncios():
    """Gera anúncio comercial para um produto em diferentes canais usando IA."""
    if AIService is None:
        return jsonify({'success': False, 'error': 'Serviço de IA indisponível neste ambiente'}), 503

    payload = request.get_json(silent=True) or {}
    descricao = (payload.get('descricao') or '').strip()
    canal = (payload.get('canal') or 'instagram').strip().lower()
    preco = payload.get('preco', '')
    detalhes = (payload.get('detalhes') or '').strip()

    if not descricao:
        return jsonify({'success': False, 'error': 'Campo descricao é obrigatório'}), 400

    canais_validos = ['mercado_livre', 'shopee', 'instagram', 'facebook', 'whatsapp']
    if canal not in canais_validos:
        return jsonify({'success': False, 'error': f'Canal inválido. Use: {", ".join(canais_validos)}'}), 400

    nomes_canal = {
        'mercado_livre': 'Mercado Livre',
        'shopee': 'Shopee',
        'instagram': 'Instagram',
        'facebook': 'Facebook',
        'whatsapp': 'WhatsApp',
    }

    preco_str = f'R$ {preco}' if preco else 'não informado'
    user_message = (
        f'Crie um anúncio completo para {nomes_canal[canal]}.\n\n'
        f'Produto: {descricao}\n'
        f'Preço: {preco_str}\n'
        f'Detalhes adicionais: {detalhes or "nenhum"}\n\n'
        f'Gere: título atrativo, descrição completa, principais benefícios, '
        f'call-to-action e hashtags (quando aplicável ao canal). '
        f'Formate bem para o canal {nomes_canal[canal]}.'
    )

    try:
        service = AIService()
        resposta = service.chat(
            prompt_name='marketing_ad',
            user_message=user_message,
            cliente_id=None,
            user_id=getattr(current_user, 'id', None),
            functionality='marketing',
            record=False,
        )
        conteudo = (resposta.get('content') or '').strip()
        if not conteudo:
            return jsonify({'success': False, 'error': 'IA não retornou conteúdo'}), 500

        return jsonify({'success': True, 'data': {'canal': canal, 'anuncio': conteudo}})
    except Exception as exc:
        logger.error('Erro no gerador de anúncios: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': f'Erro ao gerar anúncio: {exc}'}), 500


@admin_api_bp.route('/api/ia/mensagens-whatsapp', methods=['POST'])
@login_required
def api_ia_mensagens_whatsapp():
    """Gera mensagem comercial para WhatsApp usando IA."""
    if AIService is None:
        return jsonify({'success': False, 'error': 'Serviço de IA indisponível neste ambiente'}), 503

    payload = request.get_json(silent=True) or {}
    tipo = (payload.get('tipo') or 'cobranca').strip().lower()
    nome_cliente = (payload.get('nome_cliente') or '').strip()
    tom = (payload.get('tom') or 'amigavel').strip().lower()
    detalhes = (payload.get('detalhes') or '').strip()

    tipos_validos = ['cobranca', 'lembrete', 'agradecimento', 'promocao', 'recuperar_cliente', 'orcamento']
    if tipo not in tipos_validos:
        return jsonify({'success': False, 'error': f'Tipo inválido. Use: {", ".join(tipos_validos)}'}), 400

    nomes_tipo = {
        'cobranca': 'Cobrança',
        'lembrete': 'Lembrete',
        'agradecimento': 'Agradecimento',
        'promocao': 'Promoção',
        'recuperar_cliente': 'Recuperar Cliente',
        'orcamento': 'Orçamento',
    }
    nomes_tom = {'formal': 'formal', 'amigavel': 'amigável', 'persuasivo': 'persuasivo'}

    user_message = (
        f'Crie uma mensagem de WhatsApp do tipo: {nomes_tipo[tipo]}.\n'
        f'Tom: {nomes_tom.get(tom, "amigável")}.\n'
        f'{"Nome do cliente: " + nome_cliente + chr(10) if nome_cliente else ""}'
        f'{"Detalhes adicionais: " + detalhes + chr(10) if detalhes else ""}'
        f'A mensagem deve ser curta, direta e pronta para copiar e enviar. '
        f'Use emojis com moderação. Não inclua saudação redundante se já há nome.'
    )

    try:
        service = AIService()
        resposta = service.chat(
            prompt_name='whatsapp_message',
            user_message=user_message,
            cliente_id=None,
            user_id=getattr(current_user, 'id', None),
            functionality='mensagens',
            record=False,
        )
        conteudo = (resposta.get('content') or '').strip()
        if not conteudo:
            return jsonify({'success': False, 'error': 'IA não retornou conteúdo'}), 500

        return jsonify({'success': True, 'data': {'tipo': tipo, 'mensagem': conteudo}})
    except Exception as exc:
        logger.error('Erro no gerador de mensagens WhatsApp: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': f'Erro ao gerar mensagem: {exc}'}), 500


@admin_api_bp.route('/api/ia/dashboard-inteligente', methods=['GET'])
@login_required
def api_ia_dashboard_inteligente():
    """Retorna dados reais + narrativa IA para o Dashboard Inteligente."""
    raw_cliente_id = request.args.get('cliente_id')
    cliente_id = None
    if raw_cliente_id not in (None, ''):
        try:
            cliente_id = int(raw_cliente_id)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'cliente_id inválido'}), 400

    # Auto-resolver cliente da sessão
    if cliente_id is None:
        from flask import session
        cliente_id = session.get('current_client_id')
    if cliente_id is None:
        db_tmp = next(get_db())
        try:
            from database.models import UserClient
            uc = db_tmp.query(UserClient).filter(UserClient.user_id == current_user.id).order_by(UserClient.client_id.asc()).first()
            if uc:
                cliente_id = int(uc.client_id)
        except Exception:
            pass
        finally:
            db_tmp.close()
    if cliente_id is None:
        return jsonify({'success': False, 'error': 'Nenhum cliente vinculado'}), 400

    db = next(get_db())
    try:
        from datetime import datetime, timedelta
        hoje = datetime.now().date()

        # Período configurável: 'mes' (mês atual), ou N dias
        periodo = request.args.get('periodo', 'mes')
        if periodo == 'mes':
            inicio = hoje.replace(day=1)
            fim = hoje
            # Período anterior: mês anterior completo
            fim_ant = inicio - timedelta(days=1)
            inicio_ant = fim_ant.replace(day=1)
            label_periodo = f'{inicio.strftime("%d/%m")} a {fim.strftime("%d/%m/%Y")}'
        elif periodo == 'mes_ant':
            fim = hoje.replace(day=1) - timedelta(days=1)
            inicio = fim.replace(day=1)
            fim_ant = inicio - timedelta(days=1)
            inicio_ant = fim_ant.replace(day=1)
            label_periodo = f'{inicio.strftime("%d/%m")} a {fim.strftime("%d/%m/%Y")}'
        else:
            try:
                dias = int(periodo)
            except ValueError:
                dias = 30
            inicio = hoje - timedelta(days=dias - 1)
            fim = hoje
            inicio_ant = inicio - timedelta(days=dias)
            fim_ant = inicio - timedelta(days=1)
            label_periodo = f'Últimos {dias} dias'

        _filtro_fat = "status='AUTORIZADA' AND tipo_nfe='1' AND finalidade_emissao=1"
        _filtro_nfe = "status='AUTORIZADA' AND tipo_nfe='1'"

        r_periodo = db.execute(text(f"""
            SELECT
                COUNT(*) FILTER (WHERE {_filtro_nfe}) AS total_nfes,
                COALESCE(SUM(valor_total) FILTER (WHERE {_filtro_fat}), 0) AS faturamento,
                COUNT(DISTINCT destinatario_cnpj_cpf) FILTER (WHERE {_filtro_fat}) AS clientes_ativos,
                COALESCE(AVG(valor_total) FILTER (WHERE {_filtro_fat}), 0) AS ticket_medio,
                COUNT(*) FILTER (WHERE status='REJEITADA') AS nfes_rejeitadas,
                COUNT(*) FILTER (WHERE status='CANCELADA') AS nfes_canceladas
            FROM nfe_emitidas
            WHERE cliente_id = :cid AND data_emissao::date BETWEEN :ini AND :fim
        """), {'cid': cliente_id, 'ini': inicio, 'fim': fim}).fetchone()

        r_periodo_ant = db.execute(text(f"""
            SELECT
                COUNT(*) FILTER (WHERE {_filtro_nfe}) AS total_nfes,
                COALESCE(SUM(valor_total) FILTER (WHERE {_filtro_fat}), 0) AS faturamento
            FROM nfe_emitidas
            WHERE cliente_id = :cid AND data_emissao::date BETWEEN :ini AND :fim
        """), {'cid': cliente_id, 'ini': inicio_ant, 'fim': fim_ant}).fetchone()

        r_hoje = db.execute(text(f"""
            SELECT
                COUNT(*) FILTER (WHERE {_filtro_nfe}) AS nfes_hoje,
                COALESCE(SUM(valor_total) FILTER (WHERE {_filtro_fat}), 0) AS fat_hoje
            FROM nfe_emitidas
            WHERE cliente_id = :cid AND data_emissao::date = :hoje
        """), {'cid': cliente_id, 'hoje': hoje}).fetchone()

        # Top 5 produtos no período
        r_top_prods = db.execute(text("""
            SELECT
                item->>'descricao' AS descricao,
                COUNT(*) AS ocorrencias,
                COALESCE(SUM((item->>'valor_total')::numeric), 0) AS valor_total
            FROM nfe_emitidas,
                 jsonb_array_elements(json_nfe->'items') AS item
            WHERE cliente_id = :cid
              AND status='AUTORIZADA' AND tipo_nfe='1' AND finalidade_emissao=1
              AND data_emissao::date BETWEEN :ini AND :fim
            GROUP BY item->>'descricao'
            ORDER BY valor_total DESC
            LIMIT 5
        """), {'cid': cliente_id, 'ini': inicio, 'fim': fim}).fetchall()

        # Top 5 clientes no período
        r_top_clientes = db.execute(text(f"""
            SELECT destinatario_razao_social, COUNT(*) AS total_nfes,
                   COALESCE(SUM(valor_total), 0) AS faturamento
            FROM nfe_emitidas
            WHERE cliente_id = :cid AND {_filtro_fat}
              AND data_emissao::date BETWEEN :ini AND :fim
            GROUP BY destinatario_razao_social
            ORDER BY faturamento DESC LIMIT 5
        """), {'cid': cliente_id, 'ini': inicio, 'fim': fim}).fetchall()

        r_ultimas = db.execute(text("""
            SELECT numero, serie, status, tipo_nfe, finalidade_emissao,
                   destinatario_razao_social,
                   valor_total, data_emissao::date AS data_emissao
            FROM nfe_emitidas
            WHERE cliente_id = :cid
            ORDER BY data_emissao DESC, nfe_emitida_id DESC LIMIT 10
        """), {'cid': cliente_id}).fetchall()

        fat_atual = float(r_periodo.faturamento or 0)
        fat_anterior = float(r_periodo_ant.faturamento or 0)
        delta_fat = ((fat_atual - fat_anterior) / fat_anterior * 100) if fat_anterior > 0 else 0
        nfes_atual = int(r_periodo.total_nfes or 0)
        nfes_anterior = int(r_periodo_ant.total_nfes or 0)
        delta_nfes = ((nfes_atual - nfes_anterior) / nfes_anterior * 100) if nfes_anterior > 0 else 0

        fat_atual = float(r_periodo.faturamento or 0)
        fat_anterior = float(r_periodo_ant.faturamento or 0)
        delta_fat = ((fat_atual - fat_anterior) / fat_anterior * 100) if fat_anterior > 0 else 0
        nfes_atual = int(r_periodo.total_nfes or 0)
        nfes_anterior = int(r_periodo_ant.total_nfes or 0)
        delta_nfes = ((nfes_atual - nfes_anterior) / nfes_anterior * 100) if nfes_anterior > 0 else 0

        # Narrativa IA
        narrativa = None
        if AIService is not None:
            try:
                hora = datetime.now().hour
                saudacao = 'Bom dia' if hora < 12 else ('Boa tarde' if hora < 18 else 'Boa noite')
                nome_usuario = getattr(current_user, 'username', '') or getattr(current_user, 'name', 'usuário')
                top_prod_str = top_prod.get('descricao', 'não identificado') if (top_prod := dict(r_top._mapping) if r_top else None) else 'não identificado'

                prompt = (
                    f'{saudacao}, {nome_usuario}! Analise os dados e gere uma mensagem executiva curta (3-5 frases) '
                    f'com os destaques do negócio. Seja direto, use números reais, destaque o que é bom e sinalize alertas.\n\n'
                    f'Dados do período ({label_periodo}):\n'
                    f'- NF-es de saída: {nfes_atual} ({delta_nfes:+.1f}% vs período anterior)\n'
                    f'- Faturamento: R$ {fat_atual:,.2f} ({delta_fat:+.1f}% vs período anterior)\n'
                    f'- Clientes atendidos: {r_periodo.clientes_ativos or 0}\n'
                    f'- Ticket médio: R$ {float(r_periodo.ticket_medio or 0):,.2f}\n'
                    f'- Produto campeão: {r_top_prods[0].descricao if r_top_prods else "não identificado"}\n'
                    f'- NF-es emitidas hoje: {r_hoje.nfes_hoje or 0}\n'
                    f'- Faturamento hoje: R$ {float(r_hoje.fat_hoje or 0):,.2f}\n'
                )
                service = AIService()
                resp = service.chat(
                    prompt_name='assistant_business',
                    user_message=prompt,
                    cliente_id=cliente_id,
                    user_id=getattr(current_user, 'id', None),
                    functionality='dashboard',
                    record=False,
                )
                narrativa = (resp.get('content') or '').strip()
            except Exception as e:
                logger.warning('Dashboard narrativa IA falhou: %s', e)

        return jsonify({
            'success': True,
            'data': {
                'label_periodo': label_periodo,
                'periodo': periodo,
                'mes': {
                    'total_nfes': nfes_atual,
                    'faturamento': fat_atual,
                    'clientes_ativos': int(r_periodo.clientes_ativos or 0),
                    'ticket_medio': float(r_periodo.ticket_medio or 0),
                    'nfes_rejeitadas': int(r_periodo.nfes_rejeitadas or 0),
                    'nfes_canceladas': int(r_periodo.nfes_canceladas or 0),
                    'delta_nfes_pct': round(delta_nfes, 1),
                    'delta_faturamento_pct': round(delta_fat, 1),
                },
                'hoje': {
                    'nfes': int(r_hoje.nfes_hoje or 0),
                    'faturamento': float(r_hoje.fat_hoje or 0),
                },
                'top_produto': dict(r_top_prods[0]._mapping) if r_top_prods else None,
                'top_produtos': [dict(r._mapping) for r in r_top_prods],
                'top_clientes': [dict(r._mapping) for r in r_top_clientes],
                'ultimas_nfes': [
                    {
                        'numero': r.numero,
                        'serie': r.serie,
                        'status': r.status,
                        'tipo': 'Entrada' if r.tipo_nfe == '0' else ('Devolução' if r.finalidade_emissao == 4 else 'Saída'),
                        'destinatario_razao_social': r.destinatario_razao_social,
                        'valor': float(r.valor_total or 0),
                        'data_emissao': str(r.data_emissao),
                    }
                    for r in r_ultimas
                ],
                'narrativa_ia': narrativa,
            }
        })
    except Exception as exc:
        logger.error('Erro no dashboard inteligente: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Controle de Estoque
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/estoque/resumo', methods=['GET'])
@login_required
def api_estoque_resumo():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        inicio, fim = _parse_periodo_datas()
        filtro_produto = (request.args.get('filtro_produto') or '').strip()

        _ensure_estoque_caixa_tables(db)
        db.commit()

        row = db.execute(text("""
            SELECT
                COALESCE(SUM(CASE WHEN tipo_movimentacao = 'ENTRADA' THEN quantidade ELSE 0 END), 0) AS entradas,
                COALESCE(SUM(CASE WHEN tipo_movimentacao = 'SAIDA' THEN quantidade ELSE 0 END), 0) AS saidas,
                COALESCE(SUM(CASE WHEN tipo_movimentacao = 'ENTRADA' THEN quantidade ELSE -quantidade END), 0) AS saldo,
                COUNT(*) AS total_movimentacoes
            FROM estoque_movimentacoes
            WHERE cliente_id = :cid
              AND data_movimentacao::date BETWEEN :inicio AND :fim
        """), {'cid': cliente_id, 'inicio': inicio, 'fim': fim}).fetchone()

        params_produtos = {'cid': cliente_id}
        where_produto = ''
        if filtro_produto:
            where_produto = " AND p.descricao ILIKE :filtro_produto"
            params_produtos['filtro_produto'] = f'%{filtro_produto}%'

        produtos_estoque = db.execute(text(f"""
            SELECT
                p.produto_id,
                p.descricao,
                COALESCE(SUM(CASE WHEN em.tipo_movimentacao = 'ENTRADA' THEN em.quantidade ELSE -em.quantidade END), 0) AS saldo_produto
            FROM produtos p
            LEFT JOIN estoque_movimentacoes em ON em.produto_id = p.produto_id
            WHERE p.cliente_id = :cid{where_produto}
            GROUP BY p.produto_id, p.descricao
            ORDER BY saldo_produto ASC, p.descricao ASC
        """), params_produtos).fetchall()

        limite_baixo_estoque = 200 if filtro_produto else 20
        baixo_estoque = [
            {
                'produto_id': int(r.produto_id),
                'descricao': r.descricao,
                'saldo': float(r.saldo_produto or 0),
            }
            for r in produtos_estoque
            if float(r.saldo_produto or 0) <= 5
        ][:limite_baixo_estoque]

        return jsonify({
            'success': True,
            'data': {
                'cliente_id': cliente_id,
                'periodo': {
                    'data_inicio': inicio.isoformat(),
                    'data_fim': fim.isoformat(),
                },
                'filtro_produto': filtro_produto,
                'resumo': {
                    'entradas': float(row.entradas or 0),
                    'saidas': float(row.saidas or 0),
                    'saldo': float(row.saldo or 0),
                    'total_movimentacoes': int(row.total_movimentacoes or 0),
                },
                'baixo_estoque': baixo_estoque,
            },
        })
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao montar resumo de estoque: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/estoque/movimentacoes', methods=['GET'])
@login_required
def api_estoque_movimentacoes_listar():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        limit = max(1, min(request.args.get('limit', 50, type=int), 200))
        produto_id = request.args.get('produto_id', type=int)

        _ensure_estoque_caixa_tables(db)
        db.commit()

        filtros = ["em.cliente_id = :cid"]
        params = {'cid': cliente_id, 'limit': limit}
        if produto_id:
            filtros.append("em.produto_id = :produto_id")
            params['produto_id'] = produto_id

        rows = db.execute(text(f"""
            SELECT
                em.movimentacao_id,
                em.produto_id,
                p.descricao AS produto_descricao,
                em.tipo_movimentacao,
                em.quantidade,
                em.valor_unitario,
                em.observacao,
                em.data_movimentacao,
                em.created_by_user_id
            FROM estoque_movimentacoes em
            LEFT JOIN produtos p ON p.produto_id = em.produto_id
            WHERE {' AND '.join(filtros)}
            ORDER BY em.data_movimentacao DESC, em.movimentacao_id DESC
            LIMIT :limit
        """), params).fetchall()

        data = [
            {
                'movimentacao_id': int(r.movimentacao_id),
                'produto_id': int(r.produto_id) if r.produto_id is not None else None,
                'produto_descricao': r.produto_descricao,
                'tipo_movimentacao': r.tipo_movimentacao,
                'quantidade': float(r.quantidade or 0),
                'valor_unitario': float(r.valor_unitario) if r.valor_unitario is not None else None,
                'observacao': r.observacao,
                'data_movimentacao': r.data_movimentacao.isoformat() if r.data_movimentacao else None,
                'created_by_user_id': int(r.created_by_user_id) if r.created_by_user_id is not None else None,
            }
            for r in rows
        ]

        return jsonify({'success': True, 'data': data})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao listar movimentações de estoque: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/estoque/produtos', methods=['GET'])
@login_required
def api_estoque_produtos_listar():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        q = (request.args.get('q') or '').strip()
        limit = max(1, min(request.args.get('limit', 200, type=int), 500))

        params = {'cid': cliente_id, 'limit': limit}
        where_q = ''
        if q:
            where_q = " AND (p.descricao ILIKE :q OR p.codigo_interno ILIKE :q)"
            params['q'] = f'%{q}%'

        rows = db.execute(text(f"""
            SELECT p.produto_id, p.codigo_interno, p.descricao
            FROM produtos p
            WHERE p.cliente_id = :cid
              AND p.ativo = true{where_q}
            ORDER BY p.descricao
            LIMIT :limit
        """), params).fetchall()

        data = [
            {
                'produto_id': int(r.produto_id),
                'codigo_interno': r.codigo_interno,
                'descricao': r.descricao,
            }
            for r in rows
        ]

        return jsonify({'success': True, 'data': data})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao listar produtos para estoque: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/estoque/movimentacoes', methods=['POST'])
@login_required
def api_estoque_movimentacoes_criar():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        payload = request.get_json(silent=True) or {}

        produto_id = payload.get('produto_id')
        tipo_movimentacao = (payload.get('tipo_movimentacao') or '').strip().upper()
        quantidade = float(payload.get('quantidade') or 0)
        valor_unitario = payload.get('valor_unitario')
        valor_unitario = float(valor_unitario) if valor_unitario not in (None, '') else None
        observacao = payload.get('observacao')
        data_movimentacao = payload.get('data_movimentacao')

        if tipo_movimentacao not in {'ENTRADA', 'SAIDA'}:
            raise ValueError('tipo_movimentacao deve ser ENTRADA ou SAIDA')
        if quantidade <= 0:
            raise ValueError('quantidade deve ser maior que zero')
        if produto_id in (None, ''):
            raise ValueError('produto_id é obrigatório e deve ser de um produto cadastrado')

        _ensure_estoque_caixa_tables(db)

        produto_id = int(produto_id)
        produto = db.execute(text("""
            SELECT produto_id
            FROM produtos
            WHERE produto_id = :pid AND cliente_id = :cid AND ativo = true
            LIMIT 1
        """), {'pid': produto_id, 'cid': cliente_id}).fetchone()
        if not produto:
            raise PermissionError('Produto não encontrado para o cliente informado')

        dt_mov = None
        if data_movimentacao:
            dt_mov = datetime.strptime(data_movimentacao, '%Y-%m-%d')

        row = db.execute(text("""
            INSERT INTO estoque_movimentacoes (
                cliente_id, produto_id, tipo_movimentacao, quantidade,
                valor_unitario, observacao, data_movimentacao, created_by_user_id
            ) VALUES (
                :cid, :produto_id, :tipo_mov, :qtd,
                :valor_unitario, :obs, COALESCE(:dt_mov, NOW() AT TIME ZONE 'America/Sao_Paulo'), :uid
            )
            RETURNING movimentacao_id
        """), {
            'cid': cliente_id,
            'produto_id': produto_id,
            'tipo_mov': tipo_movimentacao,
            'qtd': quantidade,
            'valor_unitario': valor_unitario,
            'obs': observacao,
            'dt_mov': dt_mov,
            'uid': getattr(current_user, 'id', None),
        }).fetchone()

        db.commit()
        return jsonify({'success': True, 'movimentacao_id': int(row.movimentacao_id)}), 201
    except PermissionError as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.rollback()
        logger.error('Erro ao criar movimentação de estoque: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Fluxo de Caixa
# ─────────────────────────────────────────────────────────────────────────────

@admin_api_bp.route('/api/fluxo-caixa/categorias', methods=['GET'])
@login_required
def api_fluxo_caixa_categorias_listar():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        tipo_filtro = (request.args.get('tipo_lancamento') or '').strip().upper()
        _ensure_estoque_caixa_tables(db)
        db.commit()

        where_parts = ['cliente_id = :cid', 'ativo = true']
        params = {'cid': cliente_id}
        if tipo_filtro in {'RECEITA', 'DESPESA'}:
            where_parts.append('tipo_lancamento = :tipo')
            params['tipo'] = tipo_filtro
        where_sql = ' AND '.join(where_parts)

        rows = db.execute(text("""
            SELECT categoria_id, nome, tipo_lancamento, descricao, ativo, created_at
            FROM fluxo_caixa_categorias
            WHERE {where_sql}
            ORDER BY nome
        """.format(where_sql=where_sql)), params).fetchall()

        data = [
            {
                'categoria_id': int(r.categoria_id),
                'nome': r.nome,
                'tipo_lancamento': r.tipo_lancamento,
                'descricao': r.descricao,
                'ativo': bool(r.ativo),
                'created_at': r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

        return jsonify({'success': True, 'data': data})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao listar categorias de fluxo de caixa: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/fluxo-caixa/categorias', methods=['POST'])
@login_required
def api_fluxo_caixa_categorias_criar():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        payload = request.get_json(silent=True) or {}

        nome = (payload.get('nome') or '').strip()
        tipo_lancamento = (payload.get('tipo_lancamento') or '').strip().upper()
        descricao = (payload.get('descricao') or '').strip() or None
        if not nome:
            raise ValueError('nome da categoria é obrigatório')
        if tipo_lancamento not in {'RECEITA', 'DESPESA'}:
            raise ValueError('tipo_lancamento deve ser RECEITA ou DESPESA')

        _ensure_estoque_caixa_tables(db)

        existente = db.execute(text("""
            SELECT categoria_id, ativo
            FROM fluxo_caixa_categorias
            WHERE cliente_id = :cid
                            AND tipo_lancamento = :tipo
              AND LOWER(nome) = LOWER(:nome)
            LIMIT 1
                """), {'cid': cliente_id, 'tipo': tipo_lancamento, 'nome': nome}).fetchone()

        if existente and bool(existente.ativo):
            raise ValueError('Categoria já cadastrada para esta empresa')

        if existente and not bool(existente.ativo):
            db.execute(text("""
                UPDATE fluxo_caixa_categorias
                SET ativo = true,
                    tipo_lancamento = :tipo,
                    descricao = :descricao
                WHERE categoria_id = :categoria_id
            """), {
                'tipo': tipo_lancamento,
                'descricao': descricao,
                'categoria_id': int(existente.categoria_id),
            })
            categoria_id = int(existente.categoria_id)
        else:
            row = db.execute(text("""
                INSERT INTO fluxo_caixa_categorias (
                    cliente_id, nome, tipo_lancamento, descricao, created_by_user_id
                ) VALUES (
                    :cid, :nome, :tipo, :descricao, :uid
                )
                RETURNING categoria_id
            """), {
                'cid': cliente_id,
                'nome': nome,
                'tipo': tipo_lancamento,
                'descricao': descricao,
                'uid': getattr(current_user, 'id', None),
            }).fetchone()
            categoria_id = int(row.categoria_id)

        db.commit()
        return jsonify({'success': True, 'categoria_id': categoria_id}), 201
    except PermissionError as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.rollback()
        logger.error('Erro ao criar categoria de fluxo de caixa: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/fluxo-caixa/relatorio', methods=['GET'])
@login_required
def api_fluxo_caixa_relatorio():

    def _montar_relatorio(db, cliente_id, inicio, fim, tipo_filtro, categoria_filtro):
        where_parts = [
            'fcl.cliente_id = :cid',
            'fcl.data_lancamento::date BETWEEN :inicio AND :fim',
        ]
        params = {'cid': cliente_id, 'inicio': inicio, 'fim': fim}

        if tipo_filtro in {'RECEITA', 'DESPESA'}:
            where_parts.append('fcl.tipo_lancamento = :tipo')
            params['tipo'] = tipo_filtro

        if categoria_filtro:
            where_parts.append('fcl.categoria = :categoria')
            params['categoria'] = categoria_filtro

        where_sql = ' AND '.join(where_parts)

        resumo = db.execute(text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE 0 END), 0) AS receitas,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'DESPESA' THEN fcl.valor ELSE 0 END), 0) AS despesas,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE -fcl.valor END), 0) AS saldo,
                COUNT(*) AS total_lancamentos
            FROM fluxo_caixa_lancamentos fcl
            WHERE {where_sql}
        """), params).fetchone()

        por_categoria = db.execute(text(f"""
            SELECT
                fcl.categoria,
                fcl.tipo_lancamento,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE 0 END), 0) AS receitas,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'DESPESA' THEN fcl.valor ELSE 0 END), 0) AS despesas,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE -fcl.valor END), 0) AS saldo,
                COUNT(*) AS total_lancamentos
            FROM fluxo_caixa_lancamentos fcl
            WHERE {where_sql}
            GROUP BY fcl.categoria, fcl.tipo_lancamento
            ORDER BY fcl.categoria, fcl.tipo_lancamento
        """), params).fetchall()

        lancamentos = db.execute(text(f"""
            SELECT
                fcl.lancamento_id,
                fcl.tipo_lancamento,
                fcl.categoria,
                fcl.descricao,
                fcl.valor,
                fcl.forma_pagamento,
                fcl.observacao,
                fcl.data_lancamento,
                SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE -fcl.valor END)
                    OVER (ORDER BY fcl.data_lancamento ASC, fcl.lancamento_id ASC) AS saldo_acumulado
            FROM fluxo_caixa_lancamentos fcl
            WHERE {where_sql}
            ORDER BY fcl.data_lancamento DESC, fcl.lancamento_id DESC
            LIMIT 2000
        """), params).fetchall()

        return {
            'periodo': {
                'data_inicio': inicio.isoformat(),
                'data_fim': fim.isoformat(),
            },
            'filtros': {
                'tipo_lancamento': tipo_filtro if tipo_filtro in {'RECEITA', 'DESPESA'} else '',
                'categoria': categoria_filtro,
            },
            'resumo': {
                'receitas': float(resumo.receitas or 0),
                'despesas': float(resumo.despesas or 0),
                'saldo': float(resumo.saldo or 0),
                'total_lancamentos': int(resumo.total_lancamentos or 0),
            },
            'por_categoria': [
                {
                    'categoria': r.categoria,
                    'tipo_lancamento': r.tipo_lancamento,
                    'receitas': float(r.receitas or 0),
                    'despesas': float(r.despesas or 0),
                    'saldo': float(r.saldo or 0),
                    'total_lancamentos': int(r.total_lancamentos or 0),
                }
                for r in por_categoria
            ],
            'lancamentos': [
                {
                    'lancamento_id': int(r.lancamento_id),
                    'tipo_lancamento': r.tipo_lancamento,
                    'categoria': r.categoria,
                    'descricao': r.descricao,
                    'valor': float(r.valor or 0),
                    'forma_pagamento': r.forma_pagamento,
                    'observacao': r.observacao,
                    'data_lancamento': r.data_lancamento.isoformat() if r.data_lancamento else None,
                    'saldo_acumulado': float(r.saldo_acumulado or 0),
                }
                for r in lancamentos
            ],
        }

    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        inicio, fim = _parse_periodo_datas()
        tipo_filtro = (request.args.get('tipo_lancamento') or '').strip().upper()
        categoria_filtro = (request.args.get('categoria') or '').strip()

        _ensure_estoque_caixa_tables(db)
        db.commit()

        relatorio_data = _montar_relatorio(db, cliente_id, inicio, fim, tipo_filtro, categoria_filtro)

        return jsonify({
            'success': True,
            'data': relatorio_data,
        })
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao gerar relatório de fluxo de caixa: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/fluxo-caixa/relatorio/xlsx', methods=['GET'])
@login_required
def api_fluxo_caixa_relatorio_xlsx():

    def _montar_relatorio(db, cliente_id, inicio, fim, tipo_filtro, categoria_filtro):
        where_parts = [
            'fcl.cliente_id = :cid',
            'fcl.data_lancamento::date BETWEEN :inicio AND :fim',
        ]
        params = {'cid': cliente_id, 'inicio': inicio, 'fim': fim}

        if tipo_filtro in {'RECEITA', 'DESPESA'}:
            where_parts.append('fcl.tipo_lancamento = :tipo')
            params['tipo'] = tipo_filtro

        if categoria_filtro:
            where_parts.append('fcl.categoria = :categoria')
            params['categoria'] = categoria_filtro

        where_sql = ' AND '.join(where_parts)

        resumo = db.execute(text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE 0 END), 0) AS receitas,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'DESPESA' THEN fcl.valor ELSE 0 END), 0) AS despesas,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE -fcl.valor END), 0) AS saldo,
                COUNT(*) AS total_lancamentos
            FROM fluxo_caixa_lancamentos fcl
            WHERE {where_sql}
        """), params).fetchone()

        por_categoria = db.execute(text(f"""
            SELECT
                fcl.categoria,
                fcl.tipo_lancamento,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE 0 END), 0) AS receitas,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'DESPESA' THEN fcl.valor ELSE 0 END), 0) AS despesas,
                COALESCE(SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE -fcl.valor END), 0) AS saldo,
                COUNT(*) AS total_lancamentos
            FROM fluxo_caixa_lancamentos fcl
            WHERE {where_sql}
            GROUP BY fcl.categoria, fcl.tipo_lancamento
            ORDER BY fcl.categoria, fcl.tipo_lancamento
        """), params).fetchall()

        lancamentos = db.execute(text(f"""
            SELECT
                fcl.lancamento_id,
                fcl.tipo_lancamento,
                fcl.categoria,
                fcl.descricao,
                fcl.valor,
                fcl.forma_pagamento,
                fcl.observacao,
                fcl.data_lancamento,
                SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE -fcl.valor END)
                    OVER (ORDER BY fcl.data_lancamento ASC, fcl.lancamento_id ASC) AS saldo_acumulado
            FROM fluxo_caixa_lancamentos fcl
            WHERE {where_sql}
            ORDER BY fcl.data_lancamento DESC, fcl.lancamento_id DESC
            LIMIT 2000
        """), params).fetchall()

        return {
            'periodo': {
                'data_inicio': inicio.isoformat(),
                'data_fim': fim.isoformat(),
            },
            'filtros': {
                'tipo_lancamento': tipo_filtro if tipo_filtro in {'RECEITA', 'DESPESA'} else '',
                'categoria': categoria_filtro,
            },
            'resumo': {
                'receitas': float(resumo.receitas or 0),
                'despesas': float(resumo.despesas or 0),
                'saldo': float(resumo.saldo or 0),
                'total_lancamentos': int(resumo.total_lancamentos or 0),
            },
            'por_categoria': [
                {
                    'categoria': r.categoria,
                    'tipo_lancamento': r.tipo_lancamento,
                    'receitas': float(r.receitas or 0),
                    'despesas': float(r.despesas or 0),
                    'saldo': float(r.saldo or 0),
                    'total_lancamentos': int(r.total_lancamentos or 0),
                }
                for r in por_categoria
            ],
            'lancamentos': [
                {
                    'lancamento_id': int(r.lancamento_id),
                    'tipo_lancamento': r.tipo_lancamento,
                    'categoria': r.categoria,
                    'descricao': r.descricao,
                    'valor': float(r.valor or 0),
                    'forma_pagamento': r.forma_pagamento,
                    'observacao': r.observacao,
                    'data_lancamento': r.data_lancamento.isoformat() if r.data_lancamento else None,
                    'saldo_acumulado': float(r.saldo_acumulado or 0),
                }
                for r in lancamentos
            ],
        }

    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        inicio, fim = _parse_periodo_datas()
        tipo_filtro = (request.args.get('tipo_lancamento') or '').strip().upper()
        categoria_filtro = (request.args.get('categoria') or '').strip()

        _ensure_estoque_caixa_tables(db)
        db.commit()

        relatorio_data = _montar_relatorio(db, cliente_id, inicio, fim, tipo_filtro, categoria_filtro)

        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
        except ImportError:
            return jsonify({'success': False, 'error': 'Dependência openpyxl não instalada no servidor'}), 503

        wb = Workbook()
        ws_resumo = wb.active
        ws_resumo.title = 'Resumo'

        ws_resumo.append(['Relatório de Fluxo de Caixa'])
        ws_resumo.append(['Gerado em', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
        ws_resumo.append(['Cliente ID', cliente_id])
        ws_resumo.append(['Período', f"{relatorio_data['periodo']['data_inicio']} até {relatorio_data['periodo']['data_fim']}"])
        ws_resumo.append(['Tipo', relatorio_data['filtros']['tipo_lancamento'] or 'TODOS'])
        ws_resumo.append(['Categoria', relatorio_data['filtros']['categoria'] or 'TODAS'])
        ws_resumo.append([])

        ws_resumo.append(['Indicador', 'Valor'])
        ws_resumo.append(['Receitas', relatorio_data['resumo']['receitas']])
        ws_resumo.append(['Despesas', relatorio_data['resumo']['despesas']])
        ws_resumo.append(['Saldo', relatorio_data['resumo']['saldo']])
        ws_resumo.append(['Total de Lançamentos', relatorio_data['resumo']['total_lancamentos']])
        ws_resumo.append([])

        ws_resumo.append(['Categoria', 'Tipo', 'Receitas', 'Despesas', 'Saldo', 'Qtd'])
        for item in relatorio_data['por_categoria']:
            ws_resumo.append([
                item['categoria'] or '',
                item['tipo_lancamento'] or '',
                item['receitas'],
                item['despesas'],
                item['saldo'],
                item['total_lancamentos'],
            ])

        ws_lanc = wb.create_sheet('Lancamentos')
        ws_lanc.append(['Data', 'Tipo', 'Categoria', 'Descrição', 'Valor', 'Forma de Pagamento', 'Observação', 'Saldo Acumulado'])
        for item in relatorio_data['lancamentos']:
            ws_lanc.append([
                (item['data_lancamento'] or '')[:10],
                item['tipo_lancamento'] or '',
                item['categoria'] or '',
                item['descricao'] or '',
                item['valor'],
                item['forma_pagamento'] or '',
                item['observacao'] or '',
                item['saldo_acumulado'],
            ])

        bold = Font(bold=True)
        ws_resumo['A1'].font = bold
        ws_resumo['A8'].font = bold
        ws_resumo['A14'].font = bold
        for cell in ws_lanc[1]:
            cell.font = bold

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"relatorio_fluxo_caixa_{inicio.isoformat()}_{fim.isoformat()}.xlsx"
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}'},
        )
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao exportar relatório XLSX de fluxo de caixa: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()

@admin_api_bp.route('/api/fluxo-caixa/resumo', methods=['GET'])
@login_required
def api_fluxo_caixa_resumo():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        inicio, fim = _parse_periodo_datas()

        _ensure_estoque_caixa_tables(db)
        db.commit()

        row = db.execute(text("""
            SELECT
                COALESCE(SUM(CASE WHEN tipo_lancamento = 'RECEITA' THEN valor ELSE 0 END), 0) AS receitas,
                COALESCE(SUM(CASE WHEN tipo_lancamento = 'DESPESA' THEN valor ELSE 0 END), 0) AS despesas,
                COALESCE(SUM(CASE WHEN tipo_lancamento = 'RECEITA' THEN valor ELSE -valor END), 0) AS saldo,
                COUNT(*) AS total_lancamentos
            FROM fluxo_caixa_lancamentos
            WHERE cliente_id = :cid
              AND data_lancamento::date BETWEEN :inicio AND :fim
        """), {'cid': cliente_id, 'inicio': inicio, 'fim': fim}).fetchone()

        return jsonify({
            'success': True,
            'data': {
                'cliente_id': cliente_id,
                'periodo': {
                    'data_inicio': inicio.isoformat(),
                    'data_fim': fim.isoformat(),
                },
                'resumo': {
                    'receitas': float(row.receitas or 0),
                    'despesas': float(row.despesas or 0),
                    'saldo': float(row.saldo or 0),
                    'total_lancamentos': int(row.total_lancamentos or 0),
                },
            },
        })
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao montar resumo de fluxo de caixa: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/fluxo-caixa/lancamentos', methods=['GET'])
@login_required
def api_fluxo_caixa_lancamentos_listar():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        inicio, fim = _parse_periodo_datas()
        limit = max(1, min(request.args.get('limit', 100, type=int), 300))

        _ensure_estoque_caixa_tables(db)
        db.commit()

        rows = db.execute(text("""
            WITH base AS (
                SELECT
                    fcl.lancamento_id,
                    fcl.tipo_lancamento,
                    fcl.categoria,
                    fcl.descricao,
                    fcl.valor,
                    fcl.forma_pagamento,
                    fcl.observacao,
                    fcl.data_lancamento,
                    SUM(CASE WHEN fcl.tipo_lancamento = 'RECEITA' THEN fcl.valor ELSE -fcl.valor END)
                        OVER (ORDER BY fcl.data_lancamento ASC, fcl.lancamento_id ASC) AS saldo_acumulado
                FROM fluxo_caixa_lancamentos fcl
                WHERE fcl.cliente_id = :cid
                  AND fcl.data_lancamento::date BETWEEN :inicio AND :fim
            )
            SELECT *
            FROM base
            ORDER BY data_lancamento DESC, lancamento_id DESC
            LIMIT :limit
        """), {'cid': cliente_id, 'inicio': inicio, 'fim': fim, 'limit': limit}).fetchall()

        data = [
            {
                'lancamento_id': int(r.lancamento_id),
                'tipo_lancamento': r.tipo_lancamento,
                'categoria': r.categoria,
                'descricao': r.descricao,
                'valor': float(r.valor or 0),
                'forma_pagamento': r.forma_pagamento,
                'observacao': r.observacao,
                'data_lancamento': r.data_lancamento.isoformat() if r.data_lancamento else None,
                'saldo_acumulado': float(r.saldo_acumulado or 0),
            }
            for r in rows
        ]

        return jsonify({'success': True, 'data': data})
    except PermissionError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('Erro ao listar lançamentos do fluxo de caixa: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()


@admin_api_bp.route('/api/fluxo-caixa/lancamentos', methods=['POST'])
@login_required
def api_fluxo_caixa_lancamentos_criar():
    db = next(get_db())
    try:
        cliente_id = _resolve_cliente_id_admin_api()
        payload = request.get_json(silent=True) or {}

        tipo_lancamento = (payload.get('tipo_lancamento') or '').strip().upper()
        categoria = (payload.get('categoria') or '').strip()
        descricao = (payload.get('descricao') or '').strip()
        valor = float(payload.get('valor') or 0)
        forma_pagamento = payload.get('forma_pagamento')
        observacao = payload.get('observacao')
        data_lancamento = payload.get('data_lancamento')

        if tipo_lancamento not in {'RECEITA', 'DESPESA'}:
            raise ValueError('tipo_lancamento deve ser RECEITA ou DESPESA')
        if not categoria:
            raise ValueError('categoria é obrigatória')
        if not descricao:
            raise ValueError('descricao é obrigatória')
        if valor <= 0:
            raise ValueError('valor deve ser maior que zero')

        _ensure_estoque_caixa_tables(db)

        categoria_row = db.execute(text("""
                        SELECT nome, tipo_lancamento
            FROM fluxo_caixa_categorias
            WHERE cliente_id = :cid
              AND ativo = true
                            AND tipo_lancamento = :tipo
              AND LOWER(nome) = LOWER(:categoria)
            LIMIT 1
                """), {'cid': cliente_id, 'tipo': tipo_lancamento, 'categoria': categoria}).fetchone()
        if not categoria_row:
                        raise ValueError('Categoria inválida para o tipo informado. Cadastre ou selecione uma categoria correspondente à Receita/Despesa.')
        categoria = categoria_row.nome

        dt_lanc = None
        if data_lancamento:
            dt_lanc = datetime.strptime(data_lancamento, '%Y-%m-%d')

        row = db.execute(text("""
            INSERT INTO fluxo_caixa_lancamentos (
                cliente_id, tipo_lancamento, categoria, descricao,
                valor, forma_pagamento, observacao, data_lancamento, created_by_user_id
            ) VALUES (
                :cid, :tipo, :categoria, :descricao,
                :valor, :forma_pagamento, :obs,
                COALESCE(:dt_lanc, NOW() AT TIME ZONE 'America/Sao_Paulo'), :uid
            )
            RETURNING lancamento_id
        """), {
            'cid': cliente_id,
            'tipo': tipo_lancamento,
            'categoria': categoria,
            'descricao': descricao,
            'valor': valor,
            'forma_pagamento': forma_pagamento,
            'obs': observacao,
            'dt_lanc': dt_lanc,
            'uid': getattr(current_user, 'id', None),
        }).fetchone()

        db.commit()
        return jsonify({'success': True, 'lancamento_id': int(row.lancamento_id)}), 201
    except PermissionError as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 403
    except ValueError as exc:
        db.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.rollback()
        logger.error('Erro ao criar lançamento de fluxo de caixa: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        db.close()

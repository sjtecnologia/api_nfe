"""
routes/admin_api_routes.py

Blueprint com as rotas de API JSON do módulo admin.
Extrai as rotas puramente JSON (sem render_template) de admin_routes.py,
mantendo as URLs inalteradas (/admin/api/...).

Registrado em app.py com url_prefix='/admin'.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import requests
from sqlalchemy import text
from database.connection import get_db
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


@admin_api_bp.route('/api/ia/consultor-vendas/insights', methods=['GET'])
@login_required
def api_ia_consultor_vendas_insights():
    """Consultor de Vendas com comparativo de períodos e narrativa opcional por IA."""
    if gerar_resumo_consultor_vendas is None:
        return jsonify({'success': False, 'error': 'Consultor de vendas indisponível neste ambiente'}), 503

    raw_cliente_id = request.args.get('cliente_id')
    if raw_cliente_id in (None, ''):
        return jsonify({'success': False, 'error': 'Parâmetro cliente_id é obrigatório'}), 400

    try:
        cliente_id = int(raw_cliente_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Parâmetro cliente_id inválido'}), 400

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

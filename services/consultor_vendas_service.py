"""Serviços do Consultor de Vendas (MVP e rotinas diárias)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from database.connection import get_db
from services.auditoria_service import AuditoriaService
from services.email_service import EmailService

try:
    from services.ai_service import AIService
except ImportError:
    AIService = None


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return 0.0


def _gerar_insights_consultor_vendas(metricas: dict) -> list[str]:
    insights = []

    total_notas = int(metricas.get('total_notas') or 0)
    faturamento = float(metricas.get('faturamento') or 0)
    ticket_medio = float(metricas.get('ticket_medio') or 0)
    taxa_autorizacao = float(metricas.get('taxa_autorizacao') or 0)
    delta_faturamento_pct = float(metricas.get('delta_faturamento_pct') or 0)
    delta_notas_pct = float(metricas.get('delta_notas_pct') or 0)

    if total_notas == 0:
        insights.append('Nenhuma nota autorizada no período. Verifique operação comercial e fluxo de emissão.')
        return insights

    if delta_faturamento_pct >= 10:
        insights.append(f'Faturamento em alta: +{delta_faturamento_pct:.1f}% versus período anterior.')
    elif delta_faturamento_pct <= -10:
        insights.append(f'Faturamento em queda: {delta_faturamento_pct:.1f}% versus período anterior. Avalie campanha comercial e mix de produtos.')
    else:
        insights.append(f'Faturamento estável no período ({delta_faturamento_pct:.1f}% versus período anterior).')

    if delta_notas_pct <= -15:
        insights.append('Queda relevante na quantidade de notas. Priorize ações de recuperação de clientes recorrentes.')
    elif delta_notas_pct >= 15:
        insights.append('Volume de notas cresceu bem. Garanta estoque dos itens mais vendidos para sustentar ritmo.')

    insights.append(f'Ticket médio atual: R$ {ticket_medio:,.2f}. Faturamento total: R$ {faturamento:,.2f}.')

    if taxa_autorizacao < 90:
        insights.append(f'Taxa de autorização baixa ({taxa_autorizacao:.1f}%). Revise rejeições e dados fiscais dos cadastros.')
    else:
        insights.append(f'Taxa de autorização saudável ({taxa_autorizacao:.1f}%).')

    return insights


def _coletar_dados_vendas(db, cliente_id: int, days: int, referencia: Optional[datetime] = None) -> Dict[str, Any]:
    now = referencia or datetime.now()
    inicio_atual = now - timedelta(days=days)
    inicio_anterior = inicio_atual - timedelta(days=days)

    atual = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE UPPER(COALESCE(status, '')) = 'AUTORIZADA') AS notas_autorizadas,
            COUNT(*) AS notas_total,
            COALESCE(SUM(CASE WHEN UPPER(COALESCE(status, '')) = 'AUTORIZADA' THEN COALESCE(valor_total, 0) ELSE 0 END), 0) AS faturamento,
            COALESCE(AVG(CASE WHEN UPPER(COALESCE(status, '')) = 'AUTORIZADA' THEN COALESCE(valor_total, 0) END), 0) AS ticket_medio
        FROM nfe_emitidas
        WHERE cliente_id = :cliente_id
          AND data_criacao >= :inicio
          AND data_criacao < :fim
    """), {
        'cliente_id': cliente_id,
        'inicio': inicio_atual,
        'fim': now,
    }).fetchone()

    anterior = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE UPPER(COALESCE(status, '')) = 'AUTORIZADA') AS notas_autorizadas,
            COUNT(*) AS notas_total,
            COALESCE(SUM(CASE WHEN UPPER(COALESCE(status, '')) = 'AUTORIZADA' THEN COALESCE(valor_total, 0) ELSE 0 END), 0) AS faturamento,
            COALESCE(AVG(CASE WHEN UPPER(COALESCE(status, '')) = 'AUTORIZADA' THEN COALESCE(valor_total, 0) END), 0) AS ticket_medio
        FROM nfe_emitidas
        WHERE cliente_id = :cliente_id
          AND data_criacao >= :inicio
          AND data_criacao < :fim
    """), {
        'cliente_id': cliente_id,
        'inicio': inicio_anterior,
        'fim': inicio_atual,
    }).fetchone()

    top_produtos_rows = db.execute(text("""
        SELECT
            item->>'descricao' AS descricao,
            COUNT(*) AS total_ocorrencias,
            COALESCE(SUM(COALESCE((item->>'valor_total')::numeric, 0)), 0) AS valor_total
        FROM nfe_emitidas n
        CROSS JOIN LATERAL jsonb_array_elements(COALESCE(n.json_nfe->'items', '[]'::jsonb)) AS item
        WHERE n.cliente_id = :cliente_id
          AND n.data_criacao >= :inicio
          AND n.data_criacao < :fim
          AND UPPER(COALESCE(n.status, '')) = 'AUTORIZADA'
          AND item->>'descricao' IS NOT NULL
        GROUP BY item->>'descricao'
        ORDER BY total_ocorrencias DESC
        LIMIT 5
    """), {
        'cliente_id': cliente_id,
        'inicio': inicio_atual,
        'fim': now,
    }).fetchall()

    top_destinatarios_rows = db.execute(text("""
        SELECT
            COALESCE(destinatario_razao_social, 'Não informado') AS destinatario,
            COUNT(*) AS total_notas,
            COALESCE(SUM(COALESCE(valor_total, 0)), 0) AS faturamento
        FROM nfe_emitidas
        WHERE cliente_id = :cliente_id
          AND data_criacao >= :inicio
          AND data_criacao < :fim
          AND UPPER(COALESCE(status, '')) = 'AUTORIZADA'
        GROUP BY COALESCE(destinatario_razao_social, 'Não informado')
        ORDER BY faturamento DESC
        LIMIT 5
    """), {
        'cliente_id': cliente_id,
        'inicio': inicio_atual,
        'fim': now,
    }).fetchall()

    notas_atual = int((getattr(atual, 'notas_autorizadas', 0) if atual else 0) or 0)
    notas_total_atual = int((getattr(atual, 'notas_total', 0) if atual else 0) or 0)
    fat_atual = _to_float(getattr(atual, 'faturamento', 0) if atual else 0)
    ticket_atual = _to_float(getattr(atual, 'ticket_medio', 0) if atual else 0)

    notas_anterior = int((getattr(anterior, 'notas_autorizadas', 0) if anterior else 0) or 0)
    fat_anterior = _to_float(getattr(anterior, 'faturamento', 0) if anterior else 0)

    delta_faturamento_pct = ((fat_atual - fat_anterior) / fat_anterior * 100.0) if fat_anterior > 0 else (100.0 if fat_atual > 0 else 0.0)
    delta_notas_pct = ((notas_atual - notas_anterior) / notas_anterior * 100.0) if notas_anterior > 0 else (100.0 if notas_atual > 0 else 0.0)
    taxa_autorizacao = (notas_atual / notas_total_atual * 100.0) if notas_total_atual > 0 else 0.0

    metricas = {
        'cliente_id': cliente_id,
        'days': days,
        'total_notas': notas_atual,
        'total_notas_geral': notas_total_atual,
        'faturamento': fat_atual,
        'ticket_medio': ticket_atual,
        'faturamento_anterior': fat_anterior,
        'notas_anterior': notas_anterior,
        'delta_faturamento_pct': round(delta_faturamento_pct, 2),
        'delta_notas_pct': round(delta_notas_pct, 2),
        'taxa_autorizacao': round(taxa_autorizacao, 2),
    }

    top_produtos = [
        {
            'descricao': row.descricao,
            'total_ocorrencias': int(row.total_ocorrencias or 0),
            'valor_total': _to_float(row.valor_total),
        }
        for row in top_produtos_rows
    ]

    top_destinatarios = [
        {
            'destinatario': row.destinatario,
            'total_notas': int(row.total_notas or 0),
            'faturamento': _to_float(row.faturamento),
        }
        for row in top_destinatarios_rows
    ]

    return {
        'metricas': metricas,
        'insights': _gerar_insights_consultor_vendas(metricas),
        'top_produtos': top_produtos,
        'top_destinatarios': top_destinatarios,
        'periodo': {
            'inicio_atual': inicio_atual.isoformat(),
            'fim_atual': now.isoformat(),
            'inicio_anterior': inicio_anterior.isoformat(),
            'fim_anterior': inicio_atual.isoformat(),
        },
    }


def _gerar_narrativa_ia_consultor_vendas(
    cliente_id: int,
    metricas: Dict[str, Any],
    insights: List[str],
    top_produtos: List[Dict[str, Any]],
    top_destinatarios: List[Dict[str, Any]],
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    if AIService is None:
        return {'enabled': False, 'source': 'disabled', 'text': ''}

    resumo_struct = {
        'metricas': metricas,
        'insights_regras': insights,
        'top_produtos': top_produtos,
        'top_destinatarios': top_destinatarios,
    }

    mensagem = (
        'Atue como consultor de vendas para PMEs e gere um resumo executivo em portugues-BR. '
        'Use no maximo 6 bullets, foque em acoes praticas para os proximos 7 dias e destaque riscos. '
        'Dados estruturados: ' + str(resumo_struct)
    )

    try:
        resp = AIService().chat(
            prompt_name='assistant_business',
            user_message=mensagem,
            cliente_id=cliente_id,
            user_id=user_id,
            funcionalidade='consultor_vendas',
            contexto=resumo_struct,
            tools_scope='business',
            record=False,
        )
        text_out = (resp.get('content') or '').strip()
        return {
            'enabled': True,
            'source': 'ia' if text_out else 'fallback',
            'text': text_out,
            'model': resp.get('model'),
        }
    except Exception as exc:
        return {
            'enabled': True,
            'source': 'fallback',
            'text': '',
            'error': str(exc),
        }


def gerar_resumo_consultor_vendas(
    cliente_id: int,
    days: int = 30,
    user_id: Optional[int] = None,
    incluir_narrativa_ia: bool = True,
    referencia: Optional[datetime] = None,
) -> Dict[str, Any]:
    db = next(get_db())
    try:
        data = _coletar_dados_vendas(db, cliente_id=cliente_id, days=days, referencia=referencia)
        narrativa = {'enabled': False, 'source': 'disabled', 'text': ''}
        if incluir_narrativa_ia:
            narrativa = _gerar_narrativa_ia_consultor_vendas(
                cliente_id=cliente_id,
                metricas=data['metricas'],
                insights=data['insights'],
                top_produtos=data['top_produtos'],
                top_destinatarios=data['top_destinatarios'],
                user_id=user_id,
            )
        data['narrativa_ia'] = narrativa
        return data
    finally:
        db.close()


def _listar_destinatarios_cliente(db, cliente_id: int) -> List[str]:
    rows = db.execute(text("""
        SELECT c.email_contato
        FROM clientes c
        WHERE c.cliente_id = :cliente_id
        UNION
        SELECT u.email
        FROM user_clients uc
        JOIN users u ON u.id = uc.user_id
        WHERE uc.client_id = :cliente_id
    """), {'cliente_id': cliente_id}).fetchall()

    emails = []
    for row in rows:
        email = (row[0] or '').strip().lower()
        if email and '@' in email:
            emails.append(email)
    return sorted(set(emails))


def _montar_corpo_email_resumo(cliente_nome: str, resumo: Dict[str, Any]) -> str:
    m = resumo.get('metricas', {})
    insights = resumo.get('insights', [])
    narrativa = (resumo.get('narrativa_ia') or {}).get('text', '')

    html_insights = ''.join(f'<li>{i}</li>' for i in insights) or '<li>Sem insights no período.</li>'
    html_top_produtos = ''.join(
        f"<li>{p['descricao']} ({p['total_ocorrencias']} ocorrências, R$ {p['valor_total']:.2f})</li>"
        for p in resumo.get('top_produtos', [])
    ) or '<li>Sem dados</li>'
    html_top_dest = ''.join(
        f"<li>{d['destinatario']} ({d['total_notas']} notas, R$ {d['faturamento']:.2f})</li>"
        for d in resumo.get('top_destinatarios', [])
    ) or '<li>Sem dados</li>'

    bloco_ia = f"<h3>Narrativa IA</h3><p>{narrativa.replace(chr(10), '<br>')}</p>" if narrativa else ''

    return f"""
    <h2>Resumo diário de vendas - {cliente_nome}</h2>
    <p><strong>Período:</strong> últimos {m.get('days', 30)} dias</p>
    <ul>
      <li><strong>Notas autorizadas:</strong> {m.get('total_notas', 0)}</li>
      <li><strong>Faturamento:</strong> R$ {float(m.get('faturamento', 0)):.2f}</li>
      <li><strong>Ticket médio:</strong> R$ {float(m.get('ticket_medio', 0)):.2f}</li>
      <li><strong>Taxa de autorização:</strong> {float(m.get('taxa_autorizacao', 0)):.1f}%</li>
      <li><strong>Variação faturamento:</strong> {float(m.get('delta_faturamento_pct', 0)):.1f}%</li>
      <li><strong>Variação volume:</strong> {float(m.get('delta_notas_pct', 0)):.1f}%</li>
    </ul>

    <h3>Insights</h3>
    <ul>{html_insights}</ul>

    {bloco_ia}

    <h3>Top produtos</h3>
    <ul>{html_top_produtos}</ul>

    <h3>Top destinatários</h3>
    <ul>{html_top_dest}</ul>

    <p>Resumo enviado automaticamente pelo EmiteMax.</p>
    """


def executar_envio_diario_consultor_vendas() -> Dict[str, Any]:
    days = int(os.getenv('CONSULTOR_VENDAS_DAILY_DAYS', '1'))
    days = max(1, min(days, 30))
    include_ai = (os.getenv('CONSULTOR_VENDAS_DAILY_USE_AI', 'true').lower() == 'true')
    support_email = (os.getenv('CONSULTOR_VENDAS_EMAIL_SUPORTE', 'suporte@emitemax.com.br') or '').strip().lower()

    db = next(get_db())
    try:
        clientes = db.execute(text("""
            SELECT cliente_id, razao_social
            FROM clientes
            WHERE ativo = TRUE
            ORDER BY cliente_id
        """)).fetchall()

        enviados = 0
        falhas = []
        total_clientes = 0

        for c in clientes:
            cliente_id = int(c.cliente_id)
            cliente_nome = c.razao_social or f'Cliente {cliente_id}'
            total_clientes += 1
            try:
                resumo = gerar_resumo_consultor_vendas(
                    cliente_id=cliente_id,
                    days=days,
                    user_id=None,
                    incluir_narrativa_ia=include_ai,
                )

                destinatarios = _listar_destinatarios_cliente(db, cliente_id)
                if support_email and '@' in support_email:
                    destinatarios.append(support_email)
                destinatarios = sorted(set(destinatarios))

                if not destinatarios:
                    continue

                assunto = f"[EmiteMax] Resumo diário de vendas - {cliente_nome}"
                corpo = _montar_corpo_email_resumo(cliente_nome, resumo)

                for email in destinatarios:
                    result = EmailService().enviar_email(
                        destinatario=email,
                        assunto=assunto,
                        corpo_html=corpo,
                    )
                    if result.get('success'):
                        enviados += 1
                    else:
                        falhas.append({'cliente_id': cliente_id, 'email': email, 'erro': result.get('message')})
            except Exception as exc:
                falhas.append({'cliente_id': cliente_id, 'erro': str(exc)})

        AuditoriaService.registrar_acao(
            user_id=None,
            acao='AI_CONSULTOR_VENDAS_RESUMO_DIARIO',
            tabela_afetada='consultor_vendas',
            descricao='Execução diária do resumo de vendas por cliente',
            dados_depois={
                'clientes_processados': total_clientes,
                'emails_enviados': enviados,
                'falhas': falhas[:20],
                'days': days,
                'include_ai': include_ai,
            },
        )

        return {
            'success': True,
            'clientes_processados': total_clientes,
            'emails_enviados': enviados,
            'falhas': falhas,
            'days': days,
            'include_ai': include_ai,
        }
    finally:
        db.close()

"""
Auditoria diária de bloqueios do Assistente Fiscal.

Analisa eventos AI_ASSISTENTE_BLOQUEADO nas últimas 24h e envia alerta por email
quando encontra padrão suspeito.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import text

from database.connection import get_db
from services.auditoria_service import AuditoriaService
from services.email_service import EmailService


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _coletar_estatisticas_bloqueios(inicio: datetime, fim: datetime) -> Dict[str, Any]:
    db = next(get_db())
    try:
        resumo_row = db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(DISTINCT user_id) AS usuarios,
                    COUNT(DISTINCT registro_id) AS clientes
                FROM auditoria
                WHERE acao = 'AI_ASSISTENTE_BLOQUEADO'
                  AND timestamp >= :inicio
                  AND timestamp < :fim
                """
            ),
            {"inicio": inicio, "fim": fim},
        ).fetchone()

        top_usuarios_rows = db.execute(
            text(
                """
                SELECT
                    a.user_id,
                    COALESCE(u.username, 'desconhecido') AS username,
                    COUNT(*) AS total
                FROM auditoria a
                LEFT JOIN users u ON u.id = a.user_id
                WHERE a.acao = 'AI_ASSISTENTE_BLOQUEADO'
                  AND a.timestamp >= :inicio
                  AND a.timestamp < :fim
                GROUP BY a.user_id, u.username
                ORDER BY total DESC
                LIMIT 10
                """
            ),
            {"inicio": inicio, "fim": fim},
        ).fetchall()

        top_clientes_rows = db.execute(
            text(
                """
                SELECT
                    registro_id AS cliente_id,
                    COUNT(*) AS total
                FROM auditoria
                WHERE acao = 'AI_ASSISTENTE_BLOQUEADO'
                  AND timestamp >= :inicio
                  AND timestamp < :fim
                  AND registro_id IS NOT NULL
                GROUP BY registro_id
                ORDER BY total DESC
                LIMIT 10
                """
            ),
            {"inicio": inicio, "fim": fim},
        ).fetchall()

        total = int((resumo_row[0] or 0) if resumo_row else 0)
        usuarios = int((resumo_row[1] or 0) if resumo_row else 0)
        clientes = int((resumo_row[2] or 0) if resumo_row else 0)

        return {
            "total_bloqueios": total,
            "usuarios_afetados": usuarios,
            "clientes_afetados": clientes,
            "top_usuarios": [
                {
                    "user_id": r[0],
                    "username": r[1],
                    "total": int(r[2] or 0),
                }
                for r in top_usuarios_rows
            ],
            "top_clientes": [
                {
                    "cliente_id": r[0],
                    "total": int(r[1] or 0),
                }
                for r in top_clientes_rows
            ],
        }
    finally:
        db.close()


def _avaliar_anomalias(stats: Dict[str, Any]) -> List[str]:
    alertas: List[str] = []

    limite_total = _int_env("ASSISTENTE_AUDITORIA_ALERTA_TOTAL_BLOQUEIOS", 20)
    limite_usuario = _int_env("ASSISTENTE_AUDITORIA_ALERTA_BLOQUEIOS_POR_USUARIO", 8)
    limite_clientes = _int_env("ASSISTENTE_AUDITORIA_ALERTA_CLIENTES_AFETADOS", 5)

    total = int(stats.get("total_bloqueios") or 0)
    if total >= limite_total:
        alertas.append(
            f"Volume alto de bloqueios: {total} nas últimas 24h (limite {limite_total})."
        )

    for user_info in stats.get("top_usuarios", []):
        user_total = int(user_info.get("total") or 0)
        if user_total >= limite_usuario:
            username = user_info.get("username") or "desconhecido"
            alertas.append(
                f"Usuário com uso fora do padrão: {username} ({user_total} bloqueios, limite {limite_usuario})."
            )

    clientes_afetados = int(stats.get("clientes_afetados") or 0)
    if clientes_afetados >= limite_clientes:
        alertas.append(
            f"Muitos clientes com bloqueio: {clientes_afetados} nas últimas 24h (limite {limite_clientes})."
        )

    return alertas


def _montar_email_alerta(
    stats: Dict[str, Any],
    alertas: List[str],
    inicio: datetime,
    fim: datetime,
) -> tuple[str, str]:
    assunto = (
        "[EmiteMax] Alerta diário - bloqueios do Assistente Fiscal "
        f"({stats.get('total_bloqueios', 0)} ocorrências)"
    )

    linhas_alerta = "".join(f"<li>{a}</li>" for a in alertas)
    linhas_usuarios = "".join(
        f"<li>{u.get('username')} (user_id={u.get('user_id')}): {u.get('total')}</li>"
        for u in stats.get("top_usuarios", [])
    ) or "<li>Sem dados</li>"

    linhas_clientes = "".join(
        f"<li>cliente_id={c.get('cliente_id')}: {c.get('total')}</li>"
        for c in stats.get("top_clientes", [])
    ) or "<li>Sem dados</li>"

    corpo = f"""
    <h2>Alerta diário - Assistente Fiscal</h2>
    <p><strong>Janela analisada:</strong> {inicio.isoformat()} até {fim.isoformat()}</p>
    <p><strong>Total de bloqueios:</strong> {stats.get('total_bloqueios', 0)}</p>
    <p><strong>Usuários afetados:</strong> {stats.get('usuarios_afetados', 0)}</p>
    <p><strong>Clientes afetados:</strong> {stats.get('clientes_afetados', 0)}</p>

    <h3>Motivos do alerta</h3>
    <ul>{linhas_alerta}</ul>

    <h3>Top usuários com bloqueio</h3>
    <ul>{linhas_usuarios}</ul>

    <h3>Top clientes com bloqueio</h3>
    <ul>{linhas_clientes}</ul>

    <p>Este email foi enviado automaticamente pela auditoria diária do EmiteMax.</p>
    """

    return assunto, corpo


def _enviar_alerta_email(
    stats: Dict[str, Any],
    alertas: List[str],
    inicio: datetime,
    fim: datetime,
) -> Dict[str, Any]:
    destinatario = os.getenv("ASSISTENTE_AUDITORIA_EMAIL_DESTINO", "suporte@emitemax.com.br")
    assunto, corpo = _montar_email_alerta(stats, alertas, inicio, fim)

    resultado = EmailService().enviar_email(
        destinatario=destinatario,
        assunto=assunto,
        corpo_html=corpo,
    )

    return {
        "destinatario": destinatario,
        "success": bool(resultado.get("success")),
        "message": resultado.get("message"),
    }


def executar_auditoria_diaria_assistente(
    referencia: datetime | None = None,
    janela_horas: int = 24,
) -> Dict[str, Any]:
    fim = referencia or datetime.utcnow()
    inicio = fim - timedelta(hours=janela_horas)

    stats = _coletar_estatisticas_bloqueios(inicio, fim)
    alertas = _avaliar_anomalias(stats)

    envio_email = {
        "success": False,
        "destinatario": os.getenv("ASSISTENTE_AUDITORIA_EMAIL_DESTINO", "suporte@emitemax.com.br"),
        "message": "Sem envio (nenhuma anomalia).",
    }

    if alertas:
        envio_email = _enviar_alerta_email(stats, alertas, inicio, fim)

    AuditoriaService.registrar_acao(
        user_id=None,
        acao="AI_ASSISTENTE_AUDITORIA_DIARIA",
        tabela_afetada="assistente_ia",
        descricao="Execução da auditoria diária de bloqueios do assistente fiscal",
        dados_depois={
            "janela_inicio": inicio.isoformat(),
            "janela_fim": fim.isoformat(),
            "stats": stats,
            "alertas": alertas,
            "email": envio_email,
        },
    )

    return {
        "success": True,
        "janela_inicio": inicio.isoformat(),
        "janela_fim": fim.isoformat(),
        "stats": stats,
        "alertas": alertas,
        "email": envio_email,
    }

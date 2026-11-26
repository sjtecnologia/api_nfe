"""Serviço de notificações de orçamentos.

Centraliza a criação de notificações no sistema e o envio de e-mails para a
empresa assinante (e para o cliente do portal quando o orçamento é respondido).
"""
from __future__ import annotations

import logging
import threading
from html import escape

from sqlalchemy import text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notificações no sistema
# ---------------------------------------------------------------------------
def _usuarios_empresa(db, cliente_id: int) -> list[dict]:
    """Usuários internos da empresa que devem receber notificações."""
    rows = db.execute(text("""
        SELECT DISTINCT u.id, u.username, u.email
        FROM users u
        JOIN user_clients uc ON uc.user_id = u.id
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE uc.client_id = :cliente_id
          AND u._is_active = true
          AND LOWER(r.name) IN ('admin', 'super_admin')
        ORDER BY u.id
    """), {"cliente_id": cliente_id}).mappings().all()
    if rows:
        return [dict(row) for row in rows]

    # Fallback: usuário que criou o cadastro da empresa.
    fallback = db.execute(text("""
        SELECT u.id, u.username, u.email
        FROM clientes c
        JOIN users u ON u.id = c.created_by_user_id
        WHERE c.cliente_id = :cliente_id AND u._is_active = true
    """), {"cliente_id": cliente_id}).mappings().all()
    return [dict(row) for row in fallback]


def criar_notificacao(
    db,
    *,
    cliente_id: int,
    tipo: str,
    titulo: str,
    mensagem: str | None = None,
    link: str | None = None,
    referencia_tipo: str | None = None,
    referencia_id: int | None = None,
    user_id: int | None = None,
    enviar_email: bool = False,
    emails_extras: list[str] | None = None,
) -> None:
    """Cria uma notificação direcionada (user_id) ou para a empresa toda."""
    db.execute(text("""
        INSERT INTO notificacoes
            (cliente_id, user_id, tipo, titulo, mensagem, link, referencia_tipo, referencia_id)
        VALUES
            (:cliente_id, :user_id, :tipo, :titulo, :mensagem, :link, :referencia_tipo, :referencia_id)
    """), {
        "cliente_id": cliente_id,
        "user_id": user_id,
        "tipo": tipo,
        "titulo": titulo,
        "mensagem": mensagem,
        "link": link,
        "referencia_tipo": referencia_tipo,
        "referencia_id": referencia_id,
    })

    if enviar_email:
        destinatarios = set()
        if user_id:
            row = db.execute(text("SELECT email FROM users WHERE id = :id"), {"id": user_id}).first()
            if row and row.email:
                destinatarios.add(row.email)
        else:
            for usuario in _usuarios_empresa(db, cliente_id):
                if usuario.get("email"):
                    destinatarios.add(usuario["email"])
            cliente = db.execute(text(
                "SELECT email_contato FROM clientes WHERE cliente_id = :cliente_id"
            ), {"cliente_id": cliente_id}).first()
            if cliente and cliente.email_contato:
                destinatarios.add(cliente.email_contato)

        for email in emails_extras or []:
            if email:
                destinatarios.add(email)

        if destinatarios:
            enviar_email_notificacao(list(destinatarios), titulo, mensagem, link)


def notificar_empresa(
    db,
    *,
    cliente_id: int,
    tipo: str,
    titulo: str,
    mensagem: str | None = None,
    link: str | None = None,
    referencia_tipo: str | None = None,
    referencia_id: int | None = None,
    emails_extras: list[str] | None = None,
) -> list[int]:
    """Notifica todos os usuários internos da empresa. Retorna os IDs notificados."""
    usuarios = _usuarios_empresa(db, cliente_id)
    if not usuarios:
        criar_notificacao(
            db,
            cliente_id=cliente_id,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            link=link,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
            enviar_email=True,
            emails_extras=emails_extras,
        )
        return []

    ids = []
    for usuario in usuarios:
        criar_notificacao(
            db,
            cliente_id=cliente_id,
            user_id=usuario["id"],
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            link=link,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
        )
        ids.append(usuario["id"])

    # Um único e-mail para todos os endereços da empresa.
    emails = {u["email"] for u in usuarios if u.get("email")}
    for email in emails_extras or []:
        if email:
            emails.add(email)
    cliente = db.execute(text(
        "SELECT email_contato FROM clientes WHERE cliente_id = :cliente_id"
    ), {"cliente_id": cliente_id}).first()
    if cliente and cliente.email_contato:
        emails.add(cliente.email_contato)
    if emails:
        enviar_email_notificacao(list(emails), titulo, mensagem, link)
    return ids


def contar_notificacoes_nao_lidas(user_id: int | None, cliente_id: int | None = None) -> int:
    """Conta notificações não lidas do usuário (e da empresa, quando aplicável)."""
    if not user_id:
        return 0
    from database.connection import SessionLocal

    db = SessionLocal()
    try:
        if cliente_id:
            total = db.execute(text("""
                SELECT COUNT(*) FROM notificacoes
                WHERE lida = false
                  AND (user_id = :user_id OR (user_id IS NULL AND cliente_id = :cliente_id))
            """), {"user_id": int(user_id), "cliente_id": int(cliente_id)}).scalar()
        else:
            total = db.execute(text("""
                SELECT COUNT(*) FROM notificacoes
                WHERE lida = false AND user_id = :user_id
            """), {"user_id": int(user_id)}).scalar()
        return int(total or 0)
    except Exception as exc:  # tabela pode não existir antes da migração
        logger.warning("Falha ao contar notificações: %s", exc)
        return 0
    finally:
        db.close()


def listar_notificacoes(
    db,
    user_id: int,
    cliente_id: int | None = None,
    limite: int = 100,
    incluir_empresa: bool = True,
) -> list[dict]:
    """Lista notificações do usuário.

    ``incluir_empresa`` controla as notificações sem destinatário (user_id NULL),
    usadas para avisar a empresa toda. O portal do cliente final usa
    ``incluir_empresa=False`` para nunca exibir avisos internos da empresa.
    """
    filtro_empresa = cliente_id and incluir_empresa
    if filtro_empresa:
        rows = db.execute(text("""
            SELECT * FROM notificacoes
            WHERE user_id = :user_id OR (user_id IS NULL AND cliente_id = :cliente_id)
            ORDER BY lida ASC, created_at DESC
            LIMIT :limite
        """), {"user_id": int(user_id), "cliente_id": int(cliente_id), "limite": limite}).mappings().all()
    else:
        rows = db.execute(text("""
            SELECT * FROM notificacoes
            WHERE user_id = :user_id
            ORDER BY lida ASC, created_at DESC
            LIMIT :limite
        """), {"user_id": int(user_id), "limite": limite}).mappings().all()
    return [dict(row) for row in rows]


def marcar_notificacao_lida(db, notificacao_id: int, user_id: int, cliente_id: int | None = None) -> bool:
    filtro_cliente = "AND (user_id = :user_id OR (user_id IS NULL AND cliente_id = :cliente_id))" if cliente_id else "AND user_id = :user_id"
    params = {"notificacao_id": int(notificacao_id), "user_id": int(user_id)}
    if cliente_id:
        params["cliente_id"] = int(cliente_id)
    updated = db.execute(text(f"""
        UPDATE notificacoes
        SET lida = true, lida_em = CURRENT_TIMESTAMP
        WHERE notificacao_id = :notificacao_id {filtro_cliente}
    """), params).rowcount
    return bool(updated)


def marcar_todas_lidas(db, user_id: int, cliente_id: int | None = None) -> int:
    if cliente_id:
        updated = db.execute(text("""
            UPDATE notificacoes
            SET lida = true, lida_em = CURRENT_TIMESTAMP
            WHERE lida = false
              AND (user_id = :user_id OR (user_id IS NULL AND cliente_id = :cliente_id))
        """), {"user_id": int(user_id), "cliente_id": int(cliente_id)}).rowcount
    else:
        updated = db.execute(text("""
            UPDATE notificacoes
            SET lida = true, lida_em = CURRENT_TIMESTAMP
            WHERE lida = false AND user_id = :user_id
        """), {"user_id": int(user_id)}).rowcount
    return int(updated or 0)


# ---------------------------------------------------------------------------
# E-mail (executado em background para não travar a requisição)
# ---------------------------------------------------------------------------
def _url_absoluta(link: str | None) -> str:
    if not link:
        return ""
    if link.startswith("http://") or link.startswith("https://"):
        return link
    try:
        from flask import has_request_context, request
        if has_request_context():
            return request.url_root.rstrip("/") + link
    except Exception:
        pass
    base = ""
    try:
        import os
        base = (os.getenv("APP_BASE_URL") or "").rstrip("/")
    except Exception:
        pass
    return base + link


def _enviar_email_sync(destinatarios: list[str], titulo: str, mensagem: str | None, link: str | None) -> None:
    try:
        from services.email_service import EmailService

        url = _url_absoluta(link)
        corpo = f"""
        <html><body style="font-family:Arial,sans-serif;color:#263238">
          <h2 style="color:#0288D1">{escape(titulo)}</h2>
          <p>{escape(mensagem or '')}</p>
          {f'<p><a href="{escape(url)}" style="background:#0288D1;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none">Abrir no EmiteMax</a></p>' if url else ''}
          <p style="font-size:12px;color:#607D8B">Esta é uma notificação automática do EmiteMax.</p>
        </body></html>
        """
        service = EmailService()
        for destinatario in destinatarios:
            service.enviar_email(destinatario, titulo, corpo)
    except Exception as exc:
        logger.warning("Falha ao enviar e-mail de notificação: %s", exc)


def enviar_email_notificacao(destinatarios: list[str], titulo: str, mensagem: str | None, link: str | None) -> None:
    if not destinatarios:
        return
    # Resolve o link absoluto ainda no contexto da requisição (antes da thread).
    link_absoluto = _url_absoluta(link)
    thread = threading.Thread(
        target=_enviar_email_sync,
        args=(destinatarios, titulo, mensagem, link_absoluto),
        daemon=True,
        name="notificacao-orcamento-email",
    )
    thread.start()

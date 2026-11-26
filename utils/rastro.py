"""
Integração com o Rastro — sistema de rastreio de eventos em tempo real.

Envia eventos de erro para o endpoint de ingestão do Rastro de forma
assíncrona (fire-and-forget em thread separada), sem impactar a resposta
da requisição principal nem derrubar a aplicação em caso de falha.

Configuração via variáveis de ambiente:
    RASTRO_ENABLED          true/false  (padrão: false)
    RASTRO_INGEST_URL       URL base do endpoint de ingestão
    RASTRO_INGEST_TOKEN     Token gerado no painel do Rastro
    RASTRO_ORGANIZATION_SLUG  Slug da organização
    RASTRO_PROJECT_SLUG     Slug do projeto
    RASTRO_ENVIRONMENT      development / staging / production
    RASTRO_RELEASE          Versão ou build atual (ex.: 1.4.2)
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ── Configuração lida uma única vez no import ─────────────────────────────────

_ENABLED = os.getenv("RASTRO_ENABLED", "false").lower() == "true"
_INGEST_URL = os.getenv("RASTRO_INGEST_URL", "").rstrip("/")
_TOKEN = os.getenv("RASTRO_INGEST_TOKEN", "")
_ORG_SLUG = os.getenv("RASTRO_ORGANIZATION_SLUG", "")
_PROJECT_SLUG = os.getenv("RASTRO_PROJECT_SLUG", "")
_ENVIRONMENT = os.getenv("RASTRO_ENVIRONMENT", "production")
_RELEASE = os.getenv("RASTRO_RELEASE", "unknown")

# Timeout para a chamada HTTP ao Rastro (não bloqueia a thread principal)
_HTTP_TIMEOUT = 5  # segundos


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fingerprint(exc: BaseException | None, message: str) -> str:
    """
    Gera um fingerprint estável para deduplicação de issues.
    Usa tipo da exceção + primeiros 200 chars da mensagem.
    """
    base = f"{type(exc).__name__}:{message[:200]}" if exc else message[:200]
    return hashlib.sha256(base.encode()).hexdigest()[:32]


def _now_utc_iso() -> str:
    """Retorna timestamp UTC no formato ISO 8601 com sufixo Z (aceito pelo Rastro)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _send_payload(payload: dict[str, Any]) -> None:
    """Faz o POST para o Rastro. Executado em thread separada."""
    endpoint = f"{_INGEST_URL}/ingest/errors"
    headers = {
        "Content-Type": "application/json",
        "x-ingest-token": _TOKEN,
    }
    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=_HTTP_TIMEOUT)
        if resp.status_code == 202:
            logger.debug("Rastro: evento aceito (202) — fingerprint=%s", payload.get("fingerprint"))
        else:
            logger.warning(
                "Rastro: resposta inesperada %s — %s",
                resp.status_code,
                resp.text[:200],
            )
    except requests.exceptions.RequestException as http_err:
        # Falha silenciosa: Rastro fora do ar não deve impactar a aplicação
        logger.debug("Rastro: falha ao enviar evento — %s", http_err)


# ── API pública ───────────────────────────────────────────────────────────────

def capture_exception(
    exc: BaseException,
    level: str = "error",
    extra_message: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
) -> None:
    """
    Captura uma exceção e envia ao Rastro de forma assíncrona.

    Args:
        exc: Instância da exceção capturada.
        level: Severidade — "fatal" | "error" | "warning" | "info".
        extra_message: Prefixo opcional para a mensagem enviada.
        trace_id: ID de rastreio distribuído (opcional).
        span_id: ID do span atual (opcional).
    """
    if not _ENABLED:
        return

    if not _INGEST_URL or not _TOKEN:
        logger.warning(
            "Rastro: RASTRO_INGEST_URL ou RASTRO_INGEST_TOKEN não configurados; evento ignorado."
        )
        return

    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    message = extra_message or f"{type(exc).__name__}: {exc}"

    payload: dict[str, Any] = {
        "type": "error_event_v1",
        "organizationSlug": _ORG_SLUG,
        "projectSlug": _PROJECT_SLUG,
        "environment": _ENVIRONMENT,
        "release": _RELEASE,
        "timestamp": _now_utc_iso(),
        "message": message,
        "fingerprint": _fingerprint(exc, message),
        "level": level,
        "extra": {
            "traceback": tb_str[-4000:],  # limita para não estourar payload
        },
    }

    if trace_id:
        payload["traceId"] = trace_id
    if span_id:
        payload["spanId"] = span_id

    # Fire-and-forget: não bloqueia a requisição
    t = threading.Thread(target=_send_payload, args=(payload,), daemon=True)
    t.start()


def capture_message(
    message: str,
    level: str = "info",
    trace_id: str | None = None,
    span_id: str | None = None,
) -> None:
    """
    Envia uma mensagem/warning operacional ao Rastro (sem exceção associada).

    Args:
        message: Texto descritivo do evento.
        level: Severidade — "fatal" | "error" | "warning" | "info".
        trace_id: ID de rastreio distribuído (opcional).
        span_id: ID do span atual (opcional).
    """
    if not _ENABLED:
        return

    if not _INGEST_URL or not _TOKEN:
        return

    payload: dict[str, Any] = {
        "type": "error_event_v1",
        "organizationSlug": _ORG_SLUG,
        "projectSlug": _PROJECT_SLUG,
        "environment": _ENVIRONMENT,
        "release": _RELEASE,
        "timestamp": _now_utc_iso(),
        "message": message,
        "fingerprint": _fingerprint(None, message),
        "level": level,
    }

    if trace_id:
        payload["traceId"] = trace_id
    if span_id:
        payload["spanId"] = span_id

    t = threading.Thread(target=_send_payload, args=(payload,), daemon=True)
    t.start()

"""
Configuração centralizada de logging com suporte a JSON estruturado e data masking.

Em produção (FLASK_DEBUG=False) emite JSON (compatível com ELK/CloudWatch).
Em desenvolvimento (FLASK_DEBUG=True) emite texto legível.

Campos sensíveis nunca são gravados nos logs.
"""
import logging
import logging.config
import os
import re
import sys
from typing import Any

# Campos que jamais devem aparecer em logs
_SENSITIVE_KEYS = re.compile(
    r'(password|senha|password_hash|token|secret|pin|api_key|cert_key|master_key'
    r'|authorization|credit_card|cvv)',
    re.IGNORECASE,
)
_REDACTED = "***REDACTED***"


class SensitiveDataFilter(logging.Filter):
    """Remove campos sensíveis de qualquer mensagem ou argumento de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._mask(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: (_REDACTED if _SENSITIVE_KEYS.search(k) else v)
                               for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = type(record.args)(
                    _REDACTED if isinstance(a, str) and _SENSITIVE_KEYS.search(a) else a
                    for a in record.args
                )
        return True

    def _mask(self, text: str) -> str:
        # Redige padrões comuns no texto livre (ex: "password=abc123")
        return re.sub(
            r'(?i)(password|senha|token|pin|secret|api_key)[=:]\s*\S+',
            r'\1=' + _REDACTED,
            text,
        )


def configure_logging(level: int | None = None) -> None:
    """
    Configura o logging da aplicação.
    Deve ser chamado em app.py antes de registrar blueprints.

    - Produção: JSON via python-json-logger
    - Desenvolvimento: texto colorido legível

    Uso nos módulos:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Operação bem-sucedida: %s", descricao)
        logger.error("Falha em %s: %s", operacao, e, exc_info=True)
    """
    is_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    if level is None:
        level = logging.DEBUG if is_debug else logging.INFO

    sensitive_filter = SensitiveDataFilter()

    if is_debug:
        # Desenvolvimento: texto legível
        fmt = '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s'
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S'))
    else:
        # Produção: JSON estruturado
        try:
            from pythonjsonlogger import jsonlogger

            class _AppJsonFormatter(jsonlogger.JsonFormatter):
                def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
                    super().add_fields(log_record, record, message_dict)
                    log_record.setdefault('level', record.levelname)
                    log_record.setdefault('logger', record.name)
                    # request_id / user_id injetados via g (se disponível)
                    try:
                        from flask import g  # type: ignore
                        if hasattr(g, 'request_id'):
                            log_record['request_id'] = g.request_id
                        if hasattr(g, 'user_id'):
                            log_record['user_id'] = g.user_id
                    except RuntimeError:
                        pass  # fora do contexto de request

            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(_AppJsonFormatter('%(asctime)s %(level)s %(name)s %(message)s'))
        except ImportError:
            # fallback se python-json-logger não estiver instalado
            fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(fmt))

    handler.addFilter(sensitive_filter)

    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )

    # Silenciar libs externas muito verbosas
    for noisy in ('sqlalchemy.engine', 'werkzeug', 'urllib3', 'botocore', 'boto3'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

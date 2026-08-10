#!/usr/bin/env python3
"""Executa auditoria diária do Assistente Fiscal e dispara alerta por email quando necessário."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.assistente_auditoria_service import executar_auditoria_diaria_assistente  # noqa: E402


def main() -> int:
    try:
        resultado = executar_auditoria_diaria_assistente()
        print(json.dumps(resultado, ensure_ascii=False, default=str))
        return 0 if resultado.get("success") else 1
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

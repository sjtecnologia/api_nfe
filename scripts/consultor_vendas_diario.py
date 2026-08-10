#!/usr/bin/env python3
"""Executa envio diário do resumo do Consultor de Vendas por email."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.consultor_vendas_service import executar_envio_diario_consultor_vendas  # noqa: E402


def main() -> int:
    try:
        resultado = executar_envio_diario_consultor_vendas()
        print(json.dumps(resultado, ensure_ascii=False, default=str))
        return 0 if resultado.get("success") else 1
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

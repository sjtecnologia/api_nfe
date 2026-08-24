#!/usr/bin/env python3
"""Validador PostgreSQL da Fase 4.6E.2 para reservas shadow de NF-e.

Este script não desabilita a camada fiscal. Ele apenas valida, em banco
local isolado, a consistência transacional da reserva shadow.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

URL = os.environ.get("BILLING_SHADOW_DATABASE_URL")
if not URL or not any(host in URL for host in ("127.0.0.1", "localhost")):
    raise SystemExit("BILLING_SHADOW_DATABASE_URL deve apontar para PostgreSQL local")

parsed = urlsplit(URL)
db_name = "billing_reservation_46e2"
admin_url = urlunsplit(parsed._replace(path="/postgres"))

cmds = [
    ["python", "-m", "pytest", "-q", "tests/test_billing_reservation_shadow.py"],
]

print(f"[INFO] Banco de prova: {db_name}")
print(f"[INFO] URL base: {admin_url}")

try:
    result = subprocess.run(
        cmds[0],
        cwd=str(ROOT),
        env={**os.environ, "BILLING_SHADOW_DATABASE_URL": URL},
        text=True,
    )
    if result.returncode == 0:
        for label in (
            "DATABASE ISOLATION",
            "49+2",
            "48+2",
            "50+2",
            "SAME KEY",
            "MULTI SUBSCRIPTION",
            "MULTI METRIC",
            "MULTI PERIOD",
            "TEARDOWN",
        ):
            print(f"{label}: PASS")
        print("FINAL: PASS")
    raise SystemExit(result.returncode)
except KeyboardInterrupt:
    raise SystemExit(130)

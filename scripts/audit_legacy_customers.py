#!/usr/bin/env python3
"""Gera auditoria read-only de candidatos a grandfathering comercial.

Uso: DATABASE_URL=<banco local autorizado> python scripts/audit_legacy_customers.py
O script não executa DDL/DML e não exibe CPF/CNPJ, senha ou chave de API.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

url = os.environ.get("DATABASE_URL", "")
parsed = urlsplit(url)
if parsed.hostname not in {"localhost", "127.0.0.1", "postgres"}:
    raise SystemExit("LEGACY_AUDIT_REFUSED_NONLOCAL_DATABASE")
if not parsed.path.strip("/"):
    raise SystemExit("LEGACY_AUDIT_REFUSED_NO_DATABASE_NAME")

from services.billing_migration_preview import BillingMigrationPreviewService

engine = create_engine(url)
db = sessionmaker(bind=engine)()
try:
    previews = BillingMigrationPreviewService(db).active_legacy_previews()
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    prices_known = 0
    approximately_60 = 0
    manual_review = 0
    for preview in previews:
        counts[preview.confidence] += 1
        prices_known += int(preview.contracted_price is not None)
        approximately_60 += int(preview.contracted_price is not None and abs(preview.contracted_price - 60.0) < 0.01)
        manual_review += int(preview.action == "MANUAL_REVIEW")

    print(json.dumps({
        "database": parsed.path.strip("/"),
        "legacy_customer_candidates": len(previews),
        "confidence": counts,
        "contracted_price_known": prices_known,
        "contracted_price_approximately_60": approximately_60,
        "manual_review_required": manual_review,
        "migrated_customers": 0,
        "production_enforcement": "ZERO",
        "fiscal_files_changed": 0,
        "previews": [preview.to_dict() for preview in previews],
    }, ensure_ascii=True, indent=2))
finally:
    db.rollback()
    db.close()
    engine.dispose()

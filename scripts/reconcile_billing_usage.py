#!/usr/bin/env python3
"""Relatório read-only de reconciliação entre legado, documentos e shadow."""
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
url = os.getenv("BILLING_SHADOW_DATABASE_URL")
if not url or not any(host in url for host in ("127.0.0.1", "localhost")):
    raise SystemExit("BILLING_SHADOW_DATABASE_URL deve apontar para banco local")

engine = create_engine(url)
with engine.connect() as db:
    rows = db.execute(text("""
        SELECT a.cliente_id,
               a.nfes_consumidas AS legacy_count,
               COALESCE(SUM(CASE WHEN e.metric_key = 'NFE_ISSUED' AND e.status = 'COUNTED' THEN e.quantity ELSE 0 END), 0) AS shadow_count
        FROM assinaturas_cliente a
        LEFT JOIN billing_usage_events e ON e.cliente_id = a.cliente_id
        GROUP BY a.cliente_id, a.nfes_consumidas
        ORDER BY a.cliente_id
    """)).mappings()
    print("cliente_id,legacy_count,real_document_count,shadow_usage_count,delta")
    for row in rows:
        real_count = db.execute(text("""
            SELECT COUNT(*) FROM nfe_emitidas
            WHERE cliente_id = :cliente_id AND status = 'AUTORIZADA'
        """), {"cliente_id": row["cliente_id"]}).scalar() if db.dialect.has_table(db, "nfe_emitidas") else None
        shadow = int(row["shadow_count"] or 0)
        legacy = int(row["legacy_count"] or 0)
        print(f"{row['cliente_id']},{legacy},{real_count if real_count is not None else 'UNKNOWN'},{shadow},{legacy - shadow}")

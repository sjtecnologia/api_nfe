#!/usr/bin/env python3
"""Gera preview read-only da decisão de grandfathering para 5 clientes."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.legacy_grandfather_preview import build_preview

ALLOWED_HOSTS = {"localhost", "127.0.0.1", "postgres"}
APPROVED_IDS = (5, 11, 12, 13, 14)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="legacy_grandfather_preview.json")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL", "")
    parsed = urlsplit(url)
    if parsed.hostname not in ALLOWED_HOSTS or not parsed.path.strip("/"):
        raise SystemExit("BLOCKED_REAL_COMMERCIAL_DATABASE_NOT_AVAILABLE")

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                conn.execute(text("SET TRANSACTION READ ONLY"))
                if conn.execute(text("SELECT current_setting('transaction_read_only')")).scalar() != "on":
                    raise SystemExit("GRANDFATHER_PREVIEW_READ_ONLY_NOT_ENABLED")
                rows = conn.execute(text("""
                    SELECT c.cliente_id, COALESCE(c.ativo, TRUE) AS active,
                           a.assinatura_id, a.data_inicio, p.nome AS plan_name
                    FROM clientes c
                    LEFT JOIN assinaturas_cliente a
                      ON a.cliente_id=c.cliente_id AND a.status='ATIVA'
                    LEFT JOIN planos_nfe p ON p.plano_id=a.plano_id
                    WHERE c.cliente_id = ANY(:client_ids)
                    ORDER BY c.cliente_id, a.assinatura_id DESC NULLS LAST
                """), {"client_ids": list(APPROVED_IDS)}).mappings().all()
                by_client = {}
                for row in rows:
                    by_client.setdefault(row["cliente_id"], row)
                user_rows = conn.execute(text("""
                    SELECT uc.client_id, COUNT(DISTINCT uc.user_id) AS users
                    FROM user_clients uc JOIN users u ON u.id=uc.user_id
                    WHERE COALESCE(u._is_active, TRUE) AND uc.client_id = ANY(:client_ids)
                    GROUP BY uc.client_id
                """), {"client_ids": list(APPROVED_IDS)}).mappings()
                users = {row["client_id"]: int(row["users"]) for row in user_rows}
                previews = []
                for client_id in APPROVED_IDS:
                    row = by_client.get(client_id)
                    if row is None:
                        raise SystemExit(f"APPROVED_CLIENT_NOT_FOUND:{client_id}")
                    previews.append(build_preview(
                        cliente_id=client_id,
                        current_status="ACTIVE" if row["active"] else "INACTIVE",
                        current_plan=row["plan_name"],
                        subscription_id=row["assinatura_id"],
                        subscription_start=row["data_inicio"],
                        current_users=users.get(client_id, 0),
                        current_companies=1 if row["assinatura_id"] else 0,
                        decision_date=date.today().isoformat(),
                    ).to_dict())
                report = {
                    "decision_source": "MANUAL_BUSINESS_DECISION",
                    "historical_contract_evidence": "NOT_FOUND",
                    "customers_migrated": 0,
                    "database_writes": 0,
                    "previews": previews,
                }
                with open(args.output, "w", encoding="utf-8") as output:
                    json.dump(report, output, ensure_ascii=True, indent=2)
                print(json.dumps({
                    "total_reviewed": len(previews),
                    "grandfather_ready": sum(row["decision"] == "GRANDFATHER_READY" for row in previews),
                    "unchanged": sum(row["decision"] == "UNCHANGED_NO_COMMERCIAL_MIGRATION" for row in previews),
                    "price_confirmed": sum(row["price_confidence"] == "CONFIRMED" for row in previews),
                    "database_writes": 0,
                    "output": args.output,
                }, ensure_ascii=True, indent=2))
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

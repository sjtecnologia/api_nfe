#!/usr/bin/env python3
"""Reconstrói evidência contratual por cliente sem alterar banco ou arquivos-fonte."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text

ALLOWED_HOSTS = {"localhost", "127.0.0.1", "postgres"}
ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = sorted(
    path for path in (ROOT / "Documentacao").glob("*.docx")
    if "CONTRATO" in path.name.upper() or "RESUMO_CONTRATO" in path.name.upper()
)


def source_inventory():
    sources = []
    for path in SOURCE_PATHS:
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        sources.append({
            "source_type": "CONTRACT_TEMPLATE" if "CONTRATO" in path.name.upper() else "CONTRACT_SUMMARY",
            "source_file": str(path.relative_to(ROOT)),
            "source_date": datetime.fromtimestamp(path.stat().st_mtime).date().isoformat(),
            "source_confidence": "LOW",
            "client_related": False,
            "contains_sensitive_data": False,
            "eligible_for_human_review": True,
            "used_as_client_proof": False,
            "sha256": digest,
            "notes": "Documento genérico/template sem identificação vinculada a cliente real.",
        })
    return sources


def table_exists(conn, table):
    return bool(conn.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name=:table
    """), {"table": table}).scalar())


def run_review(conn):
    if conn.execute(text("SELECT current_setting('transaction_read_only')")).scalar() != "on":
        raise RuntimeError("CONTRACT_REVIEW_READ_ONLY_NOT_ENABLED")
    required = ("clientes", "planos_nfe", "assinaturas_cliente", "user_clients", "users")
    if not all(table_exists(conn, table) for table in required):
        raise RuntimeError("CONTRACT_REVIEW_REQUIRED_SCHEMA_UNAVAILABLE")

    clients = conn.execute(text("""
        SELECT cliente_id, COALESCE(ativo, TRUE) AS active
        FROM clientes ORDER BY cliente_id
    """)).mappings().all()
    subscriptions = conn.execute(text("""
        SELECT a.cliente_id, a.assinatura_id, a.data_inicio, a.status,
               a.nfes_consumidas, a.observacoes, p.nome AS plan_name,
               p.valor_mensal, p.quantidade_nfes, p.tipo_plano
        FROM assinaturas_cliente a
        LEFT JOIN planos_nfe p ON p.plano_id=a.plano_id
        ORDER BY a.cliente_id, a.updated_at DESC NULLS LAST, a.assinatura_id DESC
    """)).mappings().all()
    active_by_client = {}
    active_counts = Counter()
    for row in subscriptions:
        if row["status"] == "ATIVA":
            active_counts[row["cliente_id"]] += 1
            active_by_client.setdefault(row["cliente_id"], row)
    users = {row["client_id"]: int(row["user_count"]) for row in conn.execute(text("""
        SELECT uc.client_id, COUNT(DISTINCT uc.user_id) AS user_count
        FROM user_clients uc JOIN users u ON u.id=uc.user_id
        WHERE COALESCE(u._is_active, TRUE)
        GROUP BY uc.client_id
    """)).mappings()}

    def usage(client_id, days):
        if not table_exists(conn, "nfe_emitidas"):
            return None
        return int(conn.execute(text("""
            SELECT COUNT(*) FROM nfe_emitidas
            WHERE cliente_id=:client_id
              AND data_emissao >= CURRENT_DATE - (:days * INTERVAL '1 day')
              AND (status IS NULL OR status ILIKE 'AUTORIZ%')
        """), {"client_id": client_id, "days": days}).scalar() or 0)

    details = []
    for client in clients:
        client_id = client["cliente_id"]
        current = active_by_client.get(client_id)
        if current:
            plan = current["plan_name"]
            plan_match = bool(plan and any(marker in plan.casefold() for marker in ("básico", "basico", "legacy", "ilimitado")))
            catalog_r60 = current["valor_mensal"] is not None and float(current["valor_mensal"]) == 60.0
            reason_codes = ["LEGACY_PLAN_MATCH" if plan_match else "UNKNOWN_PLAN"]
            reason_codes.append("R60_PRICE_MATCH" if catalog_r60 else "PRICE_EVIDENCE_UNKNOWN")
            reason_codes.extend(["CLIENT_LINK_MISSING", "CONTRACTED_PRICE_UNKNOWN", "RIGHTS_UNKNOWN"])
            if users.get(client_id, 0) > 1:
                reason_codes.append("USER_CAPACITY_CONFLICT")
            recommended = "SPECIAL_CONTRACT_REVIEW" if users.get(client_id, 0) > 1 else "INSUFFICIENT_EVIDENCE"
        else:
            plan = None
            reason_codes = ["NO_SUBSCRIPTION", "CONTRACT_CLIENT_LINK_MISSING", "RIGHTS_UNKNOWN"]
            recommended = "NO_SUBSCRIPTION_REVIEW"
        details.append({
            "cliente_id": client_id,
            "price_evidence": "UNKNOWN",
            "price_confidence": "UNKNOWN",
            "contracted_price_candidate": None,
            "rights_evidence": {
                "nfe": "UNKNOWN", "nfce": "UNKNOWN", "nfse": "UNKNOWN",
                "users": "UNKNOWN", "companies": "UNKNOWN", "api": "UNKNOWN",
                "ai": "UNKNOWN", "support": "UNKNOWN",
            },
            "rights_confidence": "UNKNOWN",
            "source_references": [source["source_file"] for source in source_inventory()],
            "contract_date": None,
            "contract_status": "UNKNOWN",
            "plan_legacy_found": plan,
            "catalog_price": float(current["valor_mensal"]) if current and current["valor_mensal"] is not None else None,
            "users_current": users.get(client_id, 0),
            "companies_current": 1 if current else 0,
            "nfe_30d": usage(client_id, 30),
            "nfe_90d": usage(client_id, 90),
            "reason_codes": sorted(set(reason_codes)),
            "confidence": "LOW",
            "group": "GROUP_C" if current and users.get(client_id, 0) > 1 else "GROUP_E",
            "recommended_state": recommended,
            "manual_review_required": True,
            "notes": "Fonte documental genérica, sem vínculo nominal/contratual verificável com este cliente.",
        })
    return details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="legacy_contract_review.json")
    parser.add_argument("--inventory", default="CONTRACT_EVIDENCE_INVENTORY.md")
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
                details = run_review(conn)
                report = {"database_audited": True, "database_writes": 0, "sources": source_inventory(), "details": details}
                with open(args.output, "w", encoding="utf-8") as output:
                    json.dump(report, output, ensure_ascii=True, indent=2)
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
    print(json.dumps({"sources": len(report["sources"]), "total_reviewed": len(details), "price_confirmed": 0, "price_probable": 0, "price_unknown": len(details), "rights_confirmed": 0, "rights_probable": 0, "rights_unknown": len(details), "database_writes": 0, "output": args.output}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

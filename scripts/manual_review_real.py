#!/usr/bin/env python3
"""Gera dossiê administrativo read-only para revisão comercial manual."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text

ALLOWED_HOSTS = {"localhost", "127.0.0.1", "postgres"}


def table_exists(conn, table_name):
    return bool(conn.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name=:table
    """), {"table": table_name}).scalar())


def column_exists(conn, table_name, column_name):
    return bool(conn.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name=:table AND column_name=:column
    """), {"table": table_name, "column": column_name}).scalar())


def nfe_count(conn, days, client_id):
    if not table_exists(conn, "nfe_emitidas") or not column_exists(conn, "nfe_emitidas", "data_emissao"):
        return None
    return int(conn.execute(text("""
        SELECT COUNT(*) FROM nfe_emitidas
        WHERE cliente_id=:client_id
          AND data_emissao >= CURRENT_DATE - (:days * INTERVAL '1 day')
          AND (status IS NULL OR status ILIKE 'AUTORIZ%')
    """), {"client_id": client_id, "days": days}).scalar() or 0)


def simulate_plan(*, nfe_30d, company_count, user_count, rights_known, plan):
    limits = {
        "START_V1": (50, 1, 1),
        "ESSENCIAL_V1": (200, 1, 2),
        "PROFISSIONAL_V1": (500, 2, 5),
        "PREMIUM_V1": (None, 5, 10),
    }
    nfe_limit, company_limit, user_limit = limits[plan]
    conflicts = []
    if nfe_limit is not None and nfe_30d > nfe_limit:
        conflicts.append("NFE_CAPACITY_CONFLICT")
    if company_count > company_limit:
        conflicts.append("COMPANY_CAPACITY_CONFLICT")
    if user_count > user_limit:
        conflicts.append("USER_CAPACITY_CONFLICT")
    if not rights_known:
        return "CONTRACT_REVIEW", ["RIGHTS_UNKNOWN", *conflicts]
    return ("INCOMPATIBLE" if conflicts else "COMPATIBLE"), conflicts


def run_review(conn):
    if conn.execute(text("SELECT current_setting('transaction_read_only')")).scalar() != "on":
        raise RuntimeError("MANUAL_REVIEW_READ_ONLY_NOT_ENABLED")
    required = ("clientes", "planos_nfe", "assinaturas_cliente", "user_clients", "users")
    if not all(table_exists(conn, table) for table in required):
        raise RuntimeError("MANUAL_REVIEW_REQUIRED_SCHEMA_UNAVAILABLE")

    clients = conn.execute(text("""
        SELECT cliente_id, COALESCE(ativo, TRUE) AS active
        FROM clientes ORDER BY cliente_id
    """)).mappings().all()
    subscriptions = conn.execute(text("""
        SELECT a.cliente_id, a.assinatura_id, a.plano_id, a.status,
               a.data_inicio, a.data_fim, a.nfes_consumidas, a.observacoes,
               p.nome AS plan_name, p.tipo_plano, p.quantidade_nfes, p.valor_mensal
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

    user_counts = {row["client_id"]: int(row["users"]) for row in conn.execute(text("""
        SELECT uc.client_id, COUNT(DISTINCT uc.user_id) AS users
        FROM user_clients uc JOIN users u ON u.id=uc.user_id
        WHERE COALESCE(u._is_active, TRUE)
        GROUP BY uc.client_id
    """)).mappings()}

    details = []
    for client in clients:
        client_id = client["cliente_id"]
        legacy = active_by_client.get(client_id)
        users = user_counts.get(client_id, 0)
        companies = 1 if legacy else 0
        recent_30 = nfe_count(conn, 30, client_id)
        recent_90 = nfe_count(conn, 90, client_id)
        if legacy:
            plan_name = (legacy["plan_name"] or "").strip() or None
            plan_known = plan_name is not None
            legacy_match = plan_known and any(marker in plan_name.casefold() for marker in ("básico", "basico", "legacy", "ilimitado"))
            r60_match = legacy["valor_mensal"] is not None and legacy["valor_mensal"] == Decimal("60.00")
            rights_known = False
            reasons = ["LEGACY_PLAN_MATCH" if legacy_match else "UNKNOWN_PLAN"]
            reasons.append("R60_PRICE_MATCH" if r60_match else "PRICE_EVIDENCE_UNKNOWN")
            reasons.extend(["CONTRACTED_PRICE_UNKNOWN", "RIGHTS_UNKNOWN"])
            if users > 1:
                reasons.append("USER_CAPACITY_CONFLICT")
            if active_counts[client_id] > 1:
                reasons.extend(["MULTIPLE_ACTIVE_SUBSCRIPTIONS", "CONFLICTING_DATA"])
            simulations = {plan: simulate_plan(nfe_30d=recent_30 or 0, company_count=companies, user_count=users, rights_known=rights_known, plan=plan)[0] for plan in ("START_V1", "ESSENCIAL_V1", "PROFISSIONAL_V1", "PREMIUM_V1")}
            recommended_state = "SPECIAL_CONTRACT_REVIEW" if users > 1 or not rights_known else "GRANDFATHER_READY"
            group = "GROUP_C" if users > 1 else "GROUP_E"
        else:
            plan_name = None
            reasons = ["NO_SUBSCRIPTION", "RIGHTS_UNKNOWN"]
            rights_known = False
            simulations = {plan: "CONTRACT_REVIEW" for plan in ("START_V1", "ESSENCIAL_V1", "PROFISSIONAL_V1", "PREMIUM_V1")}
            recommended_state = "NO_SUBSCRIPTION_REVIEW"
            group = "GROUP_E"
        details.append({
            "cliente_id": client_id,
            "status": "ACTIVE" if client["active"] else "INACTIVE",
            "plan_current": plan_name,
            "subscription_id": legacy["assinatura_id"] if legacy else None,
            "subscription_start": legacy["data_inicio"].isoformat() if legacy and legacy["data_inicio"] else None,
            "catalog_price": float(legacy["valor_mensal"]) if legacy and legacy["valor_mensal"] is not None else None,
            "contracted_price_known": False,
            "contracted_price": None,
            "rights_evidence": "UNKNOWN",
            "users_current": users,
            "users_active_recently": None,
            "companies_current": companies,
            "nfe_30d": recent_30,
            "nfe_90d": recent_90,
            "features_relevant_used": "UNKNOWN",
            "api_right": "UNKNOWN",
            "ai_right": "UNKNOWN",
            "start_fit": simulations["START_V1"],
            "essential_fit": simulations["ESSENCIAL_V1"],
            "professional_fit": simulations["PROFISSIONAL_V1"],
            "premium_fit": simulations["PREMIUM_V1"],
            "recommended_state": recommended_state,
            "group": group,
            "reason_codes": sorted(set(reasons)),
            "confidence": "LOW",
            "manual_notes_required": True,
            "billing_account_candidate": None,
            "contract_holder_candidate": None,
            "subscription_candidate": None,
        })
    return details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="legacy_manual_review.json")
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
                report = {"database_audited": True, "database_writes": 0, "total_reviewed": len(details), "details": details}
                with open(args.output, "w", encoding="utf-8") as output:
                    json.dump(report, output, ensure_ascii=True, indent=2)
                summary = Counter(row["recommended_state"] for row in details)
                prices = Counter("UNKNOWN" if not row["contracted_price_known"] else "CONFIRMED" for row in details)
                rights = Counter(row["rights_evidence"] for row in details)
                print(json.dumps({"total_reviewed": len(details), "states": dict(summary), "price_evidence": dict(prices), "rights_evidence": dict(rights), "database_writes": 0, "output": args.output}, ensure_ascii=True, indent=2))
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

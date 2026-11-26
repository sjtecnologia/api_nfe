#!/usr/bin/env python3
"""Censo comercial real em modo estritamente read-only.

DATABASE_URL deve apontar para PostgreSQL local. Nenhuma migração, DDL ou DML
é executada; a transação usa SET TRANSACTION READ ONLY e sempre sofre rollback.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text


ALLOWED_HOSTS = {"localhost", "127.0.0.1", "postgres"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def table_exists(conn, table_name):
    return bool(conn.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = :table
    """), {"table": table_name}).scalar())


def column_exists(conn, table_name, column_name):
    return bool(conn.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table AND column_name = :column
    """), {"table": table_name, "column": column_name}).scalar())


def as_float(value):
    return float(value) if isinstance(value, Decimal) else value


def impact_level(*, monthly_nfe, company_count, user_count, unlimited_legacy, feature_conflict):
    conflicts = [monthly_nfe > 50, company_count > 1, user_count > 1, unlimited_legacy, feature_conflict]
    count = sum(conflicts)
    if unlimited_legacy or monthly_nfe > 50 or company_count > 1 or user_count > 1:
        return "BLOCKING_IMPACT"
    if count:
        return "HIGH_IMPACT"
    return "NO_IMPACT"


def run_census(conn):
    if conn.execute(text("SELECT current_setting('transaction_read_only')")).scalar() != "on":
        raise RuntimeError("CENSUS_READ_ONLY_NOT_ENABLED")
    required = {name: table_exists(conn, name) for name in ("clientes", "planos_nfe", "assinaturas_cliente")}
    if not all(required.values()):
        raise RuntimeError("CENSUS_REQUIRED_SCHEMA_UNAVAILABLE")

    clients = conn.execute(text("""
        SELECT cliente_id, COALESCE(ativo, TRUE) AS is_active
        FROM clientes
        ORDER BY cliente_id
    """)).mappings().all()
    client_status = {row["cliente_id"]: ("ACTIVE" if row["is_active"] else "INACTIVE") for row in clients}

    legacy_rows = conn.execute(text("""
        SELECT a.cliente_id, a.assinatura_id, a.plano_id, a.status,
               a.data_inicio, a.data_fim, a.nfes_consumidas,
               a.updated_at, p.nome, p.tipo_plano, p.quantidade_nfes, p.valor_mensal
        FROM assinaturas_cliente a
        LEFT JOIN planos_nfe p ON p.plano_id = a.plano_id
        ORDER BY a.cliente_id, a.updated_at DESC NULLS LAST, a.assinatura_id DESC
    """)).mappings().all()
    current_by_client = {}
    active_subscription_counts = Counter()
    for row in legacy_rows:
        if row["status"] == "ATIVA":
            active_subscription_counts[row["cliente_id"]] += 1
        if row["cliente_id"] not in current_by_client and row["status"] == "ATIVA":
            current_by_client[row["cliente_id"]] = row

    shadow_available = all(table_exists(conn, name) for name in (
        "billing_accounts", "billing_subscriptions", "billing_subscription_companies",
        "billing_plan_versions", "billing_plans",
    ))
    shadow_by_client = {}
    if shadow_available:
        shadow_rows = conn.execute(text("""
            SELECT sc.cliente_id, s.subscription_id, s.account_id,
                   s.contracted_price, v.version_code
            FROM billing_subscription_companies sc
            JOIN billing_subscriptions s ON s.subscription_id = sc.subscription_id
            JOIN billing_plan_versions v ON v.plan_version_id = s.plan_version_id
            WHERE sc.status = 'ACTIVE' AND s.status = 'ACTIVE'
        """)).mappings().all()
        shadow_by_client = {row["cliente_id"]: row for row in shadow_rows}

    user_counts = {}
    if table_exists(conn, "user_clients"):
        for row in conn.execute(text("""
            SELECT client_id AS cliente_id, COUNT(DISTINCT user_id) AS user_count
            FROM user_clients GROUP BY client_id
        """)).mappings():
            user_counts[row["cliente_id"]] = int(row["user_count"])

    monthly_nfe = Counter()
    nfe_available = table_exists(conn, "nfe_emitidas") and column_exists(conn, "nfe_emitidas", "data_emissao")
    if nfe_available:
        rows = conn.execute(text("""
            SELECT cliente_id, COUNT(*) AS total
            FROM nfe_emitidas
            WHERE data_emissao >= CURRENT_DATE - INTERVAL '30 days'
              AND (status IS NULL OR status IN ('AUTORIZADA', 'AUTORIZADA_COM_SUCESSO'))
            GROUP BY cliente_id
        """)).mappings()
        monthly_nfe = Counter({row["cliente_id"]: int(row["total"]) for row in rows})

    previews = []
    reason_counts = Counter()
    for cliente_id, legacy in current_by_client.items():
        plan_name = (legacy["nome"] or "").strip()
        normalized = plan_name.casefold()
        plan_known = bool(plan_name)
        legacy_identifiable = plan_known and any(marker in normalized for marker in ("legacy", "básico", "basico", "ilimitado"))
        r60 = legacy["valor_mensal"] is not None and legacy["valor_mensal"] == Decimal("60.00")
        unlimited = legacy["quantidade_nfes"] is None and legacy["tipo_plano"] == "PACOTE"
        shadow = shadow_by_client.get(cliente_id)
        price_known = shadow is not None and shadow["contracted_price"] is not None
        contracted_price = as_float(shadow["contracted_price"]) if price_known else None
        reasons = []
        if legacy_identifiable: reasons.append("LEGACY_PLAN_MATCH")
        if not plan_known: reasons.append("UNKNOWN_PLAN")
        if r60: reasons.append("R60_PRICE_MATCH")
        if price_known: reasons.append("CONTRACTED_PRICE_MATCH")
        if not price_known: reasons.append("MISSING_PRICE")
        if shadow: reasons.append("SHADOW_ALREADY_EXISTS")
        if unlimited: reasons.extend(["PACKAGE_UNLIMITED_LEGACY", "MANUAL_REVIEW_REQUIRED"])
        monthly = monthly_nfe.get(cliente_id, 0)
        feature_conflict = False
        impact = impact_level(monthly_nfe=monthly, company_count=1, user_count=user_counts.get(cliente_id, 0), unlimited_legacy=unlimited, feature_conflict=feature_conflict)
        if monthly > 50: reasons.append("NFE_OVER_START_LIMIT")
        if user_counts.get(cliente_id, 0) > 1: reasons.append("USER_CAPACITY_CONFLICT")
        if not shadow: reasons.append("SHADOW_MISSING")
        if active_subscription_counts[cliente_id] > 1:
            reasons.extend(["MULTIPLE_ACTIVE_SUBSCRIPTIONS", "CONFLICTING_DATA", "MANUAL_REVIEW_REQUIRED"])
        if unlimited or monthly > 50 or user_counts.get(cliente_id, 0) > 1 or active_subscription_counts[cliente_id] > 1 or not plan_known: confidence = "LOW"
        elif legacy_identifiable and price_known: confidence = "HIGH"
        elif legacy_identifiable or r60: confidence = "MEDIUM"
        else: confidence = "LOW"
        reason_counts.update(reasons)
        previews.append({
            "cliente_id": cliente_id,
            "current_plan": plan_name or None,
            "current_status": client_status.get(cliente_id, "UNKNOWN"),
            "contracted_price_known": price_known,
            "contracted_price": contracted_price,
            "legacy_candidate": True,
            "r60_candidate": r60,
            "suggested_plan": "LEGACY_START_V1",
            "confidence": confidence,
            "grandfathered": True,
            "impact_level": impact,
            "reason_codes": sorted(set(reasons)),
            "manual_review": True,
            "monthly_nfe_30d": monthly,
            "company_count": 1,
            "active_user_count": user_counts.get(cliente_id, 0),
            "already_shadow": bool(shadow),
        })

    for cliente_id, status in client_status.items():
        if cliente_id in current_by_client:
            continue
        reason_counts.update(["NO_SUBSCRIPTION", "MANUAL_REVIEW_REQUIRED"])
        previews.append({
            "cliente_id": cliente_id,
            "current_plan": None,
            "current_status": status,
            "contracted_price_known": False,
            "contracted_price": None,
            "legacy_candidate": False,
            "r60_candidate": False,
            "suggested_plan": "LEGACY_POLICY_REVIEW_REQUIRED",
            "confidence": "LOW",
            "grandfathered": False,
            "impact_level": "NO_IMPACT",
            "reason_codes": ["NO_SUBSCRIPTION", "MANUAL_REVIEW_REQUIRED"],
            "manual_review": True,
            "monthly_nfe_30d": 0,
            "company_count": 0,
            "active_user_count": user_counts.get(cliente_id, 0),
            "already_shadow": bool(shadow_by_client.get(cliente_id)),
        })

    legacy_candidates = [row for row in previews if row["legacy_candidate"]]
    return {
        "database_audited": True,
        "database_writes": 0,
        "total_clients": len(clients),
        "active": sum(status == "ACTIVE" for status in client_status.values()),
        "inactive": sum(status == "INACTIVE" for status in client_status.values()),
        "legacy_candidates": len(legacy_candidates),
        "r60_candidates": sum(row["r60_candidate"] for row in legacy_candidates),
        "confidence": dict(Counter(row["confidence"] for row in legacy_candidates)),
        "manual_review": sum(row["manual_review"] for row in previews),
        "known_price": sum(row["contracted_price_known"] for row in legacy_candidates),
        "unknown_price": sum(not row["contracted_price_known"] for row in legacy_candidates),
        "package_unlimited_legacy": sum("PACKAGE_UNLIMITED_LEGACY" in row["reason_codes"] for row in legacy_candidates),
        "over_50_nfe_month": sum(row["monthly_nfe_30d"] > 50 for row in legacy_candidates),
        "company_capacity_conflict": sum("COMPANY_CAPACITY_CONFLICT" in row["reason_codes"] for row in legacy_candidates),
        "user_capacity_conflict": sum("USER_CAPACITY_CONFLICT" in row["reason_codes"] for row in legacy_candidates),
        "feature_conflict": 0,
        "already_shadow": sum(row["already_shadow"] for row in legacy_candidates),
        "no_subscription": sum(not row["legacy_candidate"] for row in previews),
        "inconsistencies": sum("CONFLICTING_DATA" in row["reason_codes"] for row in previews),
        "reason_codes": dict(reason_counts),
        "shadow_schema_available": shadow_available,
        "nfe_history_available": nfe_available,
        "customers_migrated": 0,
        "production_enforcement": "ZERO",
        "fiscal_files_changed": 0,
        "previews": previews,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="arquivo JSON local para o relatório detalhado")
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
                report = run_census(conn)
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as output:
                        json.dump(report, output, ensure_ascii=True, indent=2)
                print(json.dumps({key: value for key, value in report.items() if key != "previews"}, ensure_ascii=True, indent=2))
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

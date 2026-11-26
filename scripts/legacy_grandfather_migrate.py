#!/usr/bin/env python3
"""Executor legacy controlado: dry-run por padrão, apply apenas em laboratório."""
from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.legacy_grandfather_migration import LegacyGrandfatherMigrationExecutor, LegacyMigrationSpec

APPROVED_LAB_IDS = {101, 102}
APPROVED_REAL_IDS = {11, 13}
LAB_PREFIX = "billing_legacy_migration_test_"


def validate_target(url: str, *, apply: bool) -> None:
    parsed = urlsplit(url)
    database = parsed.path.strip("/")
    environment = os.getenv("ENVIRONMENT", os.getenv("FLASK_ENV", "")).lower()
    lab_enabled = os.getenv("LEGACY_MIGRATION_LAB", "").lower() in {"1", "true", "yes", "on"}
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise SystemExit("REFUSE_PRODUCTION_WRITE" if apply else "REFUSE_NONLOCAL_TARGET")
    real_authorized = os.getenv("REAL_LEGACY_MIGRATION_AUTHORIZED", "").lower() in {"1", "true", "yes", "on"}
    if apply and database == "sjtnfe" and not real_authorized:
        raise SystemExit("REFUSE_PRODUCTION_WRITE")
    if apply and database != "sjtnfe" and not database.startswith(LAB_PREFIX):
        raise SystemExit("REFUSE_PRODUCTION_WRITE")
    if not apply and database != "sjtnfe" and not database.startswith(LAB_PREFIX):
        raise SystemExit("REFUSE_NON_LAB_TARGET")
    if apply and (environment == "production" or (not lab_enabled and not real_authorized)):
        raise SystemExit("REFUSE_PRODUCTION_WRITE")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--client-id", type=int, action="append", dest="client_ids")
    parser.add_argument("--dry-run", action="store_true", help="somente simulação; padrão")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-controlled-legacy-migration", action="store_true")
    parser.add_argument("--fail-after-account", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.dry_run and args.apply:
        raise SystemExit("DRY_RUN_APPLY_CONFLICT")
    if not args.database_url:
        raise SystemExit("LAB_DATABASE_URL_REQUIRED")
    validate_target(args.database_url, apply=args.apply)
    if args.apply and not args.confirm_controlled_legacy_migration:
        raise SystemExit("EXPLICIT_CONFIRMATION_REQUIRED")
    real_target = urlsplit(args.database_url).path.strip("/") == "sjtnfe"
    client_ids = args.client_ids or sorted(APPROVED_REAL_IDS if real_target else APPROVED_LAB_IDS)
    approved_ids = APPROVED_REAL_IDS if real_target else APPROVED_LAB_IDS
    if any(client_id not in approved_ids for client_id in client_ids):
        raise SystemExit("NOT_APPROVED_FOR_MIGRATION")

    engine = create_engine(args.database_url)
    Session = sessionmaker(bind=engine)
    results = []
    try:
        for client_id in client_ids:
            session = Session()
            try:
                if not args.apply:
                    session.execute(text("SET TRANSACTION READ ONLY"))
                user_count = session.execute(text("SELECT COUNT(DISTINCT user_id) FROM user_clients WHERE client_id=:client_id"), {"client_id": client_id}).scalar()
                if args.apply:
                    session.rollback()
                spec = LegacyMigrationSpec(cliente_id=client_id, current_users=int(user_count or 0), current_companies=1, contracted_price=Decimal("60.00"))
                executor = LegacyGrandfatherMigrationExecutor(session)
                if args.apply:
                    with session.begin():
                        result = executor.apply(spec, fail_after_account=args.fail_after_account)
                else:
                    result = executor.preview(spec)
                    session.rollback()
                results.append(result.to_dict())
            finally:
                session.close()
    finally:
        engine.dispose()
    print(json.dumps({"mode": "APPLY" if args.apply else "DRY_RUN", "database_writes": int(args.apply), "results": results}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

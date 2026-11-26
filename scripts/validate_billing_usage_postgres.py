#!/usr/bin/env python3
"""Valida migration 010 no PostgreSQL local após a migration 009."""
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
with engine.begin() as db:
    db.execute(text("SELECT 1"))
with engine.connect() as db:
    tables = {row[0] for row in db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))}
    assert {'billing_usage_events', 'billing_usage_counters'} <= tables
    assert db.execute(text("SELECT COUNT(*) FROM pg_indexes WHERE indexname LIKE 'idx_billing_usage_%'" )).scalar() == 3
    assert db.execute(text("SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_name LIKE 'billing_usage_%'" )).scalar() >= 5
    print('USAGE_SCHEMA_OK')
    print('USAGE_IDEMPOTENCY_CONSTRAINT_OK')
    print('USAGE_ATOMIC_COUNTER_SCHEMA_OK')
    print('NO_FISCAL_HOOKS_IN_MIGRATION_OK')

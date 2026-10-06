import os
import threading
import uuid
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from database.models import Base
from services.legacy_grandfather_migration import LegacyGrandfatherMigrationExecutor, LegacyMigrationSpec
from scripts.legacy_grandfather_migrate import main as migrate_main, validate_target


@pytest.fixture(scope="module")
def migration_db():
    admin_url = os.getenv("BILLING_SHADOW_DATABASE_URL", "postgresql://postgres@localhost:5432/postgres")
    if not any(host in admin_url for host in ("localhost", "127.0.0.1")):
        pytest.skip("PostgreSQL local não configurado")
    parsed = urlsplit(admin_url)
    name = f"billing_legacy_migration_test_{os.getpid()}_{uuid.uuid4().hex[:8]}"
    admin = create_engine(urlunsplit(parsed._replace(path="/postgres")), poolclass=NullPool)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"CREATE DATABASE {name}"))
    engine = create_engine(urlunsplit(parsed._replace(path=f"/{name}")), poolclass=NullPool)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO regimes_tributarios (regime_tributario_id,nome,crt) VALUES (1,'Simples',1)"))
        for client_id in (101, 102):
            conn.execute(text("""
                INSERT INTO clientes (cliente_id, cnpj, produtor_rural, razao_social, nome_fantasia,
                    regime_tributario_id, logradouro, numero, bairro, codigo_municipio,
                    nome_municipio, uf, cep, ambiente, ativo, data_cadastro, data_atualizacao)
                VALUES (:id, :cnpj, false, :name, :name, 1, 'Rua Lab', '1', 'Centro',
                    '3550308', 'Sao Paulo', 'SP', '01000000', 2, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """), {"id": client_id, "cnpj": f"99999999000{client_id}", "name": f"Legacy Lab {client_id}"})
    yield engine
    engine.dispose()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": name})
        conn.execute(text(f"DROP DATABASE IF EXISTS {name}"))
    admin.dispose()


def spec(client_id=101):
    return LegacyMigrationSpec(cliente_id=client_id, current_users=2 if client_id == 101 else 3, current_companies=1)


def counts(session):
    return tuple(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() for table in (
        "billing_accounts", "billing_subscriptions", "billing_subscription_companies", "billing_subscription_overrides"))


def test_dry_run_has_zero_writes_and_reports_legacy_policy(migration_db):
    Session = sessionmaker(bind=migration_db)
    session = Session()
    before = counts(session)
    session.rollback()
    with session.begin():
        result = LegacyGrandfatherMigrationExecutor(session).preview(spec())
    after = counts(session)
    session.close()
    assert result.status == "WOULD_MIGRATE"
    assert "BillingAccount" in result.objects_to_create
    assert "LEGACY_QUOTA_PRESERVED" in result.warnings
    assert before == after == (0, 0, 0, 0)


def test_apply_is_idempotent_and_preserves_users_price_and_quota(migration_db):
    Session = sessionmaker(bind=migration_db)
    session = Session()
    with session.begin():
        first = LegacyGrandfatherMigrationExecutor(session).apply(spec())
    session.close()
    session = Session()
    before = counts(session)
    session.rollback()
    with session.begin():
        second = LegacyGrandfatherMigrationExecutor(session).apply(spec())
    row = session.execute(text("""
        SELECT s.contracted_price, s.currency, v.version_code,
               u.value, c.value, f.limit_type, f.metadata_json
        FROM billing_subscriptions s
        JOIN billing_plan_versions v ON v.plan_version_id=s.plan_version_id
        JOIN billing_subscription_overrides u ON u.subscription_id=s.subscription_id AND u.key='MAX_USERS'
        JOIN billing_subscription_overrides c ON c.subscription_id=s.subscription_id AND c.key='MAX_COMPANIES'
        JOIN billing_plan_features f ON f.plan_version_id=v.plan_version_id
        JOIN billing_features bf ON bf.feature_id=f.feature_id AND bf.key='NFE_MONTHLY'
    """)).first()
    after = counts(session)
    session.close()
    assert first.status == "MIGRATED"
    assert second.status == "ALREADY_MIGRATED"
    assert before == after == (1, 1, 1, 2)
    assert row[0] == Decimal("60.00") and row[1] == "BRL" and row[2] == "LEGACY_60_V1"
    assert row[3] == "2" and row[4] == "1" and row[5] == "CONTRACTUAL"
    assert "LEGACY_PRESERVED" in row[6]
    assert session.execute(text("""
        SELECT COUNT(*) FROM billing_plan_features pf
        JOIN billing_plan_versions v ON v.plan_version_id=pf.plan_version_id AND v.version_code='LEGACY_60_V1'
        JOIN billing_features f ON f.feature_id=pf.feature_id AND f.key='AI_INSIGHTS_CENTER'
        WHERE pf.enabled = false AND pf.limit_type = 'DISABLED'
    """)).scalar() == 1


def test_failure_after_account_rolls_back_completely(migration_db):
    Session = sessionmaker(bind=migration_db)
    session = Session()
    with pytest.raises(RuntimeError, match="INJECTED_FAILURE_AFTER_ACCOUNT"):
        with session.begin():
            LegacyGrandfatherMigrationExecutor(session).apply(spec(102), fail_after_account=True)
    assert counts(session) == (1, 1, 1, 2)
    session.close()


def test_concurrent_apply_creates_one_representation(migration_db):
    Session = sessionmaker(bind=migration_db)
    results, errors = [], []
    session = Session()
    before = session.execute(text("SELECT COUNT(*) FROM billing_subscription_companies WHERE cliente_id=102")).scalar()
    session.close()

    def worker():
        session = Session()
        try:
            with session.begin():
                results.append(LegacyGrandfatherMigrationExecutor(session).apply(spec(102)).status)
        except BaseException as exc:
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(timeout=30)
    assert not errors, errors
    assert sorted(results) == ["ALREADY_MIGRATED", "MIGRATED"]
    session = Session()
    after = session.execute(text("SELECT COUNT(*) FROM billing_subscription_companies WHERE cliente_id=102")).scalar()
    assert after - before == 1
    assert session.execute(text("SELECT COUNT(*) FROM billing_subscriptions s JOIN billing_subscription_companies sc ON sc.subscription_id=s.subscription_id WHERE sc.cliente_id=102")).scalar() == 1
    session.close()


def test_apply_target_protection_is_fail_closed():
    with pytest.raises(SystemExit, match="REFUSE_PRODUCTION_WRITE"):
        validate_target("postgresql://postgres@localhost:5432/sjtnfe", apply=True)
    with pytest.raises(SystemExit, match="REFUSE_PRODUCTION_WRITE"):
        validate_target("postgresql://postgres@localhost:5432/billing_legacy_migration_test_demo", apply=True)


def test_apply_requires_explicit_confirmation_before_connecting(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("LEGACY_MIGRATION_LAB", "1")
    monkeypatch.setattr("sys.argv", ["legacy_grandfather_migrate.py", "--database-url", "postgresql://postgres@localhost:5432/billing_legacy_migration_test_demo", "--apply"])

    with pytest.raises(SystemExit, match="EXPLICIT_CONFIRMATION_REQUIRED"):
        migrate_main()


def test_real_database_is_allowed_only_for_dry_run():
    validate_target("postgresql://postgres@localhost:5432/sjtnfe", apply=False)
    with pytest.raises(SystemExit, match="REFUSE_PRODUCTION_WRITE"):
        validate_target("postgresql://postgres@localhost:5432/sjtnfe", apply=True)

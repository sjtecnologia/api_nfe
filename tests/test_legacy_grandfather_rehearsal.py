import os
import threading
import uuid
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from database.models import Base
from services.legacy_grandfather_migration import LegacyGrandfatherMigrationExecutor, LegacyMigrationSpec


@pytest.fixture()
def rehearsal_db():
    source_url = dotenv_values(Path(__file__).parents[1] / ".env.bak_localhost").get("DATABASE_URL")
    if not source_url or urlsplit(source_url).hostname not in {"localhost", "127.0.0.1"}:
        pytest.skip("Banco comercial local não disponível")
    source = create_engine(source_url, poolclass=NullPool)
    with source.connect() as conn:
        tx = conn.begin()
        conn.execute(text("SET TRANSACTION READ ONLY"))
        source_snapshot = {
            "clients": conn.execute(text("SELECT COUNT(*) FROM clientes")).scalar(),
            "subscriptions": conn.execute(text("SELECT COUNT(*) FROM assinaturas_cliente")).scalar(),
            "plans": conn.execute(text("SELECT COUNT(*) FROM planos_nfe")).scalar(),
        }
        client_rows = conn.execute(text("""
            SELECT cliente_id, ativo FROM clientes WHERE cliente_id IN (11,13) ORDER BY cliente_id
        """)).mappings().all()
        subscription_rows = conn.execute(text("""
            SELECT a.cliente_id, a.assinatura_id, a.data_inicio, a.status,
                   a.nfes_consumidas, p.nome AS plan_name, p.tipo_plano,
                   p.quantidade_nfes, p.valor_mensal
            FROM assinaturas_cliente a JOIN planos_nfe p ON p.plano_id=a.plano_id
            WHERE a.cliente_id IN (11,13) AND a.status='ATIVA'
            ORDER BY a.cliente_id
        """)).mappings().all()
        user_rows = conn.execute(text("""
            SELECT client_id, COUNT(DISTINCT user_id) AS users
            FROM user_clients WHERE client_id IN (11,13) GROUP BY client_id ORDER BY client_id
        """)).mappings().all()
        tx.rollback()
    source.dispose()
    assert [row["cliente_id"] for row in client_rows] == [11, 13]
    assert [(row["client_id"], row["users"]) for row in user_rows] == [(11, 2), (13, 3)]
    assert len(subscription_rows) == 2

    parsed = urlsplit(source_url)
    rehearsal_name = f"billing_legacy_rehearsal_{os.getpid()}_{uuid.uuid4().hex[:8]}"
    admin = create_engine(urlunsplit(parsed._replace(path="/postgres")), poolclass=NullPool)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"CREATE DATABASE {rehearsal_name}"))
    target = create_engine(urlunsplit(parsed._replace(path=f"/{rehearsal_name}")), poolclass=NullPool)
    Base.metadata.create_all(target)
    with target.begin() as conn:
        conn.execute(text("INSERT INTO regimes_tributarios (regime_tributario_id,nome,crt) VALUES (1,'Rehearsal',1)"))
        conn.execute(text("INSERT INTO planos_nfe (plano_id,nome,descricao,tipo_plano,quantidade_nfes,valor_mensal,valor_por_nfe,ativo) VALUES (2,:name,'sanitized source','PACOTE',:limit,:price,0,true)"), {"name": subscription_rows[0]["plan_name"], "limit": subscription_rows[0]["quantidade_nfes"], "price": subscription_rows[0]["valor_mensal"]})
        for source_id, fixture_id in ((11, 101), (13, 102)):
            conn.execute(text("""
                INSERT INTO clientes (cliente_id,cnpj,produtor_rural,razao_social,nome_fantasia,
                    regime_tributario_id,logradouro,numero,bairro,codigo_municipio,nome_municipio,
                    uf,cep,ambiente,ativo,data_cadastro,data_atualizacao)
                VALUES (:id,NULL,false,:name,:name,1,'Sanitized','1','Centro','0000000','Lab','SP','00000000',2,true,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            """), {"id": fixture_id, "name": f"REHEARSAL CLIENT {source_id}"})
            subscription = next(row for row in subscription_rows if row["cliente_id"] == source_id)
            conn.execute(text("""
                INSERT INTO assinaturas_cliente (assinatura_id,cliente_id,plano_id,data_inicio,status,nfes_consumidas,observacoes)
                VALUES (:subscription,:client,2,:start,'ATIVA',:usage,'SANITIZED_REHEARSAL')
            """), {"subscription": subscription["assinatura_id"], "client": fixture_id, "start": subscription["data_inicio"], "usage": subscription["nfes_consumidas"]})
            users = next(row["users"] for row in user_rows if row["client_id"] == source_id)
            for index in range(users):
                user_id = fixture_id * 10 + index
                conn.execute(text("""
                    INSERT INTO users (id,username,email,password_hash,_is_active,created_at)
                    VALUES (:id,:username,:email,'SANITIZED',true,CURRENT_TIMESTAMP)
                """), {"id": user_id, "username": f"rehearsal_{fixture_id}_{index}", "email": f"rehearsal_{fixture_id}_{index}@invalid.test"})
                conn.execute(text("INSERT INTO user_clients (user_id,client_id) VALUES (:user,:client)"), {"user": user_id, "client": fixture_id})
    yield target, source_snapshot
    target.dispose()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"), {"name": rehearsal_name})
        conn.execute(text(f"DROP DATABASE IF EXISTS {rehearsal_name}"))
    admin.dispose()


def migration_spec(client_id):
    return LegacyMigrationSpec(cliente_id=client_id, current_users=2 if client_id == 101 else 3, current_companies=1, contracted_price=Decimal("60.00"))


def counts(session):
    return tuple(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() for table in (
        "billing_accounts", "billing_subscriptions", "billing_subscription_companies", "billing_subscription_overrides"))


def test_sanitized_rehearsal_dry_run_has_zero_writes(rehearsal_db):
    target, source_snapshot = rehearsal_db
    session = sessionmaker(bind=target)()
    before = counts(session)
    session.rollback()
    with session.begin():
        first = LegacyGrandfatherMigrationExecutor(session).preview(migration_spec(101))
        second = LegacyGrandfatherMigrationExecutor(session).preview(migration_spec(102))
    after = counts(session)
    session.close()
    assert source_snapshot == {"clients": 5, "subscriptions": 2, "plans": 6}
    assert first.status == second.status == "WOULD_MIGRATE"
    assert before == after == (0, 0, 0, 0)


def test_sanitized_rehearsal_apply_preserves_real_shape_and_is_idempotent(rehearsal_db):
    target, _ = rehearsal_db
    Session = sessionmaker(bind=target)
    session = Session()
    with session.begin():
        first = LegacyGrandfatherMigrationExecutor(session).apply(migration_spec(101))
        second = LegacyGrandfatherMigrationExecutor(session).apply(migration_spec(102))
    session.close()
    session = Session()
    before = counts(session)
    session.rollback()
    with session.begin():
        again_a = LegacyGrandfatherMigrationExecutor(session).apply(migration_spec(101))
        again_b = LegacyGrandfatherMigrationExecutor(session).apply(migration_spec(102))
    rows = session.execute(text("""
        SELECT s.contracted_price, s.currency, v.version_code, sc.cliente_id,
               u.value, c.value, f.limit_type, f.metadata_json
        FROM billing_subscriptions s
        JOIN billing_plan_versions v ON v.plan_version_id=s.plan_version_id
        JOIN billing_subscription_companies sc ON sc.subscription_id=s.subscription_id
        JOIN billing_subscription_overrides u ON u.subscription_id=s.subscription_id AND u.key='MAX_USERS'
        JOIN billing_subscription_overrides c ON c.subscription_id=s.subscription_id AND c.key='MAX_COMPANIES'
        JOIN billing_plan_features f ON f.plan_version_id=v.plan_version_id
        JOIN billing_features bf ON bf.feature_id=f.feature_id AND bf.key='NFE_MONTHLY'
        ORDER BY sc.cliente_id
    """)).all()
    after = counts(session)
    session.close()
    assert [first.status, second.status] == ["MIGRATED", "MIGRATED"]
    assert [again_a.status, again_b.status] == ["ALREADY_MIGRATED", "ALREADY_MIGRATED"]
    assert before == after == (2, 2, 2, 4)
    assert [(row[3], row[0], row[1], row[2], row[4], row[5], row[6]) for row in rows] == [
        (101, Decimal("60.00"), "BRL", "LEGACY_60_V1", "2", "1", "CONTRACTUAL"),
        (102, Decimal("60.00"), "BRL", "LEGACY_60_V1", "3", "1", "CONTRACTUAL"),
    ]
    assert all("LEGACY_PRESERVED" in row[7] for row in rows)


def test_sanitized_rehearsal_rollback_and_concurrency(rehearsal_db):
    target, _ = rehearsal_db
    Session = sessionmaker(bind=target)
    session = Session()
    with pytest.raises(RuntimeError, match="INJECTED_FAILURE_AFTER_ACCOUNT"):
        with session.begin():
            LegacyGrandfatherMigrationExecutor(session).apply(migration_spec(101), fail_after_account=True)
    assert counts(session) == (0, 0, 0, 0)
    session.close()
    results, errors = [], []

    def worker():
        local = Session()
        try:
            with local.begin():
                results.append(LegacyGrandfatherMigrationExecutor(local).apply(migration_spec(102)).status)
        except BaseException as exc:
            errors.append(exc)
        finally:
            local.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(timeout=30)
    assert not errors
    assert sorted(results) == ["ALREADY_MIGRATED", "MIGRATED"]
    session = Session()
    assert session.execute(text("SELECT COUNT(*) FROM billing_subscription_companies WHERE cliente_id=102")).scalar() == 1
    session.close()

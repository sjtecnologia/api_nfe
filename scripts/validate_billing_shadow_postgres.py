#!/usr/bin/env python3
"""Valida migration/modelos/resolvers 4.6C em PostgreSQL isolado."""
import os
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
URL = os.environ.get("BILLING_SHADOW_DATABASE_URL")
if not URL or "127.0.0.1" not in URL and "localhost" not in URL:
    raise SystemExit("BILLING_SHADOW_DATABASE_URL deve apontar para PostgreSQL local")

from database.models import AssinaturaCliente, Base, PlanoNFe
from database.billing_shadow_models import (
    BillingAccount,
    BillingPlanVersion,
    BillingSubscription,
    BillingSubscriptionCompany,
    BillingSubscriptionOverride,
)
from services.billing_shadow import CapacityResolver, EntitlementResolver, LegacySubscriptionAdapter

engine = create_engine(URL)
Session = sessionmaker(bind=engine)


def prepare_legacy_schema():
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE clientes (cliente_id INTEGER PRIMARY KEY, razao_social TEXT NOT NULL)"))
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL)"))
        connection.execute(text("CREATE TABLE user_clients (user_id INTEGER NOT NULL REFERENCES users(id), client_id INTEGER NOT NULL REFERENCES clientes(cliente_id), PRIMARY KEY (user_id, client_id))"))
        connection.execute(text("INSERT INTO clientes VALUES (1, 'Legacy Company'), (2, 'Shadow A'), (3, 'Shadow B'), (4, 'Shadow C'), (5, 'Shadow D'), (6, 'Shadow E'), (7, 'Shadow F')"))
        connection.execute(text("INSERT INTO users VALUES (1, 'legacy-user')"))
        connection.execute(text("INSERT INTO user_clients VALUES (1, 1)"))
    PlanoNFe.__table__.create(engine)
    AssinaturaCliente.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO planos_nfe (plano_id,nome,descricao,tipo_plano,quantidade_nfes,valor_mensal,valor_por_nfe,ativo,ordem_exibicao) VALUES (1,'Pacote Básico','legacy','PACOTE',50,60,0,TRUE,1)"))
        connection.execute(text("INSERT INTO assinaturas_cliente (assinatura_id,cliente_id,plano_id,data_inicio,status,nfes_consumidas,updated_at) VALUES (1,1,1,CURRENT_DATE,'ATIVA',12,CURRENT_TIMESTAMP)"))
    print("LEGACY_SCHEMA_READY")


def validate():
    db = Session()
    try:
        versions = {row.version_code: row for row in db.execute(text("SELECT plan_version_id, version_code, price FROM billing_plan_versions"))}
        expected_prices = {"START_V1": "60.00", "ESSENCIAL_V1": "99.00", "PROFISSIONAL_V1": "169.00", "PREMIUM_V1": "299.00", "ENTERPRISE_V1": "None"}
        assert {key: str(row.price) for key, row in versions.items()} == expected_prices
        assert db.execute(text("SELECT COUNT(*) FROM billing_features")).scalar() == 15
        assert db.execute(text("SELECT COUNT(*) FROM billing_plan_features")).scalar() == 31

        account = BillingAccount(name="Shadow Account")
        db.add(account)
        db.flush()
        subscription = BillingSubscription(
            account_id=account.account_id,
            plan_version_id=versions["PROFISSIONAL_V1"].plan_version_id,
            contracted_price=Decimal("249.00"),
        )
        db.add(subscription)
        db.flush()
        db.add_all([
            BillingSubscriptionCompany(subscription_id=subscription.subscription_id, cliente_id=2),
            BillingSubscriptionCompany(subscription_id=subscription.subscription_id, cliente_id=3),
        ])
        db.commit()
        db.refresh(subscription)
        assert str(subscription.contracted_price) == "249.00"
        assert subscription.plan_version.version_code == "PROFISSIONAL_V1"

        capacity = CapacityResolver(db).companies(subscription.subscription_id)
        assert (capacity.used, capacity.limit, capacity.status) == (2, 2, "OK")
        db.add(BillingSubscriptionCompany(subscription_id=subscription.subscription_id, cliente_id=4))
        db.commit()
        capacity = CapacityResolver(db).companies(subscription.subscription_id)
        assert (capacity.used, capacity.limit, capacity.status) == (3, 2, "OVER_LIMIT")

        db.add(BillingSubscriptionOverride(
            subscription_id=subscription.subscription_id,
            key="MAX_COMPANIES",
            value="3",
            reason="Contrato shadow de teste",
        ))
        db.commit()
        capacity = CapacityResolver(db).companies(subscription.subscription_id)
        assert (capacity.used, capacity.limit, capacity.status) == (3, 3, "OK")

        premium_account = BillingAccount(name="Premium Shadow")
        db.add(premium_account)
        db.flush()
        premium = BillingSubscription(
            account_id=premium_account.account_id,
            plan_version_id=versions["PREMIUM_V1"].plan_version_id,
            contracted_price=Decimal("299.00"),
        )
        db.add(premium)
        db.flush()
        db.add_all([
            BillingSubscriptionCompany(subscription_id=premium.subscription_id, cliente_id=2),
            BillingSubscriptionCompany(subscription_id=premium.subscription_id, cliente_id=3),
            BillingSubscriptionCompany(subscription_id=premium.subscription_id, cliente_id=4),
            BillingSubscriptionCompany(subscription_id=premium.subscription_id, cliente_id=5),
            BillingSubscriptionCompany(subscription_id=premium.subscription_id, cliente_id=6),
        ])
        db.commit()
        premium_capacity = CapacityResolver(db).companies(premium.subscription_id)
        assert (premium_capacity.used, premium_capacity.limit, premium_capacity.status) == (5, 5, "OK")
        db.add(BillingSubscriptionCompany(subscription_id=premium.subscription_id, cliente_id=7))
        db.commit()
        premium_capacity = CapacityResolver(db).companies(premium.subscription_id)
        assert (premium_capacity.used, premium_capacity.limit, premium_capacity.status) == (6, 5, "OVER_LIMIT")

        resolver = EntitlementResolver(db)
        roadmap = resolver.resolve(subscription.subscription_id, "AI_INSIGHTS_CENTER")
        assert roadmap["enabled"] is False
        assert roadmap["limit_type"] == "DISABLED"
        assert roadmap["source"] in {"PLAN", "DEFAULT"}
        sales = resolver.resolve(subscription.subscription_id, "AI_SALES_ANALYSIS")
        assert sales["enabled"] is True and sales["limit_type"] == "ENABLED"

        legacy = LegacySubscriptionAdapter(db).get_for_company(1)
        assert legacy["source"] == "LEGACY"
        assert legacy["plan_code"] == "LEGACY_START_V1"
        assert legacy["nfe_consumed"] == 12
        assert db.execute(text("SELECT COUNT(*) FROM billing_accounts")).scalar() == 2
        assert db.execute(text("SELECT COUNT(*) FROM billing_subscriptions")).scalar() == 2
        assert db.execute(text("SELECT COUNT(*) FROM assinaturas_cliente")).scalar() == 1
        assert db.execute(text("SELECT COUNT(*) FROM billing_subscription_companies")).scalar() == 9
        assert db.execute(text("SELECT COUNT(*) FROM billing_subscription_companies WHERE cliente_id = 1")).scalar() == 0
        print("ACCOUNT_SUBSCRIPTION_PRICE_OK")
        print("CAPACITY_OVERRIDE_ENTITLEMENT_OK")
        print("LEGACY_ADAPTER_OK")
        print("NO_AUTO_MIGRATION_OK")
        print("MIGRATION_SCHEMA_SEEDS_OK")
    finally:
        db.close()


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare"]:
        prepare_legacy_schema()
    elif sys.argv[1:] == ["--validate"]:
        validate()
    else:
        raise SystemExit("uso: validate_billing_shadow_postgres.py --prepare|--validate")

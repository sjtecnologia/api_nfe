#!/usr/bin/env python3
"""Seed idempotente de fixtures sintéticas para homologação visual comercial."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if "e2e_" not in DATABASE_URL or "localhost" not in DATABASE_URL and "127.0.0.1" not in DATABASE_URL:
    raise SystemExit("COMMERCIAL_UX_E2E_REFUSED_UNSAFE_DATABASE")
engine = create_engine(DATABASE_URL)
period_start = date.today().replace(day=1)
period_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)

start_usages = tuple(int(value) for value in os.environ.get("COMMERCIAL_UX_START_USAGES", "0,39,40,49,50").split(","))
if start_usages != (0, 39, 40, 49, 50):
    raise SystemExit("COMMERCIAL_UX_START_USAGES_MUST_BE_0_39_40_49_50")

with engine.begin() as db:
    regime = db.execute(text("SELECT regime_tributario_id FROM regimes_tributarios ORDER BY regime_tributario_id LIMIT 1")).scalar()
    if regime is None:
        regime = db.execute(text("INSERT INTO regimes_tributarios(nome,crt) VALUES ('E2E',1) RETURNING regime_tributario_id")).scalar()
    role = db.execute(text("SELECT id FROM roles WHERE name='Admin' LIMIT 1")).scalar()
    if role is None:
        role = db.execute(text("INSERT INTO roles(name,description) VALUES ('Admin','Commercial UX E2E') RETURNING id")).scalar()
    user = db.execute(text("SELECT id FROM users WHERE username='commercial-ux-e2e@invalid.test'")).scalar()
    password_hash = generate_password_hash("commercial-ux-e2e-only")
    if user is None:
        user = db.execute(text("""
            INSERT INTO users(username,email,password_hash,is_active,created_at)
            VALUES ('commercial-ux-e2e@invalid.test','commercial-ux-e2e@invalid.test',:password,true,CURRENT_TIMESTAMP)
            RETURNING id
        """), {"password": password_hash}).scalar()
    else:
        db.execute(text("UPDATE users SET password_hash=:password,is_active=true WHERE id=:id"), {"password": password_hash, "id": user})
    db.execute(text("INSERT INTO user_roles(user_id,role_id) VALUES (:user,:role) ON CONFLICT DO NOTHING"), {"user": user, "role": role})

    start_version = db.execute(text("SELECT plan_version_id FROM billing_plan_versions WHERE version_code='START_V1'")).scalar()
    legacy_version = db.execute(text("SELECT plan_version_id FROM billing_plan_versions WHERE version_code='LEGACY_60_V1'")).scalar()
    if start_version is None:
        raise SystemExit("COMMERCIAL_UX_E2E_REQUIRED_START_VERSION_MISSING")
    if legacy_version is None:
        legacy_plan = db.execute(text("INSERT INTO billing_plans(code,name,active,display_order) VALUES ('LEGACY_60','Legacy Grandfathered R$60',false,99) RETURNING plan_id")).scalar()
        legacy_version = db.execute(text("INSERT INTO billing_plan_versions(plan_id,version_code,price,currency,valid_from,status,created_at) VALUES (:plan,'LEGACY_60_V1',60.00,'BRL',CURRENT_TIMESTAMP,'ACTIVE',CURRENT_TIMESTAMP) RETURNING plan_version_id"), {"plan": legacy_plan}).scalar()

    for client_id, usage in zip((201, 202, 203, 204, 205), start_usages):
        db.execute(text("""
            INSERT INTO clientes(cliente_id,cnpj,produtor_rural,razao_social,nome_fantasia,regime_tributario_id,
                logradouro,numero,bairro,codigo_municipio,nome_municipio,uf,cep,ambiente,ativo,data_cadastro,data_atualizacao)
            VALUES (:id,NULL,false,:name,:name,:regime,'E2E','1','Centro','0000000','E2E','SP','00000000',2,true,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            ON CONFLICT (cliente_id) DO UPDATE SET ativo=true,razao_social=EXCLUDED.razao_social,nome_fantasia=EXCLUDED.nome_fantasia
        """), {"id": client_id, "name": f"Commercial Start {usage:02d}", "regime": regime})
        db.execute(text("INSERT INTO user_clients(user_id,client_id) VALUES (:user,:client) ON CONFLICT DO NOTHING"), {"user": user, "client": client_id})
        account = db.execute(text("SELECT account_id FROM billing_accounts WHERE name=:name"), {"name": f"COMMERCIAL UX START {client_id}"}).scalar()
        if account is None:
            account = db.execute(text("INSERT INTO billing_accounts(name,status,created_at,updated_at) VALUES (:name,'ACTIVE',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) RETURNING account_id"), {"name": f"COMMERCIAL UX START {client_id}"}).scalar()
        subscription = db.execute(text("SELECT subscription_id FROM billing_subscriptions WHERE account_id=:account"), {"account": account}).scalar()
        if subscription is None:
            subscription = db.execute(text("""
                INSERT INTO billing_subscriptions(account_id,plan_version_id,status,contracted_price,currency,started_at,billing_cycle,created_at,updated_at)
                VALUES (:account,:version,'ACTIVE',60.00,'BRL',CURRENT_TIMESTAMP,'MONTHLY',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                RETURNING subscription_id
            """), {"account": account, "version": start_version}).scalar()
        db.execute(text("INSERT INTO billing_subscription_companies(subscription_id,cliente_id,status,linked_at) VALUES (:subscription,:client,'ACTIVE',CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"), {"subscription": subscription, "client": client_id})
        db.execute(text("""
            INSERT INTO billing_usage_counters(subscription_id,metric_key,period_start,period_end,quantity,version,updated_at)
            VALUES (:subscription,'NFE_ISSUED',:start,:end,:usage,1,CURRENT_TIMESTAMP)
            ON CONFLICT (subscription_id,metric_key,period_start,period_end)
            DO UPDATE SET quantity=EXCLUDED.quantity,version=billing_usage_counters.version+1,updated_at=CURRENT_TIMESTAMP
        """), {"subscription": subscription, "start": period_start, "end": period_end, "usage": usage})

    db.execute(text("""
        INSERT INTO clientes(cliente_id,cnpj,produtor_rural,razao_social,nome_fantasia,regime_tributario_id,
            logradouro,numero,bairro,codigo_municipio,nome_municipio,uf,cep,ambiente,ativo,data_cadastro,data_atualizacao)
        VALUES (215,NULL,false,'Commercial No Subscription','Commercial No Subscription',:regime,'E2E','1','Centro','0000000','E2E','SP','00000000',2,true,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
        ON CONFLICT (cliente_id) DO UPDATE SET ativo=true
    """), {"regime": regime})
    db.execute(text("INSERT INTO user_clients(user_id,client_id) VALUES (:user,215) ON CONFLICT DO NOTHING"), {"user": user})

    for client_id, users in ((211, 2), (213, 3)):
        db.execute(text("""
            INSERT INTO clientes(cliente_id,cnpj,produtor_rural,razao_social,nome_fantasia,regime_tributario_id,
                logradouro,numero,bairro,codigo_municipio,nome_municipio,uf,cep,ambiente,ativo,data_cadastro,data_atualizacao)
            VALUES (:id,NULL,false,:name,:name,:regime,'E2E','1','Centro','0000000','E2E','SP','00000000',2,true,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            ON CONFLICT (cliente_id) DO UPDATE SET ativo=true,razao_social=EXCLUDED.razao_social,nome_fantasia=EXCLUDED.nome_fantasia
        """), {"id": client_id, "name": f"Commercial Legacy {client_id}", "regime": regime})
        db.execute(text("INSERT INTO user_clients(user_id,client_id) VALUES (:user,:client) ON CONFLICT DO NOTHING"), {"user": user, "client": client_id})
        for index in range(users - 1):
            extra_user_id = client_id * 10 + index
            db.execute(text("""
                INSERT INTO users(id,username,email,password_hash,is_active,created_at)
                VALUES (:id,:username,:email,'E2E-SYNTHETIC',true,CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET is_active=true
            """), {"id": extra_user_id, "username": f"commercial_legacy_{client_id}_{index}", "email": f"commercial_legacy_{client_id}_{index}@invalid.test"})
            db.execute(text("INSERT INTO user_clients(user_id,client_id) VALUES (:user,:client) ON CONFLICT DO NOTHING"), {"user": extra_user_id, "client": client_id})
        account = db.execute(text("SELECT account_id FROM billing_accounts WHERE name=:name"), {"name": f"COMMERCIAL UX LEGACY {client_id}"}).scalar()
        if account is None:
            account = db.execute(text("INSERT INTO billing_accounts(name,status,created_at,updated_at) VALUES (:name,'ACTIVE',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) RETURNING account_id"), {"name": f"COMMERCIAL UX LEGACY {client_id}"}).scalar()
        subscription = db.execute(text("SELECT subscription_id FROM billing_subscriptions WHERE account_id=:account"), {"account": account}).scalar()
        if subscription is None:
            subscription = db.execute(text("INSERT INTO billing_subscriptions(account_id,plan_version_id,status,contracted_price,currency,started_at,billing_cycle,created_at,updated_at) VALUES (:account,:version,'ACTIVE',60.00,'BRL',CURRENT_TIMESTAMP,'MONTHLY',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) RETURNING subscription_id"), {"account": account, "version": legacy_version}).scalar()
        db.execute(text("INSERT INTO billing_subscription_companies(subscription_id,cliente_id,status,linked_at) VALUES (:subscription,:client,'ACTIVE',CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"), {"subscription": subscription, "client": client_id})
        for key, value in (("MAX_USERS", users), ("MAX_COMPANIES", 1)):
            db.execute(text("""
                INSERT INTO billing_subscription_overrides(subscription_id,key,value,reason,created_at)
                VALUES (:subscription,:key,:value,'Commercial UX E2E preserved capacity',CURRENT_TIMESTAMP)
                ON CONFLICT (subscription_id,key) DO UPDATE SET value=EXCLUDED.value
            """), {"subscription": subscription, "key": key, "value": str(value)})

print("COMMERCIAL_UX_SEED=PASS")
print("COMMERCIAL_UX_USER=commercial-ux-e2e@invalid.test")
print("COMMERCIAL_UX_CLIENTS=201,202,203,204,205,211,213")

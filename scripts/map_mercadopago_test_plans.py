#!/usr/bin/env python3
"""Cria/mapeia os quatro planos Mercado Pago TEST, somente com credencial TEST."""
from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from database.billing_shadow_models import BillingPlanVersion
from payments.mercadopago_sandbox import MercadoPagoSandboxClient
from services.payment_plan_mapping import PaymentPlanMappingService

PLANS = {
    "START_V1": ("EmiteMax Start V1", Decimal("60.00")),
    "ESSENCIAL_V1": ("EmiteMax Essencial V1", Decimal("99.00")),
    "PROFISSIONAL_V1": ("EmiteMax Profissional V1", Decimal("169.00")),
    "PREMIUM_V1": ("EmiteMax Premium V1", Decimal("299.00")),
}


def classify_candidates(expected_reason, expected_amount, plans, application_id):
    matches = []
    for plan in plans:
        recurring_match = (
            plan.get("reason") == expected_reason
            and Decimal(str(plan.get("transaction_amount"))) == expected_amount
            and plan.get("currency_id") == "BRL"
            and plan.get("frequency") == 1
            and plan.get("frequency_type") == "months"
            and plan.get("status") in {"active", "ACTIVE"}
            and (application_id is None or str(plan.get("application_id")) == str(application_id))
        )
        if recurring_match:
            matches.append(plan)
    if len(matches) == 1:
        return "EXACT_TEST_CANDIDATE", matches
    if len(matches) > 1:
        return "MULTIPLE_MATCHES", matches
    if any(Decimal(str(p.get("transaction_amount"))) == expected_amount for p in plans if p.get("transaction_amount") is not None):
        return "PRICE_ONLY_COLLISION", []
    if any(p.get("reason") == expected_reason for p in plans):
        return "NAME_ONLY_COLLISION", []
    return "NO_MATCH", []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--application-id", default=os.getenv("MERCADOPAGO_APPLICATION_ID", ""))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-test-plan-creation", action="store_true")
    args = parser.parse_args()
    parsed = urlsplit(args.database_url)
    if parsed.hostname not in {"localhost", "127.0.0.1"} or not parsed.path.strip("/") or parsed.path.strip("/") == "sjtnfe":
        raise SystemExit("REFUSE_NON_TEST_DATABASE")
    if os.getenv("MERCADOPAGO_ENVIRONMENT") != "TEST" or not os.getenv("MERCADOPAGO_TEST_ACCESS_TOKEN"):
        raise SystemExit("BLOCKED_MERCADOPAGO_TEST_CREDENTIAL")
    if args.apply:
        if not args.confirm_test_plan_creation:
            raise SystemExit("EXPLICIT_TEST_PLAN_CONFIRMATION_REQUIRED")
        if not os.getenv("MERCADOPAGO_TEST_BACK_URL"):
            raise SystemExit("BLOCKED_MERCADOPAGO_TEST_BACK_URL")

    provider = MercadoPagoSandboxClient()
    discovered = provider.search_preapproval_plans()
    application_ids = {str(plan["application_id"]) for plan in discovered if plan.get("application_id") is not None}
    requested_application_id = str(args.application_id).strip()
    if requested_application_id:
        if requested_application_id not in application_ids:
            raise SystemExit("BLOCKED_MERCADOPAGO_APPLICATION_NOT_FOUND")
        application_id = requested_application_id
    elif len(application_ids) == 1:
        application_id = next(iter(application_ids))
    else:
        raise SystemExit("BLOCKED_MERCADOPAGO_ENVIRONMENT_AMBIGUITY")
    discovery = []
    for version_code, (reason, amount) in PLANS.items():
        status, matches = classify_candidates(reason, amount, discovered, application_id)
        discovery.append({"plan_code": version_code, "status": status, "expected_reason": reason, "expected_amount": str(amount), "matches": len(matches)})
    if not args.apply:
        print({"mode": "DRY_RUN", "environment": "TEST", "application_id": application_id, "existing_plans_seen": len(discovered), "external_writes": 0, "local_mappings_created": 0, "discovery": discovery, "enterprise": "NOT_CREATED"})
        return

    blocked = [item for item in discovery if item["status"] not in {"NO_MATCH", "EXACT_TEST_CANDIDATE", "PRICE_ONLY_COLLISION", "MULTIPLE_MATCHES"}]
    if blocked:
        raise SystemExit(f"BLOCKED_DISCOVERY:{blocked[0]['plan_code']}:{blocked[0]['status']}")

    engine = create_engine(args.database_url)
    session = sessionmaker(bind=engine)()
    results = []
    try:
        for version_code, (reason, amount) in PLANS.items():
            if version_code == "START_V1":
                version = session.query(BillingPlanVersion).filter_by(version_code=version_code, status="ACTIVE").first()
                if version is None:
                    raise SystemExit(f"PLAN_VERSION_NOT_AVAILABLE:{version_code}")
                existing = session.execute(text("SELECT provider_plan_id, amount, currency, status FROM payment_provider_plan_mappings WHERE billing_plan_version_id=:version AND provider='MERCADOPAGO' AND environment='TEST' AND status='ACTIVE'"), {"version": version.plan_version_id}).first()
                if existing:
                    if Decimal(str(existing.amount)) != amount or existing.currency != "BRL":
                        raise SystemExit(f"PAYMENT_MAPPING_MISMATCH:{version_code}")
                    results.append({"plan_code": version_code, "status": "ALREADY_MAPPED", "provider_plan_id": existing.provider_plan_id})
                    continue
                # skip creating START_V1 here; it is already handled and should not be recreated
                continue

            version = session.query(BillingPlanVersion).filter_by(version_code=version_code, status="ACTIVE").first()
            if version is None:
                raise SystemExit(f"PLAN_VERSION_NOT_AVAILABLE:{version_code}")
            existing = session.execute(text("SELECT provider_plan_id, amount, currency, status FROM payment_provider_plan_mappings WHERE billing_plan_version_id=:version AND provider='MERCADOPAGO' AND environment='TEST' AND status='ACTIVE'"), {"version": version.plan_version_id}).first()
            if existing:
                if Decimal(str(existing.amount)) != amount or existing.currency != "BRL":
                    raise SystemExit(f"PAYMENT_MAPPING_MISMATCH:{version_code}")
                results.append({"plan_code": version_code, "status": "ALREADY_MAPPED", "provider_plan_id": existing.provider_plan_id})
                continue

            candidate = next((item for item in discovery if item["plan_code"] == version_code), None)
            if candidate is None:
                raise SystemExit(f"BLOCKED_DISCOVERY:{version_code}:MISSING")
            if candidate["status"] not in {"NO_MATCH"}:
                raise SystemExit(f"BLOCKED_DISCOVERY:{version_code}:{candidate['status']}")

            created = provider.create_preapproval_plan(reason=reason, amount=str(amount), back_url=os.getenv("MERCADOPAGO_TEST_BACK_URL"))
            validated = provider.get_preapproval_plan(str(created["id"]))
            if validated.get("reason") != reason or Decimal(str(validated.get("transaction_amount"))) != amount or validated.get("currency_id") != "BRL" or validated.get("frequency") != 1 or validated.get("frequency_type") != "months" or validated.get("status") not in {"active", "ACTIVE"} or str(validated.get("application_id")) != application_id:
                raise SystemExit(f"PAYMENT_MAPPING_MISMATCH:{version_code}")
            real_provider_plan_id = str(created["id"])
            mapping = PaymentPlanMappingService(session).register_test_mapping(plan_code=version_code, provider_plan_id=real_provider_plan_id, amount=amount)
            session.commit()
            results.append({"plan_code": version_code, "status": "CREATED", "provider_plan_id": mapping.provider_plan_id, "mercado_pago_id": real_provider_plan_id})
    finally:
        session.close()
        engine.dispose()
    print({"environment": "TEST", "enterprise": "NOT_CREATED", "results": results})


if __name__ == "__main__":
    main()

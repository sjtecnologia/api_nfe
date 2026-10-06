#!/usr/bin/env python3
"""Valida o plano criado via GET."""
from __future__ import annotations

import os
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from payments.mercadopago_sandbox import MercadoPagoSandboxClient

def main():
    if os.getenv("MERCADOPAGO_ENVIRONMENT") != "TEST" or not os.getenv("MERCADOPAGO_TEST_ACCESS_TOKEN"):
        raise SystemExit("BLOCKED_MERCADOPAGO_TEST_CREDENTIAL")
    
    provider = MercadoPagoSandboxClient()
    
    # Get all plans and find the START_V1 we created
    plans = provider.search_preapproval_plans()
    
    # Filter for our created plan
    start_v1_plans = [
        p for p in plans
        if p.get("reason") == "EmiteMax Start V1"
        and Decimal(str(p.get("transaction_amount"))) == Decimal("60.00")
        and p.get("currency_id") == "BRL"
        and p.get("frequency") == 1
        and p.get("frequency_type") == "months"
        and p.get("status") in {"active", "ACTIVE"}
    ]
    
    print(f"Found {len(start_v1_plans)} matching START_V1 plans")
    
    if len(start_v1_plans) == 0:
        print("ERROR: No START_V1 plan found!")
        sys.exit(1)
    elif len(start_v1_plans) == 1:
        plan = start_v1_plans[0]
        print(f"✓ Exactly one START_V1 plan found")
        print(f"  ID: {plan['id']}")
        print(f"  Reason: {plan['reason']}")
        print(f"  Amount: {plan['transaction_amount']}")
        print(f"  Currency: {plan['currency_id']}")
        print(f"  Frequency: {plan['frequency']} {plan['frequency_type']}")
        print(f"  Status: {plan['status']}")
        print(f"  Application ID: {plan['application_id']}")
        print(f"  Back URL: {plan['back_url']}")
        print(f"  Subscribed: {plan['subscribed']}")
        sys.exit(0)
    else:
        print(f"ERROR: Found {len(start_v1_plans)} START_V1 plans, expected exactly 1")
        for p in start_v1_plans:
            print(f"  - ID: {p['id']}, Created: {p.get('created_at', 'N/A')}")
        sys.exit(1)

if __name__ == "__main__":
    main()

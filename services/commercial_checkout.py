"""Fluxo público comercial shadow-only."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
import os

from sqlalchemy import select

from database.billing_shadow_models import BillingCheckoutAttempt, BillingPaymentEvent, BillingPlanVersion, PendingSignup
from payments.mercadopago_provider import ShadowPaymentProvider, build_payment_provider
from services.payment_plan_mapping import PaymentPlanMappingService


class CommercialCheckoutService:
    def __init__(self, db, provider=None):
        self.db = db
        if provider is not None:
            self.provider = provider
        else:
            payment_provider = os.getenv("PAYMENT_PROVIDER", "shadow").lower()
            environment = os.getenv("MERCADOPAGO_ENVIRONMENT")
            if payment_provider == "shadow":
                self.provider = ShadowPaymentProvider()
            elif environment == "TEST":
                self.provider = build_payment_provider()
            else:
                self.provider = ShadowPaymentProvider()

    def create_checkout(self, *, plan_code: str, email: str, company_name: str, contract_version: str, contract_accepted: bool, idempotency_key: str, card_token_id: str | None = None, payer_email: str | None = None):
        if not contract_accepted:
            raise ValueError("CONTRACT_ACCEPTANCE_REQUIRED")
        if not idempotency_key or len(idempotency_key) > 255:
            raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
        version = self.db.query(BillingPlanVersion).filter_by(version_code=plan_code, status="ACTIVE").first()
        if version is None:
            raise ValueError("PLAN_VERSION_NOT_AVAILABLE")
        if plan_code == "LEGACY_60_V1":
            raise ValueError("PLAN_CLOSED_TO_NEW_SUBSCRIPTIONS")
        if self.provider.name == "mercadopago" and not isinstance(card_token_id, str):
            raise ValueError("CARD_TOKEN_REQUIRED")
        if self.provider.name == "mercadopago" and not card_token_id.strip():
            raise ValueError("CARD_TOKEN_REQUIRED")
        existing = self.db.query(BillingCheckoutAttempt).filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return self._checkout_response(existing)
        provider_plan_id = None
        if self.provider.name == "mercadopago":
            mapping = PaymentPlanMappingService(self.db).resolve(plan_code=plan_code, environment="TEST")
            provider_plan_id = mapping.provider_plan_id
        normalized_email = re.sub(r"\s+", "", email or "").lower()
        if not normalized_email or "@" not in normalized_email or not company_name.strip():
            raise ValueError("SIGNUP_DATA_INVALID")
        signup = PendingSignup(
            public_token=hashlib.sha256(f"{idempotency_key}:{normalized_email}".encode()).hexdigest(),
            plan_version_id=version.plan_version_id,
            email_normalized=normalized_email,
            company_name=company_name.strip()[:255],
            status="CONTRACT_ACCEPTED",
            contract_version=contract_version.strip()[:50] or "CURRENT",
            contract_accepted_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2),
            metadata_json=json.dumps({"source": "public_commercial_api"}),
        )
        self.db.add(signup)
        self.db.flush()
        attempt = BillingCheckoutAttempt(
            pending_signup_id=signup.pending_signup_id,
            plan_version_id=version.plan_version_id,
            provider=self.provider.name,
            provider_reference=None,
            provider_plan_id=provider_plan_id,
            external_reference="PENDING",
            status="PENDING",
            amount=version.price,
            currency=version.currency,
            idempotency_key=idempotency_key,
            expires_at=signup.expires_at,
            provider_metadata=json.dumps({"source": "shadow"}),
        )
        self.db.add(attempt)
        self.db.flush()
        attempt.external_reference = f"EMITEMAX:{signup.pending_signup_id}:{plan_code}:{attempt.checkout_attempt_id}"
        provider_result = self.provider.create_checkout(
            amount=str(version.price), currency=version.currency,
            idempotency_key=idempotency_key, reference=attempt.external_reference,
            provider_plan_id=provider_plan_id,
            payer_email=payer_email or normalized_email,
            card_token_id=card_token_id,
        )
        attempt.provider_reference = provider_result.get("provider_reference") or provider_result.get("provider_subscription_id")
        attempt.provider_plan_id = provider_plan_id
        attempt.provider = self.provider.name
        attempt.provider_metadata = json.dumps({
            "source": self.provider.name,
            "checkout_url": provider_result.get("checkout_url", ""),
            "provider_subscription_id": provider_result.get("provider_subscription_id"),
            "external_reference": provider_result.get("external_reference", attempt.external_reference),
        })
        signup.status = "PAYMENT_PENDING"
        self.db.flush()
        return self._checkout_response(attempt)

    def status(self, public_token: str):
        signup = self.db.query(PendingSignup).filter_by(public_token=public_token).first()
        if signup is None:
            raise ValueError("CHECKOUT_NOT_FOUND")
        attempt = self.db.query(BillingCheckoutAttempt).filter_by(pending_signup_id=signup.pending_signup_id).order_by(BillingCheckoutAttempt.checkout_attempt_id.desc()).first()
        status = "ACTIVE" if signup.status == "COMPLETED" else "PROVISIONING" if signup.status == "PROVISIONING" else signup.status
        return {"checkout_token": signup.public_token, "status": status, "payment_status": attempt.status if attempt else "PENDING"}

    def process_webhook(self, *, raw_body: bytes, signature: str | None, payload: dict, request_id: str | None = None, data_id: str | None = None):
        if not self.provider.verify_webhook(
            raw_body=raw_body, signature=signature, request_id=request_id, data_id=data_id
        ):
            raise PermissionError("INVALID_WEBHOOK_SIGNATURE")
        event = self.provider.parse_webhook(payload, data_id=data_id)
        provider_event_id = event.get("provider_event_id")
        if not provider_event_id:
            raise ValueError("PROVIDER_EVENT_ID_REQUIRED")
        existing = self.db.query(BillingPaymentEvent).filter_by(provider=self.provider.name, provider_event_id=provider_event_id).first()
        if existing:
            return {"status": "ALREADY_PROCESSED", "event_id": existing.payment_event_id}
        attempt = self.db.query(BillingCheckoutAttempt).filter_by(checkout_attempt_id=event.get("checkout_attempt_id")).first()
        if attempt is None:
            raise ValueError("CHECKOUT_ATTEMPT_NOT_FOUND")
        if self.provider.name == "mercadopago":
            if event.get("environment") != "TEST" or event.get("plan_code") is None:
                raise ValueError("PAYMENT_MAPPING_MISMATCH")
            try:
                PaymentPlanMappingService(self.db).validate_webhook_mapping(
                    plan_code=event["plan_code"],
                    provider_plan_id=str(event.get("provider_plan_id", "")),
                    environment=event["environment"],
                    # Alguns eventos de preapproval não trazem auto_recurring.
                    # O valor persistido foi definido pelo plano no servidor e
                    # é o único fallback aceito para essa conferência.
                    amount=Decimal(str(event.get("amount") if event.get("amount") is not None else attempt.amount)),
                    currency=str(event.get("currency") or attempt.currency),
                )
            except (ValueError, TypeError, ArithmeticError) as exc:
                raise ValueError(str(exc) if str(exc) in {"PAYMENT_AMOUNT_MISMATCH", "PAYMENT_CURRENCY_MISMATCH", "PAYMENT_MAPPING_MISMATCH", "PROVIDER_PLAN_MAPPING_NOT_FOUND"} else "PAYMENT_MAPPING_MISMATCH") from exc
        status = event.get("status", "PENDING")
        if status == "AUTHORIZED":
            status = "APPROVED"
        if status not in {"APPROVED", "REJECTED", "CANCELLED", "PENDING"}:
            status = "PENDING"
        payment_event = BillingPaymentEvent(
            provider=self.provider.name, provider_event_id=provider_event_id,
            checkout_attempt_id=attempt.checkout_attempt_id, event_type=event.get("event_type", "payment"),
            status=status, processed_at=datetime.utcnow(),
            payload_hash=hashlib.sha256(raw_body).hexdigest(), metadata_json=json.dumps({"source": self.provider.name}),
        )
        self.db.add(payment_event)
        attempt.status = status
        signup = self.db.query(PendingSignup).filter_by(pending_signup_id=attempt.pending_signup_id).first()
        if status == "APPROVED": signup.status = "PROVISIONING"
        elif status in {"REJECTED", "CANCELLED"}: signup.status = status
        self.db.flush()
        return {"status": "PROCESSED", "event_id": provider_event_id, "payment_status": status}

    @staticmethod
    def _checkout_response(attempt):
        signup = attempt.pending_signup
        metadata = json.loads(attempt.provider_metadata or "{}")
        checkout_url = metadata.get("checkout_url")
        return {
            "checkout_token": signup.public_token,
            "status": "PAYMENT_PENDING" if attempt.status == "PENDING" else attempt.status,
            "redirect_url": checkout_url or f"/mock/payment/{signup.public_token}",
            "amount": str(attempt.amount), "currency": attempt.currency,
        }

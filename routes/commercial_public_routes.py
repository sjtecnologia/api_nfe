"""API pública comercial shadow-only para integração futura do site."""
from __future__ import annotations

import json
import os
import re

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from database.connection import get_db
from services.commercial_catalog import get_catalog
from services.commercial_checkout import CommercialCheckoutService

commercial_public_bp = Blueprint("commercial_public", __name__, url_prefix="/api/public/commercial")


def _limiter():
    from flask import current_app
    return current_app.extensions.get("limiter")


@commercial_public_bp.get("/plans")
def public_plans():
    catalog = get_catalog()
    catalog["plans"] = [plan for plan in catalog["plans"] if plan["availability"] in {"NEW_SALES", "CONTACT_SALES"}]
    catalog["plans"] = [{"code": plan["version_code"], **{key: value for key, value in plan.items() if key not in {"code", "version_code", "closed_to_new_subscriptions"}}} for plan in catalog["plans"]]
    return jsonify(catalog)


@commercial_public_bp.get("/checkout/test")
def mercadopago_test_checkout_page():
    """Página temporária, segura e restrita ao ambiente TEST para tokenizar cartão.

    O cartão é tratado diretamente pelo MercadoPago.js. Este servidor recebe só o
    CardToken efêmero no POST de checkout, nunca PAN, CVV ou validade.
    """
    checkout_enabled = os.getenv("FEATURE_NEW_BILLING_CHECKOUT_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    public_key = os.getenv("MERCADOPAGO_TEST_PUBLIC_KEY")
    if (
        not checkout_enabled
        or os.getenv("PAYMENT_PROVIDER", "shadow").lower() != "mercadopago"
        or os.getenv("MERCADOPAGO_ENVIRONMENT") != "TEST"
        or not public_key
    ):
        abort(503)

    eligible_plans = [
        plan for plan in get_catalog()["plans"]
        if plan["availability"] == "NEW_SALES" and plan.get("price") is not None
    ]
    requested_plan = str(request.args.get("plan_code", "")).strip()
    plan = next(
        (item for item in eligible_plans if item["version_code"] == requested_plan),
        eligible_plans[0] if eligible_plans else None,
    )
    if plan is None:
        abort(404)

    return render_template(
        "public/mercadopago_test_checkout.html",
        plan=plan,
        mercadopago_public_key=public_key,
        contract_version="2026-08",
    )


@commercial_public_bp.post("/checkout")
def public_checkout():
    checkout_enabled = os.getenv("FEATURE_NEW_BILLING_CHECKOUT_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    provider_mode = os.getenv("PAYMENT_PROVIDER", "shadow").lower()
    if not checkout_enabled:
        return jsonify({"success": False, "code": "COMMERCIAL_CHECKOUT_DISABLED"}), 503
    if provider_mode not in {"shadow", "mercadopago"}:
        return jsonify({"success": False, "code": "COMMERCIAL_CHECKOUT_DISABLED"}), 503
    limiter = _limiter()
    if limiter:
        limiter.limit("10/minute")(lambda: None)()
    payload = request.get_json(silent=True) or {}
    signup = payload.get("signup") or {}
    try:
        db = next(get_db())
        try:
            result = CommercialCheckoutService(db).create_checkout(
                plan_code=str(payload.get("plan_code", "")),
                email=str(payload.get("payer_email") or signup.get("email", "")),
                company_name=str(signup.get("company_name", "")),
                contract_version=str(payload.get("contract_version", "")),
                contract_accepted=payload.get("contract_accepted") is True,
                idempotency_key=str(request.headers.get("Idempotency-Key", payload.get("idempotency_key", ""))),
                payer_email=str(payload.get("payer_email") or signup.get("email", "")),
                card_token_id=payload.get("card_token_id"),
            )
            db.commit()
            return jsonify(result), 201
        except PermissionError as exc:
            db.rollback()
            return jsonify({"success": False, "code": str(exc)}), 401
        except ValueError as exc:
            db.rollback()
            return jsonify({"success": False, "code": str(exc)}), 400
        finally:
            db.close()
    except Exception as exc:
        # Nunca registrar payload, headers, card data ou credenciais.
        exc_text = str(exc)

        mp_http_status = "UNKNOWN"
        mp_request_ref = "NOT_PROVIDED"
        mp_error_code = "UNKNOWN"
        mp_failure_class = "UNKNOWN"

        status_match = re.search(
            r"MERCADOPAGO_TEST_HTTP_(\d{3})",
            exc_text,
        )
        if status_match:
            mp_http_status = status_match.group(1)

        request_match = re.search(
            r"REQUEST_ID=([^\s]+)",
            exc_text,
        )
        if request_match:
            mp_request_ref = request_match.group(1)[:200]

        error_marker = " ERROR="
        if error_marker in exc_text:
            raw_error = exc_text.split(error_marker, 1)[1]

            try:
                provider_body = json.loads(raw_error)

                if isinstance(provider_body, dict):
                    # Somente códigos seguros; nunca logar o body inteiro.
                    for key in ("code", "error", "status"):
                        value = provider_body.get(key)

                        if isinstance(value, (str, int)):
                            candidate = str(value)[:100]

                            if re.search(
                                r"(password|senha|token|secret|pin|api_key|authorization|credit_card|cvv)",
                                candidate,
                                re.IGNORECASE,
                            ):
                                mp_error_code = "SENSITIVE_PROVIDER_ERROR"
                            else:
                                mp_error_code = candidate
                            break

                    # Classificação segura baseada somente nos nomes
                    # dos campos rejeitados, nunca nos valores.
                    diagnostic_text = json.dumps(
                        provider_body,
                        ensure_ascii=True,
                    ).lower()

                    if "preapproval_plan_id" in diagnostic_text:
                        mp_failure_class = "PREAPPROVAL_PLAN_REJECTED"
                    elif "payer_email" in diagnostic_text:
                        mp_failure_class = "PAYER_EMAIL_REJECTED"
                    elif "card_token_id" in diagnostic_text:
                        mp_failure_class = "CARD_CREDENTIAL_REJECTED"
                    elif "back_url" in diagnostic_text:
                        mp_failure_class = "BACK_URL_REJECTED"
                    elif "external_reference" in diagnostic_text:
                        mp_failure_class = "EXTERNAL_REFERENCE_REJECTED"
                    elif "reason" in diagnostic_text:
                        mp_failure_class = "REASON_REJECTED"
                    elif "status" in diagnostic_text:
                        mp_failure_class = "STATUS_REJECTED"
                    else:
                        mp_failure_class = "PROVIDER_REQUEST_REJECTED"

            except (TypeError, ValueError):
                mp_failure_class = "PROVIDER_RESPONSE_UNPARSEABLE"

        current_app.logger.error(
            "commercial_checkout_failure "
            "exception_class=%s "
            "mp_http_status=%s "
            "mp_request_ref=%s "
            "mp_error_code=%s "
            "mp_failure_class=%s",
            type(exc).__name__,
            mp_http_status,
            mp_request_ref,
            mp_error_code,
            mp_failure_class,
        )

        return jsonify(
            {
                "success": False,
                "code": "COMMERCIAL_CHECKOUT_UNAVAILABLE",
            }
        ), 503



@commercial_public_bp.get("/checkout/<public_token>/status")
def checkout_status(public_token):
    db = next(get_db())
    try:
        try:
            return jsonify(CommercialCheckoutService(db).status(public_token))
        except ValueError as exc:
            return jsonify({"success": False, "code": str(exc)}), 404
    finally:
        db.close()


@commercial_public_bp.post("/webhooks/mercadopago")
def mercadopago_webhook():
    checkout_enabled = os.getenv("FEATURE_NEW_BILLING_CHECKOUT_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    if not checkout_enabled:
        return jsonify({"success": False, "code": "PAYMENT_WEBHOOK_DISABLED"}), 503
    if os.getenv("PAYMENT_PROVIDER", "shadow").lower() not in {"shadow", "mercadopago"}:
        return jsonify({"success": False, "code": "PAYMENT_WEBHOOK_DISABLED"}), 503
    raw_body = request.get_data(cache=True)
    is_mercadopago = os.getenv("PAYMENT_PROVIDER", "shadow").lower() == "mercadopago"
    signature = request.headers.get("X-Signature") if is_mercadopago else request.headers.get("X-Shadow-Signature")
    request_id = request.headers.get("X-Request-Id") if is_mercadopago else None
    data_id = request.args.get("data.id") if is_mercadopago else None
    payload = request.get_json(silent=True) or {}
    db = next(get_db())
    try:
        try:
            result = CommercialCheckoutService(db).process_webhook(
                raw_body=raw_body, signature=signature, payload=payload,
                request_id=request_id, data_id=data_id,
            )
            db.commit()
            return jsonify(result)
        except PermissionError as exc:
            db.rollback()
            return jsonify({"success": False, "code": str(exc)}), 401
        except ValueError as exc:
            db.rollback()
            return jsonify({"success": False, "code": str(exc)}), 400
    finally:
        db.close()

"""Provedores de checkout para o Mercado Pago.

Mantém o provider shadow para compatibilidade e expõe o provider real TEST
somente quando a configuração for explícita e segura.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from urllib.parse import urlsplit

import requests


def _database_is_safe_test_target(database_url: str | None) -> bool:
    if not database_url:
        return False
    parsed = urlsplit(database_url)
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"localhost", "127.0.0.1"}:
        return False
    database_name = parsed.path.strip("/")
    if not database_name or database_name == "sjtnfe":
        return False
    return "e2e_" in database_name or "emitemax" in database_name or "commercial" in database_name


def _required_https_url(value: str | None, *, setting_name: str) -> str:
    parsed = urlsplit(value or "")
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"{setting_name}_REQUIRED")
    return value


def build_payment_provider(provider=None):
    if provider is not None:
        return provider

    environment = os.getenv("MERCADOPAGO_ENVIRONMENT")
    if environment != "TEST":
        raise RuntimeError("BLOCKED_MERCADOPAGO_TEST_PROVIDER_CONFIGURATION")

    database_url = os.getenv("DATABASE_URL")
    if not _database_is_safe_test_target(database_url):
        raise RuntimeError("REFUSE_NON_TEST_DATABASE")

    access_token = os.getenv("MERCADOPAGO_TEST_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("MERCADOPAGO_TEST_ACCESS_TOKEN_REQUIRED")

    back_url = _required_https_url(
        os.getenv("MERCADOPAGO_TEST_BACK_URL"), setting_name="MERCADOPAGO_TEST_BACK_URL"
    )
    webhook_url = _required_https_url(
        os.getenv("MERCADOPAGO_TEST_WEBHOOK_URL"), setting_name="MERCADOPAGO_TEST_WEBHOOK_URL"
    )

    return MercadoPagoTestPaymentProvider(
        access_token=access_token, back_url=back_url, webhook_url=webhook_url
    )


class ShadowPaymentProvider:
    name = "shadow"

    def create_checkout(self, *, amount: str, currency: str, idempotency_key: str, reference: str, provider_plan_id: str | None = None, payer_email: str | None = None, card_token_id: str | None = None) -> dict:
        return {
            "provider": self.name,
            "provider_reference": f"shadow:{hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]}",
            "status": "PENDING",
            "redirect_url": f"/mock/payment/{reference}",
        }

    def get_payment_status(self, provider_reference: str) -> dict:
        return {"provider_reference": provider_reference, "status": "PENDING"}

    def verify_webhook(self, *, raw_body: bytes, signature: str | None, **_kwargs) -> bool:
        secret = os.getenv("SHADOW_WEBHOOK_SECRET", "shadow-only")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return bool(signature) and hmac.compare_digest(signature, expected)

    def parse_webhook(self, payload: dict, **_kwargs) -> dict:
        return {
            "provider_event_id": str(payload.get("id", "")),
            "event_type": str(payload.get("type", "payment")),
            "status": str(payload.get("status", "PENDING")).upper(),
            "checkout_attempt_id": payload.get("checkout_attempt_id"),
            "plan_code": payload.get("plan_code"),
            "provider_plan_id": payload.get("provider_plan_id"),
            "environment": payload.get("environment"),
            "amount": payload.get("amount"),
            "currency": payload.get("currency"),
        }


class MercadoPagoTestPaymentProvider:
    name = "mercadopago"

    def __init__(self, *, access_token: str | None = None, back_url: str | None = None, webhook_url: str | None = None):
        self.access_token = access_token or os.getenv("MERCADOPAGO_TEST_ACCESS_TOKEN")
        self.back_url = back_url or os.getenv("MERCADOPAGO_TEST_BACK_URL")
        self.webhook_url = webhook_url or os.getenv("MERCADOPAGO_TEST_WEBHOOK_URL")
        self.base_url = "https://api.mercadopago.com"
        self.client = MercadoPagoTestClient(access_token=self.access_token, back_url=self.back_url)

    def create_checkout(self, *, amount: str, currency: str, idempotency_key: str, reference: str, provider_plan_id: str | None = None, payer_email: str | None = None, card_token_id: str | None = None) -> dict:
        if not card_token_id:
            raise ValueError("CARD_TOKEN_REQUIRED")
        if not payer_email:
            raise ValueError("PAYER_EMAIL_REQUIRED")
        payload = {
            "external_reference": reference,
            "reason": reference,
            "preapproval_plan_id": provider_plan_id,
            "payer_email": payer_email,
            "card_token_id": card_token_id,
            "status": "authorized",
            "back_url": self.back_url,
            # Para Assinaturas no Brasil, a URL deve ser enviada na própria
            # criação da assinatura; a configuração global do app não cobre
            # esse produto.
            "notification_url": self.webhook_url,
            "metadata": {"external_reference": reference, "idempotency_key": idempotency_key},
        }

        minimal_preapproval = (
            os.getenv("MERCADOPAGO_TEST_MINIMAL_PREAPPROVAL", "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"}
        )

        if minimal_preapproval:
            payload = {
                "preapproval_plan_id": provider_plan_id,
                "payer_email": payer_email,
                "card_token_id": card_token_id,
                "auto_recurring": {
                    "frequency": 1,
                    "frequency_type": "months",
                    "transaction_amount": float(amount),
                    "currency_id": currency,
                },
                "status": "authorized",
                "notification_url": self.webhook_url,
                # O cliente usa esta chave somente no header HTTP; ela não é
                # persistida e não é retornada ao frontend.
                "metadata": {"idempotency_key": idempotency_key},
            }

            import logging

            logging.getLogger("app").info(
                "mp_preapproval_payload_mode=MINIMAL_AUTO_RECURRING "
                "fields=preapproval_plan_id,payer_email,card_token_id,"
                "auto_recurring,status,notification_url"
            )

        response = self.client.create_preapproval_payment(payload)
        return {
            "provider": self.name,
            "provider_reference": str(response.get("id") or response.get("provider_reference") or reference),
            "provider_subscription_id": str(response.get("id") or response.get("provider_subscription_id") or ""),
            "provider_plan_id": provider_plan_id,
            "external_reference": reference,
            "status": str(response.get("status") or "PENDING").upper(),
            "checkout_url": response.get("init_point") or response.get("sandbox_init_point") or "",
            "redirect_url": response.get("init_point") or response.get("sandbox_init_point") or "",
        }

    def get_payment_status(self, provider_reference: str) -> dict:
        response = self.client.get_preapproval_payment(provider_reference)
        return {
            "provider_reference": str(provider_reference),
            "status": str(response.get("status") or "PENDING").upper(),
            "provider_subscription_id": str(response.get("id") or provider_reference),
            "provider_plan_id": response.get("preapproval_plan_id"),
            "external_reference": response.get("external_reference"),
        }

    def verify_webhook(self, *, raw_body: bytes, signature: str | None, request_id: str | None = None, data_id: str | None = None, **_kwargs) -> bool:
        """Valida a assinatura ``x-signature`` conforme o protocolo do MP.

        A assinatura não é um HMAC do corpo: ela é calculada a partir de
        ``data.id``, ``x-request-id`` e ``ts``. Por isso o recurso só é
        consultado depois desta checagem.
        """
        if not signature:
            return False
        secret = os.getenv("MERCADOPAGO_WEBHOOK_SECRET") or os.getenv("MERCADOPAGO_TEST_WEBHOOK_SECRET")
        if not secret:
            return False
        signature_parts = {}
        for part in signature.split(","):
            key, separator, value = part.partition("=")
            if separator:
                signature_parts[key.strip()] = value.strip()
        timestamp = signature_parts.get("ts")
        received_hash = signature_parts.get("v1")
        if not timestamp or not received_hash:
            return False
        manifest_parts = []
        if data_id:
            manifest_parts.append(f"id:{str(data_id).lower()}")
        if request_id:
            manifest_parts.append(f"request-id:{request_id}")
        manifest_parts.append(f"ts:{timestamp}")
        expected = hmac.new(
            secret.encode(), (";".join(manifest_parts) + ";").encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, received_hash)

    def parse_webhook(self, payload: dict, *, data_id: str | None = None, **_kwargs) -> dict:
        resource = data_id or (payload.get("data", {}).get("id") if isinstance(payload.get("data"), dict) else payload.get("id"))
        if not resource:
            return {"provider_event_id": ""}

        subscription = self.client.get_preapproval_payment(str(resource))
        reference = str(subscription.get("external_reference") or "")
        match = re.fullmatch(r"EMITEMAX:(\d+):([A-Z0-9_]+):(\d+)", reference)
        if not match:
            raise ValueError("PAYMENT_MAPPING_MISMATCH")
        recurring = subscription.get("auto_recurring") or {}
        subscription_status = str(subscription.get("status") or "PENDING").upper()
        # A assinatura autorizada é a confirmação de que o vendedor recebeu a
        # autorização para cobrar. O status interno usa APPROVED para liberar
        # o provisionamento, sem depender do nome específico do provider.
        status = "APPROVED" if subscription_status == "AUTHORIZED" else subscription_status
        return {
            "provider_event_id": str(payload.get("id") or payload.get("event_id") or f"{resource}:{payload.get('action', '')}"),
            "event_type": str(payload.get("type") or "subscription"),
            "status": status,
            "checkout_attempt_id": int(match.group(3)),
            "plan_code": match.group(2),
            "provider_plan_id": subscription.get("preapproval_plan_id"),
            "environment": "TEST",
            "amount": recurring.get("transaction_amount"),
            "currency": recurring.get("currency_id"),
        }


class MercadoPagoTestClient:
    def __init__(self, *, access_token: str | None, back_url: str | None):
        if not access_token:
            raise RuntimeError("MERCADOPAGO_TEST_ACCESS_TOKEN_REQUIRED")
        self.access_token = access_token
        self.back_url = back_url
        self.base_url = "https://api.mercadopago.com"

    def create_preapproval_payment(self, payload: dict) -> dict:
        import logging
        import os
        import json as _json
        import re as _re

        diagnostic_enabled = (
            os.environ.get("MERCADOPAGO_TEST_CARD_DIAGNOSTIC", "")
            .strip()
            .lower()
            in {"1", "true", "yes"}
        )

        if diagnostic_enabled:
            card_ref = payload.get("card_token_id")

            if (
                isinstance(card_ref, str)
                and _re.fullmatch(r"[A-Za-z0-9_-]{1,200}", card_ref)
            ):
                probe = requests.get(
                    f"{self.base_url}/v1/card_tokens/{card_ref}",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=10,
                )

                probe_data = {}
                if probe.status_code == 200:
                    try:
                        value = probe.json()
                        if isinstance(value, dict):
                            probe_data = value
                    except Exception:
                        pass

                logging.getLogger("app").info(
                    "mp_card_probe http_status=%s visible=%s live_mode=%s state=%s",
                    probe.status_code,
                    "YES" if probe.status_code == 200 else "NO",
                    probe_data.get("live_mode"),
                    probe_data.get("status"),
                )
            else:
                logging.getLogger("app").info(
                    "mp_card_probe http_status=SKIPPED visible=UNKNOWN live_mode=UNKNOWN state=INVALID_REFERENCE"
                )

        response = requests.post(
            f"{self.base_url}/preapproval",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": payload.get("metadata", {}).get("idempotency_key", "mp-checkout"),
            },
            json=payload,
            timeout=20,
        )

        if response.status_code >= 400:
            category = "OTHER"
            error_code = "NONE"
            message_category = "UNKNOWN"
            cause_codes = []
            safe_message = "NONE"

            try:
                diagnostic_body = response.json()
                diagnostic_text = _json.dumps(
                    diagnostic_body,
                    ensure_ascii=True,
                ).lower()

                if isinstance(diagnostic_body, dict):
                    raw_error = diagnostic_body.get("error")
                    if raw_error is None:
                        raw_error = diagnostic_body.get("code")
                    if raw_error is None:
                        raw_error = diagnostic_body.get("status")

                    if raw_error is not None:
                        candidate_error = str(raw_error).strip()
                        if candidate_error:
                            error_code = candidate_error[:100]

                    raw_message = diagnostic_body.get("message")
                    message = (
                        str(raw_message).strip()
                        if raw_message is not None
                        else ""
                    )
                    message_lower = message.lower()

                    if "guest_site_mismatch" in diagnostic_text:
                        category = "GUEST_SITE_MISMATCH"
                    elif (
                        "card token service bad request" in diagnostic_text
                    ):
                        category = "CARD_TOKEN_BAD_REQUEST"
                    elif (
                        "card token" in diagnostic_text
                        and "not found" in diagnostic_text
                    ):
                        category = "PAYMENT_INSTRUMENT_NOT_FOUND"
                    elif (
                        "payer" in diagnostic_text
                        and "not found" in diagnostic_text
                    ):
                        category = "PAYER_NOT_FOUND"
                    elif (
                        (
                            "preapproval_plan" in diagnostic_text
                            or "plan" in diagnostic_text
                        )
                        and "not found" in diagnostic_text
                    ):
                        category = "PLAN_NOT_FOUND"
                    elif (
                        "payer" in message_lower
                        and "collector" in message_lower
                    ):
                        category = "PAYER_COLLECTOR_CONFLICT"
                    elif (
                        "same user" in message_lower
                        or "same account" in message_lower
                    ):
                        category = "PAYER_COLLECTOR_CONFLICT"
                    elif response.status_code == 404:
                        category = "HTTP_404_OTHER"
                    elif response.status_code == 400:
                        category = "HTTP_400_OTHER"

                    if "payer" in message_lower:
                        message_category = "PAYER"
                    elif (
                        "card token" in message_lower
                        or "card_token" in message_lower
                    ):
                        message_category = "CARD_TOKEN"
                    elif "card" in message_lower:
                        message_category = "CARD"
                    elif (
                        "preapproval_plan" in message_lower
                        or "plan" in message_lower
                    ):
                        message_category = "PLAN"
                    elif "collector" in message_lower:
                        message_category = "COLLECTOR"
                    elif "site" in message_lower:
                        message_category = "SITE"
                    elif "status" in message_lower:
                        message_category = "STATUS"
                    elif "invalid" in message_lower:
                        message_category = "VALIDATION"

                    raw_causes = diagnostic_body.get("cause")
                    if isinstance(raw_causes, list):
                        for cause in raw_causes[:10]:
                            if isinstance(cause, dict):
                                code = cause.get("code")
                                if code is not None:
                                    cause_codes.append(str(code)[:80])
                            elif isinstance(cause, (str, int)):
                                cause_codes.append(str(cause)[:80])

                    if message:
                        import re as _re

                        safe_message = message

                        safe_message = _re.sub(
                            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                            "[REDACTED_EMAIL]",
                            safe_message,
                        )

                        safe_message = _re.sub(
                            r"(?:APP_USR|TEST)-[A-Za-z0-9_-]+",
                            "[REDACTED_CREDENTIAL]",
                            safe_message,
                            flags=_re.IGNORECASE,
                        )

                        safe_message = _re.sub(
                            r"\b\d{6,19}\b",
                            "[REDACTED_NUMBER]",
                            safe_message,
                        )

                        safe_message = _re.sub(
                            r"[A-Za-z0-9_-]{32,}",
                            "[REDACTED_TOKEN]",
                            safe_message,
                        )

                        safe_message = _re.sub(
                            r"\s+",
                            " ",
                            safe_message,
                        ).strip()[:240]

            except Exception:
                if response.status_code == 404:
                    category = "HTTP_404_OTHER"
                elif response.status_code == 400:
                    category = "HTTP_400_OTHER"

            logging.getLogger("app").info(
                (
                    "mp_preapproval_diag "
                    "http_status=%s category=%s error=%s "
                    "message_category=%s cause_codes=%s "
                    "safe_message=%s"
                ),
                response.status_code,
                category,
                error_code,
                message_category,
                ",".join(cause_codes) if cause_codes else "NONE",
                safe_message,
            )

            raise RuntimeError(self._safe_http_error(response))
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("MERCADOPAGO_TEST_INVALID_RESPONSE")
        return data

    def get_preapproval_payment(self, provider_reference: str) -> dict:
        response = requests.get(
            f"{self.base_url}/preapproval/{provider_reference}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=20,
        )
        if response.status_code >= 400:
            raise RuntimeError(self._safe_http_error(response))
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("MERCADOPAGO_TEST_INVALID_RESPONSE")
        return data

    @staticmethod
    def _safe_http_error(response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict):
                body = {key: value for key, value in body.items() if key.lower() not in {"authorization", "access_token", "token", "public_key", "api_key", "cookie"}}
            detail = json.dumps(body, ensure_ascii=True, separators=(",", ":"))[:1000]
        except (TypeError, ValueError):
            detail = str(response.text)[:1000]
        request_id = next((response.headers.get(name) for name in ("x-request-id", "x-correlation-id", "x-requestid") if response.headers.get(name)), "NOT_PROVIDED")
        return f"MERCADOPAGO_TEST_HTTP_{response.status_code} REQUEST_ID={request_id} ERROR={detail}"


MockPaymentProvider = ShadowPaymentProvider

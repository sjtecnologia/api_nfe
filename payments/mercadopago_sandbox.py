"""Cliente opcional Mercado Pago TEST; nunca usa credencial de produção por padrão."""
from __future__ import annotations

import os
import json

import requests


class MercadoPagoSandboxClient:
    base_url = "https://api.mercadopago.com"

    def __init__(self, *, access_token: str | None = None):
        if os.getenv("MERCADOPAGO_ENVIRONMENT") != "TEST":
            raise RuntimeError("MERCADOPAGO_TEST_ENVIRONMENT_REQUIRED")
        self.access_token = access_token or os.getenv("MERCADOPAGO_TEST_ACCESS_TOKEN")
        if not self.access_token:
            raise RuntimeError("MERCADOPAGO_TEST_ACCESS_TOKEN_REQUIRED")

    def create_preapproval_plan(self, *, reason: str, amount: str, currency: str = "BRL", frequency: int = 1, frequency_type: str = "months", back_url: str | None = None) -> dict:
        payload = {"reason": reason, "auto_recurring": {"frequency": frequency, "frequency_type": frequency_type, "transaction_amount": float(amount), "currency_id": currency}}
        if back_url:
            payload["back_url"] = back_url
        response = requests.post(
            f"{self.base_url}/preapproval_plan",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        if not response.ok:
            print(f"MERCADOPAGO_TEST_HTTP_STATUS={response.status_code}")
            print(f"MERCADOPAGO_TEST_ERROR={self._safe_error_body(response)}")
            request_id = next((response.headers.get(name) for name in ("x-request-id", "x-correlation-id", "x-requestid") if response.headers.get(name)), "NOT_PROVIDED")
            print(f"MERCADOPAGO_TEST_REQUEST_ID={request_id}")
        response.raise_for_status()
        payload = response.json()
        if not payload.get("id"):
            raise RuntimeError("MERCADOPAGO_TEST_PLAN_ID_MISSING")
        return payload

    def search_preapproval_plans(self, *, limit: int = 20, max_pages: int = 100) -> list[dict]:
        """Lista todos os planos TEST sem criar ou alterar recursos."""
        plans = []
        offset = 0
        for _ in range(max_pages):
            response = requests.get(
                f"{self.base_url}/preapproval_plan/search",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"limit": limit, "offset": offset},
                timeout=20,
            )
            if not response.ok:
                print(f"MERCADOPAGO_TEST_HTTP_STATUS={response.status_code}")
                print(f"MERCADOPAGO_TEST_ERROR={self._safe_error_body(response)}")
                request_id = next((response.headers.get(name) for name in ("x-request-id", "x-correlation-id", "x-requestid") if response.headers.get(name)), "NOT_PROVIDED")
                print(f"MERCADOPAGO_TEST_REQUEST_ID={request_id}")
            response.raise_for_status()
            payload = response.json()
            page = payload.get("results", payload.get("data", []))
            plans.extend(self._safe_plan(plan) for plan in page if isinstance(plan, dict))
            total = payload.get("paging", {}).get("total")
            if not page or (total is not None and len(plans) >= int(total)) or len(page) < limit:
                break
            offset += len(page)
        return plans

    def get_preapproval_plan(self, provider_plan_id: str) -> dict:
        response = requests.get(
            f"{self.base_url}/preapproval_plan/{provider_plan_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=20,
        )
        if not response.ok:
            print(f"MERCADOPAGO_TEST_HTTP_STATUS={response.status_code}")
            print(f"MERCADOPAGO_TEST_ERROR={self._safe_error_body(response)}")
            request_id = next((response.headers.get(name) for name in ("x-request-id", "x-correlation-id", "x-requestid") if response.headers.get(name)), "NOT_PROVIDED")
            print(f"MERCADOPAGO_TEST_REQUEST_ID={request_id}")
        response.raise_for_status()
        return self._safe_plan(response.json())

    @staticmethod
    def _safe_plan(plan: dict) -> dict:
        recurring = plan.get("auto_recurring") or {}
        return {
            "id": plan.get("id"),
            "reason": plan.get("reason"),
            "status": plan.get("status"),
            "application_id": plan.get("application_id"),
            "collector_id": plan.get("collector_id"),
            "back_url": plan.get("back_url"),
            "frequency": recurring.get("frequency"),
            "frequency_type": recurring.get("frequency_type"),
            "transaction_amount": recurring.get("transaction_amount"),
            "currency_id": recurring.get("currency_id"),
            "subscribed": plan.get("subscribed"),
        }

    @staticmethod
    def _safe_error_body(response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict):
                body = {key: value for key, value in body.items() if key.lower() not in {"authorization", "access_token", "token", "public_key", "api_key", "cookie"}}
            return json.dumps(body, ensure_ascii=True, separators=(",", ":"))[:1000]
        except (TypeError, ValueError):
            return str(response.text)[:1000]

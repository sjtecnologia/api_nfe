"""Contrato de provider de pagamentos sem dependência do Mercado Pago real."""
from __future__ import annotations

from typing import Protocol


class PaymentProvider(Protocol):
    name: str

    def create_checkout(self, *, amount: str, currency: str, idempotency_key: str, reference: str) -> dict: ...

    def get_payment_status(self, provider_reference: str) -> dict: ...

    def verify_webhook(self, *, raw_body: bytes, signature: str | None, **kwargs) -> bool: ...

    def parse_webhook(self, payload: dict, **kwargs) -> dict: ...

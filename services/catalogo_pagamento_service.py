"""Checkout Marketplace por conta Mercado Pago vinculada ao cliente.

Tokens nunca são enviados ao navegador e ficam criptografados no banco.
"""
from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet
from sqlalchemy import text


class PagamentoConfiguracaoInvalida(RuntimeError):
    pass


def _fernet() -> Fernet:
    master_key = os.getenv("PAYMENT_MASTER_KEY")
    if not master_key:
        raise PagamentoConfiguracaoInvalida("PAYMENT_MASTER_KEY não configurada")
    key = base64.urlsafe_b64encode(hashlib.sha256(master_key.encode("utf-8")).digest())
    return Fernet(key)


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def is_configured() -> bool:
    return all(os.getenv(key) for key in (
        "MERCADOPAGO_OAUTH_CLIENT_ID",
        "MERCADOPAGO_OAUTH_CLIENT_SECRET",
        "MERCADOPAGO_OAUTH_REDIRECT_URI",
        "PAYMENT_MASTER_KEY",
    ))


def authorization_url(state: str, code_challenge: str) -> str:
    if not is_configured():
        raise PagamentoConfiguracaoInvalida("Integração Mercado Pago ainda não configurada")
    query = urlencode({
        "client_id": os.environ["MERCADOPAGO_OAUTH_CLIENT_ID"],
        "response_type": "code",
        "platform_id": "mp",
        "redirect_uri": os.environ["MERCADOPAGO_OAUTH_REDIRECT_URI"],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return f"https://auth.mercadopago.com/authorization?{query}"


def connect_account(db, cliente_id: int, code: str, code_verifier: str) -> None:
    if not is_configured():
        raise PagamentoConfiguracaoInvalida("Integração Mercado Pago ainda não configurada")
    response = requests.post(
        "https://api.mercadopago.com/oauth/token",
        json={
            "client_id": os.environ["MERCADOPAGO_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["MERCADOPAGO_OAUTH_CLIENT_SECRET"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": os.environ["MERCADOPAGO_OAUTH_REDIRECT_URI"],
            "code_verifier": code_verifier,
        },
        timeout=15,
    )
    if not response.ok:
        raise PagamentoConfiguracaoInvalida("Não foi possível vincular a conta Mercado Pago")
    payload = response.json()
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise PagamentoConfiguracaoInvalida("Resposta inválida do Mercado Pago")
    expires_in = int(payload.get("expires_in") or 0)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    db.execute(
        text("""
            INSERT INTO contas_pagamento_cliente
                (cliente_id, provider, seller_id, access_token_criptografado,
                 refresh_token_criptografado, token_expira_em, status, updated_at)
            VALUES (:cliente_id, 'mercadopago', :seller_id, :access_token,
                    :refresh_token, :expires_at, 'ATIVA', CURRENT_TIMESTAMP)
            ON CONFLICT (cliente_id) DO UPDATE SET
                provider = 'mercadopago', seller_id = EXCLUDED.seller_id,
                access_token_criptografado = EXCLUDED.access_token_criptografado,
                refresh_token_criptografado = EXCLUDED.refresh_token_criptografado,
                token_expira_em = EXCLUDED.token_expira_em, status = 'ATIVA',
                updated_at = CURRENT_TIMESTAMP
        """), {
            "cliente_id": cliente_id,
            "seller_id": str(payload.get("user_id") or ""),
            "access_token": _encrypt(access_token),
            "refresh_token": _encrypt(str(payload["refresh_token"])) if payload.get("refresh_token") else None,
            "expires_at": expires_at,
        },
    )


def _access_token(db, cliente_id: int) -> str:
    from sqlalchemy import text
    row = db.execute(text("""
        SELECT access_token_criptografado, refresh_token_criptografado, token_expira_em
        FROM contas_pagamento_cliente
        WHERE cliente_id = :cliente_id AND provider = 'mercadopago' AND status = 'ATIVA'
    """), {"cliente_id": cliente_id}).mappings().first()
    if not row:
        raise PagamentoConfiguracaoInvalida("Conta Mercado Pago não vinculada")
    if row["token_expira_em"] and row["token_expira_em"] <= datetime.utcnow() + timedelta(minutes=5):
        refresh = row["refresh_token_criptografado"]
        if not refresh or not is_configured():
            raise PagamentoConfiguracaoInvalida("Reconecte a conta Mercado Pago")
        response = requests.post("https://api.mercadopago.com/oauth/token", json={
            "client_id": os.environ["MERCADOPAGO_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["MERCADOPAGO_OAUTH_CLIENT_SECRET"],
            "refresh_token": _decrypt(refresh), "grant_type": "refresh_token",
        }, timeout=15)
        if not response.ok or not response.json().get("access_token"):
            raise PagamentoConfiguracaoInvalida("Reconecte a conta Mercado Pago")
        payload = response.json()
        token = str(payload["access_token"])
        expires_at = datetime.utcnow() + timedelta(seconds=int(payload.get("expires_in") or 0))
        db.execute(text("""
            UPDATE contas_pagamento_cliente SET access_token_criptografado=:token,
                refresh_token_criptografado=:refresh, token_expira_em=:expires_at,
                updated_at=CURRENT_TIMESTAMP WHERE cliente_id=:cliente_id
        """), {"token": _encrypt(token), "refresh": _encrypt(str(payload.get("refresh_token") or _decrypt(refresh))),
                "expires_at": expires_at, "cliente_id": cliente_id})
        return token
    return _decrypt(row["access_token_criptografado"])


def create_checkout(db, *, pedido: dict, itens: list[dict], return_url: str, notification_url: str | None = None) -> str:
    token = _access_token(db, int(pedido["cliente_id"]))
    payload = {
        "items": [{
            "id": str(item.get("produto_id") or ""), "title": item["descricao"],
            "quantity": float(item["quantidade"]), "unit_price": float(item["valor_unitario"]),
            "currency_id": "BRL",
        } for item in itens],
        "external_reference": pedido["token_publico"],
        "back_urls": {"success": return_url, "failure": return_url, "pending": return_url},
        "auto_return": "approved",
    }
    if notification_url:
        payload["notification_url"] = notification_url
    response = requests.post("https://api.mercadopago.com/checkout/preferences", json=payload,
                             headers={"Authorization": f"Bearer {token}"}, timeout=15)
    if not response.ok:
        raise PagamentoConfiguracaoInvalida("Não foi possível iniciar o pagamento")
    checkout_url = response.json().get("init_point") or response.json().get("sandbox_init_point")
    if not checkout_url:
        raise PagamentoConfiguracaoInvalida("Resposta inválida do Mercado Pago")
    return str(checkout_url)


def verify_payment(db, *, pedido: dict, payment_id: str) -> str:
    token = _access_token(db, int(pedido["cliente_id"]))
    response = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}",
                            headers={"Authorization": f"Bearer {token}"}, timeout=15)
    if not response.ok:
        raise PagamentoConfiguracaoInvalida("Não foi possível confirmar o pagamento")
    payload = response.json()
    if str(payload.get("external_reference") or "") != pedido["token_publico"]:
        raise PagamentoConfiguracaoInvalida("Pagamento não pertence a este pedido")
    return str(payload.get("status") or "pending").upper()

"""Catálogos públicos, pedidos e checkout por empresa."""
from __future__ import annotations

import base64
import hashlib
import secrets
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import quote

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import text

from auth.decorators import admin_required
from database.connection import get_db
from services import catalogo_pagamento_service as pagamentos


catalogo_vendas_bp = Blueprint("catalogo_vendas", __name__, url_prefix="/admin/catalogos-vendas")
catalogo_publico_bp = Blueprint("catalogo_publico", __name__)


def _db():
    return next(get_db())


def _cliente_ativo():
    cliente_id = session.get("current_client_id") or session.get("active_cliente_id")
    if not cliente_id:
        abort(400, "Selecione um cliente antes de usar os catálogos de vendas.")
    return int(cliente_id)


def _whatsapp_url(numero: str | None, pedido: dict, itens: list[dict]) -> str | None:
    digits = "".join(char for char in (numero or "") if char.isdigit())
    if len(digits) not in (10, 11, 12, 13):
        return None
    if len(digits) in (10, 11):
        digits = "55" + digits
    linhas = "\n".join(
        f"• {item['quantidade']} {item.get('unidade') or 'un'} — {item['descricao']}"
        for item in itens
    )
    mensagem = (
        f"Olá! Fiz o pedido {pedido['numero']} no catálogo.\n\n{linhas}\n\n"
        f"Total: R$ {Decimal(pedido['valor_total']):.2f}\n"
        f"Meu nome: {pedido['comprador_nome']}\nTelefone: {pedido['comprador_telefone']}"
    )
    return f"https://wa.me/{digits}?text={quote(mensagem)}"


def _catalogo_por_token(db, token: str):
    return db.execute(text("""
        SELECT cv.catalogo_id, cv.cliente_id, cv.token_publico, cv.titulo, cv.descricao,
               cv.whatsapp_numero, cv.pagamento_online_ativo, cv.ativo,
               COALESCE(c.nome_fantasia, c.razao_social) AS loja_nome,
               c.telefone_contato AS telefone_loja
        FROM catalogos_vendas cv
        JOIN clientes c ON c.cliente_id = cv.cliente_id
        WHERE cv.token_publico = :token
    """), {"token": token}).mappings().first()


@catalogo_vendas_bp.get("")
@login_required
@admin_required()
def listar_catalogos():
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        catalogos = db.execute(text("""
            SELECT cv.catalogo_id, cv.token_publico, cv.titulo, cv.ativo, cv.pagamento_online_ativo,
                   cv.created_at, COUNT(cvi.catalogo_item_id) AS total_itens
            FROM catalogos_vendas cv
            LEFT JOIN catalogos_vendas_itens cvi ON cvi.catalogo_id = cv.catalogo_id
            WHERE cv.cliente_id = :cliente_id
            GROUP BY cv.catalogo_id
            ORDER BY cv.created_at DESC
        """), {"cliente_id": cliente_id}).mappings().all()
        pedidos = db.execute(text("""
            SELECT pedido_id, numero, comprador_nome, status, status_pagamento, valor_total, created_at
            FROM pedidos_vendas WHERE cliente_id = :cliente_id ORDER BY created_at DESC LIMIT 20
        """), {"cliente_id": cliente_id}).mappings().all()
        conta_conectada = bool(db.execute(text("""
            SELECT 1 FROM contas_pagamento_cliente
            WHERE cliente_id = :cliente_id AND status = 'ATIVA'
        """), {"cliente_id": cliente_id}).first())
        return render_template("admin/catalogos_vendas/list.html", catalogos=catalogos, pedidos=pedidos,
                               conta_conectada=conta_conectada, pagamento_configurado=pagamentos.is_configured())
    finally:
        db.close()


@catalogo_vendas_bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required()
def novo_catalogo():
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        produtos = db.execute(text("""
            SELECT produto_id, codigo_interno, descricao, unidade_comercial, preco_unitario_padrao
            FROM produtos WHERE cliente_id=:cliente_id AND ativo=true ORDER BY descricao
        """), {"cliente_id": cliente_id}).mappings().all()
        conta_conectada = bool(db.execute(text("""
            SELECT 1 FROM contas_pagamento_cliente WHERE cliente_id=:cliente_id AND status='ATIVA'
        """), {"cliente_id": cliente_id}).first())
        if request.method == "GET":
            return render_template("admin/catalogos_vendas/form.html", produtos=produtos,
                                   conta_conectada=conta_conectada, form_data={})

        titulo = (request.form.get("titulo") or "").strip()
        selecionados = {int(value) for value in request.form.getlist("produto_id") if value.isdigit()}
        if not titulo or not selecionados:
            flash("Informe o título e selecione pelo menos um produto.", "danger")
            return render_template("admin/catalogos_vendas/form.html", produtos=produtos,
                                   conta_conectada=conta_conectada, form_data=request.form), 400
        produtos_por_id = {int(p["produto_id"]): p for p in produtos}
        if not selecionados.issubset(produtos_por_id):
            abort(400, "Produto inválido para este cliente.")
        token = secrets.token_urlsafe(18)
        catalogo_id = db.execute(text("""
            INSERT INTO catalogos_vendas
                (cliente_id, token_publico, titulo, descricao, whatsapp_numero,
                 pagamento_online_ativo, created_by_user_id)
            VALUES (:cliente_id, :token, :titulo, :descricao, :whatsapp,
                    :pagamento_online, :user_id)
            RETURNING catalogo_id
        """), {
            "cliente_id": cliente_id, "token": token, "titulo": titulo,
            "descricao": (request.form.get("descricao") or "").strip() or None,
            "whatsapp": (request.form.get("whatsapp_numero") or "").strip() or None,
            "pagamento_online": conta_conectada and request.form.get("pagamento_online_ativo") == "on",
            "user_id": current_user.id,
        }).scalar_one()
        for ordem, produto_id in enumerate(sorted(selecionados), start=1):
            raw_price = (request.form.get(f"preco_{produto_id}") or "").replace(",", ".")
            try:
                preco = Decimal(raw_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except InvalidOperation:
                preco = Decimal(produtos_por_id[produto_id]["preco_unitario_padrao"])
            if preco < 0:
                abort(400, "Preço inválido.")
            db.execute(text("""
                INSERT INTO catalogos_vendas_itens (catalogo_id, produto_id, preco_unitario, ordem)
                VALUES (:catalogo_id, :produto_id, :preco, :ordem)
            """), {"catalogo_id": catalogo_id, "produto_id": produto_id, "preco": preco, "ordem": ordem})
        db.commit()
        flash("Catálogo criado. Copie o link público e envie ao comprador.", "success")
        return redirect(url_for("catalogo_vendas.listar_catalogos"))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@catalogo_vendas_bp.post("/<int:catalogo_id>/alternar")
@login_required
@admin_required()
def alternar_catalogo(catalogo_id: int):
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        updated = db.execute(text("""
            UPDATE catalogos_vendas SET ativo = NOT ativo, updated_at=CURRENT_TIMESTAMP
            WHERE catalogo_id=:catalogo_id AND cliente_id=:cliente_id
        """), {"catalogo_id": catalogo_id, "cliente_id": cliente_id}).rowcount
        if not updated:
            abort(404)
        db.commit()
        return redirect(url_for("catalogo_vendas.listar_catalogos"))
    finally:
        db.close()


@catalogo_vendas_bp.get("/pagamentos/mercadopago/conectar")
@login_required
@admin_required()
def conectar_mercadopago():
    cliente_id = _cliente_ativo()
    state = secrets.token_urlsafe(24)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    session["mp_catalogo_oauth"] = {
        "state": state, "cliente_id": cliente_id, "user_id": current_user.id,
        "code_verifier": code_verifier,
    }
    try:
        return redirect(pagamentos.authorization_url(state, code_challenge))
    except pagamentos.PagamentoConfiguracaoInvalida as exc:
        flash(str(exc), "warning")
        return redirect(url_for("catalogo_vendas.listar_catalogos"))


@catalogo_vendas_bp.get("/pagamentos/mercadopago/retorno")
@login_required
@admin_required()
def retorno_mercadopago():
    expected = session.pop("mp_catalogo_oauth", None) or {}
    if expected.get("user_id") != current_user.id or not secrets.compare_digest(
        str(expected.get("state") or ""), str(request.args.get("state") or "")
    ):
        abort(400, "Retorno de autorização inválido.")
    code = request.args.get("code")
    if not code:
        flash("A autorização da conta Mercado Pago foi cancelada.", "warning")
        return redirect(url_for("catalogo_vendas.listar_catalogos"))
    db = _db()
    try:
        pagamentos.connect_account(db, int(expected["cliente_id"]), code, expected["code_verifier"])
        db.commit()
        flash("Conta Mercado Pago vinculada com sucesso.", "success")
    except pagamentos.PagamentoConfiguracaoInvalida as exc:
        db.rollback()
        flash(str(exc), "danger")
    finally:
        db.close()
    return redirect(url_for("catalogo_vendas.listar_catalogos"))


@catalogo_vendas_bp.post("/pagamentos/desconectar")
@login_required
@admin_required()
def desconectar_pagamento():
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        db.execute(text("DELETE FROM contas_pagamento_cliente WHERE cliente_id=:cliente_id"), {"cliente_id": cliente_id})
        db.execute(text("UPDATE catalogos_vendas SET pagamento_online_ativo=false WHERE cliente_id=:cliente_id"),
                   {"cliente_id": cliente_id})
        db.commit()
        flash("Conta de pagamento desconectada.", "success")
    finally:
        db.close()
    return redirect(url_for("catalogo_vendas.listar_catalogos"))


@catalogo_publico_bp.get("/catalogo/<token>")
def ver_catalogo(token: str):
    db = _db()
    try:
        catalogo = _catalogo_por_token(db, token)
        if not catalogo or not catalogo["ativo"]:
            abort(404)
        itens = db.execute(text("""
            SELECT p.produto_id, p.codigo_interno, p.descricao, p.unidade_comercial, cvi.preco_unitario
            FROM catalogos_vendas_itens cvi JOIN produtos p ON p.produto_id=cvi.produto_id
            WHERE cvi.catalogo_id=:catalogo_id AND p.ativo=true ORDER BY cvi.ordem, p.descricao
        """), {"catalogo_id": catalogo["catalogo_id"]}).mappings().all()
        return render_template("public/catalogo_vendas.html", catalogo=catalogo, itens=itens)
    finally:
        db.close()


@catalogo_publico_bp.post("/catalogo/<token>/pedido")
def criar_pedido(token: str):
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    comprador_nome = str(payload.get("comprador_nome") or "").strip()
    comprador_telefone = "".join(char for char in str(payload.get("comprador_telefone") or "") if char.isdigit())
    raw_items = payload.get("itens") or []
    if not comprador_nome or len(comprador_telefone) < 10 or not isinstance(raw_items, list):
        return jsonify({"success": False, "error": "Informe nome, WhatsApp e pelo menos um produto."}), 400
    quantities: dict[int, Decimal] = {}
    for item in raw_items:
        try:
            produto_id = int(item.get("produto_id"))
            quantidade = Decimal(str(item.get("quantidade"))).quantize(Decimal("0.001"))
            if quantidade <= 0 or quantidade > Decimal("9999"):
                raise InvalidOperation
            quantities[produto_id] = quantities.get(produto_id, Decimal("0")) + quantidade
        except (AttributeError, TypeError, ValueError, InvalidOperation):
            return jsonify({"success": False, "error": "Itens do pedido inválidos."}), 400
    if not quantities:
        return jsonify({"success": False, "error": "Selecione pelo menos um produto."}), 400

    db = _db()
    try:
        catalogo = _catalogo_por_token(db, token)
        if not catalogo or not catalogo["ativo"]:
            abort(404)
        rows = db.execute(text("""
            SELECT p.produto_id, p.codigo_interno, p.descricao, p.unidade_comercial, cvi.preco_unitario
            FROM catalogos_vendas_itens cvi JOIN produtos p ON p.produto_id=cvi.produto_id
            WHERE cvi.catalogo_id=:catalogo_id AND p.ativo=true
        """), {"catalogo_id": catalogo["catalogo_id"]}).mappings().all()
        produtos = {int(row["produto_id"]): row for row in rows}
        if not set(quantities).issubset(produtos):
            return jsonify({"success": False, "error": "Um dos produtos não está mais disponível."}), 409
        itens = []
        total = Decimal("0.00")
        for produto_id, quantidade in quantities.items():
            produto = produtos[produto_id]
            valor_unitario = Decimal(produto["preco_unitario"]).quantize(Decimal("0.01"))
            valor_total = (valor_unitario * quantidade).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += valor_total
            itens.append({**produto, "quantidade": quantidade, "valor_unitario": valor_unitario, "valor_total": valor_total})
        token_pedido = secrets.token_urlsafe(18)
        pedido_id = db.execute(text("""
            INSERT INTO pedidos_vendas
                (cliente_id, catalogo_id, token_publico, numero, comprador_nome, comprador_telefone,
                 comprador_email, observacao, status, status_pagamento, valor_total)
            VALUES (:cliente_id, :catalogo_id, :token, :numero, :nome, :telefone, :email, :observacao,
                    :status, :status_pagamento, :total)
            RETURNING pedido_id
        """), {
            "cliente_id": catalogo["cliente_id"], "catalogo_id": catalogo["catalogo_id"],
            "token": token_pedido, "numero": f"PV-{token_pedido[:8].upper()}", "nome": comprador_nome,
            "telefone": comprador_telefone, "email": str(payload.get("comprador_email") or "").strip() or None,
            "observacao": str(payload.get("observacao") or "").strip() or None,
            "status": "AGUARDANDO_PAGAMENTO" if catalogo["pagamento_online_ativo"] else "AGUARDANDO_ATENDIMENTO",
            "status_pagamento": "PENDENTE" if catalogo["pagamento_online_ativo"] else "NAO_SOLICITADO", "total": total,
        }).scalar_one()
        pedido = db.execute(text("SELECT * FROM pedidos_vendas WHERE pedido_id=:pedido_id"), {"pedido_id": pedido_id}).mappings().one()
        for item in itens:
            db.execute(text("""
                INSERT INTO pedidos_vendas_itens
                    (pedido_id, produto_id, codigo_produto, descricao, unidade, quantidade, valor_unitario, valor_total)
                VALUES (:pedido_id, :produto_id, :codigo, :descricao, :unidade, :quantidade, :unitario, :total)
            """), {"pedido_id": pedido_id, "produto_id": item["produto_id"], "codigo": item["codigo_interno"],
                   "descricao": item["descricao"], "unidade": item["unidade_comercial"], "quantidade": item["quantidade"],
                   "unitario": item["valor_unitario"], "total": item["valor_total"]})
        db.commit()

        if catalogo["pagamento_online_ativo"]:
            try:
                retorno = url_for("catalogo_publico.retorno_pagamento", token=token_pedido, _external=True)
                checkout_url = pagamentos.create_checkout(db, pedido=pedido, itens=itens, return_url=retorno)
                db.execute(text("""UPDATE pedidos_vendas SET provider='mercadopago', provider_reference=:reference,
                                  updated_at=CURRENT_TIMESTAMP WHERE pedido_id=:pedido_id"""),
                           {"reference": checkout_url, "pedido_id": pedido_id})
                db.commit()
                return jsonify({"success": True, "next_action": "payment", "redirect_url": checkout_url})
            except pagamentos.PagamentoConfiguracaoInvalida:
                db.rollback()
                db.execute(text("""UPDATE pedidos_vendas SET status='AGUARDANDO_ATENDIMENTO', status_pagamento='NAO_SOLICITADO',
                                  updated_at=CURRENT_TIMESTAMP WHERE pedido_id=:pedido_id"""), {"pedido_id": pedido_id})
                db.commit()
        whatsapp = _whatsapp_url(catalogo["whatsapp_numero"] or catalogo["telefone_loja"], pedido, itens)
        return jsonify({"success": True, "next_action": "whatsapp", "redirect_url": whatsapp,
                        "confirmation_url": url_for("catalogo_publico.pedido_recebido", token=token_pedido)})
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@catalogo_publico_bp.get("/catalogo/pedido/<token>")
def pedido_recebido(token: str):
    db = _db()
    try:
        pedido = db.execute(text("""
            SELECT pv.*, COALESCE(c.nome_fantasia, c.razao_social) AS loja_nome
            FROM pedidos_vendas pv JOIN clientes c ON c.cliente_id=pv.cliente_id
            WHERE pv.token_publico=:token
        """), {"token": token}).mappings().first()
        if not pedido:
            abort(404)
        return render_template("public/pedido_recebido.html", pedido=pedido)
    finally:
        db.close()


@catalogo_publico_bp.get("/catalogo/pedido/<token>/retorno")
def retorno_pagamento(token: str):
    db = _db()
    try:
        pedido = db.execute(text("SELECT * FROM pedidos_vendas WHERE token_publico=:token"), {"token": token}).mappings().first()
        if not pedido:
            abort(404)
        payment_id = request.args.get("payment_id") or request.args.get("collection_id")
        if payment_id:
            try:
                status = pagamentos.verify_payment(db, pedido=pedido, payment_id=str(payment_id))
                payment_status = {"APPROVED": "APROVADO", "REJECTED": "RECUSADO", "CANCELLED": "CANCELADO"}.get(status, "PENDENTE")
                order_status = "PAGO" if payment_status == "APROVADO" else "AGUARDANDO_PAGAMENTO"
                db.execute(text("""UPDATE pedidos_vendas SET status=:status, status_pagamento=:payment_status,
                                  provider_reference=:reference, updated_at=CURRENT_TIMESTAMP WHERE pedido_id=:pedido_id"""),
                           {"status": order_status, "payment_status": payment_status,
                            "reference": str(payment_id), "pedido_id": pedido["pedido_id"]})
                db.commit()
            except pagamentos.PagamentoConfiguracaoInvalida:
                db.rollback()
        return redirect(url_for("catalogo_publico.pedido_recebido", token=token))
    finally:
        db.close()

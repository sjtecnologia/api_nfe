"""Orçamentos, portal de clientes finais e conversão em pedidos."""
from __future__ import annotations

import json
import logging
import secrets
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import text

from auth.decorators import admin_required, portal_cliente_required
from database.connection import get_db
from services import orcamentos_service as notificacoes
from utils.password import hash_password

logger = logging.getLogger(__name__)

orcamentos_bp = Blueprint("orcamentos", __name__, url_prefix="/admin/orcamentos")
portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


STATUS_LABELS = {
    "RASCUNHO": "Rascunho",
    "SOLICITADO": "Solicitado pelo cliente",
    "ENVIADO": "Enviado ao cliente",
    "APROVADO": "Aprovado",
    "RECUSADO": "Recusado",
    "CONVERTIDO": "Convertido em pedido",
    "CANCELADO": "Cancelado",
}
STATUS_BADGES = {
    "RASCUNHO": "secondary",
    "SOLICITADO": "warning",
    "ENVIADO": "info",
    "APROVADO": "success",
    "RECUSADO": "danger",
    "CONVERTIDO": "primary",
    "CANCELADO": "dark",
}
ORIGEM_LABELS = {"INTERNO": "Interno", "PORTAL": "Portal do cliente"}


def _db():
    return next(get_db())


def _cliente_ativo() -> int:
    cliente_id = session.get("current_client_id") or session.get("active_cliente_id")
    if not cliente_id:
        abort(400, "Selecione uma empresa antes de acessar os orçamentos.")
    return int(cliente_id)


def _to_decimal(value, default: Decimal | None = None) -> Decimal:
    if value is None or str(value).strip() == "":
        if default is not None:
            return default
        raise ValueError("Valor obrigatório.")
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor numérico inválido.") from exc


def _parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _int_or_none(value):
    try:
        return int(value) if value not in (None, "", "0") else None
    except (TypeError, ValueError):
        return None


def _numero_orcamento() -> str:
    return f"ORC-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def _numero_pedido(token: str) -> str:
    return f"PV-{token[:8].upper()}"


def _validar_novo_status(status_atual: str, novo_status: str) -> str | None:
    """Valida transições de status feitas pelos formulários.

    A conversão em pedido é uma operação própria (gera o pedido de venda), por
    isso não pode ser feita pela simples troca de status. Um orçamento já
    convertido também não volta para outros status.
    """
    if novo_status not in STATUS_LABELS:
        return "Status inválido."
    if novo_status == "CONVERTIDO":
        return "Use a ação \"Converter em pedido\" para gerar o pedido de venda."
    if status_atual == "CONVERTIDO":
        return "Um orçamento convertido em pedido não pode voltar de status."
    return None


def _pode_converter(status_atual: str) -> str | None:
    """Retorna o motivo pelo qual o orçamento não pode ser convertido."""
    if status_atual == "CONVERTIDO":
        return "Este orçamento já foi convertido em pedido."
    if status_atual == "CANCELADO":
        return "Não é possível converter um orçamento cancelado."
    return None


def _produtos_empresa(db, cliente_id: int):
    return db.execute(text("""
        SELECT produto_id, codigo_interno, descricao, unidade_comercial, preco_unitario_padrao
        FROM produtos
        WHERE cliente_id = :cliente_id AND ativo = true
        ORDER BY descricao
    """), {"cliente_id": cliente_id}).mappings().all()


def _destinatarios_empresa(db, cliente_id: int):
    return db.execute(text("""
        SELECT destinatario_id, nome_razao_social, cpf_cnpj, email, telefone
        FROM destinatarios_nfe
        WHERE cliente_id = :cliente_id
        ORDER BY nome_razao_social
    """), {"cliente_id": cliente_id}).mappings().all()


def _buscar_orcamento_empresa(db, orcamento_id: int, cliente_id: int):
    return db.execute(text("""
        SELECT o.*,
               d.nome_razao_social AS cliente_nome,
               d.cpf_cnpj AS cliente_cpf_cnpj,
               d.email AS cliente_email,
               d.telefone AS cliente_telefone,
               pu.nome AS portal_nome,
               pu.email AS portal_email,
               pu.telefone AS portal_telefone,
               pv.numero AS pedido_numero
        FROM orcamentos o
        LEFT JOIN destinatarios_nfe d ON d.destinatario_id = o.destinatario_id
        LEFT JOIN portal_usuarios pu ON pu.portal_usuario_id = o.portal_usuario_id
        LEFT JOIN pedidos_vendas pv ON pv.pedido_id = o.pedido_id
        WHERE o.orcamento_id = :orcamento_id AND o.cliente_id = :cliente_id
    """), {"orcamento_id": orcamento_id, "cliente_id": cliente_id}).mappings().first()


def _itens_orcamento(db, orcamento_id: int):
    return db.execute(text("""
        SELECT * FROM orcamentos_itens
        WHERE orcamento_id = :orcamento_id
        ORDER BY orcamento_item_id
    """), {"orcamento_id": orcamento_id}).mappings().all()


def _itens_do_formulario(form) -> list[dict]:
    raw_json = form.get("itens_json")
    if raw_json:
        try:
            data = json.loads(raw_json)
        except (TypeError, ValueError) as exc:
            raise ValueError("Lista de itens inválida.") from exc
        if not isinstance(data, list):
            raise ValueError("Lista de itens inválida.")
        return [row for row in data if isinstance(row, dict)]

    ids = form.getlist("produto_id")
    quantidades = form.getlist("quantidade")
    valores = form.getlist("valor_unitario")
    itens = []
    for index, produto_id in enumerate(ids):
        if not produto_id:
            continue
        itens.append({
            "produto_id": produto_id,
            "quantidade": quantidades[index] if index < len(quantidades) else "",
            "valor_unitario": valores[index] if index < len(valores) else "",
        })
    return itens


def _resolver_itens(db, cliente_id: int, itens_form: list[dict], *, preco_padrao: bool = False):
    """Valida os itens contra o catálogo da empresa e calcula os totais."""
    if not itens_form:
        raise ValueError("Adicione pelo menos um produto ao orçamento.")

    produtos = {int(row["produto_id"]): row for row in _produtos_empresa(db, cliente_id)}
    itens = []
    total = Decimal("0.00")
    for row in itens_form:
        produto_id = _int_or_none(row.get("produto_id"))
        if not produto_id or produto_id not in produtos:
            raise ValueError("Um dos produtos selecionados não pertence a esta empresa.")

        quantidade = _to_decimal(row.get("quantidade"))
        quantidade = quantidade.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        if quantidade <= 0 or quantidade > Decimal("9999"):
            raise ValueError("A quantidade deve ser maior que zero e menor que 9.999.")

        produto = produtos[produto_id]
        if preco_padrao:
            valor_unitario = Decimal(produto["preco_unitario_padrao"])
        else:
            valor_unitario = _to_decimal(row.get("valor_unitario"), Decimal(produto["preco_unitario_padrao"]))
        valor_unitario = valor_unitario.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if valor_unitario < 0:
            raise ValueError("O valor unitário não pode ser negativo.")

        valor_total = (valor_unitario * quantidade).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += valor_total
        itens.append({
            "produto_id": produto_id,
            "codigo_produto": produto["codigo_interno"],
            "descricao": produto["descricao"],
            "unidade": produto["unidade_comercial"],
            "quantidade": quantidade,
            "valor_unitario": valor_unitario,
            "valor_total": valor_total,
        })
    return itens, total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _notificar_seguro(db, **kwargs):
    """Cria notificações sem derrubar a operação principal caso o e-mail falhe."""
    try:
        resultado = notificacoes.notificar_empresa(db, **kwargs)
        db.commit()
        return resultado
    except Exception as exc:
        db.rollback()
        logger.warning("Falha ao notificar empresa: %s", exc)
        return []


def _notificar_usuario_seguro(db, *, emails_extras: list[str] | None = None, **kwargs):
    try:
        notificacoes.criar_notificacao(db, emails_extras=emails_extras, **kwargs)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Falha ao notificar usuário: %s", exc)


# ---------------------------------------------------------------------------
# Orçamentos - área da empresa assinante
# ---------------------------------------------------------------------------
@orcamentos_bp.get("")
@login_required
@admin_required()
def listar():
    cliente_id = _cliente_ativo()
    status = (request.args.get("status") or "").strip().upper()
    origem = (request.args.get("origem") or "").strip().upper()
    busca = (request.args.get("q") or "").strip()
    db = _db()
    try:
        where = ["o.cliente_id = :cliente_id"]
        params = {"cliente_id": cliente_id}
        if status in STATUS_LABELS:
            where.append("o.status = :status")
            params["status"] = status
        if origem in ORIGEM_LABELS:
            where.append("o.origem = :origem")
            params["origem"] = origem
        if busca:
            where.append("(o.numero ILIKE :busca OR d.nome_razao_social ILIKE :busca OR pu.nome ILIKE :busca)")
            params["busca"] = f"%{busca}%"

        rows = db.execute(text(f"""
            SELECT o.*, d.nome_razao_social AS cliente_nome,
                   pu.nome AS portal_nome, pv.numero AS pedido_numero,
                   (SELECT COUNT(*) FROM orcamentos_itens oi WHERE oi.orcamento_id = o.orcamento_id) AS total_itens
            FROM orcamentos o
            LEFT JOIN destinatarios_nfe d ON d.destinatario_id = o.destinatario_id
            LEFT JOIN portal_usuarios pu ON pu.portal_usuario_id = o.portal_usuario_id
            LEFT JOIN pedidos_vendas pv ON pv.pedido_id = o.pedido_id
            WHERE {' AND '.join(where)}
            ORDER BY o.created_at DESC
            LIMIT 200
        """), params).mappings().all()

        contadores = db.execute(text("""
            SELECT status, COUNT(*) AS total
            FROM orcamentos WHERE cliente_id = :cliente_id
            GROUP BY status
        """), {"cliente_id": cliente_id}).mappings().all()
        contadores = {row["status"]: row["total"] for row in contadores}

        notificacoes_recentes = notificacoes.listar_notificacoes(db, current_user.id, cliente_id, limite=8)
        return render_template(
            "admin/orcamentos/list.html",
            orcamentos=rows,
            contadores=contadores,
            notificacoes=notificacoes_recentes,
            status_labels=STATUS_LABELS,
            status_badges=STATUS_BADGES,
            origem_labels=ORIGEM_LABELS,
            filtros={"status": status, "origem": origem, "q": busca},
        )
    finally:
        db.close()


@orcamentos_bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required()
def novo():
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        produtos = _produtos_empresa(db, cliente_id)
        destinatarios = _destinatarios_empresa(db, cliente_id)
        if request.method == "GET":
            return render_template(
                "admin/orcamentos/form.html",
                orcamento=None,
                itens=[],
                produtos=produtos,
                destinatarios=destinatarios,
                status_labels=STATUS_LABELS,
                form_data={},
            )

        destinatario_id = _int_or_none(request.form.get("destinatario_id"))
        if destinatario_id:
            existe = db.execute(text("""
                SELECT 1 FROM destinatarios_nfe
                WHERE destinatario_id = :destinatario_id AND cliente_id = :cliente_id
            """), {"destinatario_id": destinatario_id, "cliente_id": cliente_id}).first()
            if not existe:
                abort(400, "Cliente inválido para esta empresa.")

        try:
            itens, total = _resolver_itens(db, cliente_id, _itens_do_formulario(request.form))
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template(
                "admin/orcamentos/form.html",
                orcamento=None,
                itens=[],
                produtos=produtos,
                destinatarios=destinatarios,
                status_labels=STATUS_LABELS,
                form_data=request.form,
            ), 400

        status = "ENVIADO" if request.form.get("enviar") == "1" else "RASCUNHO"
        numero = _numero_orcamento()
        orcamento_id = db.execute(text("""
            INSERT INTO orcamentos
                (cliente_id, destinatario_id, numero, origem, status, validade,
                 observacao, valor_total, created_by_user_id)
            VALUES
                (:cliente_id, :destinatario_id, :numero, 'INTERNO', :status, :validade,
                 :observacao, :valor_total, :user_id)
            RETURNING orcamento_id
        """), {
            "cliente_id": cliente_id,
            "destinatario_id": destinatario_id,
            "numero": numero,
            "status": status,
            "validade": _parse_date(request.form.get("validade")),
            "observacao": (request.form.get("observacao") or "").strip() or None,
            "valor_total": total,
            "user_id": current_user.id,
        }).scalar_one()

        for item in itens:
            db.execute(text("""
                INSERT INTO orcamentos_itens
                    (orcamento_id, produto_id, codigo_produto, descricao, unidade,
                     quantidade, valor_unitario, valor_total)
                VALUES
                    (:orcamento_id, :produto_id, :codigo_produto, :descricao, :unidade,
                     :quantidade, :valor_unitario, :valor_total)
            """), {"orcamento_id": orcamento_id, **item})
        db.commit()
        flash(f"Orçamento {numero} criado com sucesso.", "success")
        return redirect(url_for("orcamentos.detalhe", orcamento_id=orcamento_id))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@orcamentos_bp.get("/<int:orcamento_id>")
@login_required
@admin_required()
def detalhe(orcamento_id: int):
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        orcamento = _buscar_orcamento_empresa(db, orcamento_id, cliente_id)
        if not orcamento:
            abort(404)
        itens = _itens_orcamento(db, orcamento_id)
        return render_template(
            "admin/orcamentos/detalhe.html",
            orcamento=orcamento,
            itens=itens,
            status_labels=STATUS_LABELS,
            status_badges=STATUS_BADGES,
            origem_labels=ORIGEM_LABELS,
        )
    finally:
        db.close()


@orcamentos_bp.route("/<int:orcamento_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required()
def editar(orcamento_id: int):
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        orcamento = _buscar_orcamento_empresa(db, orcamento_id, cliente_id)
        if not orcamento:
            abort(404)
        produtos = _produtos_empresa(db, cliente_id)
        destinatarios = _destinatarios_empresa(db, cliente_id)

        if request.method == "GET":
            return render_template(
                "admin/orcamentos/form.html",
                orcamento=orcamento,
                itens=_itens_orcamento(db, orcamento_id),
                produtos=produtos,
                destinatarios=destinatarios,
                status_labels=STATUS_LABELS,
                form_data={},
            )

        if orcamento["status"] in ("CONVERTIDO", "CANCELADO"):
            flash("Orçamentos convertidos ou cancelados não podem ser alterados.", "warning")
            return redirect(url_for("orcamentos.detalhe", orcamento_id=orcamento_id))

        destinatario_id = _int_or_none(request.form.get("destinatario_id"))
        if destinatario_id:
            existe = db.execute(text("""
                SELECT 1 FROM destinatarios_nfe
                WHERE destinatario_id = :destinatario_id AND cliente_id = :cliente_id
            """), {"destinatario_id": destinatario_id, "cliente_id": cliente_id}).first()
            if not existe:
                abort(400, "Cliente inválido para esta empresa.")

        try:
            itens, total = _resolver_itens(db, cliente_id, _itens_do_formulario(request.form))
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template(
                "admin/orcamentos/form.html",
                orcamento=orcamento,
                itens=_itens_orcamento(db, orcamento_id),
                produtos=produtos,
                destinatarios=destinatarios,
                status_labels=STATUS_LABELS,
                form_data=request.form,
            ), 400

        novo_status = (request.form.get("status") or orcamento["status"]).strip().upper()
        erro_status = _validar_novo_status(orcamento["status"], novo_status)
        if erro_status:
            # Status inválido é ignorado silenciosamente; transições proibidas
            # (conversão/cancelamento indevido) geram aviso para o usuário.
            if novo_status in STATUS_LABELS:
                flash(erro_status, "warning")
            novo_status = orcamento["status"]
        status_anterior = orcamento["status"]

        db.execute(text("""
            UPDATE orcamentos SET
                destinatario_id = :destinatario_id,
                status = :status,
                validade = :validade,
                observacao = :observacao,
                valor_total = :valor_total,
                updated_at = CURRENT_TIMESTAMP
            WHERE orcamento_id = :orcamento_id AND cliente_id = :cliente_id
        """), {
            "destinatario_id": destinatario_id,
            "status": novo_status,
            "validade": _parse_date(request.form.get("validade")),
            "observacao": (request.form.get("observacao") or "").strip() or None,
            "valor_total": total,
            "orcamento_id": orcamento_id,
            "cliente_id": cliente_id,
        })
        db.execute(text("DELETE FROM orcamentos_itens WHERE orcamento_id = :orcamento_id"),
                   {"orcamento_id": orcamento_id})
        for item in itens:
            db.execute(text("""
                INSERT INTO orcamentos_itens
                    (orcamento_id, produto_id, codigo_produto, descricao, unidade,
                     quantidade, valor_unitario, valor_total)
                VALUES
                    (:orcamento_id, :produto_id, :codigo_produto, :descricao, :unidade,
                     :quantidade, :valor_unitario, :valor_total)
            """), {"orcamento_id": orcamento_id, **item})
        db.commit()

        if novo_status == "ENVIADO" and status_anterior != "ENVIADO" and orcamento["portal_usuario_id"]:
            portal_email = db.execute(text("""
                SELECT email FROM portal_usuarios WHERE portal_usuario_id = :id
            """), {"id": orcamento["portal_usuario_id"]}).scalar()
            _notificar_usuario_seguro(
                db,
                cliente_id=cliente_id,
                user_id=_usuario_do_portal(db, orcamento["portal_usuario_id"]),
                tipo="ORCAMENTO_RESPONDIDO",
                titulo=f"Orçamento {orcamento['numero']} disponível",
                mensagem="A empresa respondeu seu pedido de orçamento. Confira os valores e aprove ou recuse.",
                link=url_for("portal.detalhe", orcamento_id=orcamento_id),
                referencia_tipo="ORCAMENTO",
                referencia_id=orcamento_id,
                enviar_email=True,
                emails_extras=[portal_email] if portal_email else None,
            )
        flash("Orçamento atualizado com sucesso.", "success")
        return redirect(url_for("orcamentos.detalhe", orcamento_id=orcamento_id))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@orcamentos_bp.post("/<int:orcamento_id>/status")
@login_required
@admin_required()
def alterar_status(orcamento_id: int):
    cliente_id = _cliente_ativo()
    novo_status = (request.form.get("status") or "").strip().upper()
    if novo_status not in STATUS_LABELS:
        abort(400, "Status inválido.")
    db = _db()
    try:
        orcamento = _buscar_orcamento_empresa(db, orcamento_id, cliente_id)
        if not orcamento:
            abort(404)
        erro_status = _validar_novo_status(orcamento["status"], novo_status)
        if erro_status:
            flash(erro_status, "warning")
            return redirect(url_for("orcamentos.detalhe", orcamento_id=orcamento_id))

        db.execute(text("""
            UPDATE orcamentos SET status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE orcamento_id = :orcamento_id AND cliente_id = :cliente_id
        """), {"status": novo_status, "orcamento_id": orcamento_id, "cliente_id": cliente_id})
        db.commit()

        if novo_status == "ENVIADO" and orcamento["status"] != "ENVIADO" and orcamento["portal_usuario_id"]:
            portal_email = db.execute(text("""
                SELECT email FROM portal_usuarios WHERE portal_usuario_id = :id
            """), {"id": orcamento["portal_usuario_id"]}).scalar()
            _notificar_usuario_seguro(
                db,
                cliente_id=cliente_id,
                user_id=_usuario_do_portal(db, orcamento["portal_usuario_id"]),
                tipo="ORCAMENTO_RESPONDIDO",
                titulo=f"Orçamento {orcamento['numero']} disponível",
                mensagem="A empresa respondeu seu pedido de orçamento. Confira os valores e aprove ou recuse.",
                link=url_for("portal.detalhe", orcamento_id=orcamento_id),
                referencia_tipo="ORCAMENTO",
                referencia_id=orcamento_id,
                enviar_email=True,
                emails_extras=[portal_email] if portal_email else None,
            )
        flash(f"Status alterado para {STATUS_LABELS[novo_status]}.", "success")
    finally:
        db.close()
    return redirect(url_for("orcamentos.detalhe", orcamento_id=orcamento_id))


@orcamentos_bp.post("/<int:orcamento_id>/converter")
@login_required
@admin_required()
def converter_em_pedido(orcamento_id: int):
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        orcamento = _buscar_orcamento_empresa(db, orcamento_id, cliente_id)
        if not orcamento:
            abort(404)
        erro_conversao = _pode_converter(orcamento["status"])
        if erro_conversao:
            categoria = "info" if orcamento["status"] == "CONVERTIDO" else "warning"
            flash(erro_conversao, categoria)
            return redirect(url_for("orcamentos.detalhe", orcamento_id=orcamento_id))

        itens = _itens_orcamento(db, orcamento_id)
        if not itens:
            flash("O orçamento não possui itens.", "warning")
            return redirect(url_for("orcamentos.detalhe", orcamento_id=orcamento_id))

        comprador_nome = orcamento["cliente_nome"] or orcamento["portal_nome"] or "Cliente"
        comprador_email = orcamento["cliente_email"] or orcamento["portal_email"]
        comprador_telefone = orcamento["cliente_telefone"] or orcamento["portal_telefone"] or ""
        token = secrets.token_urlsafe(18)
        pedido_id = db.execute(text("""
            INSERT INTO pedidos_vendas
                (cliente_id, catalogo_id, orcamento_id, token_publico, numero, comprador_nome,
                 comprador_telefone, comprador_email, observacao, status, status_pagamento, valor_total)
            VALUES
                (:cliente_id, NULL, :orcamento_id, :token, :numero, :comprador_nome,
                 :comprador_telefone, :comprador_email, :observacao, 'AGUARDANDO_ATENDIMENTO',
                 'NAO_SOLICITADO', :valor_total)
            RETURNING pedido_id
        """), {
            "cliente_id": cliente_id,
            "orcamento_id": orcamento_id,
            "token": token,
            "numero": _numero_pedido(token),
            "comprador_nome": comprador_nome,
            "comprador_telefone": comprador_telefone,
            "comprador_email": comprador_email,
            "observacao": orcamento["observacao"],
            "valor_total": orcamento["valor_total"],
        }).scalar_one()

        for item in itens:
            db.execute(text("""
                INSERT INTO pedidos_vendas_itens
                    (pedido_id, produto_id, codigo_produto, descricao, unidade,
                     quantidade, valor_unitario, valor_total)
                VALUES
                    (:pedido_id, :produto_id, :codigo_produto, :descricao, :unidade,
                     :quantidade, :valor_unitario, :valor_total)
            """), {
                "pedido_id": pedido_id,
                "produto_id": item["produto_id"],
                "codigo_produto": item["codigo_produto"],
                "descricao": item["descricao"],
                "unidade": item["unidade"],
                "quantidade": item["quantidade"],
                "valor_unitario": item["valor_unitario"],
                "valor_total": item["valor_total"],
            })

        pedido_numero = _numero_pedido(token)
        db.execute(text("""
            UPDATE orcamentos SET status = 'CONVERTIDO', pedido_id = :pedido_id,
                   updated_at = CURRENT_TIMESTAMP
            WHERE orcamento_id = :orcamento_id AND cliente_id = :cliente_id
        """), {"pedido_id": pedido_id, "orcamento_id": orcamento_id, "cliente_id": cliente_id})
        db.commit()

        if orcamento["portal_usuario_id"]:
            portal_email = db.execute(text("""
                SELECT email FROM portal_usuarios WHERE portal_usuario_id = :id
            """), {"id": orcamento["portal_usuario_id"]}).scalar()
            _notificar_usuario_seguro(
                db,
                cliente_id=cliente_id,
                user_id=_usuario_do_portal(db, orcamento["portal_usuario_id"]),
                tipo="ORCAMENTO_CONVERTIDO",
                titulo=f"Orçamento {orcamento['numero']} virou pedido",
                mensagem=f"Seu orçamento foi convertido no pedido {pedido_numero}.",
                link=url_for("portal.detalhe", orcamento_id=orcamento_id),
                referencia_tipo="ORCAMENTO",
                referencia_id=orcamento_id,
                enviar_email=True,
                emails_extras=[portal_email] if portal_email else None,
            )
        flash(f"Orçamento convertido no pedido {pedido_numero}.", "success")
        return redirect(url_for("orcamentos.detalhe", orcamento_id=orcamento_id))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Usuários do portal (clientes finais da empresa)
# ---------------------------------------------------------------------------
@orcamentos_bp.get("/portal-usuarios")
@login_required
@admin_required()
def listar_portal_usuarios():
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        usuarios = db.execute(text("""
            SELECT pu.*, u.username, u.email AS login_email, u._is_active
            FROM portal_usuarios pu
            JOIN users u ON u.id = pu.user_id
            LEFT JOIN destinatarios_nfe d ON d.destinatario_id = pu.destinatario_id
            WHERE pu.cliente_id = :cliente_id
            ORDER BY pu.nome
        """), {"cliente_id": cliente_id}).mappings().all()
        return render_template("admin/orcamentos/portal_usuarios/list.html", usuarios=usuarios)
    finally:
        db.close()


@orcamentos_bp.route("/portal-usuarios/novo", methods=["GET", "POST"])
@login_required
@admin_required()
def novo_portal_usuario():
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        destinatarios = _destinatarios_empresa(db, cliente_id)
        if request.method == "GET":
            return render_template(
                "admin/orcamentos/portal_usuarios/form.html",
                destinatarios=destinatarios,
                form_data={},
            )

        nome = (request.form.get("nome") or "").strip()
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        telefone = "".join(ch for ch in (request.form.get("telefone") or "") if ch.isdigit())
        senha = request.form.get("password") or ""
        confirmacao = request.form.get("confirm_password") or ""
        destinatario_id = _int_or_none(request.form.get("destinatario_id"))

        erro = None
        if not nome or not username or not email or not senha:
            erro = "Informe nome, login, e-mail e senha."
        elif len(telefone) < 10:
            erro = "Informe um telefone/WhatsApp válido com DDD."
        elif len(senha) < 8 or not any(c.isupper() for c in senha) or not any(c.islower() for c in senha) or not any(c.isdigit() for c in senha):
            erro = "A senha deve ter no mínimo 8 caracteres, com maiúscula, minúscula e número."
        elif senha != confirmacao:
            erro = "As senhas não coincidem."
        if destinatario_id:
            existe = db.execute(text("""
                SELECT 1 FROM destinatarios_nfe
                WHERE destinatario_id = :destinatario_id AND cliente_id = :cliente_id
            """), {"destinatario_id": destinatario_id, "cliente_id": cliente_id}).first()
            if not existe:
                erro = "Cliente final inválido para esta empresa."

        role = db.execute(text("SELECT id FROM roles WHERE LOWER(name) = 'cliente' LIMIT 1")).first()
        if not role:
            erro = "Execute a migração 019_create_orcamentos_portal.sql para habilitar o portal."

        if erro:
            flash(erro, "danger")
            return render_template(
                "admin/orcamentos/portal_usuarios/form.html",
                destinatarios=destinatarios,
                form_data=request.form,
            ), 400

        try:
            user_id = db.execute(text("""
                INSERT INTO users (username, email, password_hash, _is_active)
                VALUES (:username, :email, :password_hash, true)
                RETURNING id
            """), {
                "username": username,
                "email": email,
                "password_hash": hash_password(senha),
            }).scalar_one()
            db.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
                       {"user_id": user_id, "role_id": role.id})
            db.execute(text("INSERT INTO user_clients (user_id, client_id) VALUES (:user_id, :cliente_id)"),
                       {"user_id": user_id, "cliente_id": cliente_id})
            db.execute(text("""
                INSERT INTO portal_usuarios
                    (user_id, cliente_id, destinatario_id, nome, email, telefone, created_by_user_id)
                VALUES
                    (:user_id, :cliente_id, :destinatario_id, :nome, :email, :telefone, :created_by)
            """), {
                "user_id": user_id,
                "cliente_id": cliente_id,
                "destinatario_id": destinatario_id,
                "nome": nome,
                "email": email,
                "telefone": telefone,
                "created_by": current_user.id,
            })
            db.commit()
            flash(f"Usuário do portal {nome} criado com sucesso.", "success")
            return redirect(url_for("orcamentos.listar_portal_usuarios"))
        except Exception as exc:
            db.rollback()
            if "duplicate key value violates unique constraint" in str(exc):
                flash("Já existe um usuário com esse login ou e-mail.", "warning")
            else:
                logger.error("Erro ao criar usuário do portal: %s", exc, exc_info=True)
                flash("Não foi possível criar o usuário do portal.", "danger")
            return render_template(
                "admin/orcamentos/portal_usuarios/form.html",
                destinatarios=destinatarios,
                form_data=request.form,
            ), 400
    finally:
        db.close()


@orcamentos_bp.post("/portal-usuarios/<int:portal_usuario_id>/alternar")
@login_required
@admin_required()
def alternar_portal_usuario(portal_usuario_id: int):
    cliente_id = _cliente_ativo()
    db = _db()
    try:
        perfil = db.execute(text("""
            SELECT user_id, ativo FROM portal_usuarios
            WHERE portal_usuario_id = :id AND cliente_id = :cliente_id
        """), {"id": portal_usuario_id, "cliente_id": cliente_id}).first()
        if not perfil:
            abort(404)
        novo_ativo = not perfil.ativo
        db.execute(text("""
            UPDATE portal_usuarios SET ativo = :ativo, updated_at = CURRENT_TIMESTAMP
            WHERE portal_usuario_id = :id
        """), {"ativo": novo_ativo, "id": portal_usuario_id})
        db.execute(text("UPDATE users SET _is_active = :ativo WHERE id = :user_id"),
                   {"ativo": novo_ativo, "user_id": perfil.user_id})
        db.commit()
        flash("Acesso do usuário do portal atualizado.", "success")
    finally:
        db.close()
    return redirect(url_for("orcamentos.listar_portal_usuarios"))


# ---------------------------------------------------------------------------
# Notificações - área da empresa
# ---------------------------------------------------------------------------
@orcamentos_bp.get("/notificacoes")
@login_required
@admin_required()
def listar_notificacoes():
    cliente_id = session.get("current_client_id") or session.get("active_cliente_id")
    cliente_id = int(cliente_id) if cliente_id else None
    db = _db()
    try:
        lista = notificacoes.listar_notificacoes(db, current_user.id, cliente_id)
        return render_template("admin/orcamentos/notificacoes.html", notificacoes=lista)
    finally:
        db.close()


@orcamentos_bp.post("/notificacoes/<int:notificacao_id>/ler")
@login_required
@admin_required()
def ler_notificacao(notificacao_id: int):
    cliente_id = session.get("current_client_id") or session.get("active_cliente_id")
    cliente_id = int(cliente_id) if cliente_id else None
    db = _db()
    try:
        notificacoes.marcar_notificacao_lida(db, notificacao_id, current_user.id, cliente_id)
        db.commit()
        destino = request.form.get("link") or url_for("orcamentos.listar_notificacoes")
        if not destino.startswith("/"):
            destino = url_for("orcamentos.listar_notificacoes")
        return redirect(destino)
    finally:
        db.close()


@orcamentos_bp.post("/notificacoes/ler-todas")
@login_required
@admin_required()
def ler_todas_notificacoes():
    cliente_id = session.get("current_client_id") or session.get("active_cliente_id")
    cliente_id = int(cliente_id) if cliente_id else None
    db = _db()
    try:
        notificacoes.marcar_todas_lidas(db, current_user.id, cliente_id)
        db.commit()
        flash("Todas as notificações foram marcadas como lidas.", "success")
    finally:
        db.close()
    return redirect(url_for("orcamentos.listar_notificacoes"))


def _usuario_do_portal(db, portal_usuario_id: int | None):
    if not portal_usuario_id:
        return None
    row = db.execute(text("""
        SELECT user_id FROM portal_usuarios WHERE portal_usuario_id = :id
    """), {"id": portal_usuario_id}).first()
    return row.user_id if row else None


# ---------------------------------------------------------------------------
# Portal do cliente final
# ---------------------------------------------------------------------------
def _perfil_portal(db):
    perfil = getattr(g, "portal_cliente", None)
    if perfil:
        return perfil
    row = db.execute(text("""
        SELECT pu.portal_usuario_id, pu.cliente_id, pu.destinatario_id, pu.nome,
               pu.email, pu.telefone, c.razao_social, c.nome_fantasia, c.email_contato,
               c.telefone_contato
        FROM portal_usuarios pu
        JOIN clientes c ON c.cliente_id = pu.cliente_id
        WHERE pu.user_id = :user_id AND pu.ativo = true
        LIMIT 1
    """), {"user_id": current_user.id}).mappings().first()
    return dict(row) if row else None


@portal_bp.get("")
@login_required
@portal_cliente_required()
def dashboard():
    db = _db()
    try:
        perfil = _perfil_portal(db)
        if not perfil:
            abort(403)
        orcamentos = db.execute(text("""
            SELECT o.*,
                   (SELECT COUNT(*) FROM orcamentos_itens oi WHERE oi.orcamento_id = o.orcamento_id) AS total_itens
            FROM orcamentos o
            WHERE o.portal_usuario_id = :portal_usuario_id
            ORDER BY o.created_at DESC
            LIMIT 100
        """), {"portal_usuario_id": perfil["portal_usuario_id"]}).mappings().all()
        minhas_notificacoes = notificacoes.listar_notificacoes(
            db, current_user.id, perfil["cliente_id"], limite=20, incluir_empresa=False
        )
        return render_template(
            "portal/dashboard.html",
            perfil=perfil,
            orcamentos=orcamentos,
            notificacoes=minhas_notificacoes,
            status_labels=STATUS_LABELS,
            status_badges=STATUS_BADGES,
        )
    finally:
        db.close()


@portal_bp.route("/orcamentos/novo", methods=["GET", "POST"])
@login_required
@portal_cliente_required()
def novo_orcamento():
    db = _db()
    try:
        perfil = _perfil_portal(db)
        if not perfil:
            abort(403)
        produtos = _produtos_empresa(db, perfil["cliente_id"])

        if request.method == "GET":
            return render_template("portal/form.html", perfil=perfil, produtos=produtos)

        itens_form = []
        for produto in produtos:
            quantidade = request.form.get(f"qtd_{produto['produto_id']}")
            if not quantidade:
                continue
            try:
                quantidade_decimal = _to_decimal(quantidade, Decimal("0"))
            except ValueError:
                continue
            if quantidade_decimal > 0:
                itens_form.append({
                    "produto_id": produto["produto_id"],
                    "quantidade": quantidade_decimal,
                })
        if not itens_form:
            flash("Selecione pelo menos um produto e informe a quantidade.", "warning")
            return render_template("portal/form.html", perfil=perfil, produtos=produtos), 400

        try:
            itens, total = _resolver_itens(db, perfil["cliente_id"], itens_form, preco_padrao=True)
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("portal/form.html", perfil=perfil, produtos=produtos), 400

        numero = _numero_orcamento()
        orcamento_id = db.execute(text("""
            INSERT INTO orcamentos
                (cliente_id, destinatario_id, portal_usuario_id, numero, origem, status,
                 observacao, valor_total, created_by_user_id)
            VALUES
                (:cliente_id, :destinatario_id, :portal_usuario_id, :numero, 'PORTAL', 'SOLICITADO',
                 :observacao, :valor_total, :user_id)
            RETURNING orcamento_id
        """), {
            "cliente_id": perfil["cliente_id"],
            "destinatario_id": perfil.get("destinatario_id"),
            "portal_usuario_id": perfil["portal_usuario_id"],
            "numero": numero,
            "observacao": (request.form.get("observacao") or "").strip() or None,
            "valor_total": total,
            "user_id": current_user.id,
        }).scalar_one()

        for item in itens:
            db.execute(text("""
                INSERT INTO orcamentos_itens
                    (orcamento_id, produto_id, codigo_produto, descricao, unidade,
                     quantidade, valor_unitario, valor_total)
                VALUES
                    (:orcamento_id, :produto_id, :codigo_produto, :descricao, :unidade,
                     :quantidade, :valor_unitario, :valor_total)
            """), {"orcamento_id": orcamento_id, **item})
        db.commit()

        _notificar_seguro(
            db,
            cliente_id=perfil["cliente_id"],
            tipo="ORCAMENTO_SOLICITADO",
            titulo=f"Novo pedido de orçamento {numero}",
            mensagem=(
                f"{perfil['nome']} solicitou um orçamento com {len(itens)} item(ns). "
                f"Valor estimado: R$ {total:.2f}."
            ),
            link=url_for("orcamentos.detalhe", orcamento_id=orcamento_id),
            referencia_tipo="ORCAMENTO",
            referencia_id=orcamento_id,
        )
        flash("Pedido de orçamento enviado! A empresa foi notificada.", "success")
        return redirect(url_for("portal.detalhe", orcamento_id=orcamento_id))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@portal_bp.get("/orcamentos/<int:orcamento_id>")
@login_required
@portal_cliente_required()
def detalhe(orcamento_id: int):
    db = _db()
    try:
        perfil = _perfil_portal(db)
        if not perfil:
            abort(403)
        orcamento = db.execute(text("""
            SELECT o.*, c.razao_social AS empresa_razao_social,
                   c.nome_fantasia AS empresa_nome_fantasia, c.telefone_contato AS empresa_telefone,
                   pv.numero AS pedido_numero
            FROM orcamentos o
            JOIN clientes c ON c.cliente_id = o.cliente_id
            LEFT JOIN pedidos_vendas pv ON pv.pedido_id = o.pedido_id
            WHERE o.orcamento_id = :orcamento_id AND o.portal_usuario_id = :portal_usuario_id
        """), {
            "orcamento_id": orcamento_id,
            "portal_usuario_id": perfil["portal_usuario_id"],
        }).mappings().first()
        if not orcamento:
            abort(404)
        itens = _itens_orcamento(db, orcamento_id)
        return render_template(
            "portal/detalhe.html",
            perfil=perfil,
            orcamento=orcamento,
            itens=itens,
            status_labels=STATUS_LABELS,
            status_badges=STATUS_BADGES,
        )
    finally:
        db.close()


@portal_bp.post("/orcamentos/<int:orcamento_id>/aprovar")
@login_required
@portal_cliente_required()
def aprovar(orcamento_id: int):
    return _responder_orcamento(orcamento_id, "APROVADO")


@portal_bp.post("/orcamentos/<int:orcamento_id>/recusar")
@login_required
@portal_cliente_required()
def recusar(orcamento_id: int):
    return _responder_orcamento(orcamento_id, "RECUSADO")


def _responder_orcamento(orcamento_id: int, novo_status: str):
    db = _db()
    try:
        perfil = _perfil_portal(db)
        if not perfil:
            abort(403)
        orcamento = db.execute(text("""
            SELECT * FROM orcamentos
            WHERE orcamento_id = :orcamento_id AND portal_usuario_id = :portal_usuario_id
        """), {
            "orcamento_id": orcamento_id,
            "portal_usuario_id": perfil["portal_usuario_id"],
        }).mappings().first()
        if not orcamento:
            abort(404)
        if orcamento["status"] not in ("ENVIADO", "SOLICITADO"):
            flash("Este orçamento não está disponível para aprovação ou recusa.", "warning")
            return redirect(url_for("portal.detalhe", orcamento_id=orcamento_id))

        db.execute(text("""
            UPDATE orcamentos SET status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE orcamento_id = :orcamento_id
        """), {"status": novo_status, "orcamento_id": orcamento_id})
        db.commit()

        acao = "aprovou" if novo_status == "APROVADO" else "recusou"
        _notificar_seguro(
            db,
            cliente_id=perfil["cliente_id"],
            tipo=f"ORCAMENTO_{novo_status}",
            titulo=f"Orçamento {orcamento['numero']} {acao} pelo cliente",
            mensagem=f"{perfil['nome']} {acao} o orçamento {orcamento['numero']}.",
            link=url_for("orcamentos.detalhe", orcamento_id=orcamento_id),
            referencia_tipo="ORCAMENTO",
            referencia_id=orcamento_id,
        )
        flash(f"Orçamento {acao} com sucesso.", "success")
    finally:
        db.close()
    return redirect(url_for("portal.detalhe", orcamento_id=orcamento_id))


@portal_bp.get("/notificacoes")
@login_required
@portal_cliente_required()
def notificacoes_portal():
    db = _db()
    try:
        perfil = _perfil_portal(db)
        if not perfil:
            abort(403)
        lista = notificacoes.listar_notificacoes(
            db, current_user.id, perfil["cliente_id"], incluir_empresa=False
        )
        return render_template("portal/notificacoes.html", perfil=perfil, notificacoes=lista)
    finally:
        db.close()


@portal_bp.post("/notificacoes/<int:notificacao_id>/ler")
@login_required
@portal_cliente_required()
def ler_notificacao_portal(notificacao_id: int):
    db = _db()
    try:
        perfil = _perfil_portal(db)
        if not perfil:
            abort(403)
        notificacoes.marcar_notificacao_lida(
            db, notificacao_id, current_user.id, perfil["cliente_id"]
        )
        db.commit()
        destino = request.form.get("link") or url_for("portal.notificacoes_portal")
        if not destino.startswith("/"):
            destino = url_for("portal.notificacoes_portal")
        return redirect(destino)
    finally:
        db.close()

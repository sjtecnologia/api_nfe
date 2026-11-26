"""Testes do módulo de orçamentos, portal do cliente e notificações."""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest
from werkzeug.datastructures import MultiDict

from routes import orcamentos_routes as rotas
from services import orcamentos_service

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers de conversão e leitura do formulário
# ---------------------------------------------------------------------------
def test_to_decimal_accepts_brazilian_and_us_formats():
    assert rotas._to_decimal("10,50") == Decimal("10.50")
    assert rotas._to_decimal("10.50") == Decimal("10.50")
    assert rotas._to_decimal("", default=Decimal("0")) == Decimal("0")


@pytest.mark.parametrize("valor", ["", "abc", "1.2.3"])
def test_to_decimal_rejects_invalid_values(valor):
    with pytest.raises(ValueError):
        rotas._to_decimal(valor)


def test_parse_date_accepts_iso_and_brazilian_formats():
    assert rotas._parse_date("2026-11-06").isoformat() == "2026-11-06"
    assert rotas._parse_date("06/11/2026").isoformat() == "2026-11-06"
    assert rotas._parse_date("") is None
    assert rotas._parse_date("data inválida") is None


def test_itens_do_formulario_prioriza_json():
    form = MultiDict([("itens_json", '[{"produto_id": 1, "quantidade": 2}]')])
    assert rotas._itens_do_formulario(form) == [{"produto_id": 1, "quantidade": 2}]


def test_itens_do_formulario_le_campos_paralelos():
    form = MultiDict([
        ("produto_id", "1"),
        ("quantidade", "2"),
        ("valor_unitario", "10,00"),
        ("produto_id", ""),  # linha vazia deve ser ignorada
        ("quantidade", "1"),
        ("valor_unitario", "5,00"),
    ])
    assert rotas._itens_do_formulario(form) == [
        {"produto_id": "1", "quantidade": "2", "valor_unitario": "10,00"}
    ]


def test_itens_do_formulario_rejeita_json_invalido():
    with pytest.raises(ValueError):
        rotas._itens_do_formulario(MultiDict([("itens_json", "não é json")]))


# ---------------------------------------------------------------------------
# Resolução dos itens contra o catálogo da empresa
# ---------------------------------------------------------------------------
@pytest.fixture()
def catalogo(monkeypatch):
    def _produtos(_db, _cliente_id):
        return [
            {
                "produto_id": 1,
                "codigo_interno": "P1",
                "descricao": "Produto 1",
                "unidade_comercial": "UN",
                "preco_unitario_padrao": Decimal("10.00"),
            },
            {
                "produto_id": 2,
                "codigo_interno": "P2",
                "descricao": "Produto 2",
                "unidade_comercial": "CX",
                "preco_unitario_padrao": Decimal("7.50"),
            },
        ]

    monkeypatch.setattr(rotas, "_produtos_empresa", _produtos)
    return _produtos


def test_resolver_itens_calcula_totais_e_arredonda(catalogo):
    itens, total = rotas._resolver_itens(
        None,
        1,
        [{"produto_id": 1, "quantidade": "2", "valor_unitario": "12,555"}],
    )
    assert len(itens) == 1
    assert itens[0]["valor_unitario"] == Decimal("12.56")
    assert itens[0]["valor_total"] == Decimal("25.12")
    assert total == Decimal("25.12")


def test_resolver_itens_usa_preco_do_catalogo_no_portal(catalogo):
    itens, total = rotas._resolver_itens(
        None,
        1,
        [{"produto_id": 2, "quantidade": "2"}],
        preco_padrao=True,
    )
    assert itens[0]["valor_unitario"] == Decimal("7.50")
    assert total == Decimal("15.00")


def test_resolver_itens_rejeita_produto_de_outra_empresa(catalogo):
    with pytest.raises(ValueError):
        rotas._resolver_itens(None, 1, [{"produto_id": 99, "quantidade": "1"}])


@pytest.mark.parametrize("quantidade", ["0", "-1", "10000"])
def test_resolver_itens_rejeita_quantidade_invalida(catalogo, quantidade):
    with pytest.raises(ValueError):
        rotas._resolver_itens(
            None, 1, [{"produto_id": 1, "quantidade": quantidade}]
        )


def test_resolver_itens_rejeita_valor_negativo(catalogo):
    with pytest.raises(ValueError):
        rotas._resolver_itens(
            None,
            1,
            [{"produto_id": 1, "quantidade": "1", "valor_unitario": "-1"}],
        )


def test_resolver_itens_exige_ao_menos_um_item(catalogo):
    with pytest.raises(ValueError):
        rotas._resolver_itens(None, 1, [])


# ---------------------------------------------------------------------------
# Transições de status
# ---------------------------------------------------------------------------
def test_validar_novo_status_traduz_transicoes_do_formulario():
    assert rotas._validar_novo_status("RASCUNHO", "ENVIADO") is None
    assert rotas._validar_novo_status("SOLICITADO", "APROVADO") is None
    assert "Converter em pedido" in rotas._validar_novo_status("RASCUNHO", "CONVERTIDO")
    assert rotas._validar_novo_status("CONVERTIDO", "ENVIADO")
    assert rotas._validar_novo_status("RASCUNHO", "INEXISTENTE") == "Status inválido."


def test_pode_converter_bloqueia_estados_incompativeis():
    assert "já foi convertido" in rotas._pode_converter("CONVERTIDO")
    assert "cancelado" in rotas._pode_converter("CANCELADO")
    assert rotas._pode_converter("APROVADO") is None


# ---------------------------------------------------------------------------
# Notificações: portal não pode ver avisos internos da empresa
# ---------------------------------------------------------------------------
class _FakeResult:
    def mappings(self):
        return self

    def all(self):
        return []


class _FakeDB:
    def __init__(self):
        self.statements = []
        self.params = []

    def execute(self, statement, params=None):
        self.statements.append(str(statement))
        self.params.append(params or {})
        return _FakeResult()


def test_listar_notificacoes_do_portal_exclui_avisos_da_empresa():
    db = _FakeDB()
    orcamentos_service.listar_notificacoes(db, user_id=7, cliente_id=3, incluir_empresa=False)
    assert len(db.statements) == 1
    assert "user_id = :user_id" in db.statements[0]
    assert "cliente_id = :cliente_id" not in db.statements[0]
    assert db.params[0] == {"user_id": 7, "limite": 100}


def test_listar_notificacoes_da_empresa_inclui_avisos_gerais():
    db = _FakeDB()
    orcamentos_service.listar_notificacoes(db, user_id=7, cliente_id=3)
    assert "cliente_id = :cliente_id" in db.statements[0]
    assert db.params[0] == {"user_id": 7, "cliente_id": 3, "limite": 100}


# ---------------------------------------------------------------------------
# Rotas e templates
# ---------------------------------------------------------------------------
def test_blueprints_do_modulo_estao_registrados(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    esperados = {
        "orcamentos.listar",
        "orcamentos.novo",
        "orcamentos.detalhe",
        "orcamentos.editar",
        "orcamentos.alterar_status",
        "orcamentos.converter_em_pedido",
        "orcamentos.listar_portal_usuarios",
        "orcamentos.novo_portal_usuario",
        "orcamentos.alternar_portal_usuario",
        "orcamentos.listar_notificacoes",
        "orcamentos.ler_notificacao",
        "orcamentos.ler_todas_notificacoes",
        "portal.dashboard",
        "portal.novo_orcamento",
        "portal.detalhe",
        "portal.aprovar",
        "portal.recusar",
        "portal.notificacoes_portal",
        "portal.ler_notificacao_portal",
    }
    assert esperados <= endpoints


def test_templates_referenciam_apenas_endpoints_existentes(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    diretorios = [
        PROJECT_ROOT / "templates" / "portal",
        PROJECT_ROOT / "templates" / "admin" / "orcamentos",
    ]
    padrao = re.compile(r"url_for\(\s*['\"]([A-Za-z_.]+)['\"]")
    usados = set()
    for diretorio in diretorios:
        for arquivo in diretorio.rglob("*.html"):
            usados |= set(padrao.findall(arquivo.read_text(encoding="utf-8")))

    assert usados, "nenhum url_for encontrado nos templates do módulo"
    assert not (usados - endpoints), f"endpoints inexistentes: {sorted(usados - endpoints)}"


def test_migracao_cria_tabelas_e_vinculo_com_pedidos():
    sql = (PROJECT_ROOT / "database" / "migrations" / "019_create_orcamentos_portal.sql").read_text(
        encoding="utf-8"
    )
    for trecho in (
        "CREATE TABLE IF NOT EXISTS portal_usuarios",
        "CREATE TABLE IF NOT EXISTS orcamentos",
        "CREATE TABLE IF NOT EXISTS orcamentos_itens",
        "CREATE TABLE IF NOT EXISTS notificacoes",
        "ALTER TABLE pedidos_vendas ALTER COLUMN catalogo_id DROP NOT NULL",
        "ADD COLUMN IF NOT EXISTS orcamento_id",
    ):
        assert trecho in sql

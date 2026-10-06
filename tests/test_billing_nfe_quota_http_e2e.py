import os
import base64
import uuid
import threading
import traceback
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlsplit, urlunsplit
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from werkzeug.security import generate_password_hash
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from database.models import Base
from database.billing_shadow_models import BillingAccount, BillingPlan, BillingPlanVersion, BillingSubscription, BillingSubscriptionCompany, BillingSubscriptionOverride
from database.billing_usage_models import BillingUsageCounter
from database.models import CertificadoDigital, DestinatarioNFe, PlanoNFe, AssinaturaCliente
from database.models import ApiKey
from auth.api_key_auth import generate_api_key


def _seed_subscription(db, *, plan_code="START_V1", counted=49):
    account = BillingAccount(name=f"HTTP E2E Account {plan_code}")
    db.add(account)
    db.flush()
    plan = BillingPlan(code=plan_code, name=plan_code, active=True, display_order=1)
    db.add(plan)
    db.flush()
    version = BillingPlanVersion(plan_id=plan.plan_id, version_code=plan_code, price=60, currency="BRL", valid_from=datetime.utcnow(), status="ACTIVE", created_at=datetime.utcnow())
    db.add(version)
    db.flush()
    subscription = BillingSubscription(account_id=account.account_id, plan_version_id=version.plan_version_id, status="ACTIVE", contracted_price=60, currency="BRL", started_at=datetime.utcnow(), billing_cycle="MONTHLY", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(subscription)
    db.flush()
    db.add(BillingSubscriptionCompany(subscription_id=subscription.subscription_id, cliente_id=1, status="ACTIVE", linked_at=datetime.utcnow()))
    period_start = datetime.utcnow().date().replace(day=1)
    period_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    db.add(BillingUsageCounter(subscription_id=subscription.subscription_id, metric_key="NFE_ISSUED", period_start=period_start, period_end=period_end, quantity=counted, version=1))
    db.commit()
    return subscription


@pytest.fixture(scope="module")
def pg_engine():
    url = os.getenv("BILLING_SHADOW_DATABASE_URL")
    if not url or not any(host in url for host in ("localhost", "127.0.0.1")):
        pytest.skip("BILLING_SHADOW_DATABASE_URL não configurado para PostgreSQL local")
    parsed = urlsplit(url)
    database_name = f"billing_http_e2e_{os.getpid()}_{uuid.uuid4().hex[:8]}"
    assert database_name.startswith("billing_http_e2e_")
    admin_engine = create_engine(urlunsplit(parsed._replace(path="/postgres")), poolclass=NullPool)
    with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": database_name})
        connection.execute(text(f"CREATE DATABASE {database_name}"))
    engine = create_engine(urlunsplit(parsed._replace(path=f"/{database_name}")), poolclass=NullPool)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": database_name})
        connection.execute(text(f"DROP DATABASE IF EXISTS {database_name}"))
    admin_engine.dispose()

@pytest.fixture(autouse=True)
def e2e_environment(monkeypatch):
    monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", "true")
    monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_SHADOW", "false")
    monkeypatch.setenv("BILLING_NFE_QUOTA_ROLLOUT_CLIENT_IDS", "1")


@pytest.fixture
def http_context(app, pg_engine):
    from database.connection import SessionLocal

    original_bind = SessionLocal.kw.get("bind")
    SessionLocal.configure(bind=pg_engine)
    from database.models import NFeEmitidas
    NFeEmitidas.__table__.c.json_nfe.type = JSONB()
    original_csrf = app.config.get("WTF_CSRF_ENABLED")
    original_rate_limit = app.config.get("RATELIMIT_ENABLED")
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=True, RATELIMIT_ENABLED=False, SERVER_NAME="localhost")
    limiter = app.extensions.get("limiter")
    if limiter is not None:
        limiter.reset()
    session = sessionmaker(bind=pg_engine)()
    admin_engine = create_engine(pg_engine.url.set(database="postgres"), poolclass=NullPool)
    with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :database_name AND pid <> pg_backend_pid()"), {"database_name": pg_engine.url.database})
    admin_engine.dispose()
    with pg_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE billing_usage_reservations, billing_usage_events, billing_usage_counters, billing_subscription_companies, billing_subscriptions, billing_plan_versions, billing_plans, nfe_emitidas, certificados_digitais, destinatarios_nfe, assinaturas_cliente, planos_nfe, api_keys, api_usage_logs, user_clients, clientes, regimes_tributarios RESTART IDENTITY CASCADE"))
    _seed_http_data(session)
    session.close()
    try:
        yield app
    finally:
        SessionLocal.configure(bind=original_bind)
        app.config["WTF_CSRF_ENABLED"] = original_csrf
        app.config["RATELIMIT_ENABLED"] = original_rate_limit
        if limiter is not None:
            limiter.reset()


def _seed_http_data(db):
    db.execute(text("""
        CREATE OR REPLACE FUNCTION get_proximo_numero_nfe(p_cliente_id INTEGER, p_modelo VARCHAR, p_serie INTEGER)
        RETURNS INTEGER LANGUAGE SQL AS $$
            SELECT COALESCE(MAX(numero), 0) + 1 FROM nfe_emitidas
            WHERE cliente_id = p_cliente_id AND modelo = p_modelo AND serie = p_serie
        $$
    """))
    db.execute(text("INSERT INTO regimes_tributarios (regime_tributario_id, nome, crt) VALUES (1, 'Simples Nacional', 1) ON CONFLICT DO NOTHING"))
    db.execute(text("""
        INSERT INTO clientes (cliente_id, cnpj, inscricao_estadual, razao_social, nome_fantasia, produtor_rural, regime_tributario_id,
            cnae, logradouro, numero, bairro, codigo_municipio, nome_municipio, uf, cep, ambiente, ativo,
            data_cadastro, data_atualizacao)
        VALUES (1, '11222333000181', '110042490114', 'Cliente HTTP E2E', 'Cliente HTTP E2E', FALSE, 1, '4781100',
            'Rua E2E', '100', 'Centro', '3550308', 'Sao Paulo', 'SP', '01000000', 2, TRUE,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (cliente_id) DO UPDATE SET cnpj = EXCLUDED.cnpj, inscricao_estadual = EXCLUDED.inscricao_estadual,
            razao_social = EXCLUDED.razao_social, nome_fantasia = EXCLUDED.nome_fantasia,
            regime_tributario_id = EXCLUDED.regime_tributario_id, ativo = TRUE
    """))
    db.execute(text("""
        INSERT INTO users (username, email, password_hash, _is_active, created_at)
        VALUES ('http-e2e@emitemax.test', 'http-e2e@emitemax.test', :password, TRUE, CURRENT_TIMESTAMP)
        ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, _is_active = TRUE
    """), {"password": generate_password_hash("http-e2e-local-only")})
    user_id = db.execute(text("SELECT id FROM users WHERE username = 'http-e2e@emitemax.test'")).scalar()
    role_id = db.execute(text("SELECT id FROM roles WHERE name = 'Editor'")).scalar()
    if role_id is None:
        role_id = db.execute(text("INSERT INTO roles (name, description) VALUES ('Editor', 'E2E') RETURNING id")).scalar()
    db.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:user, :role) ON CONFLICT DO NOTHING"), {"user": user_id, "role": role_id})
    client_id = db.execute(text("SELECT cliente_id FROM clientes WHERE cnpj = '11222333000181' AND ativo = TRUE")).scalar()
    if client_id is None:
        raise AssertionError("E2E tenant was not created")
    db.execute(text("INSERT INTO user_clients (user_id, client_id) VALUES (:user, :client) ON CONFLICT DO NOTHING"), {"user": user_id, "client": client_id})

    legacy_plan = db.query(PlanoNFe).filter_by(nome="HTTP E2E Start").first()
    if not legacy_plan:
        legacy_plan = PlanoNFe(nome="HTTP E2E Start", descricao="fixture", tipo_plano="PACOTE", quantidade_nfes=50, valor_mensal=60, valor_por_nfe=0, ativo=True)
        db.add(legacy_plan)
        db.flush()
    legacy_subscription = db.query(AssinaturaCliente).filter_by(cliente_id=1).first()
    if not legacy_subscription:
        db.add(AssinaturaCliente(cliente_id=1, plano_id=legacy_plan.plano_id, data_inicio=datetime.utcnow().date(), status="ATIVA", nfes_consumidas=0))

    if not db.query(DestinatarioNFe).filter_by(cliente_id=1).first():
        db.add(DestinatarioNFe(cliente_id=1, tipo_pessoa="F", cpf_cnpj="52998224725", nome_razao_social="Destinatario E2E", logradouro="Rua B", numero="10", bairro="Centro", nome_municipio="Sao Paulo", codigo_municipio="3550308", uf="SP", codigo_uf="35", cep="01000000"))
    if not db.query(CertificadoDigital).filter_by(cliente_id=1).first():
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "E2E LOCAL ONLY")])
        certificate = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(private_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.utcnow() - timedelta(days=1)).not_valid_after(datetime.utcnow() + timedelta(days=30)).sign(private_key, hashes.SHA256())
        p12 = pkcs12.serialize_key_and_certificates(b"e2e", private_key, certificate, None, serialization.BestAvailableEncryption(b"e2e-local"))
        db.add(CertificadoDigital(cliente_id=1, fingerprint="http-e2e-fingerprint", conteudo_certificado=base64.b64encode(p12).decode(), senha_certificado="e2e-local", validade_inicio=datetime.utcnow() - timedelta(days=1), validade_fim=datetime.utcnow() + timedelta(days=1), ativo=True, nome_arquivo_original="e2e-simulado.pfx", tipo_certificado="A1"))
    db.commit()


def _csrf_token(client):
    response = client.get("/admin/nfe/emitir?cliente_id=1")
    assert response.status_code == 200
    token_response = client.get("/api/csrf-token")
    assert token_response.status_code == 200
    token = token_response.get_json().get("csrf_token")
    assert token
    return token


def _login(client):
    login_page = client.get("/auth/login")
    assert login_page.status_code == 200
    soup = BeautifulSoup(login_page.data, "html.parser")
    token = soup.select_one("input[name=csrf_token]")
    assert token and token.get("value")
    response = client.post("/auth/login", data={"csrf_token": token["value"], "username": "http-e2e@emitemax.test", "password": "http-e2e-local-only"}, follow_redirects=False)
    assert response.status_code in {302, 303}


def _form(token, number="1"):
    return {
        "csrf_token": token, "action": "emitir", "modelo": "55", "serie": "1", "numero_nfe": number,
        "tpNF": "1", "finNFe": "1", "natOp": "Venda", "formaPagamento": "0", "valorPagamento": "10",
        "modFrete": "9", "destinatario": "1",
        "items[0][json]": '{"descricao":"Produto E2E","codigo_produto":"E2E-1","unidade":"UN","quantidade":1,"valor_unitario":10,"valor_total":10,"ncm":"84713000","cfop":"5102","origem":"0","csosn_icms":"102","cst_pis":"01","cst_cofins":"01"}',
    }


def test_authenticated_web_post_50_50_blocks_before_sefaz(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, counted=50)
    subscription_id = subscription.subscription_id
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock()
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token), follow_redirects=True)
    assert response.status_code < 500
    assert b"limite de 50 NF-e" in response.data or b"PLAN_NFE_QUOTA_EXCEEDED" in response.data
    sefaz.assert_not_called()
    db = sessionmaker(bind=pg_engine)()
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid"), {"sid": subscription_id}).scalar() == 0
    db.close()


def test_authenticated_api_v2_post_50_50_returns_quota_error(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = db.query(BillingSubscription).join(BillingPlanVersion).filter(BillingSubscription.status == "ACTIVE", BillingPlanVersion.version_code == "START_V1").first()
    if subscription is None:
        subscription = _seed_subscription(db, counted=50)
    else:
        db.execute(text("UPDATE billing_usage_counters SET quantity = 50 WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription.subscription_id})
    key_value, key_hash, key_prefix = generate_api_key(1, "HTTP E2E")
    db.add(ApiKey(cliente_id=1, key_hash=key_hash, key_prefix=key_prefix, nome="HTTP E2E", ativa=True, rate_limit=1000, permissoes='{"allowed": ["nfe.write", "nfe.emit"]}'))
    db.commit()
    db.close()
    client = http_context.test_client()
    payload = {
        "destinatario": {"cpf_cnpj": "52998224725", "nome": "Destinatario E2E", "endereco": "Rua B", "numero": "10", "bairro": "Centro", "cidade": "Sao Paulo", "uf": "SP", "cep": "01000000"},
        "itens": [{"descricao": "Produto E2E", "quantidade": 1, "valor_unitario": 10, "valor_total": 10, "ncm": "84713000", "cfop": "5102", "unidade": "UN", "csosn_icms": "102", "cst_pis": "01", "cst_cofins": "01"}],
        "natureza_operacao": "Venda",
    }
    sefaz = Mock()
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/api/v2/nfe/emitir", json=payload, headers={"Authorization": f"Bearer {key_value}"})
    assert response.status_code == 409
    assert response.get_json()["code"] == "PLAN_NFE_QUOTA_EXCEEDED"
    sefaz.assert_not_called()


def test_authenticated_web_post_49_50_authorizes_and_confirms(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, counted=49)
    subscription_id = subscription.subscription_id
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock(return_value={
        "success": True,
        "status": "AUTORIZADA",
        "protocolo": "E2E-LOCAL",
        "chave_acesso": "35260811222333000181550010000000011123456789",
    })
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="2"), follow_redirects=True)
    assert response.status_code < 500
    sefaz.assert_called_once()
    db = sessionmaker(bind=pg_engine)()
    assert db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar() == 50
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid AND status = 'CONFIRMED'"), {"sid": subscription_id}).scalar() == 1
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_events WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED' AND status = 'COUNTED'"), {"sid": subscription_id}).scalar() == 1
    db.close()


def test_authenticated_web_post_49_50_releases_on_rejection(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, counted=49)
    subscription_id = subscription.subscription_id
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock(return_value={"success": False, "status": "REJEITADA", "message": "rejeicao E2E"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="3"), follow_redirects=True)
    assert response.status_code < 500
    sefaz.assert_called_once()
    db = sessionmaker(bind=pg_engine)()
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid AND status = 'RELEASED'"), {"sid": subscription_id}).scalar() == 1
    assert db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar() == 49
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_events WHERE subscription_id = :sid AND status = 'COUNTED'"), {"sid": subscription_id}).scalar() == 0
    db.close()


def test_authenticated_api_v2_post_49_50_authorizes_and_confirms(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, counted=49)
    subscription_id = subscription.subscription_id
    key_value, key_hash, key_prefix = generate_api_key(1, "HTTP E2E")
    db.add(ApiKey(cliente_id=1, key_hash=key_hash, key_prefix=key_prefix, nome="HTTP E2E", ativa=True, rate_limit=1000, permissoes='{"allowed": ["nfe.write", "nfe.emit"]}'))
    db.commit()
    db.close()
    client = http_context.test_client()
    payload = {
        "destinatario": {"cpf_cnpj": "52998224725", "nome": "Destinatario E2E", "endereco": "Rua B", "numero": "10", "bairro": "Centro", "cidade": "Sao Paulo", "uf": "SP", "cep": "01000000"},
        "itens": [{"descricao": "Produto E2E", "quantidade": 1, "valor_unitario": 10, "valor_total": 10, "ncm": "84713000", "cfop": "5102", "unidade": "UN", "csosn_icms": "102", "cst_pis": "01", "cst_cofins": "01"}],
        "natureza_operacao": "Venda",
    }
    sefaz = Mock(return_value={"success": True, "status": "AUTORIZADA", "protocolo": "E2E-API", "chave_acesso": "35260811222333000181550010000000011123456789"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/api/v2/nfe/emitir", json=payload, headers={"Authorization": f"Bearer {key_value}"})
    assert response.status_code == 201
    assert response.get_json()["success"] is True
    sefaz.assert_called_once()
    db = sessionmaker(bind=pg_engine)()
    assert db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar() == 50
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid AND status = 'CONFIRMED'"), {"sid": subscription_id}).scalar() == 1
    db.close()


def test_authenticated_web_confirm_failure_keeps_fiscal_success(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    _seed_subscription(db, counted=49)
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock(return_value={"success": True, "status": "AUTORIZADA", "protocolo": "E2E-CONFIRM", "chave_acesso": "35260811222333000181550010000000011123456780"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz), patch("services.billing_usage_shadow.BillingQuotaReservationService.confirm", side_effect=RuntimeError("billing unavailable")):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="4"), follow_redirects=True)
    assert response.status_code < 500
    assert b"NFe emitida com sucesso" in response.data
    sefaz.assert_called_once()


def test_authenticated_web_flag_off_preserves_baseline(http_context, pg_engine, monkeypatch):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, counted=50)
    subscription_id = subscription.subscription_id
    db.close()
    monkeypatch.setenv("FEATURE_BILLING_NFE_QUOTA_ENABLED", "false")
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock(return_value={"success": False, "status": "REJEITADA", "message": "baseline mock"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="5"), follow_redirects=True)
    assert response.status_code < 500
    assert b"PLAN_NFE_QUOTA_EXCEEDED" not in response.data
    sefaz.assert_called_once()
    db = sessionmaker(bind=pg_engine)()
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid"), {"sid": subscription_id}).scalar() == 0
    db.close()


def test_authenticated_web_legacy_over_50_is_not_start_blocked(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, plan_code="LEGACY_START_V1", counted=51)
    subscription_id = subscription.subscription_id
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock(return_value={"success": False, "status": "REJEITADA", "message": "legacy mock"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="6"), follow_redirects=True)
    assert response.status_code < 500
    assert b"PLAN_NFE_QUOTA_EXCEEDED" not in response.data
    sefaz.assert_called_once()
    db = sessionmaker(bind=pg_engine)()
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid"), {"sid": subscription_id}).scalar() == 0
    db.close()


def test_authenticated_web_premium_over_50_uses_fair_use(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, plan_code="PREMIUM_V1", counted=51)
    subscription_id = subscription.subscription_id
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock(return_value={"success": False, "status": "REJEITADA", "message": "premium mock"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="7"), follow_redirects=True)
    assert response.status_code < 500
    assert b"PLAN_NFE_QUOTA_EXCEEDED" not in response.data
    sefaz.assert_called_once()
    db = sessionmaker(bind=pg_engine)()
    assert db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar() == 51
    db.close()


def test_authenticated_web_override_75_allows_74_and_blocks_75(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, counted=74)
    subscription_id = subscription.subscription_id
    db.add(BillingSubscriptionOverride(subscription_id=subscription_id, key="NFE_MONTHLY", value="75", reason="HTTP E2E override"))
    db.commit()
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    allowed_sefaz = Mock(return_value={"success": False, "status": "REJEITADA", "message": "override mock"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", allowed_sefaz):
        allowed = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="8"), follow_redirects=True)
    assert allowed.status_code < 500
    allowed_sefaz.assert_called_once()
    db = sessionmaker(bind=pg_engine)()
    db.execute(text("UPDATE billing_usage_counters SET quantity = 75 WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id})
    db.commit()
    db.close()
    blocked_sefaz = Mock()
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", blocked_sefaz):
        blocked = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="9"), follow_redirects=True)
    assert blocked.status_code < 500
    assert b"limite de 50 NF-e" in blocked.data or b"PLAN_NFE_QUOTA_EXCEEDED" in blocked.data
    blocked_sefaz.assert_not_called()


def test_authenticated_web_unknown_result_keeps_pending_reservation(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, counted=49)
    subscription_id = subscription.subscription_id
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock(return_value={"success": True, "status": "PROCESSANDO", "message": "resultado pendente"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="10"), follow_redirects=True)
    assert response.status_code < 500
    sefaz.assert_called_once()
    db = sessionmaker(bind=pg_engine)()
    assert db.execute(text("SELECT COUNT(*) FROM billing_usage_reservations WHERE subscription_id = :sid AND status = 'PENDING_RECONCILIATION'"), {"sid": subscription_id}).scalar() == 1
    assert db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar() == 49
    db.close()


def test_authenticated_web_idempotent_reconciliation_duplicated(http_context, pg_engine):
    db = sessionmaker(bind=pg_engine)()
    subscription = _seed_subscription(db, counted=49)
    subscription_id = subscription.subscription_id
    db.close()
    client = http_context.test_client()
    _login(client)
    token = _csrf_token(client)
    sefaz = Mock(return_value={"success": True, "status": "PROCESSANDO", "message": "resultado pendente"})
    with patch("services.nfe_service.NFeService._processar_envio_sefaz", sefaz):
        response = client.post("/admin/nfe/emitir?cliente_id=1", data=_form(token, number="11"), follow_redirects=True)
    assert response.status_code < 500
    db = sessionmaker(bind=pg_engine)()
    reservation_key = db.execute(text("SELECT reservation_key FROM billing_usage_reservations WHERE subscription_id = :sid AND status = 'PENDING_RECONCILIATION'"), {"sid": subscription_id}).scalar()
    assert reservation_key is not None
    counter_before = db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar()
    assert counter_before == 49
    from services.billing_nfe_quota import BillingNFeQuotaAdapter
    adapter = BillingNFeQuotaAdapter(db)
    first_confirm = adapter.after_authorized(reservation_key=reservation_key, source_id=reservation_key)
    assert first_confirm.get('status') == 'CONFIRMED'
    db.commit()
    counter_after_first = db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar()
    assert counter_after_first == 50
    second_confirm = adapter.after_authorized(reservation_key=reservation_key, source_id=reservation_key)
    assert second_confirm.get('code') == 'CONFIRM_DUPLICATE'
    db.commit()
    counter_after_second = db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar()
    assert counter_after_second == 50
    event_count = db.execute(text("SELECT COUNT(*) FROM billing_usage_events WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED' AND event_key = :key"), {"sid": subscription_id, "key": reservation_key}).scalar()
    assert event_count == 1
    db.close()


def test_authenticated_concurrent_web_api_quota_conflict(http_context, pg_engine):
    """
    ETAPA 2: Concurrency HTTP WEB + API quota conflict.
    Real auth + real session + real CSRF + real quota + real Postgres.
    External provider IA is mocked only; SEFAZ is mocked only.
    """
    prepared_web_client = http_context.test_client()
    _login(prepared_web_client)
    with prepared_web_client.session_transaction() as session:
        session["current_client_id"] = 1
        prepared_web_session = dict(session)

    def _run_once(iteration):
        db = sessionmaker(bind=pg_engine)()
        subscription = db.query(BillingSubscription).join(BillingPlanVersion).filter(BillingSubscription.status == "ACTIVE", BillingPlanVersion.version_code == "START_V1").first()
        if subscription is None:
            subscription = _seed_subscription(db, counted=49)
        else:
            db.execute(text("UPDATE billing_usage_counters SET quantity = 49 WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription.subscription_id})
        subscription_id = subscription.subscription_id
        key_value, key_hash, key_prefix = generate_api_key(1, f"HTTP E2E Concurrent {iteration}")
        db.add(ApiKey(cliente_id=1, key_hash=key_hash, key_prefix=key_prefix, nome=f"HTTP E2E Concurrent {iteration}", ativa=True, rate_limit=1000, permissoes='{"allowed": ["nfe.write", "nfe.emit"]}'))
        db.commit()
        db.close()

        barrier = threading.Barrier(2)
        results = {}
        worker_errors = {}
        sefaz_calls = []

        db = sessionmaker(bind=pg_engine)()
        event_count_before = db.execute(text("SELECT COUNT(*) FROM billing_usage_events WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar()
        db.close()

        def fake_ai(*args, **kwargs):
            class FakeResponse:
                status_code = 200
                def json(self):
                    return {"valido": True, "score_confianca": 99, "avisos": [], "erros": []}
            return FakeResponse()

        def mock_sefaz(*args, **kwargs):
            sefaz_calls.append(1)
            return {
                "success": True,
                "status": "AUTORIZADA",
                "protocolo": f"proto_{len(sefaz_calls)}",
                "chave_acesso": "35260811222333000181550010000000011123456789",
            }

        web_thread_client = http_context.test_client()
        with web_thread_client.session_transaction() as session:
            session.update(prepared_web_session)
        assert web_thread_client.get("/api/csrf-token").status_code == 200
        web_token = _csrf_token(web_thread_client)
        api_client = http_context.test_client()

        def web_worker():
            try:
                barrier.wait(timeout=10)
                with patch("requests.post", side_effect=fake_ai):
                    response = web_thread_client.post("/admin/nfe/emitir?cliente_id=1", data=_form(web_token, number=str(200 + iteration)), follow_redirects=True)
                results["web"] = {
                    "status": response.status_code,
                    "body": response.get_data(as_text=True).lower(),
                }
            except BaseException as exc:
                worker_errors["web"] = (exc, traceback.format_exc())

        def api_worker():
            try:
                barrier.wait(timeout=10)
                payload = {
                    "destinatario": {"cpf_cnpj": "52998224725", "nome": "Destinatario E2E", "endereco": "Rua B", "numero": "10", "bairro": "Centro", "cidade": "Sao Paulo", "uf": "SP", "cep": "01000000"},
                    "itens": [{"descricao": "Produto E2E", "quantidade": 1, "valor_unitario": 10, "valor_total": 10, "ncm": "84713000", "cfop": "5102", "unidade": "UN", "csosn_icms": "102", "cst_pis": "01", "cst_cofins": "01"}],
                    "natureza_operacao": "Venda",
                }
                response = api_client.post("/api/v2/nfe/emitir", json=payload, headers={"Authorization": f"Bearer {key_value}"})
                results["api"] = {"status": response.status_code, "json": response.get_json() if response.is_json else None}
            except BaseException as exc:
                worker_errors["api"] = (exc, traceback.format_exc())

        with patch("services.nfe_service.NFeService._processar_envio_sefaz", side_effect=mock_sefaz):
            with patch("requests.post", side_effect=fake_ai):
                web_thread = threading.Thread(target=web_worker, daemon=True)
                api_thread = threading.Thread(target=api_worker, daemon=True)
                web_thread.start()
                api_thread.start()
                web_thread.join(timeout=30)
                api_thread.join(timeout=30)

        if worker_errors:
            details = "\n\n".join(f"{name}: {error[0]!r}\n{error[1]}" for name, error in worker_errors.items())
            pytest.fail(f"Worker error on iteration {iteration}:\n{details}")
        assert not web_thread.is_alive(), f"Web thread hung on iteration {iteration}"
        assert not api_thread.is_alive(), f"API thread hung on iteration {iteration}"
        assert "web" in results and "api" in results, f"Missing results on iteration {iteration}: {results}"

        web_status = results["web"]["status"]
        api_status = results["api"]["status"]
        web_text = results["web"]["body"]
        web_blocked = web_status in (200, 302, 400) and (
            "limite de 50 nf-e" in web_text
            or "plan_nfe_quota_exceeded" in web_text
            or "atingiu o limite de 50" in web_text
            or "não pôde prosseguir por uma regra comercial" in web_text
        )
        web_success = web_status in (200, 302) and not web_blocked and (
            "nfe emitida" in web_text
            or "nf-e emitida" in web_text
            or "emitida e autorizada" in web_text
            or "autorizada com sucesso" in web_text
        )
        api_json = results["api"]["json"] or {}
        api_success = api_status == 201 and api_json.get("success") is True
        api_blocked = api_status == 409 and api_json.get("code") == "PLAN_NFE_QUOTA_EXCEEDED"

        one_success = web_success or api_success
        one_blocked = web_blocked or api_blocked
        assert one_success and one_blocked, f"Expected 1 success + 1 blocked on iteration {iteration}; web={results['web']}, api={results['api']}, sefaz_calls={len(sefaz_calls)}"
        assert len(sefaz_calls) == 1, f"Expected exactly 1 SEFAZ call on iteration {iteration}, got {len(sefaz_calls)}"

        db = sessionmaker(bind=pg_engine)()
        counter = db.execute(text("SELECT quantity FROM billing_usage_counters WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar()
        event_count_after = db.execute(text("SELECT COUNT(*) FROM billing_usage_events WHERE subscription_id = :sid AND metric_key = 'NFE_ISSUED'"), {"sid": subscription_id}).scalar()
        assert counter == 50, f"Counter should remain 50 on iteration {iteration}; got {counter}"
        assert event_count_after - event_count_before >= 1, f"Expected at least one new event in iteration {iteration}; before={event_count_before}, after={event_count_after}"
        assert event_count_after - event_count_before <= 1, f"Expected exactly one new event in iteration {iteration}; before={event_count_before}, after={event_count_after}"
        db.close()

    iterations = int(os.getenv("BILLING_CONCURRENCY_ITERATIONS", "20"))
    for iteration in range(iterations):
        _run_once(iteration)

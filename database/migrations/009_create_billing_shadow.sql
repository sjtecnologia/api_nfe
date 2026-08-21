-- Fase 4.6C: arquitetura comercial shadow-only.
-- NÃO executar automaticamente. NÃO altera tabelas legadas.

CREATE TABLE IF NOT EXISTS billing_accounts (
    account_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS billing_plans (
    plan_id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS billing_plan_versions (
    plan_version_id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES billing_plans(plan_id),
    version_code VARCHAR(50) NOT NULL UNIQUE,
    price NUMERIC(10,2),
    currency VARCHAR(3) NOT NULL DEFAULT 'BRL',
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS billing_features (
    feature_id SERIAL PRIMARY KEY,
    key VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ROADMAP',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_billing_feature_status CHECK (status IN ('AVAILABLE','PARTIAL','ROADMAP'))
);

CREATE TABLE IF NOT EXISTS billing_plan_features (
    plan_feature_id SERIAL PRIMARY KEY,
    plan_version_id INTEGER NOT NULL REFERENCES billing_plan_versions(plan_version_id),
    feature_id INTEGER NOT NULL REFERENCES billing_features(feature_id),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    access_level VARCHAR(30) NOT NULL DEFAULT 'STANDARD',
    limit_type VARCHAR(40) NOT NULL DEFAULT 'DISABLED',
    limit_value INTEGER,
    metadata_json TEXT,
    CONSTRAINT uq_billing_plan_feature UNIQUE (plan_version_id, feature_id),
    CONSTRAINT ck_billing_limit_type CHECK (limit_type IN ('DISABLED','ENABLED','LIMITED','UNMETERED_WITH_FAIR_USE','CONTRACTUAL'))
);

CREATE TABLE IF NOT EXISTS billing_subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES billing_accounts(account_id),
    plan_version_id INTEGER NOT NULL REFERENCES billing_plan_versions(plan_version_id),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    contracted_price NUMERIC(10,2),
    currency VARCHAR(3) NOT NULL DEFAULT 'BRL',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ends_at TIMESTAMP,
    billing_cycle VARCHAR(30) NOT NULL DEFAULT 'MONTHLY',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS billing_subscription_companies (
    subscription_company_id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES billing_subscriptions(subscription_id),
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    linked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    unlinked_at TIMESTAMP,
    CONSTRAINT uq_billing_subscription_company UNIQUE (subscription_id, cliente_id)
);

CREATE TABLE IF NOT EXISTS billing_subscription_overrides (
    override_id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES billing_subscriptions(subscription_id),
    key VARCHAR(80) NOT NULL,
    value TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_by_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    CONSTRAINT uq_billing_subscription_override UNIQUE (subscription_id, key)
);

CREATE INDEX IF NOT EXISTS idx_billing_plan_versions_plan ON billing_plan_versions(plan_id);
CREATE INDEX IF NOT EXISTS idx_billing_plan_features_version ON billing_plan_features(plan_version_id);
CREATE INDEX IF NOT EXISTS idx_billing_subscription_account ON billing_subscriptions(account_id);
CREATE INDEX IF NOT EXISTS idx_billing_subscription_company_cliente ON billing_subscription_companies(cliente_id);
CREATE INDEX IF NOT EXISTS idx_billing_override_subscription ON billing_subscription_overrides(subscription_id);

-- Seeds são shadow-only e não vinculam clientes nem assinaturas existentes.
INSERT INTO billing_plans (code, name, display_order) VALUES
    ('START', 'Start', 1),
    ('ESSENCIAL', 'Essencial', 2),
    ('PROFISSIONAL', 'Profissional', 3),
    ('PREMIUM', 'Premium', 4),
    ('ENTERPRISE', 'Enterprise / Parceiros', 5)
ON CONFLICT (code) DO NOTHING;

INSERT INTO billing_plan_versions (plan_id, version_code, price, currency, status)
SELECT plan_id, 'START_V1', 60.00, 'BRL', 'ACTIVE' FROM billing_plans WHERE code = 'START'
ON CONFLICT (version_code) DO NOTHING;
INSERT INTO billing_plan_versions (plan_id, version_code, price, currency, status)
SELECT plan_id, 'ESSENCIAL_V1', 99.00, 'BRL', 'ACTIVE' FROM billing_plans WHERE code = 'ESSENCIAL'
ON CONFLICT (version_code) DO NOTHING;
INSERT INTO billing_plan_versions (plan_id, version_code, price, currency, status)
SELECT plan_id, 'PROFISSIONAL_V1', 169.00, 'BRL', 'ACTIVE' FROM billing_plans WHERE code = 'PROFISSIONAL'
ON CONFLICT (version_code) DO NOTHING;
INSERT INTO billing_plan_versions (plan_id, version_code, price, currency, status)
SELECT plan_id, 'PREMIUM_V1', 299.00, 'BRL', 'ACTIVE' FROM billing_plans WHERE code = 'PREMIUM'
ON CONFLICT (version_code) DO NOTHING;
INSERT INTO billing_plan_versions (plan_id, version_code, price, currency, status)
SELECT plan_id, 'ENTERPRISE_V1', NULL, 'BRL', 'ACTIVE' FROM billing_plans WHERE code = 'ENTERPRISE'
ON CONFLICT (version_code) DO NOTHING;

-- Não cria UsageEvent/UsageCounter/BillingEvent nesta fase.

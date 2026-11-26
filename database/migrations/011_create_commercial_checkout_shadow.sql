-- Fase 4.6G.2: aquisição comercial shadow-only.
-- Não cria Cliente/User/Subscription definitivo e não toca em tabelas fiscais.
CREATE TABLE IF NOT EXISTS pending_signups (
    pending_signup_id SERIAL PRIMARY KEY,
    public_token VARCHAR(100) NOT NULL UNIQUE,
    plan_version_id INTEGER NOT NULL REFERENCES billing_plan_versions(plan_version_id),
    email_normalized VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    contract_version VARCHAR(50) NOT NULL,
    contract_accepted_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS billing_checkout_attempts (
    checkout_attempt_id SERIAL PRIMARY KEY,
    pending_signup_id INTEGER NOT NULL REFERENCES pending_signups(pending_signup_id),
    plan_version_id INTEGER NOT NULL REFERENCES billing_plan_versions(plan_version_id),
    provider VARCHAR(30) NOT NULL DEFAULT 'shadow',
    provider_reference VARCHAR(255),
    provider_plan_id VARCHAR(255),
    external_reference VARCHAR(255) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    amount NUMERIC(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'BRL',
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    provider_metadata TEXT
);

CREATE TABLE IF NOT EXISTS billing_payment_events (
    payment_event_id SERIAL PRIMARY KEY,
    provider VARCHAR(30) NOT NULL,
    provider_event_id VARCHAR(255) NOT NULL,
    checkout_attempt_id INTEGER NOT NULL REFERENCES billing_checkout_attempts(checkout_attempt_id),
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    payload_hash VARCHAR(64) NOT NULL,
    metadata_json TEXT,
    CONSTRAINT uq_payment_provider_event UNIQUE (provider, provider_event_id)
);

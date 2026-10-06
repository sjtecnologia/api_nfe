-- Fase 4.6G.MP1: mapping explícito de planos de pagamento.
-- A migration é aditiva e não altera planos/assinaturas existentes.
CREATE TABLE IF NOT EXISTS payment_provider_plan_mappings (
    mapping_id SERIAL PRIMARY KEY,
    billing_plan_version_id INTEGER NOT NULL REFERENCES billing_plan_versions(plan_version_id),
    provider VARCHAR(30) NOT NULL,
    provider_plan_id VARCHAR(255) NOT NULL,
    environment VARCHAR(20) NOT NULL CHECK (environment IN ('TEST','PRODUCTION')),
    currency VARCHAR(3) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_provider_plan_mapping_external UNIQUE (provider, environment, provider_plan_id),
    CONSTRAINT uq_provider_plan_mapping_version UNIQUE (billing_plan_version_id, provider, environment)
);

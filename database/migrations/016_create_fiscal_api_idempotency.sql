-- Respostas de emissões fiscais protegidas contra retries duplicados.
CREATE TABLE IF NOT EXISTS fiscal_api_idempotency (
    idempotency_id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    endpoint VARCHAR(120) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    status_code INTEGER,
    response_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fiscal_api_idempotency UNIQUE (cliente_id, endpoint, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_fiscal_api_idempotency_lookup
    ON fiscal_api_idempotency (cliente_id, endpoint, idempotency_key);

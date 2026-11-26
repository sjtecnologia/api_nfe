-- Fase 4.6E: uso shadow-only. Não executar em produção automaticamente.
CREATE TABLE IF NOT EXISTS billing_usage_events (
    usage_event_id BIGSERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES billing_accounts(account_id),
    subscription_id INTEGER REFERENCES billing_subscriptions(subscription_id),
    cliente_id INTEGER REFERENCES clientes(cliente_id),
    metric_key VARCHAR(50) NOT NULL,
    event_key VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    source_id VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'COUNTED',
    metadata_json JSONB,
    occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_billing_usage_event_key UNIQUE (metric_key, event_key),
    CONSTRAINT ck_billing_usage_event_metric CHECK (metric_key IN ('NFE_ISSUED','NFCE_ISSUED','NFSE_ISSUED','AI_REQUEST','API_REQUEST')),
    CONSTRAINT ck_billing_usage_event_status CHECK (status IN ('PENDING','COUNTED','IGNORED','REVERSED')),
    CONSTRAINT ck_billing_usage_event_source CHECK (source_type IN ('NFE','NFCE','NFSE','AI','API'))
);

CREATE TABLE IF NOT EXISTS billing_usage_counters (
    usage_counter_id BIGSERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES billing_subscriptions(subscription_id),
    metric_key VARCHAR(50) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_billing_usage_counter_period UNIQUE (subscription_id, metric_key, period_start, period_end),
    CONSTRAINT ck_billing_usage_counter_metric CHECK (metric_key IN ('NFE_ISSUED','NFCE_ISSUED','NFSE_ISSUED','AI_REQUEST','API_REQUEST'))
);

CREATE INDEX IF NOT EXISTS idx_billing_usage_events_subscription ON billing_usage_events(subscription_id);
CREATE INDEX IF NOT EXISTS idx_billing_usage_events_cliente_period ON billing_usage_events(cliente_id, metric_key, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_billing_usage_counters_metric_period ON billing_usage_counters(metric_key, period_start, period_end);

-- Não há hooks nas tabelas fiscais e não há backfill automático.

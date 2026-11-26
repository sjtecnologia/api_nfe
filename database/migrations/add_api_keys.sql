-- ============================================================
-- Migração: API Keys e Webhooks
-- Data: 18/12/2024
-- Descrição: Adiciona suporte para autenticação via API Key,
--            rate limiting e webhooks
-- ============================================================

-- Tabela de API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    api_key_id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL, -- Primeiros caracteres para identificação
    nome VARCHAR(100) NOT NULL, -- Nome descritivo da chave
    ativa BOOLEAN DEFAULT TRUE,
    criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_utilizacao TIMESTAMP,
    expira_em TIMESTAMP, -- NULL = nunca expira
    rate_limit INTEGER DEFAULT 1000, -- Requisições por hora
    ip_whitelist TEXT, -- IPs permitidos (JSON array)
    permissoes TEXT, -- Permissões específicas (JSON)
    
    CONSTRAINT api_keys_cliente_nome_unique UNIQUE (cliente_id, nome)
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_cliente ON api_keys(cliente_id);
CREATE INDEX idx_api_keys_ativa ON api_keys(ativa);

COMMENT ON TABLE api_keys IS 'API Keys para autenticação de integrações externas';
COMMENT ON COLUMN api_keys.key_hash IS 'Hash SHA-256 da chave completa';
COMMENT ON COLUMN api_keys.key_prefix IS 'Primeiros 8 caracteres da chave para identificação';
COMMENT ON COLUMN api_keys.rate_limit IS 'Número máximo de requisições por hora';
COMMENT ON COLUMN api_keys.ip_whitelist IS 'Array JSON de IPs permitidos';
COMMENT ON COLUMN api_keys.permissoes IS 'JSON com permissões específicas (read, write, nfe_emit, etc)';

-- Tabela de logs de uso de API
CREATE TABLE IF NOT EXISTS api_usage_logs (
    log_id BIGSERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(api_key_id) ON DELETE SET NULL,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    metodo VARCHAR(10) NOT NULL,
    status_code INTEGER,
    ip_origem VARCHAR(45),
    user_agent TEXT,
    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    erro TEXT
);

CREATE INDEX idx_api_logs_api_key ON api_usage_logs(api_key_id);
CREATE INDEX idx_api_logs_cliente ON api_usage_logs(cliente_id);
CREATE INDEX idx_api_logs_timestamp ON api_usage_logs(request_time DESC);
CREATE INDEX idx_api_logs_endpoint ON api_usage_logs(endpoint);

COMMENT ON TABLE api_usage_logs IS 'Logs de uso da API para auditoria e rate limiting';

-- Tabela de webhooks
CREATE TABLE IF NOT EXISTS webhooks (
    webhook_id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    eventos TEXT NOT NULL, -- JSON array: ["nfe.autorizada", "nfe.cancelada", etc]
    ativo BOOLEAN DEFAULT TRUE,
    secret VARCHAR(255), -- Secret para validação HMAC
    retry_count INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 30,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_tentativa TIMESTAMP,
    ultimo_sucesso TIMESTAMP,
    total_sucessos INTEGER DEFAULT 0,
    total_falhas INTEGER DEFAULT 0,
    
    CONSTRAINT webhooks_cliente_url_unique UNIQUE (cliente_id, url)
);

CREATE INDEX idx_webhooks_cliente ON webhooks(cliente_id);
CREATE INDEX idx_webhooks_ativo ON webhooks(ativo);

COMMENT ON TABLE webhooks IS 'Webhooks para notificações de eventos em tempo real';
COMMENT ON COLUMN webhooks.eventos IS 'Array JSON de eventos que acionam o webhook';
COMMENT ON COLUMN webhooks.secret IS 'Secret para calcular HMAC-SHA256 do payload';

-- Tabela de fila de webhooks
CREATE TABLE IF NOT EXISTS webhook_queue (
    queue_id BIGSERIAL PRIMARY KEY,
    webhook_id INTEGER NOT NULL REFERENCES webhooks(webhook_id) ON DELETE CASCADE,
    evento VARCHAR(50) NOT NULL,
    payload TEXT NOT NULL, -- JSON
    tentativas INTEGER DEFAULT 0,
    max_tentativas INTEGER DEFAULT 3,
    proximo_retry TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, sent, failed
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP,
    erro TEXT
);

CREATE INDEX idx_webhook_queue_webhook ON webhook_queue(webhook_id);
CREATE INDEX idx_webhook_queue_status ON webhook_queue(status);
CREATE INDEX idx_webhook_queue_proximo_retry ON webhook_queue(proximo_retry);

COMMENT ON TABLE webhook_queue IS 'Fila de webhooks pendentes de envio';

-- Função para limpar logs antigos (manter apenas últimos 90 dias)
CREATE OR REPLACE FUNCTION limpar_api_logs_antigos()
RETURNS void AS $$
BEGIN
    DELETE FROM api_usage_logs 
    WHERE request_time < CURRENT_TIMESTAMP - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION limpar_api_logs_antigos() IS 'Remove logs de API com mais de 90 dias';

-- Função para verificar rate limit
CREATE OR REPLACE FUNCTION check_rate_limit(p_api_key_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_rate_limit INTEGER;
    v_request_count INTEGER;
BEGIN
    -- Buscar o rate limit configurado
    SELECT rate_limit INTO v_rate_limit
    FROM api_keys
    WHERE api_key_id = p_api_key_id;
    
    IF v_rate_limit IS NULL OR v_rate_limit = 0 THEN
        RETURN TRUE; -- Sem limite
    END IF;
    
    -- Contar requisições na última hora
    SELECT COUNT(*) INTO v_request_count
    FROM api_usage_logs
    WHERE api_key_id = p_api_key_id
      AND request_time > CURRENT_TIMESTAMP - INTERVAL '1 hour';
    
    RETURN v_request_count < v_rate_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_rate_limit(INTEGER) IS 'Verifica se a API Key ainda está dentro do limite de requisições';

-- Atualizar timestamp de última utilização da API Key
CREATE OR REPLACE FUNCTION update_api_key_last_used()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE api_keys
    SET ultima_utilizacao = NEW.request_time
    WHERE api_key_id = NEW.api_key_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_api_key_last_used
AFTER INSERT ON api_usage_logs
FOR EACH ROW
WHEN (NEW.api_key_id IS NOT NULL)
EXECUTE FUNCTION update_api_key_last_used();

COMMENT ON TRIGGER trigger_update_api_key_last_used ON api_usage_logs IS 'Atualiza timestamp de última utilização da API Key';

-- Inserir dados de exemplo (comentado - descomente se necessário)
-- INSERT INTO api_keys (cliente_id, key_hash, key_prefix, nome, rate_limit) VALUES
-- (1, 'hash_exemplo_1', 'emx_test', 'Chave de Teste', 1000);

COMMIT;

-- Verificar estrutura criada
SELECT 'API Keys criada: ' || COUNT(*) FROM information_schema.tables WHERE table_name = 'api_keys';
SELECT 'Webhooks criada: ' || COUNT(*) FROM information_schema.tables WHERE table_name = 'webhooks';
SELECT 'API Usage Logs criada: ' || COUNT(*) FROM information_schema.tables WHERE table_name = 'api_usage_logs';
SELECT 'Webhook Queue criada: ' || COUNT(*) FROM information_schema.tables WHERE table_name = 'webhook_queue';

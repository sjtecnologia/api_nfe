-- Migration: Infraestrutura inicial da IA do EmiteMax
-- Data: 2026-08-09

CREATE TABLE IF NOT EXISTS ai_prompts (
    prompt_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    funcionalidade VARCHAR(100) NOT NULL,
    versao VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    modelo VARCHAR(100),
    temperatura NUMERIC(4, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
    prompt TEXT NOT NULL,
    parametros JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_conversations (
    conversation_id BIGSERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    funcionalidade VARCHAR(100) NOT NULL,
    titulo VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'ATIVA',
    contexto JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_messages (
    message_id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES ai_conversations(conversation_id) ON DELETE CASCADE,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    funcionalidade VARCHAR(100) NOT NULL,
    model VARCHAR(100),
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_estimated NUMERIC(12, 6) NOT NULL DEFAULT 0,
    tool_calls JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_usage_logs (
    usage_id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT REFERENCES ai_conversations(conversation_id) ON DELETE SET NULL,
    prompt_id INTEGER REFERENCES ai_prompts(prompt_id) ON DELETE SET NULL,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    funcionalidade VARCHAR(100) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    request_type VARCHAR(50),
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_estimated NUMERIC(12, 6) NOT NULL DEFAULT 0,
    response_time_ms INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_user_limits (
    limit_id BIGSERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    plano_id INTEGER REFERENCES planos_nfe(plano_id) ON DELETE SET NULL,
    funcionalidade VARCHAR(100) NOT NULL,
    limite_mensal INTEGER NOT NULL DEFAULT 100,
    limite_diario INTEGER,
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_feedback (
    feedback_id BIGSERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    conversation_id BIGINT REFERENCES ai_conversations(conversation_id) ON DELETE SET NULL,
    message_id BIGINT REFERENCES ai_messages(message_id) ON DELETE SET NULL,
    funcionalidade VARCHAR(100) NOT NULL,
    feedback VARCHAR(20) NOT NULL,
    comentario TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_generated_content (
    generated_content_id BIGSERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    funcionalidade VARCHAR(100) NOT NULL,
    canal VARCHAR(50),
    input_data JSONB,
    output_content TEXT NOT NULL,
    model VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_conversations_cliente_id ON ai_conversations(cliente_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation_id ON ai_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_cliente_id ON ai_messages(cliente_id);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_cliente_id ON ai_usage_logs(cliente_id);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_created_at ON ai_usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_funcionalidade ON ai_usage_logs(funcionalidade);
CREATE INDEX IF NOT EXISTS idx_ai_user_limits_funcionalidade ON ai_user_limits(funcionalidade);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_cliente_id ON ai_feedback(cliente_id);

COMMENT ON TABLE ai_prompts IS 'Prompts centralizados da IA do EmiteMax';
COMMENT ON TABLE ai_conversations IS 'Conversas do assistente IA por cliente';
COMMENT ON TABLE ai_messages IS 'Mensagens da conversa IA';
COMMENT ON TABLE ai_usage_logs IS 'Log de uso, tokens e custo estimado da IA';
COMMENT ON TABLE ai_user_limits IS 'Limites de uso configuraveis por plano, cliente ou usuario';
COMMENT ON TABLE ai_feedback IS 'Feedback util/nao util da IA';
COMMENT ON TABLE ai_generated_content IS 'Conteudos gerados pela IA para marketing e documentos';
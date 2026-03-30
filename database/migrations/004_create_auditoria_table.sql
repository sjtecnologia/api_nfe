-- Migration 004: Criar tabela de auditoria
-- Data: 2025-11-07
-- Descrição: Tabela para registrar todas as ações dos usuários no sistema

-- Criar tabela de auditoria
CREATE TABLE IF NOT EXISTS auditoria (
    auditoria_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    acao VARCHAR(50) NOT NULL,
    tabela_afetada VARCHAR(100),
    registro_id INTEGER,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dados_antes JSONB,
    dados_depois JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    descricao TEXT
);

-- Criar índices para melhorar performance de consultas
CREATE INDEX IF NOT EXISTS idx_auditoria_user_id ON auditoria(user_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_acao ON auditoria(acao);
CREATE INDEX IF NOT EXISTS idx_auditoria_tabela ON auditoria(tabela_afetada);
CREATE INDEX IF NOT EXISTS idx_auditoria_timestamp ON auditoria(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_auditoria_registro ON auditoria(tabela_afetada, registro_id);

-- Criar índice composto para queries comuns
CREATE INDEX IF NOT EXISTS idx_auditoria_user_timestamp ON auditoria(user_id, timestamp DESC);

-- Comentários nas colunas
COMMENT ON TABLE auditoria IS 'Registros de auditoria de todas as ações no sistema';
COMMENT ON COLUMN auditoria.auditoria_id IS 'ID único do registro de auditoria';
COMMENT ON COLUMN auditoria.user_id IS 'ID do usuário que realizou a ação (NULL para ações do sistema)';
COMMENT ON COLUMN auditoria.acao IS 'Tipo de ação: CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.';
COMMENT ON COLUMN auditoria.tabela_afetada IS 'Nome da tabela afetada pela ação';
COMMENT ON COLUMN auditoria.registro_id IS 'ID do registro afetado';
COMMENT ON COLUMN auditoria.timestamp IS 'Data e hora da ação';
COMMENT ON COLUMN auditoria.dados_antes IS 'Estado anterior do registro (JSON)';
COMMENT ON COLUMN auditoria.dados_depois IS 'Estado posterior do registro (JSON)';
COMMENT ON COLUMN auditoria.ip_address IS 'Endereço IP do cliente';
COMMENT ON COLUMN auditoria.user_agent IS 'User agent do navegador';
COMMENT ON COLUMN auditoria.descricao IS 'Descrição adicional da ação';

-- Criar função para limpeza automática de logs antigos (opcional)
CREATE OR REPLACE FUNCTION limpar_auditoria_antiga()
RETURNS INTEGER AS $$
DECLARE
    registros_deletados INTEGER;
BEGIN
    -- Deleta registros com mais de 365 dias
    DELETE FROM auditoria
    WHERE timestamp < NOW() - INTERVAL '365 days';
    
    GET DIAGNOSTICS registros_deletados = ROW_COUNT;
    RETURN registros_deletados;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION limpar_auditoria_antiga() IS 'Remove registros de auditoria com mais de 365 dias';

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE 'Tabela de auditoria criada com sucesso!';
    RAISE NOTICE 'Índices criados para otimização de consultas.';
    RAISE NOTICE 'Execute SELECT limpar_auditoria_antiga(); para limpar logs antigos.';
END $$;

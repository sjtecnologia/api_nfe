-- Migration: Criar tabela de inutilização de numeração de NFe
-- Data: 12/02/2026
-- Descrição: Tabela para registrar inutilizações de números de NFe/NFCe na SEFAZ

-- Criar tabela nfe_inutilizacoes
CREATE TABLE IF NOT EXISTS nfe_inutilizacoes (
    inutilizacao_id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    modelo VARCHAR(2) NOT NULL, -- 55=NFe, 65=NFCe
    serie INTEGER NOT NULL,
    numero_inicial INTEGER NOT NULL,
    numero_final INTEGER NOT NULL,
    ano VARCHAR(2) NOT NULL, -- Ano com 2 dígitos (ex: 26 para 2026)
    justificativa TEXT NOT NULL, -- Mínimo 15 caracteres
    
    -- Dados da resposta SEFAZ
    status VARCHAR(50) DEFAULT 'PROCESSANDO' NOT NULL, -- PROCESSANDO, AUTORIZADA, REJEITADA
    protocolo VARCHAR(15),
    chave_inutilizacao VARCHAR(44), -- ID da inutilização
    codigo_status VARCHAR(3), -- 102 = Inutilização autorizada
    mensagem_sefaz TEXT,
    xml_pedido TEXT,
    xml_resposta TEXT,
    
    -- Auditoria
    data_criacao TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    data_inutilizacao TIMESTAMP,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    CONSTRAINT chk_modelo CHECK (modelo IN ('55', '65')),
    CONSTRAINT chk_serie CHECK (serie >= 0 AND serie <= 999),
    CONSTRAINT chk_numeros CHECK (numero_inicial > 0 AND numero_final >= numero_inicial),
    CONSTRAINT chk_ano CHECK (LENGTH(ano) = 2 AND ano ~ '^[0-9]{2}$'),
    CONSTRAINT chk_justificativa CHECK (LENGTH(justificativa) >= 15),
    CONSTRAINT chk_status CHECK (status IN ('PROCESSANDO', 'AUTORIZADA', 'REJEITADA', 'ERRO'))
);

-- Criar índices para otimização de consultas
CREATE INDEX idx_inutilizacoes_cliente_id ON nfe_inutilizacoes(cliente_id);
CREATE INDEX idx_inutilizacoes_status ON nfe_inutilizacoes(status);
CREATE INDEX idx_inutilizacoes_modelo_serie ON nfe_inutilizacoes(modelo, serie);
CREATE INDEX idx_inutilizacoes_data_criacao ON nfe_inutilizacoes(data_criacao DESC);
CREATE INDEX idx_inutilizacoes_ano ON nfe_inutilizacoes(ano);

-- Índice composto para buscar inutilizações por cliente, modelo, série e ano
CREATE INDEX idx_inutilizacoes_busca ON nfe_inutilizacoes(cliente_id, modelo, serie, ano);

-- Comentários da tabela
COMMENT ON TABLE nfe_inutilizacoes IS 'Registra inutilizações de numeração de NFe/NFCe junto à SEFAZ';
COMMENT ON COLUMN nfe_inutilizacoes.inutilizacao_id IS 'ID único da inutilização';
COMMENT ON COLUMN nfe_inutilizacoes.cliente_id IS 'Cliente que solicitou a inutilização';
COMMENT ON COLUMN nfe_inutilizacoes.modelo IS '55=NFe, 65=NFCe';
COMMENT ON COLUMN nfe_inutilizacoes.serie IS 'Série da NFe/NFCe';
COMMENT ON COLUMN nfe_inutilizacoes.numero_inicial IS 'Primeiro número a ser inutilizado';
COMMENT ON COLUMN nfe_inutilizacoes.numero_final IS 'Último número a ser inutilizado';
COMMENT ON COLUMN nfe_inutilizacoes.ano IS 'Ano da inutilização (2 dígitos)';
COMMENT ON COLUMN nfe_inutilizacoes.justificativa IS 'Justificativa obrigatória (mín 15 caracteres)';
COMMENT ON COLUMN nfe_inutilizacoes.status IS 'Status: PROCESSANDO, AUTORIZADA, REJEITADA, ERRO';
COMMENT ON COLUMN nfe_inutilizacoes.protocolo IS 'Protocolo da SEFAZ';
COMMENT ON COLUMN nfe_inutilizacoes.chave_inutilizacao IS 'ID da inutilização gerado pela SEFAZ';
COMMENT ON COLUMN nfe_inutilizacoes.codigo_status IS 'Código de status retornado pela SEFAZ (102=Autorizada)';
COMMENT ON COLUMN nfe_inutilizacoes.mensagem_sefaz IS 'Mensagem retornada pela SEFAZ';

-- Verificar se a tabela foi criada
SELECT 'Tabela nfe_inutilizacoes criada com sucesso!' AS status;

-- Verificar estrutura
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'nfe_inutilizacoes'
ORDER BY ordinal_position;

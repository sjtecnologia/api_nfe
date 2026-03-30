-- Script para adicionar colunas de sincronização na tabela NCMs

-- Adiciona colunas para controle de sincronização
ALTER TABLE ncms 
ADD COLUMN IF NOT EXISTS data_atualizacao TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS fonte_atualizacao VARCHAR(50) DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;

-- Cria índices para performance
CREATE INDEX IF NOT EXISTS idx_ncms_codigo ON ncms(codigo);
CREATE INDEX IF NOT EXISTS idx_ncms_descricao ON ncms USING gin(to_tsvector('portuguese', descricao));
CREATE INDEX IF NOT EXISTS idx_ncms_data_atualizacao ON ncms(data_atualizacao);

-- Atualiza registros existentes
UPDATE ncms 
SET data_atualizacao = NOW(), 
    fonte_atualizacao = 'importacao_inicial' 
WHERE data_atualizacao IS NULL;
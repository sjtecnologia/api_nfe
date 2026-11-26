-- Migração para adicionar campo tipo aos NCMs
-- Data: 2025-10-29

-- Adiciona coluna tipo para distinguir NCMs sintéticos vs analíticos
ALTER TABLE ncms ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) DEFAULT 'analitico';

-- Adiciona comentário na coluna
COMMENT ON COLUMN ncms.tipo IS 'Tipo do NCM: sintetico (não recebe lançamento) ou analitico (recebe lançamento)';

-- Cria índice para melhor performance
CREATE INDEX IF NOT EXISTS idx_ncms_tipo ON ncms(tipo);

-- Atualiza NCMs existentes baseado no tamanho do código
-- NCMs de 8 dígitos são analíticos (recebem lançamento)
-- NCMs de menos de 8 dígitos são sintéticos (apenas classificação)
UPDATE ncms SET tipo = CASE 
    WHEN LENGTH(codigo) = 8 THEN 'analitico'
    ELSE 'sintetico'
END;

-- Adiciona constraint para garantir valores válidos
ALTER TABLE ncms ADD CONSTRAINT chk_ncm_tipo 
CHECK (tipo IN ('sintetico', 'analitico'));
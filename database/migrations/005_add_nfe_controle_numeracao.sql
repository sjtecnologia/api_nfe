-- Migration: Adicionar controle de numeração e campos complementares na NFe
-- Data: 2025-12-09
-- Descrição: Adiciona campos numero, serie, data_emissao, valor_total e função para controle de numeração

-- 1. Adicionar colunas se não existirem
DO $$ 
BEGIN
    -- Adicionar coluna numero
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'nfe_emitidas' AND column_name = 'numero') THEN
        ALTER TABLE nfe_emitidas ADD COLUMN numero INTEGER;
        COMMENT ON COLUMN nfe_emitidas.numero IS 'Número sequencial da NFe';
    END IF;

    -- Adicionar coluna serie (já existe no modelo, verificar)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'nfe_emitidas' AND column_name = 'serie') THEN
        ALTER TABLE nfe_emitidas ADD COLUMN serie INTEGER DEFAULT 1;
        COMMENT ON COLUMN nfe_emitidas.serie IS 'Série da NFe';
    END IF;

    -- Adicionar coluna data_emissao
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'nfe_emitidas' AND column_name = 'data_emissao') THEN
        ALTER TABLE nfe_emitidas ADD COLUMN data_emissao TIMESTAMP;
        COMMENT ON COLUMN nfe_emitidas.data_emissao IS 'Data de emissão da NFe';
    END IF;

    -- Adicionar coluna valor_total
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'nfe_emitidas' AND column_name = 'valor_total') THEN
        ALTER TABLE nfe_emitidas ADD COLUMN valor_total NUMERIC(15, 2);
        COMMENT ON COLUMN nfe_emitidas.valor_total IS 'Valor total da NFe';
    END IF;
END $$;

-- 2. Criar índice único para controle de numeração (cliente_id, modelo, serie, numero)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_nfe_numeracao_unica') THEN
        CREATE UNIQUE INDEX idx_nfe_numeracao_unica 
        ON nfe_emitidas(cliente_id, modelo, serie, numero) 
        WHERE numero IS NOT NULL;
    END IF;
END $$;

-- 3. Criar função para obter próximo número de NFe
CREATE OR REPLACE FUNCTION get_proximo_numero_nfe(
    p_cliente_id BIGINT,
    p_modelo VARCHAR(2),
    p_serie INTEGER DEFAULT 1
) RETURNS INTEGER AS $$
DECLARE
    v_proximo_numero INTEGER;
BEGIN
    -- Buscar o maior número existente para o cliente, modelo e série
    SELECT COALESCE(MAX(numero), 0) + 1
    INTO v_proximo_numero
    FROM nfe_emitidas
    WHERE cliente_id = p_cliente_id
      AND modelo = p_modelo
      AND serie = p_serie;
    
    RETURN v_proximo_numero;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_proximo_numero_nfe IS 'Retorna o próximo número sequencial de NFe para um cliente, modelo e série';

-- 4. Atualizar registros existentes com valores padrão
UPDATE nfe_emitidas 
SET serie = 1 
WHERE serie IS NULL;

UPDATE nfe_emitidas 
SET data_emissao = data_criacao 
WHERE data_emissao IS NULL AND data_criacao IS NOT NULL;

-- 5. Commit das alterações
COMMIT;

-- Exibir resumo
SELECT 
    'Migration 005 executada com sucesso!' as status,
    COUNT(*) as total_nfes,
    COUNT(numero) as nfes_com_numero,
    COUNT(*) - COUNT(numero) as nfes_sem_numero
FROM nfe_emitidas;

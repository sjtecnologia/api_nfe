-- Migration: Adicionar suporte a certificados A3
-- Data: 2024-12-18
-- Descrição: Adiciona campo tipo_certificado para diferenciar A1 (arquivo) de A3 (token/smartcard)

-- Adicionar coluna tipo_certificado
ALTER TABLE certificados_digitais 
ADD COLUMN IF NOT EXISTS tipo_certificado VARCHAR(10) DEFAULT 'A1';

-- Adicionar campo para armazenar slot_id do token (apenas para A3)
ALTER TABLE certificados_digitais 
ADD COLUMN IF NOT EXISTS token_slot_id INTEGER DEFAULT NULL;

-- Adicionar campo para label do certificado no token
ALTER TABLE certificados_digitais 
ADD COLUMN IF NOT EXISTS token_label VARCHAR(255) DEFAULT NULL;

-- Adicionar campo para library PKCS#11 do fabricante
ALTER TABLE certificados_digitais 
ADD COLUMN IF NOT EXISTS pkcs11_library VARCHAR(500) DEFAULT NULL;

-- Comentários
COMMENT ON COLUMN certificados_digitais.tipo_certificado IS 'Tipo: A1 (arquivo .pfx/.p12) ou A3 (token/smartcard USB)';
COMMENT ON COLUMN certificados_digitais.token_slot_id IS 'ID do slot do token (apenas para A3)';
COMMENT ON COLUMN certificados_digitais.token_label IS 'Label do certificado no token (apenas para A3)';
COMMENT ON COLUMN certificados_digitais.pkcs11_library IS 'Caminho da biblioteca PKCS#11 do fabricante (apenas para A3)';

-- Atualizar certificados existentes para A1
UPDATE certificados_digitais 
SET tipo_certificado = 'A1' 
WHERE tipo_certificado IS NULL;

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_certificados_tipo ON certificados_digitais(tipo_certificado);

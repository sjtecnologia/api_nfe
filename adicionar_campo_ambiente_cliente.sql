-- =====================================================
-- Script: Adicionar campo ambiente na tabela clientes
-- Data: 2025-12-01
-- Descrição: Adiciona campo para controlar ambiente de emissão (Homologação/Produção)
-- =====================================================

-- Adicionar coluna ambiente na tabela clientes
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS ambiente INTEGER DEFAULT 1;

COMMENT ON COLUMN clientes.ambiente IS 'Ambiente de emissão das NFe: 1=Homologação, 2=Produção';

-- Atualizar registros existentes para Homologação (padrão seguro)
UPDATE clientes 
SET ambiente = 1 
WHERE ambiente IS NULL;

-- Adicionar constraint NOT NULL após preencher valores
ALTER TABLE clientes ALTER COLUMN ambiente SET NOT NULL;

-- Verificação final
SELECT 
    cliente_id,
    razao_social,
    CASE 
        WHEN ambiente = 1 THEN 'Homologação'
        WHEN ambiente = 2 THEN 'Produção'
        ELSE 'Desconhecido'
    END as ambiente_desc,
    ambiente
FROM clientes
ORDER BY cliente_id;

-- =====================================================
-- INSTRUÇÕES PARA APLICAÇÃO:
-- =====================================================
-- 1. Conectar no pgAdmin
-- 2. Selecionar o banco de dados correto
-- 3. Abrir Query Tool
-- 4. Executar este script completo
-- 5. Verificar resultado da query SELECT no final
-- =====================================================

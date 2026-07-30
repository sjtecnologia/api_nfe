-- MIGRAÇÃO: Inverter código de ambiente para padrão SEFAZ
-- Data: 04/02/2026
-- 
-- ANTES (Sistema):
--   1 = Homologação
--   2 = Produção
--
-- DEPOIS (Padrão SEFAZ):
--   1 = Produção
--   2 = Homologação
--
-- ATENÇÃO: Execute este script APENAS UMA VEZ!

BEGIN;

-- 1. Verificar registros atuais
SELECT 
    cliente_id, 
    razao_social, 
    ambiente,
    CASE 
        WHEN ambiente = 1 THEN 'Homologação (será: Produção)'
        WHEN ambiente = 2 THEN 'Produção (será: Homologação)'
        ELSE 'Desconhecido'
    END AS status_atual
FROM clientes
ORDER BY cliente_id;

-- 2. Inverter os valores
-- Usar valor temporário (3) para evitar conflito
UPDATE clientes SET ambiente = 3 WHERE ambiente = 1;  -- Homolog → temp
UPDATE clientes SET ambiente = 1 WHERE ambiente = 2;  -- Produção → 1
UPDATE clientes SET ambiente = 2 WHERE ambiente = 3;  -- temp → 2 (Homolog)

-- 3. Verificar resultado
SELECT 
    cliente_id, 
    razao_social, 
    ambiente,
    CASE 
        WHEN ambiente = 1 THEN 'Produção (SEFAZ)'
        WHEN ambiente = 2 THEN 'Homologação (SEFAZ)'
        ELSE 'Desconhecido'
    END AS novo_status
FROM clientes
ORDER BY cliente_id;

-- 4. Se tudo estiver correto, commit. Caso contrário, ROLLBACK.
-- COMMIT;
-- ROLLBACK;

-- IMPORTANTE: Descomente COMMIT acima para efetivar as mudanças
-- Por segurança, deixamos comentado para você revisar primeiro

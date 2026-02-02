-- Migration: Popular tabela regimes_tributarios
-- Data: 2026-02-02
-- Descrição: Adiciona os 3 regimes tributários básicos

-- Verificar se já existem registros
DO $$
BEGIN
    -- Inserir apenas se não existirem
    IF NOT EXISTS (SELECT 1 FROM regimes_tributarios WHERE regime_tributario_id = 1) THEN
        INSERT INTO regimes_tributarios (regime_tributario_id, nome, descricao)
        VALUES 
            (1, 'Simples Nacional', 'Regime Especial Unificado de Arrecadação de Tributos e Contribuições'),
            (2, 'Lucro Presumido', 'Regime de tributação pelo Lucro Presumido'),
            (3, 'Lucro Real', 'Regime de tributação pelo Lucro Real');
        
        -- Resetar sequence para iniciar do ID 4
        PERFORM setval('regimes_tributarios_regime_tributario_id_seq', 3, true);
        
        RAISE NOTICE 'Regimes tributários populados com sucesso!';
    ELSE
        RAISE NOTICE 'Regimes tributários já existem, nenhuma alteração necessária.';
    END IF;
END $$;

-- Verificar resultado
SELECT regime_tributario_id, nome, descricao 
FROM regimes_tributarios 
ORDER BY regime_tributario_id;

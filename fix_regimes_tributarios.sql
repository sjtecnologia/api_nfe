-- Verificar regimes existentes
SELECT * FROM regimes_tributarios ORDER BY regime_tributario_id;

-- Inserir regimes tributários padrão (se não existirem)
INSERT INTO regimes_tributarios (regime_tributario_id, nome, descricao, ativo)
VALUES 
    (1, 'Simples Nacional', 'Regime Tributário do Simples Nacional', true),
    (2, 'Lucro Presumido', 'Regime Tributário do Lucro Presumido', true),
    (3, 'Lucro Real', 'Regime Tributário do Lucro Real', true)
ON CONFLICT (regime_tributario_id) DO NOTHING;

-- Verificar resultado
SELECT * FROM regimes_tributarios ORDER BY regime_tributario_id;

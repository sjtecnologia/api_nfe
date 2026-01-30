-- Migração para adicionar campos da Reforma Tributária (LC 214/2025) na tabela NFS-e
-- Campos obrigatórios para GISS Online - São José do Rio Preto
-- Data: 30/01/2026
-- Executar: psql -U seu_usuario -d sjtnfe -f migrations/add_nfse_reforma_tributaria_campos.sql

BEGIN;

-- Verificar se a tabela existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'nfse') THEN
        RAISE EXCEPTION 'Tabela nfse não existe. Execute primeiro create_table_nfse.sql';
    END IF;
END $$;

-- 1. Código NBS (Nomenclatura Brasileira de Serviços)
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS codigo_nbs VARCHAR(9) DEFAULT '101010000';
COMMENT ON COLUMN nfse.codigo_nbs IS 'Código NBS - Nomenclatura Brasileira de Serviços (9 dígitos sem pontos)';

-- 2. Finalidade da NFS-e
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS finalidade_nfse VARCHAR(1) DEFAULT '0';
COMMENT ON COLUMN nfse.finalidade_nfse IS 'Finalidade: 0=Normal, 1=Complementar, 2=Ajuste, 3=Substituição';

-- 3. Indicador de Consumidor Final
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS indicador_consumidor_final VARCHAR(1) DEFAULT '0';
COMMENT ON COLUMN nfse.indicador_consumidor_final IS 'Consumidor Final: 0=Não, 1=Sim';

-- 4. Código Indicador de Operação
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS codigo_indicador_operacao VARCHAR(6) DEFAULT '000001';
COMMENT ON COLUMN nfse.codigo_indicador_operacao IS 'Código da operação IBS/CBS (6 dígitos): 000001=Interna, 000002=Interestadual, 000003=Exterior';

-- 5. Indicador de Destinatário
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS indicador_destinatario VARCHAR(1) DEFAULT '0';
COMMENT ON COLUMN nfse.indicador_destinatario IS 'Destinatário: 0=Interno (mesmo município), 1=Interestadual, 2=Exterior';

-- 6. CST IBS/CBS (Código de Situação Tributária)
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS cst_ibs_cbs VARCHAR(3) DEFAULT '001';
COMMENT ON COLUMN nfse.cst_ibs_cbs IS 'CST IBS/CBS (3 dígitos): 001=Tributado cheia, 002=Tributado com redução, 003=Diferido, 004=Isento, 005=Não tributado, 006=Suspenso judicial, 007=Suspenso administrativo, 008=Não incidência';

-- 7. Código de Classificação Tributária
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS codigo_classificacao_tributaria VARCHAR(6) DEFAULT '000001';
COMMENT ON COLUMN nfse.codigo_classificacao_tributaria IS 'Código de classificação tributária conforme Reforma Tributária (6 dígitos)';

-- 8. Código da Localidade de Incidência (município)
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS codigo_localidade_incidencia VARCHAR(7) DEFAULT '3549805';
COMMENT ON COLUMN nfse.codigo_localidade_incidencia IS 'Código IBGE do município de incidência do IBS/CBS - São José do Rio Preto padrão';

-- 9. Percentual Redutor da Base de Cálculo
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS percentual_redutor DECIMAL(5,2) DEFAULT 0.00;
COMMENT ON COLUMN nfse.percentual_redutor IS 'Percentual de redução da base de cálculo IBS/CBS (0 a 100)';

-- 10. Percentual Total de Tributos Federais
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS percentual_total_tributos_federais DECIMAL(5,2) DEFAULT 0.00;
COMMENT ON COLUMN nfse.percentual_total_tributos_federais IS 'Percentual total de tributos federais sobre o valor do serviço';

-- 11. Percentual Total de Tributos Estaduais
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS percentual_total_tributos_estaduais DECIMAL(5,2) DEFAULT 0.00;
COMMENT ON COLUMN nfse.percentual_total_tributos_estaduais IS 'Percentual total de tributos estaduais sobre o valor do serviço';

-- 12. Percentual Total de Tributos Municipais
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS percentual_total_tributos_municipais DECIMAL(5,2) DEFAULT 5.00;
COMMENT ON COLUMN nfse.percentual_total_tributos_municipais IS 'Percentual total de tributos municipais sobre o valor do serviço (geralmente ISS)';

-- 13. Regime Especial de Tributação
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS regime_especial_tributacao VARCHAR(1);
COMMENT ON COLUMN nfse.regime_especial_tributacao IS 'Regime especial: 1=ME Municipal, 2=Estimativa, 3=Sociedade Profissionais, 4=Cooperativa, 5=MEI, 6=ME/EPP Simples';

-- 14. Optante Simples Nacional
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS optante_simples_nacional BOOLEAN DEFAULT TRUE;
COMMENT ON COLUMN nfse.optante_simples_nacional IS 'Indica se o prestador é optante do Simples Nacional';

-- 15. Incentivador Cultural
ALTER TABLE nfse ADD COLUMN IF NOT EXISTS incentivador_cultural BOOLEAN DEFAULT FALSE;
COMMENT ON COLUMN nfse.incentivador_cultural IS 'Indica se o prestador é incentivador cultural';

-- Criar índices para melhorar performance nas consultas
CREATE INDEX IF NOT EXISTS idx_nfse_codigo_nbs ON nfse(codigo_nbs);
CREATE INDEX IF NOT EXISTS idx_nfse_finalidade ON nfse(finalidade_nfse);
CREATE INDEX IF NOT EXISTS idx_nfse_localidade_incidencia ON nfse(codigo_localidade_incidencia);
CREATE INDEX IF NOT EXISTS idx_nfse_cst_ibs_cbs ON nfse(cst_ibs_cbs);

-- Adicionar constraint para validar valores
ALTER TABLE nfse ADD CONSTRAINT chk_finalidade_nfse 
    CHECK (finalidade_nfse IN ('0', '1', '2', '3'));

ALTER TABLE nfse ADD CONSTRAINT chk_indicador_consumidor_final 
    CHECK (indicador_consumidor_final IN ('0', '1'));

ALTER TABLE nfse ADD CONSTRAINT chk_indicador_destinatario 
    CHECK (indicador_destinatario IN ('0', '1', '2'));

ALTER TABLE nfse ADD CONSTRAINT chk_percentual_redutor 
    CHECK (percentual_redutor >= 0 AND percentual_redutor <= 100);

ALTER TABLE nfse ADD CONSTRAINT chk_percentual_tributos_federais 
    CHECK (percentual_total_tributos_federais >= 0 AND percentual_total_tributos_federais <= 100);

ALTER TABLE nfse ADD CONSTRAINT chk_percentual_tributos_estaduais 
    CHECK (percentual_total_tributos_estaduais >= 0 AND percentual_total_tributos_estaduais <= 100);

ALTER TABLE nfse ADD CONSTRAINT chk_percentual_tributos_municipais 
    CHECK (percentual_total_tributos_municipais >= 0 AND percentual_total_tributos_municipais <= 100);

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE '✅ Migração concluída com sucesso!';
    RAISE NOTICE 'Campos da Reforma Tributária (LC 214/2025) adicionados à tabela nfse';
    RAISE NOTICE 'Total de 15 novos campos relacionados a IBS/CBS e tributos totais';
END $$;

COMMIT;

-- Verificar campos adicionados
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'nfse' 
    AND column_name IN (
        'codigo_nbs',
        'finalidade_nfse',
        'indicador_consumidor_final',
        'codigo_indicador_operacao',
        'indicador_destinatario',
        'cst_ibs_cbs',
        'codigo_classificacao_tributaria',
        'codigo_localidade_incidencia',
        'percentual_redutor',
        'percentual_total_tributos_federais',
        'percentual_total_tributos_estaduais',
        'percentual_total_tributos_municipais',
        'regime_especial_tributacao',
        'optante_simples_nacional',
        'incentivador_cultural'
    )
ORDER BY ordinal_position;

-- =====================================================================
-- CRIAÇÃO DA TABELA: regras_tributacao_servicos
-- =====================================================================
-- Tabela para armazenar regras tributárias específicas para NFS-e
-- Separada da tabela regras_tributacao (que é focada em NFe/produtos)
-- 
-- Data: 30/01/2026
-- Autor: Sistema EmiteMax
-- Reforma Tributária: LC 214/2025
-- =====================================================================

BEGIN;

-- 1. CRIAR TABELA
CREATE TABLE IF NOT EXISTS regras_tributacao_servicos (
    regra_id                          BIGSERIAL PRIMARY KEY,
    cliente_id                        BIGINT NOT NULL,
    regime_tributario_id              BIGINT NOT NULL,
    
    -- ========== IDENTIFICAÇÃO DO SERVIÇO ==========
    codigo_servico_lc116              VARCHAR(5) NOT NULL,
    codigo_nbs                        VARCHAR(9) NOT NULL DEFAULT '101010000',
    descricao_servico                 TEXT,
    
    -- ========== ISS (IMPOSTO SOBRE SERVIÇOS) ==========
    aliquota_iss                      NUMERIC(5,2) NOT NULL DEFAULT 5.00,
    iss_retido                        BOOLEAN DEFAULT FALSE,
    responsavel_retencao              VARCHAR(1),
    
    -- ========== REFORMA TRIBUTÁRIA LC 214/2025 ==========
    cst_ibs_cbs                       VARCHAR(3) DEFAULT '001',
    codigo_indicador_operacao         VARCHAR(6) DEFAULT '000001',
    codigo_classificacao_tributaria   VARCHAR(6) DEFAULT '000001',
    codigo_localidade_incidencia      VARCHAR(7) DEFAULT '3549805',
    percentual_redutor                NUMERIC(5,2) DEFAULT 0.00,
    
    -- ========== PERCENTUAIS DE TRIBUTOS ==========
    percentual_total_tributos_federais   NUMERIC(5,2) DEFAULT 0.00,
    percentual_total_tributos_estaduais  NUMERIC(5,2) DEFAULT 0.00,
    percentual_total_tributos_municipais NUMERIC(5,2) DEFAULT 5.00,
    
    -- ========== REGIME ESPECIAL ==========
    regime_especial_tributacao        VARCHAR(1),
    optante_simples_nacional          BOOLEAN DEFAULT TRUE,
    incentivador_cultural             BOOLEAN DEFAULT FALSE,
    
    -- ========== CONDIÇÕES DE APLICAÇÃO ==========
    uf_origem                         VARCHAR(2),
    uf_destino                        VARCHAR(2),
    indicador_destinatario            VARCHAR(1) DEFAULT '0',
    indicador_consumidor_final        VARCHAR(1) DEFAULT '0',
    finalidade_nfse                   VARCHAR(1) DEFAULT '0',
    
    -- ========== CONTROLE E AUDITORIA ==========
    prioridade                        INTEGER DEFAULT 100,
    descricao_regra                   TEXT,
    ativo                             BOOLEAN DEFAULT TRUE,
    data_criacao                      TIMESTAMP DEFAULT NOW(),
    data_atualizacao                  TIMESTAMP DEFAULT NOW(),
    created_by_user_id                BIGINT,
    updated_by_user_id                BIGINT,
    
    -- ========== CONSTRAINTS ==========
    CONSTRAINT fk_regras_servicos_cliente 
        FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    CONSTRAINT fk_regras_servicos_regime 
        FOREIGN KEY (regime_tributario_id) REFERENCES regimes_tributarios(regime_tributario_id),
    CONSTRAINT fk_regras_servicos_created_by 
        FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    CONSTRAINT fk_regras_servicos_updated_by 
        FOREIGN KEY (updated_by_user_id) REFERENCES users(id)
);

-- 2. CRIAR ÍNDICES
CREATE INDEX idx_regras_servicos_cliente ON regras_tributacao_servicos(cliente_id);
CREATE INDEX idx_regras_servicos_codigo_servico ON regras_tributacao_servicos(codigo_servico_lc116);
CREATE INDEX idx_regras_servicos_nbs ON regras_tributacao_servicos(codigo_nbs);
CREATE INDEX idx_regras_servicos_ativo ON regras_tributacao_servicos(ativo);
CREATE INDEX idx_regras_servicos_regime ON regras_tributacao_servicos(regime_tributario_id);
CREATE INDEX idx_regras_servicos_prioridade ON regras_tributacao_servicos(prioridade);

-- Índice composto para busca de regras
CREATE INDEX idx_regras_servicos_busca ON regras_tributacao_servicos(
    cliente_id, codigo_servico_lc116, ativo, prioridade
);

-- 3. ADICIONAR CONSTRAINTS DE VALIDAÇÃO
ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_aliquota_iss 
    CHECK (aliquota_iss >= 0 AND aliquota_iss <= 5);

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_responsavel_retencao 
    CHECK (responsavel_retencao IS NULL OR responsavel_retencao IN ('1', '2'));

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_finalidade_nfse_servicos 
    CHECK (finalidade_nfse IN ('0', '1', '2', '3'));

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_indicador_consumidor_final_servicos 
    CHECK (indicador_consumidor_final IN ('0', '1'));

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_indicador_destinatario_servicos 
    CHECK (indicador_destinatario IN ('0', '1', '2'));

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_percentual_redutor_servicos 
    CHECK (percentual_redutor >= 0 AND percentual_redutor <= 100);

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_tributos_federais_servicos 
    CHECK (percentual_total_tributos_federais >= 0 AND percentual_total_tributos_federais <= 100);

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_tributos_estaduais_servicos 
    CHECK (percentual_total_tributos_estaduais >= 0 AND percentual_total_tributos_estaduais <= 100);

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_tributos_municipais_servicos 
    CHECK (percentual_total_tributos_municipais >= 0 AND percentual_total_tributos_municipais <= 100);

ALTER TABLE regras_tributacao_servicos 
    ADD CONSTRAINT chk_regime_especial_servicos 
    CHECK (regime_especial_tributacao IS NULL OR regime_especial_tributacao IN ('1', '2', '3', '4', '5', '6'));

-- 4. ADICIONAR COMENTÁRIOS
COMMENT ON TABLE regras_tributacao_servicos IS 
    'Regras tributárias para NFS-e - Específico para prestação de serviços';

COMMENT ON COLUMN regras_tributacao_servicos.codigo_servico_lc116 IS 
    'Código do serviço conforme Lei Complementar 116/2003 (ex: 01.01, 17.05)';

COMMENT ON COLUMN regras_tributacao_servicos.codigo_nbs IS 
    'Código NBS - Nomenclatura Brasileira de Serviços (9 dígitos)';

COMMENT ON COLUMN regras_tributacao_servicos.aliquota_iss IS 
    'Alíquota do ISS em percentual (2% a 5%)';

COMMENT ON COLUMN regras_tributacao_servicos.iss_retido IS 
    'Indica se o ISS é retido na fonte pelo Tomadores';

COMMENT ON COLUMN regras_tributacao_servicos.responsavel_retencao IS 
    '1=Tomadores retém, 2=Intermediário retém';

COMMENT ON COLUMN regras_tributacao_servicos.cst_ibs_cbs IS 
    'CST IBS/CBS: 001=Tributado, 002=Redução, 003=Diferido, 004=Isento, 005=Não tributado, 006=Suspenso judicial, 007=Suspenso admin, 008=Não incidência';

COMMENT ON COLUMN regras_tributacao_servicos.codigo_indicador_operacao IS 
    'Código da operação IBS/CBS: 000001=Interna, 000002=Interestadual, 000003=Exterior';

COMMENT ON COLUMN regras_tributacao_servicos.codigo_localidade_incidencia IS 
    'Código IBGE do município de incidência (7 dígitos) - Padrão: 3549805 (São José do Rio Preto)';

COMMENT ON COLUMN regras_tributacao_servicos.percentual_redutor IS 
    'Percentual de redução da base de cálculo IBS/CBS (0 a 100)';

COMMENT ON COLUMN regras_tributacao_servicos.regime_especial_tributacao IS 
    '1=ME Municipal, 2=Estimativa, 3=Soc. Profissionais, 4=Cooperativa, 5=MEI, 6=ME/EPP Simples';

COMMENT ON COLUMN regras_tributacao_servicos.indicador_destinatario IS 
    '0=Interno (mesmo município), 1=Interestadual, 2=Exterior';

COMMENT ON COLUMN regras_tributacao_servicos.finalidade_nfse IS 
    '0=Normal, 1=Complementar, 2=Ajuste, 3=Substituição';

COMMENT ON COLUMN regras_tributacao_servicos.prioridade IS 
    'Ordem de prioridade para aplicação da regra (menor = mais prioritária)';

-- 5. CRIAR FUNÇÃO DE TRIGGER PARA ATUALIZAR data_atualizacao
CREATE OR REPLACE FUNCTION atualizar_data_atualizacao_regras_servicos()
RETURNS TRIGGER AS $$
BEGIN
    NEW.data_atualizacao = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. CRIAR TRIGGER
CREATE TRIGGER trigger_atualizar_data_atualizacao_regras_servicos
    BEFORE UPDATE ON regras_tributacao_servicos
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_data_atualizacao_regras_servicos();

-- 7. INSERIR REGRAS PADRÃO (Opcional - exemplos)
-- Você pode adicionar regras padrão aqui se desejar

COMMIT;

-- =====================================================================
-- VERIFICAÇÃO
-- =====================================================================
SELECT 
    'Tabela regras_tributacao_servicos criada com sucesso!' as mensagem,
    COUNT(*) as total_colunas
FROM information_schema.columns 
WHERE table_name = 'regras_tributacao_servicos';

-- Listar todas as colunas
SELECT 
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'regras_tributacao_servicos'
ORDER BY ordinal_position;

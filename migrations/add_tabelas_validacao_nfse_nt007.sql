--
-- Migration: Tabelas de Validação NFS-e RTC - NT007 v1.03.00
-- Data: 09/02/2026
-- Referência: AnexoVII - IndOp_IBSCBS v1.01.00
--

BEGIN;

-- =============================================================================
-- 1. TABELA: Indicadores de Operação IBS/CBS (AnexoVII v1.01.00)
-- =============================================================================

CREATE TABLE IF NOT EXISTS indicadores_operacao_ibscbs (
    codigo_indicador VARCHAR(6) PRIMARY KEY,
    descricao VARCHAR(200) NOT NULL,
    tipo_operacao VARCHAR(50) NOT NULL, -- 'Interna', 'Interestadual', 'Exterior'
    categoria VARCHAR(100),
    versao_anexo_vii VARCHAR(10) NOT NULL DEFAULT 'v1.01.00',
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comentários
COMMENT ON TABLE indicadores_operacao_ibscbs IS 'Códigos de indicadores de operação conforme AnexoVII - IndOp_IBSCBS';
COMMENT ON COLUMN indicadores_operacao_ibscbs.codigo_indicador IS 'Código do indicador (6 dígitos) - campo cIndOp';
COMMENT ON COLUMN indicadores_operacao_ibscbs.tipo_operacao IS 'Tipo: Interna, Interestadual ou Exterior';
COMMENT ON COLUMN indicadores_operacao_ibscbs.versao_anexo_vii IS 'Versão do AnexoVII de origem';

-- Índices
CREATE INDEX IF NOT EXISTS idx_indop_tipo ON indicadores_operacao_ibscbs(tipo_operacao);
CREATE INDEX IF NOT EXISTS idx_indop_ativo ON indicadores_operacao_ibscbs(ativo);
CREATE INDEX IF NOT EXISTS idx_indop_categoria ON indicadores_operacao_ibscbs(categoria);

-- Popular com dados básicos do AnexoVII v1.01.00
INSERT INTO indicadores_operacao_ibscbs (codigo_indicador, descricao, tipo_operacao, categoria) VALUES
-- Operações Internas
('000001', 'Prestação de serviço - Operação interna', 'Interna', 'Serviços Gerais'),
('000101', 'Prestação de serviço - Operação interna - Construção Civil', 'Interna', 'Construção Civil'),
('000102', 'Prestação de serviço - Operação interna - Serviços de TI', 'Inerna', 'Tecnologia da Informação'),
('000103', 'Prestação de serviço - Operação interna - Serviços Médicos', 'Interna', 'Saúde'),
('000104', 'Prestação de serviço - Operação interna - Serviços Educacionais', 'Interna', 'Educação'),
('000105', 'Prestação de serviço - Operação interna - Serviços de Consultoria', 'Interna', 'Consultoria'),

-- Operações Interestaduais
('000002', 'Prestação de serviço - Operação interestadual', 'Interestadual', 'Serviços Gerais'),
('000201', 'Prestação de serviço - Operação interestadual - Construção Civil', 'Interestadual', 'Construção Civil'),
('000202', 'Prestação de serviço - Operação interestadual - Serviços de TI', 'Interestadual', 'Tecnologia da Informação'),
('000203', 'Prestação de serviço - Operação interestadual - Serviços Médicos', 'Interestadual', 'Saúde'),

-- Operações de Exportação
('000003', 'Prestação de serviço - Exportação', 'Exterior', 'Serviços Gerais'),
('000301', 'Prestação de serviço - Exportação - Serviços de TI', 'Exterior', 'Tecnologia da Informação'),
('000302', 'Prestação de serviço - Exportação - Serviços de Consultoria', 'Exterior', 'Consultoria')

ON CONFLICT (codigo_indicador) DO NOTHING;

-- =============================================================================
-- 2. TABELA: Classificação Tributária NFS-e (cClassTrib)
-- =============================================================================

CREATE TABLE IF NOT EXISTS classificacao_tributaria_nfse (
    codigo_classificacao VARCHAR(6) PRIMARY KEY,
    descricao VARCHAR(200) NOT NULL,
    categoria VARCHAR(100),
    aliquota_sugerida_ibs DECIMAL(5,2),
    aliquota_sugerida_cbs DECIMAL(5,2),
    observacoes TEXT,
    versao_anexo VARCHAR(10) NOT NULL DEFAULT 'v1.03.00',
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comentários
COMMENT ON TABLE classificacao_tributaria_nfse IS 'Códigos de classificação tributária IBS/CBS para NFS-e';
COMMENT ON COLUMN classificacao_tributaria_nfse.codigo_classificacao IS 'Código de classificação (6 dígitos) - campo cClassTrib';
COMMENT ON COLUMN classificacao_tributaria_nfse.aliquota_sugerida_ibs IS 'Alíquota sugerida IBS (%) - valores indicativos';
COMMENT ON COLUMN classificacao_tributaria_nfse.aliquota_sugerida_cbs IS 'Alíquota sugerida CBS (%) - valores indicativos';

-- Índices
CREATE INDEX IF NOT EXISTS idx_classtrib_categoria ON classificacao_tributaria_nfse(categoria);
CREATE INDEX IF NOT EXISTS idx_classtrib_ativo ON classificacao_tributaria_nfse(ativo);

-- Popular com classificações básicas
INSERT INTO classificacao_tributaria_nfse (codigo_classificacao, descricao, categoria, aliquota_sugerida_ibs, aliquota_sugerida_cbs, observacoes) VALUES
('000001', 'Tributação normal - Regime padrão', 'Geral', 0.00, 0.00, 'Classificação padrão para serviços tributados normalmente'),
('000002', 'Tributação com redução de base de cálculo', 'Redução BC', 0.00, 0.00, 'Aplica-se quando há redução da base de cálculo'),
('000003', 'Serviços com isenção', 'Isenção', 0.00, 0.00, 'Serviços isentos de IBS/CBS'),
('000004', 'Serviços imunes', 'Imunidade', 0.00, 0.00, 'Serviços com imunidade tributária'),
('000005', 'Diferimento', 'Diferimento', 0.00, 0.00, 'Tributação diferida para momento posterior'),
('000100', 'Serviços de Tecnologia da Informação', 'TI', 0.00, 0.00, 'Serviços relacionados à TI'),
('000101', 'Desenvolvimento de Software', 'TI - Software', 0.00, 0.00, 'Desenvolvimento e programação'),
('000200', 'Serviços de Construção Civil', 'Construção', 0.00, 0.00, 'Serviços de construção e reforma'),
('000300', 'Serviços de Saúde', 'Saúde', 0.00, 0.00, 'Serviços médicos e hospitalares'),
('000400', 'Serviços Educacionais', 'Educação', 0.00, 0.00, 'Serviços de ensino e formação'),
('000500', 'Serviços de Consultoria', 'Consultoria', 0.00, 0.00, 'Consultoria e assessoria')

ON CONFLICT (codigo_classificacao) DO NOTHING;

-- =============================================================================
-- 3. TABELA: Códigos CST IBS/CBS
-- =============================================================================

CREATE TABLE IF NOT EXISTS cst_ibs_cbs (
    codigo_cst VARCHAR(3) PRIMARY KEY,
    descricao VARCHAR(200) NOT NULL,
    categoria VARCHAR(50),
    permite_credito BOOLEAN DEFAULT TRUE,
    calcula_ibs BOOLEAN DEFAULT TRUE,
    calcula_cbs BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comentários
COMMENT ON TABLE cst_ibs_cbs IS 'Códigos de Situação Tributária IBS/CBS (3 dígitos)';
COMMENT ON COLUMN cst_ibs_cbs.codigo_cst IS 'Código CST (3 dígitos) - campo cst';
COMMENT ON COLUMN cst_ibs_cbs.permite_credito IS 'Indica se permite crédito de IBS/CBS';
COMMENT ON COLUMN cst_ibs_cbs.calcula_ibs IS 'Indica se deve calcular IBS';
COMMENT ON COLUMN cst_ibs_cbs.calcula_cbs IS 'Indica se deve calcular CBS';

-- Índices
CREATE INDEX IF NOT EXISTS idx_cst_categoria ON cst_ibs_cbs(categoria);
CREATE INDEX IF NOT EXISTS idx_cst_ativo ON cst_ibs_cbs(ativo);

-- Popular com CST básicos
INSERT INTO cst_ibs_cbs (codigo_cst, descricao, categoria, permite_credito, calcula_ibs, calcula_cbs, observacoes) VALUES
('001', 'Tributação normal', 'Normal', TRUE, TRUE, TRUE, 'Tributação cheia - aplica alíquotas normais'),
('002', 'Tributação com redução de base de cálculo', 'Redução BC', TRUE, TRUE, TRUE, 'Base de cálculo reduzida conforme legislação'),
('003', 'Diferimento', 'Diferido', FALSE, FALSE, FALSE, 'Tributação diferida para momento posterior'),
('004', 'Substituição tributária', 'ST', FALSE, FALSE, FALSE, 'Substituição tributária - já recolhido'),
('005', 'Isento', 'Isento', FALSE, FALSE, FALSE, 'Serviço isento de IBS/CBS'),
('006', 'Imune', 'Imune', FALSE, FALSE, FALSE, 'Operação com imunidade tributária'),
('007', 'Não tributado', 'Não Tributado', FALSE, FALSE, FALSE, 'Fora do campo de incidência'),
('008', 'Suspensão', 'Suspenso', FALSE, FALSE, FALSE, 'Exigibilidade suspensa por decisão judicial')

ON CONFLICT (codigo_cst) DO NOTHING;

-- =============================================================================
-- CONSTRAINTS E VALIDAÇÕES
-- =============================================================================

-- Validar formato dos códigos
ALTER TABLE indicadores_operacao_ibscbs 
    ADD CONSTRAINT chk_indop_codigo_formato 
    CHECK (codigo_indicador ~ '^[0-9]{6}$');

ALTER TABLE classificacao_tributaria_nfse 
    ADD CONSTRAINT chk_classtrib_codigo_formato 
    CHECK (codigo_classificacao ~ '^[0-9]{6}$');

ALTER TABLE cst_ibs_cbs 
    ADD CONSTRAINT chk_cst_codigo_formato 
    CHECK (codigo_cst ~ '^[0-9]{3}$');

-- Validar faixas de alíquotas
ALTER TABLE classificacao_tributaria_nfse 
    ADD CONSTRAINT chk_classtrib_aliquota_ibs 
    CHECK (aliquota_sugerida_ibs IS NULL OR (aliquota_sugerida_ibs >= 0 AND aliquota_sugerida_ibs <= 100));

ALTER TABLE classificacao_tributaria_nfse 
    ADD CONSTRAINT chk_classtrib_aliquota_cbs 
    CHECK (aliquota_sugerida_cbs IS NULL OR (aliquota_sugerida_cbs >= 0 AND aliquota_sugerida_cbs <= 100));

-- =============================================================================
-- TRIGGERS PARA UPDATED_AT
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_indop_updated_at ON indicadores_operacao_ibscbs;
CREATE TRIGGER update_indop_updated_at 
    BEFORE UPDATE ON indicadores_operacao_ibscbs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_classtrib_updated_at ON classificacao_tributaria_nfse;
CREATE TRIGGER update_classtrib_updated_at 
    BEFORE UPDATE ON classificacao_tributaria_nfse 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;

-- =============================================================================
-- FIM DA MIGRATION
-- =============================================================================

-- Verificar dados inseridos
DO $$
DECLARE
    v_count_indop INTEGER;
    v_count_classtrib INTEGER;
    v_count_cst INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count_indop FROM indicadores_operacao_ibscbs;
    SELECT COUNT(*) INTO v_count_classtrib FROM classificacao_tributaria_nfse;
    SELECT COUNT(*) INTO v_count_cst FROM cst_ibs_cbs;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRATION CONCLUÍDA COM SUCESSO!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tabelas criadas:';
    RAISE NOTICE '  ✓ indicadores_operacao_ibscbs      (% registros)', v_count_indop;
    RAISE NOTICE '  ✓ classificacao_tributaria_nfse    (% registros)', v_count_classtrib;
    RAISE NOTICE '  ✓ cst_ibs_cbs                      (% registros)', v_count_cst;
    RAISE NOTICE '';
    RAISE NOTICE 'Referências:';
    RAISE NOTICE '  - Nota Técnica SE/CGNFS-e nº 007';
    RAISE NOTICE '  - AnexoVII - IndOp_IBSCBS v1.01.00';
    RAISE NOTICE '  - AnexoVI - Layout RTC v1.03.00';
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
END $$;

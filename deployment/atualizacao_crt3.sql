-- ============================================================================
-- SCRIPT DE ATUALIZAÇÃO DO BANCO DE DADOS - CRT=3 (Lucro Real/Presumido)
-- Sistema: EmiteMax v2.0
-- Data: 11/12/2025
-- Desenvolvedor: Renato
-- ============================================================================

-- IMPORTANTE: Execute este script no PostgreSQL do servidor Windows
-- psql -U postgres -d sjtnfe -f atualizacao_crt3.sql

-- ============================================================================
-- 1. ADICIONAR CAMPO CRT NA TABELA regimes_tributarios
-- ============================================================================

ALTER TABLE regimes_tributarios ADD COLUMN IF NOT EXISTS crt INTEGER DEFAULT 1;

-- Atualizar valores de CRT:
-- CRT=1 para Simples Nacional
-- CRT=3 para Lucro Real e Lucro Presumido
UPDATE regimes_tributarios SET crt = 1 WHERE regime_tributario_id = 1;
UPDATE regimes_tributarios SET crt = 3 WHERE regime_tributario_id IN (2, 3);

-- Verificar se há outros regimes e atualizar
UPDATE regimes_tributarios SET crt = 1 WHERE crt IS NULL;

-- ============================================================================
-- 2. CRIAR TABELA classificacoes_ibs_cbs
-- ============================================================================

CREATE TABLE IF NOT EXISTS classificacoes_ibs_cbs (
    classificacao_id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) UNIQUE NOT NULL,
    descricao TEXT NOT NULL,
    aliquota_ibs_uf NUMERIC(5,2) DEFAULT 0.10 NOT NULL,
    aliquota_ibs_mun NUMERIC(5,2) DEFAULT 0.00 NOT NULL,
    aliquota_cbs NUMERIC(5,2) DEFAULT 0.90 NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Inserir classificações iniciais (se não existirem)
INSERT INTO classificacoes_ibs_cbs (codigo, descricao, aliquota_ibs_uf, aliquota_ibs_mun, aliquota_cbs)
VALUES 
    ('000001', 'Medicamentos e produtos de higiene pessoal', 0.10, 0.00, 0.90),
    ('000002', 'Produtos alimentícios básicos', 0.10, 0.00, 0.90),
    ('000003', 'Outros produtos', 0.10, 0.00, 0.90)
ON CONFLICT (codigo) DO NOTHING;

-- Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_classificacoes_ativo ON classificacoes_ibs_cbs(ativo);

-- ============================================================================
-- 3. CRIAR TABELA autorizacoes_xml_nfe
-- ============================================================================

CREATE TABLE IF NOT EXISTS autorizacoes_xml_nfe (
    autorizacao_id SERIAL PRIMARY KEY,
    nfe_emitida_id BIGINT NOT NULL,
    cliente_id BIGINT NOT NULL,
    cpf_cnpj VARCHAR(14) NOT NULL,
    tipo VARCHAR(3) CHECK (tipo IN ('CPF', 'CNPJ')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_autorizacoes_nfe 
        FOREIGN KEY (nfe_emitida_id, cliente_id) 
        REFERENCES nfe_emitidas(nfe_emitida_id, cliente_id) 
        ON DELETE CASCADE
);

-- Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_autorizacoes_nfe_id 
    ON autorizacoes_xml_nfe(nfe_emitida_id, cliente_id);

-- ============================================================================
-- 4. ADICIONAR COLUNAS IBS/CBS NA TABELA nfe_emitidas
-- ============================================================================

ALTER TABLE nfe_emitidas 
    ADD COLUMN IF NOT EXISTS total_ibs NUMERIC(15,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_cbs NUMERIC(15,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_ibs_bc NUMERIC(15,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS valor_icms_st_retido NUMERIC(15,2) DEFAULT 0;

-- ============================================================================
-- 5. ADICIONAR COLUNA classificacao_ibs_cbs_id NA TABELA produtos
-- ============================================================================

ALTER TABLE produtos 
    ADD COLUMN IF NOT EXISTS classificacao_ibs_cbs_id INTEGER,
    ADD CONSTRAINT fk_produtos_classificacao_ibs 
        FOREIGN KEY (classificacao_ibs_cbs_id) 
        REFERENCES classificacoes_ibs_cbs(classificacao_id)
        ON DELETE SET NULL;

-- ============================================================================
-- 6. VERIFICAÇÃO E TESTES
-- ============================================================================

-- Verificar estrutura criada
DO $$ 
DECLARE
    v_count INTEGER;
BEGIN
    -- Verificar campo CRT
    SELECT COUNT(*) INTO v_count 
    FROM information_schema.columns 
    WHERE table_name = 'regimes_tributarios' 
    AND column_name = 'crt';
    
    IF v_count > 0 THEN
        RAISE NOTICE '✅ Campo CRT adicionado em regimes_tributarios';
    ELSE
        RAISE EXCEPTION '❌ ERRO: Campo CRT não foi criado!';
    END IF;
    
    -- Verificar tabela classificacoes_ibs_cbs
    SELECT COUNT(*) INTO v_count 
    FROM information_schema.tables 
    WHERE table_name = 'classificacoes_ibs_cbs';
    
    IF v_count > 0 THEN
        RAISE NOTICE '✅ Tabela classificacoes_ibs_cbs criada';
    ELSE
        RAISE EXCEPTION '❌ ERRO: Tabela classificacoes_ibs_cbs não existe!';
    END IF;
    
    -- Verificar tabela autorizacoes_xml_nfe
    SELECT COUNT(*) INTO v_count 
    FROM information_schema.tables 
    WHERE table_name = 'autorizacoes_xml_nfe';
    
    IF v_count > 0 THEN
        RAISE NOTICE '✅ Tabela autorizacoes_xml_nfe criada';
    ELSE
        RAISE EXCEPTION '❌ ERRO: Tabela autorizacoes_xml_nfe não existe!';
    END IF;
    
    -- Verificar colunas em nfe_emitidas
    SELECT COUNT(*) INTO v_count 
    FROM information_schema.columns 
    WHERE table_name = 'nfe_emitidas' 
    AND column_name IN ('total_ibs', 'total_cbs', 'total_ibs_bc', 'valor_icms_st_retido');
    
    IF v_count = 4 THEN
        RAISE NOTICE '✅ Colunas IBS/CBS adicionadas em nfe_emitidas';
    ELSE
        RAISE EXCEPTION '❌ ERRO: Colunas IBS/CBS incompletas! Encontradas: %', v_count;
    END IF;
    
    -- Contar classificações
    SELECT COUNT(*) INTO v_count FROM classificacoes_ibs_cbs WHERE ativo = TRUE;
    RAISE NOTICE '✅ Total de % classificações IBS/CBS ativas', v_count;
    
    -- Verificar regimes
    SELECT COUNT(*) INTO v_count FROM regimes_tributarios WHERE crt = 1;
    RAISE NOTICE '✅ Total de % regime(s) Simples Nacional (CRT=1)', v_count;
    
    SELECT COUNT(*) INTO v_count FROM regimes_tributarios WHERE crt = 3;
    RAISE NOTICE '✅ Total de % regime(s) Lucro Real/Presumido (CRT=3)', v_count;
    
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Próximos passos:';
    RAISE NOTICE '1. Atualizar arquivos do sistema no servidor';
    RAISE NOTICE '2. Reiniciar serviço EmiteMax';
    RAISE NOTICE '3. Testar emissão com cliente Lucro Real/Presumido';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 7. ESTATÍSTICAS FINAIS
-- ============================================================================

SELECT 
    'regimes_tributarios' as tabela,
    nome as regime,
    crt,
    COUNT(*) OVER (PARTITION BY crt) as total_por_crt
FROM regimes_tributarios
ORDER BY crt, regime_tributario_id;

SELECT 
    'classificacoes_ibs_cbs' as tabela,
    COUNT(*) as total_classificacoes,
    COUNT(*) FILTER (WHERE ativo = TRUE) as ativas,
    COUNT(*) FILTER (WHERE ativo = FALSE) as inativas
FROM classificacoes_ibs_cbs;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================

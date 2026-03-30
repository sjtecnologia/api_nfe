-- ========================================
-- MIGRAÇÃO 001: Preparação para IBS/CBS - Versão Simplificada
-- Data: 17/11/2025
-- Objetivo: Criar estruturas básicas para Reforma Tributária (2026-2033)
-- Referência: Lei Complementar 214/2023 e Cartilha IBS FENACON
-- ========================================

-- 1. TABELA DE CÓDIGOS DE SERVIÇO (LC 116/2003)
CREATE TABLE IF NOT EXISTS codigos_servico (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    aliquota_padrao NUMERIC(5,2) DEFAULT 0.00,
    observacoes TEXT,
    vigencia_inicio DATE DEFAULT CURRENT_DATE,
    vigencia_fim DATE,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_codigos_servico_codigo ON codigos_servico(codigo);
CREATE INDEX IF NOT EXISTS idx_codigos_servico_ativo ON codigos_servico(ativo);

-- 2. TABELA DE ALÍQUOTAS IBS POR MUNICÍPIO
CREATE TABLE IF NOT EXISTS aliquotas_ibs_municipio (
    id SERIAL PRIMARY KEY,
    codigo_municipio VARCHAR(7) NOT NULL,
    nome_municipio VARCHAR(255) NOT NULL,
    uf VARCHAR(2) NOT NULL,
    aliquota_ibs NUMERIC(5,2) DEFAULT 0.00,
    aliquota_cbs NUMERIC(5,2) DEFAULT 0.00,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    observacoes TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aliquotas_ibs_codigo_municipio ON aliquotas_ibs_municipio(codigo_municipio);
CREATE INDEX IF NOT EXISTS idx_aliquotas_ibs_uf ON aliquotas_ibs_municipio(uf);
CREATE INDEX IF NOT EXISTS idx_aliquotas_ibs_vigencia ON aliquotas_ibs_municipio(vigencia_inicio, vigencia_fim);
CREATE INDEX IF NOT EXISTS idx_aliquotas_ibs_ativo ON aliquotas_ibs_municipio(ativo);

-- 3. TABELA DE HISTÓRICO DE CÁLCULO IBS
CREATE TABLE IF NOT EXISTS historico_calculo_ibs (
    id SERIAL PRIMARY KEY,
    nfe_id INTEGER,
    tipo_operacao VARCHAR(50),
    codigo_servico VARCHAR(10),
    valor_base NUMERIC(15,2),
    aliquota_ibs NUMERIC(5,2),
    valor_ibs NUMERIC(15,2),
    aliquota_cbs NUMERIC(5,2),
    valor_cbs NUMERIC(15,2),
    municipio_origem VARCHAR(7),
    municipio_destino VARCHAR(7),
    regime_tributario VARCHAR(50),
    observacoes TEXT,
    data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_historico_ibs_nfe ON historico_calculo_ibs(nfe_id);
CREATE INDEX IF NOT EXISTS idx_historico_ibs_data ON historico_calculo_ibs(data_calculo);
CREATE INDEX IF NOT EXISTS idx_historico_ibs_tipo ON historico_calculo_ibs(tipo_operacao);

-- Comentários
COMMENT ON TABLE codigos_servico IS 'Códigos de serviço LC 116/2003 para NFS-e';
COMMENT ON TABLE aliquotas_ibs_municipio IS 'Alíquotas IBS/CBS por município (Reforma Tributária)';
COMMENT ON TABLE historico_calculo_ibs IS 'Histórico de cálculos IBS/CBS para auditoria';

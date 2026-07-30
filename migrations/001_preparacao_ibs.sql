-- ========================================
-- MIGRAÇÃO 001: Preparação para IBS/CBS
-- Data: 17/11/2025
-- Objetivo: Criar estruturas básicas para Reforma Tributária (2026-2033)
-- Referência: Lei Complementar 214/2023 e Cartilha IBS FENACON
-- ========================================

-- ========================================
-- 1. TABELA DE CÓDIGOS DE SERVIÇO (LC 116/2003)
-- ========================================
-- Base para emissão de NFS-e com IBS
-- Códigos utilizados para classificar serviços (similar ao NCM para produtos)

CREATE TABLE IF NOT EXISTS codigos_servico (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE, -- Ex: 01.01, 01.02, 14.05
    descricao TEXT NOT NULL,
    item_lista VARCHAR(10), -- Referência ao item da lista LC 116/2003
    subitem VARCHAR(5), -- Subitem quando aplicável
    observacoes TEXT,
    aliquota_iss_padrao DECIMAL(5,2), -- Alíquota ISS padrão (referência histórica)
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX idx_codigos_servico_codigo ON codigos_servico(codigo);
CREATE INDEX idx_codigos_servico_ativo ON codigos_servico(ativo);
CREATE INDEX idx_codigos_servico_item_lista ON codigos_servico(item_lista);

-- Comentários para documentação
COMMENT ON TABLE codigos_servico IS 'Códigos de serviço conforme LC 116/2003 para classificação de NFS-e';
COMMENT ON COLUMN codigos_servico.codigo IS 'Código do serviço no formato XX.XX (ex: 01.01, 14.05)';
COMMENT ON COLUMN codigos_servico.descricao IS 'Descrição completa do serviço conforme lista oficial';
COMMENT ON COLUMN codigos_servico.aliquota_iss_padrao IS 'Alíquota ISS histórica (referência, não mais aplicável com IBS)';

-- ========================================
-- 2. TABELA DE ALÍQUOTAS IBS POR MUNICÍPIO
-- ========================================
-- Armazena alíquotas IBS que serão definidas por cada município (2026+)
-- Tabela preparada para receber dados quando regulamentação for publicada

CREATE TABLE IF NOT EXISTS aliquotas_ibs (
    id SERIAL PRIMARY KEY,
    codigo_municipio VARCHAR(7) NOT NULL, -- Código IBGE do município
    ano INTEGER NOT NULL, -- Ano de vigência da alíquota
    semestre INTEGER CHECK (semestre IN (1, 2)), -- Semestre se houver mudanças semestrais
    aliquota_ibs DECIMAL(5,2) NOT NULL, -- Alíquota IBS em percentual (ex: 25.00)
    aliquota_cbs DECIMAL(5,2), -- Alíquota CBS federal (pode ser única nacional)
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE, -- NULL se vigente indefinidamente
    observacoes TEXT,
    fonte_legal VARCHAR(255), -- Lei municipal que estabeleceu a alíquota
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_aliquotas_ibs_municipio 
        FOREIGN KEY (codigo_municipio) 
        REFERENCES municipios(codigo_municipio)
        ON DELETE RESTRICT
);

-- Índices para performance
CREATE INDEX idx_aliquotas_ibs_municipio ON aliquotas_ibs(codigo_municipio);
CREATE INDEX idx_aliquotas_ibs_vigencia ON aliquotas_ibs(vigencia_inicio, vigencia_fim);
CREATE INDEX idx_aliquotas_ibs_ano ON aliquotas_ibs(ano);
CREATE INDEX idx_aliquotas_ibs_ativo ON aliquotas_ibs(ativo);

-- Índice único para evitar duplicatas
CREATE UNIQUE INDEX idx_aliquotas_ibs_unique 
    ON aliquotas_ibs(codigo_municipio, ano, COALESCE(semestre, 0)) 
    WHERE ativo = TRUE;

-- Comentários para documentação
COMMENT ON TABLE aliquotas_ibs IS 'Alíquotas IBS e CBS por município conforme Reforma Tributária (LC 214/2023)';
COMMENT ON COLUMN aliquotas_ibs.aliquota_ibs IS 'Alíquota IBS definida pelo município em percentual';
COMMENT ON COLUMN aliquotas_ibs.aliquota_cbs IS 'Alíquota CBS federal (pode ser única nacional)';
COMMENT ON COLUMN aliquotas_ibs.vigencia_inicio IS 'Data de início de vigência da alíquota';
COMMENT ON COLUMN aliquotas_ibs.vigencia_fim IS 'Data de fim de vigência (NULL se vigente)';

-- ========================================
-- 3. ADICIONAR CAMPO TIPO_NOTA NA TABELA NFES
-- ========================================
-- Permite diferenciar entre NF-e (produtos) e NFS-e (serviços)

DO $$ 
BEGIN
    -- Verifica se a coluna já existe antes de adicionar
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'nfes' AND column_name = 'tipo_nota'
    ) THEN
        ALTER TABLE nfes ADD COLUMN tipo_nota VARCHAR(10) DEFAULT 'NFE' CHECK (tipo_nota IN ('NFE', 'NFSE'));
        
        COMMENT ON COLUMN nfes.tipo_nota IS 'Tipo de nota: NFE (produtos/mercadorias) ou NFSE (serviços)';
        
        -- Criar índice para filtros por tipo
        CREATE INDEX idx_nfes_tipo_nota ON nfes(tipo_nota);
        
        -- Atualizar registros existentes para NFE (padrão atual)
        UPDATE nfes SET tipo_nota = 'NFE' WHERE tipo_nota IS NULL;
    END IF;
END $$;

-- ========================================
-- 4. TABELA DE ITENS DE SERVIÇO (FUTURA NFS-E)
-- ========================================
-- Similar à tabela de itens de produtos, mas para serviços
-- Preparação para quando sistema emitir NFS-e

CREATE TABLE IF NOT EXISTS nfe_itens_servico (
    id SERIAL PRIMARY KEY,
    nfe_id INTEGER NOT NULL,
    codigo_servico_id INTEGER, -- FK para codigos_servico
    descricao TEXT NOT NULL,
    quantidade DECIMAL(15,4) DEFAULT 1,
    valor_unitario DECIMAL(15,2) NOT NULL,
    valor_total DECIMAL(15,2) NOT NULL,
    valor_desconto DECIMAL(15,2) DEFAULT 0,
    valor_ibs DECIMAL(15,2) DEFAULT 0, -- Valor IBS calculado
    valor_cbs DECIMAL(15,2) DEFAULT 0, -- Valor CBS calculado
    aliquota_ibs DECIMAL(5,2), -- Alíquota IBS aplicada
    aliquota_cbs DECIMAL(5,2), -- Alíquota CBS aplicada
    valor_credito_ibs DECIMAL(15,2) DEFAULT 0, -- Crédito IBS sobre insumos
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_itens_servico_nfe 
        FOREIGN KEY (nfe_id) 
        REFERENCES nfes(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_itens_servico_codigo 
        FOREIGN KEY (codigo_servico_id) 
        REFERENCES codigos_servico(id)
        ON DELETE SET NULL
);

-- Índices para performance
CREATE INDEX idx_nfe_itens_servico_nfe_id ON nfe_itens_servico(nfe_id);
CREATE INDEX idx_nfe_itens_servico_codigo ON nfe_itens_servico(codigo_servico_id);

-- Comentários para documentação
COMMENT ON TABLE nfe_itens_servico IS 'Itens de serviço para NFS-e com cálculos IBS/CBS';
COMMENT ON COLUMN nfe_itens_servico.valor_ibs IS 'Valor do IBS calculado sobre o serviço';
COMMENT ON COLUMN nfe_itens_servico.valor_cbs IS 'Valor do CBS calculado sobre o serviço';
COMMENT ON COLUMN nfe_itens_servico.valor_credito_ibs IS 'Crédito IBS de insumos (regime não-cumulativo)';

-- ========================================
-- 5. TABELA DE BENEFÍCIOS FISCAIS IBS
-- ========================================
-- Armazena benefícios fiscais (isenções, reduções) do IBS

CREATE TABLE IF NOT EXISTS beneficios_fiscais_ibs (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('ISENCAO', 'REDUCAO', 'DIFERIMENTO', 'SUSPENSAO')),
    percentual_reducao DECIMAL(5,2), -- % de redução quando tipo = 'REDUCAO'
    codigo_municipio VARCHAR(7), -- NULL = benefício federal
    codigo_servico VARCHAR(10), -- Código de serviço beneficiado
    requisitos TEXT, -- Requisitos para aplicação do benefício
    base_legal TEXT, -- Lei ou decreto que estabeleceu o benefício
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX idx_beneficios_ibs_codigo ON beneficios_fiscais_ibs(codigo);
CREATE INDEX idx_beneficios_ibs_tipo ON beneficios_fiscais_ibs(tipo);
CREATE INDEX idx_beneficios_ibs_municipio ON beneficios_fiscais_ibs(codigo_municipio);
CREATE INDEX idx_beneficios_ibs_vigencia ON beneficios_fiscais_ibs(vigencia_inicio, vigencia_fim);
CREATE INDEX idx_beneficios_ibs_ativo ON beneficios_fiscais_ibs(ativo);

-- Comentários para documentação
COMMENT ON TABLE beneficios_fiscais_ibs IS 'Benefícios fiscais IBS conforme LC 214/2023 e legislações municipais';
COMMENT ON COLUMN beneficios_fiscais_ibs.tipo IS 'Tipo: ISENCAO, REDUCAO, DIFERIMENTO ou SUSPENSAO';
COMMENT ON COLUMN beneficios_fiscais_ibs.percentual_reducao IS 'Percentual de redução quando tipo = REDUCAO';

-- ========================================
-- 6. TABELA DE HISTÓRICO DE CONVERSÃO TRIBUTÁRIA
-- ========================================
-- Registra conversão aproximada ICMS/IPI → IBS para análises históricas

CREATE TABLE IF NOT EXISTS conversao_tributaria_historica (
    id SERIAL PRIMARY KEY,
    nfe_id INTEGER NOT NULL,
    valor_icms_antigo DECIMAL(15,2),
    valor_ipi_antigo DECIMAL(15,2),
    valor_pis_antigo DECIMAL(15,2),
    valor_cofins_antigo DECIMAL(15,2),
    valor_ibs_estimado DECIMAL(15,2), -- Soma dos impostos antigos (aproximação)
    valor_cbs_estimado DECIMAL(15,2), -- Estimativa CBS (PIS+COFINS)
    metodo_conversao VARCHAR(50) DEFAULT 'SOMA_SIMPLES',
    observacao TEXT DEFAULT 'Conversão aproximada para fins de análise comparativa',
    data_conversao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_conversao_nfe 
        FOREIGN KEY (nfe_id) 
        REFERENCES nfes(id)
        ON DELETE CASCADE
);

-- Índices para performance
CREATE INDEX idx_conversao_nfe_id ON conversao_tributaria_historica(nfe_id);
CREATE INDEX idx_conversao_data ON conversao_tributaria_historica(data_conversao);

-- Comentários para documentação
COMMENT ON TABLE conversao_tributaria_historica IS 'Conversão aproximada de tributação antiga para IBS (fins analíticos)';
COMMENT ON COLUMN conversao_tributaria_historica.valor_ibs_estimado IS 'Estimativa IBS = ICMS + IPI (aproximação)';
COMMENT ON COLUMN conversao_tributaria_historica.valor_cbs_estimado IS 'Estimativa CBS = PIS + COFINS (aproximação)';

-- ========================================
-- 7. VIEW PARA RELATÓRIO COMPARATIVO
-- ========================================
-- View que facilita comparação tributação antiga vs IBS

CREATE OR REPLACE VIEW vw_comparativo_tributacao AS
SELECT 
    n.id AS nfe_id,
    n.numero,
    n.data_emissao,
    n.tipo_nota,
    c.nome_fantasia AS cliente,
    -- Tributação Antiga
    COALESCE(SUM(i.valor_icms), 0) AS total_icms,
    COALESCE(SUM(i.valor_ipi), 0) AS total_ipi,
    COALESCE(SUM(i.valor_pis), 0) AS total_pis,
    COALESCE(SUM(i.valor_cofins), 0) AS total_cofins,
    (COALESCE(SUM(i.valor_icms), 0) + 
     COALESCE(SUM(i.valor_ipi), 0) + 
     COALESCE(SUM(i.valor_pis), 0) + 
     COALESCE(SUM(i.valor_cofins), 0)) AS total_impostos_antigos,
    -- Tributação IBS (quando houver dados)
    COALESCE(SUM(s.valor_ibs), 0) AS total_ibs,
    COALESCE(SUM(s.valor_cbs), 0) AS total_cbs,
    (COALESCE(SUM(s.valor_ibs), 0) + 
     COALESCE(SUM(s.valor_cbs), 0)) AS total_impostos_ibs,
    -- Diferença
    ((COALESCE(SUM(s.valor_ibs), 0) + COALESCE(SUM(s.valor_cbs), 0)) - 
     (COALESCE(SUM(i.valor_icms), 0) + COALESCE(SUM(i.valor_ipi), 0) + 
      COALESCE(SUM(i.valor_pis), 0) + COALESCE(SUM(i.valor_cofins), 0))) AS diferenca_tributaria
FROM nfes n
INNER JOIN clientes c ON n.cliente_id = c.id
LEFT JOIN nfe_itens i ON n.id = i.nfe_id
LEFT JOIN nfe_itens_servico s ON n.id = s.nfe_id
GROUP BY n.id, n.numero, n.data_emissao, n.tipo_nota, c.nome_fantasia;

-- Comentário da view
COMMENT ON VIEW vw_comparativo_tributacao IS 'View para análise comparativa entre tributação antiga (ICMS/IPI/PIS/COFINS) e nova (IBS/CBS)';

-- ========================================
-- 8. FUNÇÃO PARA BUSCAR ALÍQUOTA IBS VIGENTE
-- ========================================
-- Função auxiliar para buscar alíquota IBS vigente de um município em uma data

CREATE OR REPLACE FUNCTION buscar_aliquota_ibs_vigente(
    p_codigo_municipio VARCHAR(7),
    p_data_referencia DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    aliquota_ibs DECIMAL(5,2),
    aliquota_cbs DECIMAL(5,2),
    vigencia_inicio DATE,
    vigencia_fim DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.aliquota_ibs,
        a.aliquota_cbs,
        a.vigencia_inicio,
        a.vigencia_fim
    FROM aliquotas_ibs a
    WHERE a.codigo_municipio = p_codigo_municipio
      AND a.ativo = TRUE
      AND a.vigencia_inicio <= p_data_referencia
      AND (a.vigencia_fim IS NULL OR a.vigencia_fim >= p_data_referencia)
    ORDER BY a.vigencia_inicio DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Comentário da função
COMMENT ON FUNCTION buscar_aliquota_ibs_vigente IS 'Retorna alíquota IBS/CBS vigente para um município em uma data específica';

-- ========================================
-- 9. TRIGGERS PARA ATUALIZAÇÃO AUTOMÁTICA
-- ========================================

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION atualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger nas tabelas
DROP TRIGGER IF EXISTS trigger_codigos_servico_updated ON codigos_servico;
CREATE TRIGGER trigger_codigos_servico_updated
    BEFORE UPDATE ON codigos_servico
    FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();

DROP TRIGGER IF EXISTS trigger_aliquotas_ibs_updated ON aliquotas_ibs;
CREATE TRIGGER trigger_aliquotas_ibs_updated
    BEFORE UPDATE ON aliquotas_ibs
    FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();

DROP TRIGGER IF EXISTS trigger_itens_servico_updated ON nfe_itens_servico;
CREATE TRIGGER trigger_itens_servico_updated
    BEFORE UPDATE ON nfe_itens_servico
    FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();

DROP TRIGGER IF EXISTS trigger_beneficios_ibs_updated ON beneficios_fiscais_ibs;
CREATE TRIGGER trigger_beneficios_ibs_updated
    BEFORE UPDATE ON beneficios_fiscais_ibs
    FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();

-- ========================================
-- 10. DADOS INICIAIS (PLACEHOLDERS)
-- ========================================

-- Inserir alíquota CBS federal padrão (placeholder - aguardando definição oficial)
-- Estimativa baseada em discussões: ~12% (pode mudar)
INSERT INTO aliquotas_ibs (
    codigo_municipio, 
    ano, 
    aliquota_ibs, 
    aliquota_cbs, 
    vigencia_inicio, 
    observacoes,
    fonte_legal,
    ativo
) 
SELECT 
    m.codigo_municipio,
    2026,
    0.00, -- Placeholder - aguardando definição
    12.00, -- CBS estimada federal (placeholder)
    '2026-01-01'::DATE,
    'Valores placeholder - aguardando regulamentação oficial',
    'LC 214/2023 (aguardando regulamentação)',
    FALSE -- Inativo até definição oficial
FROM municipios m
WHERE NOT EXISTS (
    SELECT 1 FROM aliquotas_ibs a 
    WHERE a.codigo_municipio = m.codigo_municipio 
    AND a.ano = 2026
);

-- ========================================
-- FIM DA MIGRAÇÃO 001
-- ========================================

-- Log de execução
DO $$
BEGIN
    RAISE NOTICE 'Migração 001 executada com sucesso em %', CURRENT_TIMESTAMP;
    RAISE NOTICE 'Estruturas IBS/CBS criadas e prontas para receber dados';
    RAISE NOTICE 'Próximos passos: Popular tabela codigos_servico com LC 116/2003';
END $$;

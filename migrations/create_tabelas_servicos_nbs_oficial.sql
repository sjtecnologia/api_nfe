-- ==================================================================
-- TABELAS OFICIAIS: CÓDIGOS DE SERVIÇO LC116 E NBS
-- Data: 30/01/2026
-- Fonte: Gov.br - NFS-e Nacional
-- ==================================================================

-- ================================================================== 
-- 1. TABELA: códigos_servico_lc116
-- Descrição: Lista Oficial de Serviços da Lei Complementar 116/2003
-- ==================================================================
CREATE TABLE IF NOT EXISTS codigos_servico_lc116 (
    codigo VARCHAR(10) PRIMARY KEY,  -- Ex: 1.01, 1.02, 14.05
    descricao TEXT NOT NULL,         -- Descrição completa do serviço
    item_pai VARCHAR(10),            -- Item superior na hierarquia (Ex: 1.02 tem pai 1)
    aliquota_maxima NUMERIC(5,2),    -- Alíquota máxima permitida (geralmente 5%)
    observacoes TEXT,                -- Observações e exceções
    ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_servico_lc116_descricao ON codigos_servico_lc116 USING gin(to_tsvector('portuguese', descricao));
CREATE INDEX IF NOT EXISTS idx_servico_lc116_ativo ON codigos_servico_lc116(ativo);

-- Comentários
COMMENT ON TABLE codigos_servico_lc116 IS 'Lista oficial de códigos de serviço da Lei Complementar 116/2003 (Lei do ISS)';
COMMENT ON COLUMN codigos_servico_lc116.codigo IS 'Código do serviço no formato X.YY (Ex: 1.01, 14.05)';
COMMENT ON COLUMN codigos_servico_lc116.item_pai IS 'Item superior na hierarquia. Ex: código 1.02 tem item_pai = 1';

-- ==================================================================
-- 2. TABELA: codigos_nbs
-- Descrição: Nomenclatura Brasileira de Serviços (NBS 2.0)
-- Fonte: https://www.gov.br/nfse/pt-br/mei-e-demais-empresas/codigos-de-tributacao-nacional-nbs
-- ==================================================================
CREATE TABLE IF NOT EXISTS codigos_nbs (
    codigo VARCHAR(12) PRIMARY KEY,  -- Ex: 1.0101.10.10, formato X.XXXX.XX.XX
    descricao TEXT NOT NULL,         -- Descrição completa do serviço NBS
    nivel INTEGER NOT NULL,          -- Nível hierárquico (1=Seção, 2=Grupo, 3=Subgrupo, 4=Item)
    codigo_pai VARCHAR(12),          -- Código NBS pai na hierarquia
    codigo_servico_lc116 VARCHAR(10), -- Relação com LC116 (quando aplicável)
    observacoes TEXT,                -- Notas técnicas e esclarecimentos
    ativo BOOLEAN DEFAULT TRUE,
    data_vigencia_inicio DATE,       -- Data de início de vigência
    data_vigencia_fim DATE,          -- Data de fim de vigência (NULL se ativo)
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key para relacionar com LC116
    CONSTRAINT fk_nbs_servico_lc116 FOREIGN KEY (codigo_servico_lc116) 
        REFERENCES codigos_servico_lc116(codigo) ON DELETE SET NULL
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_nbs_descricao ON codigos_nbs USING gin(to_tsvector('portuguese', descricao));
CREATE INDEX IF NOT EXISTS idx_nbs_nivel ON codigos_nbs(nivel);
CREATE INDEX IF NOT EXISTS idx_nbs_servico_lc116 ON codigos_nbs(codigo_servico_lc116);
CREATE INDEX IF NOT EXISTS idx_nbs_ativo ON codigos_nbs(ativo);
CREATE INDEX IF NOT EXISTS idx_nbs_vigencia ON codigos_nbs(data_vigencia_inicio, data_vigencia_fim);

-- Comentários
COMMENT ON TABLE codigos_nbs IS 'Nomenclatura Brasileira de Serviços (NBS 2.0) - Tabela oficial para NFS-e Nacional';
COMMENT ON COLUMN codigos_nbs.codigo IS 'Código NBS no formato X.XXXX.XX.XX (4 níveis hierárquicos)';
COMMENT ON COLUMN codigos_nbs.nivel IS '1=Seção, 2=Grupo, 3=Subgrupo, 4=Item (nível mais detalhado)';
COMMENT ON COLUMN codigos_nbs.codigo_servico_lc116 IS 'Relacionamento com código de serviço LC116 para ISS';

-- ==================================================================
-- 3. RELACIONAMENTO: servicos_lc116_nbs
-- Descrição: Tabela associativa entre LC116 e NBS (relação N:N)
-- ==================================================================
CREATE TABLE IF NOT EXISTS servicos_lc116_nbs (
    id SERIAL PRIMARY KEY,
    codigo_servico_lc116 VARCHAR(10) NOT NULL,
    codigo_nbs VARCHAR(12) NOT NULL,
    principal BOOLEAN DEFAULT FALSE,  -- Marca se é o NBS principal para este serviço
    observacoes TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    CONSTRAINT fk_lc116_nbs_servico FOREIGN KEY (codigo_servico_lc116) 
        REFERENCES codigos_servico_lc116(codigo) ON DELETE CASCADE,
    CONSTRAINT fk_lc116_nbs_nbs FOREIGN KEY (codigo_nbs) 
        REFERENCES codigos_nbs(codigo) ON DELETE CASCADE,
    
    -- Constraint única
    CONSTRAINT uk_lc116_nbs UNIQUE (codigo_servico_lc116, codigo_nbs)
);

-- Índice para consultas reversas
CREATE INDEX IF NOT EXISTS idx_lc116_nbs_servico ON servicos_lc116_nbs(codigo_servico_lc116);
CREATE INDEX IF NOT EXISTS idx_lc116_nbs_nbs ON servicos_lc116_nbs(codigo_nbs);

COMMENT ON TABLE servicos_lc116_nbs IS 'Relacionamento N:N entre códigos de serviço LC116 e códigos NBS';
COMMENT ON COLUMN servicos_lc116_nbs.principal IS 'Indica se este é o código NBS principal recomendado para o serviço LC116';

-- ==================================================================
-- 4. INSERÇÃO INICIAL: Códigos de Serviço LC116 (Amostra)
-- ==================================================================

-- SEÇÃO 1: SERVIÇOS DE INFORMÁTICA E CONGÊNERES
INSERT INTO codigos_servico_lc116 (codigo, descricao, item_pai, aliquota_maxima, observacoes) VALUES
('1', 'Serviços de informática e congêneres', NULL, 5.00, 'Seção principal - Serviços de TI'),
('1.01', 'Análise e desenvolvimento de sistemas', '1', 5.00, 'Inclui consultoria, análise, programação'),
('1.02', 'Programação', '1', 5.00, 'Desenvolvimento de software sob demanda'),
('1.03', 'Processamento de dados e congêneres', '1', 5.00, 'Processamento, armazenamento de dados'),
('1.04', 'Elaboração de programas de computadores, inclusive de jogos eletrônicos', '1', 5.00, 'Desenvolvimento de software'),
('1.05', 'Licenciamento ou cessão de direito de uso de programas de computação', '1', 5.00, 'Licenças de software'),
('1.06', 'Assessoria e consultoria em informática', '1', 5.00, 'Consultoria técnica em TI'),
('1.07', 'Suporte técnico em informática, inclusive instalação, configuração e manutenção de programas de computação e bancos de dados', '1', 5.00, 'Suporte e manutenção'),
('1.08', 'Planejamento, confecção, manutenção e atualização de páginas eletrônicas', '1', 5.00, 'Desenvolvimento web'),
('1.09', 'Disponibilização, sem cessão definitiva, de conteúdos de áudio, vídeo, imagem e texto por meio da internet', '1', 5.00, 'Streaming e conteúdo digital')
ON CONFLICT (codigo) DO NOTHING;

-- SEÇÃO 3: SERVIÇOS PRESTADOS MEDIANTE LOCAÇÃO, CESSÃO DE DIREITO DE USO E CONGÊNERES
INSERT INTO codigos_servico_lc116 (codigo, descricao, item_pai, aliquota_maxima, observacoes) VALUES
('3', 'Serviços prestados mediante locação, cessão de direito de uso e congêneres', NULL, 5.00, 'Seção principal - Locação de bens'),
('3.01', 'Locação de bens móveis', '3', 5.00, 'Locação de máquinas, equipamentos'),
('3.02', 'Cessão de direito de uso de marcas e de sinais de propaganda', '3', 5.00, 'Licenciamento de marcas'),
('3.03', 'Exploração de salões de festas, centro de convenções, escritórios virtuais, stands, quadras esportivas, estádios, ginásios, auditórios, casas de espetáculos, parques de diversões, canchas e congêneres', '3', 5.00, 'Locação de espaços para eventos')
ON CONFLICT (codigo) DO NOTHING;

-- SEÇÃO 14: SERVIÇOS RELATIVOS A BENS DE TERCEIROS
INSERT INTO codigos_servico_lc116 (codigo, descricao, item_pai, aliquota_maxima, observacoes) VALUES
('14', 'Serviços relativos a bens de terceiros', NULL, 5.00, 'Seção principal - Serviços sobre bens'),
('14.01', 'Lubrificação, limpeza, lustração, revisão, carga e recarga, conserto, restauração, blindagem, manutenção e conservação de máquinas, veículos, aparelhos, equipamentos, motores, elevadores ou de qualquer objeto', '14', 5.00, 'Manutenção em geral'),
('14.02', 'Assistência técnica', '14', 5.00, 'Serviços de assistência técnica'),
('14.03', 'Recondicionamento de motores', '14', 5.00, 'Reforma de motores'),
('14.04', 'Recauchutagem ou regeneração de pneus', '14', 5.00, 'Recauchutagem'),
('14.05', 'Restauração, recondicionamento, acondicionamento, pintura, beneficiamento, lavagem, secagem, tingimento, galvanoplastia, anodização, corte, recorte, polimento, plastificação e congêneres, de objetos quaisquer', '14', 5.00, 'Serviços de beneficiamento')
ON CONFLICT (codigo) DO NOTHING;

-- ==================================================================
-- 5. INSERÇÃO INICIAL: Códigos NBS (Amostra - Seção 1)
-- Fonte: Anexo I - NBS 2.0 com alterações de 06/12/2018
-- ==================================================================

-- NÍVEL 1: SEÇÕES (Primeiro dígito)
INSERT INTO codigos_nbs (codigo, descricao, nivel, codigo_pai, codigo_servico_lc116) VALUES
('1', 'Serviços de tecnologia da informação', 1, NULL, '1')
ON CONFLICT (codigo) DO NOTHING;

-- NÍVEL 2: GRUPOS (Quatro primeiros dígitos)
INSERT INTO codigos_nbs (codigo, descricao, nivel, codigo_pai, codigo_servico_lc116) VALUES
('1.0100', 'Serviços de desenvolvimento de sistemas e software', 2, '1', '1'),
('1.0200', 'Serviços de consultoria em tecnologia da informação', 2, '1', '1'),
('1.0300', 'Serviços de suporte técnico', 2, '1', '1'),
('1.0400', 'Serviços de processamento de dados', 2, '1', '1'),
('1.0700', 'Serviços de hospedagem na internet e outros serviços relacionados', 2, '1', '1')
ON CONFLICT (codigo) DO NOTHING;

-- NÍVEL 3: SUBGRUPOS (Seis primeiros dígitos)
INSERT INTO codigos_nbs (codigo, descricao, nivel, codigo_pai, codigo_servico_lc116) VALUES
('1.0101', 'Serviços de análise de negócios', 3, '1.0100', '1.01'),
('1.0102', 'Serviços de programação de computadores', 3, '1.0100', '1.02'),
('1.0103', 'Serviços de desenvolvimento de aplicativos', 3, '1.0100', '1.04'),
('1.0701', 'Serviços de hospedagem de sítios na internet (web hosting)', 3, '1.0700', '1.08')
ON CONFLICT (codigo) DO NOTHING;

-- NÍVEL 4: ITENS (Código completo - 10 dígitos)
INSERT INTO codigos_nbs (codigo, descricao, nivel, codigo_pai, codigo_servico_lc116) VALUES
('1.0101.10.00', 'Serviços de análise de sistemas de tecnologia da informação', 4, '1.0101', '1.01'),
('1.0101.20.00', 'Serviços de projeto de sistemas de tecnologia da informação', 4, '1.0101', '1.01'),
('1.0102.10.00', 'Serviços de programação de aplicativos', 4, '1.0102', '1.02'),
('1.0102.20.00', 'Serviços de programação de páginas web', 4, '1.0102', '1.08'),
('1.0103.10.00', 'Serviços de desenvolvimento de aplicativos customizados', 4, '1.0103', '1.04'),
('1.0103.20.00', 'Serviços de desenvolvimento de jogos eletrônicos', 4, '1.0103', '1.04'),
('1.0701.00.00', 'Serviços de hospedagem de sítios na internet (web hosting)', 4, '1.0701', '1.08')
ON CONFLICT (codigo) DO NOTHING;

-- ==================================================================
-- 6. VIEWS AUXILIARES: Consultas facilitadas
-- ==================================================================

-- View para buscar NBS por serviço LC116
CREATE OR REPLACE VIEW vw_servicos_com_nbs AS
SELECT 
    s.codigo AS codigo_servico,
    s.descricao AS descricao_servico,
    n.codigo AS codigo_nbs,
    n.descricao AS descricao_nbs,
    n.nivel AS nivel_nbs
FROM codigos_servico_lc116 s
LEFT JOIN codigos_nbs n ON n.codigo_servico_lc116 = s.codigo
WHERE s.ativo = TRUE AND (n.ativo = TRUE OR n.ativo IS NULL)
ORDER BY s.codigo, n.codigo;

-- View para hierarquia NBS completa
CREATE OR REPLACE VIEW vw_hierarquia_nbs AS
WITH RECURSIVE hierarquia AS (
    -- Nível 1: Seções
    SELECT 
        codigo,
        descricao,
        nivel,
        codigo_pai,
        codigo AS caminho,
        descricao AS caminho_descricao
    FROM codigos_nbs
    WHERE nivel = 1 AND ativo = TRUE
    
    UNION ALL
    
    -- Níveis inferiores
    SELECT 
        n.codigo,
        n.descricao,
        n.nivel,
        n.codigo_pai,
        h.caminho || ' > ' || n.codigo,
        h.caminho_descricao || ' > ' || n.descricao
    FROM codigos_nbs n
    INNER JOIN hierarquia h ON n.codigo_pai = h.codigo
    WHERE n.ativo = TRUE
)
SELECT * FROM hierarquia
ORDER BY caminho;

COMMENT ON VIEW vw_servicos_com_nbs IS 'Relacionamento entre códigos de serviço LC116 e seus códigos NBS correspondentes';
COMMENT ON VIEW vw_hierarquia_nbs IS 'Hierarquia completa da estrutura NBS (Seção > Grupo > Subgrupo > Item)';

-- ==================================================================
-- 7. FUNÇÃO: Buscar NBS por palavra-chave
-- ==================================================================
CREATE OR REPLACE FUNCTION buscar_nbs_por_palavra_chave(palavra_chave TEXT)
RETURNS TABLE (
    codigo VARCHAR(12),
    descricao TEXT,
    nivel INTEGER,
    codigo_servico_lc116 VARCHAR(10),
    relevancia REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        n.codigo,
        n.descricao,
        n.nivel,
        n.codigo_servico_lc116,
        ts_rank(to_tsvector('portuguese', n.descricao), plainto_tsquery('portuguese', palavra_chave)) AS relevancia
    FROM codigos_nbs n
    WHERE n.ativo = TRUE
    AND to_tsvector('portuguese', n.descricao) @@ plainto_tsquery('portuguese', palavra_chave)
    ORDER BY relevancia DESC, n.codigo
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION buscar_nbs_por_palavra_chave IS 'Busca full-text em códigos NBS por palavra-chave, retorna top 20 mais relevantes';

-- ==================================================================
-- FIM DO SCRIPT
-- ==================================================================

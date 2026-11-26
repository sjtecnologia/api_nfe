--
-- Migration: Tabela NBS (Nomenclatura Brasileira de Serviços)
-- Data: 09/02/2026
-- Referência: NT007 v1.03.00 - Código NBS obrigatório
--

BEGIN;

-- =============================================================================
-- TABELA: Nomenclatura Brasileira de Serviços (NBS)
-- =============================================================================

CREATE TABLE IF NOT EXISTS nomenclatura_brasileira_servicos (
    codigo_nbs VARCHAR(9) PRIMARY KEY,
    descricao TEXT NOT NULL,
    codigo_lc116 VARCHAR(5), -- Correlação com LC 116/2003
    categoria VARCHAR(100),
    subcategoria VARCHAR(100),
    palavras_chave TEXT, -- Para busca textual
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comentários
COMMENT ON TABLE nomenclatura_brasileira_servicos IS 'Nomenclatura Brasileira de Serviços - Códigos oficiais NBS';
COMMENT ON COLUMN nomenclatura_brasileira_servicos.codigo_nbs IS 'Código NBS (9 dígitos sem pontos)';
COMMENT ON COLUMN nomenclatura_brasileira_servicos.codigo_lc116 IS 'Código da Lista de Serviços LC 116/2003 correlacionado';
COMMENT ON COLUMN nomenclatura_brasileira_servicos.palavras_chave IS 'Palavras-chave para facilitar busca';

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_nbs_codigo_lc116 ON nomenclatura_brasileira_servicos(codigo_lc116);
CREATE INDEX IF NOT EXISTS idx_nbs_categoria ON nomenclatura_brasileira_servicos(categoria);
CREATE INDEX IF NOT EXISTS idx_nbs_subcategoria ON nomenclatura_brasileira_servicos(subcategoria);
CREATE INDEX IF NOT EXISTS idx_nbs_ativo ON nomenclatura_brasileira_servicos(ativo);

-- Índice para busca textual (Full-Text Search)
CREATE INDEX IF NOT EXISTS idx_nbs_descricao_gin ON nomenclatura_brasileira_servicos 
    USING gin(to_tsvector('portuguese', descricao));
CREATE INDEX IF NOT EXISTS idx_nbs_palavras_chave_gin ON nomenclatura_brasileira_servicos 
    USING gin(to_tsvector('portuguese', COALESCE(palavras_chave, '')));

-- =============================================================================
-- POPULAR COM DADOS BÁSICOS (Códigos mais comuns)
-- =============================================================================

INSERT INTO nomenclatura_brasileira_servicos (codigo_nbs, descricao, codigo_lc116, categoria, subcategoria, palavras_chave) VALUES

-- 01 - SERVIÇOS DE INFORMÁTICA E CORRELATOS (LC 116 - 1.01 a 1.09)
('101010000', 'Análise e desenvolvimento de sistemas', '01.01', 'Informática', 'Análise de Sistemas', 'analise desenvolvimento sistemas software aplicativo'),
('101020000', 'Programação', '01.02', 'Informática', 'Programação', 'programacao codigo desenvolvimento software'),
('101030000', 'Processamento de dados e congêneres', '01.03', 'Informática', 'Processamento de Dados', 'processamento dados informacao banco'),
('101040000', 'Elaboração de programas de computadores, inclusive de jogos eletrônicos', '01.04', 'Informática', 'Desenvolvimento', 'programa software aplicativo jogo game'),
('101050000', 'Licenciamento ou cessão de direito de uso de programas de computação', '01.05', 'Informática', 'Licenciamento', 'licenca software uso cessao direito'),
('101060000', 'Assessoria e consultoria em informática', '01.06', 'Informática', 'Consultoria', 'assessoria consultoria ti tecnologia'),
('101070000', 'Suporte técnico em informática, inclusive instalação, configuração e manutenção de programas', '01.07', 'Informática', 'Suporte Técnico', 'suporte tecnico manutencao instalacao'),
('101080000', 'Planejamento, confecção, manutenção e atualização de páginas eletrônicas', '01.08', 'Informática', 'Web Design', 'web site pagina internet homepage'),
('101090000', 'Disponibilização, sem cessão definitiva, de conteúdos de áudio, vídeo, imagem e texto', '01.09', 'Informática', 'Conteúdo Digital', 'streaming audio video conteudo digital'),

-- 07 - SERVIÇOS RELATIVOS A ENGENHARIA, ARQUITETURA E AFINS (LC 116 - 7.01 a 7.22)
('107010000', 'Engenharia, agronomia, agrimensura, arquitetura, geologia, urbanismo, paisagismo e congêneres', '07.01', 'Engenharia', 'Projetos', 'engenharia projeto arquitetura construcao'),
('107020000', 'Execução, por administração, empreitada ou subempreitada, de obras de construção civil', '07.02', 'Construção Civil', 'Execução de Obras', 'construcao obra civil edificacao'),
('107030000', 'Elaboração de planos diretores, estudos de viabilidade, estudos organizacionais e outros', '07.03', 'Engenharia', 'Estudos e Projetos', 'plano estudo viabilidade projeto'),
('107040000', 'Demolição', '07.04', 'Construção Civil', 'Demolição', 'demolicao derrubada edificacao'),
('107050000', 'Reparação, conservação e reforma de edifícios, estradas, pontes, portos e congêneres', '07.05', 'Construção Civil', 'Reforma e Manutenção', 'reforma manutencao reparo conservacao'),
('107060000', 'Colocação e instalação de tapetes, carpetes, assoalhos, cortinas, revestimentos de parede', '07.06', 'Construção Civil', 'Acabamento', 'instalacao tapete carpete piso'),
('107070000', 'Recuperação, raspagem, polimento e lustração de pisos e congêneres', '07.07', 'Construção Civil', 'Tratamento de Pisos', 'piso polimento lustração raspagem'),

-- 10 - SERVIÇOS DE DIVERSÕES, LAZER, ENTRETENIMENTO E CONGÊNERES
('110010000', 'Espetáculos teatrais', '10.01', 'Entretenimento', 'Teatro', 'teatro espetaculo apresentacao'),
('110020000', 'Exibições cinematográficas', '10.02', 'Entretenimento', 'Cinema', 'cinema filme exibicao'),
('110030000', 'Espetáculos circenses', '10.03', 'Entretenimento', 'Circo', 'circo espetaculo apresentacao'),

-- 17 - SERVIÇOS DE APOIO TÉCNICO, ADMINISTRATIVO, JURÍDICO, CONTÁBIL E SIMILARES (LC 116 - 17.01 a 17.25)
('117010000', 'Assessoria ou consultoria de qualquer natureza, não contida em outros itens', '17.01', 'Consultoria', 'Assessoria Geral', 'assessoria consultoria apoio'),
('117020000', 'Datilografia, digitação, estenografia, expediente, secretaria em geral, resposta audível', '17.02', 'Serviços Administrativos', 'Secretaria', 'digitacao secretaria expediente'),
('117030000', 'Planejamento, coordenação, programação ou organização técnica, financeira ou administrativa', '17.03', 'Consultoria', 'Planejamento', 'planejamento organizacao coordenacao'),
('117040000', 'Recrutamento, agenciamento, seleção e colocação de mão-de-obra', '17.04', 'Recursos Humanos', 'Recrutamento', 'recrutamento selecao rh vagas'),
('117050000', 'Fornecimento de mão-de-obra, mesmo em caráter temporário, inclusive de empregados', '17.05', 'Recursos Humanos', 'Mão de Obra', 'temporario mao obra pessoal'),
('117060000', 'Propaganda e publicidade, inclusive promoção de vendas, planejamento de campanhas', '17.06', 'Marketing', 'Publicidade', 'propaganda publicidade marketing campanha'),

-- 25 - SERVIÇOS FUNERÁRIOS
('125010000', 'Funerais, inclusive fornecimento de caixão, urna ou esquifes; aluguel de capela', '25.01', 'Serviços Funerários', 'Funerais', 'funeral cemiterio velorio'),

-- 40 - EDUCAÇÃO, ENSINO, ORIENTAÇÃO PEDAGÓGICA E EDUCACIONAL
('140010000', 'Ensino regular pré-escolar, fundamental, médio e superior', '40.01', 'Educação', 'Ensino Regular', 'ensino escola educacao aula'),
('140020000', 'Instrução, treinamento, orientação pedagógica e educacional, avaliação de conhecimentos', '40.02', 'Educação', 'Treinamento', 'treinamento curso capacitacao')

ON CONFLICT (codigo_nbs) DO NOTHING;

-- =============================================================================
-- CONSTRAINTS E VALIDAÇÕES
-- =============================================================================

-- Validar formato do código NBS (9 dígitos)
ALTER TABLE nomenclatura_brasileira_servicos 
    ADD CONSTRAINT chk_nbs_codigo_formato 
    CHECK (codigo_nbs ~ '^[0-9]{9}$');

-- Validar formato do código LC 116 quando informado
ALTER TABLE nomenclatura_brasileira_servicos 
    ADD CONSTRAINT chk_nbs_lc116_formato 
    CHECK (codigo_lc116 IS NULL OR codigo_lc116 ~ '^[0-9]{2}\.[0-9]{2}$');

-- =============================================================================
-- TRIGGER PARA UPDATED_AT
-- =============================================================================

DROP TRIGGER IF EXISTS update_nbs_updated_at ON nomenclatura_brasileira_servicos;
CREATE TRIGGER update_nbs_updated_at 
    BEFORE UPDATE ON nomenclatura_brasileira_servicos 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEW PARA BUSCA FACILITADA
-- =============================================================================

CREATE OR REPLACE VIEW vw_nbs_busca AS
SELECT 
    codigo_nbs,
    descricao,
    codigo_lc116,
    categoria,
    subcategoria,
    CONCAT(codigo_nbs, ' - ', descricao) AS descricao_completa,
    COALESCE(palavras_chave, '') AS palavras_chave
FROM nomenclatura_brasileira_servicos
WHERE ativo = TRUE
ORDER BY categoria, subcategoria, codigo_nbs;

COMMENT ON VIEW vw_nbs_busca IS 'View para facilitar busca de códigos NBS no formulário';

COMMIT;

-- =============================================================================
-- FUNÇÃO DE BUSCA DE NBS
-- =============================================================================

CREATE OR REPLACE FUNCTION buscar_nbs(
    p_termo TEXT,
    p_limite INTEGER DEFAULT 20
)
RETURNS TABLE (
    codigo_nbs VARCHAR(9),
    descricao TEXT,
    codigo_lc116 VARCHAR(5),
    categoria VARCHAR(100),
    relevancia REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        n.codigo_nbs,
        n.descricao,
        n.codigo_lc116,
        n.categoria,
        ts_rank(
            to_tsvector('portuguese', n.descricao || ' ' || COALESCE(n.palavras_chave, '')),
            plainto_tsquery('portuguese', p_termo)
        ) AS relevancia
    FROM nomenclatura_brasileira_servicos n
    WHERE 
        n.ativo = TRUE
        AND (
            n.codigo_nbs ILIKE '%' || p_termo || '%'
            OR n.descricao ILIKE '%' || p_termo || '%'
            OR n.codigo_lc116 ILIKE '%' || p_termo || '%'
            OR n.palavras_chave ILIKE '%' || p_termo || '%'
            OR to_tsvector('portuguese', n.descricao || ' ' || COALESCE(n.palavras_chave, '')) 
               @@ plainto_tsquery('portuguese', p_termo)
        )
    ORDER BY relevancia DESC, n.categoria, n.codigo_nbs
    LIMIT p_limite;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION buscar_nbs IS 'Busca códigos NBS por termo (código, descrição ou palavras-chave)';

-- =============================================================================
-- FIM DA MIGRATION
-- =============================================================================

DO $$
DECLARE
    v_count_nbs INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count_nbs FROM nomenclatura_brasileira_servicos;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRATION NBS CONCLUÍDA COM SUCESSO!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Estruturas criadas:';
    RAISE NOTICE '  ✓ Tabela nomenclatura_brasileira_servicos (% registros)', v_count_nbs;
    RAISE NOTICE '  ✓ View vw_nbs_busca';
    RAISE NOTICE '  ✓ Função buscar_nbs()';
    RAISE NOTICE '';
    RAISE NOTICE 'Índices criados:';
    RAISE NOTICE '  ✓ idx_nbs_codigo_lc116';
    RAISE NOTICE '  ✓ idx_nbs_categoria';
    RAISE NOTICE '  ✓ idx_nbs_descricao_gin (Full-Text Search)';
    RAISE NOTICE '  ✓ idx_nbs_palavras_chave_gin';
    RAISE NOTICE '';
    RAISE NOTICE 'Para popular com lista completa:';
    RAISE NOTICE '  - Importar arquivo CSV oficial da RFB';
    RAISE NOTICE '  - Usar script popular_nbs_completo.py';
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
END $$;

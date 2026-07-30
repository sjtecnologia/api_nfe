-- Tabela para rastrear sugestões da IA
-- Permite analytics sobre uso e efetividade do sistema de IA

CREATE TABLE IF NOT EXISTS sugestoes_ia (
    sugestao_id SERIAL PRIMARY KEY,
    produto_id INTEGER REFERENCES produtos(produto_id) ON DELETE CASCADE,
    cliente_id INTEGER REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    
    -- Dados da sugestão
    descricao_produto TEXT NOT NULL,
    ncm_sugerido VARCHAR(10),
    ncm_confianca DECIMAL(5,2),
    cest_sugerido VARCHAR(10),
    cest_confianca DECIMAL(5,2),
    cst_sugerido VARCHAR(5),
    csosn_sugerido VARCHAR(5),
    cfop_sugerido VARCHAR(5),
    
    -- Se o usuário aceitou ou não
    sugestao_aceita BOOLEAN DEFAULT NULL,  -- NULL = não decidiu ainda
    
    -- Metadados
    data_sugestao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tempo_resposta_ms INTEGER,  -- Tempo que a IA levou
    
    -- Índices para performance
    INDEX idx_sugestoes_produto (produto_id),
    INDEX idx_sugestoes_cliente (cliente_id),
    INDEX idx_sugestoes_data (data_sugestao)
);

-- Comentários da tabela
COMMENT ON TABLE sugestoes_ia IS 'Rastreamento de sugestões da IA para analytics e métricas';
COMMENT ON COLUMN sugestoes_ia.sugestao_aceita IS 'NULL = não decidiu, TRUE = aceita, FALSE = rejeitada';
COMMENT ON COLUMN sugestoes_ia.tempo_resposta_ms IS 'Tempo de resposta da IA em milissegundos';

-- =====================================================
-- MIGRAÇÃO: Sistema de Faturamento e Cobrança
-- Data: 2025-11-18
-- Descrição: Tabelas para controle de preços, faturamento
--            e extratos de cobrança por cliente
-- =====================================================

-- Tabela de configuração de faturamento por cliente
CREATE TABLE IF NOT EXISTS cliente_configuracao_faturamento (
    config_faturamento_id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    
    -- Valores e forma de pagamento
    valor_por_nfe NUMERIC(10, 2) NOT NULL DEFAULT 0.50,
    forma_pagamento VARCHAR(50) DEFAULT 'boleto' CHECK (forma_pagamento IN ('boleto', 'pix', 'cartao_credito', 'debito_automatico', 'transferencia')),
    
    -- Ciclo de cobrança
    dia_vencimento INTEGER DEFAULT 10 CHECK (dia_vencimento BETWEEN 1 AND 28),
    periodicidade VARCHAR(20) DEFAULT 'mensal' CHECK (periodicidade IN ('mensal', 'quinzenal', 'trimestral')),
    
    -- Controles
    ativo BOOLEAN DEFAULT TRUE,
    inicio_vigencia DATE DEFAULT CURRENT_DATE,
    fim_vigencia DATE,
    
    -- Observações e metadados
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id),
    
    -- Garantir apenas uma configuração ativa por cliente
    CONSTRAINT unique_cliente_config UNIQUE (cliente_id)
);

-- Tabela de histórico de faturamento mensal
CREATE TABLE IF NOT EXISTS faturamento_mensal (
    faturamento_id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    
    -- Período
    mes_referencia INTEGER NOT NULL CHECK (mes_referencia BETWEEN 1 AND 12),
    ano_referencia INTEGER NOT NULL CHECK (ano_referencia >= 2024),
    
    -- Cálculos
    quantidade_nfes INTEGER DEFAULT 0,
    valor_unitario NUMERIC(10, 2) NOT NULL,
    valor_total NUMERIC(10, 2) NOT NULL,
    
    -- Status de pagamento
    status_pagamento VARCHAR(30) DEFAULT 'pendente' CHECK (status_pagamento IN ('pendente', 'pago', 'vencido', 'cancelado', 'isento')),
    data_vencimento DATE NOT NULL,
    data_pagamento DATE,
    
    -- Forma de pagamento e comprovante
    forma_pagamento VARCHAR(50),
    comprovante_pagamento TEXT, -- URL ou referência do comprovante
    
    -- Observações
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Evitar duplicatas
    CONSTRAINT unique_mes_ano_cliente UNIQUE (cliente_id, mes_referencia, ano_referencia)
);

-- Tabela de log de extratos gerados
CREATE TABLE IF NOT EXISTS extrato_faturamento_log (
    log_id SERIAL PRIMARY KEY,
    faturamento_id INTEGER REFERENCES faturamento_mensal(faturamento_id) ON DELETE CASCADE,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    
    -- Informações do extrato
    tipo_extrato VARCHAR(30) DEFAULT 'mensal' CHECK (tipo_extrato IN ('mensal', 'trimestral', 'anual', 'customizado')),
    data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    gerado_por_user_id INTEGER REFERENCES users(id),
    
    -- Formato e envio
    formato VARCHAR(10) DEFAULT 'pdf' CHECK (formato IN ('pdf', 'html', 'excel', 'csv')),
    enviado_email BOOLEAN DEFAULT FALSE,
    email_destinatario VARCHAR(255),
    data_envio TIMESTAMP,
    
    -- Armazenamento
    caminho_arquivo TEXT,
    hash_arquivo VARCHAR(64), -- SHA256 do arquivo gerado
    
    observacoes TEXT
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_config_faturamento_cliente ON cliente_configuracao_faturamento(cliente_id, ativo);
CREATE INDEX IF NOT EXISTS idx_faturamento_periodo ON faturamento_mensal(ano_referencia DESC, mes_referencia DESC);
CREATE INDEX IF NOT EXISTS idx_faturamento_status ON faturamento_mensal(status_pagamento);
CREATE INDEX IF NOT EXISTS idx_faturamento_vencimento ON faturamento_mensal(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_extrato_data ON extrato_faturamento_log(data_geracao DESC);

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_faturamento_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_config_faturamento
    BEFORE UPDATE ON cliente_configuracao_faturamento
    FOR EACH ROW
    EXECUTE FUNCTION update_faturamento_timestamp();

CREATE TRIGGER trigger_update_faturamento_mensal
    BEFORE UPDATE ON faturamento_mensal
    FOR EACH ROW
    EXECUTE FUNCTION update_faturamento_timestamp();

-- View para resumo de faturamento por cliente
CREATE OR REPLACE VIEW vw_resumo_faturamento_cliente AS
SELECT 
    c.cliente_id,
    c.razao_social,
    c.cnpj,
    cfg.valor_por_nfe,
    cfg.forma_pagamento,
    cfg.dia_vencimento,
    cfg.ativo as config_ativa,
    COUNT(DISTINCT fm.faturamento_id) as total_faturas,
    COUNT(DISTINCT CASE WHEN fm.status_pagamento = 'pago' THEN fm.faturamento_id END) as faturas_pagas,
    COUNT(DISTINCT CASE WHEN fm.status_pagamento = 'pendente' THEN fm.faturamento_id END) as faturas_pendentes,
    COUNT(DISTINCT CASE WHEN fm.status_pagamento = 'vencido' THEN fm.faturamento_id END) as faturas_vencidas,
    COALESCE(SUM(fm.valor_total), 0) as valor_total_faturado,
    COALESCE(SUM(CASE WHEN fm.status_pagamento = 'pago' THEN fm.valor_total ELSE 0 END), 0) as valor_total_pago,
    COALESCE(SUM(CASE WHEN fm.status_pagamento IN ('pendente', 'vencido') THEN fm.valor_total ELSE 0 END), 0) as valor_total_pendente
FROM clientes c
LEFT JOIN cliente_configuracao_faturamento cfg ON c.cliente_id = cfg.cliente_id
LEFT JOIN faturamento_mensal fm ON c.cliente_id = fm.cliente_id
GROUP BY c.cliente_id, c.razao_social, c.cnpj, cfg.valor_por_nfe, cfg.forma_pagamento, cfg.dia_vencimento, cfg.ativo;

-- Comentários para documentação
COMMENT ON TABLE cliente_configuracao_faturamento IS 'Configuração de preços e formas de pagamento por cliente';
COMMENT ON TABLE faturamento_mensal IS 'Registro de faturamento mensal consolidado por cliente';
COMMENT ON TABLE extrato_faturamento_log IS 'Log de extratos gerados e enviados aos clientes';
COMMENT ON VIEW vw_resumo_faturamento_cliente IS 'View com resumo consolidado de faturamento por cliente';

-- Inserir configuração padrão para clientes existentes (opcional)
-- INSERT INTO cliente_configuracao_faturamento (cliente_id, valor_por_nfe, forma_pagamento, dia_vencimento, created_by_user_id)
-- SELECT cliente_id, 0.50, 'boleto', 10, 1 
-- FROM clientes 
-- WHERE ativo = TRUE 
-- ON CONFLICT (cliente_id) DO NOTHING;

-- =====================================================
-- FIM DA MIGRAÇÃO
-- =====================================================

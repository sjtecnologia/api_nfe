-- Migration: Sistema de Planos e Assinaturas para NFe
-- Data: 2025-12-10
-- Descrição: Criar tabelas para gerenciar planos de cobrança (avulso e pacotes)

-- 1. Tabela de Planos (Pacotes disponíveis)
CREATE TABLE IF NOT EXISTS planos_nfe (
    plano_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    tipo_plano VARCHAR(20) NOT NULL, -- 'AVULSO' ou 'PACOTE'
    quantidade_nfes INTEGER, -- NULL para avulso, valor para pacotes
    valor_mensal NUMERIC(10, 2) NOT NULL,
    valor_por_nfe NUMERIC(10, 2), -- Valor unitário no caso de avulso
    ativo BOOLEAN DEFAULT true,
    ordem_exibicao INTEGER DEFAULT 0, -- Para ordenar na interface
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE planos_nfe IS 'Planos de cobrança disponíveis para emissão de NFe';
COMMENT ON COLUMN planos_nfe.tipo_plano IS 'AVULSO: cobra por NFe emitida | PACOTE: valor fixo mensal com limite';
COMMENT ON COLUMN planos_nfe.quantidade_nfes IS 'Quantidade de NFes incluídas no pacote (NULL para avulso)';
COMMENT ON COLUMN planos_nfe.valor_mensal IS 'Valor mensal do plano/pacote';
COMMENT ON COLUMN planos_nfe.valor_por_nfe IS 'Valor unitário por NFe (usado em avulso ou excedente)';

-- 2. Tabela de Assinaturas (Vincula cliente ao plano)
CREATE TABLE IF NOT EXISTS assinaturas_cliente (
    assinatura_id SERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    plano_id INTEGER NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE, -- NULL = sem data de término
    status VARCHAR(20) DEFAULT 'ATIVA', -- 'ATIVA', 'SUSPENSA', 'CANCELADA'
    dia_vencimento INTEGER DEFAULT 10, -- Dia do mês para vencimento
    nfes_consumidas INTEGER DEFAULT 0, -- Contador de NFes no período atual
    periodo_ref_inicio DATE, -- Início do período de referência atual
    periodo_ref_fim DATE, -- Fim do período de referência atual
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    FOREIGN KEY (plano_id) REFERENCES planos_nfe(plano_id) ON DELETE RESTRICT
);

COMMENT ON TABLE assinaturas_cliente IS 'Assinaturas dos clientes aos planos de NFe';
COMMENT ON COLUMN assinaturas_cliente.status IS 'ATIVA: pode emitir NFe | SUSPENSA: temporariamente bloqueado | CANCELADA: encerrado';
COMMENT ON COLUMN assinaturas_cliente.nfes_consumidas IS 'Quantidade de NFes emitidas no período de referência atual';
COMMENT ON COLUMN assinaturas_cliente.periodo_ref_inicio IS 'Data de início do ciclo de cobrança atual';
COMMENT ON COLUMN assinaturas_cliente.periodo_ref_fim IS 'Data de fim do ciclo de cobrança atual';

-- 3. Índices para performance
CREATE INDEX idx_assinaturas_cliente ON assinaturas_cliente(cliente_id);
CREATE INDEX idx_assinaturas_status ON assinaturas_cliente(status);
CREATE INDEX idx_assinaturas_periodo ON assinaturas_cliente(periodo_ref_inicio, periodo_ref_fim);
CREATE INDEX idx_planos_tipo ON planos_nfe(tipo_plano, ativo);

-- 4. Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_planos_nfe_updated_at
    BEFORE UPDATE ON planos_nfe
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assinaturas_updated_at
    BEFORE UPDATE ON assinaturas_cliente
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 5. Inserir planos padrão
INSERT INTO planos_nfe (nome, descricao, tipo_plano, quantidade_nfes, valor_mensal, valor_por_nfe, ordem_exibicao) VALUES
    ('Avulso', 'Pagamento por NFe emitida', 'AVULSO', NULL, 0.00, 0.50, 1),
    ('Pacote Básico', 'Até 50 NFes por mês', 'PACOTE', 50, 20.00, 0.60, 2),
    ('Pacote Intermediário', 'Até 100 NFes por mês', 'PACOTE', 100, 35.00, 0.55, 3),
    ('Pacote Profissional', 'Até 250 NFes por mês', 'PACOTE', 250, 80.00, 0.50, 4),
    ('Pacote Empresarial', 'Até 500 NFes por mês', 'PACOTE', 500, 140.00, 0.45, 5),
    ('Pacote Ilimitado', 'NFes ilimitadas', 'PACOTE', NULL, 300.00, 0.00, 6)
ON CONFLICT DO NOTHING;

-- 6. Função para verificar se cliente pode emitir NFe
CREATE OR REPLACE FUNCTION pode_emitir_nfe(p_cliente_id BIGINT)
RETURNS TABLE (
    pode_emitir BOOLEAN,
    mensagem TEXT,
    nfes_disponiveis INTEGER,
    plano_nome VARCHAR(100)
) AS $$
DECLARE
    v_assinatura RECORD;
    v_plano RECORD;
BEGIN
    -- Buscar assinatura ativa do cliente
    SELECT * INTO v_assinatura
    FROM assinaturas_cliente
    WHERE cliente_id = p_cliente_id 
      AND status = 'ATIVA'
      AND (data_fim IS NULL OR data_fim >= CURRENT_DATE)
    ORDER BY assinatura_id DESC
    LIMIT 1;
    
    -- Se não tem assinatura ativa
    IF NOT FOUND THEN
        RETURN QUERY SELECT false, 'Cliente sem assinatura ativa'::TEXT, 0, ''::VARCHAR(100);
        RETURN;
    END IF;
    
    -- Buscar dados do plano
    SELECT * INTO v_plano
    FROM planos_nfe
    WHERE plano_id = v_assinatura.plano_id;
    
    -- Verificar se é plano AVULSO (sempre pode emitir)
    IF v_plano.tipo_plano = 'AVULSO' THEN
        RETURN QUERY SELECT true, 'Plano avulso - cobrança por NFe'::TEXT, 999999, v_plano.nome;
        RETURN;
    END IF;
    
    -- Verificar se é plano ILIMITADO
    IF v_plano.tipo_plano = 'PACOTE' AND v_plano.quantidade_nfes IS NULL THEN
        RETURN QUERY SELECT true, 'Plano ilimitado'::TEXT, 999999, v_plano.nome;
        RETURN;
    END IF;
    
    -- Verificar se ainda tem NFes disponíveis no pacote
    IF v_assinatura.nfes_consumidas < v_plano.quantidade_nfes THEN
        RETURN QUERY SELECT 
            true, 
            'NFes disponíveis no pacote'::TEXT,
            v_plano.quantidade_nfes - v_assinatura.nfes_consumidas,
            v_plano.nome;
        RETURN;
    ELSE
        RETURN QUERY SELECT 
            false, 
            format('Limite do pacote atingido (%s/%s NFes)', v_assinatura.nfes_consumidas, v_plano.quantidade_nfes),
            0,
            v_plano.nome;
        RETURN;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION pode_emitir_nfe IS 'Verifica se o cliente pode emitir NFe baseado em sua assinatura e consumo';

-- 7. Função para registrar emissão de NFe (incrementa contador)
CREATE OR REPLACE FUNCTION registrar_emissao_nfe(p_cliente_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_assinatura_id INTEGER;
BEGIN
    -- Buscar assinatura ativa
    SELECT assinatura_id INTO v_assinatura_id
    FROM assinaturas_cliente
    WHERE cliente_id = p_cliente_id 
      AND status = 'ATIVA'
      AND (data_fim IS NULL OR data_fim >= CURRENT_DATE)
    ORDER BY assinatura_id DESC
    LIMIT 1;
    
    IF FOUND THEN
        -- Incrementar contador
        UPDATE assinaturas_cliente
        SET nfes_consumidas = nfes_consumidas + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE assinatura_id = v_assinatura_id;
        
        RETURN true;
    ELSE
        RETURN false;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION registrar_emissao_nfe IS 'Registra a emissão de uma NFe, incrementando o contador da assinatura';

-- 8. Função para renovar período de cobrança (zera contador mensal)
CREATE OR REPLACE FUNCTION renovar_periodo_assinatura(p_assinatura_id INTEGER)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE assinaturas_cliente
    SET nfes_consumidas = 0,
        periodo_ref_inicio = CURRENT_DATE,
        periodo_ref_fim = CURRENT_DATE + INTERVAL '1 month',
        updated_at = CURRENT_TIMESTAMP
    WHERE assinatura_id = p_assinatura_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION renovar_periodo_assinatura IS 'Renova o período de cobrança, zerando o contador de NFes consumidas';

-- Commit
COMMIT;

-- Exibir resumo
SELECT 
    'Migration 006 executada com sucesso!' as status,
    (SELECT COUNT(*) FROM planos_nfe) as total_planos,
    (SELECT COUNT(*) FROM assinaturas_cliente) as total_assinaturas;

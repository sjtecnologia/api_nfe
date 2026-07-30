-- Migração para criar tabela de NFS-e Nacional
-- Padrão ABRASF 2.04 - São José do Rio Preto (GISS Online)
-- Executar: psql -U seu_usuario -d sjtnfe -f migrations/create_table_nfse.sql

CREATE TABLE IF NOT EXISTS nfse (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id),
    
    -- Identificação RPS
    numero_rps INTEGER NOT NULL,
    serie_rps VARCHAR(5) DEFAULT '1',
    tipo_rps VARCHAR(1) DEFAULT '1',  -- 1=RPS, 2=NF Conjugada, 3=Cupom
    
    -- Identificação NFS-e (após autorização)
    numero_nfse VARCHAR(20),
    codigo_verificacao VARCHAR(50),
    
    -- Datas
    data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_competencia DATE,
    
    -- Natureza da operação
    natureza_operacao VARCHAR(2) DEFAULT '1',
    -- 1=Tributação no município
    -- 2=Tributação fora do município
    -- 3=Isenção
    -- 4=Imune
    -- 5=Exigibilidade suspensa por decisão judicial
    -- 6=Exigibilidade suspensa por procedimento administrativo
    
    -- Prestador (referência ao cliente)
    prestador_cnpj VARCHAR(14),
    prestador_inscricao_municipal VARCHAR(20),
    
    -- Tomador
    tomador_id INTEGER REFERENCES destinatarios_nfe(destinatario_id),
    tomador_cpf_cnpj VARCHAR(14),
    tomador_razao_social VARCHAR(150),
    tomador_inscricao_municipal VARCHAR(20),
    tomador_endereco VARCHAR(500),
    tomador_email VARCHAR(100),
    tomador_telefone VARCHAR(20),
    
    -- Serviço
    codigo_servico VARCHAR(20),  -- Código LC 116/2003
    codigo_cnae VARCHAR(10),
    codigo_tributacao_municipal VARCHAR(20),
    discriminacao TEXT,
    codigo_municipio_prestacao VARCHAR(7) DEFAULT '3549805',  -- SJRP
    
    -- Valores
    valor_servicos DECIMAL(15,2) DEFAULT 0,
    valor_deducoes DECIMAL(15,2) DEFAULT 0,
    valor_pis DECIMAL(15,2) DEFAULT 0,
    valor_cofins DECIMAL(15,2) DEFAULT 0,
    valor_inss DECIMAL(15,2) DEFAULT 0,
    valor_ir DECIMAL(15,2) DEFAULT 0,
    valor_csll DECIMAL(15,2) DEFAULT 0,
    outras_retencoes DECIMAL(15,2) DEFAULT 0,
    desconto_incondicionado DECIMAL(15,2) DEFAULT 0,
    desconto_condicionado DECIMAL(15,2) DEFAULT 0,
    
    -- ISS
    base_calculo DECIMAL(15,2) DEFAULT 0,
    aliquota_iss DECIMAL(5,4) DEFAULT 0,
    valor_iss DECIMAL(15,2) DEFAULT 0,
    iss_retido BOOLEAN DEFAULT FALSE,
    valor_iss_retido DECIMAL(15,2) DEFAULT 0,
    
    -- Totais
    valor_liquido DECIMAL(15,2) DEFAULT 0,
    
    -- Construção Civil (opcional)
    codigo_obra VARCHAR(20),
    art VARCHAR(20),
    
    -- Informações complementares
    informacoes_complementares TEXT,
    
    -- XML e processamento
    xml_rps TEXT,
    xml_nfse TEXT,
    xml_cancelamento TEXT,
    protocolo VARCHAR(50),
    
    -- Status
    status VARCHAR(2) DEFAULT '0',
    -- 0=Pendente
    -- 1=Autorizada
    -- 2=Aguardando processamento
    -- 3=Cancelada
    -- 4=Rejeitada
    
    mensagem_retorno TEXT,
    ambiente VARCHAR(20) DEFAULT 'homologacao',  -- homologacao ou producao
    
    -- Auditoria
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    
    -- Constraints
    CONSTRAINT uk_nfse_rps UNIQUE (cliente_id, numero_rps, serie_rps),
    CONSTRAINT uk_nfse_numero UNIQUE (numero_nfse, codigo_verificacao)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_nfse_cliente ON nfse(cliente_id);
CREATE INDEX IF NOT EXISTS idx_nfse_data_emissao ON nfse(data_emissao);
CREATE INDEX IF NOT EXISTS idx_nfse_status ON nfse(status);
CREATE INDEX IF NOT EXISTS idx_nfse_Tomadores ON nfse(Tomadores_cpf_cnpj);
CREATE INDEX IF NOT EXISTS idx_nfse_protocolo ON nfse(protocolo);

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_nfse_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_nfse_updated_at ON nfse;
CREATE TRIGGER trigger_nfse_updated_at
    BEFORE UPDATE ON nfse
    FOR EACH ROW
    EXECUTE FUNCTION update_nfse_updated_at();

-- Comentários
COMMENT ON TABLE nfse IS 'Notas Fiscais de Serviço Eletrônicas - Padrão Nacional ABRASF 2.04';
COMMENT ON COLUMN nfse.natureza_operacao IS '1=Tributação município, 2=Tributação fora, 3=Isenção, 4=Imune, 5=Suspensa judicial, 6=Suspensa administrativa';
COMMENT ON COLUMN nfse.status IS '0=Pendente, 1=Autorizada, 2=Aguardando, 3=Cancelada, 4=Rejeitada';

-- Inserir registros de teste se necessário (descomente para testes)
-- INSERT INTO nfse (cliente_id, numero_rps, serie_rps, discriminacao, valor_servicos, status)
-- VALUES (1, 1, '1', 'Serviço de teste', 100.00, '0');

SELECT 'Tabela nfse criada com sucesso!' as resultado;

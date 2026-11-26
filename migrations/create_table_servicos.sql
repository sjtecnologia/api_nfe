-- Migração: Catálogo de Serviços do cliente (análogo à tabela `produtos`)
-- Usado para faturamento via NFS-e; a classificação tributária (LC116/NBS/ISS/
-- IBS-CBS) permanece em `regras_tributacao_servicos` (referenciada por regra_id).
-- Data: 15/07/2026
-- Executar: psql -U seu_usuario -d sjtnfe -f migrations/create_table_servicos.sql

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'clientes') THEN
        RAISE EXCEPTION 'Tabela clientes não existe.';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS servicos (
    servico_id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    codigo_interno VARCHAR(50) NOT NULL,
    descricao TEXT NOT NULL,
    unidade VARCHAR(6) NOT NULL DEFAULT 'UN',
    valor_padrao NUMERIC(15,2) NOT NULL DEFAULT 0,
    regra_id INTEGER REFERENCES regras_tributacao_servicos(regra_id) ON DELETE SET NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id INTEGER REFERENCES users(id),
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT servico_codigo_interno_u UNIQUE (cliente_id, codigo_interno)
);

CREATE INDEX IF NOT EXISTS idx_servicos_cliente ON servicos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_servicos_ativo ON servicos(ativo);
CREATE INDEX IF NOT EXISTS idx_servicos_regra ON servicos(regra_id);

COMMENT ON TABLE servicos IS 'Catálogo de serviços faturáveis do cliente (análogo a produtos), usado na emissão de NFS-e.';
COMMENT ON COLUMN servicos.regra_id IS 'Regra tributária de serviço aplicada (LC116/NBS/ISS/IBS-CBS) — ver tabela regras_tributacao_servicos.';

COMMIT;

-- Migração 009: Categorias do Fluxo de Caixa
-- Data: 2026-08-12

BEGIN;

CREATE TABLE IF NOT EXISTS fluxo_caixa_categorias (
    categoria_id BIGSERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    tipo_lancamento VARCHAR(10) NOT NULL CHECK (tipo_lancamento IN ('RECEITA', 'DESPESA')),
    descricao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE INDEX IF NOT EXISTS idx_fluxo_cat_cliente_nome
    ON fluxo_caixa_categorias (cliente_id, nome);

CREATE INDEX IF NOT EXISTS idx_fluxo_cat_cliente_tipo_nome
    ON fluxo_caixa_categorias (cliente_id, tipo_lancamento, nome);

COMMIT;

-- Migração 008: Controle de Estoque + Fluxo de Caixa
-- Data: 2026-08-12

BEGIN;

CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
    movimentacao_id BIGSERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    produto_id INTEGER,
    tipo_movimentacao VARCHAR(10) NOT NULL CHECK (tipo_movimentacao IN ('ENTRADA', 'SAIDA')),
    quantidade NUMERIC(15, 3) NOT NULL CHECK (quantidade > 0),
    valor_unitario NUMERIC(15, 2),
    observacao TEXT,
    data_movimentacao TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE INDEX IF NOT EXISTS idx_estoque_mov_cliente_data
    ON estoque_movimentacoes (cliente_id, data_movimentacao DESC);

CREATE INDEX IF NOT EXISTS idx_estoque_mov_produto
    ON estoque_movimentacoes (produto_id);

CREATE TABLE IF NOT EXISTS fluxo_caixa_lancamentos (
    lancamento_id BIGSERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    tipo_lancamento VARCHAR(10) NOT NULL CHECK (tipo_lancamento IN ('RECEITA', 'DESPESA')),
    categoria VARCHAR(100) NOT NULL,
    descricao TEXT NOT NULL,
    valor NUMERIC(15, 2) NOT NULL CHECK (valor > 0),
    forma_pagamento VARCHAR(50),
    observacao TEXT,
    data_lancamento TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE INDEX IF NOT EXISTS idx_fluxo_caixa_cliente_data
    ON fluxo_caixa_lancamentos (cliente_id, data_lancamento DESC);

CREATE INDEX IF NOT EXISTS idx_fluxo_caixa_tipo
    ON fluxo_caixa_lancamentos (tipo_lancamento);

COMMIT;

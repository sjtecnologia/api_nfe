-- Catálogo público, pedidos e conexão de pagamento por empresa.
-- Execute esta migração antes de habilitar o módulo em produção.

CREATE TABLE IF NOT EXISTS catalogos_vendas (
    catalogo_id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    token_publico VARCHAR(80) NOT NULL UNIQUE,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    whatsapp_numero VARCHAR(20),
    pagamento_online_ativo BOOLEAN NOT NULL DEFAULT FALSE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_catalogos_vendas_cliente ON catalogos_vendas(cliente_id);

CREATE TABLE IF NOT EXISTS catalogos_vendas_itens (
    catalogo_item_id BIGSERIAL PRIMARY KEY,
    catalogo_id BIGINT NOT NULL REFERENCES catalogos_vendas(catalogo_id) ON DELETE CASCADE,
    -- produtos possui chave composta (produto_id, cliente_id) no schema legado;
    -- a associação é validada pela consulta sempre escopada ao cliente do catálogo.
    produto_id BIGINT NOT NULL,
    preco_unitario NUMERIC(15,2) NOT NULL CHECK (preco_unitario >= 0),
    ordem INTEGER NOT NULL DEFAULT 0,
    UNIQUE (catalogo_id, produto_id)
);

CREATE TABLE IF NOT EXISTS contas_pagamento_cliente (
    conta_pagamento_id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL UNIQUE REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    provider VARCHAR(30) NOT NULL DEFAULT 'mercadopago',
    seller_id VARCHAR(100),
    access_token_criptografado TEXT NOT NULL,
    refresh_token_criptografado TEXT,
    token_expira_em TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'ATIVA',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedidos_vendas (
    pedido_id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    catalogo_id BIGINT NOT NULL REFERENCES catalogos_vendas(catalogo_id),
    token_publico VARCHAR(80) NOT NULL UNIQUE,
    numero VARCHAR(30) NOT NULL UNIQUE,
    comprador_nome VARCHAR(255) NOT NULL,
    comprador_telefone VARCHAR(20) NOT NULL,
    comprador_email VARCHAR(255),
    observacao TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'AGUARDANDO_ATENDIMENTO',
    status_pagamento VARCHAR(30) NOT NULL DEFAULT 'NAO_SOLICITADO',
    valor_total NUMERIC(15,2) NOT NULL CHECK (valor_total >= 0),
    provider VARCHAR(30),
    provider_reference VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pedidos_vendas_cliente_data ON pedidos_vendas(cliente_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_pedidos_vendas_catalogo ON pedidos_vendas(catalogo_id);

CREATE TABLE IF NOT EXISTS pedidos_vendas_itens (
    pedido_item_id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL REFERENCES pedidos_vendas(pedido_id) ON DELETE CASCADE,
    produto_id BIGINT,
    codigo_produto VARCHAR(50),
    descricao VARCHAR(500) NOT NULL,
    unidade VARCHAR(10),
    quantidade NUMERIC(15,3) NOT NULL CHECK (quantidade > 0),
    valor_unitario NUMERIC(15,2) NOT NULL CHECK (valor_unitario >= 0),
    valor_total NUMERIC(15,2) NOT NULL CHECK (valor_total >= 0)
);

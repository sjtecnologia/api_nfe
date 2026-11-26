-- Orçamentos, portal do cliente final e notificações.
-- Execute esta migração antes de habilitar o módulo em produção.

-- Papel usado pelos usuários do portal (clientes da empresa assinante).
INSERT INTO roles (name, description)
SELECT 'Cliente', 'Usuário do portal de clientes (pedidos de orçamento)'
WHERE NOT EXISTS (SELECT 1 FROM roles WHERE LOWER(name) = 'cliente');

-- Usuários do portal: ligam um login ao cliente final (destinatário) de uma empresa.
CREATE TABLE IF NOT EXISTS portal_usuarios (
    portal_usuario_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    cliente_id BIGINT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    destinatario_id BIGINT REFERENCES destinatarios_nfe(destinatario_id) ON DELETE SET NULL,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefone VARCHAR(20),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_portal_usuarios_cliente ON portal_usuarios(cliente_id);
CREATE INDEX IF NOT EXISTS ix_portal_usuarios_destinatario ON portal_usuarios(destinatario_id);

-- Orçamentos: criados pela empresa (INTERNO) ou solicitados pelo portal (PORTAL).
CREATE TABLE IF NOT EXISTS orcamentos (
    orcamento_id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    destinatario_id BIGINT REFERENCES destinatarios_nfe(destinatario_id) ON DELETE SET NULL,
    portal_usuario_id BIGINT REFERENCES portal_usuarios(portal_usuario_id) ON DELETE SET NULL,
    numero VARCHAR(40) NOT NULL UNIQUE,
    origem VARCHAR(20) NOT NULL DEFAULT 'INTERNO',
    status VARCHAR(30) NOT NULL DEFAULT 'RASCUNHO',
    validade DATE,
    observacao TEXT,
    valor_total NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (valor_total >= 0),
    pedido_id BIGINT,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT orcamentos_origem_check CHECK (origem IN ('INTERNO', 'PORTAL')),
    CONSTRAINT orcamentos_status_check CHECK (
        status IN ('RASCUNHO', 'SOLICITADO', 'ENVIADO', 'APROVADO', 'RECUSADO', 'CONVERTIDO', 'CANCELADO')
    )
);

CREATE INDEX IF NOT EXISTS ix_orcamentos_cliente_data ON orcamentos(cliente_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_orcamentos_destinatario ON orcamentos(destinatario_id);
CREATE INDEX IF NOT EXISTS ix_orcamentos_portal ON orcamentos(portal_usuario_id);

CREATE TABLE IF NOT EXISTS orcamentos_itens (
    orcamento_item_id BIGSERIAL PRIMARY KEY,
    orcamento_id BIGINT NOT NULL REFERENCES orcamentos(orcamento_id) ON DELETE CASCADE,
    produto_id BIGINT,
    codigo_produto VARCHAR(50),
    descricao VARCHAR(500) NOT NULL,
    unidade VARCHAR(10),
    quantidade NUMERIC(15,3) NOT NULL CHECK (quantidade > 0),
    valor_unitario NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (valor_unitario >= 0),
    valor_total NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (valor_total >= 0)
);

CREATE INDEX IF NOT EXISTS ix_orcamentos_itens_orcamento ON orcamentos_itens(orcamento_id);

-- Permite que pedidos de venda sejam originados de um orçamento (sem catálogo público).
ALTER TABLE pedidos_vendas ALTER COLUMN catalogo_id DROP NOT NULL;
ALTER TABLE pedidos_vendas ADD COLUMN IF NOT EXISTS orcamento_id BIGINT REFERENCES orcamentos(orcamento_id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_pedidos_vendas_orcamento ON pedidos_vendas(orcamento_id);

-- Notificações no sistema para a empresa assinante e para usuários do portal.
CREATE TABLE IF NOT EXISTS notificacoes (
    notificacao_id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tipo VARCHAR(40) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT,
    link VARCHAR(500),
    referencia_tipo VARCHAR(40),
    referencia_id BIGINT,
    lida BOOLEAN NOT NULL DEFAULT FALSE,
    lida_em TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_notificacoes_usuario ON notificacoes(user_id, lida, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_notificacoes_cliente ON notificacoes(cliente_id, created_at DESC);

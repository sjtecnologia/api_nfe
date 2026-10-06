CREATE TABLE IF NOT EXISTS transport_documents (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    tipo_documento VARCHAR(30) NOT NULL,
    ambiente VARCHAR(20) NOT NULL DEFAULT 'homologacao',
    referencia VARCHAR(80) NOT NULL,
    numero INTEGER,
    serie INTEGER,
    status VARCHAR(30) NOT NULL DEFAULT 'RASCUNHO',
    chave_acesso VARCHAR(44),
    protocolo VARCHAR(60),
    codigo_status VARCHAR(10),
    mensagem TEXT,
    payload_json TEXT NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    xml_envio TEXT,
    xml_autorizado TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    authorized_at TIMESTAMP,
    CONSTRAINT transport_documents_type_check CHECK (
        tipo_documento IN ('cte', 'cte_os', 'cte_simplificado', 'mdfe')
    ),
    CONSTRAINT transport_documents_environment_check CHECK (
        ambiente IN ('homologacao', 'producao')
    ),
    CONSTRAINT uq_transport_document_reference UNIQUE (cliente_id, tipo_documento, referencia)
);

CREATE INDEX IF NOT EXISTS ix_transport_documents_client_type
    ON transport_documents (cliente_id, tipo_documento, created_at DESC);

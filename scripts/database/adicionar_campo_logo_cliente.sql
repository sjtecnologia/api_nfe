-- Adicionar campo logo_path na tabela clientes
-- Este campo armazenará o caminho do arquivo de logo do cliente
-- Executar este script no banco de dados PostgreSQL

-- Adicionar coluna logo_path
ALTER TABLE clientes 
ADD COLUMN IF NOT EXISTS logo_path VARCHAR(255) DEFAULT NULL;

-- Comentário descritivo
COMMENT ON COLUMN clientes.logo_path IS 'Caminho do arquivo de logo do cliente (ex: logos/cliente_123.png)';

-- Verificar se a coluna foi adicionada
SELECT 
    column_name, 
    data_type, 
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'clientes' 
  AND column_name = 'logo_path';

-- Exibir estrutura atualizada da tabela
\d clientes;

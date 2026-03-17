-- Migration: Adicionar suporte a CPF e Produtor Rural na tabela clientes
-- Data: 17/03/2026
-- Descrição: Adiciona campos cpf e produtor_rural para suporte a emissão de NF-e para produtores rurais

-- Adicionar coluna cpf (nullable pois empresas não terão CPF)
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS cpf VARCHAR(14) UNIQUE;

-- Adicionar coluna produtor_rural com default false
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS produtor_rural BOOLEAN NOT NULL DEFAULT FALSE;

-- Modificar coluna cnpj para nullable (produtor rural pode não ter CNPJ)
ALTER TABLE clientes ALTER COLUMN cnpj DROP NOT NULL;

-- Adicionar comentários nas colunas
COMMENT ON COLUMN clientes.cpf IS 'CPF do produtor rural (sem formatação)';
COMMENT ON COLUMN clientes.produtor_rural IS 'Flag indicando se é produtor rural (usa CPF ao invés de CNPJ)';
COMMENT ON COLUMN clientes.cnpj IS 'CNPJ da empresa (nullable para produtor rural)';

-- Adicionar constraint para garantir que tenha ou CNPJ ou CPF
ALTER TABLE clientes ADD CONSTRAINT check_cnpj_ou_cpf 
CHECK (
    (cnpj IS NOT NULL AND cpf IS NULL AND produtor_rural = FALSE) OR 
    (cpf IS NOT NULL AND cnpj IS NULL AND produtor_rural = TRUE)
);

-- Criar índice para melhorar performance de busca por CPF
CREATE INDEX IF NOT EXISTS idx_clientes_cpf ON clientes(cpf) WHERE cpf IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_clientes_produtor_rural ON clientes(produtor_rural) WHERE produtor_rural = TRUE;

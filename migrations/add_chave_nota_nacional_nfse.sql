-- Migração: adiciona a chave de acesso da NFS-e no Ambiente de Dados Nacional (ADN)
-- Necessária para consulta pública (nfse.gov.br) e para geração do DANFSe (NT008)
-- Data: 15/07/2026
-- Executar: psql -U seu_usuario -d sjtnfe -f migrations/add_chave_nota_nacional_nfse.sql

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'nfse') THEN
        RAISE EXCEPTION 'Tabela nfse não existe. Execute primeiro create_table_nfse.sql';
    END IF;
END $$;

ALTER TABLE nfse ADD COLUMN IF NOT EXISTS chave_nota_nacional VARCHAR(60);
COMMENT ON COLUMN nfse.chave_nota_nacional IS 'Chave de acesso da NFS-e no Ambiente de Dados Nacional (ADN), retornada pelo GISS em CompNfse/ChaveNotaNacional. Usada para consulta pública e DANFSe (NT008).';

CREATE INDEX IF NOT EXISTS idx_nfse_chave_nota_nacional ON nfse(chave_nota_nacional);

COMMIT;

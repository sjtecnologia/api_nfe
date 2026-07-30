-- Migration para corrigir nomes de colunas da tabela nfse
-- De Tomadores_* (maiúsculo) para tomador_* (minúsculo)
-- Data: 30/01/2026

-- Renomear colunas do tomador
ALTER TABLE nfse RENAME COLUMN Tomadores_id TO tomador_id;
ALTER TABLE nfse RENAME COLUMN Tomadores_cpf_cnpj TO tomador_cpf_cnpj;
ALTER TABLE nfse RENAME COLUMN Tomadores_razao_social TO tomador_razao_social;
ALTER TABLE nfse RENAME COLUMN Tomadores_inscricao_municipal TO tomador_inscricao_municipal;
ALTER TABLE nfse RENAME COLUMN Tomadores_endereco TO tomador_endereco;
ALTER TABLE nfse RENAME COLUMN Tomadores_email TO tomador_email;
ALTER TABLE nfse RENAME COLUMN Tomadores_telefone TO tomador_telefone;

-- Verificar resultado
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'nfse' 
  AND column_name LIKE 'tomador%'
ORDER BY column_name;

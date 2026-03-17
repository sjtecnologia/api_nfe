-- =============================================================================
-- MIGRAÇÃO: Suporte a Emitente Produtor Rural (CPF sem CNPJ)
-- Data: 2026-03-06
-- Descrição: Ajusta a tabela 'clientes' para suportar emitentes que são
--            Produtores Rurais — Pessoa Física que emite NF-e com CPF,
--            podendo não ter Inscrição Estadual nem CNPJ.
--            Conforme NF-e Schema 4.00 - grupo <emit>: usa <CPF> ou <CNPJ>.
-- =============================================================================

BEGIN;

-- 1. Torna o campo 'cnpj' nullable (Produtor Rural não possui CNPJ)
ALTER TABLE public.clientes
    ALTER COLUMN cnpj DROP NOT NULL;

-- 2. Adiciona campo CPF para Produtor Rural (11 dígitos, sem formatação)
ALTER TABLE public.clientes
    ADD COLUMN IF NOT EXISTS cpf character varying(11) DEFAULT NULL;

-- 3. Adiciona flag que identifica o emitente como Produtor Rural
ALTER TABLE public.clientes
    ADD COLUMN IF NOT EXISTS produtor_rural boolean NOT NULL DEFAULT false;

-- 4. Comentários para documentação
COMMENT ON COLUMN public.clientes.cpf IS
    'CPF do emitente Produtor Rural (11 dígitos, sem formatação). Preenchido apenas quando produtor_rural = true.';
COMMENT ON COLUMN public.clientes.produtor_rural IS
    'Identifica o emitente como Produtor Rural (Pessoa Física sem CNPJ). Quando true, usa CPF no XML <emit>.';
COMMENT ON COLUMN public.clientes.cnpj IS
    'CNPJ do emitente (14 dígitos). NULL quando produtor_rural = true.';

-- 5. Constraint: cada cliente deve ter cnpj OU cpf preenchido (não ambos nulos)
ALTER TABLE public.clientes
    ADD CONSTRAINT clientes_cnpj_or_cpf_required
    CHECK (
        (cnpj IS NOT NULL AND cpf IS NULL AND produtor_rural = false)
        OR
        (cpf IS NOT NULL AND cnpj IS NULL AND produtor_rural = true)
    );

-- 6. Unique constraint para CPF (somente quando preenchido)
ALTER TABLE public.clientes
    ADD CONSTRAINT clientes_cpf_unique
    UNIQUE (cpf);

-- 7. (Também ajustar destinatarios_nfe para o campo produtor_rural — destinatário)
ALTER TABLE public.destinatarios_nfe
    ADD COLUMN IF NOT EXISTS produtor_rural boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.destinatarios_nfe.produtor_rural IS
    'Indica se o destinatário é Produtor Rural (CPF + IE contribuinte ICMS).';

COMMIT;

-- Verificar resultado:
-- SELECT cliente_id, razao_social, cnpj, cpf, produtor_rural FROM clientes ORDER BY cliente_id;

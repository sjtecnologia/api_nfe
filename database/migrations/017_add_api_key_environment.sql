ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS ambiente VARCHAR(20) NOT NULL DEFAULT 'producao';

UPDATE api_keys
SET ambiente = CASE
    WHEN key_prefix LIKE 'emx_test_%' THEN 'teste'
    ELSE 'producao'
END
WHERE ambiente IS NULL OR ambiente NOT IN ('teste', 'producao');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'api_keys_ambiente_check'
          AND conrelid = 'api_keys'::regclass
    ) THEN
        ALTER TABLE api_keys
            ADD CONSTRAINT api_keys_ambiente_check CHECK (ambiente IN ('teste', 'producao'));
    END IF;
END $$;

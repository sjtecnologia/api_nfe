-- Fase 4.6G.MP5: persist the canonical external reference on existing E2E attempts.
ALTER TABLE billing_checkout_attempts
    ADD COLUMN IF NOT EXISTS external_reference VARCHAR(255);

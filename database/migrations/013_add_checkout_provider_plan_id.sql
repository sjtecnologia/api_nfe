-- Fase 4.6G.MP5: align existing E2E checkout schema with the ORM model.
ALTER TABLE billing_checkout_attempts
    ADD COLUMN IF NOT EXISTS provider_plan_id VARCHAR(255);

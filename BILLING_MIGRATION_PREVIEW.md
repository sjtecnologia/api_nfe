# Billing Migration Preview

**Fase:** 4.6F.5  
**Modo:** somente leitura

## Saída

O serviço `BillingMigrationPreviewService` produz, por cliente, `cliente_id`, plano legacy observado, `contracted_price` conhecido, `BillingAccount` correspondente, plano sugerido, grandfathering, motivo, confidence, ação e estado de migração. Não retorna CPF/CNPJ, credenciais ou chaves.

Exemplo conceitual:

```json
{
  "cliente_id": 123,
  "legacy_plan": "Pacote Básico",
  "contracted_price": null,
  "billing_account_id": null,
  "suggested_plan": "LEGACY_POLICY_REVIEW_REQUIRED",
  "grandfathered": true,
  "reason": "PUBLIC_PLAN_PRICE_APPROXIMATES_60_BUT_CONTRACT_PRICE_UNKNOWN",
  "confidence": "MEDIUM",
  "action": "MANUAL_REVIEW",
  "migration_state": "REVIEW_REQUIRED"
}
```

## Fonte e segurança

A fonte legacy é `assinaturas_cliente` + `planos_nfe`. A fonte shadow é `billing_subscriptions` + `billing_subscription_companies` + `billing_accounts`. O serviço não chama `commit`, não executa migration e não bloqueia emissão.

## Critérios

Assinatura ativa com nome legacy explícito ou evidência shadow coerente pode ser `MEDIUM`/`HIGH`. Preço público próximo de R$60 sem `contracted_price` nunca é suficiente para alta confiança. Dados ausentes ou conflitantes são `LOW`/`REVIEW_REQUIRED`.

## Auditoria

Execute:

```bash
DATABASE_URL=postgresql://... python scripts/audit_legacy_customers.py
```

Somente bancos locais (`localhost`, `127.0.0.1` ou serviço local `postgres`) são aceitos. O script emite agregados sem CPF/CNPJ e termina com rollback.

## Resultado desta fase

O banco comercial configurado nesta sessão não foi auditado porque a configuração disponível não forneceu um database local parseável. O banco E2E é sintético e não representa a população comercial. Nenhum cliente foi migrado.

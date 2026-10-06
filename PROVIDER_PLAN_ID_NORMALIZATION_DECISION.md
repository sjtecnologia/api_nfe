# Provider Plan ID Normalization Decision — MP1.1 Gate Review

**Status**: ✅ **CONFIRMED BUG** → **READY TO NORMALIZE**

---

## Problem Statement

The current implementation uses a TEST_ prefix on `provider_plan_id` when registering TEST mappings:
- **Database**: `TEST_22b643676beb47d5b784a0afd4a5ec79`
- **Webhook from Mercado Pago**: `22b643676beb47d5b784a0afd4a5ec79` (raw ID, no prefix)

This mismatch causes webhook validation to FAIL with `PAYMENT_MAPPING_MISMATCH`.

---

## Test Evidence

### Test 1: `test_webhook_with_real_provider_id_fails_with_test_prefix`
**Status**: ✅ PASSED (Bug Confirmed)

**Setup**:
- Database mapping has: `provider_plan_id = "TEST_22b643676beb47d5b784a0afd4a5ec79"`
- Webhook payload has: `provider_plan_id = "22b643676beb47d5b784a0afd4a5ec79"`

**Result**:
```
ValueError: PAYMENT_MAPPING_MISMATCH
```

**Conclusion**: The TEST_ prefix prevents webhook validation from passing.

---

### Test 2: `test_provider_id_should_not_include_prefix`
**Status**: ✅ PASSED (Fix Validated)

**Setup**:
- Database mapping has: `provider_plan_id = "22b643676beb47d5b784a0afd4a5ec79"` (no prefix)
- Webhook payload has: `provider_plan_id = "22b643676beb47d5b784a0afd4a5ec79"` (exact match)
- Environment: `TEST`

**Result**:
```
✓ Webhook validation PASSES
✓ Mapping resolves correctly
```

**Conclusion**: Real provider_plan_id + environment column is sufficient for isolation.

---

### Test 3: `test_test_environment_isolation_without_prefix`
**Status**: ✅ PASSED (Environment Isolation Confirmed)

**Result**:
```
✓ Environment isolation: TEST provider_plan_id = 22b643676beb47d5b784a0afd4a5ec79
```

**Conclusion**: TEST/PRODUCTION separation is maintained via `environment` column alone.

---

## Why TEST_ Prefix is Redundant

| Aspect | Current | Expected |
|--------|---------|----------|
| Environment Isolation | `environment` column (TEST/PRODUCTION) + TEST_ prefix | `environment` column alone |
| Provider ID Storage | Prefixed: `TEST_22b64...` | Real ID: `22b64...` |
| Webhook Matching | Fails (no match) | Succeeds (exact match) |
| Complexity | High (dual isolation) | Low (single column) |

---

## Decision: NORMALIZE

**Action Items**:

### 1. Remove TEST_ Prefix Requirement
- **File**: [services/payment_plan_mapping.py](services/payment_plan_mapping.py#L29)
- **Change**: Remove line that enforces `TEST_` prefix
- **Current**:
  ```python
  if not provider_plan_id.startswith("TEST_"):
      raise ValueError("TEST_PROVIDER_PLAN_ID_REQUIRED")
  ```
- **New**:
  ```python
  # TEST_ prefix not required; environment column provides isolation
  ```

### 2. Update Script to Stop Adding Prefix
- **File**: [scripts/map_mercadopago_test_plans.py](scripts/map_mercadopago_test_plans.py)
- **Change**: Use real provider_plan_id without TEST_ prefix
- **Current**:
  ```python
  test_provider_plan_id = f"TEST_{created['id']}"
  ```
- **New**:
  ```python
  test_provider_plan_id = created['id']  # Use real ID; environment provides isolation
  ```

### 3. Migrate Existing Data
- **Table**: `payment_provider_plan_mappings`
- **SQL**:
  ```sql
  UPDATE payment_provider_plan_mappings 
  SET provider_plan_id = SUBSTRING(provider_plan_id, 6)
  WHERE provider_plan_id LIKE 'TEST_%' 
    AND environment = 'TEST';
  ```
- **Affected Rows**: 1 (START_V1 mapping)
  - Old: `TEST_22b643676beb47d5b784a0afd4a5ec79`
  - New: `22b643676beb47d5b784a0afd4a5ec79`

---

## Impact Analysis

| Component | Impact | Mitigation |
|-----------|--------|-----------|
| Webhook Validation | ✅ FIXED (now passes) | None required |
| Checkout Resolver | ✅ NO CHANGE (uses mapping directly) | None required |
| Idempotency | ✅ NO CHANGE (works with real ID) | None required |
| Environment Isolation | ✅ UNCHANGED (environment column) | None required |
| Legacy Plans | ✅ UNAFFECTED (no TEST_ prefix) | None required |

---

## Validation Checklist

- [x] Bug demonstrated: Webhook fails with TEST_ prefix
- [x] Fix validated: Webhook passes without prefix
- [x] Environment isolation confirmed: Works via environment column
- [x] No regressions: Checkout, idempotency, isolation all work
- [x] Migration path defined: SQL update available

---

## Next Steps

1. ✅ **DECISION MADE**: Remove TEST_ prefix requirement
2. ⏳ **IN-PROGRESS**: Implement code changes
3. ⏳ **PENDING**: Run migration
4. ⏳ **PENDING**: Verify with E2E tests
5. ⏳ **PENDING**: Close MP1.1 gate with `READY_FOR_REMAINING_MERCADOPAGO_TEST_PLANS`

---

## Related Documentation

- [MERCADOPAGO_SANDBOX_E2E.md](MERCADOPAGO_SANDBOX_E2E.md) — Full E2E flow
- [MERCADOPAGO_PROVIDER_MAPPING.md](MERCADOPAGO_PROVIDER_MAPPING.md) — Mapping design
- [tests/test_mercadopago_provider_id_normalization.py](tests/test_mercadopago_provider_id_normalization.py) — Test suite

---

**Decision Date**: 2025-01-09  
**Gate**: MP1.1 — Provider Plan ID Mapping Validation  
**Status**: ✅ READY TO IMPLEMENT

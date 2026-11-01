# Fix runtime crash: Add missing `increment_used()` method

## Summary

```diff
 enemygen/models.py
+ def increment_used(self):
+     """ Increments the 'used' counter for the template. """
+     self.used += 1
+     self.save(update_fields=['used'])
```

Adds the `increment_used()` method to `EnemyTemplate` that is already called by `views_lib.py` during enemy generation but was missing from the model, causing a runtime `AttributeError` crash whenever generation runs with `increment=True`. Uses `save(update_fields=['used'])` to avoid accidentally persisting unrelated in-memory field changes.

## Evidence

- **Before:** `views_lib.py` calls `et.increment_used()` at lines 148 and 193, but the method doesn't exist in `EnemyTemplate`. Any enemy generation with `increment=True` crashes with:

```
AttributeError: 'EnemyTemplate' object has no attribute 'increment_used'
```

- **After:** All 49 tests pass, including 7 new tests covering every call path and edge case:

```
Found 49 test(s).
----------------------------------------------------------------------
Ran 49 tests in 3.218s
OK
```

**New tests added:**
- `test_increment_used` — verifies the method increments `used` and persists to the database.
- `test_get_enemies_calls_increment_used` — verifies `get_enemies()` in `views_lib.py` calls `increment_used()` when `increment=True` (used by `generate_enemies` and `generate_enemies_json` views).
- `test_get_enemies_no_increment` — verifies `get_enemies()` does NOT call `increment_used()` when `increment=False` (used when `dont_increment` POST param is set).
- `test_get_generated_party_calls_increment_used` — verifies `get_generated_party()` calls `increment_used()` for each template in a party (used by `generate_party` and `generate_party_json` views).
- `test_increment_used_does_not_save_other_fields` — verifies `save(update_fields=['used'])` prevents unrelated in-memory field changes from being persisted.
- `test_get_enemies_increments_both_used_and_generated` — verifies a single generation call increments both `used` and `generated` counters.
- `test_get_enemies_multiple_templates_increment_independently` — verifies each template's `used` counter increments independently when generating from multiple templates.

## Merge Danger

**Door:** Two-way — reverting removes the method, restoring the crash.
**Blast Radius:** Very low — adds one method to the model. The method is already called in production code; this fix simply makes those calls work instead of crashing.

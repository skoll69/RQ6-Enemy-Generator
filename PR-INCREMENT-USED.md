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

- **After:** All 53 tests pass, including 11 new tests covering every call path, edge case, external API, and smoke tests:

```
Found 53 test(s).
----------------------------------------------------------------------
Ran 53 tests in 3.532s
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
- `test_generate_enemies_json_api_increments_used` — end-to-end test: hits `/generate_enemies_json/` API, verifies valid JSON response and `used` counter increment.
- `test_generate_party_json_api_increments_used` — end-to-end test: hits `/generate_party_json/` API, verifies valid JSON response and `used` counter increment.
- `test_generate_enemies_view_does_not_crash` — smoke test: verifies the main generation view's code path (`get_enemies` with `increment=True`) does not crash. This test would have caught the `increment_used()` deletion bug.
- `test_generate_party_view_does_not_crash` — smoke test: verifies the party generation view's code path (`get_generated_party`) does not crash. This test would have caught the `increment_used()` deletion bug.

**External APIs affected:**
Two JSON API endpoints call generation with `increment=True`, which would crash before this fix:
- `/generate_enemies_json/` — always increments `used` (no `dont_increment` option).
- `/generate_party_json/` — always increments `used` via `get_generated_party()`.

The AJAX endpoints in `ajax.py` are **not affected** — they do not call `get_enemies()`, `get_generated_party()`, or `increment_used()`.

## Merge Danger

**Door:** Two-way — reverting removes the method, restoring the crash.
**Blast Radius:** Very low — adds one method to the model. The method is already called in production code; this fix simply makes those calls work instead of crashing.

## Manual Testing

### Prerequisites

1. Check out the `pr/increment-used-fix` branch.
2. Start the development server: `python manage.py runserver`.
3. Ensure at least one enemy template exists and is published.

### Test 1: Enemy Generation No Longer Crashes

**Why:** Before this fix, generating an enemy crashes with `AttributeError: 'EnemyTemplate' object has no attribute 'increment_used'`.

**Steps:**
1. Navigate to `http://localhost:8000/`.
2. Select any enemy template from the list.
3. Set the amount to `1` and click **Generate**.
4. Verify the page loads the generated enemy stat block without errors.

**Expected:** Enemy generates successfully; no 500 error or traceback.

### Test 2: `used` Counter Increments on Generation

**Why:** The `used` counter tracks how many times a template has been used for generation.

**Steps:**
1. Navigate to an enemy template's edit page (e.g., `http://localhost:8000/edit_enemy/1/`).
2. Note the current **Used** count displayed on the template.
3. Go back to the home page and generate one enemy from this template.
4. Return to the edit page and check the **Used** count again.

**Expected:** The **Used** count increased by exactly 1.

### Test 3: Party Generation Increments `used` per Template

**Why:** Generating a party should increment `used` for each template in the party, not just once.

**Steps:**
1. Create or identify a party with at least one template.
2. Note the **Used** count for each template in the party.
3. Navigate to the party page and click **Generate Party**.
4. Check the **Used** count for each template after generation.

**Expected:** Each template's **Used** count increased by 1, regardless of the amount of enemies generated from that template.

### Test 4: JSON API — Single Enemy Generation

**Why:** The `/generate_enemies_json/` endpoint is used by external tools and always increments `used`.

**Steps:**
1. Find the ID of a published enemy template (e.g., `1`).
2. Open `http://localhost:8000/generate_enemies_json/?id=1&amount=2` in a browser or via `curl`.
3. Verify the response is valid JSON with 2 enemy objects.

**Expected:** Valid JSON response with 2 enemies; no 500 error.

### Test 5: JSON API — Party Generation

**Why:** The `/generate_party_json/` endpoint is used by external tools and always increments `used`.

**Steps:**
1. Find the ID of a published party (e.g., `1`).
2. Open `http://localhost:8000/generate_party_json/?id=1` in a browser or via `curl`.
3. Verify the response is valid JSON with a `party_name` and `enemies` array.

**Expected:** Valid JSON response with party data; no 500 error.

### Test 6: `dont_increment` Parameter Skips Counter

**Why:** The generation form has a `dont_increment` option that should skip incrementing `used`.

**Steps:**
1. Note the **Used** count for a template.
2. Generate an enemy from the template using the form, but inspect the POST data to confirm `dont_increment` is sent (or use the browser console to add the parameter).
3. Check the **Used** count after generation.

**Expected:** The **Used** count did not change.

**Note:** This test is harder to perform manually since the `dont_increment` parameter is not exposed in the UI. The automated test `test_get_enemies_no_increment` covers this path.

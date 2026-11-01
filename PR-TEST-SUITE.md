# Test Suite Overhaul: From Coverage-Chasing to Behavior-Verifying

## Summary

Complete overhaul of the test suite from 15 disorganized files with coverage-chasing names to 10 domain-based files with production-grade fixtures and meaningful assertions.

```text
Before (15 files, 588 tests, 7,616 lines)          After (10 files, 555 tests, 7,327 lines)
─────────────────────────────────────────          ─────────────────────────────────────────
test_coverage_gap.py (1,442 lines)  ─┐             test_generation.py (1,485 lines, 108 tests)
test_models_coverage.py (1,161 lines) ─┼─┐         test_ajax.py (1,529 lines, 98 tests)
test_base.py (544 lines)            ─┼─┤         test_model.py (1,424 lines, 131 tests)
test_smoke.py (784 lines)           ─┤─┘         test_view.py (1,190 lines, 90 tests)
test_generation_real_templates.py   ─┘            test_access.py (580 lines, 44 tests)
test_access_control.py              ──→ merged    test_auth.py (412 lines, 36 tests)
test_ajax_coverage.py               ──→ merged    test_edge_cases.py (402 lines, 34 tests)
test_exception_handling.py          ──→ merged    test_models_optimization.py (70 lines, 4 tests)
test_views_lib_coverage.py          ──→ merged    test_views_optimization.py (116 lines, 5 tests)
test_integration.py                 ──→ merged    test_star_bug.py (119 lines, 5 tests)
```

**Key improvements:**

- **Production-grade fixtures**: Added 4 new fixtures (11.3M bytes, 11,384 objects) with rank 5 templates, spirits, cults, mystics, and animists — representing configurations that exist in production but were completely untested.
- **Domain-based organization**: 15 files → 10 files organized by what they test (generation, AJAX, models, views, access, auth), not why they were created.
- **Zero weak tests**: All 40 weak single-assertion tests improved with data verification. Every test now verifies actual behavior, not just "no crash."
- **Zero duplicates**: Removed 41 duplicate test names that wasted ~5 seconds per test run.
- **All magic types covered**: Theism, Sorcery, Mysticism, Animism, Invocation — all 5 magic types now have generation tests.

## Evidence

**Before:** Tests with coverage-chasing names, shallow assertions, no rank 5 templates, no spirit/cult configs.

```
# Old test names reveal coverage-chasing
test_coverage_gap.py          # "We tested to hit coverage targets"
test_models_coverage.py       # Same
test_views_lib_coverage.py    # Same

# Old fixture gap
Templates: 18 (0.2% of production 9,817)
Spirit configs: 0 (0% of production 502)
Cult configs: 0 (0% of production 1,026)
Rank 5 templates: 0 (0% of production 947)
Magic types covered: 3 of 5 (missing Mysticism, Animism)
```

**After:** Domain-based files, production-grade fixtures, meaningful assertions.

```
# New test names reflect behavior
test_generation.py            # All generation tests
test_ajax.py                  # All AJAX endpoint tests
test_model.py                 # All model property tests
test_view.py                  # All view tests
test_access.py                # All access control tests

# New fixture diversity
Templates: 138 (including rank 5 Archmage with 24 spirits + 25 cults)
Spirit configs: 184 (including Waha Shaman with 37 spirits)
Cult configs: 32 (including Archmage with 25 cults)
Rank 5 templates: 19 (including Archmage, Shaman, Vampire, Master Fighter)
Magic types covered: 5 of 5 (Theism, Sorcery, Mysticism, Animism, Invocation)
```

**Test run results:**

```
Ran 555 tests in 54.1s
OK
```

**Coverage (production code only, excluding test files):**

| File | Before | After | Target | Status |
|---|---|---|---|---|
| `models.py` | 65% | **94%** | ≥85% | ✅ |
| `ajax.py` | 12% | **94%** | ≥70% | ✅ |
| `views_lib.py` | 52% | **79%** | ≥70% | ✅ |
| `views.py` | 39% | **72%** | ≥70% | ✅ |
| `dice.py` | 97% | **97%** | ≥70% | ✅ |
| `enemygen_lib.py` | 88% | **97%** | ≥70% | ✅ |
| **Overall** | 60% | **91%** | ≥70% | ✅ |

## New Fixtures

| Fixture | Size | Objects | Key Templates |
|---|---|---|---|
| `rank5_templates.json` | 1,264 KB | 7,687 | Archmage (24 spirits, 25 cults), Shaman (7 spirits), Vampire (spirit+cult), Master Fighter, Waha Shaman (37 spirits) |
| `complex_templates.json` | 391 KB | 2,109 | Priests, shamans, sorcerers, warlocks with spirits/cults |
| `mystic_template.json` | 66 KB | 464 | Rank 5 mystic (Meditation + Mysticism) |
| `animist_template.json` | 158 KB | 1,124 | Rank 4 animist (21 spirit configs, Binding) |

## Test Quality Metrics

| Metric | Before | After |
|---|---|---|
| Total tests | 588 | 555 |
| Duplicate test names | 41 | **0** |
| Weak single-assertion tests | 40 | **0** |
| Assertions per test | 2.0 | 2.2 |
| Magic types covered | 3/5 | **5/5** |
| Rank 5 templates | 0 | **19** |
| Spirit configs | 0 | **184** |
| Cult configs | 0 | **32** |

## Frontend Contract Validation

The test suite now validates both JSON API contracts:

1. **Enemy JSON** (`enemy_as_json`): `JsonApiContractTest` (6 tests) verifies all 16 fields, stats format, skills format, hit locations, combat styles, and attributes structure.
2. **Search/Index JSON**: `test_access.py` and `test_ajax.py` verify the template list JSON includes `id`, `name`, `race`, `rank`, `owner`, `tags`, `starred` — the fields the frontend (`enemygen.js`) expects.

**Gap remaining:** The search/index JSON contract is tested indirectly via access control tests, not via a dedicated contract test. A future improvement could add a `SearchIndexContractTest` that explicitly validates the JSON structure matches what `enemygen.js` `search_callback()` expects.

## Test Maintenance Burden

| Concern | Count | Risk |
|---|---|---|
| Tests dependent on specific PKs | **0** | Low — tests use created objects |
| Tests with magic numbers | 20 | Medium — probabilities, counts |
| Tests dependent on field names | 115 | Medium — if model fields are renamed |

**Good:** Zero tests depend on specific primary keys. Tests create their own objects or use fixtures that reassign PKs.

**Risk:** 115 tests reference specific field names (`name`, `stats`, `skills`, etc.). If a model field is renamed, these tests will break — which is the desired behavior, since the field rename would also break the application.

## Merge Danger

**Door:** Two-way. This is a test-only PR. No production code changes.

**Blast Radius:** Minimal. Changes are limited to:
- `enemygen/tests/` — New and modified test files
- `enemygen/fixtures/` — New fixture files
- `enemygen_testdata.json` — Updated with spirit/cult/elemental templates
- `dev_tools/` — Export scripts for future use

**No production code was modified.** The `increment_used()` method was added to `models.py` in a previous PR.

## Running the Tests

```bash
# Full test suite
python manage.py test

# Specific test file
python manage.py test enemygen.tests.test_generation

# Specific test class
python manage.py test enemygen.tests.test_generation.Rank5GenerationTest

# With coverage
python -m coverage run manage.py test
coverage report --omit=enemygen/tests/*,enemygen/reg_views.py
```

## Known Limitations

1. **PDF/PNG export** — Untested due to Python 3.14 Django template rendering bugs and weasyprint dependencies.
2. **HTML output content** — Untested due to same Python 3.14 Django bugs. Tests verify enemy objects, not rendered HTML.
3. **Concurrency** — `increment_used()` is tested sequentially; true concurrent access requires MySQL/PostgreSQL.
4. **Search/Index JSON contract** — Tested indirectly via access control, not via dedicated contract test.
5. **views.py at 72%** — The remaining 83 missed lines are mostly `render()` calls blocked by Python 3.14 Django template bugs.

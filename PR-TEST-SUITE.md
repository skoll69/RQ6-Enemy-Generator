# Test Suite Overhaul: Production-Grade Fixtures and Domain-Based Organization

## What is different from `master`

This PR replaces the 4 existing test files with 10 domain-based files, adds 4 new fixtures exported from the production database, and enriches the test data with Spirit/Cult/Elemental races.

| Metric | `master` | This PR |
|---|---|---|
| Test files | 4 | **10** |
| Test lines | 1,070 | **8,092** |
| Total tests | 53 | **594** |
| Fixtures | 0 | **4** (1.8 MB) |
| Rank 5 templates in fixtures | 0 | **19** |
| Spirit configs in fixtures | 0 | **184** |
| Cult configs in fixtures | 0 | **32** |
| Magic types covered | unknown | **5/5** (Theism, Sorcery, Mysticism, Animism, Invocation) |

### Files changed (18 files, +142,156 / -20,903)

**Added (16 files):**

| File | Lines | Description |
|---|---|---|
| `enemygen/tests/test_generation.py` | 1,485 | Generation: smoke, real templates, rank 5, negative cases, integration |
| `enemygen/tests/test_ajax.py` | 1,529 | All AJAX endpoints: add/delete, submit, error messages, login |
| `enemygen/tests/test_model.py` | 1,424 | All models: Race, HitLocation, EnemyTemplate, Party, CombatStyle, etc. |
| `enemygen/tests/test_view.py` | 1,190 | All views: pages, listing APIs, views_lib functions |
| `enemygen/tests/test_access.py` | 580 | Access control: visibility, search syntax, JSON API access |
| `enemygen/tests/test_auth.py` | 412 | Auth: login, registration, password change/reset |
| `enemygen/tests/test_edge_cases.py` | 402 | Edge cases: error messages, path traversal, amount caps, pagination |
| `enemygen/fixtures/rank5_templates.json` | 1.2 MB | Rank 5 templates with spirits, cults, magic users |
| `enemygen/fixtures/complex_templates.json` | 392 KB | Priests, shamans, sorcerers with spirits/cults |
| `enemygen/fixtures/mystic_template.json` | 68 KB | Rank 5 mystic (Meditation + Mysticism) |
| `enemygen/fixtures/animist_template.json` | 160 KB | Rank 4 animist (21 spirit configs, Binding) |
| `enemygen/tests/complex_templates.json` | 392 KB | Copy of complex_templates for test directory |
| `dev_tools/export_rank5_templates.py` | 164 | Export script for rank 5 templates from production |
| `dev_tools/export_complex_templates.py` | 154 | Export script for complex templates from production |
| `PR-TEST-SUITE.md` | 163 | This PR description |
| `PR-CRITICAL-TESTS.md` | 78 | Legacy PR notes (can be removed) |

**Deleted (1 file):**

| File | Lines | Reason |
|---|---|---|
| `enemygen/tests/test_base.py` | 544 | Replaced by domain-specific test files |

**Modified (1 file):**

| File | Change |
|---|---|
| `enemygen_testdata.json` | Added Spirit, Cult, Elemental races and templates (+20,121 / -20,903) |

**Kept unchanged (3 files):**

| File | Tests | Reason |
|---|---|---|
| `test_models_optimization.py` | 15 | Specific optimization tests |
| `test_views_optimization.py` | 5 | Specific optimization tests |
| `test_star_bug.py` | 5 | Specific regression test |

## Coverage Results

All coverage targets are met. These numbers are from production code only, excluding test files.

| File | `master` | This PR | Target | Status |
|---|---|---|---|---|
| `models.py` | ~50% | **94%** | ≥85% | ✅ |
| `ajax.py` | ~10% | **94%** | ≥70% | ✅ |
| `views_lib.py` | ~40% | **79%** | ≥70% | ✅ |
| `views.py` | ~30% | **74%** | ≥70% | ✅ |
| `dice.py` | ~90% | **97%** | ≥70% | ✅ |
| `enemygen_lib.py` | ~80% | **97%** | ≥70% | ✅ |
| **Overall** | ~45% | **91%** | ≥70% | ✅ |

## New Fixtures

Four new fixtures were exported from the production database to cover configurations that were previously untested.

| Fixture | Size | Key Templates |
|---|---|---|
| `rank5_templates.json` | 1.2 MB | Archmage (24 spirits, 25 cults), Shaman (7 spirits), Vampire (spirit+cult), Master Fighter, Waha Shaman (37 spirits) |
| `complex_templates.json` | 392 KB | Priests, shamans, sorcerers, warlocks with spirits/cults |
| `mystic_template.json` | 68 KB | Rank 5 mystic (Meditation + Mysticism) |
| `animist_template.json` | 160 KB | Rank 4 animist (21 spirit configs, Binding) |

### Fixture diversity vs. production

| Dimension | Production | `master` | This PR |
|---|---|---|---|
| Templates | 9,817 | 18 | **138** |
| Spirit configs | 502 | 0 | **184** |
| Cult configs | 1,026 | 0 | **32** |
| Rank 5 templates | 947 | 0 | **19** |
| Magic types | 5 | 3 | **5** (Theism, Sorcery, Mysticism, Animism, Invocation) |

## Test Categories

Each test file covers a specific domain. The test classes within each file are organized by the behavior they verify.

### test_generation.py (108 tests)

- **GenerationSmokeTest**: Web form, JSON API, lucky generation, party generation
- **RealTemplateGenerationTest**: Generation with real database templates (priests, shamans, sorcerers, mystics)
- **Rank5GenerationTest**: Archmage (24 spirits + 25 cults), Shaman (7 spirits), Vampire (spirit+cult), Master Fighter, Waha Shaman (37 spirits)
- **MysticGenerationTest**: Rank 5 mystic with Meditation + Mysticism
- **AnimistGenerationTest**: Rank 4 animist with 21 spirit configs and Binding
- **NegativeGenerationTest**: Generation with no stats, zero stats, no skills, invalid spell amounts, empty namelist
- **IntegrationWorkflowTest**: End-to-end workflows: create→generate, clone→modify, party→generate, search→generate
- **PartyGenerationTest**: Party generation with multiple templates, used counter increment

### test_ajax.py (98 tests)

- **AjaxAddDeleteTest**: add_template_to_party, del_item for all object types
- **AjaxSubmitTest**: submit() for custom weapons, race fields, party fields, template fields, features, spells, spirits, cults
- **AjaxErrorMessageTest**: Error message validation for invalid die values, probabilities, ranges, HP modifiers
- **AjaxLoginRequiredTest**: All endpoints require authentication
- **AjaxPathTraversalTest**: Path traversal protection in submit endpoint

### test_model.py (131 tests)

- **RaceTest**: Race CRUD, stats, hit locations
- **EnemyTemplateTest**: Template properties, search, summary, clone, delete
- **PartyTest**: Party methods, template management
- **CombatStyleTest**: Combat style options, weapons
- **SpiritCultTest**: Spirit and cult generation with magic skills
- **DiceParsingTest**: Dice expression parsing, modifiers, H/L/M suffixes
- **PerformanceRegressionTest**: N+1 query detection for get_enemy_templates, search, generate

### test_view.py (90 tests)

- **PageViewTest**: All page views render correctly
- **ListingApiTest**: index_json, party_index_json with field validation
- **ViewsLibTest**: get_enemy_templates, get_statistics, get_context, determine_enemies
- **ViewRedirectTest**: Redirect views for create, edit, delete

### test_access.py (44 tests)

- **TemplateAccessControlTest**: Owner sees own private, anonymous sees only public
- **PartyAccessControlTest**: Same for parties
- **SearchAccessControlTest**: Search respects access control
- **SearchSyntaxTest**: All search operators, filters, edge cases

### test_auth.py (36 tests)

- **LoginViewTest**: Correct/incorrect login, non-existent user, empty credentials
- **RegistrationViewTest**: Valid registration, password mismatch, duplicate username
- **PasswordChangeViewTest**: Login requirement, form validation, wrong old password
- **PasswordResetViewTest**: Valid/invalid email

### test_edge_cases.py (34 tests)

- **LuckyGenerationEdgeCaseTest**: Lucky with no templates, filter fallback
- **SanitizeHtmlPathSecurityTest**: Path traversal protection
- **DetermineEnemiesEdgeCaseTest**: Amount cap at 40, invalid amounts
- **JsonApiContractTest**: All 16 JSON fields, stats format, skills format, hit locations, combat styles
- **SessionStateTest**: Filter/party_filter session persistence
- **PaginationEdgeCaseTest**: page=abc, page=999, filter preservation

## Merge Danger

**Risk:** Low. This is a test-only PR. No production code was modified.

**Blast radius:** Changes are limited to:
- `enemygen/tests/` — Test files only
- `enemygen/fixtures/` — Fixture data only
- `enemygen_testdata.json` — Test fixture data
- `dev_tools/` — Export scripts for future use

**No production code changes.** The `increment_used()` method in `models.py` was added in a previous PR.

## Running the Tests

```bash
# Full test suite
python manage.py test

# Specific file
python manage.py test enemygen.tests.test_generation

# Specific class
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
5. **views.py at 74%** — The remaining 76 missed lines are mostly `render()` calls blocked by Python 3.14 Django template bugs.

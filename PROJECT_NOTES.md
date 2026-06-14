# Mythras Encounter Generator Project Notes

This file is a working reference for future Codex sessions in this repo.

## Purpose

Mythras Encounter Generator is a Django web app for Mythras/RuneQuest 6 game masters. Registered users create and maintain randomizable templates for enemies, races, cults, spirits, parties, weapons, spells, skills, names, and extra features. Public users can browse published templates/parties and generate encounters from them.

Hosted project per `readme.md`: `https://mythras.skoll.xyz/`.

## Stack

- Python/Django project, tested by the maintainer with Python 3.11.
- Django 3.2.25, MySQL via `pymysql`, `django-registration`, `django-taggit`, `django-extensions`.
- WeasyPrint and Pillow are used for PDF/PNG export of generated encounter HTML.
- Frontend is server-rendered Django templates with jQuery/axios helpers in `static/js/enemygen.js`.
- Settings are not committed; copy `mythras_eg/settings_example.py` to `mythras_eg/settings.py`.
- Tests: `python manage.py test`.

## Top-Level Layout

- `manage.py`: Django entry point.
- `mythras_eg/`: project settings example, root URLs, WSGI, simple CORS middleware.
- `enemygen/`: main app. Most domain and generation logic is here.
- `enemygen/templates/`: app templates for browsing, editing, generation output, parties, races, etc.
- `templates/`: auth/registration templates.
- `static/`: CSS, JS, images, copied Django admin static assets.
- `enemygen_testdata.json`: fixture used by tests.
- `dump.sql` / `dump.sql.bak`: large database dumps, avoid touching unless explicitly asked.
- `temp/`: required runtime output directory for generated HTML/PDF/PNG files.

## Important Entry Points

- Root URL config: `mythras_eg/urls.py`.
- App URL config: `enemygen/urls.py`.
- HTML views and public JSON views: `enemygen/views.py`.
- Shared view/generation helpers and JSON serialization: `enemygen/views_lib.py`.
- Inline edit and AJAX endpoints: `enemygen/ajax.py`.
- Domain models and generated enemy runtime classes: `enemygen/models.py`.
- Dice parser/roller: `enemygen/dice.py`.
- Weighted random helpers: `enemygen/enemygen_lib.py`.
- Admin registrations: `enemygen/admin.py`.
- CORS for public JSON endpoints: `mythras_eg/middleware.py`.

## Domain Model

Most models live in `enemygen/models.py`.

Core authoring models:

- `Ruleset`: currently mainly RuneQuest 6/Mythras data holder for stats, skills, races.
- `Race`: movement, notes/special text, hit locations, race stat defaults, flags for `discorporate` spirits and `elemental`.
- `HitLocation`: race-level hit location ranges, armor, and HP modifiers.
- `EnemyTemplate`: central template model. Owns race, rank, spell amounts, cult/spirit amounts, notes, tags, name list, natural armor flag, weapon filter, publication state, and counters.
- `Party`: published or user-owned encounter packages made of template plus amount specs.
- `TemplateToParty`: joins a party to an enemy template with an amount dice expression.
- `CombatStyle`: template combat skill and weapon selection amounts by weapon type.
- `Weapon`: admin-created system weapons, tag-filtered.
- `EnemyWeapon` / `CustomWeapon`: per-combat-style weighted weapon options.
- `SkillAbstract`, `EnemySkill`, `CustomSkill`: base skills and per-template/custom skill formulas.
- `StatAbstract`, `RaceStat`, `EnemyStat`: base stats, race defaults, template stat dice expressions.
- `SpellAbstract`, `EnemySpell`, `CustomSpell`: base and custom spell options with probabilities/details.
- `EnemySpirit`, `EnemyCult`: weighted links from a template to possible spirit/cult templates.
- `AdditionalFeatureList`, `AdditionalFeatureItem`: reusable weighted lists for names, enemy features, and party features.
- `EnemyAdditionalFeatureList`, `PartyAdditionalFeatureList`: weighted feature-list attachments.
- `EnemyNonrandomFeature`, `PartyNonrandomFeature`: fixed feature attachments.
- `Star`: per-user favorite templates.
- `ChangeLog`: "what's new" content.

Generated runtime objects:

- `_Enemy`: in-memory generated enemy, not a DB model.
- `_Spirit`: special generation rules for discorporate races.
- `_Elemental`: special generation rules for elemental races.
- `_Cult`: special generated object used to add cult spells/spirits to enemies.

## Generation Flow

Common HTML generation path:

1. `views.generate_enemies()` receives POSTed `enemy_template_id_<id>` amount fields.
2. `views_lib.determine_enemies()` resolves templates and clamps each amount to max 40.
3. `views_lib.get_enemies()` calls `EnemyTemplate.increment_used()` and `EnemyTemplate.generate(suffix, increment)`.
4. `EnemyTemplate.generate()` chooses `_Enemy`, `_Spirit`, `_Elemental`, or `_Cult` based on race/template flags.
5. Runtime object rolls stats, skills, spells, features, hit locations, attributes, spirits/cults, combat styles, and weapons.
6. `views_lib.save_as_html()` renders `generated_enemies.html` to `settings.TEMP` for later PDF/PNG export.

Public JSON generation:

- `GET /generate_enemies_json/?id=<template_id>&amount=<n>` returns `views_lib.as_json(get_enemies(...))`.
- `GET /generate_party_json/?id=<party_id>` returns generated party enemies and party features.
- JSON serialization is in `views_lib.enemy_as_json()`.
- `SimpleCorsMiddleware` adds permissive CORS only for public JSON endpoints: `/index_json/`, `/party_index_json/`, `/generate_enemies_json/`, `/generate_party_json/`.

Party generation:

- `views.generate_party()` picks a submitted party or a random published one for "lucky".
- `views_lib.get_generated_party()` generates each `TemplateToParty` amount and party-level random/nonrandom features.

## Dice and Randomness

- Dice syntax is parsed by `Dice` in `enemygen/dice.py`; examples: `D6`, `2D6-D4+5`, plain numbers.
- `dice.clean()` normalizes formulas, combines similar dice components, and keeps stat names such as `STR`/`DEX`.
- Formulas can contain stat names; `enemygen_lib.replace_die_set()` substitutes rolled stat values before rolling.
- Weighted choices use `select_random_item()` and `select_random_items()` in `enemygen/enemygen_lib.py`. Items need a numeric `probability`.
- Several model setters validate dice expressions by constructing/rolling `Dice`.

## Editing Flow

- Most inline field edits go through `POST /rest/submit/<id>/`, implemented as a long `if/elif` dispatcher in `enemygen/ajax.py`.
- The frontend helper `submit()` in `static/js/enemygen.js` posts `{ value, object, parent_id }`.
- Add/delete actions have dedicated REST-ish endpoints in `enemygen/ajax.py`, for example custom spells/skills/weapons, spirits, cults, hit locations, party templates, features, tags, stars, and weapon filtering.
- `POST /rest/change_template/` edits previously generated HTML in `settings.TEMP`; it uses `sanitize_html_path()` and returns JSON errors for invalid file names or missing target spans.
- Ownership checks are uneven. Some submit branches filter by `owner=request.user`; some direct add/delete branches fetch by ID without owner checks. Be careful when changing auth-sensitive behavior.

## Browsing and Search

- `views.home()` shows starred templates.
- `views.index()` shows public/personal templates by session filter.
- `views.party_index()` shows published parties by session filter.
- `ajax.search()` calls `EnemyTemplate.search()` and returns `summary_dict()` rows for the frontend table.
- Tags are handled by `django-taggit`; template/party filters use tag names stored in the session.

## Export Flow

- Generated HTML is saved into `settings.TEMP`.
- `views.pdf_export()` calls `views_lib.sanitize_html_path()` then `generate_pdf()`.
- `views.png_export()` calls `sanitize_html_path()` then `generate_pngs()`.
- `sanitize_html_path()` guards against path traversal by requiring a basename with `.html`, resolving under `settings.TEMP`, and checking file existence. It is also reused by `ajax.change_template()`.
- WeasyPrint install is OS-specific; tests or local runs involving export may fail if native dependencies are absent.

## Tests

- Main tests are in `enemygen/tests.py`.
- Fixture: `enemygen_testdata.json`.
- Coverage includes dice parsing/rolling, template creation, enemy generation, attributes, hit locations, spirit damage calculation, weighted selection, JSON shape, common context creation, generated HTML editing, and CORS middleware.
- Use the repository virtualenv on this Windows workspace: `.\.venv\Scripts\python.exe manage.py test`. The system `python` was Python 3.12 and crashed with a Windows access violation during test startup; the project README says Python 3.11 is the tested version.
- There is at least one disabled test-like method: `notest_16_generate_check_weapon_styles`.

## Practical Caveats

- `models.py` is large and mixes persisted models with runtime generation classes. Read local context before moving logic.
- Query properties often return QuerySets and are used in templates; changing them to lists can affect downstream behavior.
- `EnemyTemplate.is_cult` depends on `race.name == 'Cult'`, not a dedicated flag.
- `Race.set_published()` validates non-discorporate hit locations cover the full 1-20 range.
- `select_random_item()` assumes total probability is positive; callers usually filter probability > 0 or use non-empty option lists, but not universally.
- `settings_example.py` includes development defaults and empty secrets/passwords; do not treat it as production-safe.

## Common Commands

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item mythras_eg\settings_example.py mythras_eg\settings.py
python manage.py test
python manage.py runserver
```

The local database is expected to be configured in `mythras_eg/settings.py`. The committed settings example uses MySQL database `mythras_eg`.

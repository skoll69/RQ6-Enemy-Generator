# Mythras Encounter Generator System Overview

## Purpose

Mythras Encounter Generator is a server-rendered Django application for creating
randomized enemies and parties for Mythras/RuneQuest 6. Users define reusable
templates containing characteristic formulas, skills, equipment, magic, and
other options. The application rolls those definitions to produce encounter
stat blocks in HTML, JSON, PDF, or PNG format.

Generated enemies are temporary Python objects. The database stores their
templates and supporting reference data, but it does not store each generated
enemy.

## Architecture

The main request flow is:

```text
Browser
  -> Django URL routing
  -> Views or AJAX handlers
  -> Generation and orchestration logic
  -> Django ORM and database
  -> HTML, JSON, PDF, or PNG response
```

The project uses the following layers:

- `mythras_eg/` contains project-level Django settings, URL routing,
  middleware, and the WSGI entry point.
- `enemygen/views.py` handles pages, generation requests, public JSON
  endpoints, and exports.
- `enemygen/ajax.py` handles browser-driven searches and data modifications.
- `enemygen/views_lib.py` coordinates requests, model operations,
  serialization, and export processing.
- `enemygen/models.py` contains the database model and most of the domain and
  generation logic.
- `enemygen/dice.py` parses and evaluates dice expressions.
- `enemygen/enemygen_lib.py` contains shared helpers such as weighted random
  selection and characteristic substitution.
- `enemygen/templates/` contains server-rendered HTML templates.
- `static/js/` contains the jQuery and Axios browser behavior.

Most of the business logic is concentrated in `enemygen/models.py`. The
application does not use a separate REST service or background job system.

## Entry Points

### Development and Administration

`manage.py` is the Django command-line entry point. It configures
`mythras_eg.settings` and delegates to Django's management commands.

Common commands are:

```bash
python3 manage.py migrate
python3 manage.py loaddata enemygen_testdata.json
python3 manage.py runserver
python3 manage.py test
```

### Production

`mythras_eg/wsgi.py` exposes the WSGI application. The provided deployment
script, `setup.sh`, is designed to run it through Gunicorn behind Nginx.

### URL Routing

`mythras_eg/urls.py` provides project-level routing for:

- Django administration under `/admin/`
- Registration and authentication under `/accounts/`
- Application routes from `enemygen/urls.py`

`enemygen/urls.py` defines the pages, generation endpoints, JSON interfaces,
and AJAX operations.

## Persistent Domain Model

The application stores reusable encounter definitions in SQLite or MySQL. The
complete application schema is represented by the Django models in
`enemygen/models.py` and the initial migration in
`enemygen/migrations/0001_initial.py`.

### Enemy Templates

`EnemyTemplate` is the central persistent model. A template can reference:

- A ruleset and race
- Characteristic and skill formulas
- Hit locations and armor formulas
- Combat styles and possible weapons
- Folk magic, theism, sorcery, and mysticism spells
- Spirits and cult packages
- Fixed and random features
- A random name list
- Tags, rank, movement, notes, and publication state

Creating a normal template copies initial characteristics, skills, movement,
notes, and hit locations from its race. It also creates a default primary
combat style. Spirit and cult templates follow specialized initialization
paths.

### Races

A `Race` defines defaults shared by enemy templates, including:

- Characteristic formulas
- Movement
- Notes and special rules
- Hit-location ranges
- Hit-location armor formulas and hit-point modifiers
- Whether the race represents a spirit or elemental

Publishing a normal race validates that its hit-location ranges cover all
results from 1 through 20.

### Catalog Data

Shared catalog records include:

- Characteristics
- Skills
- Weapons
- Spells
- Rulesets

Template-specific records point to these catalogs and add formulas,
probabilities, inclusion flags, or descriptive details.

### Parties

A `Party` is a collection of enemy templates. `TemplateToParty` associates a
template with a party and stores the number of enemies as a dice expression.
For example, a party can contain `1D4+2` guards and one captain.

Parties can also have fixed and random party-level features.

### Features and Names

`AdditionalFeatureList` and `AdditionalFeatureItem` represent reusable lists
for:

- Enemy features
- Party features
- Random names

Enemy feature probabilities can use formulas based on generated
characteristics. Party features use integer percentage probabilities. Name
lists reuse the same list and item structure.

### Favorites and Tags

Django Taggit supplies tags for templates, parties, and weapons. The `Star`
model associates a user with a favorite enemy template.

## Dice Expressions

`enemygen/dice.py` supports expressions such as:

```text
3D6
2D6+6
1D10-D4+5
```

Formulas can also refer to generated characteristics:

```text
STR+DEX+20
POW+POW
```

Characteristic tokens are replaced with their rolled integer values before
the remaining expression is evaluated. The dice module can calculate both a
random result and the maximum possible result.

## Enemy Generation

### Request Parsing

The HTML generation form submits fields with names such as:

```text
enemy_template_id_42=3
```

`determine_enemies()` in `enemygen/views_lib.py` reads these fields, resolves
the selected templates, removes non-positive amounts, limits each amount to
40, and sorts the templates by descending rank.

### Runtime Objects

`EnemyTemplate.generate()` selects an appropriate runtime class:

- `_Enemy` for a normal creature
- `_Spirit` for a spirit
- `_Cult` for a package of cult-related magic and spirits
- `_Elemental` for an elemental

These objects are generated in memory for the current request and are not
saved as database rows.

### Normal Enemy Pipeline

`_Enemy.generate()` performs generation in this order:

1. Generate a name.
2. Roll characteristics.
3. Roll included skills.
4. Select spells.
5. Select additional features.
6. Calculate armor and hit points for each hit location.
7. Calculate derived attributes.
8. Generate bound spirits when applicable.
9. Apply selected cult packages.
10. Roll combat styles and select weapons.

This order is significant. Skills, feature probabilities, hit points, and
derived attributes can depend on characteristics rolled earlier in the
pipeline.

### Names

By default, an enemy's name is based on its template name and optional sequence
number. If the template has a name list, a randomly selected name is prepended
to the generated label.

An example result is:

```text
Hrothgar (Town Guard 1)
```

### Characteristics and Skills

Each characteristic formula is rolled independently. Skill formulas then
replace characteristic names with those generated values.

For example:

```text
STR = 3D6
DEX = 2D6+6
Athletics = STR+DEX
```

The application rolls `STR` and `DEX` first, substitutes both values into the
Athletics expression, and evaluates the result.

### Weighted Selection

Spells, weapons, spirits, and cults use weighted random selection without
replacement. The configured values are relative weights rather than direct
percentages.

For example:

```text
Sword: 5
Spear: 3
Axe:   2
```

The sword has five units of probability out of ten total units. Once an item
has been selected, it cannot be selected again during the same operation.

The shared implementation is in `enemygen/enemygen_lib.py`.

### Magic

The generator supports separate amount formulas and weighted options for:

- Folk magic
- Theism
- Sorcery
- Mysticism

Cult templates can add spells and spirits to a normal enemy. Duplicate spells
are removed after cult packages have been applied.

### Hit Locations

Normal enemies calculate base hit points using `CON` and `SIZ`:

```text
base hit points = ceil((CON + SIZ) / 5)
location hit points = max(base hit points + location modifier, 1)
```

Armor is rolled separately from the armor formula assigned to each hit
location.

### Derived Attributes

The generator derives values including:

- Action points
- Damage modifier
- Magic points
- Strike rank
- Armor penalty
- Movement
- Devotional pool and theism intensity
- Sorcery shaping and intensity
- Mysticism intensities
- Animist spirit limits

Representative formulas include:

```text
natural strike rank = (INT + DEX) // 2
action points = ceil((DEX + INT) / 12)
magic points = POW
```

Armor encumbrance reduces strike rank unless armor is marked as natural.

### Combat Styles and Weapons

For each combat style, the generator:

1. Rolls the style's skill value.
2. Rolls how many weapons to choose from each category.
3. Selects weapons using their relative weights.
4. Adjusts weapon size and reach for unusually large or small creatures.

Weapon categories are one-handed melee, two-handed melee, ranged, and shield.

### Spirits and Cults

Animist enemies can receive bound spirits. The generator attempts to keep a
spirit's POW within the enemy's calculated spirit limit, rerolling a limited
number of times when necessary.

Cult templates act as packages rather than complete creatures. Applying a cult
can merge cult spells and spirits into a normal enemy.

### Spirit and Elemental Generation

Spirits omit physical hit locations and conventional combat styles. They
derive several physical characteristics from POW and calculate spirit-specific
attributes such as intensity and spirit damage.

Elementals derive several characteristics from STR and POW and use their own
hit-point calculation.

## Party Generation

A party request follows this process:

1. Load the selected party, or select one from the active filters.
2. Roll each `TemplateToParty.amount` expression.
3. Generate that many instances of each enemy template.
4. Update usage and generation counters.
5. Select party-level fixed and random features.
6. Render the result using the generated-enemies template.

Party orchestration is implemented in `enemygen/views_lib.py`.

## Web Interface

### Search and Generation

The home page provides a search-first workflow:

1. The browser searches by text, rank, or cult rank.
2. Axios sends the query to `/rest/search/`.
3. Matching templates are displayed.
4. The user selects templates and quantities.
5. The form submits the selection to `/generate_enemies/`.
6. Django generates and returns complete stat-block HTML.

The full enemy and party pages provide additional browsing and tag filtering.

### Content Editing

Authenticated users can manage their own templates, parties, and related
content. Most editor fields save when their value changes:

```text
Browser field changes
  -> JavaScript submit function
  -> POST /rest/submit/<id>/
  -> enemygen.ajax.submit()
  -> Django ORM update
  -> JSON success or error response
```

Structural changes, such as adding a weapon or spell, usually reload the page
after a successful AJAX request.

### Cloning

Logged-in users can clone shared templates or parties. Template cloning copies
most template-specific relationships so the user receives an independently
editable copy.

### Generated Results

`enemygen/templates/generated_enemies.html` displays generated
characteristics, attributes, hit locations, skills, magic, spirits, features,
combat styles, and weapons.

Displayed names and notes can be edited in the result page. These changes
modify the temporary export snapshot only; they do not change the underlying
enemy template.

## HTTP Interfaces

### Main Pages

Important routes include:

| Route | Purpose |
| --- | --- |
| `/` | Search and select enemy templates |
| `/enemies/` | Browse enemy templates |
| `/parties/` | Browse parties |
| `/edit_index/` | Manage user-owned content |
| `/enemy_template/<id>/` | View or edit an enemy template |
| `/race/<id>/` | View or edit a race |
| `/party/<id>/` | View or edit a party |
| `/statistics/` | View application statistics |
| `/instructions/` | View in-application help |

### Generation and JSON

Important generation routes include:

| Route | Output |
| --- | --- |
| `/generate_enemies/` | Generated encounter HTML |
| `/generate_party/` | Generated party HTML |
| `/index_json/` | Enemy template index JSON |
| `/party_index_json/` | Party index JSON |
| `/generate_enemies_json/?id=N&amount=M` | Generated enemy JSON |
| `/generate_party_json/?id=N` | Generated party JSON |

`enemy_as_json()` in `enemygen/views_lib.py` serializes characteristics,
skills, spells, hit locations, combat styles, weapons, attributes, features,
cults, and nested spirits.

### AJAX

AJAX routes under `/rest/` support operations such as:

- Searching
- Saving editor fields
- Managing favorites
- Adding or removing skills, spells, weapons, spirits, and cults
- Managing party members
- Filtering available weapons

The browser implementation is primarily in `static/js/enemygen.js` and
`static/js/helpers.js`.

## Output and Export Processing

### HTML

Django renders generated encounters with
`enemygen/templates/generated_enemies.html`. A uniquely named copy is also
stored in the configured `temp/` directory for subsequent editing and export.

### PDF

PDF export reopens the stored HTML and converts it using WeasyPrint.

### PNG

PNG export separates the generated enemy containers, renders each container
with WeasyPrint, and crops the resulting image using Pillow.

Export requests validate that the requested HTML file remains inside the
configured temporary directory.

Generated temporary files are not automatically removed by the application.

## Authentication and Visibility

Authentication uses Django's built-in authentication system together with
`django-registration`.

The intended content visibility rules are:

- Anonymous users can browse published templates and parties.
- Authenticated users can also see their own unpublished content.
- Non-owners receive a not-found response when opening unpublished template or
  party detail pages.
- Owners receive editable pages; other users receive read-only pages.

Race administration also uses membership in a `race_admin` group.

Visibility checks are implemented in several view and query functions rather
than in one centralized authorization layer. New endpoints should therefore
apply explicit publication and ownership checks instead of assuming they are
inherited automatically.

## Configuration

The checked-in `mythras_eg/settings.py` uses SQLite for local development.
`mythras_eg/settings_example.py` demonstrates MySQL configuration and includes
SMTP and error-email settings suitable for further production configuration.

Important configuration areas include:

- Database connection
- `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS`
- Static file directories
- Temporary export directory
- Authentication redirects
- CORS origin allowlist
- SMTP settings

The public JSON generation endpoints receive permissive cross-origin response
headers from `mythras_eg/middleware.py`. Other cross-origin access depends on
the configured allowlist.

## Development Setup

For the automated SQLite setup:

```bash
chmod +x dev_tools/setup_sqlite.sh
./dev_tools/setup_sqlite.sh
python3 manage.py runserver
```

For a manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
mkdir -p temp
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py loaddata enemygen_testdata.json
python3 manage.py runserver
```

The development server is available at:

```text
http://127.0.0.1:8000/
```

See `dev_tools/SQLITE_DEV.md` for the full SQLite setup and MySQL-to-SQLite import
instructions.

## Testing

Run the Django test suite with:

```bash
python3 manage.py test
```

The tests in `enemygen/tests.py` cover the dice engine, core enemy generation,
skill formulas, weighted selection, JSON serialization, and CORS behavior.

The repository currently has no browser test suite, JavaScript test suite, or
automated PDF/PNG integration tests.

## Deployment

Production serves `mythras_eg.wsgi:application`, normally through Gunicorn and
Nginx. The provided `setup.sh` installs infrastructure packages and creates
Gunicorn service definitions for an Ubuntu-style host.

The script is not a complete unattended release process. Production deployment
must additionally provide:

- Application code in the expected deployment directory
- Production settings and secrets
- Database creation, migration, and data import
- Static-file collection and Nginx configuration
- TLS certificates
- Appropriate system users and permissions
- Temporary-file cleanup and operational monitoring

Install the platform-specific WeasyPrint dependencies before enabling PDF or
PNG export. The project `readme.md` links to the official WeasyPrint installation
instructions.

## End-to-End Example

A typical request works as follows:

1. A user opens `/` and searches for an enemy template.
2. JavaScript requests matching templates from `/rest/search/`.
3. The user selects templates and enters quantities.
4. The browser posts the selection to `/generate_enemies/`.
5. `determine_enemies()` resolves and validates the requested templates.
6. `get_enemies()` invokes `EnemyTemplate.generate()` for each instance.
7. The runtime generator rolls characteristics, skills, magic, features, hit
   locations, attributes, spirits, cults, combat styles, and weapons.
8. Django renders the generated stat blocks as HTML.
9. A second copy is stored in `temp/` for PDF or PNG export.
10. Usage and generation counters are persisted in the database.

In summary, the system stores configurable Mythras enemy blueprints in Django
models, evaluates their formulas and weighted options into temporary encounter
objects, and presents the results through web pages, JSON APIs, PDFs, or images.

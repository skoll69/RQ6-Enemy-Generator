# Mythras Encounter Generator

A tool for Mythras GM's for generating enemy stats.

Hosted at https://mythras.skoll.xyz/

## Dev env installation

Mythras Encounter Generator has been tested with Python 3.10. Other versions might or might not work.

Database requirements:
- recommended: MySQL 8.4+)
- MariaDB 10.3 or newer (not tested with these instructions)

These versions are compatible with Django 3.2 (used by this project) when using the PyMySQL driver.

* Copy `mythras_eg/settings_example.py` to `mythras_eg/settings.py`
  * Fill in DB configuration
* It is recommended to create a virtualenv
* Install requirements from `requirements.txt`
* Create a folder named `temp` in the project directory (it's not possible to add empty folders to git)

### WeasyPrint

If you want to use PDF/PNG export features, follow OS-specific installation instructions for WeasyPrint at
https://doc.courtbouillon.org/weasyprint/stable/

## Start Dev env

### Option A: Local MySQL already installed

`python manage.py runserver`

### Option B: Run with Docker (recommended)

You can run MySQL 8 locally using the standard Docker CLI. This matches our Makefile and the infra tests under tests/infradocker.

Prerequisites:
- Docker (or Rancher Desktop providing a docker-compatible CLI)
- .env at project root with at least: MYSQL_ROOT_PASSWORD. Optionally set DB_NAME/DB_USER/DB_PASSWORD used by Django.

Quick start using Makefile targets:
- make start-db         # starts MySQL in container mythras-mysql at 127.0.0.1:3308
- make mysql-create-user  # (optional) create app user and grant privileges for DB_NAME
- make show-db-env      # prints effective DB host/port/name for your Django .env
- make logs-db          # view container logs
- make stop-db          # stop/remove the container

Manual Docker command (equivalent to make start-db):
```
docker rm -f mythras-mysql >/dev/null 2>&1 || true
MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD \
docker run --name mythras-mysql \
  -p 127.0.0.1:3308:3306 \
  -e MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  -d docker.io/library/mysql:8
```

After the DB is running:
- python manage.py migrate
- (Optional) python manage.py loaddata enemygen_testdata.json
- python manage.py runserver

Importing a dump with Docker:
- Place dump.sql at project root
- make upload-dump           # uses docker by default in this Makefile
- make upload-dump-compat    # enables MySQL 8 compatibility normalization

Shell helpers (Docker):
- make mysql-shell           # app user shell inside container
- make mysql-shell-root      # root shell inside container

Notes:
- Our Django settings load .env automatically (python-dotenv). Key vars: DB_NAME, db_user/DB_USER, db_password/DB_PASSWORD, DB_HOST, DB_PORT. Defaults match the Docker setup (127.0.0.1:3308).
- Infra tests that exercise Docker require docker CLI and MYSQL_ROOT_PASSWORD in .env. Use pytest -m infra to run them.

<!-- Apple container documentation has been moved to README-APPLE-CONTAINER.md -->

Use ONLY the following exact command to start MySQL (reads password from your shell env or .env):

### Option A: Local MySQL already installed

`python manage.py runserver`

### Option B: Start MySQL 8 with Docker (required syntax)

Use ONLY the following exact command to start MySQL (reads password from your shell env or .env):

```
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3308:3306 \
  --volume "$HOME/container-data/mysql:/var/lib/mysql" \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
```
<!-- Previous (no volume) kept for reference:
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3308:3306 \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
-->

Then, in another terminal:
- python manage.py migrate
- (Optional) python manage.py loaddata enemygen_testdata.json
- python manage.py runserver

The Django settings read configuration from environment variables and will automatically load a .env file at the project root during development (via python-dotenv). Key variables: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_SSL_CA (optional), SECRET_KEY, DEBUG, ALLOWED_HOSTS, TIME_ZONE, ADMIN_EMAILS, and EMAIL_* (see .env.example). Defaults match our container setup and expose MySQL on 127.0.0.1:3308 when using the Makefile Docker target.


## Automatic import on first run (container datastore area)

If you want the MySQL container to automatically import your dump into the database on first initialization and persist it into the container’s datastore (/var/lib/mysql):

1) Place your dump file into the db_init directory in this repository:
   - For example: db_init/01_dump.sql or db_init/01_dump.sql.gz
   - Multiple scripts are allowed and run in alphanumeric order.
2) Enable the init-mount in docker-compose.yml by uncommenting the line under db -> volumes:
   - ./db_init:/docker-entrypoint-initdb.d:ro
3) Ensure this is a fresh database (the init scripts only run when the data directory is empty):
  - Apple container: container rm -f mythras-mysql || true
4) Start the DB with the exact required syntax (reads password from your shell env or .env):

```
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3308:3306 \
  --volume "$HOME/container-data/mysql:/var/lib/mysql" \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
```
<!-- Previous (no volume) kept for reference:
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3308:3306 \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
-->
5) The import runs once and the data is stored in the named volume (db_data). Subsequent restarts will not re-run these scripts unless you wipe the volume again (down -v).

Notes:
- Environment variables (MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD) in .env influence the default DB/user created by MySQL on first run.
- If your dump already contains CREATE DATABASE/USE statements, it will create/populate as defined in the file.
- For large dumps or existing volumes, consider the manual import methods in the previous section.

## Tests: Running with tox (recommended)

We provide a tox configuration to run both pytest and Django’s unittest runner.
Assumption: your database/container is already up and reachable; tox does not start services.

Basic usage:
- Install tox: pip install tox
- Ensure DB env vars are set (or rely on .env autoload by Django settings):
  - DB_NAME, db_user/DB_USER, db_password/DB_PASSWORD, DB_HOST, DB_PORT
- Run everything: tox
  - This runs pytest with -vv and then Django’s unittest runner (scoped to enemygen.tests)

Tips:
- Pass extra pytest options via PYTEST_ADDOPTS, e.g.: PYTEST_ADDOPTS="-k makefile -q" tox
- Include only infra tests: PYTEST_ADDOPTS="-m infra" tox
- Exclude infra tests: PYTEST_ADDOPTS="-m 'not infra'" tox
- Keep DB between runs: PYTEST_ADDOPTS="--keepdb" tox

macOS (Apple container) note before running infra tests:
- make test-ready  # starts the Apple container system service to avoid XPC errors

Direct pytest usage (optional):
- Install dev dependencies: pip install -r requirements_dev.txt
- Run all tests verbosely: pytest -vv
- Quieter: pytest -q
- Single file/test: pytest tests/infradocker/test_makefile_targets.py::test_live_ps_docker_detects_state_if_cli_present
- Marker selection: pytest -m infra  (or -m "not infra")
- Keyword selection: pytest -k makefile

Alternative (Django’s built-in test runner):
- python manage.py test enemygen.tests --verbosity=2

PyCharm tips:
- Set default test runner to pytest (Settings/Preferences > Tools > Python Integrated Tools > Testing)
- Tests live under tests/ and enemygen/tests/
- pytest.ini sets: testpaths = tests enemygen/tests

## AWS Setup reminder list

* Add IPv6 to the VPC
* Create a subnet with IPv6 and Private IPv4
* Add IPv6 to Routing table - Internet Gateway (not Egress Only)
* Create EC2 instance
  * Disable public IPv4 address
* Connect using EC2 Connect Endpoint
* Run script `setup.sh`


## Database users required (MySQL 8)

The application needs a single database and a normal MySQL user that has privileges on that database. Defaults used by this repo (see .env.example and docker-compose.yml):
- Database: mythras_eg
- User: mythras_eg
- Password: ${MYSQL_PASSWORD}

Minimum privileges needed: ALL PRIVILEGES on mythras_eg.* (covers CREATE, ALTER, INDEX, INSERT, UPDATE, DELETE, SELECT, REFERENCES, TRIGGER). Root access is not required for the app.

### SQL (run as MySQL root or an admin)

-- Create database (UTF8MB4 recommended on MySQL 8)
CREATE DATABASE IF NOT EXISTS mythras_eg
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

-- Create an app user and grant full privileges on that database
-- Option A: allow from any host (useful for containers)
CREATE USER IF NOT EXISTS 'mythras_eg'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON mythras_eg.* TO 'mythras_eg'@'%';

-- Option B: restrict to localhost only
-- CREATE USER IF NOT EXISTS 'mythras_eg'@'localhost' IDENTIFIED BY '${MYSQL_PASSWORD}';
-- GRANT ALL PRIVILEGES ON mythras_eg.* TO 'mythras_eg'@'localhost';

FLUSH PRIVILEGES;

Notes:
- Adjust the password to your choosing and keep it in sync with DB_PASSWORD in your .env.
- PyMySQL (used by this project) supports MySQL 8’s default caching_sha2_password authentication.
- If you later change the password: ALTER USER 'mythras_eg'@'%' IDENTIFIED BY '$MYSQL_PASSWORD';

## Troubleshooting: Git init/errors (HEAD.lock / index.lock / symref permission)

If you see errors like the following when running `git add`, `git commit`, or `git init`:

- warning: unable to unlink '.git/HEAD.lock': Operation not permitted
- error: unable to write symref for HEAD: Operation not permitted
- error: Unable to create '.git/HEAD.lock': File exists. Another git process seems to be running...
- error: Unable to create '.git/index.lock': File exists. Another git process seems to be running...

This usually means your .git directory has incorrect ownership/permissions or there is a stale lock file left behind by a crashed git process (or an editor spawned by git is still open).

Quick fix (macOS/Linux):

1) Run our helper (from repo root) or use Make:

   ./tools/git_repair.sh
   make git-repair

What the helper does:
- Removes stale .git/*.lock files (HEAD.lock, index.lock)
- Attempts to fix .git ownership to your current user and group (uses sudo if necessary)
- Ensures .git/HEAD is a valid symbolic ref (defaults to refs/heads/main)
- Ensures refs/heads exists and sets default branch
- Verifies with `git status`

Manual steps (if you prefer):
- Ensure no other git process is running (no interactive editor spawned by git). If unsure, wait a few seconds or check your processes.
- rm -f .git/HEAD.lock .git/index.lock
- chown -R "$(id -u)":"$(id -g)" .git   # may require sudo depending on your system
- chmod -R u+rwX .git
- If .git/HEAD is missing or corrupted, recreate it: echo "ref: refs/heads/main" > .git/HEAD
- Ensure HEAD points to a default branch: git symbolic-ref HEAD refs/heads/main

If the directory is on a protected filesystem (e.g., read-only or restricted by corporate security tools), move the project to a writable location (like your home directory) or adjust the protection settings.



## Management command: taggit_dedup

If you see an IntegrityError during migrate similar to:

- django.db.utils.IntegrityError: (1062, "Duplicate entry '12-37-3' for key 'taggit_taggeditem.taggit_taggeditem_content_type_id_object_id_tag_id_..._uniq'")

it means your database already contains duplicate rows in django-taggit’s taggit_taggeditem table that violate the unique constraint on (content_type_id, object_id, tag_id).

Use the provided management command to safely deduplicate them:

- Preview only (no changes):
  - python manage.py taggit_dedup --dry-run
- Perform deduplication (keeps the lowest id per unique triple):
  - python manage.py taggit_dedup

After a successful run, re-run migrations (if you were blocked by this error):
- python manage.py migrate_safe
- or: python manage.py migrate --fake-initial

Troubleshooting:
- Ensure you run the command from the project root (where manage.py is located).
- Ensure INSTALLED_APPS includes enemygen (it does by default in settings.py), since the command lives under enemygen/management/commands.
- List available commands to verify it’s discovered:
  - python manage.py help | grep taggit_dedup



## Important: Tests use the normal database (no separate test_ DB)

This project is configured to use the normal application database for tests as well.
- Django setting: DATABASES['default']['TEST'] = { 'MIRROR': 'default' }
- Effect: The test runner will NOT create a separate test_<dbname> database; it will operate on the same DB defined by DB_NAME (e.g., mythras_eg).

Caution:
- Running tests can INSERT/UPDATE/DELETE data. Run tests only against a disposable copy or backup your data first.
- For safer local testing, point DB_NAME in your .env to a clone (e.g., mythras_eg_dev) before running tests.

You can verify connectivity before running tests:
  - python manage.py checkdb

Tip: If your DB already contains data and you want tests to avoid loading the baseline fixture, set an environment variable:
  - SKIP_TEST_LOADDATA=1 pytest -q

 Running tests:
- Install dev requirements: `pip install -r requirements_dev.txt`
- Run all tests: `pytest`
- Quieter output: `pytest -q`
- Speed up repeated runs by keeping the test DB after first creation: `pytest --keepdb`
- If you want Django to (re)create the test DB explicitly on a run, use: `pytest --create-db`




## Important: Tests use the normal database (no separate test_ DB)

This project is configured to use the normal application database for tests as well.
- Django setting: DATABASES['default']['TEST'] = { 'MIRROR': 'default' }
- Effect: The test runner will NOT create a separate test_<dbname> database; it will operate on the same DB defined by DB_NAME (e.g., mythras_eg).

Caution:
- Running tests can INSERT/UPDATE/DELETE data. Run tests only against a disposable copy or backup your data first.
- For safer local testing, point DB_NAME in your .env to a clone (e.g., mythras_eg_dev) before running tests.


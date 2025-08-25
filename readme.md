# Mythras Encounter Generator

A tool for Mythras GM's for generating enemy stats.

Hosted at https://mythras.skoll.xyz/

## Dev env installation

Mythras Encounter Generator has been tested with Python 3.11. Other versions might or might not work.

Database requirements:
- MySQL 5.7 or newer (recommended: MySQL 8.0+), or
- MariaDB 10.3 or newer

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

### Option B: Start MySQL 8 with Apple container (required syntax)

Use ONLY the following exact command to start MySQL (reads password from your shell env or .env):

```
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --volume "$HOME/container-data/mysql:/var/lib/mysql" \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
```
<!-- Previous (no volume) kept for reference:
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
-->

Then, in another terminal:
- python manage.py migrate
- (Optional) python manage.py loaddata enemygen_testdata.json
- python manage.py runserver

The Django settings read configuration from environment variables and will automatically load a .env file at the project root during development (via python-dotenv). Key variables: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_SSL_CA (optional), SECRET_KEY, DEBUG, ALLOWED_HOSTS, TIME_ZONE, ADMIN_EMAILS, and EMAIL_* (see .env.example). The defaults match the docker-compose values and expose MySQL on 127.0.0.1:3306.

### Option C: Run with Apple container (macOS)

Use ONLY this exact command to start MySQL with Apple container (reads password from your shell env or .env):

```
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --volume "$HOME/container-data/mysql:/var/lib/mysql" \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
```
<!-- Previous (no volume) kept for reference:
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
-->

After that:
- python manage.py migrate
- (Optional) python manage.py loaddata enemygen_testdata.json
- python manage.py runserver

Notes:
- Ensure 'container' is installed and in PATH: https://github.com/apple/container/releases
- This project no longer uses docker compose or alternate run flags for starting MySQL.

## Import an existing MySQL dump (Apple container)

If you have a SQL dump (e.g., dump.sql) you want to use to create/restore the database:

Warning: Ensure the file you import is an actual SQL dump, not a shell command. A file containing a line like `sudo mysqldump mythras_eg > dump.sql` is NOT a dump; it’s a command that produces one. Point the tool to the resulting dump.sql (or .sql.gz), not to the command text file.

To create a valid dump from a running container (Apple container example):
- container exec -i mythras-mysql mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --databases mythras_eg > dump.sql

Prerequisites:
- Ensure the MySQL container is running (Apple container).
- Ensure your Django .env matches the dump’s database/user names, or be ready to import as root and grant access.

1) Start the DB (Apple container, exact required syntax; reads password from your shell env or .env):

```
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --volume "$HOME/container-data/mysql:/var/lib/mysql" \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
```
<!-- Previous (no volume) kept for reference:
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
-->

2) Copy the dump into the MySQL container (optional but convenient):
- Apple container:
  - container cp dump.sql mythras-mysql:/dump.sql

3) Import the dump into MySQL
- If your dump already includes CREATE DATABASE/USE statements, import as root:
  - Apple container: container exec -i mythras-mysql sh -c "mysql -uroot -p\"$MYSQL_ROOT_PASSWORD\" < /dump.sql"

- If the dump does NOT include CREATE DATABASE, create it and import into a specific DB (defaults shown match .env):
  - Apple container:
    - container exec -i mythras-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS mythras_eg CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
    - container exec -i mythras-mysql sh -c "mysql -umythras_eg -p\"$MYSQL_PASSWORD\" mythras_eg < /dump.sql"

Notes:
- Credentials come from the container environment (.env): MYSQL_ROOT_PASSWORD, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE.
- If your dump includes users/privileges, you may need to align DB_USER/DB_PASSWORD in your Django .env or GRANT privileges, e.g.:
  - container exec -i mythras-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'mythras_eg'@'%' IDENTIFIED BY '$MYSQL_PASSWORD'; GRANT ALL PRIVILEGES ON mythras_eg.* TO 'mythras_eg'@'%'; FLUSH PRIVILEGES;"
- Gzipped dump: use zcat to stream without copying:
  - macOS host -> Apple container root import: zcat dump.sql.gz | container exec -i mythras-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD"

4) Point Django to the database in .env and run migrations if needed:
- python manage.py migrate

5) Start the dev server:
- python manage.py runserver

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
  --publish 127.0.0.1:3307:3306 \
  --volume "$HOME/container-data/mysql:/var/lib/mysql" \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
```
<!-- Previous (no volume) kept for reference:
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
-->
5) The import runs once and the data is stored in the named volume (db_data). Subsequent restarts will not re-run these scripts unless you wipe the volume again (down -v).

Notes:
- Environment variables (MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD) in .env influence the default DB/user created by MySQL on first run.
- If your dump already contains CREATE DATABASE/USE statements, it will create/populate as defined in the file.
- For large dumps or existing volumes, consider the manual import methods in the previous section.

## Start Apple container service (macOS)

Before running any container commands on macOS, ensure the Apple container system service is running:

- make ac-start-service  # or: ./tools/ac_service.sh
- make ac-list           # verify the service is up and list containers

If you previously saw errors like:

Error: interrupted: "internalError: "failed to list containers" (cause: "interrupted: "XPC connection error: Connection invalid"")\nEnsure container system service has been started with `container system start`."

— these steps resolve it by starting the Apple container system service and letting you confirm with a list.

## Quick test with Apple container

If you installed Apple container, you can quickly spin up MySQL using the required syntax:

- Start MySQL (required syntax; reads password from your shell env or .env):
```
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --volume "$HOME/container-data/mysql:/var/lib/mysql" \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
```
<!-- Previous (no volume) kept for reference:
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3307:3306 \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
-->
- Or via Makefile: make start-db (it runs the exact command above, frees host port 3306 by killing listeners, and auto-removes any existing mythras-mysql container before starting)
- Optional: make scripts-chmod  # if you want to run helper scripts; they now invoke the same exact command
- cp .env.example .env       # if you haven’t already
  # If a non-default port was used (e.g., 3307), set DB_PORT in your .env accordingly before running Django.
- make checkdb               # runs python manage.py checkdb; should print Database connection OK
- make migrate               # initialize tables if using an empty DB
- Place your SQL dump at project root as 'dump.sql'.
- ./upload_dump.sh          # imports ./dump.sql into the running MySQL container
  - or: make upload-dump
  - Debug mode: make upload-dump-debug  # prints step-by-step info
  - If you see MySQL 8 syntax errors during import, enable MySQL 8 compat normalization:
    - make upload-dump-debug ARGS=--mysql8-compat
    - or: make upload-dump-compat (or make upload-dump-compat-debug)
  - Note: The upload commands do not start the DB. Ensure MySQL is running first (e.g., make start-db), then run make upload-dump or make upload-dump-debug. If the local data directory is empty (default $HOME/container-data/mysql), the upload will ensure the target database exists (when importing as root) before importing.  <!-- legacy default was .apple_container/mysql_data -->
 - make run                   # start Django dev server
 - ./stop_db.sh               # stop the DB (compose mode)
 - ./stop_db_nocompose.sh     # stop the DB (no-compose mode; add --volumes to wipe data directory)
 - Tip: To wipe local data in no-compose mode via Make, use: make stop-db VOLUMES=1

## Viewing container logs

- Apple container:
  - container logs mythras-mysql
  - container logs --follow mythras-mysql
- Makefile helpers:
  - make logs-db            # show logs once
  - make logs-db-follow     # stream logs
- To list containers:
  - make ps-ac              # running
  - make ps-ac-all          # all (including stopped)

## Troubleshooting Apple container (no-compose mode)

- Container exits immediately after start:
  - Likely causes: non-empty or incompatible data directory, or permission issues.
  - Fix: stop and wipe data directory, then start fresh:
    - make stop-db VOLUMES=1
    - ./run_db_nocompose.sh --fresh
  - If you need first-run DB initialization scripts, add --db-init.
- Port 3306 already in use:
  - The script auto-selects a free port (e.g., 3307) and prints a reminder.
  - Update DB_PORT in your .env accordingly before running Django.
- Ensure MYSQL_ROOT_PASSWORD is set in .env. The script reads .env automatically.

 Notes:
 - On macOS, you can always run with an explicit interpreter, e.g. `bash ./start_db.sh` or `bash ./run_db_nocompose.sh`.
 - Container name is mythras-mysql. In no-compose mode, data is persisted under $HOME/container-data/mysql by default. <!-- legacy: .apple_container/mysql_data -->
 - DB env defaults: DB_HOST=127.0.0.1, DB_PORT=3306, DB_NAME=\"mythras_eg\", DB_USER=\"mythras_eg\".

## Tests: Pytest (Recommended)

Run the test suite with pytest for the best developer experience.

Before running tests on macOS, ensure the Apple container system service is started first:
- make test-ready
  - This runs ac-start-service under the hood (container system start) so infra tests won’t fail due to XPC connection errors.

- Install dev dependencies (includes pytest and plugins):
  - pip install -r requirements_dev.txt
- Run all tests (verbose output):
  - pytest
- Quieter output:
  - pytest -q
- Run a single file or test:
  - pytest tests/infra/test_makefile_targets.py
  - pytest tests/infra/test_makefile_targets.py::test_live_ps_ac_detects_state_if_cli_present
- Use markers:
  - Exclude infrastructure tests: pytest -m "not infra"
  - Only infrastructure tests: pytest -m infra
- Select by keyword:
  - pytest -k makefile

Notes about Apple container (macOS):
- Some infra tests are skipped if the Apple 'container' CLI is not available or its system service is not running.
- To enable those tests:
  - Install the CLI: https://github.com/apple/container/releases
  - Start the service: make ac-start-service (or ./tools/ac_service.sh)

Alternative (Django’s built-in test runner):
- python manage.py test

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

### Apple container one-liner (inside the running MySQL container)

container exec -i mythras-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "\
CREATE DATABASE IF NOT EXISTS mythras_eg CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; \
CREATE USER IF NOT EXISTS 'mythras_eg'@'%' IDENTIFIED BY '$MYSQL_PASSWORD'; \
GRANT ALL PRIVILEGES ON mythras_eg.* TO 'mythras_eg'@'%'; \
FLUSH PRIVILEGES;"

After creating the user/database, ensure your Django environment matches:
- DB_NAME=mythras_eg
- DB_USER=mythras_eg
- DB_PASSWORD=the_password_you_set
- DB_HOST=127.0.0.1
- DB_PORT=3306

Then run:
- python manage.py checkdb   # should print Database connection OK
- python manage.py migrate



## Helper: Start DB with smart fallback (Apple container)

If you want a single command that will try compose, fall back to no-compose, and automatically retry in ephemeral mode if the bind-mounted data directory fails, use:

- make start-db-auto

This will:
- try ./start_db.sh (compose),
- on failure, try ./run_db_nocompose.sh (no-compose with a bind-mounted data dir),
- and if that fails (common on Apple container due to mount permissions), retry with ./run_db_nocompose.sh --ephemeral (no host data mount, no persistence).

After it starts, update DB_PORT in your .env if a non-default port was selected (e.g., 3307), then run:
- python manage.py checkdb
- python manage.py migrate

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

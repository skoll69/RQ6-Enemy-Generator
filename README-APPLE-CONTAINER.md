# Apple container (macOS)

This guide covers running MySQL for this project using Apple's container CLI on macOS. If you are using Docker or a Docker-compatible runtime, use readme.md instead.

This document contains all Apple container specific instructions that were previously embedded in the main readme. If you are using Docker (or Rancher Desktop with a docker-compatible CLI), you can ignore this file and follow the main readme instead.

## Prerequisites
- Install Apple container CLI: https://github.com/apple/container/releases
- Ensure the Apple container system service is running before using the CLI:
  - make ac-start-service
  - or run tools/ac_service.sh

## Start MySQL 8 with Apple container (required syntax)
Use ONLY the following exact command to start MySQL (reads password from your shell env or .env):

```
container run \
  --name mythras-mysql \
  --publish 127.0.0.1:3308:3306 \
  --volume "$HOME/container-data/mysql:/var/lib/mysql" \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  docker.io/library/mysql:8
```

Then, in another terminal:
- python manage.py migrate
- (Optional) python manage.py loaddata enemygen_testdata.json
- python manage.py runserver

Notes:
- Ensure 'container' is installed and in PATH.
- This project no longer uses docker compose to start Apple containers.

## Import an existing MySQL dump (Apple container)

Warning: Ensure the file you import is an actual SQL dump, not a shell command. A file containing a line like `sudo mysqldump mythras_eg > dump.sql` is NOT a dump.

To create a valid dump from a running container (Apple container example):
- container exec -i mythras-mysql mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --databases mythras_eg > dump.sql

Prerequisites:
- Ensure the MySQL container is running (Apple container).
- Ensure your Django .env matches the dump’s database/user names, or be ready to import as root and grant access.

1) Start the DB (required syntax shown above)
2) Copy the dump into the MySQL container (optional):
   - container cp dump.sql mythras-mysql:/dump.sql
3) Import the dump into MySQL
   - If your dump already includes CREATE DATABASE/USE statements, import as root:
     - container exec -i mythras-mysql sh -c "mysql -uroot -p\"$MYSQL_ROOT_PASSWORD\" < /dump.sql"
   - If the dump does NOT include CREATE DATABASE, create it and import into a specific DB (defaults shown match .env):
     - container exec -i mythras-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS mythras_eg CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
     - container exec -i mythras-mysql sh -c "mysql -umythras_eg -p\"$MYSQL_PASSWORD\" mythras_eg < /dump.sql"

Notes:
- Credentials come from the container environment (.env): MYSQL_ROOT_PASSWORD, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE.
- If your dump includes users/privileges, you may need to align DB_USER/DB_PASSWORD in your Django .env or GRANT privileges.

## Automatic import on first run (container datastore area)
If you want the MySQL container to automatically import your dump on first initialization and persist it into the container’s datastore (/var/lib/mysql):

1) Place your dump file into db_init (e.g., db_init/01_dump.sql)
2) Mount it in docker-compose.yml (if you adapt this for Apple container, ensure proper volume mapping)
3) Ensure this is a fresh database (empty data directory)
4) Start the DB with the required syntax shown above

## Quick test with Apple container

- Start MySQL (see command above)
- cp .env.example .env
- python manage.py checkdb
- python manage.py migrate
- Optional: import a dump via ./upload_dump.sh or make upload-dump
- python manage.py runserver
- Stop DB: ./stop_db_nocompose.sh or ./stop_db.sh

## Viewing container logs (Apple container)
- container logs mythras-mysql
- container logs --follow mythras-mysql

## Troubleshooting Apple container (no-compose mode)
- Container exits immediately after start: often due to data directory issues or port conflicts. Try wiping the data dir and starting fresh.
- Port 3306 already in use: select a free port or stop the conflicting service.
- Ensure MYSQL_ROOT_PASSWORD is set in .env; scripts read .env automatically.

## Convenience SQL
Run ad-hoc MySQL queries inside the running container:
- make sql SQL="SELECT VERSION();"
- make mysql-shell-root


## Reference notes

This appendix has been moved to README-APPLE-CONTAINER.md to keep the main README focused on the docker-based workflow used by the Makefile and infradocker tests.

Please see README-APPLE-CONTAINER.md for the complete macOS Apple container instructions.

The following sections apply when using Apple's container CLI. If you are using Docker (recommended), you can skip this appendix.

### Start Apple container service (macOS)

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
- Or via Makefile: make start-db (it runs the exact command above, frees host port 3306 by killing listeners, and auto-removes any existing mythras-mysql container before starting)
- Optional: make scripts-chmod  # if you want to run helper scripts; they now invoke the same exact command
- cp .env.example .env       # if you haven’t already
  # If a non-default port was used (e.g., 3308), set DB_PORT in your .env accordingly before running Django.
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
  - The script auto-selects a free port (e.g., 3308) and prints a reminder.
  - Update DB_PORT in your .env accordingly before running Django.
- Ensure MYSQL_ROOT_PASSWORD is set in .env. The script reads .env automatically.

 Notes:
 - On macOS, you can always run with an explicit interpreter, e.g. `bash ./start_db.sh` or `bash ./run_db_nocompose.sh`.
 - Container name is mythras-mysql. In no-compose mode, data is persisted under $HOME/container-data/mysql by default. <!-- legacy: .apple_container/mysql_data -->
 - DB env defaults: DB_HOST=127.0.0.1, DB_PORT=3306, DB_NAME=\"mythras_eg\", DB_USER=\"mythras_eg\".

### Option C: Run with Apple container (macOS)

Moved to README-APPLE-CONTAINER.md.

See Appendix: Apple container (macOS) at the end of this document for full details. A quick-start command is shown here for convenience:

Use ONLY this exact command to start MySQL with Apple container (reads password from your shell env or .env):

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
- If your DB was created from a dump and already contains Django tables (e.g., django_content_type), run:
  - python manage.py migrate_safe
  - or: python manage.py migrate --fake-initial
- Otherwise (empty DB), run:
  - python manage.py migrate

5) Start the dev server:
- python manage.py runserver


### Apple container one-liner (inside the running MySQL container)

container exec -i mythras-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "\
CREATE DATABASE IF NOT EXISTS mythras_eg CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; \
CREATE USER IF NOT EXISTS 'mythras_eg'@'%' IDENTIFIED BY '$MYSQL_PASSWORD'; \
GRANT ALL PRIVILEGES ON mythras_eg.* TO 'mythras_eg'@'%'; \
FLUSH PRIVILEGES;"

After creating the user/database, ensure your Django environment matches:
- DB_NAME=mythras_eg
- db_user=mythras_eg        # preferred; lowercase key now supported
- db_password=the_password_you_set  # preferred; lowercase key now supported
- DB_HOST=127.0.0.1
- DB_PORT=3306

Notes:
- For backward compatibility, you can still use DB_USER/DB_PASSWORD. If both lowercase and uppercase are set, lowercase (db_user/db_password) take precedence.

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

After it starts, update DB_PORT in your .env if a non-default port was selected (e.g., 3308), then run:
- python manage.py checkdb
- python manage.py migrate


Notes about Apple container (macOS):
- Some infra tests are skipped if the Apple 'container' CLI is not available or its system service is not running.
- To enable those tests:
  - Install the CLI: https://github.com/apple/container/releases
  - Start the service: make ac-start-service (or ./tools/ac_service.sh)

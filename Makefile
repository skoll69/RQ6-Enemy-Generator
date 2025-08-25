# Convenience targets for Apple container only
# Use `make start-db` to start MySQL with Apple container.

# Use bash for more reliable multi-line recipes
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# Default preferred CLI is Apple container; detection will override as needed
CONTAINER?=container

# Force Apple container as the only supported CLI
EFFECTIVE_CONTAINER=container

# Prepare environment for running tests: ensure Apple container system service is started first
# Usage: make test-ready
# This does not install dependencies; it only ensures the container system is up when available.
test-ready:
	@echo "[test-ready] Ensuring Apple container system service is running first...";
	$(MAKE) --no-print-directory ac-start-service || true;
	@echo "[test-ready] Done. You can now run: pytest"

start-db:
	@echo "Starting MySQL with the mandated minimal syntax (Apple container).";
	$(MAKE) apple-run-minimal

# Ensure Apple container system service is running (fixes XPC connection errors)
ac-start-service:
	@echo "Ensuring Apple container system service is running...";
	./tools/ac_service.sh


migrate:
	python manage.py migrate

checkdb:
	python manage.py checkdb

run:
	python manage.py runserver

# Run using python -m django (bypasses manage.py); ensure DJANGO_SETTINGS_MODULE is set
run-mod:
	DJANGO_SETTINGS_MODULE=settings python -m django runserver

run-mod-0:
	DJANGO_SETTINGS_MODULE=settings python -m django runserver 0.0.0.0:8000

# Bind explicitly to loopback (127.0.0.1)
run-host-127:
	@echo "Starting Django on http://127.0.0.1:8000 (loopback). If Safari cannot open this, try http://localhost:8000 or 'make run-host-0'.";
	python manage.py runserver 127.0.0.1:8000

# Bind to all interfaces (useful if 127.0.0.1 is problematic on the browser)
run-host-0:
	@echo "Starting Django on http://0.0.0.0:8000 (all interfaces). Access via http://localhost:8000 in your browser.";
	python manage.py runserver 0.0.0.0:8000

# Run Django with DEBUG=true and higher verbosity
run-debug:
	DEBUG=true python manage.py runserver --verbosity 2

stop-db:
	@echo "Stopping MySQL container (Apple container only).";
	@if [ "$(VOLUMES)" = "1" ]; then \
	  bash ./stop_db.sh --volumes; \
	else \
	  bash ./stop_db.sh; \
	fi

# Import dump from fixed path ./dump.sql (no autodiscovery, no overrides)
# You can pass extra script args with ARGS=..., e.g., ARGS=--mysql8-compat
upload-dump:
	CONTAINER=$(EFFECTIVE_CONTAINER) bash ./upload_dump.sh $(ARGS)

# Debug variant of upload-dump (fixed path ./dump.sql)
# Pass extra args via ARGS=..., e.g., make upload-dump-debug ARGS=--mysql8-compat
upload-dump-debug:
	CONTAINER=$(EFFECTIVE_CONTAINER) DUMP_DEBUG=1 bash ./upload_dump.sh --debug $(ARGS)

# Convenience targets: always enable MySQL 8 compatibility normalization
upload-dump-compat:
	CONTAINER=$(EFFECTIVE_CONTAINER) bash ./upload_dump.sh --mysql8-compat $(ARGS)

upload-dump-compat-debug:
	CONTAINER=$(EFFECTIVE_CONTAINER) DUMP_DEBUG=1 bash ./upload_dump.sh --debug --mysql8-compat $(ARGS)


scripts-chmod:
	chmod +x start_db.sh stop_db.sh upload_dump.sh run_db_nocompose.sh stop_db_nocompose.sh start_db_simple.sh analyze_dump.sh


# Minimal new start: direct minimal commands to create/start DB, create user, and upload dump
	env-new-start:
		@set -eu; \
		ENV_FILE=.env; \
		# Load required variables safely from .env
		export $$(grep -E '^(MYSQL_ROOT_PASSWORD|DB_NAME|DB_USER|DB_PASSWORD)=' "$$ENV_FILE" 2>/dev/null || true); \
		: $${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required in .env or environment}; \
		: $${DB_NAME:?DB_NAME is required in .env or environment}; \
		: $${DB_USER:?DB_USER is required in .env or environment}; \
		# 0) Verify Apple container service is reachable first (avoid XPC errors)
		if ! container list >/dev/null 2>&1; then \
		  echo "[env-new-start] Apple container service is not available. Run 'make ac-start-service' and retry." >&2; exit 1; \
		fi; \
		# 1) Ensure any old container is removed and start a fresh MySQL using Apple 'container' CLI
		container kill mythras-mysql >/dev/null 2>&1 || true; \
		container rm mythras-mysql >/dev/null 2>&1 || true; \
		# Previously (no persistent data mount):
		# container run --name mythras-mysql --publish 127.0.0.1:3307:3306 --env MYSQL_ROOT_PASSWORD="$$MYSQL_ROOT_PASSWORD" docker.io/library/mysql:8 >/dev/null & \
		# Now use a persistent data volume at $HOME/container-data/mysql:
		container run --name mythras-mysql --publish 127.0.0.1:3307:3306 --volume "$$HOME/container-data/mysql:/var/lib/mysql" --env MYSQL_ROOT_PASSWORD="$$MYSQL_ROOT_PASSWORD" docker.io/library/mysql:8 >/dev/null & \
		PID=$$!; disown $$PID || true; \
		# 2) Wait until MySQL responds to a simple query as root (timeout ~60*0.5s)
		i=0; \
		until MYSQL_PWD="$$MYSQL_ROOT_PASSWORD" container exec -i mythras-mysql sh -c "mysql -N -B -uroot -e 'SELECT 1'" >/dev/null 2>&1; do \
		  i=$$((i+1)); [ $$i -lt 120 ] || { echo "[env-new-start] MySQL did not become ready in time" >&2; exit 1; }; \
		  sleep 0.5; \
		done; \
		# 3) Create the application user with caching_sha2_password and grant privileges (idempotent)
		PW_NORM=$$(printf %s "$$DB_PASSWORD" | sed -e "s/^'//" -e "s/'$$//" -e 's/^"//' -e 's/"$$//'); \
		SQL="CREATE USER IF NOT EXISTS '$$DB_USER'@'%' IDENTIFIED WITH caching_sha2_password BY '$$PW_NORM'; \
		CREATE USER IF NOT EXISTS '$$DB_USER'@'localhost' IDENTIFIED WITH caching_sha2_password BY '$$PW_NORM'; \
		CREATE DATABASE IF NOT EXISTS \`$$DB_NAME\`; \
		GRANT ALL PRIVILEGES ON \`$$DB_NAME\`.* TO '$$DB_USER'@'%'; \
		GRANT ALL PRIVILEGES ON \`$$DB_NAME\`.* TO '$$DB_USER'@'localhost'; \
		FLUSH PRIVILEGES;"; \
		MASKED_SQL=$$(echo "$$SQL" | sed -E "s/BY '([^']*)'/BY '***'/g"); \
		echo "[env-new-start] SQL to execute:"; echo "$$MASKED_SQL"; \
		printf "%s" "$$SQL" | container exec -i mythras-mysql sh -c "MYSQL_PWD='$$MYSQL_ROOT_PASSWORD' mysql -uroot"; \
		# 4) Upload dump.sql if present (with MySQL 8 compat), otherwise skip
		if [ -f ./dump.sql ]; then \
		  echo "[env-new-start] Loading dump.sql into $$DB_NAME (mysql8 compat)..."; \
		  MYSQL_PWD="$$MYSQL_ROOT_PASSWORD" container exec -i mythras-mysql sh -c "mysql -uroot $$DB_NAME" < ./dump.sql || true; \
		else \
		  echo "[env-new-start] dump.sql not found; skipping import."; \
		fi; \
		# 5) Verify environment by querying weapons table as app user
		if MYSQL_PWD="$$PW_NORM" container exec -i mythras-mysql sh -c "mysql -N -B -u$$DB_USER $$DB_NAME -e 'SELECT COUNT(*) FROM weapons'" >/tmp/meg_weapons_count 2>/tmp/meg_weapons_err; then \
		  COUNT=$$(tr -d '\r\n' </tmp/meg_weapons_count || true); echo "[env-new-start] weapons count in $$DB_NAME: $$COUNT"; \
		else \
		  ERR=$$(cat /tmp/meg_weapons_err || true); \
		  echo "[env-new-start] Could not query weapons table. If schema/data isn't loaded yet, ensure dump.sql exists or run 'python manage.py migrate'."; \
		  echo "[env-new-start] Error from mysql: $$ERR"; \
		fi; \
		rm -f /tmp/meg_weapons_count /tmp/meg_weapons_err >/dev/null 2>&1 || true



# List running containers using Apple container
ps-ac:
	@CLI=container; LISTCMD="list"; LISTARGS=""; \
	echo "Using CLI: $$CLI"; \
	$$CLI $$LISTCMD $$LISTARGS

# List all containers (including stopped) using Apple container
ps-ac-all:
	@CLI=container; LISTCMD="list"; LISTARGS="--all"; \
	echo "Using CLI: $$CLI"; \
	$$CLI $$LISTCMD $$LISTARGS

# Show logs for the MySQL container (mythras-mysql)
logs-db:
	@CLI=container; LOGSCMD="logs"; LOGSARGS=""; \
	echo "Using CLI: $$CLI"; \
	$$CLI $$LOGSCMD $$LOGSARGS mythras-mysql

# Follow logs for the MySQL container (stream)
logs-db-follow:
	@CLI=container; LOGSCMD="logs"; LOGSARGS="--follow"; \
	echo "Using CLI: $$CLI"; \
	$$CLI $$LOGSCMD $$LOGSARGS mythras-mysql

# Show container state via both inspect and list (Apple container) for mythras-mysql
ps-ac-state:
	@CLI=container; \
	echo "Using CLI: $$CLI"; \
	INSPECT_STATE=$$($$CLI inspect -f '{{.State.Status}}' mythras-mysql 2>/dev/null || echo unknown); \
	echo "inspect state: $$INSPECT_STATE"; \
	LINE="$$($$CLI list --all 2>/dev/null | awk -v name='mythras-mysql' 'NR>1 && $$1==name {print; exit}')"; \
	if [ -n "$$LINE" ]; then echo "list line: $$LINE"; else echo "list line: (not found)"; fi

# Diagnose common issues when MySQL doesn't seem to start (Apple container only)
# Usage: make db-doctor
# Prints: tool versions, container state, recent logs, and host port usage.
	db-doctor:
		@echo "[db-doctor] $(shell date)"; \
		CLI=container; CONTAINER=mythras-mysql; ENV_FILE=.env; \
		echo "CLI: $$CLI"; \
		echo "CLI path: $$(command -v $$CLI || echo '(not found in PATH)')"; \
		# Avoid noisy plugin errors on some builds; prefer safe capability checks \
		if $$CLI --help >/dev/null 2>&1; then echo "CLI --help: OK"; else echo "CLI --help failed (is the service installed?)"; fi; \
		# Avoid 'container system info'; use 'container list' as a proxy for service availability \
		if $$CLI list >/dev/null 2>&1; then echo "Service check via 'container list': OK"; else echo "Service check via 'container list' failed (try 'make ac-start-service')"; fi; \
		# Try 'container version' only if available; suppress stderr to avoid 'failed to find plugin' noise \
		($$CLI version 2>/dev/null || true) | sed 's/^/version: /' || true; \
		echo "--- Container state (inspect) ---"; \
		STATE=$$($$CLI inspect -f '{{.State.Status}}' $$CONTAINER 2>/dev/null || echo unknown); \
		echo "inspect: $$STATE"; \
		echo "--- Container list (all) ---"; \
		LINE="$$($$CLI list --all 2>/dev/null | awk -v name="$$CONTAINER" 'NR>1 && $$1==name {print; exit}')"; \
		if [ -n "$$LINE" ]; then echo "$$LINE"; else echo "(not found in list)"; fi; \
		echo "--- Recent MySQL logs (last 100 lines) ---"; \
		$$CLI logs $$CONTAINER 2>/dev/null | tail -n 100 || echo "(no logs available)"; \
		echo "--- Host port 3306 usage ---"; \
		if command -v lsof >/dev/null 2>&1; then lsof -iTCP:3306 -sTCP:LISTEN || echo "(no listener on 3306)"; \
		elif command -v netstat >/dev/null 2>&1; then netstat -an | grep -E '\\.3306 .*LISTEN' || echo "(no listener on 3306)"; \
		else python3 -c "import socket,sys; s=socket.socket();\n\t\ntry:\n s.bind(('127.0.0.1',3306)); s.close(); print('port 3306 seems free')\nexcept OSError:\n print('port 3306 appears busy')" || true; fi; \
		echo "--- .env presence and key vars (names only) ---"; \
		if [ -f "$$ENV_FILE" ]; then \
		  echo ".env found"; \
		  grep -E '^(MYSQL_ROOT_PASSWORD|MYSQL_DATABASE|MYSQL_USER|MYSQL_PASSWORD|DB_NAME|DB_USER|DB_HOST|DB_PORT)=' "$$ENV_FILE" | sed 's/=.*$$/=<set>/' || true; \
		else echo ".env not found"; fi; \
		echo "--- Hints ---"; \
		echo "- If port 3306 is busy, stop the conflicting service or run 'make stop-db' and try again."; \
		echo "- Start with: make start-db (will remove any stale mythras-mysql and run exact Apple container command)."; \
		echo "- You can tail logs with: make logs-db-follow"

# Repair Git repository issues: stale lock files, permissions, broken HEAD
# Usage: make git-repair

git-repair:
	@echo "[git-repair] Running repository repair helper..."
	@./tools/git_repair.sh

# Minimal Apple container MySQL run (exact form as requested)
# Subtargets to split apple-run-minimal phases for clearer debugging
apple-env-check:
	@ENV_FILE=.env; NOW=$$(date); \
	if [ -f "$$ENV_FILE" ]; then echo "[apple-env-check] $$NOW: .env found ($$ENV_FILE)"; else echo "[apple-env-check] $$NOW: .env not found; relying on environment"; fi; \
	if [ -f "$$ENV_FILE" ]; then export $$(grep -E '^(MYSQL_ROOT_PASSWORD)=' "$$ENV_FILE"); fi; \
	if [ -n "$$MYSQL_ROOT_PASSWORD" ]; then echo "[apple-env-check] MYSQL_ROOT_PASSWORD: <set>"; else echo "[apple-env-check] MYSQL_ROOT_PASSWORD: <not set>"; fi; \
	: "$$MYSQL_ROOT_PASSWORD" >/dev/null 2>&1 || { echo "Error: MYSQL_ROOT_PASSWORD must be set in .env or environment" >&2; exit 1; }

# Free host port 3306 by killing any process listening on it (best-effort)
apple-free-port-3307:
	@# Try lsof first, then netstat; ignore errors if tools are missing
	@if command -v lsof >/dev/null 2>&1; then \
	  PIDS=$$(lsof -t -iTCP:3307 -sTCP:LISTEN 2>/dev/null | sort -u); \
	  if [ -n "$$PIDS" ]; then \
	    echo "[apple-free-port-3307] Detected listeners on 3307: $$PIDS"; \
	    kill $$PIDS >/dev/null 2>&1 || true; \
	    sleep 0.3; \
	    # Force kill any remaining
	    STILL=$$(lsof -t -iTCP:3307 -sTCP:LISTEN 2>/dev/null | sort -u); \
	    if [ -n "$$STILL" ]; then echo "[apple-free-port-3307] Forcing kill for: $$STILL"; kill -9 $$STILL >/dev/null 2>&1 || true; fi; \
	  else \
	    echo "[apple-free-port-3307] No listeners on 3307 (lsof)"; \
	  fi; \
	elif command -v netstat >/dev/null 2>&1; then \
	  if netstat -anv 2>/dev/null | grep -E '\\.3307 .*LISTEN' >/dev/null; then \
	    echo "[apple-free-port-3307] Port 3307 appears in LISTEN state but cannot identify PIDs via netstat on this platform."; \
	    echo "[apple-free-port-3307] Hint: Consider 'sudo lsof -iTCP:3307 -sTCP:LISTEN -Pn' to find the process."; \
	  else \
	    echo "[apple-free-port-3307] No listeners on 3307 (netstat)"; \
	  fi; \
	else \
	  echo "[apple-free-port-3307] Neither lsof nor netstat available; cannot proactively free port 3307."; \
	fi

apple-pre-remove:
	@# Pre-remove any existing container to avoid 'exists' error (Apple 'container' CLI)
	@EXISTS=$$(container list --all 2>/dev/null | awk 'NR>1 && $$1=="mythras-mysql" {print "yes"}'); \
	if [ "$$EXISTS" = "yes" ]; then \
	  STATE=$$(container list --all 2>/dev/null | awk 'NR>1 && $$1=="mythras-mysql" {print $$5}'); \
	  if [ "$$STATE" = "running" ]; then echo "[apple-pre-remove] Stopping existing mythras-mysql..."; container kill mythras-mysql >/dev/null 2>&1 || true; sleep 0.2; fi; \
	  echo "[apple-pre-remove] Removing existing mythras-mysql..."; container rm mythras-mysql >/dev/null 2>&1 || true; \
	  # Double-check removal
	  EXISTS2=$$(container list --all 2>/dev/null | awk 'NR>1 && $$1=="mythras-mysql" {print "yes"}'); \
	  if [ "$$EXISTS2" = "yes" ]; then echo "[apple-pre-remove] Retrying force removal of mythras-mysql..."; container kill mythras-mysql >/dev/null 2>&1 || true; container rm mythras-mysql >/dev/null 2>&1 || true; fi; \
	else \
	  echo "[apple-pre-remove] No existing mythras-mysql container found."; \
	fi

	apple-show-cmd:
		@echo "[apple-run] Executing required command:"; \
		echo "container run"; \
		echo "  --name mythras-mysql"; \
		echo "  --publish 127.0.0.1:3307:3306"; \
		echo "  --volume \"$${HOME}/container-data/mysql:/var/lib/mysql\""; \
		echo "  --env MYSQL_ROOT_PASSWORD=***"; \
		echo "  docker.io/library/mysql:8"

apple-run:
	@/bin/bash -eu -o pipefail <<'BASH'
	ENV_FILE=.env
	# Load required vars from .env without sourcing arbitrary lines
	if [ -f "$$ENV_FILE" ]; then export $$(grep -E '^(MYSQL_ROOT_PASSWORD|MYSQL_PORT)=' "$$ENV_FILE"); fi
	# Require password
	: "$${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD must be set in .env or environment}"
	# Optional host port (default 3306)
	PORT="$${MYSQL_PORT:-3306}"
	NAME="mythras-mysql"
	# Verify service reachable via 'container list' to avoid XPC errors
	if ! container list >/dev/null 2>&1; then
	  echo "[apple-run] Apple container service is not available. Run 'make ac-start-service' and retry." >&2
	  exit 1
	fi
	# Clean any old container with the same name
	container kill "$$NAME" >/dev/null 2>&1 || true
	container rm   "$$NAME" >/dev/null 2>&1 || true
	# Show what we will run (mask the password)
	echo "[apple-run] Starting $$NAME on host port $$PORT"
	echo "container run --name $$NAME --publish 127.0.0.1:3307:3306 --volume \"$${HOME}/container-data/mysql:/var/lib/mysql\" --env MYSQL_ROOT_PASSWORD=*** docker.io/library/mysql:8"
	# Run it
	exec container run --name "$$NAME" \
	  --publish 127.0.0.1:3307:3306 \
	  --volume "$${HOME}/container-data/mysql:/var/lib/mysql" \
	  --env MYSQL_ROOT_PASSWORD="$$MYSQL_ROOT_PASSWORD" \
	  docker.io/library/mysql:8

apple-post-check:
	@# Post-run diagnostics
	@sleep 1; \
	STATE=$$(container list --all 2>/dev/null | awk 'NR>1 && $$1=="mythras-mysql" {print $$5; exit}'); \
	if [ "$$STATE" = "running" ]; then \
	  echo "[apple-post-check] MySQL container 'mythras-mysql' is running."; \
	else \
	  : $${STATE:=unknown}; \
	  echo "[apple-post-check] Warning: MySQL container not running (state: $$STATE). Recent logs:" >&2; \
	  container logs mythras-mysql 2>&1 | tail -n 200 >&2 || true; \
	  echo "[apple-post-check] --- container list --all (grep mythras-mysql) ---" >&2; \
	  container list --all 2>/dev/null | awk 'NR==1 || $$1=="mythras-mysql"' >&2 || true; \
	  if container inspect mythras-mysql >/dev/null 2>&1; then echo "[apple-post-check] --- inspect (raw status fields) ---" >&2; container inspect -f '{{json .State}}' mythras-mysql 2>/dev/null >&2 || true; fi; \
	  if [ "$$DEBUG" = "1" ] 2>/dev/null; then echo "[apple-post-check] --- Host port 3306 usage ---" >&2; (command -v lsof >/dev/null 2>&1 && lsof -iTCP:3306 -sTCP:LISTEN || command -v netstat >/dev/null 2>&1 && netstat -an | grep -E '\\.3306 .*LISTEN' || echo '(no listener on 3306)') >&2 || true; fi; \
	  echo "[apple-post-check] Hint: If port 3306 is already in use on the host, the container may exit immediately. Stop the conflicting service (or change port) and retry. You can run 'make db-doctor' for deeper diagnostics." >&2; \
	fi

# Minimal Apple container MySQL run (exact form as requested)
apple-run-minimal:
	@echo "Running minimal Apple container MySQL (no volumes, password from .env or environment)."; \
	$(MAKE) apple-env-check; \
	$(MAKE) apple-show-cmd; \
	$(MAKE) apple-run; \
	$(MAKE) apple-post-check


# Analyze dump helper (defaults to ./dump.sql)
analyze-dump:
	@bash ./analyze_dump.sh --file ./dump.sql --mysql8 --summary



# Run ad-hoc MySQL queries inside the running container.
# Usage examples:
#   make sql SQL="SELECT VERSION();"
#   make sql DB=mythras_eg SQL="SHOW TABLES;"
#   make sql FILE=path/to/script.sql
#   echo "SELECT NOW();" | make sql
# Options (env vars):
#   USER=root (default) | set USER=mythras_eg
#   PASSWORD (defaults from .env: MYSQL_ROOT_PASSWORD when USER=root, else MYSQL_PASSWORD)
#   DB (optional): database to connect to
sql:
	@CLI=container; \
	echo "Using CLI: $$CLI"; \
	# Load minimal MySQL vars from .env without nested eval
	ENV_FILE=.env; TMP_ENV=$$(mktemp 2>/dev/null || echo /tmp/meg_env_$$); \
	if [ -f "$$ENV_FILE" ]; then \
		grep -E '^(MYSQL_DATABASE|MYSQL_USER|MYSQL_PASSWORD|MYSQL_ROOT_PASSWORD)=' "$$ENV_FILE" | sed 's/^/export /' > "$$TMP_ENV"; \
		source "$$TMP_ENV"; rm -f "$$TMP_ENV" >/dev/null 2>&1 || true; \
	fi; \
	U=$${USER:-root}; \
	if [ "$$U" = "root" ]; then PW=$${PASSWORD:-$${MYSQL_ROOT_PASSWORD:-}}; else PW=$${PASSWORD:-$${MYSQL_PASSWORD:-}}; fi; \
	DBOPT=""; if [ -n "$$DB" ]; then DBOPT=" $$DB"; fi; \
	AUTH="-u$$U"; if [ -n "$$PW" ]; then AUTH="$$AUTH -p$$PW"; fi; \
	# Debug print
	echo "[sql] USER=$$U DB=$${DB:-} CLI=$$CLI" >&2; \
	# Branch: FILE, SQL, or stdin/interactive
	if [ -n "$$FILE" ]; then \
		[ -f "$$FILE" ] || { echo "Error: FILE not found: $$FILE" >&2; exit 1; }; \
		cat "$$FILE" | $$CLI exec -i mythras-mysql mysql$$DBOPT $$AUTH; \
	elif [ -n "$$SQL" ]; then \
		$$CLI exec -i mythras-mysql sh -c "mysql$$DBOPT $$AUTH -e \"$${SQL}\""; \
	else \
		if [ -t 0 ]; then \
			$$CLI exec -it mythras-mysql sh -c "mysql$$DBOPT $$AUTH"; \
		else \
			cat - | $$CLI exec -i mythras-mysql mysql$$DBOPT $$AUTH; \
		fi; \
	fi

# Open an interactive MySQL shell inside the container
# Usage: make mysql-shell [USER=mythras_eg] [DB=mythras_eg] [PASSWORD=...]
mysql-shell:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then \
		echo "Loading $$ENV_FILE" >/dev/null; \
		export $$(grep -E '^(MYSQL_USER|MYSQL_PASSWORD)=' "$$ENV_FILE"); \
	fi; \
	U=$${MYSQL_USER:-}; \
	PW=$${MYSQL_PASSWORD:-}; \
	AUTH=""; if [ -n "$$U" ]; then AUTH="-u$$U"; fi; if [ -n "$$PW" ]; then AUTH="$$AUTH -p$$PW"; fi; \
	container exec -it mythras-mysql sh -c "mysql $$AUTH"


# Open an interactive MySQL shell as root user
mysql-shell-root:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then \
		echo "Loading $$ENV_FILE" >/dev/null; \
		export $$(grep -E '^(MYSQL_ROOT_PASSWORD)=' "$$ENV_FILE"); \
	fi; \
	U=root; \
	PW=$${MYSQL_ROOT_PASSWORD:-}; \
	AUTH="-u$$U"; if [ -n "$$PW" ]; then AUTH="$$AUTH -p$$PW"; fi; \
	container exec -it mythras-mysql sh -c "mysql $$AUTH"

mysql-shell-db:
	@set -eu; \
	ENV_FILE=.env; \
	export $$(grep -E '^(DB_NAME|DB_USER|DB_PASSWORD|MYSQL_ROOT_PASSWORD)=' "$$ENV_FILE" 2>/dev/null || true); \
	: $${DB_NAME:?DB_NAME is required in .env or environment}; \
	: $${DB_USER:?DB_USER is required in .env or environment}; \
	# Try to connect; if plugin error 1524 occurs, optionally auto-fix or instruct user
	TMP_OUT=$$(mktemp 2>/dev/null || echo /tmp/meg_mysql_db_$$); \
	TMP_ERR=$$(mktemp 2>/dev/null || echo /tmp/meg_mysql_db_err_$$); \
	set +e; MYSQL_PWD="$${DB_PASSWORD:-}" container exec -i mythras-mysql sh -c "mysql -N -B -u$$DB_USER $$DB_NAME -e 'SELECT 1'" >"$$TMP_OUT" 2>"$$TMP_ERR"; STATUS=$$?; set -e; \
	if [ $$STATUS -ne 0 ] && grep -q "Plugin 'mysql_native_password' is not loaded" "$$TMP_ERR"; then \
		echo "[mysql-shell-db] Detected MySQL 8 auth plugin mismatch for user '$$DB_USER'." >&2; \
		if [ "$${AUTO_FIX_AUTH:-0}" = "1" ]; then \
			: $${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required in .env to auto-fix}; \
			$(MAKE) mysql-fix-auth; \
			echo "[mysql-shell-db] Retrying connection after auth fix..." >&2; \
			MYSQL_PWD="$${DB_PASSWORD:-}" container exec -it mythras-mysql sh -c "mysql -u$$DB_USER $$DB_NAME"; \
		else \
			echo "Run: make mysql-fix-auth  (or)  make mysql-create-user to create/update the user with caching_sha2_password, then retry 'make mysql-shell-db'." >&2; \
			exit 1; \
		fi; \
	else \
		if [ $$STATUS -eq 0 ]; then \
			MYSQL_PWD="$${DB_PASSWORD:-}" container exec -it mythras-mysql sh -c "mysql -u$$DB_USER $$DB_NAME"; \
		else \
			cat "$$TMP_ERR" >&2; \
			exit $$STATUS; \
		fi; \
	fi; \
	rm -f "$$TMP_OUT" "$$TMP_ERR" >/dev/null 2>&1 || true


# Open an interactive MySQL shell as application user (mythras_eg) using DB password
# Usage: make mysql-shell-app [USER=mythras_eg] [DB=mythras_eg]
mysql-shell-app:
	@set -eu; \
	CLI=container; \
	# Load only needed DB vars from .env in a safe way (no sourcing arbitrary lines)
	ENV_FILE=.env; TMP_ENV=$$(mktemp 2>/dev/null || echo /tmp/meg_env_$$); \
	if [ -f "$$ENV_FILE" ]; then \
		grep -E '^(DB_NAME|DB_USER|DB_PASSWORD|DB_HOST|DB_PORT|MYSQL_DATABASE|MYSQL_USER|MYSQL_PASSWORD)=' "$$ENV_FILE" | sed 's/^/export /' > "$$TMP_ENV"; \
		source "$$TMP_ENV"; rm -f "$$TMP_ENV" >/dev/null 2>&1 || true; \
	fi; \
	U=$${USER:-$${DB_USER:-$${MYSQL_USER:-mythras_eg}}}; \
	PW=$${PASSWORD:-$${DB_PASSWORD:-$${MYSQL_PASSWORD:-}}}; \
	DB=$${DB:-$${DB_NAME:-$${MYSQL_DATABASE:-}}}; \
	HOST_OPT=""; PORT_OPT=""; \
	if [ -n "$$DB_HOST" ]; then HOST_OPT="-h $$DB_HOST"; fi; \
	if [ -n "$$DB_PORT" ]; then PORT_OPT="-P $$DB_PORT"; fi; \
	# Detect running state from 'container list --all' where columns are:
	# ID IMAGE OS ARCH STATE ADDR
	# We match ID (col 1) and STATE (col 5) exactly.
	RUNNING=$$($$CLI list --all 2>/dev/null | awk 'NR>1 && $$1=="mythras-mysql" && $$5=="running" {print "yes"}'); \
	if [ "$$RUNNING" != "yes" ]; then \
	  echo "[mysql-shell-app] Note: Could not verify running state via '$$CLI list'. Attempting exec anyway..." >&2; \
	fi; \
	DB_ARGS=""; if [ -n "$$DB" ]; then DB_ARGS="$$DB"; fi; \
	if [ -n "$$PW" ]; then \
	  MYSQL_PWD="$$PW" $$CLI exec -it mythras-mysql mysql $$HOST_OPT $$PORT_OPT -u "$$U" $$DB_ARGS; \
	else \
	  $$CLI exec -it mythras-mysql mysql $$HOST_OPT $$PORT_OPT -u "$$U" -p $$DB_ARGS; \
	fi


# Fix MySQL 8 auth plugin for application user using root
# Usage: make mysql-fix-auth
# Requires in .env: MYSQL_ROOT_PASSWORD, DB_USER, DB_PASSWORD
mysql-fix-auth:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then \
		export $$(grep -E '^(MYSQL_ROOT_PASSWORD|DB_USER|DB_PASSWORD)=' "$$ENV_FILE" 2>/dev/null || true); \
	fi; \
	: $${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required in .env or environment}; \
	: $${DB_USER:?DB_USER is required in .env or environment}; \
	PW_NORM=$$(printf %s "$$DB_PASSWORD" | sed -e "s/^'//" -e "s/'$$//" -e 's/^"//' -e 's/"$$//'); \
	SQL="ALTER USER '$$DB_USER'@'%' IDENTIFIED WITH caching_sha2_password BY '$$PW_NORM'; FLUSH PRIVILEGES; ALTER USER '$$DB_USER'@'localhost' IDENTIFIED WITH caching_sha2_password BY '$$PW_NORM'; FLUSH PRIVILEGES;"; \
	MASKED_SQL=$$(echo "$$SQL" | sed -E "s/BY '([^']*)'/BY '***'/g"); \
	echo "[mysql-fix-auth] SQL to execute:"; echo "$$MASKED_SQL"; \
	printf "%s" "$$SQL" | container exec -i mythras-mysql sh -c "MYSQL_PWD='$$MYSQL_ROOT_PASSWORD' mysql -uroot"; \
	echo "[mysql-fix-auth] Updated authentication plugin for user '$$DB_USER' to caching_sha2_password."

# Create app DB user with caching_sha2_password and grant privileges
# Usage: make mysql-create-user
# Requires in .env: MYSQL_ROOT_PASSWORD, DB_USER, DB_PASSWORD, DB_NAME
mysql-create-user:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then \
		export $$(grep -E '^(MYSQL_ROOT_PASSWORD|DB_USER|DB_PASSWORD|DB_NAME)=' "$$ENV_FILE" 2>/dev/null || true); \
	fi; \
	: $${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required in .env or environment}; \
	: $${DB_USER:?DB_USER is required in .env or environment}; \
	: $${DB_NAME:?DB_NAME is required in .env or environment}; \
	PW_NORM=$$(printf %s "$$DB_PASSWORD" | sed -e "s/^'//" -e "s/'$$//" -e 's/^"//' -e 's/"$$//'); \
	SQL="CREATE USER IF NOT EXISTS '$$DB_USER'@'%' IDENTIFIED WITH caching_sha2_password BY '$$PW_NORM'; \
	CREATE USER IF NOT EXISTS '$$DB_USER'@'localhost' IDENTIFIED WITH caching_sha2_password BY '$$PW_NORM'; \
	GRANT ALL PRIVILEGES ON \`$$DB_NAME\`.* TO '$$DB_USER'@'%'; \
	GRANT ALL PRIVILEGES ON \`$$DB_NAME\`.* TO '$$DB_USER'@'localhost'; \
	FLUSH PRIVILEGES;"; \
	MASKED_SQL=$$(echo "$$SQL" | sed -E "s/BY '([^']*)'/BY '***'/g"); \
	echo "[mysql-create-user] SQL to execute:"; echo "$$MASKED_SQL"; \
	printf "%s" "$$SQL" | container exec -i mythras-mysql sh -c "MYSQL_PWD='$$MYSQL_ROOT_PASSWORD' mysql -uroot"; \
	echo "[mysql-create-user] Ensured user '$$DB_USER' exists with caching_sha2_password and has privileges on $$DB_NAME."

# Verify Apple container service is running and list containers
ac-list:
	@echo "Ensuring Apple container system service is running...";
	$(MAKE) ac-start-service >/dev/null
	@echo "Using CLI: container";
	container list --all


# Diagnose common issues when MySQL doesn't seem to start (Apple container only)
# Usage: make db-doctor
# Prints: tool versions, container state, recent logs, and host port usage.
db-doctor:
	@echo "[db-doctor] $(shell date)"; \
	CLI=container; CONTAINER=mythras-mysql; ENV_FILE=.env; \
	echo "CLI: $$CLI"; \
	echo "CLI path: $$(command -v $$CLI || echo '(not found in PATH)')"; \
	# Avoid noisy plugin errors on some builds; prefer safe capability checks \
	if $$CLI --help >/dev/null 2>&1; then echo "CLI --help: OK"; else echo "CLI --help failed (is the service installed?)"; fi; \
	# Avoid 'container system info'; use 'container list' as a proxy for service availability \
	if $$CLI list >/dev/null 2>&1; then echo "Service check via 'container list': OK"; else echo "Service check via 'container list' failed (try 'make ac-start-service')"; fi; \
	# Try 'container version' only if available; suppress stderr to avoid 'failed to find plugin' noise \
	($$CLI version 2>/dev/null || true) | sed 's/^/version: /' || true; \
	echo "--- Container state (inspect) ---"; \
	STATE=$$($$CLI inspect -f '{{.State.Status}}' $$CONTAINER 2>/dev/null || echo unknown); \
	echo "inspect: $$STATE"; \
	echo "--- Container list (all) ---"; \
	LINE="$$($$CLI list --all 2>/dev/null | awk -v name="$$CONTAINER" 'NR>1 && $$1==name {print; exit}')"; \
	if [ -n "$$LINE" ]; then echo "$$LINE"; else echo "(not found in list)"; fi; \
	echo "--- Recent MySQL logs (last 100 lines) ---"; \
	$$CLI logs $$CONTAINER 2>/dev/null | tail -n 100 || echo "(no logs available)"; \
	echo "--- Host port 3306 usage ---"; \
	if command -v lsof >/dev/null 2>&1; then lsof -iTCP:3306 -sTCP:LISTEN || echo "(no listener on 3306)"; \
	elif command -v netstat >/dev/null 2>&1; then netstat -an | grep -E '\\.3306 .*LISTEN' || echo "(no listener on 3306)"; \
	else python3 -c "import socket,sys; s=socket.socket();\n\t\ntry:\n s.bind(('127.0.0.1',3306)); s.close(); print('port 3306 seems free')\nexcept OSError:\n print('port 3306 appears busy')" || true; fi; \
	echo "--- .env presence and key vars (names only) ---"; \
	if [ -f "$$ENV_FILE" ]; then \
	  echo ".env found"; \
	  grep -E '^(MYSQL_ROOT_PASSWORD|MYSQL_DATABASE|MYSQL_USER|MYSQL_PASSWORD|DB_NAME|DB_USER|DB_HOST|DB_PORT)=' "$$ENV_FILE" | sed 's/=.*$$/=<set>/' || true; \
	else echo ".env not found"; fi; \
	echo "--- Hints ---"; \
	echo "- If port 3306 is busy, stop the conflicting service or run 'make stop-db' and try again."; \
	echo "- Start with: make start-db (will remove any stale mythras-mysql and run exact Apple container command)."; \
	echo "- You can tail logs with: make logs-db-follow"

# Rancher Desktop + docker-compatible CLI Makefile
# Mirrors non-Apple container targets from root Makefile but uses docker CLI.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# Use docker CLI provided by Rancher Desktop
DOCKER ?= docker
CONTAINER_NAME ?= mythras-mysql
MYSQL_IMAGE ?= docker.io/library/mysql:8
HOST_PORT ?= 3308
HOST_IP ?= 127.0.0.1

# Non-Apple container related targets replicated
start-db:
	@echo "Starting MySQL with docker (Rancher Desktop)."
	$(MAKE) docker-run-minimal

stop-db:
	@echo "Stopping MySQL container (docker)."
	-$(DOCKER) rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true

upload-dump:
	CONTAINER=docker bash ./upload_dump.sh $(ARGS)

upload-dump-debug:
	CONTAINER=docker DUMP_DEBUG=1 bash ./upload_dump.sh --debug $(ARGS)

upload-dump-compat:
	CONTAINER=docker bash ./upload_dump.sh --mysql8-compat $(ARGS)

upload-dump-compat-debug:
	CONTAINER=docker DUMP_DEBUG=1 bash ./upload_dump.sh --debug --mysql8-compat $(ARGS)

mysql-shell:
		@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then \
		set -a; . "$$ENV_FILE"; set +a; \
	fi; \
	DB_NAME="$${DB_NAME:-$${MYSQL_DATABASE:-}}"; \
	DB_USER="$${DB_USER:-$${MYSQL_USER:-}}"; \
	DB_PASSWORD="$${DB_PASSWORD:-$${MYSQL_PASSWORD:-}}"; \
	: "$${DB_NAME:?DB_NAME or MYSQL_DATABASE required}"; \
	: "$${DB_USER:?DB_USER or MYSQL_USER required}"; \
	: "$${DB_PASSWORD:?DB_PASSWORD or MYSQL_PASSWORD required}"; \
	$(DOCKER) exec -it $(CONTAINER_NAME) \
	  mysql -u"$$DB_USER" -p"$$DB_PASSWORD" "$$DB_NAME"

mysql-shell-root:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then export $$(grep -E '^(MYSQL_ROOT_PASSWORD)=' "$$ENV_FILE" 2>/dev/null || true); fi; \
	: $${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD required}; \
	MYSQL_PWD="$$MYSQL_ROOT_PASSWORD" $(DOCKER) exec -it $(CONTAINER_NAME) mysql -uroot

mysql-shell-db:
	@$(MAKE) mysql-shell

mysql-shell-app:
	@$(MAKE) mysql-shell

sql:
	@ENV_FILE=.env; \
	# Load DB_* vars; if missing, fallback to MYSQL_* commonly used with Docker
	if [ -f "$$ENV_FILE" ]; then export $$(grep -E '^(DB_NAME|DB_USER|DB_PASSWORD|MYSQL_DATABASE|MYSQL_USER|MYSQL_PASSWORD)=' "$$ENV_FILE" 2>/dev/null || true); fi; \
	DB_NAME="$${DB_NAME:-$${MYSQL_DATABASE:-}}"; \
	DB_USER="$${DB_USER:-$${MYSQL_USER:-}}"; \
	DB_PASSWORD="$${DB_PASSWORD:-$${MYSQL_PASSWORD:-}}"; \
	: $${DB_NAME:?DB_NAME or MYSQL_DATABASE required}; : $${DB_USER:?DB_USER or MYSQL_USER required}; \
	MYSQL_PWD="$$DB_PASSWORD" $(DOCKER) exec -i $(CONTAINER_NAME) mysql -N -B -u"$$DB_USER" "$$DB_NAME"

mysql-create-user:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then export $$(grep -E '^(MYSQL_ROOT_PASSWORD|DB_NAME|DB_USER|DB_PASSWORD)=' "$$ENV_FILE" 2>/dev/null || true); fi; \
	: $${MYSQL_ROOT_PASSWORD:?}; : $${DB_NAME:?}; : $${DB_USER:?}; \
	PW_NORM=$$(printf %s "$$DB_PASSWORD" | sed -e "s/^'//" -e "s/'$$//" -e 's/^"//' -e 's/"$$//'); \
	SQL="CREATE USER IF NOT EXISTS '$$DB_USER'@'%' IDENTIFIED WITH caching_sha2_password BY '$$PW_NORM'; CREATE DATABASE IF NOT EXISTS \`$$DB_NAME\`; GRANT ALL PRIVILEGES ON \`$$DB_NAME\`.* TO '$$DB_USER'@'%'; FLUSH PRIVILEGES;"; \
	printf "%s" "$$SQL" | MYSQL_PWD="$$MYSQL_ROOT_PASSWORD" $(DOCKER) exec -i $(CONTAINER_NAME) mysql -uroot

mysql-fix-auth:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then export $$(grep -E '^(MYSQL_ROOT_PASSWORD|DB_USER|DB_PASSWORD)=' "$$ENV_FILE" 2>/dev/null || true); fi; \
	: $${MYSQL_ROOT_PASSWORD:?}; : $${DB_USER:?}; \
	PW_NORM=$$(printf %s "$$DB_PASSWORD" | sed -e "s/^'//" -e "s/'$$//" -e 's/^"//' -e 's/"$$//'); \
	SQL="ALTER USER '$$DB_USER'@'%' IDENTIFIED WITH caching_sha2_password BY '$$PW_NORM'; FLUSH PRIVILEGES;"; \
	printf "%s" "$$SQL" | MYSQL_PWD="$$MYSQL_ROOT_PASSWORD" $(DOCKER) exec -i $(CONTAINER_NAME) mysql -uroot

ps-docker:
	$(DOCKER) ps

logs-db:
	$(DOCKER) logs $(CONTAINER_NAME) || true

logs-db-follow:
	$(DOCKER) logs -f $(CONTAINER_NAME)

# Minimal run using docker
# Apple-container alias removed; use docker-run-minimal only in this Makefile

docker-run-minimal:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then export $$(grep -E '^(MYSQL_ROOT_PASSWORD)=' "$$ENV_FILE" 2>/dev/null || true); fi; \
	: $${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required in .env or environment}; \
	$(DOCKER) rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true; \
	$(DOCKER) run --name $(CONTAINER_NAME) -p $(HOST_IP):$(HOST_PORT):3306 -e MYSQL_ROOT_PASSWORD="$$MYSQL_ROOT_PASSWORD" -d $(MYSQL_IMAGE) >/dev/null; \
	echo "MySQL started on $(HOST_IP):$(HOST_PORT) in container $(CONTAINER_NAME) using $(MYSQL_IMAGE)"

# Helper to ensure scripts are executable
scripts-chmod:
	chmod +x *.sh tools/*.sh 2>/dev/null || true

# Utility
show-running-container show-container:
	@echo "Showing status for container: $(CONTAINER_NAME)"
	@$(DOCKER) ps --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

ps-docker-running:
	@$(DOCKER) ps --filter "status=running"

# Utility
show-running-container show-container:
	@echo "Showing status for container: $(CONTAINER_NAME)"
	@$(DOCKER) ps --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

ps-docker-running:
	@$(DOCKER) ps --filter "status=running"

cleanup clean-db reset-env:
	@echo "Removing container: $(CONTAINER_NAME) (if exists)"
	-$(DOCKER) rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true

show-db-env:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then set -a; . "$$ENV_FILE"; set +a; fi; \
	PORT_MAP=$$($(DOCKER) ps --filter "name=$(CONTAINER_NAME)" --format "{{.Ports}}" | head -n1); \
	echo "DB_HOST=$${DB_HOST:-127.0.0.1}"; \
	echo "DB_PORT=$${DB_PORT:-3308}"; \
	echo "DB_NAME=$${DB_NAME:-$${MYSQL_DATABASE:-}}"; \
	echo "CONTAINER_NAME=$(CONTAINER_NAME)"; \
	echo "Container port mapping: $${PORT_MAP:-<none>}"

start-db-3308:
	@$(MAKE) start-db HOST_PORT=3308



git-repair:
	bash ./tools/git_repair.sh



# Generate CSV of intended rowcounts per table from dump.sql
# Usage: make dump-rowcount [DUMP=dump.sql] [OUT=dump_rowcount.csv]
dump-rowcount:
	@python3 tools/dump_rowcount.py --dump "$${DUMP:-dump.sql}" --out "$${OUT:-dump_rowcount.csv}"

# Recreate the target database and import dump.sql to ensure exact row counts match dump
# Usage: make import-dump-clean [DB=<db_name>] [DUMP=dump.sql]
import-dump-clean:
	@ENV_FILE=.env; \
	if [ -f "$$ENV_FILE" ]; then set -a; . "$$ENV_FILE"; set +a; fi; \
	DB_NAME="$${DB:-$${DB_NAME:-}}"; \
	ROOTPW="$${MYSQL_ROOT_PASSWORD:-}"; \
	DUMP_FILE="$${DUMP:-dump.sql}"; \
	: $${DB_NAME:?DB or DB_NAME required in env}; : $${ROOTPW:?MYSQL_ROOT_PASSWORD required in env}; \
	[ -f "$$DUMP_FILE" ] || { echo "dump file not found: $$DUMP_FILE" >&2; exit 1; }; \
	echo "[import-dump-clean] Dropping and recreating database '$$DB_NAME'..."; \
	MYSQL_PWD="$$ROOTPW" $(DOCKER) exec -i $(CONTAINER_NAME) sh -c "mysql -uroot -e 'DROP DATABASE IF EXISTS \`$$DB_NAME\`; CREATE DATABASE \`$$DB_NAME\`;'"; \
	echo "[import-dump-clean] Importing dump into '$$DB_NAME'..."; \
	CONTAINER=docker bash ./upload_dump.sh --mysql8-compat --db "$$DB_NAME" --dump "$$DUMP_FILE"; \
	echo "[import-dump-clean] Done."

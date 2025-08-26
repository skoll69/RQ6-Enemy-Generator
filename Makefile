# Rancher Desktop + docker-compatible CLI Makefile
# Mirrors non-Apple container targets from root Makefile but uses docker CLI.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# Use docker CLI provided by Rancher Desktop
DOCKER ?= docker
CONTAINER_NAME ?= mythras-mysql
MYSQL_IMAGE ?= docker.io/library/mysql:8
HOST_PORT ?= 3307
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
apple-run-minimal docker-run-minimal:
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
git-repair:
	bash ./tools/git_repair.sh

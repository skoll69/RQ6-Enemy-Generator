#!/usr/bin/env bash
set -euo pipefail

# Uploads and imports a MySQL dump into the running MySQL 8 container.
# Supports .sql and .sql.gz files.
# By default imports as root unless --db and --user are provided.
# Requires the container to be running (use ./start_db.sh first).

# Apple container is the only supported CLI
if command -v container >/dev/null 2>&1; then
  CONTAINER_CLI=container
else
  echo "Error: 'container' CLI is required (https://github.com/apple/container/releases)." >&2
  exit 1
fi
CONTAINER_NAME=mythras-mysql
DUMP_PATH=""
TARGET_DB=""
MYSQL_USER_ARG=""
MYSQL_PWD_ARG=""
AS_ROOT=1
DEBUG_MODE=${DUMP_DEBUG:-0}

usage() {
  cat <<EOF
Usage: $0 [--db DB_NAME] [--user USER] [--password PASS] [--as-root] [--debug] [--mysql8-compat]

Options:
  --db DB_NAME         Database to import into (omit if dump contains CREATE DATABASE/USE)
  --user USER          MySQL user to import as (default: root when --as-root)
  --password PASS      Password for the chosen user (read from .env when possible)
  --as-root            Import as root using MYSQL_ROOT_PASSWORD from .env (default)
  --as-user            Import using provided --user/--password
  --debug              Print detailed debug info while running
  --mysql8-compat      Apply common MySQL 8 compatibility normalizations to the dump while importing

Environment:
  ENV_FILE=.env                       Path to .env file (default: .env if exists)
  MYSQL8_COMPAT=1                     Enable MySQL 8 compatibility normalization (same as --mysql8-compat)
  MYSQL_DATABASE / MYSQL_USER / MYSQL_PASSWORD / MYSQL_ROOT_PASSWORD may be read from .env
  DUMP_DEBUG=1                        Alternate way to enable debug output
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage; exit 0
fi

# Per requirement: do not autodiscover or accept other paths. Always use ./dump.sql
DUMP_PATH="./dump.sql"

# Defaults
ENV_FILE=${ENV_FILE:-.env}
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC2046
  export $(grep -E '^(MYSQL_DATABASE|MYSQL_USER|MYSQL_PASSWORD|MYSQL_ROOT_PASSWORD)=' "$ENV_FILE" | xargs -I{} echo {})
fi

MYSQL8_COMPAT=${MYSQL8_COMPAT:-0}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --db)
      TARGET_DB=${2:-}; shift 2;;
    --user)
      MYSQL_USER_ARG=${2:-}; shift 2;;
    --password)
      MYSQL_PWD_ARG=${2:-}; shift 2;;
    --as-root)
      AS_ROOT=1; shift;;
    --as-user)
      AS_ROOT=0; shift;;
    --debug)
      DEBUG_MODE=1; shift;;
    --mysql8-compat)
      MYSQL8_COMPAT=1; shift;;
    *)
      echo "Unknown argument: $1" >&2; usage; exit 1;;
  esac
done


# Debug helper
debug_print() {
  if [[ "$DEBUG_MODE" == "1" ]]; then
    echo "[DEBUG] $*" >&2
  fi
}

# Print a concise summary of options in effect (no secrets)
print_options_summary() {
  local mode="root"
  local mysql_user_display
  if [[ $AS_ROOT -eq 1 ]]; then
    mode="root"
    mysql_user_display="root"
  else
    mode="user"
    mysql_user_display="${MYSQL_USER_ARG:-}"
  fi
  local db_display="(auto)"
  if [[ -n "$TARGET_DB" ]]; then db_display="$TARGET_DB"; fi
  local gz="no"
  if [[ "${DUMP_PATH}" == *.gz ]]; then gz="yes"; fi
  echo "Options in effect:" >&2
  echo "  CLI           : ${CONTAINER_CLI}" >&2
  echo "  Container     : ${CONTAINER_NAME}" >&2
  echo "  Dump file     : ${DUMP_PATH}" >&2
  echo "  Gzip          : ${gz}" >&2
  echo "  Import mode   : ${mode}" >&2
  echo "  MySQL user    : ${mysql_user_display}" >&2
  echo "  Target DB     : ${db_display}" >&2
  echo "  ENV file      : ${ENV_FILE}" >&2
  echo "  AUTO_START_DB : ${AUTO_START_DB:-0}" >&2
  echo "  MySQL8 compat : ${MYSQL8_COMPAT}" >&2
  if [[ "$DEBUG_MODE" == "1" ]]; then
    echo "  Debug mode    : enabled" >&2
  fi
}

# Validate dump path and existence
if [[ ! -f "$DUMP_PATH" ]]; then
  echo "Error: Dump file not found: $DUMP_PATH" >&2
  echo "This tool now only uses './dump.sql' in the project root. Please place your SQL dump there." >&2
  exit 1
fi

# Heuristic content check: fail early if the file looks like a shell command instead of SQL
# Read first few lines only
content_sample=$(LC_ALL=C head -n 5 "$DUMP_PATH" 2>/dev/null || true)
if echo "$content_sample" | grep -qiE '^\s*(sudo|docker|container)\b'; then
  echo "Error: The provided file appears to contain shell commands, not SQL. Please provide a real SQL dump file (e.g., .sql or .sql.gz)." >&2
  echo "Hint: To create a dump from a running container: container exec mythras-mysql mysqldump -uroot -p\"$MYSQL_ROOT_PASSWORD\" --databases mythras_eg > dump.sql" >&2
  exit 2
fi
if echo "$content_sample" | grep -qiE 'mysqldump\s+.*>\s*dump\.sql'; then
  echo "Error: The provided file contains a redirect to create a dump, not the SQL dump itself. Use the resulting dump.sql as input." >&2
  exit 2
fi
if echo "$content_sample" | grep -qiE '^\s*#!'; then
  echo "Error: The provided file looks like a script (shebang detected), not a SQL dump." >&2
  exit 2
fi

debug_print "ENV_FILE=$ENV_FILE"
debug_print "CONTAINER_CLI=$CONTAINER_CLI"
debug_print "CONTAINER_NAME=$CONTAINER_NAME"
debug_print "Using fixed dump path: $DUMP_PATH"
echo "Using dump file: $DUMP_PATH" >&2

# Print one-line options summary (no secrets)
print_options_summary

# If running in no-compose workflow, detect host data directory emptiness to decide DB ensure step
# Legacy default was '.apple_container/mysql_data' (kept here as a comment for reference)
# DATA_DIR_DEFAULT=".apple_container/mysql_data"
DATA_DIR_DEFAULT="$HOME/container-data/mysql"
DATA_DIR_FROM_ENV=$(grep -E '^DATA_DIR=' "$ENV_FILE" | tail -n1 | cut -d'=' -f2- || true)
DATA_DIR_PATH=${DATA_DIR_FROM_ENV:-$DATA_DIR_DEFAULT}
DB_DIR_EMPTY=0
if [[ -d "$DATA_DIR_PATH" ]]; then
  # Consider empty if no files inside
  if [[ -z "$(ls -A "$DATA_DIR_PATH" 2>/dev/null)" ]]; then
    DB_DIR_EMPTY=1
    echo "Detected empty database directory at $DATA_DIR_PATH; will ensure target database exists before import." >&2
  fi
fi

# Validate CLI and container
if ! command -v "$CONTAINER_CLI" >/dev/null 2>&1; then
  echo "Error: '$CONTAINER_CLI' CLI not found in PATH." >&2; exit 1
fi

if ! "$CONTAINER_CLI" inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  echo "Error: Container '$CONTAINER_NAME' not found. Start it first." >&2
  echo "Hints:" >&2
  echo " - Start it with the required syntax (Apple container):" >&2
  echo "   container run \\" >&2
  echo "     --name mythras-mysql \\" >&2
  echo "     --publish 127.0.0.1:3307:3306 \\" >&2
  echo "     --env MYSQL_ROOT_PASSWORD=\"$$MYSQL_ROOT_PASSWORD\" \\" >&2
  echo "     docker.io/library/mysql:8" >&2
  echo " - Or via Makefile: make start-db (runs the exact command above)" >&2
  exit 1
fi

# Determine running state via inspect
state=$("$CONTAINER_CLI" inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo unknown)
debug_print "Container state via inspect: $state"

# Fallback for Apple container: if inspect is unreliable, consult `container list`
if [[ "$state" != "running" && "$CONTAINER_CLI" == "container" ]]; then
  list_line=$(container list --all 2>/dev/null | awk -v name="$CONTAINER_NAME" 'NR>1 && $1==name {print $0}')
  if [[ -n "$list_line" && "$list_line" == *" running "* ]]; then
    debug_print "Fallback: container list shows '$CONTAINER_NAME' running; proceeding despite inspect state '$state'"
    state="running"
  else
    debug_print "Fallback: container list did not confirm running state for '$CONTAINER_NAME'"
  fi
fi

if [[ "$state" != "running" ]]; then
  echo "Error: Container '$CONTAINER_NAME' not running (state: $state). Start it first (e.g., ./run_db_nocompose.sh)." >&2
  exit 1
fi

# Determine import command
IMPORT_CMD=("mysql")
DUMP_CMD=("cat")
if [[ "$DUMP_PATH" == *.gz ]]; then
  if command -v zcat >/dev/null 2>&1; then
    DUMP_CMD=("zcat")
  else
    echo "Error: zcat not found; required for .gz dumps." >&2; exit 1
  fi
fi

# If AUTO_START_DB=1 and importing as root, and no --db was given, choose a DB to create/use
# Priority: TARGET_DB (if set) > MYSQL_DATABASE > DB_NAME
if [[ -z "$TARGET_DB" && "$AS_ROOT" -eq 1 && "${AUTO_START_DB:-0}" == "1" ]]; then
  if [[ -n "${MYSQL_DATABASE:-}" ]]; then
    TARGET_DB="$MYSQL_DATABASE"
  elif [[ -f "$ENV_FILE" ]]; then
    # Try to read DB_NAME from .env lazily without exporting everything
    _ENV_DB_NAME=$(grep -E '^DB_NAME=' "$ENV_FILE" | tail -n1 | cut -d'=' -f2- || true)
    if [[ -n "$_ENV_DB_NAME" ]]; then TARGET_DB="$_ENV_DB_NAME"; fi
  fi
  if [[ -n "$TARGET_DB" ]]; then
    echo "[auto] Will ensure and import into database: $TARGET_DB" >&2
  else
    echo "[auto] No explicit target DB selected; relying on dump statements or server default." >&2
  fi
fi

# Additional robust fallback: when importing as root and TARGET_DB still empty,
# resolve from MYSQL_DATABASE or DB_NAME regardless of AUTO_START_DB or data dir state.
if [[ -z "$TARGET_DB" && "$AS_ROOT" -eq 1 ]]; then
  if [[ -n "${MYSQL_DATABASE:-}" ]]; then
    TARGET_DB="$MYSQL_DATABASE"
  elif [[ -f "$ENV_FILE" ]]; then
    _ENV_DB_NAME=$(grep -E '^DB_NAME=' "$ENV_FILE" | tail -n1 | cut -d'=' -f2- || true)
    if [[ -n "$_ENV_DB_NAME" ]]; then TARGET_DB="$_ENV_DB_NAME"; fi
  fi
  if [[ -n "$TARGET_DB" ]]; then
    echo "[auto] Resolved target database: $TARGET_DB" >&2
  fi
fi

debug_print "DUMP_CMD=${DUMP_CMD[*]}"

if [[ $AS_ROOT -eq 1 ]]; then
  MYSQL_USER_ARG="root"
  MYSQL_PWD_ARG=${MYSQL_ROOT_PASSWORD:-}
  if [[ -z "${MYSQL_PWD_ARG}" ]]; then
    echo "Error: MYSQL_ROOT_PASSWORD not set. Put it in .env or pass --as-user with --user/--password." >&2
    exit 1
  fi
  debug_print "Importing as root"
else
  debug_print "Importing as user: $MYSQL_USER_ARG"
fi

# If DB specified or auto-selected, or if host data dir is empty, ensure DB exists (when using root)
if [[ -n "$TARGET_DB" || $DB_DIR_EMPTY -eq 1 ]]; then
  # Resolve DB name if not explicitly provided, preferring MYSQL_DATABASE then DB_NAME from .env
  if [[ -z "$TARGET_DB" ]]; then
    if [[ -n "${MYSQL_DATABASE:-}" ]]; then
      TARGET_DB="$MYSQL_DATABASE"
    else
      _ENV_DB_NAME=$(grep -E '^DB_NAME=' "$ENV_FILE" | tail -n1 | cut -d'=' -f2- || true)
      TARGET_DB="${_ENV_DB_NAME:-}"
    fi
    if [[ -n "$TARGET_DB" ]]; then
      echo "[auto] Empty data dir detected; will create and import into database: $TARGET_DB" >&2
    else
      echo "[auto] Empty data dir detected but no DB name resolved (set --db or MYSQL_DATABASE/DB_NAME). Proceeding without PRE-create; relying on dump statements." >&2
    fi
  fi
  if [[ -n "$TARGET_DB" ]]; then
    if [[ $AS_ROOT -eq 1 ]]; then
      debug_print "Ensuring database exists: $TARGET_DB"
      "$CONTAINER_CLI" exec -i "$CONTAINER_NAME" mysql -uroot -p"$MYSQL_PWD_ARG" -e "CREATE DATABASE IF NOT EXISTS \`$TARGET_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
    else
      echo "Note: Database creation requested but not running as root; ensure DB exists: $TARGET_DB" >&2
    fi
    IMPORT_CMD+=("$TARGET_DB")
  fi
fi

debug_print "IMPORT_CMD=${IMPORT_CMD[*]}"

# Build mysql auth flags
MYSQL_FLAGS=("-u${MYSQL_USER_ARG}")
if [[ -n "$MYSQL_PWD_ARG" ]]; then
  MYSQL_FLAGS+=("-p${MYSQL_PWD_ARG}")
fi

debug_print "MYSQL_FLAGS=${MYSQL_FLAGS[*]}"

# Build optional MySQL 8 compatibility filter
build_mysql8_filter() {
  # sed expressions to normalize common incompatibilities:
  # - remove DEFINER clauses and /*!50013 DEFINER=... */ (single-line)
  # - change SQL SECURITY DEFINER -> SQL SECURITY INVOKER (safer)
  # - drop GTID_PURGED and SQL_LOG_BIN statements
  # Use BSD/macOS sed-friendly patterns (no GNU-specific I modifier on address commands).
  sed -E \
    -e 's|/\*![0-9][0-9]*[[:space:]]+DEFINER=`[^`]+`@`[^`]+`[[:space:]]+\*/||g' \
    -e 's|DEFINER=`[^`]+`@`[^`]+`||g' \
    -e 's/[Ss][Qq][Ll][[:space:]]+[Ss][Ee][Cc][Uu][Rr][Ii][Tt][Yy][[:space:]]+[Dd][Ee][Ff][Ii][Nn][Ee][Rr]/SQL SECURITY INVOKER/g' \
    -e '/^[[:space:]]*[Ss][Ee][Tt][[:space:]]+@@[Gg][Ll][Oo][Bb][Aa][Ll]\.[Gg][Tt][Ii][Dd]_[Pp][Uu][Rr][Gg][Ee][Dd]/d' \
    -e '/^[[:space:]]*[Ss][Ee][Tt][[:space:]]+[Ss][Qq][Ll]_[Ll][Oo][Gg]_[Bb][Ii][Nn][[:space:]]*=.*/d'
}

# Helper to show error context around a failing line
show_error_context() {
  local errfile="$1"
  local dumpfile="$2"
  local lineno
  lineno=$(grep -Eo 'at line [0-9]+' "$errfile" | tail -n1 | awk '{print $3}' || true)
  if [[ -n "$lineno" && -f "$dumpfile" ]]; then
    echo "--- Context around line $lineno in $dumpfile ---" >&2
    awk -v n="$lineno" 'NR>=n-5 && NR<=n+5 {printf "%6d | %s\n", NR, $0}' "$dumpfile" >&2
    echo "--- end context ---" >&2
  fi
}

# Stream import without copying file into container
TMP_ERR=$(mktemp 2>/dev/null || echo "/tmp/upload_dump_err.$$")
echo "Importing $DUMP_PATH into container $CONTAINER_NAME using $CONTAINER_CLI..."
set +e
if [[ "${DUMP_CMD[0]}" == "zcat" ]]; then
  if [[ "$MYSQL8_COMPAT" == "1" ]]; then
    debug_print "Command: (echo SET NAMES utf8mb4; zcat) | sed(filters) | exec mysql"
    { echo "SET NAMES utf8mb4;"; zcat "$DUMP_PATH"; } \
      | build_mysql8_filter \
      | "$CONTAINER_CLI" exec -i "$CONTAINER_NAME" "${IMPORT_CMD[@]}" "${MYSQL_FLAGS[@]}" 2>"$TMP_ERR"
  else
    debug_print "Command: zcat '$DUMP_PATH' | $CONTAINER_CLI exec -i $CONTAINER_NAME ${IMPORT_CMD[*]} ${MYSQL_FLAGS[*]}"
    zcat "$DUMP_PATH" | "$CONTAINER_CLI" exec -i "$CONTAINER_NAME" "${IMPORT_CMD[@]}" "${MYSQL_FLAGS[@]}" 2>"$TMP_ERR"
  fi
else
  if [[ "$MYSQL8_COMPAT" == "1" ]]; then
    debug_print "Command: (echo SET NAMES utf8mb4; cat) | sed(filters) | exec mysql"
    { echo "SET NAMES utf8mb4;"; cat "$DUMP_PATH"; } \
      | build_mysql8_filter \
      | "$CONTAINER_CLI" exec -i "$CONTAINER_NAME" "${IMPORT_CMD[@]}" "${MYSQL_FLAGS[@]}" 2>"$TMP_ERR"
  else
    debug_print "Command: cat '$DUMP_PATH' | $CONTAINER_CLI exec -i $CONTAINER_NAME ${IMPORT_CMD[*]} ${MYSQL_FLAGS[*]}"
    cat "$DUMP_PATH" | "$CONTAINER_CLI" exec -i "$CONTAINER_NAME" "${IMPORT_CMD[@]}" "${MYSQL_FLAGS[@]}" 2>"$TMP_ERR"
  fi
fi
status=$?
set -e
if [[ $status -ne 0 ]]; then
  echo "Import failed (exit code $status). mysql stderr:" >&2
  cat "$TMP_ERR" >&2 || true
  show_error_context "$TMP_ERR" "$DUMP_PATH"
  rm -f "$TMP_ERR" >/dev/null 2>&1 || true
  exit $status
fi
rm -f "$TMP_ERR" >/dev/null 2>&1 || true

echo "Import completed."

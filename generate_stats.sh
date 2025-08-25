#!/usr/bin/env bash
set -euo pipefail
# Generate a statistics report of table row counts for a MySQL database
# running inside the Apple container 'mythras-mysql'.
#
# Usage:
#   ./generate_stats.sh
# Environment:
#   ENV_FILE=.env (default) used to read MYSQL_ROOT_PASSWORD and DB_NAME if not provided
#   CONTAINER=container (Apple container CLI is required)
#   STAT_DIR=statistic (output directory)
#   KEEP=10 (number of latest files to keep)

CONTAINER_CLI=${CONTAINER:-container}
CONTAINER_NAME=${CONTAINER_NAME:-mythras-mysql}
ENV_FILE=${ENV_FILE:-.env}
STAT_DIR=${STAT_DIR:-statistic}
KEEP=${KEEP:-10}
TARGET_DB=""

usage(){
  cat <<EOF
Usage: $0
Generates a statistics file listing all tables in DB_NAME (from .env/environment) and their row counts.
Writes to ${STAT_DIR}/<timestamp>-table-counts-<db>.txt and keeps only the latest ${KEEP} files.
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then usage; exit 0; fi

if ! command -v "$CONTAINER_CLI" >/dev/null 2>&1; then
  echo "Error: '$CONTAINER_CLI' CLI not found. This tool requires Apple container." >&2
  exit 1
fi

# Load minimal env
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

# Resolve DB strictly from DB_NAME
if [[ -z "$TARGET_DB" && -n "${DB_NAME:-}" ]]; then TARGET_DB="$DB_NAME"; fi
if [[ -z "$TARGET_DB" ]]; then
  echo "Error: Set DB_NAME in $ENV_FILE or environment." >&2
  exit 1
fi

ROOT_PW=${MYSQL_ROOT_PASSWORD:-}
if [[ -z "$ROOT_PW" ]]; then
  echo "Error: MYSQL_ROOT_PASSWORD must be set in $ENV_FILE or environment." >&2
  exit 1
fi

# Verify container running
state=$("$CONTAINER_CLI" list --all 2>/dev/null | awk -v n="$CONTAINER_NAME" 'NR>1 && $1==n {print $5}')
if [[ "$state" != "running" ]]; then
  echo "Error: Container '$CONTAINER_NAME' is not running (state: ${state:-unknown})." >&2
  exit 1
fi

mkdir -p "$STAT_DIR" 2>/dev/null || true
TS=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="$STAT_DIR/${TS}-table-counts-${TARGET_DB}.txt"
{
  echo "# Table row counts for database '$TARGET_DB'"
  echo "# Generated: $(date)"
  echo "# Container: $CONTAINER_NAME"
  echo
} > "$REPORT_FILE"

# List tables
LIST_SQL="SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='${TARGET_DB}' ORDER BY TABLE_NAME;"
TABLES_OUT=$("$CONTAINER_CLI" exec -i "$CONTAINER_NAME" \
  sh -lc "MYSQL_PWD='${ROOT_PW}' mysql -N -B -uroot -e \"$LIST_SQL\"") || true

if [[ -n "$TABLES_OUT" ]]; then
  FIRST_FAIL_NOTED=0
  while IFS= read -r T; do
    # Strip CRs and skip blank lines
    T=${T//$'\r'/}
    [[ -z "$T" ]] && continue

    # Escape any literal backticks for MySQL identifier quoting
    T_ESC=${T//\`/\`\`}

    # Build SQL safely with backticks intact
    printf -v SQL 'SELECT COUNT(*) FROM `%s`;' "$T_ESC"

    # Feed SQL via STDIN to avoid backtick parsing by shell
    if ! C_OUT=$(printf '%s\n' "$SQL" | \
          "$CONTAINER_CLI" exec -i "$CONTAINER_NAME" \
            sh -lc "MYSQL_PWD='${ROOT_PW}' mysql -N -B -uroot -D \"$TARGET_DB\"" \
        ); then
      if [[ $FIRST_FAIL_NOTED -eq 0 ]]; then
        echo "# Note: Failed to count some tables; leaving '?' for those." >> "$REPORT_FILE"
        FIRST_FAIL_NOTED=1
      fi
      C_TRIM="?"
    else
      C_TRIM=${C_OUT//$'\r'/}
    fi

    printf "%s\t%s\n" "$T" "$C_TRIM" >> "$REPORT_FILE"
  done <<< "$TABLES_OUT"
else
  echo "(no tables found in ${TARGET_DB})" >> "$REPORT_FILE"
fi

# Retention: keep only the latest $KEEP files
ls -1t "$STAT_DIR"/*-table-counts-*.txt 2>/dev/null | awk -v k="$KEEP" 'NR>k' | xargs -r rm -f

echo "Statistics report written to: $REPORT_FILE" >&2
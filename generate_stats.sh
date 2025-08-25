#!/usr/bin/env bash
set -euo pipefail
# Generate a statistics report of table row counts for a MySQL database
# running inside the Apple container 'mythras-mysql'.
# This is separated from upload_dump.sh by requirement.
#
# Usage:
#   ./generate_stats.sh [--db DB_NAME]
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
Usage: $0 [--db DB_NAME]
Generates a statistics file listing all tables in DB_NAME and their row counts.
Writes to ${STAT_DIR}/<timestamp>-table-counts-<db>.txt and keeps only the latest ${KEEP} files.
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then usage; exit 0; fi
if [[ ${1:-} == "--db" ]]; then TARGET_DB=${2:-}; shift 2 || true; fi

if ! command -v "$CONTAINER_CLI" >/dev/null 2>&1; then
  echo "Error: '$CONTAINER_CLI' CLI not found. This tool requires Apple container." >&2
  exit 1
fi

# Load minimal env
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC2046
  export $(grep -E '^(MYSQL_DATABASE|DB_NAME|MYSQL_ROOT_PASSWORD)=' "$ENV_FILE" | xargs -I{} echo {})
fi

# Resolve DB
if [[ -z "$TARGET_DB" ]]; then
  if [[ -n "${MYSQL_DATABASE:-}" ]]; then TARGET_DB="$MYSQL_DATABASE"; fi
fi
if [[ -z "$TARGET_DB" && -n "${DB_NAME:-}" ]]; then TARGET_DB="$DB_NAME"; fi
if [[ -z "$TARGET_DB" ]]; then
  echo "Error: No database specified. Provide --db or set DB_NAME/MYSQL_DATABASE in $ENV_FILE." >&2
  exit 1
fi

ROOT_PW=${MYSQL_ROOT_PASSWORD:-}
if [[ -z "$ROOT_PW" ]]; then
  echo "Error: MYSQL_ROOT_PASSWORD must be set in $ENV_FILE or environment." >&2
  exit 1
fi

# Verify container running
if ! "$CONTAINER_CLI" inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  echo "Error: Container '$CONTAINER_NAME' not found. Start DB first." >&2
  exit 1
fi
state=$("$CONTAINER_CLI" inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo unknown)
if [[ "$state" != "running" ]]; then
  echo "Error: Container '$CONTAINER_NAME' is not running (state: $state)." >&2
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

# List tables and count
LIST_SQL="SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='${TARGET_DB}' ORDER BY TABLE_NAME;"
set +e
TABLES_OUT=$("$CONTAINER_CLI" exec -i "$CONTAINER_NAME" sh -c "MYSQL_PWD='${ROOT_PW}' mysql -N -B -uroot -e \"$LIST_SQL\"")
LIST_STATUS=$?
set -e
if [[ $LIST_STATUS -ne 0 ]]; then
  echo "# Warning: Could not list tables for '${TARGET_DB}'." >> "$REPORT_FILE"
  echo "(no tables found in ${TARGET_DB} or query failed)" >> "$REPORT_FILE"
else
  if [[ -n "$TABLES_OUT" ]]; then
    FIRST_FAIL_NOTED=0
    while IFS= read -r T; do
      T_ESC=${T//`/\`}
      CNT_CMD="MYSQL_PWD='${ROOT_PW}' mysql -N -B -uroot -D \"${TARGET_DB}\" -e \"SELECT COUNT(*) FROM \`$T_ESC\`;\""
      set +e
      C_OUT=$("$CONTAINER_CLI" exec -i "$CONTAINER_NAME" sh -c "$CNT_CMD" 2>/tmp/meg_stats_err.$$)
      C_STATUS=$?
      set -e
      if [[ $C_STATUS -ne 0 || -z "$C_OUT" ]]; then
        if [[ $FIRST_FAIL_NOTED -eq 0 ]]; then
          ERR_TXT=$(cat /tmp/meg_stats_err.$$ 2>/dev/null | tail -n1)
          echo "# Note: Failed to count some tables; leaving '?' for those. Last error: ${ERR_TXT}" >> "$REPORT_FILE"
          FIRST_FAIL_NOTED=1
        fi
        C_TRIM="?"
      else
        C_TRIM=$(echo "$C_OUT" | tr -d '\r\n')
      fi
      echo -e "${T}\t${C_TRIM}" >> "$REPORT_FILE"
      rm -f /tmp/meg_stats_err.$$ >/dev/null 2>&1 || true
    done <<< "$TABLES_OUT"
  else
    echo "(no tables found in ${TARGET_DB})" >> "$REPORT_FILE"
  fi
fi

# Retention: keep only the latest $KEEP files
ls -1t "$STAT_DIR"/*-table-counts-*.txt 2>/dev/null | awk -v k="$KEEP" 'NR>k' | xargs -I{} sh -c 'rm -f "$1"' _ {} 2>/dev/null || true

echo "Statistics report written to: $REPORT_FILE" >&2

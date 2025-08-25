#!/usr/bin/env bash
set -euo pipefail
# Static analyzer for MySQL dump files with MySQL 8.0 compatibility hints
# Defaults to analyzing ./dump.sql and printing a summary; can also emit a
# normalized copy suitable for MySQL 8 via --fix-out.
#
# Usage examples:
#   ./analyze_dump.sh                   # analyze ./dump.sql and print report
#   ./analyze_dump.sh --file dump.sql --mysql8 --summary
#   ./analyze_dump.sh --file dump.sql --mysql8 --fix-out dump.mysql8.sql --utf8mb4
#   make analyze-dump                   # Makefile helper (defaults to ./dump.sql)
#
# Checks include:
# - DEFINER clauses and SQL SECURITY DEFINER
# - SET @@GLOBAL.GTID_PURGED and SET SQL_LOG_BIN statements
# - IDENTIFIED BY PASSWORD (removed)
# - Old utf8/utf8mb3 charsets and collations
# - ZERO-DATEs like '0000-00-00' (can fail under strict SQL modes)
# - Deprecated sql_mode tokens (NO_AUTO_CREATE_USER)
# - CREATE VIEW/TRIGGER/PROC with DEFINER
# - TIMESTAMP DEFAULT/ON UPDATE combos that might fail under stricter modes (heuristic)
#
# Normalizations performed by --fix-out (subset of upload_dump.sh transformations):
# - remove DEFINER clauses and /*!50013 DEFINER=... */ wrappers
# - change SQL SECURITY DEFINER -> SQL SECURITY INVOKER
# - drop GTID_PURGED and SQL_LOG_BIN lines
# - optionally map charset/collation utf8/utf8mb3 to utf8mb4 when --utf8mb4 is provided

FILE="./dump.sql"
DO_MYSQL8=0
SUMMARY=1
LINES=3
FIX_OUT=""
DO_UTF8MB4=0
STRIP_DEFINER=0
STRIP_GTID=0
STRIP_SQLLOGBIN=0
DEBUG=${DEBUG:-0}

usage() {
  cat <<EOF
Usage: $0 [--file PATH] [--mysql8] [--summary] [--lines N] [--fix-out OUT.sql]
          [--utf8mb4] [--strip-definer] [--strip-gtid] [--strip-sql-log-bin]
          [--debug]

Options:
  --file PATH           Dump file to analyze (default: ./dump.sql)
  --mysql8              Enable MySQL 8 compatibility checks (default: off)
  --summary             Print human-readable summary (default: on)
  --lines N             Context lines to show around matches (default: 3)
  --fix-out OUT.sql     Write a normalized MySQL 8-friendly dump to OUT.sql
  --utf8mb4             When fixing, map utf8/utf8mb3 charsets/collations to utf8mb4
  --strip-definer       When fixing, remove DEFINER and SQL SECURITY DEFINER
  --strip-gtid          When fixing, drop SET @@GLOBAL.GTID_PURGED lines
  --strip-sql-log-bin   When fixing, drop SET SQL_LOG_BIN lines
  --debug               Print debug information

Notes:
- The --mysql8 flag automatically implies the following default fix flags if --fix-out is used:
    --strip-definer --strip-gtid --strip-sql-log-bin
- Use --utf8mb4 together with --fix-out to upgrade old utf8/utf8mb3 charsets to utf8mb4.
EOF
}

dbg() { if [[ "$DEBUG" == "1" ]]; then echo "[DEBUG] $*" >&2; fi }

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) FILE=${2:-}; shift 2;;
    --mysql8) DO_MYSQL8=1; shift;;
    --summary) SUMMARY=1; shift;;
    --lines) LINES=${2:-3}; shift 2;;
    --fix-out) FIX_OUT=${2:-}; shift 2;;
    --utf8mb4) DO_UTF8MB4=1; shift;;
    --strip-definer) STRIP_DEFINER=1; shift;;
    --strip-gtid) STRIP_GTID=1; shift;;
    --strip-sql-log-bin) STRIP_SQLLOGBIN=1; shift;;
    --debug) DEBUG=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1" >&2; usage; exit 1;;
  esac
done

if [[ ! -f "$FILE" ]]; then
  echo "Error: dump file not found: $FILE" >&2
  exit 1
fi

echo "Analyzing dump file: $FILE" >&2

# Define helper: search with context that prints line numbers and short hints
report_match() {
  local pattern="$1"; shift
  local hint="$1"; shift
  local flags="${1:-}"; shift || true
  # Use grep -nE for line numbers; use -i for case-insensitive when requested via flags
  local gi=""; if [[ "$flags" == *i* ]]; then gi="-i"; fi
  if grep -nE $gi -- "$pattern" "$FILE" >/dev/null 2>&1; then
    echo "- Found: $hint" >&2
    # Show small context around first few matches for clarity
    # macOS grep supports -n -E -i and -C N for context
    grep -nE $gi -C "$LINES" -- "$pattern" "$FILE" | sed 's/^/    /' >&2 || true
  fi
}

# Perform checks
if [[ $SUMMARY -eq 1 ]]; then
  printf "\nChecks (potential MySQL 8 issues):\n" >&2
fi

# DEFINER and SQL SECURITY DEFINER
report_match 'DEFINER=`[^`]+`@`[^`]+`' \
  "DEFINER clauses (may require removal or change to INVOKER on MySQL 8)." i
report_match "SQL[[:space:]]+SECURITY[[:space:]]+DEFINER" \
  "SQL SECURITY DEFINER detected; consider SQL SECURITY INVOKER." i
# Wrapped definer in comments like /*!50013 DEFINER=`...` */
report_match '/\*!50013[[:space:]]+DEFINER=`[^`]+`@`[^`]+`[[:space:]][^*]*\*/' \
  "Comment-wrapped DEFINER found (/*!50013 DEFINER=... */)." 

# GTID_PURGED / SQL_LOG_BIN
report_match "^SET[[:space:]]+@@GLOBAL\\.GTID_PURGED" \
  "SET @@GLOBAL.GTID_PURGED present; often blocked on restore without GTID setup." i
report_match "^SET[[:space:]]+SQL_LOG_BIN[[:space:]]*=" \
  "SET SQL_LOG_BIN present; restricted on MySQL 8 (non-super users)." i

# IDENTIFIED BY PASSWORD (removed)
report_match "IDENTIFIED[[:space:]]+BY[[:space:]]+PASSWORD" \
  "IDENTIFIED BY PASSWORD is removed in MySQL 8; use IDENTIFIED BY 'secret' instead." i

# Old utf8/utf8mb3 charset/collations
report_match "CHARSET=(utf8|utf8mb3)([^a-zA-Z0-9_]|$)" \
  "Old charset 'utf8' (utf8mb3) detected; prefer utf8mb4 on MySQL 8." i
report_match "COLLATE=(utf8_|utf8mb3_)" \
  "Old utf8 collations detected; consider utf8mb4_0900_ai_ci or a suitable utf8mb4 collation." i

# ZERO-DATEs (0000-00-00)
report_match "'0000-00-00'|'0000-00-00 00:00:00'" \
  "Zero dates detected; may fail under NO_ZERO_DATE / strict modes in MySQL 8." 

# Deprecated sql_mode tokens
report_match "NO_AUTO_CREATE_USER" \
  "Deprecated sql_mode token NO_AUTO_CREATE_USER found; removed in MySQL 8." 

# CREATE VIEW/PROCEDURE/TRIGGER with DEFINER already captured, but also check for those objects
report_match '^CREATE[[:space:]]+(DEFINER=`[^`]+`@`[^`]+`[[:space:]]+)?VIEW([[:space:]]|\()' \
  "CREATE VIEW statements; verify DEFINER and security semantics." i
report_match '^CREATE[[:space:]]+(DEFINER=`[^`]+`@`[^`]+`[[:space:]]+)?TRIGGER([[:space:]]|\()' \
  "CREATE TRIGGER statements; verify DEFINER and SQL SECURITY." i
report_match '^CREATE[[:space:]]+(DEFINER=`[^`]+`@`[^`]+`[[:space:]]+)?PROCEDURE([[:space:]]|\()' \
  "CREATE PROCEDURE statements; verify DEFINER and SQL SECURITY." i

# TIMESTAMP DEFAULT / ON UPDATE patterns (heuristic warning)
report_match "TIMESTAMP[[:space:]]+.*DEFAULT[[:space:]]+['0-9:-]+[[:space:]]+ON[[:space:]]+UPDATE" \
  "TIMESTAMP with DEFAULT ... ON UPDATE combination; validate against strict modes." i

# Summary footer
if [[ $SUMMARY -eq 1 ]]; then
  echo "\nTip: You can generate a MySQL 8–friendly copy using --fix-out OUT.sql.\n" >&2
fi

# If no fix requested, stop here
if [[ -z "$FIX_OUT" ]]; then
  exit 0
fi

# Default fix flags implied by --mysql8 (unless user explicitly set others)
if [[ $DO_MYSQL8 -eq 1 ]]; then
  [[ $STRIP_DEFINER -eq 0 ]] && STRIP_DEFINER=1
  [[ $STRIP_GTID -eq 0 ]] && STRIP_GTID=1
  [[ $STRIP_SQLLOGBIN -eq 0 ]] && STRIP_SQLLOGBIN=1
fi

echo "Writing normalized dump to: $FIX_OUT" >&2

# Build sed script dynamically
SED_ARGS=()
# Remove /*!50013 DEFINER=... */ wrappers and bare DEFINER clauses, change SQL SECURITY
if [[ $STRIP_DEFINER -eq 1 ]]; then
  SED_ARGS+=(
    -e 's/\/\*!50013 DEFINER=`[^`]+`@`[^`]+` [^*]*\*\///g'
    -e 's/DEFINER=`[^`]+`@`[^`]+`//g'
    -e 's/SQL SECURITY[ ]+DEFINER/SQL SECURITY INVOKER/gI'
  )
fi
# Drop GTID_PURGED
if [[ $STRIP_GTID -eq 1 ]]; then
  SED_ARGS+=( -e '/^SET[ ]+@@GLOBAL\.GTID_PURGED/dI' )
fi
# Drop SQL_LOG_BIN
if [[ $STRIP_SQLLOGBIN -eq 1 ]]; then
  SED_ARGS+=( -e '/^SET[ ]+SQL_LOG_BIN[ ]*=.*/dI' )
fi
# Map utf8/utf8mb3 to utf8mb4 (charset and some common collations)
if [[ $DO_UTF8MB4 -eq 1 ]]; then
  SED_ARGS+=(
    -e 's/CHARSET=(utf8mb3|utf8)\b/CHARSET=utf8mb4/Ig'
    -e 's/\butf8_general_ci\b/utf8mb4_0900_ai_ci/Ig'
    -e 's/\butf8_unicode_ci\b/utf8mb4_0900_ai_ci/Ig'
  )
fi

# Apply transformations
if [[ ${#SED_ARGS[@]} -eq 0 ]]; then
  # Nothing to change; just copy
  cp "$FILE" "$FIX_OUT"
else
  # shellcheck disable=SC2068
  sed -E ${SED_ARGS[@]} -- "$FILE" > "$FIX_OUT" || { echo "Error: sed normalization failed." >&2; exit 2; }
fi

echo "Done. Review $FIX_OUT and try importing it (e.g., make upload-dump-debug --mysql8-compat)." >&2

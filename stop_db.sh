#!/usr/bin/env bash
set -euo pipefail

# Stops the MySQL 8 container using Apple container CLI only.
# Default behavior: stop and remove the single container (mythras-mysql).
# Use --volumes to also remove the local data directory used in no-compose mode.

# Apple container is the only supported CLI
CONTAINER_CLI=container
SERVICE_NAME=db
CONTAINER_NAME=mythras-mysql

usage() {
  cat <<EOF
Usage: $0 [--volumes]

Options:
  --volumes   Remove named volumes as well (data loss!)

Environment:
  REMOVE_VOLUMES=1             Also remove local data dir
EOF
}

REMOVE_VOLUMES=0
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage; exit 0
elif [[ "${1:-}" == "--volumes" ]]; then
  REMOVE_VOLUMES=1
fi
# Honor environment override (e.g., make stop-db VOLUMES=1 -> REMOVE_VOLUMES=1)
if [[ "${REMOVE_VOLUMES:-0}" == "1" ]]; then
  REMOVE_VOLUMES=1
fi

# Verify CLI available
if ! command -v "$CONTAINER_CLI" >/dev/null 2>&1; then
  echo "Error: 'container' CLI not found in PATH. Install it from https://github.com/apple/container/releases" >&2
  exit 1
fi

# Stop/remove the single container created by the minimal Apple container run
if "$CONTAINER_CLI" inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  state=$("$CONTAINER_CLI" inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo unknown)
  if [[ "$state" == "running" ]]; then
    echo "Killing container $CONTAINER_NAME..."; "$CONTAINER_CLI" kill "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
  echo "Removing container $CONTAINER_NAME..."; "$CONTAINER_CLI" rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
  # Double-check removal and retry once if still present
  if "$CONTAINER_CLI" inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "Container still present; retrying force removal...";
    "$CONTAINER_CLI" kill "$CONTAINER_NAME" >/dev/null 2>&1 || true
    "$CONTAINER_CLI" rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
else
  echo "Container $CONTAINER_NAME not found; nothing to stop."
fi

if [[ $REMOVE_VOLUMES -eq 1 ]]; then
  # Previously defaulted to .apple_container/mysql_data
  DATA_DIR=${DATA_DIR:-$HOME/container-data/mysql}
  echo "Removing data directory ${DATA_DIR} (data loss!)"; rm -rf "$DATA_DIR"
else
  echo "Tip: To also wipe the local data directory, run with --volumes or set VOLUMES=1 (e.g., 'make stop-db VOLUMES=1')." >&2
fi

echo "Done."

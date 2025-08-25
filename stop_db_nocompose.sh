#!/usr/bin/env bash
set -euo pipefail

# Stop/remove MySQL 8 started without compose using Apple container only
# Usage:
#   ./stop_db_nocompose.sh [--volumes]
#
# Options:
#   --volumes   Remove the host data directory as well (DATA_DIR)
#
# Environment:
#   DATA_DIR=$HOME/container-data/mysql  # legacy: .apple_container/mysql_data
#   CONTAINER_NAME=mythras-mysql

if command -v container >/dev/null 2>&1; then
  CONTAINER_CLI=container
else
  echo "Error: 'container' is required in PATH (https://github.com/apple/container/releases)." >&2
  exit 1
fi

CONTAINER_NAME=${CONTAINER_NAME:-mythras-mysql}
# Previously: DATA_DIR defaulted to .apple_container/mysql_data
DATA_DIR=${DATA_DIR:-$HOME/container-data/mysql}
REMOVE_VOLUMES=0

if [[ ${1:-} == "--volumes" ]]; then
  REMOVE_VOLUMES=1
fi

if $CONTAINER_CLI inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  state=$($CONTAINER_CLI inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo unknown)
  if [[ "$state" == "running" ]]; then
    echo "Killing container ${CONTAINER_NAME}..."
    $CONTAINER_CLI kill "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
  echo "Removing container ${CONTAINER_NAME}..."
  $CONTAINER_CLI rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
  # Double-check removal: if still present, try force remove once more
  if $CONTAINER_CLI inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "Container still present; retrying force removal..."
    $CONTAINER_CLI kill "$CONTAINER_NAME" >/dev/null 2>&1 || true
    $CONTAINER_CLI rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
else
  echo "Container ${CONTAINER_NAME} not found; nothing to stop."
fi

if [[ $REMOVE_VOLUMES -eq 1 ]]; then
  echo "Removing data directory ${DATA_DIR} (data loss!)"
  rm -rf "$DATA_DIR"
fi

echo "Done."
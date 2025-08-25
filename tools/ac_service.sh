#!/usr/bin/env bash
set -euo pipefail

# Apple container system service helper
# - Verifies Apple 'container' CLI exists
# - Checks if the container system service is running
# - Starts it if needed via `container system start`
# - Prints concise diagnostics and exit status
#
# Usage:
#   ./tools/ac_service.sh           # start if needed
#   ./tools/ac_service.sh status    # only check status
#   ./tools/ac_service.sh start     # force a start attempt
#
# Common error it remedies:
#   Error: interrupted: "XPC connection error: Connection invalid"
# This usually means the Apple container system service is not started.

command -v container >/dev/null 2>&1 || {
  echo "[ac_service] Error: Apple 'container' CLI not found in PATH." >&2
  echo "[ac_service] Install from: https://github.com/apple/container/releases" >&2
  exit 127
}

mode=${1:-auto}

check_status() {
  # Avoid 'container system info'; use 'container list' as a proxy health check.
  if container list >/dev/null 2>&1; then
    echo "[ac_service] Apple container system service: running"
    return 0
  else
    echo "[ac_service] Apple container system service: not running"
    return 1
  fi
}

start_service() {
  echo "[ac_service] Attempting to start Apple container system service..."
  if container system start >/dev/null 2>&1; then
    echo "[ac_service] Start command issued. Verifying..."
  else
    echo "[ac_service] Warning: 'container system start' returned a non-zero status; will verify status anyway." >&2
  fi
  # Re-check
  if check_status; then
    return 0
  fi
  echo "[ac_service] Error: Failed to start the Apple container system service." >&2
  echo "[ac_service] Hints:" >&2
  echo "  - Ensure you installed the latest 'container' CLI and rebooted recently if required." >&2
  echo "  - Try running again, or consult 'container system logs' for details." >&2
  exit 1
}

case "$mode" in
  status)
    check_status || exit 1
    ;;
  start)
    start_service
    ;;
  auto)
    if check_status; then
      exit 0
    fi
    start_service
    ;;
  *)
    echo "Usage: $0 [auto|status|start]" >&2
    exit 2
    ;;
esac

import shutil
import pytest

from .conftest import run


@pytest.mark.infra
@pytest.mark.live_db
def test_mysql_service_running(has_container_cli, ensure_apple_run_started):
    """
    Verify that the MySQL container 'mythras-mysql' is running.

    Strategy:
      - Use the Apple 'container' CLI only (no Docker fallback).
      - Attempt a harmless 'exec true' inside the container; if it returns 0, it's running.
      - On failure, include recent logs to aid troubleshooting.
    """
    if not has_container_cli:
        pytest.skip("Apple 'container' CLI not present on this system (no Docker fallback in tests)")

    cli = 'container' if shutil.which('container') else None
    assert cli, "Apple 'container' CLI is required for these tests (no Docker fallback)"

    name = 'mythras-mysql'

    try:
        # Apple container: if container is not running, exec will fail
        code, _out, _err = run([cli, 'exec', name, 'sh', '-c', 'true'])
        running = (code == 0)
    except Exception as e:
        pytest.fail(f"Error checking container state: {e}")

    if not running:
        # Include container list and recent logs for context
        try:
            _c, clist, _e = run([cli, 'list', '--all'])
            clist_tail = '\n'.join((clist or '').splitlines()[-5:])
        except Exception:
            clist_tail = '(no container list available)'
        try:
            code, logs, err = run([cli, 'logs', name])
            tail = '\n'.join((logs or err or '').splitlines()[-50:])
        except Exception:
            tail = '(no logs available)'
        pytest.fail(
            "MySQL service is not running in container 'mythras-mysql'.\n"
            "Hint: run 'make apple-run' (Apple container) or your DB start target first.\n"
            f"Container list (tail):\n{clist_tail}\n"
            f"Recent logs (tail):\n{tail}"
        )

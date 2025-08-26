import pytest

from .conftest import run


@pytest.mark.infra
@pytest.mark.live_db
def test_mysql_service_running_docker(has_docker_cli, ensure_docker_run_started):
    """
    Verify that the MySQL docker container 'mythras-mysql' is running.
    """
    if not has_docker_cli:
        pytest.skip("docker CLI not present on this system")

    name = 'mythras-mysql'

    code, _out, _err = run(['docker', 'exec', name, 'sh', '-c', 'true'])
    running = (code == 0)

    if not running:
        # Include docker ps and recent logs for context
        try:
            _c, clist, _e = run(['docker', 'ps', '-a'])
            clist_tail = '\n'.join((clist or '').splitlines()[-5:])
        except Exception:
            clist_tail = '(no docker ps available)'
        try:
            code, logs, err = run(['docker', 'logs', name])
            tail = '\n'.join((logs or err or '').splitlines()[-50:])
        except Exception:
            tail = '(no logs available)'
        pytest.fail(
            "MySQL service is not running in docker container 'mythras-mysql'.\n"
            "Hint: run 'make -f infra-docker/Makefile start-db' first.\n"
            f"docker ps -a (tail):\n{clist_tail}\n"
            f"Recent logs (tail):\n{tail}"
        )

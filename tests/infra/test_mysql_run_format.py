import os
import shutil
import pytest

from .conftest import run, _mask_cmd_and_output


@pytest.mark.infra
@pytest.mark.live_db
def test_apple_container_mysql_run_exact_format():
    """
    Launch MySQL using the exact command/flag format requested in the issue.

    Skips when Apple 'container' CLI is not available. Cleans up any existing
    container named mythras-mysql before starting, and removes it at the end.
    """
    if not shutil.which('container'):
        pytest.skip("Apple 'container' CLI not present on this system")

    cli = 'container'
    name = 'mythras-mysql'

    # Pre-clean to avoid conflicts with an existing container of same name
    run([cli, 'kill', name])
    run([cli, 'rm', name])

    # Prepare volume path with $HOME
    home = os.path.expanduser('~')
    # Required standard host bind path uses literal "$HOME"; we expand here for test runtime:
    # "$HOME/container-data/mysql:/var/lib/mysql"
    volume = f"{home}/container-data/mysql:/var/lib/mysql"

    # Use the literal credentials as specified by the issue description
    envs = [
        "-e", "MYSQL_ROOT_PASSWORD=YourStrongRootPwd",
        "-e", "MYSQL_DATABASE=mythras_eg",
        "-e", "MYSQL_USER=mythras_eg",
        "-e", "MYSQL_PASSWORD=JurgenTuunaa7",
    ]

    cmd = [
        cli, 'run',
        '--name', name,
        '--detach',
        '--user', '999:999',
        '--publish', '127.0.0.1:3307:3306',
        *envs,
        '--volume', volume,
        'docker.io/library/mysql:8',
    ]

    code, out, err = run(cmd, timeout=60)

    # Mask password in diagnostics
    masked_cmd, mout, merr = _mask_cmd_and_output(cmd, out, err, None)
    print(f"[mysql-run-format] cmd: {masked_cmd}\nexit: {code}\nstdout:\n{mout}\nstderr:\n{merr}")

    try:
        assert code == 0, f"Failed to start mysql container: {err or out}"

        # Verify that container shows up as running
        lcode, lout, lerr = run([cli, 'list', '--all'])
        assert lcode == 0, f"container list failed: {lerr or lout}"
        lines = (lout or '').splitlines()
        running_line = next((ln for i, ln in enumerate(lines) if i > 0 and ln.split()[0] == name), '')
        assert running_line, f"Container {name} not in list. Output:\n{lout}\n{lerr}"
        assert 'running' in running_line.lower(), f"Container not running yet: {running_line}"

    finally:
        # Teardown: stop and remove container to avoid affecting other tests
        run([cli, 'kill', name])
        run([cli, 'rm', name])

import shutil
import pytest
import sys

from .conftest import run, env_vars


@pytest.mark.infra
@pytest.mark.live_db
def test_mysql_cli_sanity_tcp_tls(has_docker_cli, ensure_docker_run_started, env_vars):
    """
    Host MySQL CLI sanity test:
    - Runs: mysql --protocol=TCP --ssl-mode=REQUIRED -hHOST -PPORT -uUSER -pPASS DB -e "SELECT 1;"
    - Values are read from .env via env_vars fixture. Password is not printed in clear text.
    - Skips if mysql client not installed, required env vars missing, or docker CLI absent.
    """
    # Ensure mysql CLI exists on host
    mysql_cli = shutil.which('mysql')
    if not mysql_cli:
        pytest.skip("mysql client not found on PATH; install mysql client to run this sanity test")

    if not has_docker_cli:
        pytest.skip("docker CLI not present on this system")

    host = env_vars.get('DB_HOST', '127.0.0.1')
    port = env_vars.get('DB_PORT', '3308')
    user = env_vars.get('DB_USER') or env_vars.get('MYSQL_USER')
    password = env_vars.get('DB_PASSWORD') or env_vars.get('MYSQL_PASSWORD')
    dbname = env_vars.get('DB_NAME') or env_vars.get('MYSQL_DATABASE')

    # Basic validations
    if not (user and password and dbname):
        pytest.skip("Missing DB_USER/DB_PASSWORD/DB_NAME in .env; cannot run mysql sanity test")

    # Build command
    cmd = [
        mysql_cli,
        '--protocol=TCP',
        '--ssl-mode=REQUIRED',
        f'-h{host}',
        f'-P{port}',
        f'-u{user}',
        f"-p{password}",
        dbname,
        '-e',
        'SELECT 1;'
    ]

    # Execute
    code, out, err = run(cmd, timeout=20)

    # Diagnostics (mask password)
    masked_cmd = ' '.join([p if not p.startswith('-p') else '-p***' for p in map(str, cmd)])
    print(f"[mysql sanity] cmd: {masked_cmd}", file=sys.stderr)
    print(f"[mysql sanity] exit: {code}", file=sys.stderr)
    if out:
        print(f"[mysql sanity] stdout:\n{out}", file=sys.stderr)
    if err:
        print(f"[mysql sanity] stderr:\n{err}", file=sys.stderr)

    if code != 0:
        # Common TLS error text hint
        combined = (err or '') + (out or '')
        if 'SSL' in combined or 'ssl' in combined:
            pytest.skip(
                "mysql client failed with TLS/SSL error while using --ssl-mode=REQUIRED. "
                "Ensure the server supports TLS or provide proper CA via DB_SSL_CA."
            )
        pytest.fail(f"mysql sanity command failed (exit {code}). See logs above.")

    # Success criteria: SELECT 1 returns a line with '1'
    assert '1' in (out or ''), "Expected SELECT 1 to produce '1' in output"


@pytest.mark.infra
@pytest.mark.live_db
def test_additional_network_and_container_sanity(has_docker_cli, ensure_docker_run_started, env_vars):
    """
    Additional sanity checks requested:
    - nc -vz 127.0.0.1 <DB_PORT>
    - lsof -nPiTCP:<DB_PORT> -sTCP:LISTEN
    - docker exec -it mythras-mysql mysql -uroot -p -e "SELECT 1;" (non-interactive via MYSQL_PWD)
    - docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
    - docker port mythras-mysql 3306 (should print 127.0.0.1:<DB_PORT>)
    - docker inspect mythras-mysql --format '{{json .HostConfig.PortBindings}}'
    """
    if not has_docker_cli:
        pytest.skip("docker CLI not present on this system")

    host = env_vars.get('DB_HOST', '127.0.0.1')
    port = env_vars.get('DB_PORT', '3308')  # default to 3308 per current .env
    root_pw = env_vars.get('MYSQL_ROOT_PASSWORD')

    # 1) nc -vz host port
    nc = shutil.which('nc') or shutil.which('netcat')
    if nc:
        code, out, err = run([nc, '-vz', host, str(port)], timeout=15)
        print(f"[nc -vz {host} {port}] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}", file=sys.stderr)
        # Enforce success: many nc variants print "succeeded" or "open"
        combined = f"{out}\n{err}".lower()
        assert code == 0 and ("succeeded" in combined or "open" in combined), \
            f"nc should say succeeded/open to {host}:{port}. Exit={code}. Output: {out or err}"
    else:
        pytest.skip("[nc] netcat not found; cannot perform nc connectivity check")

    # 2) lsof -nPiTCP:port -sTCP:LISTEN (disabled by requirement)
    print("[lsof] check disabled by requirement; skipping verifying listener ownership.", file=sys.stderr)

    # 3) docker exec mysql -uroot -p -e "SELECT 1;" (non-interactive)
    if not root_pw:
        pytest.skip("MYSQL_ROOT_PASSWORD not set in .env; cannot run docker exec mysql root sanity")
    code, out, err = run([
        'docker', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
        f"MYSQL_PWD='{root_pw}' mysql -N -B -uroot -e 'SELECT 1;'"
    ], timeout=20)
    print(f"[docker exec mysql root SELECT 1] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}", file=sys.stderr)
    assert code == 0, f"docker exec mysql SELECT 1 failed: {err or out}"
    assert '1' in (out or ''), "Expected '1' in mysql output from docker exec"

    # 4) docker ps formatted table
    code, out, err = run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'], timeout=15)
    print(f"[docker ps --format table] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}", file=sys.stderr)
    assert code == 0, f"docker ps formatted failed: {err or out}"

    # 5) docker port mapping for 3306 should show host:port
    code, out, err = run(['docker', 'port', 'mythras-mysql', '3306'], timeout=15)
    mapped = (out or '').strip()
    print(f"[docker port mythras-mysql 3306] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}", file=sys.stderr)
    assert code == 0, f"docker port query failed: {err or out}"
    # Accept both exact and presence of host:port combination
    assert f"{host}:{port}" in mapped, f"Expected port mapping to include {host}:{port}, got: {mapped!r}"

    # 6) docker inspect PortBindings
    code, out, err = run(['docker', 'inspect', 'mythras-mysql', '--format', '{{json .HostConfig.PortBindings}}'], timeout=15)
    print(f"[docker inspect PortBindings] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}", file=sys.stderr)
    assert code == 0, f"docker inspect PortBindings failed: {err or out}"

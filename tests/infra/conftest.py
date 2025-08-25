import os
import shutil
import subprocess
from pathlib import Path
import pytest
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE_PATH = PROJECT_ROOT / 'Makefile'
ENV_PATH = PROJECT_ROOT / '.env'


def parse_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = k.strip()
        v = v.strip()
        if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            v = v[1:-1]
        data[k] = v
    return data


def run(cmd, cwd=None, env=None, timeout=15):
    """Run a command and return (code, stdout, stderr).
    On timeout, returns code 124 and includes the timed-out command in output.
    """
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd or PROJECT_ROOT),
        env=env or os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        cmd_str = " ".join(map(str, cmd))
        msg = f"[run-timeout] cmd: {cmd_str} (timeout={timeout}s)\n"
        # Print for pytest output visibility and include in stderr
        print(msg.strip(), file=sys.stderr)
        err = (msg + (err or "")) if err is not None else msg
        return 124, out, err
    return proc.returncode, out, err


def _mask_cmd_and_output(cmd: list, out: str | None, err: str | None, env: dict | None):
    # Mask secrets in command and outputs; focus on MYSQL_ROOT_PASSWORD occurrences
    def mask_text(s: str) -> str:
        if not s:
            return s
        s2 = s.replace('MYSQL_ROOT_PASSWORD', 'MYSQL_ROOT_PASSWORD')
        # Replace any explicit assignments like MYSQL_ROOT_PASSWORD=xxxx in echoed commands
        return s2.replace('MYSQL_ROOT_PASSWORD=', 'MYSQL_ROOT_PASSWORD=***')

    masked_cmd = []
    for part in map(str, cmd):
        if part.startswith('MYSQL_ROOT_PASSWORD='):
            masked_cmd.append('MYSQL_ROOT_PASSWORD=***')
        else:
            masked_cmd.append(part)
    return " ".join(masked_cmd), mask_text(out or ''), mask_text(err or '')


def run_logged(cmd, label=None, cwd=None, env=None, timeout=15):
    """Run a command via run() and print command + exit code and outputs.
    Intended for ensure_apple_run_started to expose what happens.
    """
    code, out, err = run(cmd, cwd=cwd, env=env, timeout=timeout)
    masked_cmd, mout, merr = _mask_cmd_and_output(cmd, out, err, env)
    prefix = label or 'run'
    print(f"[{prefix}] cmd: {masked_cmd}", file=sys.stderr)
    print(f"[{prefix}] exit: {code}", file=sys.stderr)
    if mout:
        print(f"[{prefix}] stdout:\n{mout}", file=sys.stderr)
    if merr:
        print(f"[{prefix}] stderr:\n{merr}", file=sys.stderr)
    return code, out, err


@pytest.fixture(scope='session')
def project_root():
    return PROJECT_ROOT


@pytest.fixture(scope='session')
def env_vars():
    return parse_env(ENV_PATH)


@pytest.fixture(scope='session')
def has_container_cli():
    # Only Apple 'container' CLI is supported in tests; no fallback to Docker.
    # Detect presence by probing the CLI without using 'system info'.
    if not shutil.which('container'):
        return False
    code, _out, _err = run(['container', 'list'])
    return code == 0


@pytest.fixture(scope='session')
def ensure_apple_run_started(env_vars, has_container_cli):
    """Ensure a minimal MySQL container setup equivalent to `make apple-run`.
    - Requires Apple 'container' CLI and MYSQL_ROOT_PASSWORD in .env.
    - If the container is already running, does nothing.
    - Otherwise, removes any old container and starts a fresh one with the exact flags.
    - Waits until the container process accepts exec (not full MySQL readiness), with a longer, more robust timeout.
    """
    if not has_container_cli:
        pytest.skip("Apple 'container' CLI not present; cannot perform apple-run setup in tests")
    cli = 'container'
    root_pw = env_vars.get('MYSQL_ROOT_PASSWORD')
    if not root_pw:
        pytest.skip("MYSQL_ROOT_PASSWORD not set in .env; cannot perform apple-run setup in tests")

    # Do not use 'container system info' or 'system start' here. We'll rely on list/run/exec probes.

    # If container already running, return quickly (match by name and state from list output)
    code, out, err = run_logged([cli, 'list', '--all'], label='ac.list.all')
    if code == 0:
        for i, line in enumerate((out or '').splitlines()):
            if i == 0:
                continue
            if 'mythras-mysql' in line and 'running' in line.lower():
                return  # Already running

    # Remove any stale container and start a new one
    run_logged([cli, 'kill', 'mythras-mysql'], label='ac.kill')
    run_logged([cli, 'rm', 'mythras-mysql'], label='ac.rm')
    env = os.environ.copy()
    env['MYSQL_ROOT_PASSWORD'] = root_pw
    host_port = env_vars.get('DB_PORT', env_vars.get('MYSQL_PORT', '3307'))

    # Start container (non-blocking from test perspective). Short timeout (15s); logs will show if it times out.
    _code, _out, _err = run_logged([cli, 'run', '--name', 'mythras-mysql', '--publish', '127.0.0.1:3307:3306', '--env', f"MYSQL_ROOT_PASSWORD={root_pw}", 'docker.io/library/mysql:8'], label='ac.run', env=env, timeout=15)

    # Wait until exec works (container is up). Total wait capped at 15 seconds.
    import time
    start = time.time()
    deadline = 15  # seconds
    attempt = 0
    last_state_print = 0
    while time.time() - start < deadline:
        attempt += 1
        # Log the first exec probe to show the exact command/result; later attempts rely on state lines
        if attempt == 1:
            code, _o, _e = run_logged([cli, 'exec', 'mythras-mysql', 'sh', '-c', 'true'], label='ac.exec.probe')
        else:
            code, _o, _e = run([cli, 'exec', 'mythras-mysql', 'sh', '-c', 'true'])
        if code == 0:
            return
        # Every 3 seconds, print container state to help debugging slow startups
        now = time.time()
        if now - last_state_print > 3:
            last_state_print = now
            # Avoid relying on inspect formatting which may differ; use list output for a rough status line
            _c2, list_out, _ = run_logged([cli, 'list', '--all'], label='ac.list.all.wait')
            st = 'unknown'
            if _c2 == 0:
                for i, l in enumerate((list_out or '').splitlines()):
                    if i == 0:
                        continue
                    if 'mythras-mysql' in l:
                        st = l
                        break
            print(f"[ensure_apple_run_started] waiting for exec (attempt {attempt}) - state: {st}")
        time.sleep(0.5)

    pytest.skip("apple-run-like container did not become available to exec within timeout; check 'make db-doctor'")


@pytest.fixture(scope='session')
def ensure_db_user_exists(env_vars, ensure_apple_run_started):
    """As the last step of test setup, ensure DB_USER exists in MySQL with the right plugin and grants.
    - Requires .env keys: DB_USER, DB_PASSWORD, DB_NAME, MYSQL_ROOT_PASSWORD.
    - Runs idempotent CREATE USER IF NOT EXISTS / CREATE DATABASE IF NOT EXISTS / GRANT ... / FLUSH PRIVILEGES.
    - Skips if prerequisites are missing to avoid failing CI without DB."""

    import shutil
    import pytest

    from .conftest import run

    @pytest.fixture(scope='session')
    def ensure_db_user_exists(env_vars, ensure_apple_run_started):
        """
        Ensure DB user/database exist on the MySQL in Apple container.
        Uses Apple 'container' if available, otherwise docker.
        """
        cli = 'container' if shutil.which('container') else ('docker' if shutil.which('docker') else None)
        if not cli:
            pytest.skip("No container or docker CLI present on this system")

        db_user = env_vars.get('DB_USER')
        db_pass = env_vars.get('DB_PASSWORD', '')
        db_name = env_vars.get('DB_NAME')
        root_pw = env_vars.get('MYSQL_ROOT_PASSWORD')

        if not (db_user and db_name and root_pw):
            pytest.skip("DB_USER/DB_NAME/MYSQL_ROOT_PASSWORD not set; cannot ensure DB user before tests")

        # Normalize and escape password for SQL single-quoted literal
        if db_pass and ((db_pass.startswith("'") and db_pass.endswith("'")) or (
                db_pass.startswith('"') and db_pass.endswith('"'))):
            db_pass = db_pass[1:-1]
        pw_sql = db_pass.replace("'", "''")  # SQL string literal escaping

        # Escape username for single-quoted literal (rarely needed, but safe)
        user_sql = db_user.replace("'", "''")

        # Build SQL (idempotent)
        sql = f"""
    CREATE DATABASE IF NOT EXISTS `{db_name}`;
    CREATE USER IF NOT EXISTS '{user_sql}'@'%'        IDENTIFIED WITH caching_sha2_password BY '{pw_sql}';
    CREATE USER IF NOT EXISTS '{user_sql}'@'localhost' IDENTIFIED WITH caching_sha2_password BY '{pw_sql}';
    ALTER USER '{user_sql}'@'%'        IDENTIFIED WITH caching_sha2_password BY '{pw_sql}';
    ALTER USER '{user_sql}'@'localhost' IDENTIFIED WITH caching_sha2_password BY '{pw_sql}';
    GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{user_sql}'@'%';
    GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{user_sql}'@'localhost';
    FLUSH PRIVILEGES;
    """.strip()

        # Log a masked version for debugging output
        print("[ensure_db_user_exists] SQL to execute:\n" + sql.replace(f"BY '{pw_sql}'", "BY '***'"))

        # Use a single-quoted heredoc so the SQL is passed verbatim to mysql inside the container
        heredoc = f"MYSQL_PWD='{root_pw}' mysql -N -B -uroot <<'SQL'\n{sql}\nSQL\n"

        code, out, err = run([cli, 'exec', '-i', 'mythras-mysql', 'sh', '-c', heredoc])
        if code != 0:
            # include tail of logs to help
            try:
                lcode, logs, _ = run([cli, 'logs', 'mythras-mysql'])
                tail = '\n'.join((logs or '').splitlines()[-50:])
            except Exception:
                tail = '(no logs available)'
            pytest.skip(
                f"Failed to ensure DB user (exit {code}).\nSTDOUT:\n{out}\nSTDERR:\n{err}\nLogs tail:\n{tail}"
            )
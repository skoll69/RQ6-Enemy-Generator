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
    Intended for ensure_docker_run_started to expose what happens.
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
def has_docker_cli():
    if not shutil.which('docker'):
        return False
    code, _out, _err = run(['docker', 'ps'])
    return code == 0


@pytest.fixture(scope='session')
def ensure_docker_run_started(env_vars, has_docker_cli):
    """Ensure a minimal MySQL container is running using docker.
    - Requires docker CLI and MYSQL_ROOT_PASSWORD in .env.
    - Removes any old container named mythras-mysql and starts a fresh one.
    - Waits until docker exec works (container up), with a capped timeout.
    """
    if not has_docker_cli:
        pytest.skip("docker CLI not present; cannot perform docker-run setup in tests")

    cli = 'docker'
    name = 'mythras-mysql'
    root_pw = env_vars.get('MYSQL_ROOT_PASSWORD')
    if not root_pw:
        pytest.skip("MYSQL_ROOT_PASSWORD not set in .env; cannot perform docker-run setup in tests")

    # Pre-clean
    run_logged([cli, 'rm', '-f', name], label='docker.rm')

    # Start detached
    env = os.environ.copy()
    env['MYSQL_ROOT_PASSWORD'] = root_pw
    _code, _out, _err = run_logged([
        cli, 'run', '--name', name,
        '-p', '127.0.0.1:3308:3306',
        '-e', f"MYSQL_ROOT_PASSWORD={root_pw}",
        '-d', 'docker.io/library/mysql:8'
    ], label='docker.run', env=env, timeout=30)

    # Wait until MySQL responds: first docker exec works, then mysqladmin ping or simple query
    import time
    start = time.time()
    deadline = 60
    # Step 1: wait for exec true
    while time.time() - start < deadline:
        code, _o, _e = run([cli, 'exec', name, 'sh', '-c', 'true'])
        if code == 0:
            break
        time.sleep(0.5)
    else:
        pytest.skip("docker-run container did not become available to exec within timeout")

    # Step 2: wait for mysql readiness
    start2 = time.time()
    while time.time() - start2 < 60:
        # Try mysqladmin ping, then fallback to SELECT 1
        code, _o, _e = run([cli, 'exec', name, 'sh', '-c', f"MYSQL_PWD='{root_pw}' mysqladmin ping -uroot --silent"], timeout=5)
        if code == 0:
            return
        code2, _o2, _e2 = run([cli, 'exec', name, 'sh', '-c', f"MYSQL_PWD='{root_pw}' mysql -N -B -uroot -e 'SELECT 1'"], timeout=5)
        if code2 == 0:
            return
        time.sleep(1)

    # If not ready, still proceed but tests may skip; provide diagnostics hint
    print("[ensure_docker_run_started] MySQL did not report ready within 60s; continuing.", file=sys.stderr)
    return


@pytest.fixture(scope='session')
def ensure_db_user_exists(env_vars, ensure_docker_run_started):
    """Ensure DB user/database exist in the running MySQL docker container before any tests."""
    import time

    cli = 'docker'

    db_user = env_vars.get('DB_USER')
    db_pass = env_vars.get('DB_PASSWORD', '')
    db_name = env_vars.get('DB_NAME')
    root_pw = env_vars.get('MYSQL_ROOT_PASSWORD')

    print(f"[ensure_db_user_exists] {time.strftime('%Y-%m-%d %H:%M:%S')} starting...", file=sys.stderr)
    print(f"[ensure_db_user_exists] CLI: {cli}", file=sys.stderr)
    print(f"[ensure_db_user_exists] env: DB_USER={'<set>' if db_user else '<missing>'}, DB_NAME={'<set>' if db_name else '<missing>'}, MYSQL_ROOT_PASSWORD={'<set>' if root_pw else '<missing>'}", file=sys.stderr)

    if not (db_user and db_name and root_pw):
        pytest.skip("DB_USER/DB_NAME/MYSQL_ROOT_PASSWORD not set; cannot ensure DB user before tests")

    # Normalize and escape password for SQL single-quoted literal
    if db_pass and ((db_pass.startswith("'") and db_pass.endswith("'")) or (db_pass.startswith('"') and db_pass.endswith('"'))):
        db_pass = db_pass[1:-1]
    pw_sql = db_pass.replace("'", "''")  # SQL string literal escaping
    user_sql = db_user.replace("'", "''")

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

    masked_sql = sql.replace(f"BY '{pw_sql}'", "BY '***'")
    print("[ensure_db_user_exists] SQL to execute (masked):\n" + masked_sql, file=sys.stderr)

    heredoc = f"MYSQL_PWD='{root_pw}' mysql -N -B -uroot <<'SQL'\n{sql}\nSQL\n"

    print(f"[ensure_db_user_exists] exec: {cli} exec -i mythras-mysql sh -c '<heredoc-sql>'", file=sys.stderr)
    code, out, err = run([cli, 'exec', '-i', 'mythras-mysql', 'sh', '-c', heredoc])
    print(f"[ensure_db_user_exists] exit={code}", file=sys.stderr)
    if out:
        print(f"[ensure_db_user_exists] stdout:\n{out}", file=sys.stderr)
    if err:
        print(f"[ensure_db_user_exists] stderr:\n{err}", file=sys.stderr)

    if code != 0:
        try:
            _c1, clist, _e1 = run([cli, 'ps', '-a'])
            clist_tail = '\n'.join((clist or '').splitlines()[-5:])
        except Exception:
            clist_tail = '(no docker ps available)'
        try:
            _c2, logs, _e2 = run([cli, 'logs', 'mythras-mysql'])
            logs_tail = '\n'.join((logs or '').splitlines()[-50:])
        except Exception:
            logs_tail = '(no logs available)'
        pytest.skip(
            "Failed to ensure DB user before docker tests.\n" +
            f"Exit: {code}\nSTDOUT:\n{out}\nSTDERR:\n{err}\n" +
            f"docker ps -a (tail):\n{clist_tail}\nLogs (tail):\n{logs_tail}"
        )

    print("[ensure_db_user_exists] completed successfully.", file=sys.stderr)


@pytest.fixture(scope='session', autouse=True)
def _autouse_run_db_user_setup(ensure_db_user_exists):
    print("[autouse] ensured DB user setup (docker) has been invoked.", file=sys.stderr)
    return None


# --- Auto-upload dump before tests (if present) ---
@pytest.fixture(scope='session')
def ensure_dump_uploaded(env_vars, ensure_db_user_exists, has_docker_cli):
    import time

    if not has_docker_cli:
        print("[ensure_dump_uploaded] docker CLI not present; skipping dump upload.", file=sys.stderr)
        return

    project_root = PROJECT_ROOT
    dump_path = project_root / 'dump.sql'
    if not dump_path.exists():
        print(f"[ensure_dump_uploaded] {dump_path} not found; skipping dump upload.", file=sys.stderr)
        return

    db_name = env_vars.get('DB_NAME')
    root_pw = env_vars.get('MYSQL_ROOT_PASSWORD')
    if not (db_name and root_pw):
        print("[ensure_dump_uploaded] DB_NAME/MYSQL_ROOT_PASSWORD not set in .env; skipping dump upload.", file=sys.stderr)
        return

    # Normalize quotes in root_pw if user left them in .env
    if root_pw and ((root_pw.startswith("'") and root_pw.endswith("'")) or (root_pw.startswith('"') and root_pw.endswith('"'))):
        root_pw = root_pw[1:-1]

    print(f"[ensure_dump_uploaded] {time.strftime('%Y-%m-%d %H:%M:%S')} starting dump upload (docker)...", file=sys.stderr)
    print(f"[ensure_dump_uploaded] dump file: {dump_path}", file=sys.stderr)

    # Execute Makefile target with -f (root Makefile)
    code, out, err = run(['make', '-f', str(MAKEFILE_PATH), 'upload-dump-compat', f'ARGS=--db {db_name}'], timeout=600)
    print(f"[ensure_dump_uploaded] make -f Makefile upload-dump-compat exit={code}", file=sys.stderr)
    if out:
        print(f"[ensure_dump_uploaded] stdout:\n{out}", file=sys.stderr)
    if err:
        print(f"[ensure_dump_uploaded] stderr:\n{err}", file=sys.stderr)

    if code != 0:
        print("[ensure_dump_uploaded] Warning: upload-dump-compat failed; tests may skip if data not present.", file=sys.stderr)
        return

    # Quick verification: show table count (non-fatal)
    vcode, vout, verr = run([
        'docker', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
        f"MYSQL_PWD='{root_pw}' mysql -N -B -uroot {db_name} -e 'SHOW TABLES;'"
    ], timeout=60)
    if vcode == 0:
        tables = (vout or '').strip().splitlines() if vout else []
        print(f"[ensure_dump_uploaded] Verification: {len(tables)} tables in {db_name}.", file=sys.stderr)
        if tables:
            preview = "\n".join(tables[:25])
            print(f"[ensure_dump_uploaded] Tables (first 25):\n{preview}", file=sys.stderr)
    else:
        print(f"[ensure_dump_uploaded] Verification SHOW TABLES failed: {(verr or '').strip()}", file=sys.stderr)

    print("[ensure_dump_uploaded] dump upload completed.", file=sys.stderr)


@pytest.fixture(scope='session', autouse=True)
def _autouse_upload_dump(ensure_dump_uploaded):
    print("[autouse] ensured dump upload setup (docker) has been invoked.", file=sys.stderr)
    return None


# --- Generate statistics after dump upload, before tests ---
@pytest.fixture(scope='session')
def ensure_stats_generated(env_vars, ensure_dump_uploaded, has_docker_cli):
    import time

    if not has_docker_cli:
        print("[ensure_stats_generated] docker CLI not present; skipping stats generation.", file=sys.stderr)
        return

    db_name = env_vars.get('DB_NAME')
    root_pw = env_vars.get('MYSQL_ROOT_PASSWORD')
    if not (db_name and root_pw):
        print("[ensure_stats_generated] DB_NAME/MYSQL_ROOT_PASSWORD not set in .env; skipping stats generation.", file=sys.stderr)
        return

    # Normalize quotes for safety
    if root_pw and ((root_pw.startswith("'") and root_pw.endswith("'")) or (root_pw.startswith('"') and root_pw.endswith('"'))):
        root_pw = root_pw[1:-1]

    print(f"[ensure_stats_generated] {time.strftime('%Y-%m-%d %H:%M:%S')} generating stats...", file=sys.stderr)
    # Reuse root Makefile target (generic)
    code, out, err = run(['make', 'generate-stats'], timeout=300)
    print(f"[ensure_stats_generated] make generate-stats exit={code}", file=sys.stderr)
    if out:
        print(f"[ensure_stats_generated] stdout:\n{out}", file=sys.stderr)
    if err:
        print(f"[ensure_stats_generated] stderr:\n{err}", file=sys.stderr)
    if code != 0:
        print("[ensure_stats_generated] Warning: generate-stats failed; continuing without blocking tests.", file=sys.stderr)
        return

    print("[ensure_stats_generated] statistics generated.", file=sys.stderr)


@pytest.fixture(scope='session', autouse=True)
def _autouse_generate_stats(ensure_stats_generated):
    print("[autouse] ensured stats generation (docker) has been invoked.", file=sys.stderr)
    return None

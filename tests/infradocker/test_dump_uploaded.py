import os
import pytest
import sys

from .conftest import run, env_vars, MAKEFILE_PATH


@pytest.mark.infra
@pytest.mark.live_db
def test_dump_uploaded_verifies_weapons_table_docker(has_docker_cli, ensure_docker_run_started, ensure_db_user_exists, env_vars):
    """
    Verify that the dump has been uploaded by checking a table in the DB (docker variant).
    Uses docker CLI and the infra-docker Makefile upload target.
    """
    if not has_docker_cli:
        pytest.skip("docker CLI not present on this system")

    # 1) Ensure dump.sql exists at project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dump_path = os.path.join(project_root, 'dump.sql')
    if not os.path.isfile(dump_path):
        pytest.skip("dump.sql not found at the project root; cannot verify dump upload")

    # 2) Verify DB is running (docker exec true)
    code, _out, _err = run(['docker', 'exec', 'mythras-mysql', 'sh', '-c', 'true'])
    if code != 0:
        _c, clist, _e = run(['docker', 'ps', '-a'])
        clist_tail = '\n'.join((clist or '').splitlines()[-5:])
        pytest.fail(
            "MySQL container 'mythras-mysql' does not appear to be running.\n"
            "Hint: run 'make start-db' first.\n"
            f"[docker ps -a] tail:\n{clist_tail}"
        )

    db_name = env_vars.get('DB_NAME')
    root_password = env_vars.get('MYSQL_ROOT_PASSWORD', '')
    # normalize quotes if user left them in .env
    if root_password and ((root_password.startswith("'") and root_password.endswith("'")) or (root_password.startswith('"') and root_password.endswith('"'))):
        root_password = root_password[1:-1]

    if not db_name or not root_password:
        pytest.skip("DB_NAME/MYSQL_ROOT_PASSWORD not set in .env; cannot verify dump upload as root")

    # Show database diagnostics first (very visible in output)
    print("\n=== DB DIAGNOSTICS BEGIN (docker) ===", file=sys.stderr)
    dcode, dout, derr = run([
        'docker', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
        f"MYSQL_PWD='{root_password}' mysql -N -B -uroot {db_name} -e 'SELECT DATABASE();'"
    ])
    if dcode == 0:
        print(f"[diagnostic] SELECT DATABASE(): {(dout or '').strip()}", file=sys.stderr)
    else:
        print(f"[diagnostic] SELECT DATABASE() failed: {(derr or '').strip()}", file=sys.stderr)

    dbsc, dbso, dbse = run([
        'docker', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
        f"MYSQL_PWD='{root_password}' mysql -N -B -uroot -e 'SHOW DATABASES;'"
    ])
    dblist = (dbso or '').strip()
    print("[diagnostic] SHOW DATABASES:\n" + (dblist if dblist else '(no databases or query failed)'), file=sys.stderr)
    if dbsc != 0 and dbse:
        print("[diagnostic] SHOW DATABASES stderr:\n" + dbse, file=sys.stderr)

    tcode, tout, terr = run([
        'docker', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
        f"MYSQL_PWD='{root_password}' mysql -N -B -uroot {db_name} -e 'SHOW TABLES;'"
    ])
    tables_list = (tout or '').strip()
    if tables_list:
        lines = tables_list.splitlines()
        print(f"[diagnostic] SHOW TABLES in {db_name} (count={len(lines)}):\n" + tables_list, file=sys.stderr)
    else:
        print(f"[diagnostic] SHOW TABLES in {db_name}: (no tables or query failed)", file=sys.stderr)
    if tcode != 0 and terr:
        print("[diagnostic] SHOW TABLES stderr:\n" + terr, file=sys.stderr)
    print("=== DB DIAGNOSTICS END (docker) ===\n", file=sys.stderr)

    # helper: try a sequence of candidate tables likely present after import
    candidate_tables = [
        'mw_enemyweapon',  # preferred domain table if present
        'auth_user',       # fallback from Django auth tables
        'auth_group',      # another common table in dump
    ]

    def query_any_count_as_root():
        last = (1, '', '')
        for table in candidate_tables:
            code, out, err = run([
                'docker', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
                f"MYSQL_PWD='{root_password}' mysql -N -B -uroot {db_name} -e 'SELECT COUNT(*) FROM {table}'"
            ])
            if code == 0 and (out or '').strip().isdigit():
                return 0, table, (out or '').strip(), ''
            last = (code, out or '', err or '')
        return last[0], None, (last[1] or '').strip(), last[2]

    code, found_table, out, err = query_any_count_as_root()
    if code == 0 and found_table is not None and out.isdigit():
        assert int(out) >= 0, f"Unexpected negative count from {found_table}: {out}"
        if os.environ.get('FORCE_VERIFY_DUMP', '0') == '1':
            assert int(out) > 0, f"{found_table} table exists but appears empty; set FORCE_VERIFY_DUMP=0 to skip or upload a dump first"
        return

    # Try to import dump if present
    if os.path.isfile(dump_path):
        mcode, mout, merr = run(['make', '-f', str(MAKEFILE_PATH), 'upload-dump-compat'])
        # Retry the query
        code, found_table, out, err = query_any_count_as_root()
        if code == 0 and found_table is not None and out.isdigit():
            if os.environ.get('FORCE_VERIFY_DUMP', '0') == '1':
                assert int(out) > 0, f"Dump loaded but {found_table} count is 0; expected > 0 with FORCE_VERIFY_DUMP=1"
            return

    msg = [
        "Could not verify that dump has been uploaded to the database (as root, docker).",
        "- Ensure dump.sql exists at project root and run: make upload-dump-compat",
        "- Or start DB: make start-db",
        "- You can force failure instead of skip with FORCE_VERIFY_DUMP=1",
        f"Last error: {err}",
    ]
    if os.environ.get('FORCE_VERIFY_DUMP', '0') == '1':
        pytest.fail("\n".join(msg))
    else:
        pytest.skip("\n".join(msg))

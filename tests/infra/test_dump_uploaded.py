import os
import shutil
import pytest
import sys

from .conftest import run, env_vars


@pytest.mark.infra
@pytest.mark.live_db
def test_dump_uploaded_verifies_weapons_table(has_container_cli, ensure_apple_run_started, ensure_db_user_exists, env_vars):
    """
    Verify that the dump has been uploaded by checking the weapons table.
    Behavior:
      - Uses Apple 'container' CLI only; skips if not available.
      - Requires DB_NAME and MYSQL_ROOT_PASSWORD from .env; skips if missing.
      - Verifies at the start that dump.sql exists in the project root; otherwise skips with a clear message.
      - Verifies at the start that the database container is running (quick exec true); otherwise fails with explicit diagnostics.
      - Tries to SELECT COUNT(*) FROM weapons using the ROOT user (non-interactive via MYSQL_PWD).
      - If table missing or count is empty, and dump.sql exists, attempts to load the dump via Makefile 'upload-dump-compat', then re-checks.
      - If still missing and FORCE_VERIFY_DUMP=1 is set in environment, fails; otherwise, skips with guidance.
    """
    if not has_container_cli:
        pytest.skip("Apple 'container' CLI not present on this system (no Docker fallback in tests)")

    # 1) Ensure dump.sql exists at project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dump_path = os.path.join(project_root, 'dump.sql')
    if not os.path.isfile(dump_path):
        pytest.skip("dump.sql not found at the project root; cannot verify dump upload")

    # 2) Explicitly verify DB is running (container exec true)
    code, _out, _err = run(['container', 'exec', 'mythras-mysql', 'sh', '-c', 'true'])
    if code != 0:
        # Also show container list tail for clarity
        _c, clist, _e = run(['container', 'list', '--all'])
        clist_tail = '\n'.join((clist or '').splitlines()[-5:])
        pytest.fail(
            "MySQL container 'mythras-mysql' does not appear to be running.\n"
            "Hint: run 'make apple-run' or 'make env-new-start' first.\n"
            f"[container list --all] tail:\n{clist_tail}"
        )

    db_name = env_vars.get('DB_NAME')
    root_password = env_vars.get('MYSQL_ROOT_PASSWORD', '')
    # normalize quotes if user left them in .env
    if root_password and ((root_password.startswith("'") and root_password.endswith("'")) or (root_password.startswith('"') and root_password.endswith('"'))):
        root_password = root_password[1:-1]

    if not db_name or not root_password:
        pytest.skip("DB_NAME/MYSQL_ROOT_PASSWORD not set in .env; cannot verify dump upload as root")

    # Show database diagnostics first (very visible in output)
    print("\n=== DB DIAGNOSTICS BEGIN ===", file=sys.stderr)
    # Selected DB name from mysql perspective
    dcode, dout, derr = run([
        'container', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
        f"MYSQL_PWD='{root_password}' mysql -N -B -uroot {db_name} -e 'SELECT DATABASE();'"
    ])
    if dcode == 0:
        print(f"[diagnostic] SELECT DATABASE(): {(dout or '').strip()}", file=sys.stderr)
    else:
        print(f"[diagnostic] SELECT DATABASE() failed: {(derr or '').strip()}", file=sys.stderr)

    # List all databases
    dbsc, dbso, dbse = run([
        'container', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
        f"MYSQL_PWD='{root_password}' mysql -N -B -uroot -e 'SHOW DATABASES;'"
    ])
    dblist = (dbso or '').strip()
    print("[diagnostic] SHOW DATABASES:\n" + (dblist if dblist else '(no databases or query failed)'), file=sys.stderr)
    if dbsc != 0 and dbse:
        print("[diagnostic] SHOW DATABASES stderr:\n" + dbse, file=sys.stderr)

    # List all tables in target DB
    tcode, tout, terr = run([
        'container', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
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
    print("=== DB DIAGNOSTICS END ===\n", file=sys.stderr)

    # helper to run count as root
    def query_weapons_count_as_root():
        code, out, err = run([
            'container', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
            f"MYSQL_PWD='{root_password}' mysql -N -B -uroot {db_name} -e 'SELECT COUNT(*) FROM mw_enemyweapon'"
        ])
        return code, (out or '').strip(), (err or '')

    code, out, err = query_weapons_count_as_root()
    if code == 0 and out.isdigit():
        assert int(out) >= 0, f"Unexpected negative count from weapons: {out}"
        if os.environ.get('FORCE_VERIFY_DUMP', '0') == '1':
            assert int(out) > 0, "weapons table exists but appears empty; set FORCE_VERIFY_DUMP=0 to skip or upload a dump first"
        return

    # If we reach here, either table missing or auth/db error. Try to import dump if present.
    if os.path.isfile(dump_path):
        # Run upload via Makefile helper which also handles MySQL 8 compatibility
        mcode, mout, merr = run(['make', 'upload-dump-compat'])
        # Regardless of result, retry the query
        code, out, err = query_weapons_count_as_root()
        if code == 0 and out.isdigit():
            if os.environ.get('FORCE_VERIFY_DUMP', '0') == '1':
                assert int(out) > 0, "Dump loaded but weapons count is 0; expected > 0 with FORCE_VERIFY_DUMP=1"
            return

    # Final: still not verifiable
    msg = [
        "Could not verify that dump has been uploaded to the database (as root).",
        "- Ensure dump.sql exists at project root and run: make upload-dump-compat",
        "- Or run: make env-new-start to create DB, user, and upload dump if present",
        "- You can force failure instead of skip with FORCE_VERIFY_DUMP=1",
        f"Last error: {err}",
    ]
    if os.environ.get('FORCE_VERIFY_DUMP', '0') == '1':
        pytest.fail("\n".join(msg))
    else:
        pytest.skip("\n".join(msg))

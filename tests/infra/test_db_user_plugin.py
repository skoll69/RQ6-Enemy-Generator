import os
import pytest

from .conftest import run, env_vars


@pytest.mark.infra
@pytest.mark.live_db
def test_db_user_exists_and_plugin_is_caching_sha2(has_container_cli, ensure_apple_run_started, ensure_db_user_exists, env_vars):
    """
    Verify that DB_USER exists in mysql.user and uses the proper authentication plugin for MySQL 8.
    Requirements:
      - Apple 'container' CLI only (no Docker fallback).
      - .env must define DB_USER and MYSQL_ROOT_PASSWORD.
      - We check both '%' and 'localhost' host records. If either exists, the user "exists".
      - We assert the authentication plugin is 'caching_sha2_password'.
    """
    if not has_container_cli:
        pytest.skip("Apple 'container' CLI not present on this system (no Docker fallback in tests)")

    db_user = env_vars.get('DB_USER')
    root_pw = env_vars.get('MYSQL_ROOT_PASSWORD', '')
    if root_pw and ((root_pw.startswith("'") and root_pw.endswith("'")) or (root_pw.startswith('"') and root_pw.endswith('"'))):
        root_pw = root_pw[1:-1]

    if not db_user or not root_pw:
        pytest.skip("DB_USER and/or MYSQL_ROOT_PASSWORD not set in .env; cannot verify user/plugin")

    # Helper to run a root query returning single-line result
    def root_query(sql: str):
        return run(['container', 'exec', '-i', 'mythras-mysql', 'sh', '-c', f"MYSQL_PWD='{root_pw}' mysql -N -B -uroot -e \"{sql}\""])

    # 1) Check existence on '%' and 'localhost'
    user_esc = db_user.replace("'", "\\'")
    sql_exists = (
        "SELECT CONCAT(User,'@',Host) FROM mysql.user "
        f"WHERE User='{user_esc}' AND Host IN ('%','localhost') LIMIT 1;"
    )
    code, out, err = root_query(sql_exists)
    if code != 0:
        pytest.fail(f"Failed to query mysql.user for existence: {err or out}")
    out = (out or '').strip()
    assert out != '', f"DB user '{db_user}' not found in mysql.user for hosts '%' or 'localhost'"

    # 2) Check plugin
    sql_plugin = (
        "SELECT plugin FROM mysql.user "
        f"WHERE User='{user_esc}' AND Host IN ('%','localhost') LIMIT 1;"
    )
    code, out, err = root_query(sql_plugin)
    if code != 0:
        pytest.fail(f"Failed to query mysql.user for plugin: {err or out}")
    plugin = (out or '').strip()
    assert plugin != '', f"Could not determine auth plugin for '{db_user}'"
    # MySQL 8 default plugin
    assert plugin == 'caching_sha2_password', (
        f"DB user '{db_user}' plugin is '{plugin}', expected 'caching_sha2_password'.\n"
        "Hint: run 'make mysql-fix-auth' or 'make mysql-create-user' and retry."
    )

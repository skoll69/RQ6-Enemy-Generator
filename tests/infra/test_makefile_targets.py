import re
from pathlib import Path
import pytest
from .conftest import run, MAKEFILE_PATH

REQUIRED_TARGETS = [
    'start-db', 'env-new-start', 'sql',
    'mysql-shell', 'mysql-shell-root', 'mysql-shell-db', 'mysql-shell-app',
    'upload-dump', 'upload-dump-debug', 'upload-dump-compat', 'upload-dump-compat-debug',
    'mysql-create-user', 'mysql-fix-auth',
    'ps-ac', 'ps-ac-all', 'logs-db', 'logs-db-follow',
    'apple-env-check', 'apple-free-port-3307', 'apple-pre-remove', 'apple-show-cmd', 'apple-run', 'apple-post-check', 'apple-run-minimal',
    'git-repair',
]


@pytest.mark.infra
def test_makefile_exists_and_contains_targets(project_root):
    assert MAKEFILE_PATH.exists(), 'Makefile not found at project root.'
    content = MAKEFILE_PATH.read_text(encoding='utf-8', errors='ignore')
    missing = []
    for t in REQUIRED_TARGETS:
        # Use a conservative pattern to reduce false positives
        pat = re.compile(rf"^\s*{re.escape(t)}\s*:\s*$", re.MULTILINE)
        if not pat.search(content):
            missing.append(t)
    assert not missing, f"Required Make targets missing from Makefile: {missing}"


@pytest.mark.infra
@pytest.mark.parametrize('target', [
    'ps-ac', 'ps-ac-all', 'apple-show-cmd', 'db-doctor', 'git-repair',
])
def test_dry_run_basic_targets(target):
    code, out, err = run(['make', '-n', target])
    assert code == 0, f"make -n {target} failed: {err or out}"
    assert isinstance(out, str)


@pytest.mark.infra
@pytest.mark.parametrize('target, expect_substrings', [
    ('env-new-start', ['container run', 'MYSQL_ROOT_PASSWORD']),
    ('mysql-create-user', ['CREATE USER', 'caching_sha2_password']),
    ('mysql-fix-auth', ['ALTER USER', 'caching_sha2_password']),
    ('sql', ['mysql']),
])
def test_make_dry_run_commands_include_expected_parts(target, expect_substrings):
    code, out, err = run(['make', '-n', target])
    # Some recipes echo via shell; dry-run still should parse without stopping.
    assert code == 0, f"make -n {target} failed to parse: {err or out}"
    combined = (out or '') + (err or '')
    for s in expect_substrings:
        assert s in combined, f"Expected '{s}' to appear in dry-run output of {target}"


@pytest.mark.infra
@pytest.mark.live_db
def test_live_ps_ac_detects_state_if_cli_present(has_container_cli):
    if not has_container_cli:
        pytest.skip("Apple 'container' CLI not present on this system (no Docker fallback in tests)")
    code, out, err = run(['make', 'ps-ac'])
    # This should run and print the list (even if container is not running)
    assert code == 0, f"make ps-ac failed: {err or out}"
    # Echo the tail of the list to test output for visibility
    lines = (out or '').splitlines()
    print("\n[make ps-ac] tail:\n" + "\n".join(lines[-5:] if lines else []))
    assert 'ID' in out

import re
from pathlib import Path
import pytest
from .conftest import run, MAKEFILE_PATH

REQUIRED_TARGETS = [
    'start-db', 'sql',
    'mysql-shell', 'mysql-shell-root', 'mysql-shell-db', 'mysql-shell-app',
    'upload-dump', 'upload-dump-debug', 'upload-dump-compat', 'upload-dump-compat-debug',
    'mysql-create-user', 'mysql-fix-auth',
    'ps-docker', 'logs-db', 'logs-db-follow',
    'git-repair',
]


@pytest.mark.infra
def test_makefile_exists_and_contains_targets(project_root):
    assert MAKEFILE_PATH.exists(), 'infra-docker/Makefile not found.'
    content = MAKEFILE_PATH.read_text(encoding='utf-8', errors='ignore')
    missing = []
    for t in REQUIRED_TARGETS:
        # Use a conservative pattern to reduce false positives
        pat = re.compile(rf"^\s*{re.escape(t)}\s*:\s*$", re.MULTILINE)
        if not pat.search(content):
            missing.append(t)
    assert not missing, f"Required Make targets missing from infra-docker/Makefile: {missing}"


@pytest.mark.infra
@pytest.mark.parametrize('target', [
    'ps-docker', 'git-repair',
])
def test_dry_run_basic_targets(target):
    code, out, err = run(['make', '-n', '-f', str(MAKEFILE_PATH), target])
    assert code == 0, f"make -n -f infra-docker/Makefile {target} failed: {err or out}"
    assert isinstance(out, str)


@pytest.mark.infra
@pytest.mark.parametrize('target, expect_substrings', [
    ('mysql-create-user', ['CREATE USER', 'caching_sha2_password']),
    ('mysql-fix-auth', ['ALTER USER', 'caching_sha2_password']),
    ('sql', ['mysql']),
])

def test_make_dry_run_commands_include_expected_parts(target, expect_substrings):
    code, out, err = run(['make', '-n', '-f', str(MAKEFILE_PATH), target])
    # Some recipes echo via shell; dry-run still should parse without stopping.
    assert code == 0, f"make -n -f infra-docker/Makefile {target} failed to parse: {err or out}"
    combined = (out or '') + (err or '')
    for s in expect_substrings:
        assert s in combined, f"Expected '{s}' to appear in dry-run output of {target}"


@pytest.mark.infra
@pytest.mark.live_db
def test_live_ps_docker_detects_state_if_cli_present(has_docker_cli):
    if not has_docker_cli:
        pytest.skip("docker CLI not present on this system")
    code, out, err = run(['make', '-f', str(MAKEFILE_PATH), 'ps-docker'])
    assert code == 0, f"make -f infra-docker/Makefile ps-docker failed: {err or out}"
    lines = (out or '').splitlines()
    print("\n[make -f infra-docker/Makefile ps-docker] tail:\n" + "\n".join(lines[-5:] if lines else []))
    assert 'CONTAINER' in (out or '').upper() or 'IMAGE' in (out or '').upper()

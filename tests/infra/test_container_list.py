import pytest
from .conftest import run


@pytest.mark.infra
@pytest.mark.live_db
def test_container_list_shows_output(has_container_cli):
    """
    Show the Apple 'container' list output and print the end results to the test output.
    - Skips if Apple container CLI is not present.
    - Asserts the command succeeds and prints the standard header line.
    - Always echoes the final container list (including the last non-header line) to help debugging.
    """
    if not has_container_cli:
        pytest.skip("Apple 'container' CLI not present on this system (no Docker fallback in tests)")

    code, out, err = run(['container', 'list', '--all'])
    assert code == 0, f"'container list --all' failed: {err or out}"
    # Expect a header line like: ID IMAGE OS ARCH STATE ADDR
    lines = (out or '').splitlines()
    header = lines[0] if lines else ''
    assert 'ID' in header and 'STATE' in header, f"Unexpected header from container list: {header!r}"

    # Show the end results (tail) of container list explicitly in test output
    tail_lines = lines[-5:] if len(lines) > 1 else lines
    print("\n[container list --all] tail:\n" + "\n".join(tail_lines))

    # Optionally, ensure our expected container name appears (not mandatory if not created yet)
    # This test's purpose is to show the list; presence of mythras-mysql is validated elsewhere.

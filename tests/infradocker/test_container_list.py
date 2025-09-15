import pytest
from .conftest import run


@pytest.mark.infra
@pytest.mark.live_db
def test_docker_ps_shows_output(has_docker_cli):
    """
    Show the docker 'ps -a' output and print the end results to the test output.
    - Skips if docker CLI is not present.
    - Asserts the command succeeds and that some header-like content is present.
    - Always echoes the final lines for debugging.
    """
    if not has_docker_cli:
        pytest.skip("docker CLI not present on this system")

    code, out, err = run(['docker', 'ps', '-a'])
    assert code == 0, f"'docker ps -a' failed: {err or out}"
    lines = (out or '').splitlines()
    header = lines[0] if lines else ''
    # Docker header often includes columns like CONTAINER ID, IMAGE, COMMAND, STATUS, NAMES
    assert 'CONTAINER' in header.upper() or 'IMAGE' in header.upper(), f"Unexpected header from docker ps: {header!r}"

    tail_lines = lines[-5:] if len(lines) > 1 else lines
    print("\n[docker ps -a] tail:\n" + "\n".join(tail_lines))

import shutil
import pytest

from .conftest import run


@pytest.mark.infra
def test_run_hello_world_container():
    """
    Run a simple container: run --rm docker.io/hello-world
    Strategy:
      - Prefer Apple 'container' CLI if present.
      - Fallback to docker if available.
      - If none present, skip the test.
      - Assert exit code 0 and that output mentions 'Hello from Docker!' (typical message),
        but do not strictly require text match to avoid image variant differences.
    """
    cli = None
    if shutil.which('container'):
        cli = 'container'
    elif shutil.which('docker'):
        cli = 'docker'

    if not cli:
        pytest.skip("No container or docker CLI present on this system")

    # Some CLIs require fully qualified image names; the issue requests docker.io/hello-world
    image = 'docker.io/hello-world'

    code, out, err = run([cli, 'run', '--rm', image], timeout=60)

    # Show stdout/stderr in test output for diagnostics
    print(f"[{cli} run --rm {image}] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}")

    assert code == 0, f"{cli} failed to run hello-world: {err or out}"

    # Try to be flexible about the output message
    combined = (out or '') + '\n' + (err or '')
    assert 'Hello from Docker!' in combined or 'hello-world' in combined.lower()

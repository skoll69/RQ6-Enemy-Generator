import shutil
import pytest

from .conftest import run


@pytest.mark.infra
def test_run_hello_world_docker():
    """
    Run a simple container: docker run --rm docker.io/hello-world
    Skips if docker CLI is not present.
    """
    cli = 'docker' if shutil.which('docker') else None

    if not cli:
        pytest.skip("docker CLI not present on this system")

    image = 'docker.io/hello-world'

    code, out, err = run([cli, 'run', '--rm', image], timeout=60)

    # Show stdout/stderr in test output for diagnostics
    print(f"[{cli} run --rm {image}] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}")

    assert code == 0, f"{cli} failed to run hello-world: {err or out}"

    combined = (out or '') + '\n' + (err or '')
    assert 'Hello from Docker!' in combined or 'hello-world' in combined.lower()

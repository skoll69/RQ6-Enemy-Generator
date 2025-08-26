import pytest

from .conftest import run, _mask_cmd_and_output


@pytest.mark.infra
@pytest.mark.live_db
def test_docker_mysql_run_exact_format():
    """
    Placeholder mirror of Apple test; disabled by requirement.
    """
    pytest.skip("Disabled by requirement: skip running test_mysql_run_format (docker)")

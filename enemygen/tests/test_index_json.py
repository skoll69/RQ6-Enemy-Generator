import json
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="session")
def load_data_for_index_json(django_db_setup, django_db_blocker):
    """Reuse the same baseline data loading strategy as other web tests.
    Idempotent and safe on shared DBs.
    """
    import os
    from enemygen.models import EnemyTemplate, EnemySkill  # type: ignore

    if os.environ.get("SKIP_TEST_LOADDATA", "").strip() in {"1", "true", "True", "yes"}:
        return

    try:
        if EnemyTemplate.objects.exists() or EnemySkill.objects.exists():
            return
    except Exception:
        pass

    with django_db_blocker.unblock():
        from django.core.management import call_command
        try:
            call_command("loaddata", "enemygen_testdata.json", verbosity=0, ignorenonexistent=True)
        except Exception:
            return


def _extract_ids_from_index_json(resp_bytes: bytes) -> set[int]:
    data = json.loads(resp_bytes.decode("utf-8"))
    # index_json returns a list of template dicts with an 'id' key for each entry
    return {int(item["id"]) for item in data if isinstance(item, dict) and "id" in item}


def test_index_json_returns_all_published_ids(client, load_data_for_index_json):
    from enemygen.models import EnemyTemplate  # type: ignore

    expected_ids = set(
            EnemyTemplate.objects.filter(published=True).exclude(race__name='Cult').values_list("id", flat=True)
        )

    resp = client.get(reverse("index_json"))
    assert resp.status_code == 200

    returned_ids = _extract_ids_from_index_json(resp.content)

    # Every published template id should be present in index_json result
    missing = expected_ids - returned_ids
    assert not missing, f"index_json missing published template ids: {sorted(missing)}"

    # Sanity: ensure no extraneous types
    assert all(isinstance(x, int) for x in returned_ids)

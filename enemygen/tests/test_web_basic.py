import pytest
from django.urls import reverse


pytestmark = pytest.mark.django_db

@pytest.fixture(scope="session")
def load_data(django_db_setup, django_db_blocker):
    """
    Load baseline data once per test session.
    Because tests run against the normal DB (not a test_ clone),
    make this idempotent: if core data already exists, skip loaddata.
    """
    import os
    from enemygen.models import EnemyTemplate, EnemySkill  # type: ignore

    # Allow skipping fixture import entirely if environment indicates existing prod data
    if os.environ.get("SKIP_TEST_LOADDATA", "").strip() in {"1", "true", "True", "yes"}:
        return

    # If we already have core data, assume baseline data is present.
    try:
        if EnemyTemplate.objects.exists() or EnemySkill.objects.exists():
            return
    except Exception:
        # If the tables don't exist yet, proceed to loaddata
        pass

    # Load the provided fixture with baseline data
    with django_db_blocker.unblock():
        from django.core.management import call_command
        # Use --ignorenonexistent just in case optional apps are absent; fail on real duplicates
        try:
            call_command("loaddata", "enemygen_testdata.json", verbosity=0, ignorenonexistent=True)
        except Exception:
            # If duplicate errors occur anyway (e.g., partial existing data), skip loading
            # to prevent IntegrityError from breaking the entire test session.
            # Tests rely on read-only pages which should work with existing data.
            return


def test_home_page_200(client, load_data):
    resp = client.get(reverse("home"))
    assert resp.status_code == 200
    # Basic content markers
    assert b"Encounter Generator" in resp.content
    # Static CSS ref (from base.html)
    assert b"base.css" in resp.content


def test_index_page_200(client, load_data):
    resp = client.get(reverse("index"))
    assert resp.status_code == 200
    # Should render the enemy_template_list table
    assert b"enemy_template_list" in resp.content


def test_party_index_page_200(client, load_data):
    resp = client.get(reverse("party_index"))
    assert resp.status_code == 200
    assert b"party_list" in resp.content


def test_enemy_template_detail_200(client, load_data):
    # Pick first template id from index_json
    resp = client.get(reverse("index"))
    assert resp.status_code == 200
    # naive scrape: look for href to enemy_template/<id>/
    import re
    m = re.search(rb"/enemy_template/(\d+)/", resp.content)
    assert m, "Could not find enemy_template link in index page"
    et_id = int(m.group(1))

    resp2 = client.get(reverse("enemy_template", args=[et_id]))
    assert resp2.status_code == 200
    # Check star icon usage (static path rendered via {% static %})
    assert b"images/star_" in resp2.content



def test_generate_enemies_post_minimal(client, load_data):
    # Get a template ID from index as above
    resp = client.get(reverse("index"))
    assert resp.status_code == 200
    import re
    m = re.search(rb"name=\"enemy_template_id_(\d+)\"", resp.content)
    assert m, "No enemy_template_id_* input found on index page"
    et_id = int(m.group(1))

    # POST to generate_enemies with minimal payload: include one template amount
    post_data = {f"enemy_template_id_{et_id}": "1"}
    resp2 = client.post(reverse("generate_enemies"), data=post_data)
    assert resp2.status_code == 200
    # Generated page should include an enemies container and some table markers
    assert b"class=\"enemy_container\"" in resp2.content or b"class=\"row_container\"" in resp2.content


def test_rest_search_endpoint(client, load_data):
    # Ensure search returns JSON structure with 'results'
    url = reverse("search")
    resp = client.get(url, {"string": "", "rank_filter": [], "cult_rank_filter": []})
    assert resp.status_code == 200
    # Avoid strict JSON parsing if it returns application/json already; just sanity check key
    assert b"results" in resp.content

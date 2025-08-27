import json
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="session")
def load_data_for_generate_json(django_db_setup, django_db_blocker):
    """Load baseline data once per session in an idempotent way.
    Mirrors the strategy used in other tests and respects SKIP_TEST_LOADDATA.
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


def _pick_template():
    from enemygen.models import EnemyTemplate  # type: ignore
    # Prefer a published, non-Cult template that likely has related fields
    et = (
        EnemyTemplate.objects.filter(published=True)
        .exclude(race__name="Cult")
        .select_related("race", "owner")
        .first()
    )
    assert et is not None, "No published EnemyTemplate found; ensure fixture data is loaded"
    return et


def test_generate_enemies_json_amount_1_contains_expected_fields(client, load_data_for_generate_json):
    from enemygen.models import EnemyStat, EnemySkill, EnemyHitLocation, SkillAbstract  # type: ignore

    et = _pick_template()

    url = reverse("generate_enemies_json")
    resp = client.get(url, {"id": et.id, "amount": 1})
    assert resp.status_code == 200

    payload = json.loads(resp.content.decode("utf-8"))
    assert isinstance(payload, list)
    assert len(payload) == 1, "amount=1 should produce a single generated enemy"

    enemy = payload[0]
    # Core scalar fields from DB
    assert enemy["name"].startswith(et.name[:1])  # name may include suffix like _1
    assert enemy["cult_rank"] == getattr(et, "cult_rank", enemy["cult_rank"])  # numeric rank
    assert enemy.get("notes", "") == (et.notes or "")

    # Stats: names should reflect EnemyStat links (values are randomized)
    expected_stat_names = list(
        EnemyStat.objects.filter(enemy_template=et).select_related("stat").values_list("stat__name", flat=True)
    )
    # Some data sets may not have explicit EnemyStat rows for each stat; ensure at least a subset match
    returned_stat_names = {list(d.keys())[0] for d in enemy.get("stats", []) if isinstance(d, dict) and d}
    for sname in expected_stat_names:
        assert sname in returned_stat_names, f"Missing stat name in JSON: {sname}"

    # Skills: ensure at least the defined EnemySkill names are present
    expected_skill_names = list(
        EnemySkill.objects.filter(enemy_template=et).select_related("skill").values_list("skill__name", flat=True)
    )
    returned_skill_names = {list(d.keys())[0] for d in enemy.get("skills", []) if isinstance(d, dict) and d}
    for sk in expected_skill_names:
        assert sk in returned_skill_names, f"Missing skill in JSON: {sk}"

    # Hit locations: ensure names align
    expected_hl_names = list(
        EnemyHitLocation.objects.filter(enemy_template=et).select_related("hit_location").values_list(
            "hit_location__name", flat=True
        )
    )
    returned_hl_names = {d.get("name") for d in enemy.get("hit_locations", []) if isinstance(d, dict)}
    for hl in expected_hl_names:
        assert hl in returned_hl_names, f"Missing hit location in JSON: {hl}"

    # Spells lists must be present (may be empty)
    for key in ("folk_spells", "theism_spells", "sorcery_spells", "mysticism_spells"):
        assert key in enemy
        assert isinstance(enemy[key], list)

    # Combat styles structure (may be empty) must have expected shape if present
    if enemy.get("combat_styles"):
        assert isinstance(enemy["combat_styles"], list)
        cs0 = enemy["combat_styles"][0]
        assert "name" in cs0 and "weapons" in cs0
        if cs0.get("weapons"):
            w0 = cs0["weapons"][0]
            # spot-check some keys from views_lib.enemy_as_json
            for k in ("name", "damage", "ap", "hp", "size", "reach", "effects", "type"):
                assert k in w0

    # Attributes should be present (dict)
    assert "attributes" in enemy and isinstance(enemy["attributes"], dict)

    # Cults/features/spirits should be lists (may be empty)
    for key in ("cults", "features", "spirits"):
        assert key in enemy and isinstance(enemy[key], list)

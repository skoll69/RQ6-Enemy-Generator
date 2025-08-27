import pytest
from django.urls import reverse
from django.utils.html import escape

pytestmark = pytest.mark.django_db


@ pytest.fixture(scope="session")
def load_data_for_ui(django_db_setup, django_db_blocker):
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


def test_enemy_template_read_only_matches_db_fields(client, load_data_for_ui):
    from enemygen.models import EnemyStat, EnemyHitLocation  # type: ignore

    et = _pick_template()

    url = reverse("enemy_template", args=[et.id])
    resp = client.get(url)
    assert resp.status_code == 200

    html = resp.content.decode("utf-8", errors="ignore")

    # 1) Name (allow either literal or HTML-escaped)
    assert (et.name in html) or (escape(et.name) in html)

    # 2) Rank display
    rank_disp = et.get_rank_display()
    assert rank_disp in html

    # 3) Race link and name
    race_href = f"/race/{et.race.id}/"
    assert race_href in html
    assert et.race.name in html

    # 4) Cult rank display
    cult_disp = et.get_cult_rank_display()
    assert cult_disp in html

    # 5) Notes (if present)
    if et.notes:
        note_text = str(et.notes)
        assert (note_text in html) or (escape(note_text) in html)

    # 6) Creator username
    assert et.owner.username in html

    # 7) Attributes: Movement and Natural armor
    assert str(et.movement) in html
    if et.natural_armor:
        assert "Natural armor" in html and "Yes" in html
    else:
        assert "Natural armor" in html and "No" in html

    # 8) Stats table: each stat name and die_set visible
    stat_qs = EnemyStat.objects.filter(enemy_template=et).select_related("stat")
    for st in stat_qs:
        assert st.stat.name in html
        # die_set may be an empty string in some datasets; only assert if it is non-empty
        if st.die_set:
            assert st.die_set in html

    # 9) Hit locations: name, range, and armor (armor optional if empty)
    hl_qs = EnemyHitLocation.objects.filter(enemy_template=et).select_related("hit_location")
    for hl in hl_qs:
        # range renders as safe HTML text like "1-3"
        rng = str(hl.range)
        assert rng in html
        assert hl.name in html
        if hl.armor:
            assert hl.armor in html

    # 10) Tags (if any)
    for tag_name in et.get_tags():
        assert tag_name in html

    # 11) Namelist (if present)
    if getattr(et, "namelist_id", None):
        assert et.namelist.name in html

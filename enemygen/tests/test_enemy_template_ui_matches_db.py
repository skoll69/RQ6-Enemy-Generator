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
    print("[ui_matches] GET:", url)
    print(f"[ui_matches] template.id={et.id} name={et.name}")
    assert resp.status_code == 200

    html = resp.content.decode("utf-8", errors="ignore")

    # 1) Name (allow either literal or HTML-escaped)
    print("[ui_matches][name] expecting one of:")
    print("  - literal:", et.name)
    print("  - escaped:", escape(et.name))
    assert (et.name in html) or (escape(et.name) in html)

    # 2) Rank display
    rank_disp = et.get_rank_display()
    print("[ui_matches][rank] expected rank display:", rank_disp)
    assert rank_disp in html

    # 3) Race link and name
    race_href = f"/race/{et.race.id}/"
    print("[ui_matches][race] href:", race_href, " name:", et.race.name)
    assert race_href in html
    assert et.race.name in html

    # 4) Cult rank display
    cult_disp = et.get_cult_rank_display()
    print("[ui_matches][cult_rank] expected display:", cult_disp)
    assert cult_disp in html

    # 5) Notes (if present)
    if et.notes:
        note_text = str(et.notes)
        print("[ui_matches][notes] expecting one of:")
        print("  - literal:", note_text)
        print("  - escaped:", escape(note_text))
        assert (note_text in html) or (escape(note_text) in html)
    else:
        print("[ui_matches][notes] no notes present in DB; skipping")

    # 6) Creator username
    print("[ui_matches][creator] username:", et.owner.username)
    assert et.owner.username in html

    # 7) Attributes: Movement and Natural armor
    print("[ui_matches][attributes] movement:", et.movement, " natural_armor:", et.natural_armor)
    assert str(et.movement) in html
    if et.natural_armor:
        print("[ui_matches][attributes] expect 'Natural armor' + 'Yes'")
        assert "Natural armor" in html and "Yes" in html
    else:
        print("[ui_matches][attributes] expect 'Natural armor' + 'No'")
        assert "Natural armor" in html and "No" in html

    # 8) Stats table: each stat name and die_set visible
    stat_qs = EnemyStat.objects.filter(enemy_template=et).select_related("stat")
    print(f"[ui_matches][stats] total stats: {stat_qs.count()}")
    for st in stat_qs:
        print("  - stat:", st.stat.name, " die_set:", st.die_set)
        assert st.stat.name in html
        # die_set may be an empty string in some datasets; only assert if it is non-empty
        if st.die_set:
            assert st.die_set in html

    # 9) Hit locations: name, range, and armor (armor optional if empty)
    hl_qs = EnemyHitLocation.objects.filter(enemy_template=et).select_related("hit_location")
    print(f"[ui_matches][hit_locations] total HL: {hl_qs.count()}")
    for hl in hl_qs:
        rng = str(hl.range)
        print("  - HL name:", hl.name, " range:", rng, " armor:", hl.armor)
        # range renders as safe HTML text like "1-3"
        assert rng in html
        assert hl.name in html
        if hl.armor:
            assert hl.armor in html

    # 10) Tags (if any)
    tags = list(et.get_tags())
    print(f"[ui_matches][tags] tags: {tags}")
    for tag_name in tags:
        assert tag_name in html

    # 11) Namelist (if present)
    if getattr(et, "namelist_id", None):
        print("[ui_matches][namelist] name:", et.namelist.name)
        assert et.namelist.name in html
    else:
        print("[ui_matches][namelist] no namelist linked; skipping")

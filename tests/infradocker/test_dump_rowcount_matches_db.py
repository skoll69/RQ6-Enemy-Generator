import csv
from pathlib import Path
import pytest
import sys

from .conftest import run, env_vars


@pytest.mark.infra
@pytest.mark.live_db
def test_dump_rowcount_csv_matches_database(has_docker_cli, ensure_docker_run_started, ensure_dump_uploaded, env_vars):
    """
    Generate dump_rowcount.csv from dump.sql and compare each table's expected rowcount
    to the actual count in the live database using docker exec (root).
    """
    if not has_docker_cli:
        pytest.skip("docker CLI not present on this system")

    project_root = Path(__file__).resolve().parents[2]
    dump_path = project_root / 'dump.sql'
    assert dump_path.exists(), f"dump.sql not found at {dump_path}"

    # 1) Generate CSV via Makefile
    code, out, err = run(['make', 'dump-rowcount'], timeout=120)
    print(f"[make dump-rowcount] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}", file=sys.stderr)
    assert code == 0, f"make dump-rowcount failed: {err or out}"

    csv_path = project_root / 'dump_rowcount.csv'
    assert csv_path.exists(), f"Rowcount CSV not generated at {csv_path}"

    # 2) Load expected rowcounts
    expected = []  # list of (table, rowcount)
    with csv_path.open('r', encoding='utf-8') as cf:
        reader = csv.DictReader(cf)
        for row in reader:
            table = row['table']
            try:
                cnt = int(row['rowcount'])
            except Exception:
                continue
            expected.append((table, cnt))

    assert expected, "No rows parsed from dump_rowcount.csv"

    db_name = env_vars.get('DB_NAME')
    root_pw = env_vars.get('MYSQL_ROOT_PASSWORD')
    if not (db_name and root_pw):
        pytest.skip("DB_NAME/MYSQL_ROOT_PASSWORD not set in .env; cannot verify live DB counts")

    # Ensure exact equality by re-creating the database and importing the dump freshly
    code, out, err = run(['make', 'import-dump-clean'], timeout=900)
    print(f"[make import-dump-clean] exit={code}\nSTDOUT:\n{out}\nSTDERR:\n{err}", file=sys.stderr)
    assert code == 0, f"make import-dump-clean failed: {err or out}"

    # 3) Compare counts: SELECT COUNT(*) FROM `<table>`
    mismatches = []
    for table, expected_cnt in expected:
        code, out, err = run([
            'docker', 'exec', '-i', 'mythras-mysql', 'sh', '-c',
            f"MYSQL_PWD='{root_pw}' mysql -N -B -uroot {db_name} -e 'SELECT COUNT(*) FROM `{table}`'"
        ], timeout=30)
        if code != 0:
            mismatches.append({
                'table': table,
                'expected': expected_cnt,
                'actual': None,
                'note': f"query failed: {err or out}"
            })
            continue
        out = (out or '').strip()
        if not out.isdigit():
            mismatches.append({
                'table': table,
                'expected': expected_cnt,
                'actual': None,
                'note': f"non-numeric result: {out!r}"
            })
            continue
        actual_cnt = int(out)
        if actual_cnt != expected_cnt:
            mismatches.append({
                'table': table,
                'expected': expected_cnt,
                'actual': actual_cnt,
                'note': 'count mismatch'
            })

    if mismatches:
        # Print each mismatching table with expected and actual counts clearly
        lines = []
        for m in mismatches:
            exp = m['expected']
            act = 'N/A' if m['actual'] is None else m['actual']
            note = m.get('note') or ''
            lines.append(f"- table={m['table']}, expected={exp}, actual={act}{(' (' + note + ')') if note else ''}")
        details = "\n".join(lines)
        pytest.fail("Rowcount mismatches between dump_rowcount.csv and database:\n" + details)

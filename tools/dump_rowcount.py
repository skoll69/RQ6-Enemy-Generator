#!/usr/bin/env python3
import argparse
import csv
import re
import time
from datetime import datetime
from pathlib import Path

# Simple parser for MySQL dumps to count inserted rows per table
# It looks for INSERT INTO <table> ... VALUES (...),(...),...; and counts the top-level value tuples.

# Support variants like:
# INSERT [IGNORE|DELAYED|LOW_PRIORITY] INTO `db`.`table` [(col,...)] VALUES ...
# REPLACE INTO `table` [(col,...)] VALUES ...
INSERT_RE = re.compile(
    r"^\s*(INSERT|REPLACE)\s+(?:IGNORE\s+|DELAYED\s+|LOW_PRIORITY\s+)?INTO\s+"
    r"(?:`?[A-Za-z0-9_]+`?\.)?`?([A-Za-z0-9_]+)`?"  # optional schema, capture table
    r"\s*(?:\([^;]*?\)\s*)?"                      # optional column list
    r"VALUES\s*(.*)$",
    re.IGNORECASE,
)


def _find_stmt_end(sql: str) -> int:
    """Return index of the first semicolon that terminates the current SQL statement,
    skipping those inside quotes or comments. Returns -1 if not found."""
    i = 0
    n = len(sql)
    in_squote = False
    in_dquote = False
    in_line_comment = False
    in_block_comment = False
    while i < n:
        ch = sql[i]
        nxt = sql[i+1] if i + 1 < n else ''
        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == '*' and nxt == '/':
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if not in_squote and not in_dquote:
            if ch == '-' and nxt == '-':
                in_line_comment = True
                i += 2
                continue
            if ch == '#':
                in_line_comment = True
                i += 1
                continue
            if ch == '/' and nxt == '*':
                in_block_comment = True
                i += 2
                continue
        if in_squote:
            if ch == '\\':
                i += 2
                continue
            if ch == "'":
                in_squote = False
                i += 1
                continue
            i += 1
            continue
        if in_dquote:
            if ch == '\\':
                i += 2
                continue
            if ch == '"':
                in_dquote = False
                i += 1
                continue
            i += 1
            continue
        if ch == "'":
            in_squote = True
            i += 1
            continue
        if ch == '"':
            in_dquote = True
            i += 1
            continue
        if ch == ';':
            return i
        i += 1
    return -1


def _strip_comments(values_blob: str) -> str:
    """Remove comments from a VALUES blob while preserving content in quotes."""
    out = []
    i = 0
    n = len(values_blob)
    in_squote = False
    in_dquote = False
    in_line_comment = False
    in_block_comment = False
    while i < n:
        ch = values_blob[i]
        nxt = values_blob[i+1] if i + 1 < n else ''
        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
                out.append(ch)
            i += 1
            continue
        if in_block_comment:
            if ch == '*' and nxt == '/':
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if not in_squote and not in_dquote:
            if ch == '-' and nxt == '-':
                in_line_comment = True
                i += 2
                continue
            if ch == '#':
                in_line_comment = True
                i += 1
                continue
            if ch == '/' and nxt == '*':
                in_block_comment = True
                i += 2
                continue
        if ch == "'" and not in_dquote:
            in_squote = not in_squote
            out.append(ch)
            i += 1
            continue
        if ch == '"' and not in_squote:
            in_dquote = not in_dquote
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def count_tuples_in_values(values_blob: str) -> int:
    """Count top-level parenthesized tuple groups in a VALUES blob.
    Assumes input like: (..),(..),(..);
    Works across lines. Skips parentheses inside quoted strings and comments."""
    blob = _strip_comments(values_blob)
    depth = 0
    count = 0
    in_tuple = False
    in_squote = False
    in_dquote = False
    escape = False
    for ch in blob:
        if in_squote:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == "'":
                in_squote = False
            continue
        if in_dquote:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_dquote = False
            continue
        if ch == "'":
            in_squote = True
            continue
        if ch == '"':
            in_dquote = True
            continue
        if ch == '(':
            depth += 1
            if depth == 1:
                in_tuple = True
        elif ch == ')':
            if depth > 0:
                depth -= 1
                if depth == 0 and in_tuple:
                    count += 1
                    in_tuple = False
    return count


def parse_dump(dump_path: Path) -> dict:
    """Parse dump.sql and return {table: intended_rowcount} by counting INSERT value tuples."""
    table_counts: dict[str, int] = {}

    if not dump_path.exists():
        raise FileNotFoundError(f"Dump file not found: {dump_path}")

    # Accumulate lines between INSERT start and terminating semicolon
    current_table = None
    buffer_parts: list[str] = []

    with dump_path.open('r', encoding='utf-8', errors='ignore') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')

            # If not currently inside an INSERT, look for start
            if current_table is None:
                m = INSERT_RE.match(line)
                if not m:
                    continue
                # group(2) = table, group(3) = tail after VALUES
                current_table = m.group(2)
                rest = m.group(3)
                buffer_parts = [rest]
                # If this line already contains a terminating semicolon (not inside quotes/comments), process immediately
                joined = ''.join(buffer_parts)
                idx = _find_stmt_end(joined)
                if idx != -1:
                    blob = joined[:idx]
                    tuples = count_tuples_in_values(blob)
                    table_counts[current_table] = table_counts.get(current_table, 0) + tuples
                    current_table = None
                    buffer_parts = []
                continue

            # We are inside an INSERT values continuation
            buffer_parts.append(line)
            joined = '\n'.join(buffer_parts)
            idx = _find_stmt_end(joined)
            if idx != -1:
                blob = joined[:idx]
                tuples = count_tuples_in_values(blob)
                table_counts[current_table] = table_counts.get(current_table, 0) + tuples
                current_table = None
                buffer_parts = []

    return table_counts


def main():
    a = argparse.ArgumentParser(description="Count inserted rows per table from a MySQL dump.sql and write CSV (table,rowcount)")
    a.add_argument('--dump', default=str(Path(__file__).resolve().parents[1] / 'dump.sql'), help='Path to dump.sql')
    a.add_argument('--out', default=str(Path(__file__).resolve().parents[1] / 'dump_rowcount.csv'), help='Output CSV path')
    args = a.parse_args()

    dump_path = Path(args.dump)
    out_path = Path(args.out)

    # Start printout
    start_ts = datetime.now().isoformat(timespec='seconds')
    t0 = time.time()
    print(f"[dump_rowcount] START {start_ts} dump={dump_path}")

    counts = parse_dump(dump_path)

    # Write CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', newline='', encoding='utf-8') as cf:
        w = csv.writer(cf)
        w.writerow(['table', 'rowcount'])
        for table, cnt in sorted(counts.items()):
            w.writerow([table, cnt])

    # End printout
    end_ts = datetime.now().isoformat(timespec='seconds')
    duration = time.time() - t0
    print(f"Wrote rowcount CSV: {out_path} ({len(counts)} tables)")
    print(f"[dump_rowcount] END   {end_ts} dump={dump_path} out={out_path} tables={len(counts)} duration={duration:.2f}s")


if __name__ == '__main__':
    main()

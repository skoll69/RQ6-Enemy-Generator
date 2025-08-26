#!/usr/bin/env python3
import argparse
import csv
import re
import os
import time
from datetime import datetime
from pathlib import Path

# We now use a SQL tokenizer/parser (sqlparse) instead of brittle regexes.
# This greatly improves correctness on multi-line INSERTs, odd whitespace, comments, and quoted strings.
try:
    import sqlparse  # type: ignore
    from sqlparse.sql import Identifier, IdentifierList, TokenList
    from sqlparse.tokens import Keyword, DML
except Exception:
    sqlparse = None  # We'll fall back to the previous robust regex-based parser if sqlparse isn't available.


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


def _count_values_section(values_sql: str) -> int:
    return count_tuples_in_values(values_sql)


def _parse_with_sqlparse(sql_text: str) -> dict:
    counts: dict[str, int] = {}
    # sqlparse can be extremely slow for huge dumps; only use if explicitly enabled
    if not os.getenv('DUMP_ROWCOUNT_USE_SQLPARSE'):
        return counts
    for stmt in sqlparse.parse(sql_text):
        tokens = [t for t in stmt.tokens if not t.is_whitespace]
        if not tokens:
            continue
        dml_tok = next((t for t in tokens if t.ttype is DML or (t.ttype is Keyword and t.value.upper() in ("INSERT", "REPLACE"))), None)
        if not dml_tok:
            continue
        upper = stmt.normalized.upper()
        if not (upper.startswith('INSERT') or upper.startswith('REPLACE')):
            continue
        table_name = None
        saw_into = False
        for t in tokens:
            if t.ttype is Keyword and t.value.upper() == 'INTO':
                saw_into = True
                continue
            if saw_into:
                if isinstance(t, Identifier):
                    table_name = t.get_real_name()
                    break
                val = t.value.strip()
                if val:
                    if '.' in val:
                        val = val.split('.')[-1]
                    table_name = val.strip('`')
                    break
        if not table_name:
            continue
        raw = str(stmt)
        m = re.search(r"\bVALUE(S)?\b", raw, flags=re.IGNORECASE)
        if not m:
            continue
        values_sql = raw[m.end():]
        if values_sql.endswith(';'):
            values_sql = values_sql[:-1]
        tuples = _count_values_section(values_sql)
        counts[table_name] = counts.get(table_name, 0) + tuples
    return counts


def parse_dump(dump_path: Path) -> dict:
    """Parse dump.sql and return {table: intended_rowcount} by counting INSERT value tuples.
    Default: use robust streaming parser to avoid hangs. Optionally, if DUMP_ROWCOUNT_USE_SQLPARSE=1,
    try sqlparse first, then fall back to streaming on error.
    """
    if not dump_path.exists():
        raise FileNotFoundError(f"Dump file not found: {dump_path}")

    # Optional sqlparse path (disabled by default)
    if sqlparse is not None and os.getenv('DUMP_ROWCOUNT_USE_SQLPARSE'):
        try:
            sql_text = dump_path.read_text(encoding='utf-8', errors='ignore')
            return _parse_with_sqlparse(sql_text)
        except Exception as e:
            if os.getenv('DEBUG'):
                print(f"[dump_rowcount] sqlparse failed, falling back to streaming parser: {e}")
            # fall through to streaming

    # Streaming parser: reads file line-by-line, accumulates only current statement
    table_counts: dict[str, int] = {}
    current_table: str | None = None
    buffer_parts: list[str] = []
    waiting_for_values = False

    # emergency guard: prevent pathological single-statement buffers (e.g., >100MB)
    MAX_STMT_CHARS = 100 * 1024 * 1024

    with dump_path.open('r', encoding='utf-8', errors='ignore') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')

            # If not currently inside an INSERT
            if current_table is None and not waiting_for_values:
                # Fast pre-filter to skip lines that cannot be start of INSERT/REPLACE
                if not line or ('INSERT' not in line.upper() and 'REPLACE' not in line.upper()):
                    continue
                # Identify table name after INTO (schema-qualified allowed)
                m_into = re.search(r"\b(INSERT|REPLACE)\b\s+(?:IGNORE\s+|DELAYED\s+|LOW_PRIORITY\s+)?INTO\s+((`?[A-Za-z0-9_]+`?\.)?`?([A-Za-z0-9_]+)`?)", line, flags=re.IGNORECASE)
                if not m_into:
                    continue
                current_table = m_into.group(4)
                # Look for VALUES on same line
                m_vals = re.search(r"\bVALUES?\b", line, flags=re.IGNORECASE)
                if m_vals:
                    rest = line[m_vals.end():]
                    buffer_parts = [rest]
                    joined = ''.join(buffer_parts)
                    idx = _find_stmt_end(joined)
                    if idx != -1:
                        blob = joined[:idx]
                        tuples = count_tuples_in_values(blob)
                        table_counts[current_table] = table_counts.get(current_table, 0) + tuples
                        current_table = None
                        buffer_parts = []
                    else:
                        waiting_for_values = False
                    continue
                else:
                    # values appear later lines
                    waiting_for_values = True
                    buffer_parts = []
                    continue

            # Waiting for VALUES portion after header
            if waiting_for_values and current_table is not None:
                m_vals2 = re.search(r"\bVALUES?\b", line, flags=re.IGNORECASE)
                if not m_vals2:
                    continue
                rest = line[m_vals2.end():]
                buffer_parts = [rest]
                waiting_for_values = False
                joined = ''.join(buffer_parts)
                idx = _find_stmt_end(joined)
                if idx != -1:
                    blob = joined[:idx]
                    tuples = count_tuples_in_values(blob)
                    table_counts[current_table] = table_counts.get(current_table, 0) + tuples
                    current_table = None
                    buffer_parts = []
                continue

            # Accumulating VALUES continuation
            if current_table is not None and not waiting_for_values:
                buffer_parts.append(line)
                # emergency guard on buffer size
                if sum(len(p) for p in buffer_parts) > MAX_STMT_CHARS:
                    if os.getenv('DEBUG'):
                        print(f"[dump_rowcount] WARNING: statement for table {current_table} exceeded {MAX_STMT_CHARS} chars; flushing partial")
                    blob = '\n'.join(buffer_parts)
                    # try to count what we can up to current point (best-effort)
                    tuples = count_tuples_in_values(blob)
                    table_counts[current_table] = table_counts.get(current_table, 0) + tuples
                    current_table = None
                    buffer_parts = []
                    continue
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


import os
import re
import sqlite3
import sys

def get_mysql_schema(dump_file):
    schema = {}
    current_table = None
    with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            create_match = re.search(r'CREATE TABLE [`"]([^`"]+)[`"] \(', line)
            if create_match:
                current_table = create_match.group(1)
                schema[current_table] = []
                continue
            
            if current_table:
                col_match = re.search(r'^\s*[`"]([^`"]+)[`"]', line)
                if col_match:
                    schema[current_table].append(col_match.group(1))
                elif line.strip().startswith(('PRIMARY KEY', 'KEY', 'UNIQUE KEY', 'CONSTRAINT', 'FULLTEXT KEY')):
                    continue
                elif line.strip().startswith(')'):
                    current_table = None
    return schema

def get_sqlite_schema(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info('{table}');")
        schema[table] = [row[1] for row in cursor.fetchall()]
    conn.close()
    return schema

def clean_value(val):
    if val == 'NULL':
        return None
    if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
        content = val[1:-1]
        content = content.replace("\\'", "'")
        content = content.replace('\\"', '"')
        content = content.replace("\\n", "\n")
        content = content.replace("\\r", "\r")
        content = content.replace("\\t", "\t")
        content = content.replace("\\\\", "\\")
        return content
    return val

def parse_values(values_str):
    results = []
    current_pos = 0
    while current_pos < len(values_str):
        if values_str[current_pos] == '(':
            current_pos += 1
            row = []
            current_val = ""
            in_string = False
            string_char = None
            escaped = False
            
            while current_pos < len(values_str):
                c = values_str[current_pos]
                if escaped:
                    current_val += c
                    escaped = False
                elif c == '\\':
                    current_val += c
                    escaped = True
                elif not in_string and (c == "'" or c == '"'):
                    in_string = True
                    string_char = c
                    current_val += c
                elif in_string and c == string_char:
                    in_string = False
                    current_val += c
                elif not in_string and c == ',':
                    row.append(clean_value(current_val.strip()))
                    current_val = ""
                elif not in_string and c == ')':
                    row.append(clean_value(current_val.strip()))
                    results.append(row)
                    current_pos += 1
                    break
                else:
                    current_val += c
                current_pos += 1
        else:
            current_pos += 1
    return results

def verify():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Prefer local_dump.sql if it exists
    dump_file = os.path.join(script_dir, 'local_dump.sql')
    if not os.path.exists(dump_file):
        dump_file = os.path.join(script_dir, 'dump.sql')
        
    db_file = os.path.join(script_dir, '..', 'db.sqlite3')

    if not os.path.exists(dump_file):
        print(f"Error: {dump_file} not found.")
        return
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found.")
        return
    
    mysql_schema = get_mysql_schema(dump_file)
    sqlite_schema = get_sqlite_schema(db_file)
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    table_data = {}
    
    # Use the robust parser from smart_import.py
    with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
        current_table = None
        current_values = ""
        in_insert = False
        in_string = False
        string_char = None
        escaped = False
        
        for line in f:
            if not in_insert:
                match = re.match(r'INSERT INTO [`"]([^`"]+)[`"] VALUES ', line)
                if match:
                    current_table = match.group(1)
                    current_values = line[match.end():]
                    in_insert = True
            
            if in_insert:
                pos = 0
                while pos < len(current_values):
                    c = current_values[pos]
                    if escaped:
                        escaped = False
                    elif c == '\\':
                        escaped = True
                    elif not in_string and (c == "'" or c == '"'):
                        in_string = True
                        string_char = c
                    elif in_string and c == string_char:
                        in_string = False
                    elif not in_string and c == ';':
                        val_to_process = current_values[:pos]
                        if current_table not in table_data:
                            table_data[current_table] = []
                        table_data[current_table].extend(parse_values(val_to_process))
                        
                        remaining = current_values[pos+1:]
                        current_values = ""
                        in_insert = False
                        
                        match = re.match(r'^\s*INSERT INTO [`"]([^`"]+)[`"] VALUES ', remaining)
                        if match:
                            current_table = match.group(1)
                            current_values = remaining[match.end():]
                            in_insert = True
                            pos = -1
                        else:
                            break
                    pos += 1
                
                if in_insert:
                    next_line = f.readline()
                    if not next_line:
                        break
                    current_values += next_line

    summary = []
    all_passed = True
    
    for table_name, dump_rows in table_data.items():
        if table_name not in sqlite_schema:
            summary.append(f"Table {table_name}: SKIPPED (not in SQLite)")
            continue
            
        m_cols = mysql_schema.get(table_name, [])
        s_cols = sqlite_schema[table_name]
        
        # We need a way to check if a row exists.
        # Most tables have 'id' as primary key at index 0 or somewhere.
        # We'll use all mapped columns for verification.
        
        print(f"Verifying {table_name}...")
        
        # Map dump rows to sqlite schema
        mapped_rows = []
        if m_cols and set(s_cols).issubset(set(m_cols)) and (len(dump_rows[0]) == len(m_cols)):
            for row in dump_rows:
                row_dict = dict(zip(m_cols, row))
                mapped_rows.append(tuple(row_dict.get(col) for col in s_cols))
        elif len(dump_rows[0]) == len(s_cols):
            mapped_rows = [tuple(row) for row in dump_rows]
        else:
            summary.append(f"Table {table_name}: FAILED (Column mismatch)")
            all_passed = False
            continue

        # Get all rows from SQLite for comparison
        cursor.execute(f"SELECT {','.join(['\"'+c+'\"' for c in s_cols])} FROM \"{table_name}\"")
        sqlite_rows = set(cursor.fetchall())
        sqlite_rows_strings = set(tuple(str(x) if x is not None else None for x in r) for r in sqlite_rows)
        
        missing = 0
        diffs = []
        # Pre-calculate stripped string tuples for flexible matching
        sqlite_rows_stripped = set(tuple(x.strip() if isinstance(x, str) else x for x in r) for r in sqlite_rows)
        
        for i, row in enumerate(mapped_rows):
            normalized_row = []
            for val in row:
                if val is not None and val.isdigit():
                    normalized_row.append(int(val))
                elif val is not None and val.replace('.','',1).isdigit():
                    try:
                        normalized_row.append(float(val))
                    except:
                        normalized_row.append(val)
                else:
                    normalized_row.append(val)
            
            normalized_tuple = tuple(normalized_row)
            if normalized_tuple not in sqlite_rows:
                # Try more flexible comparison
                found = False
                # If exact tuple not found, try converting all to strings
                string_tuple = tuple(str(x) if x is not None else None for x in normalized_row)
                if string_tuple in sqlite_rows_strings:
                    found = True
                
                if not found:
                    # Strip whitespace from strings
                    stripped_normalized = tuple(x.strip() if isinstance(x, str) else x for x in normalized_row)
                    if stripped_normalized in sqlite_rows_stripped:
                        found = True
                
                if not found:
                    missing += 1
                    if len(diffs) < 5:
                        diffs.append((row, normalized_tuple))

        if missing == 0:
            summary.append(f"Table {table_name}: PASSED ({len(dump_rows)} rows)")
        else:
            summary.append(f"Table {table_name}: FAILED ({missing}/{len(dump_rows)} rows missing)")
            if diffs:
                # Find the row in SQLite with the same ID (if ID is first column)
                if s_cols[0] == 'id':
                    # Use the ID from the first missing row
                    target_id = diffs[0][1][0]
                    cursor.execute(f"SELECT {','.join(['\"'+c+'\"' for c in s_cols])} FROM \"{table_name}\" WHERE id=?", (target_id,))
                    actual = cursor.fetchone()
                    print(f"DEBUG {table_name} ID={target_id}:")
                    print(f"  Dump mapped: {diffs[0][1]}")
                    print(f"  Actual SQL:  {actual}")
                    if actual:
                         print(f"  Diff: {[(d, a) for d, a in zip(diffs[0][1], actual) if d != a]}")
            all_passed = False

    print("\n--- Verification Summary ---")
    for line in summary:
        print(line)
    
    conn.close()
    if not all_passed:
        sys.exit(1)

if __name__ == '__main__':
    verify()
